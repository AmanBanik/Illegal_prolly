import time
import pytest
from Proj_07.src.models import ImageData, ImageJob, PipelineConfig
from Proj_07.src.pipeline import PixelFlowPipeline
from Proj_07.src.transforms import CallableTransform, GrayscaleTransform


def test_concurrent_memory_budget_is_strictly_enforced():
    """Verify that under concurrent load, in-flight memory never exceeds the defined budget."""
    job_size = 50 * 1024  # 50 KB
    max_memory = 150 * 1024  # 150 KB (at most 3 jobs can be in flight simultaneously)
    num_jobs = 15

    def slow_transform(img: ImageData) -> ImageData:
        time.sleep(0.02)
        return img

    pipeline = PixelFlowPipeline(
        transforms=[GrayscaleTransform(), CallableTransform("slow", slow_transform)],
        config=PipelineConfig(
            max_workers=6,
            max_memory_bytes=max_memory,
        ),
    )

    jobs = [
        ImageJob(f"job_{i}", ImageData(f"job_{i}", b"A" * job_size, {}))
        for i in range(num_jobs)
    ]

    results = list(pipeline.process_batch(jobs))

    # Invariants
    assert len(results) == num_jobs
    assert pipeline.memory_manager.peak_memory_bytes <= max_memory
    assert pipeline.memory_manager.current_memory_bytes == 0  # All memory returned
    pipeline.close()


def test_bounded_lazy_iteration_read_ahead():
    """Verify pipeline does not materialize the entire iterator ahead of time."""
    consumed_count = 0

    def infinite_job_generator():
        nonlocal consumed_count
        i = 0
        while True:
            consumed_count += 1
            yield ImageJob(f"job_{i}", ImageData(f"job_{i}", b"payload", {}))
            i += 1

    pipeline = PixelFlowPipeline(
        transforms=[GrayscaleTransform()],
        config=PipelineConfig(max_workers=2, max_in_flight_jobs=4),
    )

    # Read only 3 items from output
    iterator = pipeline.process_batch(infinite_job_generator())
    received = []
    for _ in range(3):
        received.append(next(iterator))

    pipeline.close()

    assert len(received) == 3
    # Producer should only have read ahead up to max_in_flight + small buffer, nowhere near 1000
    assert consumed_count <= 10


def test_context_manager_lifecycle():
    with PixelFlowPipeline(
        transforms=[GrayscaleTransform()],
        config=PipelineConfig(max_workers=2),
    ) as pipeline:
        jobs = [ImageJob("j1", ImageData("j1", b"data", {}))]
        res = list(pipeline.process_batch(jobs))
        assert len(res) == 1
        assert res[0].success is True

    assert pipeline._is_closed is True
