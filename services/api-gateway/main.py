"""
API Gateway — entry point for the Dual-GPU AI Orchestrator.
Exposes REST endpoints for job submission, status, and results.
"""
import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from prometheus_client import make_asgi_app
from typing import List
import asyncio
import aioredis
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/jobs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def redis_listener():
    redis = await aioredis.create_redis(REDIS_URL)
    res = await redis.subscribe("job_status")
    ch = res[0]
    while await ch.wait_message():
        msg = await ch.get(encoding="utf-8")
        await manager.broadcast(msg)

@app.on_event("startup")
def start_redis_listener():
    loop = asyncio.get_event_loop()
    loop.create_task(redis_listener())

from routers import jobs, health
from models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Dual-GPU AI Orchestrator",
    version="1.0.0",
    description="Heterogeneous inference platform using Intel iGPU + AMD WX 3100",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(health.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
