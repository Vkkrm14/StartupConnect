from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class IntroStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    COMPLETED = "completed"
    FAILED = "failed"

class IntroRequestCreate(BaseModel):
    requester_id: str
    founder_id: str
    investor_id: str
    path_nodes: List[str]  # User IDs in the intro path
    message: str = Field(..., min_length=10, max_length=1000)
    domain: Optional[str] = None

class IntroRequestResponse(BaseModel):
    intro_id: str
    requester_id: str
    founder_id: str
    investor_id: str
    path_nodes: List[str]
    current_node_index: int
    status: IntroStatus
    message: str
    created_at: datetime
    updated_at: datetime

class ApprovalAction(BaseModel):
    intro_id: str
    approver_id: str
    action: str = Field(..., pattern="^(accept|decline)$")
    comment: Optional[str] = None
