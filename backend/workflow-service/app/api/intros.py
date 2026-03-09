from fastapi import APIRouter, HTTPException, Request, status
from datetime import datetime
from typing import Optional
import uuid
import logging
import httpx
import sys
sys.path.append("/app/shared")
from messaging.kafka_producer import KafkaEventProducer

from app.schemas.intro_schemas import (
    IntroRequestCreate,
    IntroRequestResponse,
    ApprovalAction,
    IntroStatus
)
from app.services.notification_service import notification_service
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── Name resolution helper ───────────────────────────────────────────────────
async def resolve_names(user_ids: list) -> dict:
    """Fetch display names for a list of user IDs from graph-service.
    Returns {user_id: name}. Missing IDs get a shortened ID as fallback."""
    names = {}
    unique_ids = list(set(uid for uid in user_ids if uid))
    async with httpx.AsyncClient(timeout=5.0) as client:
        for uid in unique_ids:
            try:
                r = await client.get(f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{uid}")
                if r.status_code == 200:
                    data = r.json()
                    names[uid] = data.get("name") or data.get("username") or uid[:8]
                else:
                    names[uid] = uid[:8]
            except Exception:
                names[uid] = uid[:8]
    return names


def _build_path_user_ids(intro_doc: dict) -> list:
    """
    Build the ordered list of user IDs along the full intro path:
      requester → path_nodes → investor

    This is passed as `path_user_ids` in the intro_completed Kafka event
    so that graph-service can increment successful_intros on each consecutive
    TRUSTS edge and recompute trust scores along the chain.
    """
    requester_id = intro_doc.get("requester_id", "")
    investor_id  = intro_doc.get("investor_id",  "")
    path_nodes   = intro_doc.get("path_nodes",   [])

    # Build ordered chain, deduplicated while preserving order
    full_path = [requester_id] + list(path_nodes) + [investor_id]
    seen = set()
    result = []
    for uid in full_path:
        if uid and uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result


def _expected_approver(intro_doc: dict) -> Optional[str]:
    path_nodes = intro_doc.get("path_nodes", [])
    current_index = intro_doc.get("current_node_index", 0)
    if 0 <= current_index < len(path_nodes):
        return path_nodes[current_index]
    return None


def _normalize_intermediary_nodes(
    requester_id: str,
    founder_id: str,
    investor_id: str,
    path_nodes: list,
) -> list:
    excluded_ids = {requester_id, founder_id, investor_id}
    result = []
    seen = set()
    for uid in path_nodes or []:
        if not uid or uid in excluded_ids or uid in seen:
            continue
        seen.add(uid)
        result.append(uid)
    return result


async def _publish_intro_completed_once(db, intro_doc: dict) -> None:
    intro_id = intro_doc["intro_id"]
    if intro_doc.get("completion_event_published_at"):
        logger.info(f"⏭️ intro_completed already published for {intro_id}")
        return

    if not kafka_producer:
        logger.warning(f"⚠️ Kafka producer unavailable; intro_completed not published for {intro_id}")
        return

    path_user_ids = _build_path_user_ids(intro_doc)
    await kafka_producer.publish_event(
        topic="intro-events",
        event_type="intro_completed",
        data={
            "intro_id": intro_id,
            "path_user_ids": path_user_ids,
            "requester_id": intro_doc.get("requester_id"),
            "investor_id": intro_doc.get("investor_id"),
            "founder_id": intro_doc.get("founder_id"),
        },
        key=intro_id
    )
    published_at = datetime.utcnow()
    await db.intro_requests.update_one(
        {"intro_id": intro_id},
        {"$set": {"completion_event_published_at": published_at, "updated_at": published_at}}
    )
    intro_doc["completion_event_published_at"] = published_at
    logger.info(f"✅ Published intro_completed for {intro_id} (path: {path_user_ids})")


async def _ensure_direct_trust_connection(requester_id: str, investor_id: str, domain_tags: list) -> None:
    if not requester_id or not investor_id:
        return

    async with httpx.AsyncClient(timeout=5.0) as client:
        for from_user_id, to_user_id in (
            (requester_id, investor_id),
            (investor_id, requester_id),
        ):
            create_response = await client.post(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts",
                json={
                    "from_user_id": from_user_id,
                    "to_user_id": to_user_id,
                    "strength_score": 0.7,
                    "domain_tags": domain_tags,
                }
            )
            if create_response.status_code not in (200, 201, 400):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to create direct trust edge {from_user_id}->{to_user_id}"
                )

            accept_response = await client.put(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/accept",
                params={"from_user_id": from_user_id, "to_user_id": to_user_id}
            )
            if accept_response.status_code not in (200, 404):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to activate direct trust edge {from_user_id}->{to_user_id}"
                )

    logger.info(f"✅ Direct TRUSTS connection ensured between {requester_id} ↔ {investor_id}")
