from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.error_handlers import setup_logging, setup_error_handlers, setup_request_logging
from app.core.elasticsearch_client import es_client
from app.api import search, health

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting Search Service...")
    
    # Connect to Elasticsearch
    try:
        await es_client.connect()
        logger.info("✅ Elasticsearch connected")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Elasticsearch: {str(e)}")
    
    yield
    
    logger.info("🛑 Shutting down Search Service...")
    await es_client.close()

app = FastAPI(
    title="TrustGraph - Search Service",
    description="Search and discovery service with Elasticsearch",
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
app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])

@app.get("/")
async def root():
    return {
        "service": "TrustGraph Search Service",
        "version": "1.0.0",
        "status": "operational"
    }
