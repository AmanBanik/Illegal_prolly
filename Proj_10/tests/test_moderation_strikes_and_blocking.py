import pytest
from Proj_10.src.exceptions import ContentRejectedError, UserBlockedError


def test_strike_accumulation_on_violations(service):
    user_state = service.get_user_state("user_bad")
    assert user_state.strikes == 0
    assert not user_state.is_blocked

    # First violation
    with pytest.raises(ContentRejectedError) as exc_info:
        service.create_comment("post_1", "user_bad", "Check out this spam link")
    assert exc_info.value.current_strikes == 1
    assert not exc_info.value.is_blocked

    state1 = service.get_user_state("user_bad")
    assert state1.strikes == 1
    assert not state1.is_blocked

    # Second violation
    with pytest.raises(ContentRejectedError) as exc_info2:
        service.create_comment("post_2", "user_bad", "Another violation detected")
    assert exc_info2.value.current_strikes == 2
    assert not exc_info2.value.is_blocked

    state2 = service.get_user_state("user_bad")
    assert state2.strikes == 2
    assert not state2.is_blocked

    # Valid comment does not clear or alter existing strikes
    valid_comment = service.create_comment("post_3", "user_bad", "Clean comment here")
    assert valid_comment.id is not None
    assert service.get_user_state("user_bad").strikes == 2


def test_threshold_blocks_user_automatically(service):
    # Service max_strikes is 3
    # Strike 1
    with pytest.raises(ContentRejectedError):
        service.create_comment("post_1", "user_troll", "Spam 1")

    # Strike 2
    with pytest.raises(ContentRejectedError):
        service.create_comment("post_1", "user_troll", "Spam 2")

    # Strike 3 (reaches threshold -> auto-block)
    with pytest.raises(ContentRejectedError) as exc_info:
        service.create_comment("post_1", "user_troll", "Spam 3")
    assert exc_info.value.current_strikes == 3
    assert exc_info.value.is_blocked is True

    user_state = service.get_user_state("user_troll")
    assert user_state.strikes == 3
    assert user_state.is_blocked is True
    assert user_state.blocked_at is not None

    # Subsequent comment attempts are blocked immediately without calling checker
    with pytest.raises(UserBlockedError):
        service.create_comment("post_1", "user_troll", "I promise to be nice now")


def test_blocked_user_cannot_edit_existing_comments(service):
    # User creates a valid comment first
    comment = service.create_comment("post_1", "user_edit", "Clean initial comment")

    # User accumulates 3 strikes elsewhere
    for i in range(3):
        with pytest.raises(ContentRejectedError):
            service.create_comment("post_2", "user_edit", f"Spam {i}")

    assert service.get_user_state("user_edit").is_blocked is True

    # User tries to edit their earlier comment
    with pytest.raises(UserBlockedError):
        service.edit_comment(comment.id, "user_edit", "Edited content")


def test_editing_with_violation_adds_strike(service):
    comment = service.create_comment("post_1", "user_author", "Original good text")
    assert service.get_user_state("user_author").strikes == 0

    # Edit with violation
    with pytest.raises(ContentRejectedError) as exc_info:
        service.edit_comment(comment.id, "user_author", "Edit with spam content")
    assert exc_info.value.current_strikes == 1

    # Verify original comment remains unchanged
    fetched = service.get_comment(comment.id)
    assert fetched.content == "Original good text"
    assert not fetched.is_edited


def test_administrative_unblock_and_reset(service):
    for _ in range(3):
        with pytest.raises(ContentRejectedError):
            service.create_comment("post_1", "user_reform", "Spam")

    assert service.get_user_state("user_reform").is_blocked is True

    # Administrative unblock
    state = service.unblock_user("user_reform", reset_strikes=True)
    assert state.is_blocked is False
    assert state.strikes == 0

    # Can now post clean comments again
    comment = service.create_comment("post_1", "user_reform", "Reformed user comment")
    assert comment.id is not None