# ──────────────────────────────────────────────────────────────────────────────

# Initialize Kafka producer
kafka_producer = None
if settings.KAFKA_BOOTSTRAP_SERVERS:
    try:
        kafka_producer = KafkaEventProducer(settings.KAFKA_BOOTSTRAP_SERVERS)
        kafka_producer.connect()
        logger.info("✅ Kafka producer connected")
    except Exception as e:
        logger.warning(f"⚠️ Kafka not available: {e}")

@router.post("/", response_model=IntroRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_intro_request(request: Request, intro_data: IntroRequestCreate):
    """
    Create a new intro request
    
    **Workflow**:
    1. Requester initiates intro with path
    2. Each intermediary must approve
    3. Forward to next node upon approval
    4. Final node connects to investor
    """
    db = request.app.state.db
    normalized_path_nodes = _normalize_intermediary_nodes(
        requester_id=intro_data.requester_id,
        founder_id=intro_data.founder_id,
        investor_id=intro_data.investor_id,
        path_nodes=intro_data.path_nodes,
    )

    if not normalized_path_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intro request requires at least one intermediary in the selected path"
        )
    
    intro_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    intro_doc = {
        "intro_id": intro_id,
        "requester_id": intro_data.requester_id,
        "founder_id": intro_data.founder_id,
        "investor_id": intro_data.investor_id,
        "path_nodes": normalized_path_nodes,
        "current_node_index": 0,
        "status": IntroStatus.PENDING.value,
        "message": intro_data.message,
        "domain": intro_data.domain,
        "approvals": [],
        "created_at": now,
        "updated_at": now
    }
    
    try:
        await db.intro_requests.insert_one(intro_doc)
        logger.info(f"✅ Created intro request: {intro_id}")
        
        # Publish intro_created event
        if kafka_producer:
            try:
                await kafka_producer.publish_event(
                    topic="intro-events",
                    event_type="intro_created",
                    data={
                        "intro_id": intro_id,
                        "requester_id": intro_data.requester_id,
                        "founder_id": intro_data.founder_id,
                        "investor_id": intro_data.investor_id,
                        "path_nodes": intro_data.path_nodes,
                        "domain": intro_data.domain
                    },
                    key=intro_id
                )
            except Exception as e:
                logger.warning(f"Failed to publish intro_created event: {e}")
        
        # Send notification to first intermediary
        if notification_service and len(normalized_path_nodes) > 0:
            try:
                await notification_service.send_intro_request_notification(
                    intro_id=intro_id,
                    requester_name=intro_data.requester_id,
                    target_name=intro_data.investor_id,
                    intermediary_id=normalized_path_nodes[0],
                    message=intro_data.message
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
        
        all_ids = list(set([intro_data.requester_id, intro_data.founder_id, intro_data.investor_id] + normalized_path_nodes))
        names = await resolve_names(all_ids)

        return IntroRequestResponse(
            intro_id=intro_id,
            requester_id=intro_data.requester_id,
            founder_id=intro_data.founder_id,
            investor_id=intro_data.investor_id,
            path_nodes=normalized_path_nodes,
            current_node_index=0,
            status=IntroStatus.PENDING,
            message=intro_data.message,
            created_at=now,
            updated_at=now,
            requester_name=names.get(intro_data.requester_id),
            founder_name=names.get(intro_data.founder_id),
            investor_name=names.get(intro_data.investor_id),
            path_node_names=[names.get(uid, uid[:8]) for uid in normalized_path_nodes],
        )
    except Exception as e:
        logger.error(f"❌ Failed to create intro request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/user/{user_id}")
async def get_user_intro_requests(request: Request, user_id: str):
    """Get all intro requests involving a user (as requester, founder, or investor)"""
    db = request.app.state.db

    docs = await db.intro_requests.find({
        "$or": [
            {"requester_id": user_id},
            {"founder_id": user_id},
            {"investor_id": user_id}
        ]
    }).sort("created_at", -1).to_list(length=100)

    # Collect all unique user IDs across docs for a single batch resolve
    all_ids = set()
    for doc in docs:
        all_ids.update([doc["requester_id"], doc["founder_id"], doc["investor_id"]] + doc.get("path_nodes", []))
    names = await resolve_names(list(all_ids))

    result = []
    for doc in docs:
        path_nodes = doc.get("path_nodes", [])
        result.append({
            "intro_id": doc["intro_id"],
            "requester_id": doc["requester_id"],
            "founder_id": doc["founder_id"],
            "investor_id": doc["investor_id"],
            "path_nodes": path_nodes,
            "current_node_index": doc.get("current_node_index", 0),
            "status": doc["status"],
            "message": doc.get("message", ""),
            "created_at": doc["created_at"].isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
            "updated_at": doc["updated_at"].isoformat() if hasattr(doc.get("updated_at"), "isoformat") else str(doc.get("updated_at", "")),
            "requester_name": names.get(doc["requester_id"]),
            "founder_name": names.get(doc["founder_id"]),
            "investor_name": names.get(doc["investor_id"]),
            "path_node_names": [names.get(uid, uid[:8]) for uid in path_nodes],
        })

    return {"intro_requests": result}


@router.get("/pending/{user_id}")
async def get_pending_approvals(request: Request, user_id: str):
    """Get intro requests pending the user's approval (user is next in path_nodes)"""
    db = request.app.state.db

    docs = await db.intro_requests.find({
        "path_nodes": user_id,
        "status": {"$in": [IntroStatus.PENDING.value, IntroStatus.APPROVED.value]}
    }).sort("created_at", -1).to_list(length=100)

    # Collect all unique IDs for batch resolution
    all_ids = set()
    for doc in docs:
        all_ids.update([doc["requester_id"], doc["founder_id"], doc["investor_id"]] + doc.get("path_nodes", []))
    names = await resolve_names(list(all_ids))

    # Filter to only those where user_id is the current node awaiting action
    result = []
    for doc in docs:
        current_index = doc.get("current_node_index", 0)
        path_nodes = doc.get("path_nodes", [])
        if current_index < len(path_nodes) and path_nodes[current_index] == user_id:
            result.append({
                "intro_id": doc["intro_id"],
                "requester_id": doc["requester_id"],
                "founder_id": doc["founder_id"],
                "investor_id": doc["investor_id"],
                "path_nodes": path_nodes,
                "current_node_index": current_index,
                "status": doc["status"],
                "message": doc.get("message", ""),
                "created_at": doc["created_at"].isoformat() if hasattr(doc.get("created_at"), "isoformat") else str(doc.get("created_at", "")),
                "updated_at": doc["updated_at"].isoformat() if hasattr(doc.get("updated_at"), "isoformat") else str(doc.get("updated_at", "")),
                "requester_name": names.get(doc["requester_id"]),
                "founder_name": names.get(doc["founder_id"]),
                "investor_name": names.get(doc["investor_id"]),
                "path_node_names": [names.get(uid, uid[:8]) for uid in path_nodes],
            })

    return {"pending_intros": result}


@router.post("/{intro_id}/approve")
async def approve_intro_by_id(request: Request, intro_id: str):
    """Approve an intro request (user_id in body)"""
    db = request.app.state.db
    body = await request.json()
    user_id = body.get("user_id") or body.get("approver_id")
    message = body.get("message") or body.get("comment", "")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approver_id is required")

    intro_doc = await db.intro_requests.find_one({"intro_id": intro_id})
    if not intro_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Intro {intro_id} not found")

    current_index = intro_doc.get("current_node_index", 0)
    path_nodes = intro_doc.get("path_nodes", [])
    expected_approver = _expected_approver(intro_doc)

    if expected_approver is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intro has no pending approver"
        )

    if user_id != expected_approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to approve this step"
        )

    new_index = current_index + 1
    chain_complete = new_index >= len(path_nodes)
    new_status = IntroStatus.COMPLETED.value if chain_complete else IntroStatus.APPROVED.value

    await db.intro_requests.update_one(
        {"intro_id": intro_id},
        {
            "$set": {"current_node_index": new_index, "status": new_status, "updated_at": datetime.utcnow()},
            "$push": {"approvals": {"approver_id": user_id, "action": "accept", "comment": message, "timestamp": datetime.utcnow()}}
        }
    )
    logger.info(f"✅ Intro {intro_id} approved by {user_id}")
    if chain_complete:
        requester_id = intro_doc.get("requester_id")
        investor_id  = intro_doc.get("investor_id")
        domain_tags  = (
            intro_doc.get("domain", [])
            if isinstance(intro_doc.get("domain"), list)
            else ([intro_doc["domain"]] if intro_doc.get("domain") else [])
        )
        await _ensure_direct_trust_connection(requester_id, investor_id, domain_tags)
        await _publish_intro_completed_once(db, intro_doc)
        return {"message": "Introduction fully approved by all parties!", "status": "completed"}
    return {"message": "Approval recorded, forwarded to next node", "next_approver": path_nodes[new_index] if new_index < len(path_nodes) else None}


