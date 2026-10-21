import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, Iterator, List, Optional
from .exceptions import (
    InvalidJobError,
    MemoryBudgetExceededError,
    PipelineClosedError,
    PipelineError,
)
from .memory_manager import MemoryBudgetManager
from .models import ImageData, ImageJob, PipelineConfig, TransformResult
from .transforms import ImageTransform


class PixelFlowPipeline:
    """Production-grade batch image processing pipeline.

    Guarantees:
    - Ordered transformations within each job.
    - Concurrent multi-threaded processing with worker pool limits.
    - Failure isolation: errors in one job do not impact others.
    - Deterministic result ordering: results are yielded in exact input FIFO order.
    - Bounded lazy consumption: streams inputs without full batch materialization.
    - In-flight memory budgeting based on original image size.
    """

    def __init__(
        self,
        transforms: List[ImageTransform],
        config: Optional[PipelineConfig] = None,
    ):
        self._transforms = list(transforms)
        self._config = config or PipelineConfig()
        self._memory_manager = MemoryBudgetManager(self._config.max_memory_bytes)
        self._is_closed = False
        self._executor = ThreadPoolExecutor(
            max_workers=self._config.max_workers,
            thread_name_prefix="PixelFlowWorker",
        )

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def memory_manager(self) -> MemoryBudgetManager:
        return self._memory_manager

    def _execute_job(self, index: int, job: ImageJob) -> TransformResult:
        """Executes all pipeline transformations on a single job sequentially."""
        start_time = time.perf_counter()
        current_image = job.image

        try:
            for transform in self._transforms:
                current_image = transform.apply(current_image)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TransformResult(
                job_id=job.job_id,
                success=True,
                image=current_image,
                execution_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TransformResult(
                job_id=job.job_id,
                success=False,
                image=None,
                error=str(e),
                execution_time_ms=elapsed_ms,
            )

    def process_batch(self, jobs: Iterable[ImageJob]) -> Iterator[TransformResult]:
        """Processes an iterable of ImageJobs lazily with deterministic result ordering.

        Yields:
            TransformResult in the exact FIFO order of the input iterable.
        """
        if self._is_closed:
            raise PipelineClosedError("Cannot process batch on a closed pipeline")

        # Synchronization structures
        lock = threading.Lock()
        condition = threading.Condition(lock)

        completed_results: Dict[int, TransformResult] = {}
        producer_done = False
        producer_error: Optional[Exception] = None
        total_jobs_submitted = 0

        # Bound in-flight jobs to prevent unbounded memory from iterator read-ahead
        in_flight_semaphore = threading.Semaphore(self._config.get_max_in_flight())

        def producer_worker():
            nonlocal producer_done, producer_error, total_jobs_submitted
            try:
                for idx, job in enumerate(jobs):
                    if self._is_closed:
                        break

                    if not isinstance(job, ImageJob):
                        raise InvalidJobError(f"Expected ImageJob, got {type(job)}")

                    # 1. Acquire in-flight worker slot
                    in_flight_semaphore.acquire()

                    # 2. Acquire memory budget for this image
                    image_size = job.image.size_bytes
                    try:
                        self._memory_manager.acquire(image_size)
                    except MemoryBudgetExceededError as mem_err:
                        # Isolate failure: oversized image yields failed result without crashing pipeline
                        in_flight_semaphore.release()
                        with condition:
                            completed_results[idx] = TransformResult(
                                job_id=job.job_id,
                                success=False,
                                error=str(mem_err),
                            )
                            total_jobs_submitted += 1
                            condition.notify_all()
                        continue

                    # 3. Dispatch to thread pool with memory release hook
                    with condition:
                        total_jobs_submitted += 1

                    def make_task(task_idx: int, task_job: ImageJob, mem_size: int):
                        def task_runner():
                            try:
                                res = self._execute_job(task_idx, task_job)
                            finally:
                                self._memory_manager.release(mem_size)

                            with condition:
                                completed_results[task_idx] = res
                                condition.notify_all()

                        return task_runner

                    self._executor.submit(make_task(idx, job, image_size))

            except Exception as ex:
                producer_error = ex
            finally:
                with condition:
                    producer_done = True
                    condition.notify_all()

        # Start producer thread
        producer_thread = threading.Thread(
            target=producer_worker,
            name="PixelFlowProducer",
            daemon=True,
        )
        producer_thread.start()

        # Consumer generator: yields results in strictly increasing index order
        next_yield_index = 0
        while True:
            with condition:
                while next_yield_index not in completed_results:
                    if producer_done and next_yield_index >= total_jobs_submitted:
                        if producer_error:
                            raise producer_error
                        return  # Batch complete

                    condition.wait()

                result = completed_results.pop(next_yield_index)

            # Release in-flight slot for the producer to stream next item
            in_flight_semaphore.release()
            next_yield_index += 1
            yield result

    def close(self) -> None:
        """Shuts down the pipeline and terminates worker thread pool."""
        self._is_closed = True
        self._executor.shutdown(wait=True)

    def __enter__(self) -> "PixelFlowPipeline":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
