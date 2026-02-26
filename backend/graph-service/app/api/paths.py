from fastapi import APIRouter, HTTPException, Depends
import logging

from app.schemas.path_schemas import (
    PathDiscoveryRequest,
    PathDiscoveryResponse,
    IntroPath
)
from app.services.path_discovery import PathDiscoveryService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/discover", response_model=PathDiscoveryResponse)
async def discover_intro_paths(
    request: PathDiscoveryRequest,
    path_service: PathDiscoveryService = Depends()
):
    """
    🔍 Discover trust-weighted intro paths from Founder to Investor
    
    **Algorithm**:
    - Traverses TRUSTS edges up to 4 hops
    - Prioritizes mutual trust (bidirectional edges)
    - Scores paths by: trust × strength × recency × mutual_boost
    - Returns top N ranked paths
    
    **Constraints**:
    - Max hops: 4 (configurable)
    - Min trust score: 0.3
    - Filters out low-quality paths
    
    **Example**:
    ```json
    {
      "founder_id": "user123",
      "investor_id": "user456",
      "max_paths": 5,
      "domain_filter": "fintech"
    }
    ```
    """
    try:
        logger.info(
            f"Path discovery: {request.founder_id} → {request.investor_id}"
        )
        
        paths = await path_service.find_intro_paths(
            founder_id=request.founder_id,
            investor_id=request.investor_id,
            max_paths=request.max_paths,
            domain_filter=request.domain_filter
        )
        
        return PathDiscoveryResponse(
            founder_id=request.founder_id,
            investor_id=request.investor_id,
            paths=paths,
            total_paths_found=len(paths)
        )
        
    except Exception as e:
        logger.error(f"Path discovery error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
