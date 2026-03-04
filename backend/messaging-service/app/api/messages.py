import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from shared.auth.dependencies import get_current_user, CurrentUser
from app.schemas.message import (
    SendMessageRequest,
    MessageResponse,
    MessagePageResponse,
    ReadReceiptRequest,
    TypingIndicatorRequest,
)
from app.services.message_service import message_service
from app.services.conversation_service import conversation_service
from app.services.event_producer import event_producer
from app.core.redis import redis_manager
from app.core.config import settings
from app.api.websocket import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@router.post("/send", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        request.conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    recipient = await conversation_service.get_other_participant(
        request.conversation_id, current_user.user_id
    )
    if recipient and await conversation_service.is_blocked(current_user.user_id, recipient):
        raise HTTPException(status_code=403, detail="Cannot send message to this user")

    allowed = await redis_manager.check_rate_limit(
        current_user.user_id, settings.RATE_LIMIT_MESSAGES_PER_MINUTE
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if len(request.encrypted_payload) > settings.MAX_MESSAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Message too large")

    message = await message_service.store_message(
        conversation_id=request.conversation_id,
        sender_id=current_user.user_id,
        encrypted_payload=request.encrypted_payload,
        message_type=request.message_type.value,
        encrypted_key=request.encrypted_key,
        metadata=request.metadata,
    )

    await conversation_service.update_last_message(
        conversation_id=request.conversation_id,
        message_type=request.message_type.value,
        timestamp=datetime.utcnow(),
        preview=f"[{request.message_type.value}]",
    )

    outbound = {"event": "new_message", **message}
    await connection_manager.send_to_user(current_user.user_id, outbound)
    if recipient:
        await connection_manager.send_to_user(recipient, outbound)

    await event_producer.emit_message_sent(message)
    return MessageResponse(**message)


@router.get("/{conversation_id}", response_model=MessagePageResponse)
async def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: Optional[str] = Query(default=None, description="ISO timestamp cursor"),
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    messages, has_more = await message_service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        before=before,
    )

    next_cursor = None
    if has_more and messages:
        next_cursor = messages[-1]["created_at"]

    return MessagePageResponse(
        messages=messages,
        conversation_id=conversation_id,
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.post("/read-receipt", status_code=status.HTTP_204_NO_CONTENT)
async def send_read_receipt(
    request: ReadReceiptRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        request.conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    recipient = await conversation_service.get_other_participant(
        request.conversation_id, current_user.user_id
    )
    if recipient:
        await connection_manager.send_to_user(
            recipient,
            {
                "event": "read_receipt",
                "conversation_id": request.conversation_id,
                "message_id": request.message_id,
                "reader_id": current_user.user_id,
                "read_at": datetime.utcnow().isoformat(),
            },
        )
    await event_producer.emit_message_read(
        request.conversation_id, current_user.user_id, request.message_id
    )


@router.post("/typing", status_code=status.HTTP_204_NO_CONTENT)
async def typing_indicator(
    request: TypingIndicatorRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        request.conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    if request.is_typing:
        await redis_manager.set_typing(current_user.user_id, request.conversation_id)
    else:
        await redis_manager.clear_typing(current_user.user_id, request.conversation_id)

    recipient = await conversation_service.get_other_participant(
        request.conversation_id, current_user.user_id
    )
    if recipient:
        event_name = "typing" if request.is_typing else "stop_typing"
        await connection_manager.send_to_user(
            recipient,
            {
                "event": event_name,
                "conversation_id": request.conversation_id,
                "user_id": current_user.user_id,
            },
        )
