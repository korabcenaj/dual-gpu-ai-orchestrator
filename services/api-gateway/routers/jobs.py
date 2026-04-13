"""
Job router — submit, list, get, and cancel inference jobs.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import Counter, Histogram

from models.database import get_db
from models.schemas import JobOut, JobStatus, Priority
from models.crud import create_job, get_job, list_jobs, update_job_status
from worker import submit_job_task

router = APIRouter(tags=["jobs"])

JOBS_SUBMITTED = Counter("jobs_submitted_total", "Jobs submitted", ["job_type"])
JOBS_DURATION = Histogram(
    "job_duration_seconds",
    "Job end-to-end duration",
    ["job_type", "backend"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
)


@router.post("/jobs", response_model=JobOut, status_code=202)
async def submit_job(
    job_type: str = Form(..., description="'vision' or 'llm'"),
    prompt: Optional[str] = Form(None, description="Text prompt for LLM jobs"),
    task: Optional[str] = Form(None, description="Inference task override"),
    labels: Optional[str] = Form(None, description="Comma-separated labels for classify task"),
    max_tokens: Optional[int] = Form(None, description="Maximum output tokens for LLM jobs"),
    temperature: Optional[float] = Form(None, description="Sampling temperature for LLM jobs"),
    priority: str = Form("medium", description="Job priority: low, medium, or high"),
    file: Optional[UploadFile] = File(None, description="Image file for vision jobs"),
    db: AsyncSession = Depends(get_db),
):
    if job_type not in ("vision", "llm"):
        raise HTTPException(status_code=422, detail="job_type must be 'vision' or 'llm'")
    if priority not in ("low", "medium", "high"):
        raise HTTPException(status_code=422, detail="priority must be 'low', 'medium', or 'high'")
    if job_type == "vision" and file is None:
        raise HTTPException(status_code=422, detail="Vision jobs require an image file")
    if job_type == "llm" and not prompt:
        raise HTTPException(status_code=422, detail="LLM jobs require a prompt")

    payload: dict = {"job_type": job_type}
    if file:
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
        payload["filename"] = file.filename
        payload["file_bytes"] = contents.hex()  # store safely
    if prompt:
        if len(prompt) > 4096:
            raise HTTPException(status_code=422, detail="Prompt exceeds 4096 characters")
        payload["prompt"] = prompt
    if task:
        payload["task"] = task
    if labels:
        payload["labels"] = [label.strip() for label in labels.split(",") if label.strip()]
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature

    job = await create_job(db, job_type=job_type, payload=payload, priority=priority)
    JOBS_SUBMITTED.labels(job_type=job_type).inc()

    submit_job_task.delay(str(job.id), job_type, payload)
    return job


@router.post("/jobs/batch", response_model=list[JobOut], status_code=202)
async def submit_batch_jobs(
    task: str = Form("classify", description="Vision task for all jobs"),
    priority: str = Form("medium", description="Job priority: low, medium, or high"),
    files: list[UploadFile] = File(..., description="Image files for batch processing"),
    db: AsyncSession = Depends(get_db),
):
    if priority not in ("low", "medium", "high"):
        raise HTTPException(status_code=422, detail="priority must be 'low', 'medium', or 'high'")
    if not files:
        raise HTTPException(status_code=422, detail="At least one file is required")
    if len(files) > 100:
        raise HTTPException(status_code=413, detail="Maximum 100 files per batch")

    results = []
    for file in files:
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File {file.filename} exceeds 10 MB limit")

        payload = {
            "job_type": "vision",
            "filename": file.filename,
            "file_bytes": contents.hex(),
            "task": task,
        }
        
        job = await create_job(db, job_type="vision", payload=payload, priority=priority)
        JOBS_SUBMITTED.labels(job_type="vision").inc()
        submit_job_task.delay(str(job.id), "vision", payload)
        results.append(job)

    return results


@router.get("/jobs", response_model=list[JobOut])
async def list_all_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await list_jobs(db, status=status, limit=min(limit, 200), offset=offset)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.PENDING, JobStatus.QUEUED):
        raise HTTPException(status_code=409, detail=f"Cannot cancel job in state: {job.status}")
    await update_job_status(db, job_id, JobStatus.CANCELLED)
    return Response(status_code=204)
