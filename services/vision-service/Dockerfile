FROM python:3.14-slim

# OpenVINO OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade \
    pip==26.1.2 setuptools==83.0.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import onnxruntime, PIL, redis, sqlalchemy"

COPY . .

# Models are runtime data mounted through the models volume. Set
# VISION_BOOTSTRAP_MODELS=1 to download them deliberately at startup.
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1

# Expose DRI device (needed for Intel iGPU OpenVINO)
# device access is granted via docker-compose 'devices' section

ENTRYPOINT ["./entrypoint.sh"]
CMD ["celery", "-A", "worker", "worker", "--queues=vision", "--concurrency=1", "--loglevel=info"]
