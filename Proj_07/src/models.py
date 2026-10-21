from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ImageData:
    """Represents in-memory image binary and associated metadata."""
    image_id: str
    data: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_bytes(self) -> int:
        """Returns original payload size in bytes used for memory budgeting."""
        return len(self.data)


@dataclass(frozen=True)
class ImageJob:
    """Represents a job submitted to the transformation pipeline."""
    job_id: str
    image: ImageData


@dataclass(frozen=True)
class TransformResult:
    """Result of processing an ImageJob through the pipeline."""
    job_id: str
    success: bool
    image: Optional[ImageData] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration governing worker concurrency and in-flight memory budgets."""
    max_workers: int = 4
    max_memory_bytes: int = 50 * 1024 * 1024  # 50 MB default
    max_in_flight_jobs: Optional[int] = None   # Defaults to 2 * max_workers if None

    def get_max_in_flight(self) -> int:
        if self.max_in_flight_jobs is not None and self.max_in_flight_jobs > 0:
            return self.max_in_flight_jobs
        return max(4, self.max_workers * 2)
