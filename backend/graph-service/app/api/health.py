from fastapi import APIRouter
from app.core.graph_client import graph_client

router = APIRouter()

@router.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        g = graph_client.get_traversal()
        # Simple graph query to verify connection
        g.V().limit(1).toList()
        
        return {
            "status": "healthy",
            "service": "graph-service",
            "janusgraph": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "graph-service",
            "error": str(e)
        }

@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {"ready": True}
