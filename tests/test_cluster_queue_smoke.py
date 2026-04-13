import json
import os
import time
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
    with request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


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
    current = created
    seen_statuses = {current["status"]}

    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline and current["status"] in {"pending", "queued"}:
        time.sleep(POLL_SECONDS)
        status_code, current = _request_json("GET", f"/api/v1/jobs/{job_id}")
        assert status_code == 200
        seen_statuses.add(current["status"])

    assert current["status"] not in {"pending", "queued"}, (
        f"Job {job_id} stayed queued/pending for {TIMEOUT_SECONDS}s. "
        f"Seen statuses: {sorted(seen_statuses)}"
    )
