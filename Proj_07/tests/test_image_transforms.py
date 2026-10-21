import pytest
from Proj_07.src.exceptions import TransformError
from Proj_07.src.models import ImageData
from Proj_07.src.transforms import (
    CallableTransform,
    GrayscaleTransform,
    ResizeTransform,
    WatermarkTransform,
)


def test_grayscale_transform(sample_image):
    t = GrayscaleTransform()
    res = t.apply(sample_image)
    assert res.metadata["color_space"] == "grayscale"
    assert "grayscale" in res.metadata["transforms_applied"]
    assert res.data != sample_image.data
    assert len(res.data) == len(sample_image.data)


def test_resize_transform(sample_image):
    t = ResizeTransform(scale_factor=0.5)
    res = t.apply(sample_image)
    assert res.metadata["width"] == 32
    assert res.metadata["height"] == 32
    assert len(res.data) == len(sample_image.data) // 2


def test_watermark_transform(sample_image):
    t = WatermarkTransform("Confidential")
    res = t.apply(sample_image)
    assert res.metadata["watermark"] == "Confidential"
    assert b"Confidential" in res.data


def test_callable_transform_success(sample_image):
    def invert(img: ImageData) -> ImageData:
        return ImageData(img.image_id, bytes(255 - b for b in img.data), {"inverted": True})

    t = CallableTransform("invert", invert)
    res = t.apply(sample_image)
    assert res.metadata["inverted"] is True


def test_callable_transform_error(sample_image):
    def faulty(_img: ImageData) -> ImageData:
        raise ValueError("Corrupt header")

    t = CallableTransform("faulty", faulty)
    with pytest.raises(TransformError) as exc_info:
        t.apply(sample_image)
    assert "Corrupt header" in str(exc_info.value)


def test_ordered_sequence_execution(sample_image):
    t1 = GrayscaleTransform()
    t2 = ResizeTransform(0.5)
    t3 = WatermarkTransform("Verified")

    out = t3.apply(t2.apply(t1.apply(sample_image)))
    assert out.metadata["transforms_applied"] == ["grayscale", "resize_0.5", "watermark"]
