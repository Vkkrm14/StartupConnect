import logging
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query

from shared.auth.dependencies import get_current_user, CurrentUser
from app.schemas.conversation import (
    CreateConversationRequest,
    ConversationResponse,
    ConversationListResponse,
    BlockUserRequest,
    EncryptionKeyUpload,
    EncryptionKeyResponse,
    ParticipantInfo,
)
from app.services.conversation_service import conversation_service
from app.services.event_producer import event_producer
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.user_id == request.participant_id:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")

    is_blocked = await conversation_service.is_blocked(
        current_user.user_id, request.participant_id
    )
    if is_blocked:
        raise HTTPException(status_code=403, detail="Cannot create conversation with this user")

    # Verify the two users have an accepted mutual trust connection
    try:
        from app.core.config import settings as _settings
        async with httpx.AsyncClient(timeout=5.0) as _client:
            _resp = await _client.get(
                f"{_settings.GRAPH_SERVICE_URL}/api/v1/edges/trusts/connected"
                f"/{current_user.user_id}/{request.participant_id}"
            )
            if _resp.status_code == 200 and not _resp.json().get("is_connected", False):
                raise HTTPException(
                    status_code=403,
                    detail="You must be connected with this user to start a conversation",
                )
    except HTTPException:
        raise
    except Exception as _e:
        logger.warning(f"Could not verify connection status before conversation creation: {_e}")

    conv = await conversation_service.get_or_create_conversation(
        current_user.user_id, request.participant_id
    )
    await event_producer.emit_conversation_created(conv)
    return ConversationResponse(**conv)


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
):
    conversations = await conversation_service.get_user_conversations(
        current_user.user_id, skip=skip, limit=limit
    )
    total = await conversation_service.get_user_conversation_count(current_user.user_id)
    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in conversations],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    conv = await conversation_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(**conv)


@router.get("/{conversation_id}/presence")
async def get_conversation_presence(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    other = await conversation_service.get_other_participant(
        conversation_id, current_user.user_id
    )
    if not other:
        return {"user_id": None, "status": "unknown"}

    presence = await redis_manager.get_user_presence(other)
    typing_users = await redis_manager.get_typing_users(conversation_id)

    return {
        "user_id": other,
        "status": presence.get("status", "offline") if presence else "offline",
        "is_typing": other in typing_users,
    }


@router.post("/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_user(
    request: BlockUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    if current_user.user_id == request.blocked_user_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    await conversation_service.block_user(current_user.user_id, request.blocked_user_id)
    await event_producer.emit_user_blocked(current_user.user_id, request.blocked_user_id)


@router.delete("/block/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    await conversation_service.unblock_user(current_user.user_id, user_id)


@router.get("/block/list")
async def list_blocked_users(
    current_user: CurrentUser = Depends(get_current_user),
):
    blocked = await conversation_service.get_blocked_users(current_user.user_id)
    return {"blocked_users": blocked}


@router.put("/encryption-key", response_model=EncryptionKeyResponse)
async def upload_encryption_key(
    request: EncryptionKeyUpload,
    current_user: CurrentUser = Depends(get_current_user),
):
    await conversation_service.store_encryption_key(
        current_user.user_id, request.public_key, request.key_type
    )
    key_doc = await conversation_service.get_encryption_key(current_user.user_id)
    return EncryptionKeyResponse(**key_doc)


@router.get("/encryption-key/{user_id}", response_model=EncryptionKeyResponse)
async def get_encryption_key(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    key_doc = await conversation_service.get_encryption_key(user_id)
    if not key_doc:
        raise HTTPException(status_code=404, detail="Encryption key not found for user")
    return EncryptionKeyResponse(**key_doc)
