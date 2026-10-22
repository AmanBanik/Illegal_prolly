"""Lifecycle, hierarchy limits, and state isolation tests for CommentService."""

import pytest

from Proj_02.src.exceptions import (
    CommentNotFoundError,
    InvalidHierarchyError,
    ResourceNotFoundError,
    ValidationError,
)
from Proj_02.src.service import CommentService


def test_add_comment_basic_lifecycle(service: CommentService) -> None:
    """Verify adding top-level comments creates valid comment entities."""
    c1 = service.add_comment(post_id="post_100", author_id="user_alice", content="First comment")
    assert c1.id == 1
    assert c1.post_id == "post_100"
    assert c1.author_id == "user_alice"
    assert c1.content == "First comment"
    assert c1.replies == []

    c2 = service.add_comment(post_id="post_100", author_id="user_bob", content="Second comment")
    assert c2.id == 2
    assert c2.post_id == "post_100"
    assert c2.author_id == "user_bob"
    assert c2.content == "Second comment"


def test_independent_auto_incrementing_ids(service: CommentService) -> None:
    """Verify comment and reply sequences increment independently from 1."""
    # Add comments
    c1 = service.add_comment("p1", "u1", "Comment 1")
    c2 = service.add_comment("p1", "u2", "Comment 2")
    assert c1.id == 1
    assert c2.id == 2

    # Add replies
    r1 = service.add_reply(comment_id=c1.id, author_id="u3", content="Reply 1")
    r2 = service.add_reply(comment_id=c1.id, author_id="u4", content="Reply 2")
    assert r1.id == 1  # Independent sequence starting at 1
    assert r2.id == 2

    # Add third comment
    c3 = service.add_comment("p1", "u5", "Comment 3")
    assert c3.id == 3  # Comment sequence continues independently

    # Add reply to comment 2
    r3 = service.add_reply(comment_id=c2.id, author_id="u6", content="Reply 3")
    assert r3.id == 3  # Reply sequence continues independently


def test_two_level_hierarchy_limit_rejection(service: CommentService) -> None:
    """Verify that replies cannot have replies (strict 2-level limit: Post -> Comment -> Reply)."""
    c1 = service.add_comment("post_xyz", "alice", "Parent discussion")
    r1 = service.add_reply(comment_id=c1.id, author_id="bob", content="Direct reply")

    # Attempt to reply to a reply via model method
    with pytest.raises(InvalidHierarchyError) as exc_info1:
        r1.add_reply("charlie", "Nested reply attempt")
    assert "Discussions are strictly limited to two levels" in str(exc_info1.value)

    # Attempt to reply to a reply via service rejection method
    with pytest.raises(InvalidHierarchyError) as exc_info2:
        service.add_reply_to_reply(reply_id=r1.id, author_id="charlie", content="Nested attempt")
    assert "Cannot reply to reply ID" in str(exc_info2.value)

    # Attempt to reply to a reply via target_type
    with pytest.raises(InvalidHierarchyError) as exc_info3:
        service.add_reply(
            comment_id=r1.id,
            author_id="charlie",
            content="Nested",
            target_type="reply",
        )
    assert "Cannot reply to reply ID" in str(exc_info3.value)


def test_state_isolation_across_posts(service: CommentService) -> None:
    """Ensure comments and replies on one post are completely isolated from another."""
    c_a1 = service.add_comment("post_A", "alice", "Discussion A1")
    c_a2 = service.add_comment("post_A", "bob", "Discussion A2")
    service.add_reply(comment_id=c_a1.id, author_id="charlie", content="Reply to A1")

    c_b1 = service.add_comment("post_B", "david", "Discussion B1")

    post_a_thread = service.get_comments_for_post("post_A")
    post_b_thread = service.get_comments_for_post("post_B")

    assert len(post_a_thread) == 2
    assert [c.id for c in post_a_thread] == [c_a1.id, c_a2.id]
    assert len(post_a_thread[0].replies) == 1
    assert post_a_thread[0].replies[0].content == "Reply to A1"

    assert len(post_b_thread) == 1
    assert [c.id for c in post_b_thread] == [c_b1.id]
    assert len(post_b_thread[0].replies) == 0


def test_preserving_creation_order(service: CommentService) -> None:
    """Verify comments and replies retain exact FIFO insertion order."""
    post_id = "chronology_post"
    for i in range(1, 6):
        service.add_comment(post_id, f"author_{i}", f"Comment #{i}")

    thread = service.get_comments_for_post(post_id)
    assert [c.id for c in thread] == [1, 2, 3, 4, 5]
    assert [c.content for c in thread] == [f"Comment #{i}" for i in range(1, 6)]

    # Add 5 replies to comment 3
    c3 = thread[2]
    for j in range(1, 6):
        service.add_reply(comment_id=c3.id, author_id=f"replier_{j}", content=f"Sub-reply #{j}")

    retrieved_c3 = service.get_comment(c3.id)
    assert [r.id for r in retrieved_c3.replies] == [1, 2, 3, 4, 5]
    assert [r.content for r in retrieved_c3.replies] == [f"Sub-reply #{j}" for j in range(1, 6)]


def test_post_id_relationship_validation(service: CommentService) -> None:
    """Ensure verifying post_id when adding reply prevents cross-post misassignment."""
    c = service.add_comment("post_correct", "alice", "Hello")

    # Mismatched post_id
    with pytest.raises(ValidationError) as exc_info:
        service.add_reply(
            comment_id=c.id,
            author_id="bob",
            content="Reply",
            post_id="post_wrong",
        )
    assert "belongs to post 'post_correct', not 'post_wrong'" in str(exc_info.value)

    # Correct post_id passes
    reply = service.add_reply(
        comment_id=c.id,
        author_id="bob",
        content="Reply",
        post_id="post_correct",
    )
    assert reply.post_id == "post_correct"


def test_nonexistent_resource_queries(service: CommentService) -> None:
    """Verify appropriate exceptions and empty responses for unknown IDs."""
    with pytest.raises(CommentNotFoundError):
        service.get_comment(999)

    with pytest.raises(CommentNotFoundError):
        service.get_replies_for_comment(999)

    with pytest.raises(ResourceNotFoundError):
        service.get_reply(999)

    # Empty post returns empty list
    assert service.get_comments_for_post("uncommented_post") == []
    assert service.get_thread("uncommented_post") == []


def test_platform_statistics_and_clear(service: CommentService) -> None:
    """Verify aggregate metrics tracking and clear functionality."""
    assert service.get_stats() == {"total_posts": 0, "total_comments": 0, "total_replies": 0}

    c1 = service.add_comment("p1", "u1", "C1")
    c2 = service.add_comment("p2", "u2", "C2")
    service.add_reply(c1.id, "u3", "R1")

    assert service.get_stats() == {"total_posts": 2, "total_comments": 2, "total_replies": 1}

    service.clear()
    assert service.get_stats() == {"total_posts": 0, "total_comments": 0, "total_replies": 0}
