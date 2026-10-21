class PipelineError(Exception):
    """Base exception for all image transform pipeline errors."""
    pass


class TransformError(PipelineError):
    """Raised when an individual transformation step encounters an error."""
    pass


class MemoryBudgetExceededError(PipelineError):
    """Raised when an individual image exceeds the total pipeline memory budget."""
    pass


class PipelineClosedError(PipelineError):
    """Raised when operations are attempted on a terminated pipeline."""
    pass


class InvalidJobError(PipelineError):
    """Raised when input job or image payload is malformed."""
    pass
