"""Download the runtime model artifacts needed by the vision service.

MobileNet has a configured public source. Object detection is optional and
requires an operator-provided ``YOLO_ONNX_URL`` so the runtime image does not
pull PyTorch and CUDA packages merely to export a model.
"""

import os
import tempfile
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent
MODELS_DIR.mkdir(exist_ok=True)

MOBILENET_URL = (
    "https://github.com/onnx/models/raw/main/validated/vision/classification/"
    "mobilenet/model/mobilenetv2-12.onnx"
)
YOLO_ONNX_URL = os.getenv("YOLO_ONNX_URL")
MOBILENET_PATH = MODELS_DIR / "mobilenetv2.onnx"
YOLO_ONNX_PATH = MODELS_DIR / "yolov8n.onnx"

IMAGENET_LABELS_URL = "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  {dest.name} already exists, skipping.")
        return
    print(f"  Downloading {dest.name} ...")
    with tempfile.NamedTemporaryFile(delete=False, dir=dest.parent) as tmp_file:
        tmp_path = Path(tmp_file.name)
    try:
        urllib.request.urlretrieve(url, tmp_path)
        tmp_path.replace(dest)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    print(f"  Saved to {dest}")


def download_yolo_onnx() -> None:
    if YOLO_ONNX_PATH.exists():
        print(f"  {YOLO_ONNX_PATH.name} already exists, skipping.")
        return

    if not YOLO_ONNX_URL:
        print("  YOLO_ONNX_URL is not set; detection model bootstrap skipped.")
        return

    download(YOLO_ONNX_URL, YOLO_ONNX_PATH)


def main():
    download(MOBILENET_URL, MOBILENET_PATH)
    download_yolo_onnx()

    print("Downloading ImageNet labels ...")
    download(IMAGENET_LABELS_URL, MODELS_DIR / "imagenet_labels.txt")
    print("Done.")


if __name__ == "__main__":
    main()
