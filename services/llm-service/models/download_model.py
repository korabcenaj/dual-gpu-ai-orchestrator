#!/usr/bin/env python3
"""
Download the TinyLlama GGUF model from HuggingFace.
Model: TinyLlama-1.1B-Chat-v1.0 Q4_K_M (~700 MB)
"""
import os
import tempfile
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent
MODELS_DIR.mkdir(exist_ok=True)

MODEL_URL = os.getenv(
    "MODEL_URL",
    "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/"
    "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
)
MODEL_PATH = MODELS_DIR / os.getenv(
    "MODEL_FILENAME", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
)


def show_progress(count, block_size, total_size):
    pct = count * block_size * 100 // total_size if total_size > 0 else 0
    mb = count * block_size / 1_048_576
    print(f"\r  {pct:3d}%  {mb:.1f} MB downloaded", end="", flush=True)


def main():
    if MODEL_PATH.exists():
        print(f"Model already present: {MODEL_PATH}")
        return
    print(f"Downloading TinyLlama Q4_K_M (~700 MB) to {MODEL_PATH} ...")
    with tempfile.NamedTemporaryFile(delete=False, dir=MODELS_DIR) as tmp_file:
        tmp_path = Path(tmp_file.name)
    try:
        urllib.request.urlretrieve(MODEL_URL, tmp_path, reporthook=show_progress)
        tmp_path.replace(MODEL_PATH)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    print(f"\nSaved: {MODEL_PATH}  ({MODEL_PATH.stat().st_size // 1_048_576} MB)")


if __name__ == "__main__":
    main()
