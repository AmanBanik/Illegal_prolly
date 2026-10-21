import pytest
from Proj_10.src.exceptions import CommentNotFoundError, UnauthorizedError


def test_edit_comment_unauthorized_user(service):
    comment = service.create_comment("post_1", "user_alice", "Alice's original thought")

    # Bob tries to edit Alice's comment
    with pytest.raises(UnauthorizedError) as exc_info:
        service.edit_comment(comment.id, "user_bob", "Bob tampering with Alice's post")
    assert "not authorized to edit comment" in str(exc_info.value)

    # Verify content was not modified
    fetched = service.get_comment(comment.id)
    assert fetched.content == "Alice's original thought"


def test_delete_comment_unauthorized_user(service):
    comment = service.create_comment("post_1", "user_alice", "Alice's comment")

    # Bob tries to delete Alice's comment
    with pytest.raises(UnauthorizedError) as exc_info:
        service.delete_comment(comment.id, "user_bob")
    assert "not authorized to delete comment" in str(exc_info.value)

    # Verify comment still exists
    assert service.get_comment(comment.id).id == comment.id


def test_edit_nonexistent_comment(service):
    with pytest.raises(CommentNotFoundError):
        service.edit_comment(comment_id=999, user_id="user_alice", new_content="New text")


def test_delete_nonexistent_comment(service):
    with pytest.raises(CommentNotFoundError):
        service.delete_comment(comment_id=999, user_id="user_alice")


def test_get_nonexistent_comment(service):
    with pytest.raises(CommentNotFoundError):
        service.get_comment(comment_id=999)
