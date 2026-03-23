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
    trust_score: float = Field(
        default=0.5,
        ge=-1.0,
        le=1.0,
        description="Trust score: -1.0 (distrust) to 1.0 (high trust), 0.0 (neutral)"
    )
    strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    recency_score: float = Field(default=1.0, ge=0.0, le=1.0)
    interaction_count: int = Field(default=0, ge=0)

# ========================================
# TRUSTS Edge
# ========================================
class TrustsEdgeCreate(EdgeBase):
    """Create TRUSTS edge with optional negative trust (distrust) scores"""
    from_user_id: str
    to_user_id: str
    endorsement_count: int = Field(default=0, ge=0)
    domain_tags: List[str] = Field(default_factory=list)
    # Per-domain trust scores, e.g. {"ai": 0.8, "fintech": 0.6}
    # Supports negative values for domain-specific distrust
    domain_trust_scores: Optional[dict] = Field(default_factory=dict)

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
    endorsement_count: int
    domain_tags: List[str]
    successful_intros: int
    is_mutual: bool = False
    status: str = "pending"
    suspicion_flag: bool = False
    last_interaction_at: Optional[datetime]
    created_at: datetime
    # Negative trust indicator
    has_distrust_override: bool = False  # True if DISTRUSTS edge overrides this

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

# ========================================
# DISTRUSTS Edge
# ========================================
class DisTrustsReasonCategory(str, Enum):
    FRAUD = "fraud"
    UNRELIABLE_COLLABORATOR = "unreliable_collaborator"
    HARASSMENT = "harassment"
    DISPUTE = "dispute"

class DisTrustsEdgeCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    reason_category: DisTrustsReasonCategory
    severity: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Severity of distrust (0.0=mild, 1.0=extreme)"
    )
    # Evidence notes are stored but only visible to moderators
    evidence_notes: Optional[str] = Field(default=None, max_length=1000)

class DisTrustsEdgeResponse(BaseModel):
    edge_id: str
    from_user_id: str
    to_user_id: str
    distrust_score: float = Field(
        ge=-1.0,
        le=-0.0,
        description="Negative trust score (-1.0 to -0.0)"
    )
    reason_category: DisTrustsReasonCategory
    severity: float
    is_active: bool           # False until moderator review passes
    is_disputed: bool
    dispute_count: int = 0
    moderator_reviewed: bool
    created_at: datetime
    expires_at: datetime      # created_at + 365 days
    # Conflict resolution fields
    appeal_reason: Optional[str] = None         # Reason for disputing the DISTRUSTS
    resolution_type: Optional[str] = None       # mutual_resolution, invalid, mediated, expired
    resolved_at: Optional[datetime] = None      # When dispute was resolved

# ========================================
# VOUCHES Edge
# ========================================
class VouchCreate(BaseModel):
    voucher_id: str
    target_user_id: str
    vouch_strength: float = Field(default=0.7, ge=0.0, le=1.0)
    domain_tags: List[str] = Field(default_factory=list)

    @field_validator('domain_tags')
    def validate_domain_tags(cls, v):
        return [tag.lower().strip() for tag in v]

class VouchResponse(BaseModel):
    edge_id: str
    voucher_id: str
    target_user_id: str
    vouch_strength: float
    domain_tags: List[str]
    is_revoked: bool
    created_at: datetime
