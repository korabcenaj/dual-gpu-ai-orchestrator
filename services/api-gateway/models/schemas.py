"""
Pydantic schemas for API request/response validation.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobCreate(BaseModel):
    job_type: str
    payload: dict[str, Any]
    priority: Priority = Priority.MEDIUM


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: JobStatus
    priority: Priority
    backend: str | None
    created_at: datetime
    updated_at: datetime
    duration_ms: int | None
    result: dict[str, Any] | None
    error: str | None
