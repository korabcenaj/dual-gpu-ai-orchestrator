"""
Celery worker for the LLM service.
Listens on the 'llm' queue and runs text inference on the AMD WX 3100 via Vulkan.
"""
from __future__ import annotations

import logging
import os
import time

from celery import Celery
from psycopg2.extras import Json
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://orchestrator:orchestrator@postgres:5432/orchestrator",
)

celery_app = Celery("llm_service", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

sync_engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _update_job(job_id, status, backend, result=None, error=None, duration_ms=None):
    with sync_engine.connect() as conn:
        values = {"status": status, "backend": backend}
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


@celery_app.task(name="llm_service.run_inference", bind=True, max_retries=2)
def run_inference(self, job_id: str, payload: dict):
    _update_job(job_id, "running", "amd-wx3100-vulkan")
    t0 = time.perf_counter()
    try:
        from inference import run_inference as _infer

        result = _infer(
            text=payload["prompt"],
            task=payload.get("task", "generate"),
            labels=payload.get("labels"),
            max_tokens=int(payload.get("max_tokens", 256)),
            temperature=float(payload.get("temperature", 0.3)),
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)
        _update_job(job_id, "completed", "amd-wx3100-vulkan",
                    result=result, duration_ms=duration_ms)
        logger.info("Job %s completed — %d tokens in %d ms", job_id,
                    result.get("tokens_generated", 0), duration_ms)
    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        if self.request.retries >= self.max_retries:
            _update_job(job_id, "failed", "amd-wx3100-vulkan", error=str(exc))
            return
        raise self.retry(exc=exc, countdown=10)
