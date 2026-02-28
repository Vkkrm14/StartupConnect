from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
import logging

from app.core.config import settings
from app.api import intros, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB client
mongo_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global mongo_client
    logger.info("🚀 Starting Workflow Service...")
    
    # Connect to MongoDB
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    app.state.db = mongo_client[settings.MONGODB_DB_NAME]
    logger.info("✅ Connected to MongoDB")
    
    yield
    
    logger.info("🛑 Shutting down Workflow Service...")
    mongo_client.close()

app = FastAPI(
    title="TrustGraph - Workflow Service",
    description="Intro workflow and approval chain management",
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
app.include_router(intros.router, prefix="/api/v1/intros", tags=["Intro Workflow"])

@app.get("/")
async def root():
    return {
        "service": "TrustGraph Workflow Service",
        "version": "1.0.0",
        "status": "operational"
    }
