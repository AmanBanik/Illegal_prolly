from unittest.mock import MagicMock
import pytest
from Proj_10.src.checker import CallableContentChecker
from Proj_10.src.exceptions import CheckerExecutionError
from Proj_10.src.models import ModerationResult
from Proj_10.src.service import ReviewDesk


def test_checker_crash_does_not_consume_comment_id():
    """Verify that when the content checker raises an exception,

    the monotonic sequential ID counter is not incremented.
    """
    call_count = 0

    def unreliable_checker(text: str) -> ModerationResult:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise TimeoutError("Content checker connection timed out")
        return ModerationResult.approved()

    checker = CallableContentChecker(unreliable_checker)
    service = ReviewDesk(checker=checker, max_strikes=3)

    # 1st comment succeeds -> gets ID 1
    c1 = service.create_comment("post_1", "user_1", "First clean comment")
    assert c1.id == 1

    # 2nd comment crashes during moderation
    with pytest.raises(CheckerExecutionError) as exc_info:
        service.create_comment("post_1", "user_2", "This will crash the checker")
    assert "Content checker connection timed out" in str(exc_info.value)

    # 3rd comment succeeds -> MUST get ID 2 (no gap from the failed attempt!)
    c3 = service.create_comment("post_1", "user_3", "Third comment succeeds")
    assert c3.id == 2

    # Verify only 2 comments exist in total
    comments = service.list_comments("post_1")
    assert len(comments) == 2
    assert [c.id for c in comments] == [1, 2]


def test_checker_crash_does_not_increment_user_strikes():
    """Verify that an external checker crash does not falsely penalize the user."""
    mock_checker = MagicMock()
    mock_checker.check_content.side_effect = RuntimeError("500 Internal Checker Error")

    service = ReviewDesk(checker=mock_checker, max_strikes=3)

    user_state_before = service.get_user_state("innocent_user")
    assert user_state_before.strikes == 0

    with pytest.raises(CheckerExecutionError):
        service.create_comment("post_1", "innocent_user", "Completely normal comment")

    user_state_after = service.get_user_state("innocent_user")
    assert user_state_after.strikes == 0
    assert not user_state_after.is_blocked


def test_checker_crash_on_edit_preserves_content_and_strikes():
    """Verify that when editing fails due to checker error, the comment content

    remains untouched and no strike is issued.
    """
    should_fail = False

    def toggle_checker(text: str) -> ModerationResult:
        if should_fail:
            raise ConnectionResetError("Connection reset by peer")
        return ModerationResult.approved()

    service = ReviewDesk(checker=CallableContentChecker(toggle_checker), max_strikes=3)

    # Create initial comment
    comment = service.create_comment("post_1", "user_1", "Original perfect text")
    assert comment.content == "Original perfect text"

    # Trigger checker outage
    should_fail = True
    with pytest.raises(CheckerExecutionError):
        service.edit_comment(comment.id, "user_1", "Attempted revision")

    # Content and strikes must remain unaltered
    fetched = service.get_comment(comment.id)
    assert fetched.content == "Original perfect text"
    assert not fetched.is_edited
    assert service.get_user_state("user_1").strikes == 0


def test_checker_returning_invalid_object_raises_cleanly():
    """Verify that if the checker returns garbage instead of ModerationResult,

    state remains clean.
    """
    bad_checker = CallableContentChecker(lambda text: "invalid_string_not_result")
    service = ReviewDesk(checker=bad_checker)

    with pytest.raises(CheckerExecutionError) as exc_info:
        service.create_comment("post_1", "user_1", "Some content")
    assert "valid ModerationResult" in str(exc_info.value)

    # Verify ID is still 1 on next attempt with a fixed checker
    fixed_checker = CallableContentChecker(lambda text: ModerationResult.approved())
    service._checker = fixed_checker

    c = service.create_comment("post_1", "user_1", "Some content")
    assert c.id == 1
