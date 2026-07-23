"""LLM inference for the AMD Vulkan worker, with a CPU fallback.

Models are loaded from the runtime-mounted ``models`` volume instead of being
embedded in the container image.

Supported tasks:
    - summarize   — condense a document into bullet points
    - classify    — categorise text into predefined labels
    - generate    — freeform text completion

To add a new model:
    1. Place the model file in the models/ directory and add to DEFAULT_MODELS.
    2. Add a new prompt/task to PROMPTS if needed.
    3. Call run_inference(text, task, ..., model_name="yourmodel")
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODELS = {
    "tinyllama": MODELS_DIR / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
}


def _detect_provider() -> str:
    provider = os.getenv("LLM_PROVIDER")
    if provider:
        return provider
    if os.getenv("ROCM_VISIBLE_DEVICES"):
        return "rocm"
    if os.getenv("LLAMACPP_VULKAN"):
        return "vulkan"
    if os.getenv("OPENVINO_DEVICE"):
        return "openvino"
    return "cpu"


def _load_model(
    model_name: str = "tinyllama",
    provider: str | None = None,
    gpu_layers: int | None = None,
):
    from llama_cpp import Llama

    try:
        model_file = DEFAULT_MODELS[model_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown LLM model {model_name!r}; choose from {sorted(DEFAULT_MODELS)}"
        ) from exc

    model_path = str(model_file)
    if not model_file.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run: python models/download_model.py"
        )
    provider = provider or _detect_provider()
    if gpu_layers is None:
        if provider == "cuda":
            gpu_layers = int(os.getenv("LLM_GPU_LAYERS", "40"))
        elif provider in {"rocm", "vulkan"}:
            gpu_layers = int(os.getenv("LLM_GPU_LAYERS", "35"))
        else:
            gpu_layers = 0
    logger.info(
        "Loading LLM %r from %s (provider=%s, n_gpu_layers=%s)",
        model_name,
        model_path,
        provider,
        gpu_layers,
    )
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=gpu_layers,
        n_ctx=2048,
        n_batch=512,
        verbose=False,
    )
    logger.info("Model loaded.")
    return llm


_llm_cache: dict[tuple[str, str | None, int | None], Any] = {}


def get_llm(
    model_name: str = "tinyllama",
    provider: str | None = None,
    gpu_layers: int | None = None,
):
    key = (model_name, provider, gpu_layers)
    if key not in _llm_cache:
        _llm_cache[key] = _load_model(model_name, provider, gpu_layers)
    return _llm_cache[key]


PROMPTS = {
    "summarize": (
        "<|system|>You are a precise summarizer. Reply with 3-5 concise bullet points only.</s>"
        "<|user|>Summarize the following text:\n\n{text}</s>"
        "<|assistant|>"
    ),
    "classify": (
        "<|system|>You are a text classifier. Reply with only one label from: "
        "{labels}. No explanation.</s>"
        "<|user|>Classify this text:\n\n{text}</s>"
        "<|assistant|>"
    ),
    "generate": ("<|system|>You are a helpful assistant.</s><|user|>{text}</s><|assistant|>"),
}

DEFAULT_LABELS = ["positive", "negative", "neutral", "technical", "general", "question"]


def run_inference(
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
    model_name: str = "tinyllama",
    provider: str | None = None,
    gpu_layers: int | None = None,
) -> dict[str, Any]:
    if task not in PROMPTS:
        raise ValueError(f"Unknown task {task!r}. Choose from: {list(PROMPTS)}")
    if len(text) > 8000:
        text = text[:8000]
    label_str = ", ".join(labels or DEFAULT_LABELS)
    prompt = PROMPTS[task].format(text=text, labels=label_str)
    t0 = time.perf_counter()
    llm = get_llm(model_name, provider, gpu_layers)
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["</s>", "<|user|>"],
        echo=False,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    generated = output["choices"][0]["text"].strip()
    tokens_used = output["usage"]["completion_tokens"]
    tokens_per_sec = round(tokens_used / max(elapsed_ms / 1000, 0.001), 1)
    return {
        "task": task,
        "output": generated,
        "tokens_generated": tokens_used,
        "tokens_per_second": tokens_per_sec,
        "inference_ms": elapsed_ms,
        "model": model_name,
        "provider": provider or _detect_provider(),
    }


def run_inference_with_progress(
    job_id: str,
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
    progress_callback: Any | None = None,
    model_name: str = "tinyllama",
    provider: str | None = None,
    gpu_layers: int | None = None,
) -> dict[str, Any]:
    if task not in PROMPTS:
        raise ValueError(f"Unknown task {task!r}. Choose from: {list(PROMPTS)}")
    if len(text) > 8000:
        text = text[:8000]
    label_str = ", ".join(labels or DEFAULT_LABELS)
    prompt = PROMPTS[task].format(text=text, labels=label_str)
    t0 = time.perf_counter()
    llm = get_llm(model_name, provider, gpu_layers)
    tokens_generated = 0
    output_parts: list[str] = []
    chunks = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["</s>", "<|user|>"],
        echo=False,
        stream=True,
    )
    for chunk in chunks:
        token = chunk["choices"][0]["text"]
        output_parts.append(token)
        tokens_generated += 1
        if progress_callback:
            percent = min(100, int(100 * tokens_generated / max_tokens))
            progress_callback(job_id, percent)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "task": task,
        "output": "".join(output_parts).strip(),
        "tokens_generated": tokens_generated,
        "inference_ms": elapsed_ms,
        "model": model_name,
        "provider": provider or _detect_provider(),
    }
