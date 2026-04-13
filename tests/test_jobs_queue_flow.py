from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient

from main import app
from models.database import get_db
from routers import jobs as jobs_router
from worker import submit_job_task


class DummyJob:
    def __init__(self, job_type: str, priority: str):
        now = datetime.now(timezone.utc)
        self.id = uuid.uuid4()
        self.job_type = job_type
        self.status = "queued"
        self.priority = priority
        self.backend = None
        self.created_at = now
        self.updated_at = now
        self.duration_ms = None
        self.result = None
        self.error = None


async def _fake_db_dep():
    yield object()


def _build_client() -> TestClient:
    app.dependency_overrides[get_db] = _fake_db_dep
    return TestClient(app)


def test_submit_llm_job_propagates_priority_and_dispatches(monkeypatch):
    created = []
    dispatched = []

    async def fake_create_job(db, job_type, payload, priority="medium"):
        created.append({"job_type": job_type, "payload": payload, "priority": priority})
        return DummyJob(job_type=job_type, priority=priority)

    def fake_delay(job_id, job_type, payload):
        dispatched.append((job_id, job_type, payload))

    monkeypatch.setattr(jobs_router, "create_job", fake_create_job)
    monkeypatch.setattr(jobs_router.submit_job_task, "delay", fake_delay)

    client = _build_client()
    try:
        response = client.post(
            "/api/v1/jobs",
            data={
                "job_type": "llm",
                "prompt": "hello world",
                "task": "generate",
                "max_tokens": "64",
                "priority": "high",
            },
        )
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["priority"] == "high"

    assert len(created) == 1
    assert created[0]["job_type"] == "llm"
    assert created[0]["priority"] == "high"

    assert len(dispatched) == 1
    assert dispatched[0][1] == "llm"


def test_submit_batch_vision_jobs_enqueues_every_file(monkeypatch):
    created = []
    dispatched = []

    async def fake_create_job(db, job_type, payload, priority="medium"):
        created.append({"job_type": job_type, "payload": payload, "priority": priority})
        return DummyJob(job_type=job_type, priority=priority)

    def fake_delay(job_id, job_type, payload):
        dispatched.append((job_id, job_type, payload))

    monkeypatch.setattr(jobs_router, "create_job", fake_create_job)
    monkeypatch.setattr(jobs_router.submit_job_task, "delay", fake_delay)

    client = _build_client()
    try:
        response = client.post(
            "/api/v1/jobs/batch",
            data={"task": "classify", "priority": "low"},
            files=[
                ("files", ("img1.jpg", b"image-one", "image/jpeg")),
                ("files", ("img2.jpg", b"image-two", "image/jpeg")),
            ],
        )
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert len(body) == 2
    assert {item["priority"] for item in body} == {"low"}

    assert len(created) == 2
    assert all(item["job_type"] == "vision" for item in created)
    assert all(item["priority"] == "low" for item in created)

    assert len(dispatched) == 2
    assert all(item[1] == "vision" for item in dispatched)


def test_dispatch_worker_routes_to_expected_queue(monkeypatch):
    sent = []

    def fake_send_task(task_name, args=None, queue=None, **kwargs):
        sent.append((task_name, args, queue))

    monkeypatch.setattr("worker.celery_app.send_task", fake_send_task)

    submit_job_task.run("job-vision", "vision", {"x": 1})
    submit_job_task.run("job-llm", "llm", {"x": 2})

    assert sent[0] == ("vision_service.run_inference", ["job-vision", {"x": 1}], "vision")
    assert sent[1] == ("llm_service.run_inference", ["job-llm", {"x": 2}], "llm")
