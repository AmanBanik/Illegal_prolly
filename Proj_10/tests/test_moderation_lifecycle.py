from datetime import datetime, timezone
import pytest
from Proj_10.src.exceptions import CommentNotFoundError, UnauthorizedError


def test_create_and_retrieve_comment(service):
    comment = service.create_comment(
        post_id="post_100",
        user_id="user_alice",
        content="This is a great system design article!",
    )

    assert comment.id == 1
    assert comment.post_id == "post_100"
    assert comment.user_id == "user_alice"
    assert comment.content == "This is a great system design article!"
    assert not comment.is_edited
    assert comment.created_at is not None
    assert comment.updated_at == comment.created_at

    fetched = service.get_comment(1)
    assert fetched == comment


def test_edit_comment_success(service):
    comment = service.create_comment(
        post_id="post_100",
        user_id="user_alice",
        content="Initial comment version",
    )

    edited = service.edit_comment(
        comment_id=comment.id,
        user_id="user_alice",
        new_content="Updated content with more clarity",
    )

    assert edited.id == comment.id
    assert edited.post_id == "post_100"
    assert edited.user_id == "user_alice"
    assert edited.content == "Updated content with more clarity"
    assert edited.is_edited is True
    assert edited.updated_at >= edited.created_at

    # Verify persistent state update
    fetched = service.get_comment(comment.id)
    assert fetched.content == "Updated content with more clarity"
    assert fetched.is_edited is True


def test_list_comments_chronological_order(service):
    c1 = service.create_comment("post_42", "user_1", "First")
    c2 = service.create_comment("post_42", "user_2", "Second")
    c3 = service.create_comment("post_99", "user_1", "Other post comment")
    c4 = service.create_comment("post_42", "user_3", "Third")

    post_42_comments = service.list_comments("post_42")
    assert len(post_42_comments) == 3
    assert [c.id for c in post_42_comments] == [c1.id, c2.id, c4.id]
    assert [c.content for c in post_42_comments] == ["First", "Second", "Third"]


def test_list_comments_by_user(service):
    service.create_comment("post_1", "user_alice", "Alice comment 1")
    service.create_comment("post_2", "user_bob", "Bob comment 1")
    service.create_comment("post_3", "user_alice", "Alice comment 2")

    alice_comments = service.list_comments_by_user("user_alice")
    assert len(alice_comments) == 2
    assert [c.content for c in alice_comments] == ["Alice comment 1", "Alice comment 2"]

    bob_comments = service.list_comments_by_user("user_bob")
    assert len(bob_comments) == 1
    assert bob_comments[0].content == "Bob comment 1"


def test_delete_comment_lifecycle(service):
    comment = service.create_comment("post_1", "user_alice", "Soon to be deleted")
    assert service.get_comment(comment.id).content == "Soon to be deleted"

    success = service.delete_comment(comment.id, "user_alice")
    assert success is True

    # Verification: comment should no longer exist in lookups
    with pytest.raises(CommentNotFoundError):
        service.get_comment(comment.id)

    assert len(service.list_comments("post_1")) == 0
    assert len(service.list_comments_by_user("user_alice")) == 0
