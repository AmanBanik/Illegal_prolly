"""Multi-threaded concurrency and race condition stress tests for FeatureFlagService."""

import concurrent.futures
import random
import time

from Proj_06.src.models import (
    Operator,
    RolloutConfig,
    RolloutVariant,
    RuleCondition,
    TargetingRule,
    UserContext,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


def test_concurrent_evaluations_during_updates(service: FeatureFlagService) -> None:
    """Verify concurrent evaluations execute cleanly while writers update flag rules and rollouts."""
    flag_key = "concurrent_dynamic_flag"
    service.create_flag(
        key=flag_key,
        name="Concurrent Flag",
        variants=[Variant("v_off"), Variant("v_on"), Variant("v_beta")],
        default_variant="v_off",
        rollout=RolloutConfig([RolloutVariant("v_off", 50.0), RolloutVariant("v_on", 50.0)]),
    )

    num_readers = 25
    num_writers = 5
    iterations = 20
    stop_event = concurrent.futures.thread.threading.Event()

    def reader_worker(worker_id: int) -> int:
        count = 0
        while not stop_event.is_set():
            uid = f"user_{worker_id}_{count}"
            context = UserContext(
                user_id=uid,
                attributes={"role": "tester" if count % 2 == 0 else "guest"},
            )
            res = service.evaluate(flag_key, context)
            assert res.variant_key in ("v_off", "v_on", "v_beta")
            count += 1
            if count >= iterations:
                break
        return count

    def writer_worker(worker_id: int) -> None:
        for i in range(10):
            # Toggle enabled or update rules/rollouts
            service.update_flag(
                flag_key,
                enabled=bool(i % 2 == 0),
                rollout=RolloutConfig(
                    [
                        RolloutVariant("v_off", 30.0 + (i % 20)),
                        RolloutVariant("v_on", 70.0 - (i % 20)),
                    ]
                ),
            )
            time.sleep(0.005)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_readers + num_writers) as executor:
        writer_futures = [executor.submit(writer_worker, i) for i in range(num_writers)]
        reader_futures = [executor.submit(reader_worker, i) for i in range(num_readers)]

        for wf in writer_futures:
            wf.result()

        stop_event.set()
        for rf in reader_futures:
            reads = rf.result()
            assert reads > 0


def test_concurrent_flag_creation(service: FeatureFlagService) -> None:
    """Verify multiple worker threads can concurrently create distinct flags without race conditions."""
    num_threads = 25

    def create_worker(worker_id: int) -> str:
        key = f"flag_thread_{worker_id}"
        service.create_flag(
            key=key,
            name=f"Thread Flag {worker_id}",
            variants=[Variant("v1"), Variant("v2")],
            default_variant="v1",
        )
        return key

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_worker, i) for i in range(num_threads)]
        created_keys = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(created_keys) == num_threads
    assert len(set(created_keys)) == num_threads

    all_flags = service.list_flags()
    assert len(all_flags) == num_threads


def test_concurrent_evaluations_throughput(service: FeatureFlagService) -> None:
    """Stress test high-throughput concurrent evaluations across 5 distinct flags."""
    # Seed 5 flags
    for i in range(5):
        service.create_flag(
            key=f"perf_flag_{i}",
            name=f"Perf Flag {i}",
            variants=[Variant("ctrl"), Variant("treat")],
            default_variant="ctrl",
            rollout=RolloutConfig([RolloutVariant("ctrl", 50.0), RolloutVariant("treat", 50.0)]),
        )

    num_evals = 100

    def eval_worker(worker_id: int) -> None:
        target_flag = f"perf_flag_{worker_id % 5}"
        uid = f"user_{worker_id}"
        res = service.evaluate(target_flag, UserContext(user_id=uid))
        assert res.variant_key in ("ctrl", "treat")

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(eval_worker, i) for i in range(num_evals)]
        for f in concurrent.futures.as_completed(futures):
            f.result()
