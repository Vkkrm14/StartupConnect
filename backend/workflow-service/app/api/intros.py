from fastapi import APIRouter, HTTPException, Request, status
from datetime import datetime
import uuid
import logging
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
    
    intro_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    intro_doc = {
        "intro_id": intro_id,
        "requester_id": intro_data.requester_id,
        "founder_id": intro_data.founder_id,
        "investor_id": intro_data.investor_id,
        "path_nodes": intro_data.path_nodes,
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
        if notification_service and len(intro_data.path_nodes) > 0:
            try:
                await notification_service.send_intro_request_notification(
                    intro_id=intro_id,
                    requester_name=intro_data.requester_id,
                    target_name=intro_data.investor_id,
                    intermediary_id=intro_data.path_nodes[0],
                    message=intro_data.message
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
        
        return IntroRequestResponse(
            intro_id=intro_id,
            requester_id=intro_data.requester_id,
            founder_id=intro_data.founder_id,
            investor_id=intro_data.investor_id,
            path_nodes=intro_data.path_nodes,
            current_node_index=0,
            status=IntroStatus.PENDING,
            message=intro_data.message,
            created_at=now,
            updated_at=now
        )
    except Exception as e:
        logger.error(f"❌ Failed to create intro request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

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
    
    return IntroRequestResponse(
        intro_id=intro_doc["intro_id"],
        requester_id=intro_doc["requester_id"],
        founder_id=intro_doc["founder_id"],
        investor_id=intro_doc["investor_id"],
        path_nodes=intro_doc["path_nodes"],
        current_node_index=intro_doc["current_node_index"],
        status=intro_doc["status"],
        message=intro_doc["message"],
        created_at=intro_doc["created_at"],
        updated_at=intro_doc["updated_at"]
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
            return {"message": "Intro request completed!", "status": "completed"}
        else:
            return {
                "message": "Approval recorded, forwarded to next node",
                "next_approver": path_nodes[new_index]
            }
