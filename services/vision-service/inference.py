"""Vision inference for the Intel iGPU worker, with a CPU fallback.

Models are loaded from the runtime-mounted ``models`` volume instead of being
embedded in the container image.

Supports:
    - Image classification (MobileNetV2, top-5 labels)
    - Object detection (YOLOv8n — single-class bounding boxes)

To add a new model:
    1. Place the model file in the models/ directory and add to DEFAULT_MODELS.
    2. Add a new function (e.g., run_newtask) if needed.
    3. Call run_classification(image_bytes, model_name="yourmodel") or similar.
"""

from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
IMAGENET_LABELS_PATH = MODELS_DIR / "imagenet_labels.txt"

DEFAULT_MODELS = {
    "mobilenetv2": MODELS_DIR / "mobilenetv2.onnx",
    "yolov8n": MODELS_DIR / "yolov8n.onnx",
}


def _provider_candidates() -> list[tuple[str, dict[str, str]]]:
    """Return Intel-first ONNX Runtime provider candidates."""
    providers: list[tuple[str, dict[str, str]]] = []
    openvino_device = os.getenv("OPENVINO_DEVICE", "GPU_FP16")
    providers.append(("OpenVINOExecutionProvider", {"device_type": openvino_device}))
    providers.append(("OpenVINOExecutionProvider", {"device_type": "CPU_FP32"}))
    providers.append(("CPUExecutionProvider", {}))
    return providers


def _build_session(model_name: str) -> ort.InferenceSession:
    try:
        model_path = DEFAULT_MODELS[model_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown vision model {model_name!r}; choose from {sorted(DEFAULT_MODELS)}"
        ) from exc
    if not model_path.exists():
        raise FileNotFoundError(f"Model file missing: {model_path}")
    available = set(ort.get_available_providers())
    logger.info("ONNX Runtime providers available: %s", sorted(available))
    for provider, options in _provider_candidates():
        if provider in available:
            try:
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                sess = ort.InferenceSession(
                    str(model_path),
                    sess_options=sess_options,
                    providers=[(provider, options)] if options else [provider],
                )
                logger.info(
                    "Loaded %s with provider %s options=%s",
                    model_path.name,
                    provider,
                    options,
                )
                return sess
            except Exception as exc:  # noqa: BLE001 - try the next runtime provider
                logger.warning("Provider %s failed: %s — trying next", provider, exc)
    raise RuntimeError(
        f"No valid provider found for {model_path}. Available providers: {sorted(available)}"
    )


def _load_imagenet_labels() -> list[str]:
    if not IMAGENET_LABELS_PATH.exists():
        return [str(i) for i in range(1000)]
    return IMAGENET_LABELS_PATH.read_text().splitlines()


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
    return {
        "top5": top5,
        "inference_ms": elapsed_ms,
        "task": "classification",
        "model": model_name,
    }


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
            {"box": b, "score": s, "class_id": c} for b, s, c in zip(boxes, scores, class_ids)
        ],
        "inference_ms": elapsed_ms,
        "task": "detection",
        "model": model_name,
    }
