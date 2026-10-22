"""Input validation and strict type safety tests for CommentService."""

import pytest

from Proj_02.src.exceptions import ValidationError
from Proj_02.src.service import CommentService


def test_reject_boolean_trap_in_numeric_ids(service: CommentService) -> None:
    """Ensure bool is strictly rejected where int is expected (isinstance(True, int) is True)."""
    # Reject True as comment_id
    with pytest.raises(ValidationError) as exc:
        service.get_comment(True)  # type: ignore
    assert "must be an integer, received bool" in str(exc.value)

    # Reject False as comment_id
    with pytest.raises(ValidationError) as exc:
        service.get_comment(False)  # type: ignore
    assert "must be an integer, received bool" in str(exc.value)

    # Reject True in add_reply
    with pytest.raises(ValidationError) as exc:
        service.add_reply(comment_id=True, author_id="alice", content="hello")  # type: ignore
    assert "must be an integer, received bool" in str(exc.value)


def test_reject_boolean_in_string_fields(service: CommentService) -> None:
    """Ensure bool is strictly rejected where string is expected."""
    with pytest.raises(ValidationError) as exc:
        service.add_comment(post_id=True, author_id="user1", content="text")  # type: ignore
    assert "must be a string, received bool" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        service.add_comment(post_id="p1", author_id=False, content="text")  # type: ignore
    assert "must be a string, received bool" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        service.add_comment(post_id="p1", author_id="user1", content=True)  # type: ignore
    assert "must be a string, received bool" in str(exc.value)


def test_reject_empty_and_whitespace_strings(service: CommentService) -> None:
    """Verify empty and whitespace-only strings fail validation."""
    # Empty post_id
    with pytest.raises(ValidationError) as exc:
        service.add_comment("", "author", "content")
    assert "cannot be empty or whitespace-only" in str(exc.value)

    # Whitespace-only author
    with pytest.raises(ValidationError) as exc:
        service.add_comment("p1", "   \t\n  ", "content")
    assert "cannot be empty or whitespace-only" in str(exc.value)

    # Whitespace-only content
    with pytest.raises(ValidationError) as exc:
        service.add_comment("p1", "author", "   ")
    assert "cannot be empty or whitespace-only" in str(exc.value)


def test_reject_non_string_types(service: CommentService) -> None:
    """Verify non-string types fail validation for post_id, author_id, and content."""
    for invalid_val in [None, 123, 45.67, ["list"], {"dict": 1}]:
        with pytest.raises(ValidationError):
            service.add_comment(invalid_val, "author", "content")  # type: ignore

        with pytest.raises(ValidationError):
            service.add_comment("p1", invalid_val, "content")  # type: ignore

        with pytest.raises(ValidationError):
            service.add_comment("p1", "author", invalid_val)  # type: ignore


def test_reject_non_positive_integers(service: CommentService) -> None:
    """Verify IDs must be strictly > 0."""
    with pytest.raises(ValidationError) as exc:
        service.get_comment(0)
    assert "must be greater than 0" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        service.get_comment(-42)
    assert "must be greater than 0" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        service.get_reply(0)
    assert "must be greater than 0" in str(exc.value)


def test_reject_non_integer_types_for_ids(service: CommentService) -> None:
    """Verify floats and string representations of numbers fail numeric ID validation."""
    for invalid_id in [1.5, "1", None, [1]]:
        with pytest.raises(ValidationError):
            service.get_comment(invalid_id)  # type: ignore

        with pytest.raises(ValidationError):
            service.get_reply(invalid_id)  # type: ignore
