import concurrent.futures
import pytest
from Proj_10.src.checker import RuleBasedContentChecker
from Proj_10.src.exceptions import ContentRejectedError, UserBlockedError
from Proj_10.src.service import ReviewDesk


def test_concurrent_comment_creation_monotonic_ids():
    """Verify that under concurrent load, comment IDs are strictly monotonic and unique."""
    checker = RuleBasedContentChecker()
    service = ReviewDesk(checker=checker, max_strikes=5)
    num_threads = 30

    def create_task(i: int):
        return service.create_comment(
            post_id=f"post_{i % 5}",
            user_id=f"user_{i}",
            content=f"Concurrent message number {i}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_task, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads
    ids = sorted(r.id for r in results)
    assert ids == list(range(1, num_threads + 1))


def test_concurrent_violations_atomic_strike_accumulation():
    """Verify that multiple concurrent violations for a single user atomically accumulate

    strikes and immediately block upon reaching the threshold.
    """
    checker = RuleBasedContentChecker(banned_words=["spam"])
    max_strikes = 3
    service = ReviewDesk(checker=checker, max_strikes=max_strikes)
    num_threads = 20

    rejections = 0
    blocked_rejections = 0

    def spam_task(i: int):
        return service.create_comment(
            post_id="post_concurrency",
            user_id="spammer_target",
            content=f"Unsolicited spam message {i}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(spam_task, i) for i in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except ContentRejectedError:
                rejections += 1
            except UserBlockedError:
                blocked_rejections += 1

    total_handled = rejections + blocked_rejections
    assert total_handled == num_threads

    user_state = service.get_user_state("spammer_target")
    assert user_state.is_blocked is True
    assert user_state.strikes == max_strikes
    assert rejections == max_strikes
    assert blocked_rejections == num_threads - max_strikes


def test_concurrent_edits_on_same_comment():
    """Verify that concurrent edits on a single comment execute safely without race conditions."""
    checker = RuleBasedContentChecker()
    service = ReviewDesk(checker=checker)
    comment = service.create_comment("post_1", "user_editor", "Initial content")

    num_threads = 15

    def edit_task(i: int):
        return service.edit_comment(
            comment_id=comment.id,
            user_id="user_editor",
            new_content=f"Revision {i}",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(edit_task, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads
    final_comment = service.get_comment(comment.id)
    assert final_comment.is_edited is True
    assert final_comment.content.startswith("Revision ")