@router.post("/{intro_id}/decline")
async def decline_intro_by_id(request: Request, intro_id: str):
    """Decline an intro request (user_id in body)"""
    db = request.app.state.db
    body = await request.json()
    user_id = body.get("user_id") or body.get("approver_id")
    message = body.get("message") or body.get("comment", "")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approver_id is required")

    intro_doc = await db.intro_requests.find_one({"intro_id": intro_id})
    if not intro_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Intro {intro_id} not found")

    expected_approver = _expected_approver(intro_doc)
    if expected_approver is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intro has no pending approver"
        )

    if user_id != expected_approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to decline this step"
        )

    await db.intro_requests.update_one(
        {"intro_id": intro_id},
        {
            "$set": {"status": IntroStatus.DECLINED.value, "updated_at": datetime.utcnow()},
            "$push": {"approvals": {"approver_id": user_id, "action": "decline", "comment": message, "timestamp": datetime.utcnow()}}
        }
    )
    logger.info(f"❌ Intro {intro_id} declined by {user_id}")
    return {"message": "Intro request declined"}


@router.post("/{intro_id}/complete")
async def complete_intro_by_id(request: Request, intro_id: str):
    """Mark an intro request as completed"""
    db = request.app.state.db

    intro_doc = await db.intro_requests.find_one({"intro_id": intro_id})
    if not intro_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Intro {intro_id} not found")

    if intro_doc.get("status") != IntroStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intro cannot be force-completed before all approvals are finished"
        )

    await db.intro_requests.update_one(
        {"intro_id": intro_id},
        {"$set": {"status": IntroStatus.COMPLETED.value, "updated_at": datetime.utcnow()}}
    )
    logger.info(f"✅ Intro {intro_id} marked as completed")

    await _publish_intro_completed_once(db, intro_doc)

    return {"message": "Intro request completed"}


