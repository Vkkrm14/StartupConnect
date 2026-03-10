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

# ========================================
# Direct Edges Service Proxy Routes
# ========================================

@app.post("/api/v1/edges/trusts")
async def create_trusts_edge_direct(request: Request):
    """Proxy to graph service - create TRUSTS edge (direct route)"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts",
        json=body
    )
    return response.json()

@app.put("/api/v1/edges/trusts/accept")
async def accept_trusts_edge(from_user_id: str, to_user_id: str):
    """Proxy to graph service - accept TRUSTS edge"""
    response = await http_client.put(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/accept",
        params={"from_user_id": from_user_id, "to_user_id": to_user_id}
    )
    return response.json()

@app.put("/api/v1/edges/trusts/reject")
async def reject_trusts_edge(from_user_id: str, to_user_id: str):
    """Proxy to graph service - reject TRUSTS edge"""
    response = await http_client.put(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/reject",
        params={"from_user_id": from_user_id, "to_user_id": to_user_id}
    )
    return response.json()

@app.get("/api/v1/edges/trusts/pending/{user_id}")
async def get_pending_trust_edges(user_id: str):
    """Proxy to graph service - get pending TRUSTS edges for user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/pending/{user_id}"
    )
    return response.json()

@app.get("/api/v1/edges/trusts/user/{user_id}")
async def get_user_trust_edges(user_id: str, edge_status: str = None, direction: str = "out"):
    """Proxy to graph service - get user trust edges"""
    params = {"direction": direction}
    if edge_status:
        params["edge_status"] = edge_status
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/user/{user_id}",
        params=params
    )
    return response.json()

@app.delete("/api/v1/edges/trusts")
async def delete_trust_edge(from_user_id: str, to_user_id: str):
    """Proxy to graph service - delete trust edge"""
    response = await http_client.delete(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts",
        params={"from_user_id": from_user_id, "to_user_id": to_user_id}
    )
    return response.json()

@app.get("/api/v1/edges/trusts/score/{from_user_id}/{to_user_id}")
async def get_trust_score(from_user_id: str, to_user_id: str):
    """Proxy to graph service - get trust score between users"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/score/{from_user_id}/{to_user_id}"
    )
    return response.json()

@app.get("/api/v1/edges/trusts/connected/{from_user_id}/{to_user_id}")
async def get_connection_status(from_user_id: str, to_user_id: str):
    """Proxy to graph service - check connection status"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/connected/{from_user_id}/{to_user_id}"
    )
    return response.json()

@app.post("/api/v1/edges/trusts/increment-interaction")
async def increment_interaction(from_user_id: str, to_user_id: str):
    """Proxy to graph service - increment interaction count"""
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/increment-interaction",
        params={"from_user_id": from_user_id, "to_user_id": to_user_id}
    )
    return response.json()

@app.get("/api/v1/edges/trusts/reputation/{user_id}")
async def get_reputation_score(user_id: str):
    """Proxy to graph service - get reputation score"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/reputation/{user_id}"
    )
    return response.json()

@app.patch("/api/v1/users/{user_id}")
async def update_user(request: Request, user_id: str):
    """Proxy to graph service - update user"""
    body = await request.json()
    response = await http_client.patch(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}",
        json=body
    )
    return response.json()

# ---- DISTRUSTS ----

@app.post("/api/v1/edges/distrusts")
async def create_distrusts_edge(request: Request):
    """Proxy to graph service - create DISTRUSTS edge"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/distrusts",
        json=body
    )
    return response.json()

@app.put("/api/v1/edges/distrusts/activate")
async def activate_distrusts_edge(request: Request):
    """Proxy to graph service - moderator activates a DISTRUSTS edge"""
    body = await request.json()
    response = await http_client.put(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/distrusts/activate",
        json=body
    )
    return response.json()

@app.delete("/api/v1/edges/distrusts")
async def delete_distrusts_edge(request: Request):
    """Proxy to graph service - delete/expire a DISTRUSTS edge"""
    body = await request.json()
    response = await http_client.request(
        "DELETE",
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/distrusts",
        json=body
    )
    return response.json()

@app.get("/api/v1/edges/distrusts/by/{user_id}")
async def get_distrusts_by_user(user_id: str):
    """Proxy to graph service - get DISTRUSTS edges filed by a user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/distrusts/by/{user_id}"
    )
    return response.json()

@app.get("/api/v1/edges/distrusts/for/{user_id}")
async def get_distrusts_for_user(user_id: str):
    """Proxy to graph service - get DISTRUSTS edges targeting a user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/distrusts/for/{user_id}"
    )
    return response.json()

# ---- VOUCHES ----

@app.post("/api/v1/edges/vouches")
async def create_vouch(request: Request):
    """Proxy to graph service - create a VOUCH edge"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/vouches",
        json=body
    )
    return response.json()

@app.delete("/api/v1/edges/vouches/revoke")
async def revoke_vouch(request: Request):
    """Proxy to graph service - revoke a VOUCH edge"""
    body = await request.json()
    response = await http_client.request(
        "DELETE",
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/vouches/revoke",
        json=body
    )
    return response.json()

@app.get("/api/v1/edges/vouches/for/{user_id}")
async def get_vouches_for_user(user_id: str):
    """Proxy to graph service - get active vouches targeting a user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/vouches/for/{user_id}"
    )
    return response.json()

@app.get("/api/v1/edges/vouches/by/{user_id}")
async def get_vouches_by_user(user_id: str):
    """Proxy to graph service - get vouches created by a user"""
    response = await http_client.get(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/vouches/by/{user_id}"
    )
    return response.json()

# ---- Admin ----

@app.post("/api/v1/edges/admin/eigen-trust-refresh")
async def trigger_eigen_trust_refresh(request: Request):
    """Proxy to graph service - trigger EigenTrust batch recomputation"""
    body = await request.json()
    response = await http_client.post(
        f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/admin/eigen-trust-refresh",
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
