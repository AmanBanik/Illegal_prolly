import concurrent.futures
import pytest
from Proj_03.src.exceptions import CodeAlreadyExistsError
from Proj_03.src.models import CreateLinkRequest


def test_concurrent_hit_counting_exact_increments(service):
    """Verify that under high concurrent traffic, all hit count increments are atomically preserved."""
    meta = service.create_short_link(CreateLinkRequest("https://high-traffic.com", "user_1"))
    short_code = meta.short_code
    num_hits = 60

    def record_hit(_):
        return service.get_destination_and_record_hit(short_code)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(record_hit, i) for i in range(num_hits)]
        for f in concurrent.futures.as_completed(futures):
            assert f.result() == "https://high-traffic.com"

    # Verify exact atomic hit count
    final_meta = service.get_link_metadata(short_code)
    assert final_meta.hit_count == num_hits, f"Expected {num_hits} hits, got {final_meta.hit_count}"


def test_concurrent_link_creation_uniqueness(service):
    """Verify concurrent link generation creates distinct codes without collisions."""
    num_links = 25

    def create_link(idx: int):
        req = CreateLinkRequest(f"https://example.com/page/{idx}", f"user_{idx}")
        return service.create_short_link(req)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(create_link, i) for i in range(num_links)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    codes = [r.short_code for r in results]
    assert len(codes) == num_links
    assert len(set(codes)) == num_links  # All unique


def test_concurrent_custom_code_race_single_winner(service):
    """Verify that when multiple threads attempt to claim the same custom code, exactly one wins."""
    custom_code = "limited_offer_2026"
    num_threads = 15
    success_count = 0
    conflict_count = 0

    def claim_code(thread_id: int):
        req = CreateLinkRequest(
            original_url=f"https://brand.com/{thread_id}",
            user_id=f"merchant_{thread_id}",
            custom_code=custom_code,
        )
        return service.create_short_link(req)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(claim_code, i): i for i in range(num_threads)}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
                success_count += 1
            except CodeAlreadyExistsError:
                conflict_count += 1

    assert success_count == 1, f"Expected exactly 1 winner, got {success_count}"
    assert conflict_count == num_threads - 1, f"Expected {num_threads - 1} conflicts, got {conflict_count}"
