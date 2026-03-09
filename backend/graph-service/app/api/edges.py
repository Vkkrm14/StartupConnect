from fastapi import APIRouter, HTTPException, status
import logging
from typing import Optional, List

from app.schemas.edge_schemas import (
    TrustsEdgeCreate, TrustsEdgeResponse,
    FoundedEdgeCreate, FoundedEdgeResponse,
    InvestedInEdgeCreate, InvestedInEdgeResponse,
    DisTrustsEdgeCreate, DisTrustsEdgeResponse,
    VouchCreate, VouchResponse,
)
from app.services.edge_service import EdgeService
from app.services.trust_scoring import trust_scoring_service

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
    Edge starts with status='pending' — receiver must accept.
    """
    try:
        return await edge_service.create_trusts_edge(edge_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create TRUSTS edge error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ── Connection Request / Approval Flow ──

@router.put("/trusts/accept")
async def accept_trusts_edge(from_user_id: str, to_user_id: str):
    """Accept a pending TRUSTS edge (the receiver approves the connection)"""
    success = await edge_service.accept_trusts_edge(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending TRUSTS edge found between these users"
        )
    return {"message": "TRUSTS edge accepted", "from_user_id": from_user_id, "to_user_id": to_user_id}

@router.put("/trusts/reject")
async def reject_trusts_edge(from_user_id: str, to_user_id: str):
    """Reject a pending TRUSTS edge (the receiver declines the connection)"""
    success = await edge_service.reject_trusts_edge(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending TRUSTS edge found between these users"
        )
    return {"message": "TRUSTS edge rejected", "from_user_id": from_user_id, "to_user_id": to_user_id}

@router.get("/trusts/pending/{user_id}")
async def get_pending_requests(user_id: str):
    """Get all pending TRUSTS edges where this user is the receiver"""
    pending = await edge_service.get_pending_requests(user_id)
    return {"user_id": user_id, "pending_requests": pending, "count": len(pending)}

@router.get("/trusts/user/{user_id}")
async def get_user_trust_edges(
    user_id: str,
    edge_status: Optional[str] = None,
    direction: str = "out"
):
    """Get all TRUSTS edges for a user.
    
    Query params:
    - **edge_status**: Filter by 'pending', 'accepted', or 'rejected'
    - **direction**: 'out' (sent), 'in' (received), or 'both' (default: out)
    """
    if direction not in ("out", "in", "both"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="direction must be 'out', 'in', or 'both'"
        )
    edges = await edge_service.get_user_trust_edges(user_id, status=edge_status, direction=direction)
    return {"user_id": user_id, "edges": edges, "count": len(edges)}

# ── Edge Deletion ──

@router.delete("/trusts")
async def delete_trusts_edge(from_user_id: str, to_user_id: str):
    """Delete a mutual connection between two users"""
    success = await edge_service.delete_trusts_edge(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRUSTS edge not found"
        )
    return {"message": "TRUSTS edge deleted", "from_user_id": from_user_id, "to_user_id": to_user_id}

@router.get("/trusts/connected/{from_user_id}/{to_user_id}")
async def get_connection_status(from_user_id: str, to_user_id: str):
    """Check whether two users are mutually connected via accepted trust edges."""
    forward_connected = await edge_service.has_accepted_trust_edge(from_user_id, to_user_id)
    reverse_connected = await edge_service.has_accepted_trust_edge(to_user_id, from_user_id)
    return {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "is_connected": forward_connected and reverse_connected,
        "forward_connected": forward_connected,
        "reverse_connected": reverse_connected,
    }

@router.delete("/founded")
async def delete_founded_edge(user_id: str, startup_id: str):
    """Delete a FOUNDED edge between a user and startup"""
    success = await edge_service.delete_founded_edge(user_id, startup_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FOUNDED edge not found"
        )
    return {"message": "FOUNDED edge deleted", "user_id": user_id, "startup_id": startup_id}

@router.delete("/invested")
async def delete_invested_in_edge(investor_id: str, startup_id: str):
    """Delete an INVESTED_IN edge between an investor and startup"""
    success = await edge_service.delete_invested_in_edge(investor_id, startup_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="INVESTED_IN edge not found"
        )
    return {"message": "INVESTED_IN edge deleted", "investor_id": investor_id, "startup_id": startup_id}

# ── Interaction Count (with auto score sync) ──

@router.post("/trusts/increment-interaction")
async def increment_interaction_count(from_user_id: str, to_user_id: str):
    """Increment interaction count and auto-recalculate trust score"""
    success = await edge_service.increment_interaction_count(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRUSTS edge not found"
        )
    return {"message": "Interaction count incremented and trust score recalculated"}

@router.put("/trusts/score")
async def update_trust_score(
    from_user_id: str,
    to_user_id: str,
    new_score: Optional[float] = None
):
    """Update trust score on existing edge.
    Omit new_score to auto-recalculate using the scoring formula.
    """
    if new_score is not None and not (0 <= new_score <= 1):
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
    
    label = "recalculated" if new_score is None else "updated"
    return {"message": f"Trust score {label}", "new_score": new_score}

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


@router.get("/trusts/score/{from_user_id}/{to_user_id}")
async def get_trust_score(from_user_id: str, to_user_id: str):
    """Get the calculated trust score between two users"""
    score = await trust_scoring_service.calculate_trust_score(from_user_id, to_user_id)
    return {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "trust_score": score,
        "trust_level": "high" if score >= 0.7 else "medium" if score >= 0.3 else "low"
    }


@router.get("/trusts/reputation/{user_id}")
async def get_reputation(user_id: str):
    """Get and refresh the reputation score for a user"""
    reputation = await trust_scoring_service.update_reputation_score(user_id)
    return {"user_id": user_id, "reputation_score": reputation}


@router.get("/trusts/centrality/{user_id}")
async def get_centrality(user_id: str):
    """Get network centrality metrics for a user"""
    return await trust_scoring_service.calculate_network_centrality(user_id)

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

# ========================================
# DISTRUSTS Routes
# ========================================

@router.post("/distrusts", response_model=DisTrustsEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_distrusts_edge(edge_data: DisTrustsEdgeCreate):
    """
    File a distrust report against another user.

    **Guardrails applied**:
    - Must have had a prior accepted connection with this user
    - Max 3 reports per 30 days
    - Mutual reports are auto-flagged as disputes
    - Report is inactive until moderator review
    """
    try:
        return await edge_service.create_distrusts_edge(edge_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create DISTRUSTS edge error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/distrusts/activate")
async def activate_distrusts_edge(from_user_id: str, to_user_id: str):
    """Activate a distrust report after moderator review."""
    success = await edge_service.activate_distrusts_edge(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No DISTRUSTS edge found for this pair"
        )
    return {"message": "Distrust edge activated", "from_user_id": from_user_id, "to_user_id": to_user_id}

@router.delete("/distrusts")
async def delete_distrusts_edge(from_user_id: str, to_user_id: str):
    """Remove a distrust report (moderator dismissal or self-withdrawal before review)."""
    success = await edge_service.delete_distrusts_edge(from_user_id, to_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No DISTRUSTS edge found for this pair"
        )
    return {"message": "Distrust report removed"}

@router.get("/distrusts/by/{user_id}")
async def get_distrusts_by_user(user_id: str):
    """Get all distrust reports filed by a user."""
    reports = await edge_service.get_distrusts_by_user(user_id)
    return {"user_id": user_id, "reports_filed": reports, "count": len(reports)}

@router.get("/distrusts/for/{user_id}")
async def get_distrusts_for_user(user_id: str):
    """Get all active distrust reports targeting a user (moderator endpoint)."""
    reports = await edge_service.get_distrusts_for_user(user_id)
    return {"user_id": user_id, "reports_received": reports, "count": len(reports)}

# ========================================
# VOUCHES Routes
# ========================================

@router.post("/vouches", response_model=VouchResponse, status_code=status.HTTP_201_CREATED)
async def create_vouch(vouch_data: VouchCreate):
    """
    Vouch for another user in the network.

    **Guardrails applied**:
    - Max 5 vouches per day
    - Cannot vouch for someone you have an active distrust report against
    - One active vouch per direction per pair
    """
    try:
        return await edge_service.create_vouch(vouch_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create VOUCH error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/vouches/revoke")
async def revoke_vouch(voucher_id: str, target_user_id: str):
    """Revoke a previously given vouch."""
    success = await edge_service.revoke_vouch(voucher_id, target_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active vouch found for this pair"
        )
    return {"message": "Vouch revoked", "voucher_id": voucher_id, "target_user_id": target_user_id}

@router.get("/vouches/for/{user_id}")
async def get_vouches_for_user(user_id: str):
    """Get all active vouches received by a user."""
    vouches = await edge_service.get_vouches_for_user(user_id)
    return {"user_id": user_id, "vouches_received": vouches, "count": len(vouches)}

@router.get("/vouches/by/{user_id}")
async def get_vouches_by_user(user_id: str):
    """Get all vouches given by a user."""
    vouches = await edge_service.get_vouches_by_user(user_id)
    return {"user_id": user_id, "vouches_given": vouches, "count": len(vouches)}

# ========================================
# EigenTrust Admin Route
# ========================================

@router.post("/admin/eigen-trust-refresh")
async def trigger_eigen_trust_refresh():
    """Manually trigger EigenTrust rank recomputation across all users."""
    updated = await trust_scoring_service.compute_eigen_trust_ranks()
    return {"message": "EigenTrust ranks refreshed", "users_updated": updated}
