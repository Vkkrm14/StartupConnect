from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    FOUNDER = "founder"
    INVESTOR = "investor"
    OPERATOR = "operator"
    CONNECTOR = "connector"

class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"

class StartupStage(str, Enum):
    IDEA = "idea"
    MVP = "mvp"
    SEED = "seed"
    SERIES_A = "seriesA"
    SERIES_B = "seriesB"
    SERIES_C_PLUS = "seriesC+"

class VisibilityLevel(str, Enum):
    PUBLIC = "public"
    TRUSTED_ONLY = "trusted_only"
    PRIVATE = "private"

class OrgType(str, Enum):
    VC = "vc"
    ACCELERATOR = "accelerator"
    INCUBATOR = "incubator"
    ANGEL_NETWORK = "angel_network"
    LAW_FIRM = "law_firm"

# ========================================
# User Vertex Schema
# ========================================
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    password_hash: Optional[str] = None
    role_primary: UserRole
    roles_secondary: List[UserRole] = []
    domain_tags: List[str] = Field(default_factory=list)
    geography: Optional[str] = None
    experience_years: int = Field(default=0, ge=0)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    
    @field_validator('domain_tags')
    def validate_domain_tags(cls, v):
        return [tag.lower().strip() for tag in v]

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: Optional[str] = None
    password_hash: Optional[str] = None
    role_primary: UserRole
    roles_secondary: List[UserRole]
    domain_tags: List[str]
    geography: Optional[str]
    experience_years: int
    reputation_score: float
    verification_status: VerificationStatus
    created_at: datetime

# ========================================
# Startup Vertex Schema
# ========================================
class StartupCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: str
    stage: StartupStage
    geography: Optional[str] = None
    founded_year: Optional[int] = Field(None, ge=1900, le=2100)
    funding_status: Optional[str] = None
    employee_count: Optional[int] = Field(None, ge=0)
    visibility_level: VisibilityLevel = VisibilityLevel.PUBLIC

class StartupResponse(BaseModel):
    startup_id: str
    name: str
    domain: str
    stage: StartupStage
    geography: Optional[str]
    founded_year: Optional[int]
    funding_status: Optional[str]
    employee_count: Optional[int]
    visibility_level: VisibilityLevel
    created_at: datetime

# ========================================
# Organization Vertex Schema
# ========================================
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: OrgType
    geography: Optional[str] = None
    domains: List[str] = Field(default_factory=list)
    website: Optional[str] = None

class OrganizationResponse(BaseModel):
    org_id: str
    name: str
    type: OrgType
    geography: Optional[str]
    domains: List[str]
    website: Optional[str]
    created_at: datetime
