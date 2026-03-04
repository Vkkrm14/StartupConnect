from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import httpx

from app.core.config import settings
from app.core.error_handlers import setup_logging, setup_error_handlers, setup_request_logging
from app.api import auth

# Setup logging
logger = setup_logging()

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

# Setup error handlers and request logging
setup_error_handlers(app)
setup_request_logging(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)

# HTTP client for service communication
http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

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
    
    try:
        messaging_response = await http_client.get(f"{settings.MESSAGING_SERVICE_URL}/health")
        services_status["messaging-service"] = messaging_response.status_code == 200
    except:
        services_status["messaging-service"] = False
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }

# ========================================
# Graph Service Proxy Routes
# ========================================

@app.get("/api/v1/users")
async def list_users(role: str = None, limit: int = 100):
    """Proxy to graph service - list users"""
    params = {"limit": limit}
    if role:
        params["role"] = role
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users",
        params=params
    )
    return response.json()

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

@app.get("/api/v1/users/{user_id}/connections")
async def get_user_connections(user_id: str):
    """Proxy to graph service - get user connections"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}/connections"
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
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/",
        json=body
    )
    return response.json()

@app.get("/api/v1/intros/user/{user_id}")
async def get_user_intro_requests(user_id: str):
    """Proxy to workflow service - get user's intro requests"""
    response = await http_client.get(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/user/{user_id}"
    )
    return response.json()

@app.get("/api/v1/intros/pending/{user_id}")
async def get_pending_approvals(user_id: str):
    """Proxy to workflow service - get pending approvals for user"""
    response = await http_client.get(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/pending/{user_id}"
    )
    return response.json()

@app.get("/api/v1/intros/{intro_id}")
async def get_intro_request(intro_id: str):
    """Proxy to workflow service - get intro request"""
    response = await http_client.get(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/{intro_id}"
    )
    return response.json()

@app.post("/api/v1/intros/{intro_id}/approve")
async def approve_intro_request(request: Request, intro_id: str):
    """Proxy to workflow service - approve intro request"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/{intro_id}/approve",
        json=body
    )
    return response.json()

@app.post("/api/v1/intros/{intro_id}/decline")
async def decline_intro_request(request: Request, intro_id: str):
    """Proxy to workflow service - decline intro request"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/{intro_id}/decline",
        json=body
    )
    return response.json()

@app.post("/api/v1/intros/{intro_id}/complete")
async def complete_intro_request(request: Request, intro_id: str):
    """Proxy to workflow service - complete intro request"""
    response = await http_client.post(
        f"{settings.WORKFLOW_SERVICE_URL}/api/v1/intros/{intro_id}/complete"
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


# ========================================
# Messaging Service Proxy Routes
# ========================================

@app.post("/api/v1/messages/send")
async def proxy_send_message(request: Request):
    """Proxy to messaging service - send message"""
    body = await request.json()
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.post(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/messages/send",
        json=body, headers=headers
    )
    return response.json()

@app.get("/api/v1/messages/{conversation_id}")
async def proxy_get_messages(request: Request, conversation_id: str, limit: int = 50, before: str = None):
    """Proxy to messaging service - get conversation messages"""
    params = {"limit": limit}
    if before:
        params["before"] = before
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.get(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/messages/{conversation_id}",
        params=params, headers=headers
    )
    return response.json()

@app.post("/api/v1/messages/read-receipt")
async def proxy_read_receipt(request: Request):
    """Proxy to messaging service - read receipt"""
    body = await request.json()
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.post(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/messages/read-receipt",
        json=body, headers=headers
    )
    return response.json()

@app.post("/api/v1/messages/typing")
async def proxy_typing(request: Request):
    """Proxy to messaging service - typing indicator"""
    body = await request.json()
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.post(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/messages/typing",
        json=body, headers=headers
    )
    return response.json()

@app.post("/api/v1/conversations/")
async def proxy_create_conversation(request: Request):
    """Proxy to messaging service - create conversation"""
    body = await request.json()
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.post(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/conversations/",
        json=body, headers=headers
    )
    return response.json()

@app.get("/api/v1/conversations/")
async def proxy_list_conversations(request: Request, skip: int = 0, limit: int = 50):
    """Proxy to messaging service - list conversations"""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.get(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/conversations/",
        params={"skip": skip, "limit": limit}, headers=headers
    )
    return response.json()

@app.get("/api/v1/conversations/{conversation_id}")
async def proxy_get_conversation(request: Request, conversation_id: str):
    """Proxy to messaging service - get conversation"""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.get(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/conversations/{conversation_id}",
        headers=headers
    )
    return response.json()

@app.get("/api/v1/conversations/{conversation_id}/presence")
async def proxy_conversation_presence(request: Request, conversation_id: str):
    """Proxy to messaging service - presence status"""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.get(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/conversations/{conversation_id}/presence",
        headers=headers
    )
    return response.json()

@app.post("/api/v1/conversations/block")
async def proxy_block_user(request: Request):
    """Proxy to messaging service - block user"""
    body = await request.json()
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.post(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/conversations/block",
        json=body, headers=headers
    )
    return response.json()

@app.get("/api/v1/images/download/{conversation_id}/{file_id}")
async def proxy_download_image(request: Request, conversation_id: str, file_id: str):
    """Proxy to messaging service - download encrypted image"""
    headers = {"Authorization": request.headers.get("Authorization", "")}
    response = await http_client.get(
        f"{settings.MESSAGING_SERVICE_URL}/api/v1/images/download/{conversation_id}/{file_id}",
        headers=headers
    )
    from fastapi.responses import Response
    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "application/octet-stream"),
        headers={"Content-Disposition": response.headers.get("content-disposition", "")}
    )