@router.get("/{intro_id}", response_model=IntroRequestResponse)
async def get_intro_request(request: Request, intro_id: str):
    """Get intro request by ID"""
    db = request.app.state.db
    
    intro_doc = await db.intro_requests.find_one({"intro_id": intro_id})
    
    if not intro_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intro request {intro_id} not found"
        )
    
    path_nodes = intro_doc["path_nodes"]
    all_ids = list(set([intro_doc["requester_id"], intro_doc["founder_id"], intro_doc["investor_id"]] + path_nodes))
    names = await resolve_names(all_ids)

    return IntroRequestResponse(
        intro_id=intro_doc["intro_id"],
        requester_id=intro_doc["requester_id"],
        founder_id=intro_doc["founder_id"],
        investor_id=intro_doc["investor_id"],
        path_nodes=path_nodes,
        current_node_index=intro_doc["current_node_index"],
        status=intro_doc["status"],
        message=intro_doc["message"],
        created_at=intro_doc["created_at"],
        updated_at=intro_doc["updated_at"],
        requester_name=names.get(intro_doc["requester_id"]),
        founder_name=names.get(intro_doc["founder_id"]),
        investor_name=names.get(intro_doc["investor_id"]),
        path_node_names=[names.get(uid, uid[:8]) for uid in path_nodes],
    )

