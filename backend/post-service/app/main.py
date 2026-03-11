import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import mongo_client
from app.core.redis import redis_manager
from app.api.posts import router as posts_router

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME}...")
    await mongo_client.connect()
    await redis_manager.connect()
    logger.info(f"{settings.SERVICE_NAME} started on port {settings.SERVICE_PORT}")
    yield
    await redis_manager.close()
    await mongo_client.close()
    logger.info(f"{settings.SERVICE_NAME} shut down")


app = FastAPI(
    title="TrustGraph - Post Service",
    description="Startup Posts Microservice",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts_router)


@app.get("/")
async def root():
    return {
        "service": "TrustGraph Post Service",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    health_status = {"mongodb": False, "redis": False}
    try:
        db = mongo_client.get_db()
        await db.command("ping")
        health_status["mongodb"] = True
    except Exception:
        pass
    try:
        await redis_manager.client.ping()
        health_status["redis"] = True
    except Exception:
        pass
    all_healthy = all(health_status.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "dependencies": health_status,
    }
