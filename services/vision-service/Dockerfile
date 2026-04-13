FROM python:3.12-slim

# OpenVINO OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libglib2.0-0 libGL1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download models at build time
RUN python models/download_models.py || true
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1

# Expose DRI device (needed for Intel iGPU OpenVINO)
# device access is granted via docker-compose 'devices' section

ENTRYPOINT ["./entrypoint.sh"]
CMD ["celery", "-A", "worker", "worker", "--queues=vision", "--concurrency=1", "--loglevel=info"]
