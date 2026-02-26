from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PathNode(BaseModel):
    """Represents a node in an intro path"""
    user_id: str
    name: str
    role: str
    reputation_score: float = Field(ge=0.0, le=1.0)

class IntroPath(BaseModel):
    """Represents a complete intro path from founder to investor"""
    nodes: List[PathNode]
    edges: List[Dict[str, Any]]
    hop_count: int
    path_score: float = Field(description="Aggregate trust-weighted score")
    success_probability: float = Field(description="Estimated success rate")
    explanation: str = Field(description="Human-readable path explanation")

class PathDiscoveryRequest(BaseModel):
    founder_id: str
    investor_id: str
    max_paths: int = Field(default=5, ge=1, le=20)
    domain_filter: Optional[str] = None

class PathDiscoveryResponse(BaseModel):
    founder_id: str
    investor_id: str
    paths: List[IntroPath]
    total_paths_found: int
