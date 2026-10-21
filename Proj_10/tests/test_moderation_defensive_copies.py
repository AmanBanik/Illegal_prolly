import pytest


def test_comment_defensive_copy_isolation(service):
    comment = service.create_comment("post_1", "user_alice", "Original immutable content")

    # Attempting to mutate dataclass fields or returned structures
    # Even if caller gets a copy, altering it should never change internal store
    fetched1 = service.get_comment(comment.id)
    assert fetched1.content == "Original immutable content"

    # Verify list defensive copies
    comments_list = service.list_comments("post_1")
    comments_list.clear()  # Caller clears their list

    # Internal list should still have the comment
    assert len(service.list_comments("post_1")) == 1


def test_user_state_defensive_copy_isolation(service):
    state = service.get_user_state("user_alice")
    assert state.strikes == 0
    assert not state.is_blocked

    # Verify that calling get_user_state returns fresh snapshots
    state2 = service.get_user_state("user_alice")
    assert state == state2
    assert state is not state2  # Distinct object instances
