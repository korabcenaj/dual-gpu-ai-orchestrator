import json
import os
import time
from urllib import error
from urllib import parse, request

import pytest


RUN_LIVE_SMOKE = os.getenv("RUN_LIVE_SMOKE", "0") == "1"
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://192.168.1.200").rstrip("/")
HOST_HEADER = os.getenv("SMOKE_HOST_HEADER", "ai-orchestrator.local.lan")
TIMEOUT_SECONDS = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "120"))
POLL_SECONDS = float(os.getenv("SMOKE_POLL_SECONDS", "3"))

pytestmark = pytest.mark.skipif(
    not RUN_LIVE_SMOKE,
    reason="Set RUN_LIVE_SMOKE=1 to run live cluster smoke tests",
)


def _request_json(method: str, path: str, form: dict[str, str] | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    headers = {"Host": HOST_HEADER}
    data = None
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = parse.urlencode(form).encode("utf-8")

    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _request_multipart_json(
    path: str,
    fields: dict[str, str],
    files: list[tuple[str, str, bytes, str]],
) -> tuple[int, dict]:
    boundary = f"----smoke-{os.urandom(8).hex()}"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    for field_name, filename, content, content_type in files:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = request.Request(
        f"{BASE_URL}{path}",
        data=bytes(body),
        method="POST",
        headers={
            "Host": HOST_HEADER,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _wait_until_not_queued(job_id: str) -> tuple[dict, set[str]]:
    status_code, current = _request_json("GET", f"/api/v1/jobs/{job_id}")
    assert status_code == 200
    seen_statuses = {current["status"]}

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline and current["status"] in {"pending", "queued"}:
        time.sleep(POLL_SECONDS)
        status_code, current = _request_json("GET", f"/api/v1/jobs/{job_id}")
        assert status_code == 200
        seen_statuses.add(current["status"])

    return current, seen_statuses


def test_job_leaves_queued_state_within_timeout():
    status_code, created = _request_json(
        "POST",
        "/api/v1/jobs",
        form={
            "job_type": "llm",
            "prompt": "Reply with only: ok",
            "task": "generate",
            "max_tokens": "16",
            "priority": "high",
        },
    )
    assert status_code == 202

    job_id = created["id"]
    current, seen_statuses = _wait_until_not_queued(job_id)

    assert current["status"] not in {"pending", "queued"}, (
        f"Job {job_id} stayed queued/pending for {TIMEOUT_SECONDS}s. "
        f"Seen statuses: {sorted(seen_statuses)}"
    )


def test_batch_jobs_leave_queued_state_within_timeout():
    # We use LLM jobs here to avoid multipart construction in stdlib-only helper.
    # The purpose is to validate queue progression under bursty submissions.
    submitted_ids: list[str] = []
    for i in range(3):
        status_code, created = _request_json(
            "POST",
            "/api/v1/jobs",
            form={
                "job_type": "llm",
                "prompt": f"Reply with only: ok-{i}",
                "task": "generate",
                "max_tokens": "16",
                "priority": "high",
            },
        )
        assert status_code == 202
        submitted_ids.append(created["id"])

    still_queued: list[tuple[str, list[str]]] = []
    terminal_states: dict[str, str] = {}
    for job_id in submitted_ids:
        current, seen_statuses = _wait_until_not_queued(job_id)
        terminal_states[job_id] = current["status"]
        if current["status"] in {"pending", "queued"}:
            still_queued.append((job_id, sorted(seen_statuses)))

    assert not still_queued, (
        f"Some batch-submitted jobs stayed queued/pending for {TIMEOUT_SECONDS}s: "
        f"{still_queued}. Terminal states: {terminal_states}"
    )


def test_vision_batch_endpoint_jobs_leave_queued_state_within_timeout():
    status_code, created_jobs = _request_multipart_json(
        "/api/v1/jobs/batch",
        fields={"task": "classify", "priority": "high"},
        files=[
            ("files", "sample-a.jpg", b"fake-jpeg-a", "image/jpeg"),
            ("files", "sample-b.jpg", b"fake-jpeg-b", "image/jpeg"),
        ],
    )
    assert status_code == 202, created_jobs
    assert isinstance(created_jobs, list)
    assert len(created_jobs) == 2

    still_queued: list[tuple[str, list[str]]] = []
    terminal_states: dict[str, str] = {}
    for job in created_jobs:
        job_id = job["id"]
        current, seen_statuses = _wait_until_not_queued(job_id)
        terminal_states[job_id] = current["status"]
        if current["status"] in {"pending", "queued"}:
            still_queued.append((job_id, sorted(seen_statuses)))

    assert not still_queued, (
        f"Some vision-batch jobs stayed queued/pending for {TIMEOUT_SECONDS}s: "
        f"{still_queued}. Terminal states: {terminal_states}"
    )
