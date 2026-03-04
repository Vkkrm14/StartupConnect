from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateConversationRequest(BaseModel):
    participant_id: str = Field(..., description="The other user to start a conversation with")


class ParticipantInfo(BaseModel):
    """Participant information for conversations"""
    user_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    participants: List[str]
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_type: Optional[str] = None
    # Participant info (populated when fetching conversations)
    participant_info: Optional[ParticipantInfo] = None


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class BlockUserRequest(BaseModel):
    blocked_user_id: str


class EncryptionKeyUpload(BaseModel):
    public_key: str
    key_type: str = "x25519"


class EncryptionKeyResponse(BaseModel):
    user_id: str
    public_key: str
    key_type: str
    updated_at: datetime
