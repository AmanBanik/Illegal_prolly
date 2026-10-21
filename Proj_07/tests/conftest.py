import sys
from pathlib import Path
import pytest

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from Proj_07.src.models import ImageData, ImageJob, PipelineConfig
from Proj_07.src.pipeline import PixelFlowPipeline
from Proj_07.src.transforms import GrayscaleTransform, ResizeTransform, WatermarkTransform


@pytest.fixture
def sample_image():
    return ImageData(
        image_id="img_001",
        data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024,  # 1 KB dummy PNG
        metadata={"width": 64, "height": 64, "format": "png"},
    )


@pytest.fixture
def standard_transforms():
    return [
        GrayscaleTransform(),
        ResizeTransform(scale_factor=0.5),
        WatermarkTransform(text="PixelFlow"),
    ]


@pytest.fixture
def default_pipeline(standard_transforms):
    pipeline = PixelFlowPipeline(
        transforms=standard_transforms,
        config=PipelineConfig(max_workers=4, max_memory_bytes=10 * 1024 * 1024),
    )
    yield pipeline
    pipeline.close()
