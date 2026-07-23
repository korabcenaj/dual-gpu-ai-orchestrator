"""Health check and readiness endpoints."""

import os

import redis.asyncio as aioredis
from fastapi import APIRouter
from models.database import async_engine
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness():
    checks = {}

    # DB check
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must report dependency failures
        checks["postgres"] = f"error: {exc}"

    # Redis check
    try:
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must report dependency failures
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
