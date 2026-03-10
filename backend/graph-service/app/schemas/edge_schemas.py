from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class IntroStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"

class InvestmentRound(str, Enum):
    ANGEL = "angel"
    SEED = "seed"
    SERIES_A = "seriesA"
    SERIES_B = "seriesB"
    SERIES_C_PLUS = "seriesC+"

class InvestmentVisibility(str, Enum):
    PUBLIC = "public"
    TRUSTED_ONLY = "trusted_only"
    PRIVATE = "private"

# ========================================
# Base Edge Schema
# ========================================
class EdgeBase(BaseModel):
    """Common properties for all edges"""
    strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    recency_score: float = Field(default=1.0, ge=0.0, le=1.0)
    interaction_count: int = Field(default=0, ge=0)
    # trust_score is intentionally excluded — always computed server-side

# ========================================
# TRUSTS Edge
# ========================================
class TrustsEdgeCreate(EdgeBase):
    from_user_id: str
    to_user_id: str
    endorsement_count: int = Field(default=0, ge=0)
    domain_tags: List[str] = Field(default_factory=list)
    
    @field_validator('domain_tags')
    def validate_domain_tags(cls, v):
        return [tag.lower().strip() for tag in v]

class TrustsEdgeStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class TrustsEdgeResponse(EdgeBase):
    edge_id: str
    from_user_id: str
    to_user_id: str
    trust_score: float = Field(ge=0.0, le=1.0)  # server-computed; always present in responses
    endorsement_count: int
    domain_tags: List[str]
    successful_intros: int
    is_mutual: bool = False
    status: str = "pending"
    last_interaction_at: Optional[datetime]
    created_at: datetime

# ========================================
# FOUNDED Edge
# ========================================
class FoundedEdgeCreate(BaseModel):
    user_id: str
    startup_id: str
    role: str = Field(default="founder")  # founder / cofounder
    start_date: Optional[datetime] = None
    active: bool = True

class FoundedEdgeResponse(BaseModel):
    edge_id: str
    user_id: str
    startup_id: str
    role: str
    start_date: Optional[datetime]
    active: bool
    created_at: datetime

# ========================================
# INVESTED_IN Edge
# ========================================
class InvestedInEdgeCreate(BaseModel):
    investor_id: str
    startup_id: str
    round: InvestmentRound
    amount_range: Optional[str] = None  # e.g., "100K-500K"
    year: int = Field(..., ge=1900, le=2100)
    visibility: InvestmentVisibility = InvestmentVisibility.TRUSTED_ONLY

class InvestedInEdgeResponse(BaseModel):
    edge_id: str
    investor_id: str
    startup_id: str
    round: InvestmentRound
    amount_range: Optional[str]
    year: int
    visibility: InvestmentVisibility
    created_at: datetime

# ========================================
# MEMBER_OF Edge
# ========================================
class MemberOfEdgeCreate(BaseModel):
    user_id: str
    org_id: str
    role: str  # partner / scout / associate / member
    start_date: Optional[datetime] = None
    active: bool = True

class MemberOfEdgeResponse(BaseModel):
    edge_id: str
    user_id: str
    org_id: str
    role: str
    start_date: Optional[datetime]
    active: bool
    created_at: datetime
