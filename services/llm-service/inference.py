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
def get_llm():

# --- Multi-model and multi-provider support ---
DEFAULT_MODELS = {
    "tinyllama": MODELS_DIR / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    # Add more models here
    # "llama2-7b": MODELS_DIR / "llama-2-7b.Q4_K_M.gguf",
}

def _detect_provider():
    # Try to detect the best provider based on environment or node labels
    # Priority: NVIDIA (CUDA), AMD (ROCm/Vulkan), Intel (OpenVINO), CPU
    provider = os.getenv("LLM_PROVIDER")
    if provider:
        return provider
    # Fallback: try to detect from environment
    if os.getenv("NVIDIA_VISIBLE_DEVICES"):
        return "cuda"
    if os.getenv("ROCM_VISIBLE_DEVICES"):
        return "rocm"
    if os.getenv("LLAMACPP_VULKAN"):
        return "vulkan"
    if os.getenv("OPENVINO_DEVICE"):
        return "openvino"
    return "cpu"

def _load_model(model_name="tinyllama", provider=None, gpu_layers=None):
    from llama_cpp import Llama
    model_path = str(DEFAULT_MODELS[model_name])
    if not DEFAULT_MODELS[model_name].exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run: "
            "python models/download_model.py"
        )
    provider = provider or _detect_provider()
    if gpu_layers is None:
        # Set sensible defaults based on provider
        if provider == "cuda":
            gpu_layers = int(os.getenv("LLM_GPU_LAYERS", "40"))
        elif provider == "rocm" or provider == "vulkan":
            gpu_layers = int(os.getenv("LLM_GPU_LAYERS", "35"))
        else:
            gpu_layers = 0
    logger.info(f"Loading LLM '{model_name}' from {model_path} (provider={provider}, n_gpu_layers={gpu_layers})")
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=gpu_layers,
        n_ctx=2048,
        n_batch=512,
        verbose=False,
    )
    logger.info("Model loaded.")
    return llm

# Cache for loaded models by (model_name, provider)
_llm_cache = {}

def get_llm(model_name="tinyllama", provider=None, gpu_layers=None):
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
    "generate": (
        "<|system|>You are a helpful assistant.</s>"
        "<|user|>{text}</s>"
        "<|assistant|>"
    ),
}

DEFAULT_LABELS = ["positive", "negative", "neutral", "technical", "general", "question"]



# --- Generic inference function supporting multiple models/providers ---
def run_inference(
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
    model_name: str = "tinyllama",
    provider: str = None,
    gpu_layers: int = None,
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



# --- Generic inference with progress (for jobs) ---
def run_inference_with_progress(
    job_id: str,
    text: str,
    task: str = "generate",
    labels: list[str] | None = None,
    max_tokens: int = 256,
    temperature: float = 0.3,
    progress_callback=None,
    model_name: str = "tinyllama",
    provider: str = None,
    gpu_layers: int = None,
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
        "model": model_name,
        "provider": provider or _detect_provider(),
    }

# --- TEMPLATE: Add new model/task here ---
# To add a new model:
# 1. Place the model file in the models/ directory and add to DEFAULT_MODELS.
# 2. Add a new prompt/task to PROMPTS if needed.
# 3. Call run_inference(text, task, ..., model_name="yourmodel")
