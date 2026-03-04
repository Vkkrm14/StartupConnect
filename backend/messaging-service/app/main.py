import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.cassandra import cassandra_client
from app.core.mongodb import mongo_client
from app.core.redis import redis_manager
from app.services.event_producer import event_producer
from app.services.image_service import image_service
from app.api.messages import router as messages_router
from app.api.conversations import router as conversations_router
from app.api.images import router as images_router
from app.api.websocket import connection_manager

logger = logging.getLogger(__name__)


async def _image_cleanup_loop():
    while True:
        try:
            await asyncio.sleep(86400)
            removed = await image_service.cleanup_old_images()
            logger.info(f"Background cleanup removed {removed} images")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Image cleanup error: {e}")
            await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME}...")

    cassandra_client.connect()
    await mongo_client.connect()
    await redis_manager.connect()
    event_producer.connect()

    await connection_manager.start_pubsub_listener()
    cleanup_task = asyncio.create_task(_image_cleanup_loop())

    logger.info(f"{settings.SERVICE_NAME} started on port {settings.SERVICE_PORT}")
    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    event_producer.close()
    await redis_manager.close()
    await mongo_client.close()
    cassandra_client.close()
    logger.info(f"{settings.SERVICE_NAME} shut down")


app = FastAPI(
    title="TrustGraph - Messaging Service",
    description="Encrypted Direct Messaging Microservice",
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

app.include_router(messages_router)
app.include_router(conversations_router)
app.include_router(images_router)


@app.get("/")
async def root():
    return {
        "service": "TrustGraph Messaging Service",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    health_status = {"cassandra": False, "mongodb": False, "redis": False, "kafka": False}

    try:
        cassandra_client.get_session()
        health_status["cassandra"] = True
    except Exception:
        pass

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

    try:
        if event_producer.producer:
            health_status["kafka"] = True
    except Exception:
        pass

    all_healthy = all(health_status.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "dependencies": health_status,
        "storage": image_service.get_storage_stats(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = await connection_manager.authenticate(websocket)
    if not user_id:
        return

    session_id = await connection_manager.connect(websocket, user_id)
    try:
        while True:
            raw = await websocket.receive_text()
            await connection_manager.handle_message(user_id, raw)
    except WebSocketDisconnect:
        await connection_manager.disconnect(user_id, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        await connection_manager.disconnect(user_id, session_id)
