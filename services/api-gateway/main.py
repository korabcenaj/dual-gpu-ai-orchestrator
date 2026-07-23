"""FastAPI entry point for the heterogeneous GPU job orchestrator."""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models.database import init_db
from prometheus_client import make_asgi_app
from routers import health, jobs

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class ConnectionManager:
    """Track dashboard WebSockets and remove failed connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        with contextlib.suppress(ValueError):
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        failed: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except RuntimeError:
                failed.append(connection)
        for connection in failed:
            self.disconnect(connection)


manager = ConnectionManager()


async def redis_listener() -> None:
    """Forward worker status events from Redis to connected dashboards."""
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe("job_status")
        async for event in pubsub.listen():
            if event["type"] == "message":
                await manager.broadcast(str(event["data"]))
    finally:
        await pubsub.aclose()
        await client.aclose()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize persistence and own the Redis-listener task."""
    await init_db()
    listener_task = asyncio.create_task(redis_listener())
    try:
        yield
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task


app = FastAPI(
    title="Dual-GPU AI Orchestrator",
    version="1.0.0",
    description="Heterogeneous inference platform for Intel and AMD Linux GPU devices.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/metrics", make_asgi_app())
app.include_router(health.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")


@app.websocket("/ws/jobs")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
