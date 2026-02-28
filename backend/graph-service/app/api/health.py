from fastapi import APIRouter
from app.core.graph_client import graph_client
import asyncio

router = APIRouter()

@router.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        g = graph_client.get_traversal()
        
        # Run graph query in executor to avoid blocking event loop
        def check_connection():
            return g.V().limit(1).toList()
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, check_connection)
        
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
