"""
Celery worker task — dispatches jobs to vision or LLM service queues.
"""
import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "api_gateway",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.task_routes = {
    "worker.submit_job_task": {"queue": "dispatch"},
}
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


@celery_app.task(name="worker.submit_job_task", bind=True, max_retries=3)
def submit_job_task(self, job_id: str, job_type: str, payload: dict):
    """Route the job to the appropriate inference queue."""
    queue = "vision" if job_type == "vision" else "llm"
    celery_app.send_task(
        f"{queue}_service.run_inference",
        args=[job_id, payload],
        queue=queue,
    )
