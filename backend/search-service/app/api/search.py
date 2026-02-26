from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.services.search_service import SearchService
from app.services.ranking import RankingService
from app.services.indexer import indexer_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Service instances
search_service = SearchService()
ranking_service = RankingService()

@router.get("/users")
async def search_users(
    q: str = Query(..., min_length=2),
    role: Optional[str] = None,
    domain: Optional[str] = None,
    geography: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user_id: Optional[str] = None
):
    """
    Search for users by name, domain tags, or other criteria
    
    **Elasticsearch full-text search with graph-aware ranking**
    """
    try:
        # Execute search
        results = await search_service.search_users(
            query=q,
            role=role,
            domain=domain,
            geography=geography,
            limit=limit,
            offset=offset
        )
        
        # Apply graph-aware ranking if user context provided
        if current_user_id and results.get("results"):
            results["results"] = await ranking_service.rank_users_by_proximity(
                results["results"],
                current_user_id
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "query": q,
            "total": 0,
            "results": [],
            "error": str(e)
        }

@router.get("/startups")
async def search_startups(
    q: str = Query(..., min_length=2),
    stage: Optional[str] = None,
    domain: Optional[str] = None,
    geography: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Search for startups"""
    try:
        results = await search_service.search_startups(
            query=q,
            stage=stage,
            domain=domain,
            geography=geography,
            limit=limit,
            offset=offset
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return {
            "query": q,
            "total": 0,
            "results": [],
            "error": str(e)
        }

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    type: str = Query("users", description="Entity type (users/startups)"),
    limit: int = Query(5, ge=1, le=20)
):
    """Autocomplete suggestions"""
    try:
        suggestions = await search_service.autocomplete(
            query=q,
            entity_type=type,
            limit=limit
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Autocomplete error: {str(e)}")
        return {"suggestions": [], "error": str(e)}

@router.post("/index/user")
async def index_user(user_data: dict):
    """Index a user document"""
    try:
        success = await indexer_service.index_user(user_data)
        
        if success:
            return {"status": "indexed", "user_id": user_data["user_id"]}
        else:
            return {"status": "failed", "user_id": user_data["user_id"]}
            
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        return {"status": "error", "error": str(e)}

@router.post("/index/startup")
async def index_startup(startup_data: dict):
    """Index a startup document"""
    try:
        success = await indexer_service.index_startup(startup_data)
        
        if success:
            return {"status": "indexed", "startup_id": startup_data["startup_id"]}
        else:
            return {"status": "failed", "startup_id": startup_data["startup_id"]}
            
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        return {"status": "error", "error": str(e)}
