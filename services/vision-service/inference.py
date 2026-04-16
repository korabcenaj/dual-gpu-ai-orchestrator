"""
Vision inference engine.
Uses ONNX Runtime with the OpenVINO Execution Provider targeting the Intel HD 530 iGPU.
Falls back to CPU if the GPU device is unavailable.

Supports:
  - Image classification (MobileNetV2, top-5 labels)
  - Object detection (YOLOv8n — single-class bounding boxes)
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image
import io

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
IMAGENET_LABELS_PATH = MODELS_DIR / "imagenet_labels.txt"

# --- Multi-model and multi-provider support ---
DEFAULT_MODELS = {
    "mobilenetv2": MODELS_DIR / "mobilenetv2.onnx",
    "yolov8n": MODELS_DIR / "yolov8n.onnx",
    # Add more models here
    # "resnet50": MODELS_DIR / "resnet50.onnx",
}

def _detect_providers():
    # Try to detect the best providers based on environment or node labels
    # Priority: NVIDIA (CUDA), AMD (ROCm/Vulkan), Intel (OpenVINO), CPU
    providers = []
    if os.getenv("NVIDIA_VISIBLE_DEVICES"):
        providers.append(("CUDAExecutionProvider", {}))
    if os.getenv("ROCM_VISIBLE_DEVICES"):
        providers.append(("ROCMExecutionProvider", {}))
    if os.getenv("OPENVINO_DEVICE") or True:  # Always try OpenVINO for Intel
        providers.append(("OpenVINOExecutionProvider", {"device_type": os.getenv("OPENVINO_DEVICE", "GPU_FP16")}))
        providers.append(("OpenVINOExecutionProvider", {"device_type": "CPU_FP32"}))
    providers.append(("CPUExecutionProvider", {}))
    return providers



def _build_session(model_name: str) -> ort.InferenceSession:
    model_path = DEFAULT_MODELS[model_name]
    if not model_path.exists():
        raise FileNotFoundError(f"Model file missing: {model_path}")
    available = {p for p in ort.get_available_providers()}
    logger.info("ONNX Runtime providers available: %s", sorted(available))
    for provider, opts in _detect_providers():
        if provider in available or provider == "CPUExecutionProvider":
            try:
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                sess = ort.InferenceSession(
                    str(model_path),
                    sess_options=sess_options,
                    providers=[(provider, opts)] if opts else [provider],
                )
                logger.info("Loaded %s with provider %s opts=%s", model_path.name, provider, opts)
                return sess
            except Exception as exc:
                logger.warning("Provider %s failed: %s — trying next", provider, exc)
    raise RuntimeError(
        f"No valid provider found for {model_path}. "
        f"Available providers: {sorted(available)}"
    )


def _load_imagenet_labels() -> list[str]:
    if not IMAGENET_LABELS_PATH.exists():
        return [str(i) for i in range(1000)]
    return IMAGENET_LABELS_PATH.read_text().splitlines()


def run_classification(image_bytes: bytes) -> dict[str, Any]:
def run_detection(image_bytes: bytes) -> dict[str, Any]:

# --- Generic inference functions supporting multiple models/providers ---
def run_classification(image_bytes: bytes, model_name: str = "mobilenetv2") -> dict[str, Any]:
    t0 = time.perf_counter()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    arr = arr.transpose(2, 0, 1)[np.newaxis]  # NCHW
    sess = _build_session(model_name)
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: arr})
    logits = outputs[0][0]
    probs = np.exp(logits) / np.exp(logits).sum()
    labels = _load_imagenet_labels()
    top5_idx = probs.argsort()[-5:][::-1]
    top5 = [
        {"label": labels[i] if i < len(labels) else str(i), "score": float(probs[i])}
        for i in top5_idx
    ]
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {"top5": top5, "inference_ms": elapsed_ms, "task": "classification", "model": model_name}

def run_detection(image_bytes: bytes, model_name: str = "yolov8n") -> dict[str, Any]:
    t0 = time.perf_counter()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    orig_w, orig_h = img.size
    resized = img.resize((640, 640))
    arr = np.array(resized, dtype=np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[np.newaxis]  # NCHW
    sess = _build_session(model_name)
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: arr})
    preds = outputs[0][0].T  # [8400, 84]
    boxes, scores, class_ids = [], [], []
    for det in preds:
        cx, cy, w, h = det[:4]
        cls_scores = det[4:]
        class_id = int(cls_scores.argmax())
        score = float(cls_scores[class_id])
        if score < 0.25:
            continue
        x1 = int((cx - w / 2) * orig_w / 640)
        y1 = int((cy - h / 2) * orig_h / 640)
        x2 = int((cx + w / 2) * orig_w / 640)
        y2 = int((cy + h / 2) * orig_h / 640)
        boxes.append([x1, y1, x2, y2])
        scores.append(score)
        class_ids.append(class_id)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "detections": [
            {"box": b, "score": s, "class_id": c}
            for b, s, c in zip(boxes, scores, class_ids)
        ],
        "inference_ms": elapsed_ms,
        "task": "detection",
        "model": model_name,
    }

# --- TEMPLATE: Add new model/task here ---
# To add a new model:
# 1. Place the model file in the models/ directory and add to DEFAULT_MODELS.
# 2. Add a new function (e.g., run_newtask) if needed.
# 3. Call run_classification(image_bytes, model_name="yourmodel") or similar.
