"""
CRUD helpers — async database operations for jobs.
"""
import uuid
from typing import Optional, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm import Job
from models.schemas import JobStatus


async def create_job(
    db: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
) -> Job:
    job = Job(job_type=job_type, payload=payload, status=JobStatus.QUEUED)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    q = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Job.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: JobStatus,
    backend: Optional[str] = None,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> None:
    values: dict[str, Any] = {"status": status}
    if backend is not None:
        values["backend"] = backend
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error"] = error
    if duration_ms is not None:
        values["duration_ms"] = duration_ms
    await db.execute(update(Job).where(Job.id == job_id).values(**values))
    await db.commit()
