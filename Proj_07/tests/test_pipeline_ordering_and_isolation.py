import time
import pytest
from Proj_07.src.models import ImageData, ImageJob, PipelineConfig
from Proj_07.src.pipeline import PixelFlowPipeline
from Proj_07.src.transforms import CallableTransform, GrayscaleTransform


def test_deterministic_result_ordering_with_variable_latencies():
    """Verify results are yielded in exact input FIFO order even if later jobs finish earlier."""
    # Variable delay transform: job_0 takes 0.08s, others take 0.01s
    def variable_sleep(img: ImageData) -> ImageData:
        if img.image_id == "job_0":
            time.sleep(0.08)
        else:
            time.sleep(0.01)
        return img

    pipeline = PixelFlowPipeline(
        transforms=[CallableTransform("sleeper", variable_sleep)],
        config=PipelineConfig(max_workers=4, max_memory_bytes=1024 * 1024),
    )

    jobs = [
        ImageJob(f"job_{i}", ImageData(f"job_{i}", b"fake_data", {}))
        for i in range(8)
    ]

    results = list(pipeline.process_batch(jobs))
    pipeline.close()

    assert len(results) == 8
    # Exact deterministic sequence
    for i, res in enumerate(results):
        assert res.job_id == f"job_{i}"
        assert res.success is True


def test_failure_isolation_preserves_pipeline():
    """Ensure a failure in one job does not abort other jobs or crash the pipeline."""
    def fail_on_three(img: ImageData) -> ImageData:
        if img.image_id == "job_2":
            raise ValueError("Corrupt image data at byte 42")
        return img

    pipeline = PixelFlowPipeline(
        transforms=[GrayscaleTransform(), CallableTransform("fail_detector", fail_on_three)],
        config=PipelineConfig(max_workers=3, max_memory_bytes=1024 * 1024),
    )

    jobs = [
        ImageJob(f"job_{i}", ImageData(f"job_{i}", b"data_" + str(i).encode(), {}))
        for i in range(5)
    ]

    results = list(pipeline.process_batch(jobs))
    pipeline.close()

    assert len(results) == 5
    assert [r.job_id for r in results] == [f"job_{i}" for i in range(5)]

    # Jobs 0, 1, 3, 4 succeeded
    assert results[0].success is True
    assert results[1].success is True
    assert results[3].success is True
    assert results[4].success is True

    # Job 2 isolated as failure
    assert results[2].success is False
    assert "Corrupt image data at byte 42" in results[2].error


def test_oversized_image_failure_isolation():
    """An image exceeding the total memory budget is isolated as a failed result without deadlocking."""
    pipeline = PixelFlowPipeline(
        transforms=[GrayscaleTransform()],
        config=PipelineConfig(max_workers=2, max_memory_bytes=1000),  # 1000 bytes budget
    )

    jobs = [
        ImageJob("small_1", ImageData("small_1", b"x" * 200, {})),
        ImageJob("giant_2", ImageData("giant_2", b"x" * 1500, {})),  # Exceeds 1000
        ImageJob("small_3", ImageData("small_3", b"x" * 200, {})),
    ]

    results = list(pipeline.process_batch(jobs))
    pipeline.close()

    assert len(results) == 3
    assert results[0].success is True
    assert results[1].success is False
    assert "exceeds total memory budget" in results[1].error
    assert results[2].success is True


def test_empty_batch(default_pipeline):
    results = list(default_pipeline.process_batch([]))
    assert results == []
