from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    URL = "url"


class SendMessageRequest(BaseModel):
    conversation_id: str
    encrypted_payload: str = Field(..., description="Base64-encoded encrypted content")
    encrypted_key: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    sender_id: str
    encrypted_payload: str
    encrypted_key: Optional[str] = None
    message_type: str
    metadata: Optional[dict] = None
    created_at: datetime


class MessagePageResponse(BaseModel):
    messages: List[MessageResponse]
    conversation_id: str
    has_more: bool
    next_cursor: Optional[str] = None


class ReadReceiptRequest(BaseModel):
    conversation_id: str
    message_id: str


class TypingIndicatorRequest(BaseModel):
    conversation_id: str
    is_typing: bool
