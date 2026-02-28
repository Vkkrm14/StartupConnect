from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.graph_client import graph_client
from app.api import vertices, edges, paths, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Graph Service...")
    await graph_client.connect()
    logger.info("✅ Connected to JanusGraph")
    yield
    logger.info("🛑 Shutting down Graph Service...")
    await graph_client.close()

app = FastAPI(
    title="TrustGraph - Graph Service",
    description="Graph traversal and trust-weighted path discovery service",
    version="1.0.0",
    lifespan=lifespan
)

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
