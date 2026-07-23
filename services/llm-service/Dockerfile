FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake glslang-tools glslc libvulkan-dev spirv-headers \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

ENV CMAKE_ARGS="-DGGML_VULKAN=on" \
    FORCE_CMAKE=1

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libvulkan1 mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade \
    pip==26.1.2 setuptools==83.0.0

WORKDIR /app

COPY requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
RUN python -c "import llama_cpp, redis, sqlalchemy"

COPY . .

# Models are runtime data mounted through the models volume. Set
# LLM_BOOTSTRAP_MODELS=1 to download them deliberately at startup.
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    LLAMACPP_VULKAN=1 \
    LLM_GPU_LAYERS=35

# Needs /dev/dri/renderD129 (AMD) and /dev/kfd (optional ROCm)
ENTRYPOINT ["./entrypoint.sh"]
CMD ["celery", "-A", "worker", "worker", "--queues=llm", "--concurrency=1", "--loglevel=info"]
