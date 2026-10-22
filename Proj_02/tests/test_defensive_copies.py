"""Defensive copy snapshot and state isolation tests for CommentService."""

import pytest

from Proj_02.src.models import Reply
from Proj_02.src.service import CommentService


def test_defensive_copy_on_comment_mutation(service: CommentService) -> None:
    """Ensure mutating properties on a returned Comment does not affect service state."""
    created = service.add_comment("post_sec", "alice", "Original comment")
    assert created.content == "Original comment"

    # Attempt external mutation
    created.content = "Mutated comment"
    created.author_id = "attacker"
    created.post_id = "post_hacked"

    # Verify service state is pristine
    retrieved = service.get_comment(created.id)
    assert retrieved.content == "Original comment"
    assert retrieved.author_id == "alice"
    assert retrieved.post_id == "post_sec"


def test_defensive_copy_on_replies_list_mutation(service: CommentService) -> None:
    """Ensure clearing, appending to, or popping from the replies list has zero impact on stored state."""
    comment = service.add_comment("post_sec", "alice", "Discussion")
    reply1 = service.add_reply(comment.id, "bob", "First reply")
    reply2 = service.add_reply(comment.id, "charlie", "Second reply")

    retrieved = service.get_comment(comment.id)
    assert len(retrieved.replies) == 2

    # Malicious clear
    retrieved.replies.clear()
    assert len(service.get_comment(comment.id).replies) == 2

    # Malicious append
    fake_reply = Reply(
        id=9999,
        comment_id=comment.id,
        post_id="post_sec",
        author_id="hacker",
        content="Injected",
        created_at=0.0,
    )
    retrieved.replies.append(fake_reply)
    assert len(service.get_comment(comment.id).replies) == 2

    # Mutating nested reply within retrieved comment
    fresh = service.get_comment(comment.id)
    fresh.replies[0].content = "Defaced reply"
    assert service.get_comment(comment.id).replies[0].content == "First reply"


def test_defensive_copy_on_thread_list_mutation(service: CommentService) -> None:
    """Ensure modifying the list returned by get_comments_for_post does not mutate internal collections."""
    service.add_comment("post_list", "u1", "Comment 1")
    service.add_comment("post_list", "u2", "Comment 2")

    thread = service.get_comments_for_post("post_list")
    assert len(thread) == 2

    # Mutate the list
    thread.pop()
    thread.clear()

    # Verify service maintains both comments
    fresh_thread = service.get_comments_for_post("post_list")
    assert len(fresh_thread) == 2


def test_defensive_copy_on_get_replies_for_comment(service: CommentService) -> None:
    """Ensure modifying get_replies_for_comment return value leaves service state intact."""
    comment = service.add_comment("p1", "u1", "Parent")
    service.add_reply(comment.id, "u2", "R1")
    service.add_reply(comment.id, "u3", "R2")

    replies = service.get_replies_for_comment(comment.id)
    assert len(replies) == 2

    replies[0].content = "Tampered"
    replies.clear()

    fresh_replies = service.get_replies_for_comment(comment.id)
    assert len(fresh_replies) == 2
    assert fresh_replies[0].content == "R1"
