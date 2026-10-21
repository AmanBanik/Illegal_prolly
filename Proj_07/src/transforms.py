from abc import ABC, abstractmethod
from typing import Callable, Optional
from .exceptions import TransformError
from .models import ImageData


class ImageTransform(ABC):
    """Abstract base class for all image transformations.

    Transformations must be pure and deterministic: given the same input ImageData,
    they must produce equivalent output ImageData.
    """

    @abstractmethod
    def apply(self, image: ImageData) -> ImageData:
        """Applies transformation and returns a new ImageData instance."""
        pass


class CallableTransform(ImageTransform):
    """Wraps an arbitrary Python callable into an ImageTransform."""

    def __init__(self, name: str, func: Callable[[ImageData], ImageData]):
        self.name = name
        self._func = func

    def apply(self, image: ImageData) -> ImageData:
        try:
            return self._func(image)
        except Exception as e:
            raise TransformError(f"Transform '{self.name}' failed: {e}") from e


class GrayscaleTransform(ImageTransform):
    """Simulates converting image to grayscale and updates metadata."""

    def apply(self, image: ImageData) -> ImageData:
        # Simple simulation: invert or modify byte payload while preserving size
        new_metadata = dict(image.metadata)
        new_metadata["color_space"] = "grayscale"
        new_metadata["transforms_applied"] = new_metadata.get("transforms_applied", []) + ["grayscale"]

        # Byte manipulation simulating luminance calculation
        transformed_bytes = bytes(b ^ 0x10 for b in image.data)
        return ImageData(
            image_id=image.image_id,
            data=transformed_bytes,
            metadata=new_metadata,
        )


class ResizeTransform(ImageTransform):
    """Simulates resizing image dimensions and scaling byte buffer."""

    def __init__(self, scale_factor: float):
        if scale_factor <= 0:
            raise ValueError("scale_factor must be positive")
        self.scale_factor = scale_factor

    def apply(self, image: ImageData) -> ImageData:
        new_metadata = dict(image.metadata)
        orig_width = new_metadata.get("width", 100)
        orig_height = new_metadata.get("height", 100)
        new_metadata["width"] = int(orig_width * self.scale_factor)
        new_metadata["height"] = int(orig_height * self.scale_factor)
        new_metadata["transforms_applied"] = new_metadata.get("transforms_applied", []) + [
            f"resize_{self.scale_factor}"
        ]

        target_len = max(1, int(len(image.data) * self.scale_factor))
        if target_len >= len(image.data):
            # Extend or pad
            new_data = (image.data * (target_len // len(image.data) + 1))[:target_len]
        else:
            new_data = image.data[:target_len]

        return ImageData(
            image_id=image.image_id,
            data=new_data,
            metadata=new_metadata,
        )


class WatermarkTransform(ImageTransform):
    """Applies a watermark text to image metadata and appends signature."""

    def __init__(self, text: str):
        self.text = text

    def apply(self, image: ImageData) -> ImageData:
        new_metadata = dict(image.metadata)
        new_metadata["watermark"] = self.text
        new_metadata["transforms_applied"] = new_metadata.get("transforms_applied", []) + ["watermark"]

        # Append watermark signature bytes
        signature = f" [WM:{self.text}]".encode("utf-8")
        return ImageData(
            image_id=image.image_id,
            data=image.data + signature,
            metadata=new_metadata,
        )