@router.post("/approve")
async def approve_or_decline_intro(request: Request, action: ApprovalAction):
    """
    Approve or decline an intro request
    
    **State Machine**:
    - Accept → Forward to next node or mark completed
    - Decline → Mark as declined, notify requester
    """
    db = request.app.state.db
    
    intro_doc = await db.intro_requests.find_one({"intro_id": action.intro_id})
    
    if not intro_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intro request {action.intro_id} not found"
        )
    
    # Verify approver is current node
    current_index = intro_doc["current_node_index"]
    path_nodes = intro_doc["path_nodes"]
    
    if current_index >= len(path_nodes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intro already completed"
        )
    
    expected_approver = path_nodes[current_index]
    
    if action.approver_id != expected_approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not authorized to approve this step"
        )
    
    # Process action
    if action.action == "decline":
        # Mark as declined
        await db.intro_requests.update_one(
            {"intro_id": action.intro_id},
            {
                "$set": {
                    "status": IntroStatus.DECLINED.value,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "approvals": {
                        "approver_id": action.approver_id,
                        "action": "decline",
                        "comment": action.comment,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )
        
        logger.info(f"❌ Intro {action.intro_id} declined by {action.approver_id}")
        return {"message": "Intro request declined"}
    
    elif action.action == "accept":
        # Move to next node
        new_index = current_index + 1
        
        if new_index >= len(path_nodes):
            # Completed!
            new_status = IntroStatus.COMPLETED.value
        else:
            new_status = IntroStatus.APPROVED.value
        
        await db.intro_requests.update_one(
            {"intro_id": action.intro_id},
            {
                "$set": {
                    "current_node_index": new_index,
                    "status": new_status,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "approvals": {
                        "approver_id": action.approver_id,
                        "action": "accept",
                        "comment": action.comment,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )
        
        logger.info(f"✅ Intro {action.intro_id} approved by {action.approver_id}")
        
        if new_status == IntroStatus.COMPLETED.value:
            requester_id = intro_doc.get("requester_id")
            investor_id = intro_doc.get("investor_id")
            domain_tags = (
                intro_doc.get("domain", [])
                if isinstance(intro_doc.get("domain"), list)
                else ([intro_doc["domain"]] if intro_doc.get("domain") else [])
            )
            await _ensure_direct_trust_connection(requester_id, investor_id, domain_tags)
            await _publish_intro_completed_once(db, intro_doc)
            return {"message": "Intro request completed!", "status": "completed"}
        else:
            return {
                "message": "Approval recorded, forwarded to next node",
                "next_approver": path_nodes[new_index]
            }
