"""
Celery worker for the vision service.
Listens on the 'vision' queue, runs inference, and writes results back
to the API gateway via a shared database connection.
"""
from __future__ import annotations

import logging
import os
import time
import uuid

from celery import Celery
from psycopg2.extras import Json
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
import redis
import json

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://orchestrator:orchestrator@postgres:5432/orchestrator",
)

celery_app = Celery("vision_service", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

sync_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
redis_client = redis.from_url(REDIS_URL)


def _update_job(
    job_id: str,
    status: str,
    backend: str,
    result: dict | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
) -> None:
    from sqlalchemy import text

    with sync_engine.connect() as conn:
        values: dict = {"status": status, "backend": backend}
        if result is not None:
            values["result"] = Json(result)
        if error is not None:
            values["error"] = error
        if duration_ms is not None:
            values["duration_ms"] = duration_ms
        placeholders = ", ".join(f"{k} = :{k}" for k in values)
        conn.execute(
            text(f"UPDATE jobs SET {placeholders}, updated_at = now() WHERE id = :id"),
            {**values, "id": job_id},
        )
        conn.commit()


def broadcast_status(job_id, status, backend, result=None, error=None, duration_ms=None):
    message = {
        "job_id": job_id,
        "status": status,
        "backend": backend,
        "result": result,
        "error": error,
        "duration_ms": duration_ms,
    }
    redis_client.publish("job_status", json.dumps(message, default=str))


@celery_app.task(name="vision_service.run_inference", bind=True, max_retries=2)
def run_inference(self, job_id: str, payload: dict):
    _update_job(job_id, "running", "intel-igpu-openvino")
    broadcast_status(job_id, "running", "intel-igpu-openvino")
    t0 = time.perf_counter()
    try:
        from inference import run_inference as _infer

        result = _infer(payload)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        _update_job(job_id, "completed", "intel-igpu-openvino", result=result, duration_ms=duration_ms)
        broadcast_status(job_id, "completed", "intel-igpu-openvino", result=result, duration_ms=duration_ms)
    except Exception as e:
        _update_job(job_id, "failed", "intel-igpu-openvino", error=str(e))
        broadcast_status(job_id, "failed", "intel-igpu-openvino", error=str(e))
        raise
