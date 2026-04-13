FROM python:3.12-slim AS builder

# Vulkan + cmake build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build build-essential \
    libvulkan1 libvulkan-dev vulkan-tools \
    glslang-tools \
    && rm -rf /var/lib/apt/lists/*

# Install llama-cpp-python with Vulkan backend
ENV CMAKE_ARGS="-DGGML_VULKAN=on"
RUN pip install --no-cache-dir llama-cpp-python==0.3.2

# ── Runtime image ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY requirements.txt .
RUN pip install --no-cache-dir celery[redis]==5.4.0 redis==5.2.0 \
    psycopg2-binary==2.9.10 sqlalchemy==2.0.36

COPY . .

# Download model at build time; skip on failure (CI)
RUN python models/download_model.py || echo "Model download skipped — mount at runtime"
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    LLM_GPU_LAYERS=35

# Needs /dev/dri/renderD129 (AMD) and /dev/kfd (optional ROCm)
ENTRYPOINT ["./entrypoint.sh"]
CMD ["celery", "-A", "worker", "worker", "--queues=llm", "--concurrency=1", "--loglevel=info"]
