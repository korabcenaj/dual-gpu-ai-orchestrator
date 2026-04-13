#!/usr/bin/env python3
"""
Download or export the models needed by the vision service.

The service prefers prebuilt ONNX artifacts when available. If a YOLO ONNX
artifact is not configured, it downloads the PyTorch checkpoint and exports it
to ONNX locally so the stack can bootstrap end-to-end without manual prep.
"""
import os
import shutil
import tempfile
from pathlib import Path
import urllib.request

MODELS_DIR = Path(__file__).parent
MODELS_DIR.mkdir(exist_ok=True)

MOBILENET_URL = (
    "https://github.com/onnx/models/raw/main/validated/vision/classification/"
    "mobilenet/model/mobilenetv2-12.onnx"
)
YOLO_PT_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
YOLO_ONNX_URL = os.getenv("YOLO_ONNX_URL")
MOBILENET_PATH = MODELS_DIR / "mobilenetv2.onnx"
YOLO_PT_PATH = MODELS_DIR / "yolov8n.pt"
YOLO_ONNX_PATH = MODELS_DIR / "yolov8n.onnx"

IMAGENET_LABELS_URL = (
    "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
)


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


def export_yolo_to_onnx() -> None:
    if YOLO_ONNX_PATH.exists():
        print(f"  {YOLO_ONNX_PATH.name} already exists, skipping export.")
        return

    if YOLO_ONNX_URL:
        print("  Trying direct YOLO ONNX download ...")
        try:
            download(YOLO_ONNX_URL, YOLO_ONNX_PATH)
            return
        except Exception as exc:
            print(f"  Direct YOLO ONNX download failed: {exc}")

    download(YOLO_PT_URL, YOLO_PT_PATH)
    print("  Exporting YOLOv8n to ONNX ...")
    from ultralytics import YOLO

    model = YOLO(str(YOLO_PT_PATH))
    exported_path = Path(
        model.export(format="onnx", imgsz=640, opset=12, simplify=False, dynamic=False)
    )
    if exported_path != YOLO_ONNX_PATH:
        shutil.move(str(exported_path), YOLO_ONNX_PATH)
    print(f"  Saved to {YOLO_ONNX_PATH}")


def main():
    download(MOBILENET_URL, MOBILENET_PATH)
    export_yolo_to_onnx()

    print("Downloading ImageNet labels ...")
    download(IMAGENET_LABELS_URL, MODELS_DIR / "imagenet_labels.txt")
    print("Done.")


if __name__ == "__main__":
    main()
