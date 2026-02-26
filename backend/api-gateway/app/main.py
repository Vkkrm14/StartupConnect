from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import httpx

from app.core.config import settings
from app.api import auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting API Gateway...")
    yield
    logger.info("🛑 Shutting down API Gateway...")

app = FastAPI(
    title="TrustGraph - API Gateway",
    description="Main API Gateway for TrustGraph platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)

# HTTP client for service communication
http_client = httpx.AsyncClient(timeout=30.0)

@app.get("/")
async def root():
    return {
        "service": "TrustGraph API Gateway",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Aggregate health check from all services"""
    services_status = {}
    
    try:
        # Check graph service
        graph_response = await http_client.get(f"{settings.GRAPH_SERVICE_URL}/health")
        services_status["graph-service"] = graph_response.status_code == 200
    except:
        services_status["graph-service"] = False
    
    try:
        # Check workflow service
        workflow_response = await http_client.get(f"{settings.WORKFLOW_SERVICE_URL}/health")
        services_status["workflow-service"] = workflow_response.status_code == 200
    except:
        services_status["workflow-service"] = False
    
    try:
        # Check search service
        search_response = await http_client.get(f"{settings.SEARCH_SERVICE_URL}/health")
        services_status["search-service"] = search_response.status_code == 200
    except:
        services_status["search-service"] = False
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }

# ========================================
# Graph Service Proxy Routes
# ========================================

@app.post("/api/v1/users")
async def create_user(request: Request):
    """Proxy to graph service - create user"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users",
        json=body
    )
    return response.json()

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str):
    """Proxy to graph service - get user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}"
    )
    return response.json()

@app.post("/api/v1/trusts")
async def create_trust_edge(request: Request):
    """Proxy to graph service - create TRUSTS edge"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts",
        json=body
    )
    return response.json()

@app.post("/api/v1/paths/discover")
async def discover_paths(request: Request):
    """Proxy to graph service - discover intro paths"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/paths/discover",
        json=body
    )
    return response.json()

# ========================================
# Workflow Service Proxy Routes
# ========================================

@app.post("/api/v1/intros")
async def create_intro_request(request: Request):
    """Proxy to workflow service - create intro request"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros",
        json=body
    )
    return response.json()

@app.get("/api/v1/intros/{intro_id}")
async def get_intro_request(intro_id: str):
    """Proxy to workflow service - get intro request"""
    response = await http_client.get(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/{intro_id}"
    )
    return response.json()

# ========================================
# Search Service Proxy Routes
# ========================================

@app.get("/api/v1/search/users")
async def search_users(q: str, limit: int = 10):
    """Proxy to search service - search users"""
    response = await http_client.get(
        f"{settings.SEARCH_SERVICE_URL}/api/v1/search/users",
        params={"q": q, "limit": limit}
    )
    return response.json()
