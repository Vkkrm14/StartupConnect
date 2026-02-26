from fastapi import APIRouter, HTTPException, status
import logging

from app.schemas.edge_schemas import (
    TrustsEdgeCreate, TrustsEdgeResponse,
    FoundedEdgeCreate, FoundedEdgeResponse,
    InvestedInEdgeCreate, InvestedInEdgeResponse
)
from app.services.edge_service import EdgeService

router = APIRouter()
logger = logging.getLogger(__name__)
edge_service = EdgeService()

@router.post("/trusts", response_model=TrustsEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_trusts_edge(edge_data: TrustsEdgeCreate):
    """
    Create a TRUSTS edge between two users
    
    **Properties**:
    - trust_score: 0-1 (how much from_user trusts to_user)
    - strength_score: 0-1 (relationship strength)
    - recency_score: 0-1 (decay over time)
    - domain_tags: areas of trust
    
    **Note**: TRUSTS edges are directional. For mutual trust, create two edges.
    """
    try:
        return await edge_service.create_trusts_edge(edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create TRUSTS edge error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/trusts/score")
async def update_trust_score(
    from_user_id: str,
    to_user_id: str,
    new_score: float
):
    """Update trust score on existing edge"""
    if not (0 <= new_score <= 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trust score must be between 0 and 1"
        )
    
    success = await edge_service.update_trust_score(from_user_id, to_user_id, new_score)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRUSTS edge not found"
        )
    
    return {"message": "Trust score updated", "new_score": new_score}

@router.post("/trusts/increment-intros")
async def increment_successful_intros(from_user_id: str, to_user_id: str):
    """Increment successful intro count (called after successful intro)"""
    success = await edge_service.increment_successful_intros(from_user_id, to_user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRUSTS edge not found"
        )
    
    return {"message": "Successful intro count incremented"}

@router.post("/founded", response_model=FoundedEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_founded_edge(edge_data: FoundedEdgeCreate):
    """
    Create a FOUNDED edge (User → Startup)
    
    Links a user (founder) to their startup.
    """
    try:
        return await edge_service.create_founded_edge(edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create FOUNDED edge error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/invested", response_model=InvestedInEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_invested_in_edge(edge_data: InvestedInEdgeCreate):
    """
    Create an INVESTED_IN edge (Investor → Startup)
    
    Records an investment relationship between an investor and a startup.
    """
    try:
        return await edge_service.create_invested_in_edge(edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create INVESTED_IN edge error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
