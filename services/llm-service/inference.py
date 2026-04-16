"""
LLM inference engine.
Uses llama-cpp-python compiled with Vulkan support, targeting the AMD WX 3100.
Falls back to CPU if Vulkan is unavailable.

Supported tasks:
  - summarize   — condense a document into bullet points
  - classify    — categorise text into predefined labels
  - generate    — freeform text completion
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL = MODELS_DIR / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# Number of layers to offload to GPU; WX 3100 has 2 GB VRAM
# Q4_K_M of TinyLlama ~700 MB — safe to offload all layers
GPU_LAYERS = int(os.getenv("LLM_GPU_LAYERS", "35"))


def _load_model():
    from llama_cpp import Llama

    model_path = str(DEFAULT_MODEL)
    if not DEFAULT_MODEL.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run: "
            "python models/download_model.py"
        )

    logger.info("Loading LLM from %s (n_gpu_layers=%d)", model_path, GPU_LAYERS)
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=GPU_LAYERS,
        n_ctx=2048,
        n_batch=512,
        verbose=False,
    )
    logger.info("Model loaded.")
    return llm


_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = _load_model()
    return _llm


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
    "generate": (
        "<|system|>You are a helpful assistant.</s>"
        "<|user|>{text}</s>"
        "<|assistant|>"
    ),
}

DEFAULT_LABELS = ["positive", "negative", "neutral", "technical", "general", "question"]


def run_inference(
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
) -> dict[str, Any]:
    if task not in PROMPTS:
        raise ValueError(f"Unknown task {task!r}. Choose from: {list(PROMPTS)}")
    if len(text) > 8000:
        text = text[:8000]

    label_str = ", ".join(labels or DEFAULT_LABELS)
    prompt = PROMPTS[task].format(text=text, labels=label_str)

    t0 = time.perf_counter()
    llm = get_llm()
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
    }


def run_inference_with_progress(
    job_id: str,
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
    progress_callback=None,
) -> dict[str, Any]:
    if task not in PROMPTS:
        raise ValueError(f"Unknown task {task!r}. Choose from: {list(PROMPTS)}")
    if len(text) > 8000:
        text = text[:8000]

    label_str = ", ".join(labels or DEFAULT_LABELS)
    prompt = PROMPTS[task].format(text=text, labels=label_str)

    t0 = time.perf_counter()
    llm = get_llm()
    tokens_generated = 0
    output_text = ""
    def on_token(token):
        nonlocal tokens_generated, output_text
        tokens_generated += 1
        output_text += token
        if progress_callback:
            percent = int(100 * tokens_generated / max_tokens)
            progress_callback(job_id, percent)
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["</s>", "<|user|>"],
        echo=False,
        stream=True,
        callback=on_token,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "task": task,
        "output": output_text,
        "tokens_generated": tokens_generated,
        "inference_ms": elapsed_ms,
    }
