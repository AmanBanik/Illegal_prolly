"""Multi-threaded concurrency and race condition stress tests for CommentService."""

import concurrent.futures
import random
from typing import List

from Proj_02.src.models import Comment, Reply
from Proj_02.src.service import CommentService


def test_concurrent_comment_additions_single_post(service: CommentService) -> None:
    """Verify that multiple concurrent threads adding comments to a post generate unique sequential IDs."""
    num_threads = 25
    post_id = "concurrent_post"

    def worker(worker_id: int) -> Comment:
        return service.add_comment(
            post_id=post_id,
            author_id=f"user_{worker_id}",
            content=f"Concurrent message {worker_id}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        results: List[Comment] = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Validate unique IDs
    assert len(results) == num_threads
    comment_ids = {c.id for c in results}
    assert len(comment_ids) == num_threads
    assert comment_ids == set(range(1, num_threads + 1))

    # Validate post comments in service
    thread = service.get_comments_for_post(post_id)
    assert len(thread) == num_threads
    thread_ids = [c.id for c in thread]
    assert len(set(thread_ids)) == num_threads


def test_concurrent_reply_additions_single_comment(service: CommentService) -> None:
    """Verify multiple concurrent threads adding replies to a comment generate unique sequential reply IDs."""
    comment = service.add_comment("shared_post", "author_parent", "Parent thread")
    num_replies = 25

    def reply_worker(worker_id: int) -> Reply:
        return service.add_reply(
            comment_id=comment.id,
            author_id=f"replier_{worker_id}",
            content=f"Reply text {worker_id}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_replies) as executor:
        futures = [executor.submit(reply_worker, i) for i in range(num_replies)]
        replies: List[Reply] = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Validate unique reply IDs
    assert len(replies) == num_replies
    reply_ids = {r.id for r in replies}
    assert len(reply_ids) == num_replies
    assert reply_ids == set(range(1, num_replies + 1))

    # Validate parent comment contains all replies
    updated_comment = service.get_comment(comment.id)
    assert len(updated_comment.replies) == num_replies
    assert {r.id for r in updated_comment.replies} == reply_ids


def test_concurrent_multi_post_isolation(service: CommentService) -> None:
    """Verify concurrent operations across multiple posts maintain complete state isolation."""
    num_posts = 10
    comments_per_post = 5
    total_expected_comments = num_posts * comments_per_post

    def worker(post_idx: int, comment_idx: int) -> Comment:
        post_id = f"post_{post_idx}"
        return service.add_comment(
            post_id=post_id,
            author_id=f"user_{post_idx}_{comment_idx}",
            content=f"Comment {comment_idx} on post {post_idx}",
        )

    tasks = [(p, c) for p in range(num_posts) for c in range(comments_per_post)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker, p, c) for p, c in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == total_expected_comments
    assert len({c.id for c in results}) == total_expected_comments

    # Check isolation for each post
    for p in range(num_posts):
        post_id = f"post_{p}"
        comments = service.get_comments_for_post(post_id)
        assert len(comments) == comments_per_post
        for c in comments:
            assert c.post_id == post_id


def test_concurrent_mixed_traffic_stress(service: CommentService) -> None:
    """Stress test service with interleaved reads, comment creations, and reply additions."""
    # Seed initial comment
    seed = service.add_comment("post_main", "root", "Root discussion")

    total_ops = 60
    created_comment_ids = [seed.id]
    lock = concurrent.futures.thread.threading.Lock()

    def traffic_worker(op_id: int) -> None:
        action = op_id % 4
        if action == 0:
            # Add new comment
            c = service.add_comment("post_main", f"user_{op_id}", f"Comment {op_id}")
            with lock:
                created_comment_ids.append(c.id)
        elif action == 1:
            # Add reply to a known comment
            with lock:
                target_id = random.choice(created_comment_ids)
            service.add_reply(target_id, f"replier_{op_id}", f"Reply {op_id}")
        elif action == 2:
            # Read thread
            service.get_comments_for_post("post_main")
        else:
            # Query stats
            service.get_stats()

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(traffic_worker, i) for i in range(total_ops)]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # Should complete without error

    stats = service.get_stats()
    assert stats["total_posts"] == 1
    assert stats["total_comments"] == len(created_comment_ids)
    assert stats["total_replies"] >= 0
