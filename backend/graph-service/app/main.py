from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.error_handlers import setup_logging, setup_error_handlers, setup_request_logging
from app.core.graph_client import graph_client
from app.api import vertices, edges, paths, health
from app.services.trust_scoring import trust_scoring_service

# Setup logging
logger = setup_logging()


async def _seconds_until_next_midnight() -> float:
    """Return seconds until next UTC midnight."""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # advance by one day
    from datetime import timedelta
    next_midnight = midnight + timedelta(days=1)
    return (next_midnight - now).total_seconds()


async def _daily_interaction_decay_loop():
    """
    Background task: waits until next UTC midnight, then applies a 40%
    interaction decay to all TRUSTS edges, and repeats every 24 hours.
    Also refreshes recency_score on every edge using the live formula.
    """
    # Wait until the start of the next day before first run
    wait_secs = await _seconds_until_next_midnight()
    logger.info(
        f"⏰ Daily interaction decay scheduled in "
        f"{wait_secs/3600:.2f}h (next UTC midnight)"
    )
    await asyncio.sleep(wait_secs)

    while True:
        try:
            logger.info("📉 Running daily interaction decay (40% reduction)...")
            decayed = await trust_scoring_service.daily_interaction_decay()
            logger.info(f"📉 Daily interaction decay complete: {decayed} edges updated")

            logger.info("🕒 Running daily recency_score refresh...")
            refreshed = await trust_scoring_service.decay_trust_scores()
            logger.info(f"🕒 Recency refresh complete: {refreshed} edges updated")

            logger.info("🧮 Running EigenTrust global rank computation...")
            eigen_updated = await trust_scoring_service.compute_eigen_trust_ranks()
            logger.info(f"🧮 EigenTrust complete: {eigen_updated} users updated")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Daily decay loop error: {e}")

        # Sleep exactly 24 hours until next run
        await asyncio.sleep(86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Graph Service...")
    await graph_client.connect()
    logger.info("✅ Connected to JanusGraph")

    decay_task = asyncio.create_task(_daily_interaction_decay_loop())

    yield

    decay_task.cancel()
    try:
        await decay_task
    except asyncio.CancelledError:
        pass

    logger.info("🛑 Shutting down Graph Service...")
    await graph_client.close()

app = FastAPI(
    title="TrustGraph - Graph Service",
    description="Graph traversal and trust-weighted path discovery service",
    version="1.0.0",
    lifespan=lifespan
)

# Setup error handlers and request logging
setup_error_handlers(app)
setup_request_logging(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(vertices.router, prefix="/api/v1/vertices", tags=["Vertices"])
app.include_router(edges.router, prefix="/api/v1/edges", tags=["Edges"])
app.include_router(paths.router, prefix="/api/v1/paths", tags=["Path Discovery"])

@app.get("/")
async def root():
    return {
        "service": "TrustGraph Graph Service",
        "version": "1.0.0",
        "status": "operational"
    }
