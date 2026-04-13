FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download model at build time; skip on failure (CI)
RUN python models/download_model.py || echo "Model download skipped — mount at runtime"
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    LLM_GPU_LAYERS=35

# Needs /dev/dri/renderD129 (AMD) and /dev/kfd (optional ROCm)
ENTRYPOINT ["./entrypoint.sh"]
CMD ["celery", "-A", "worker", "worker", "--queues=llm", "--concurrency=1", "--loglevel=info"]
