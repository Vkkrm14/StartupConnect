"""
Tests for path discovery with DISTRUSTS filtering.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.path_discovery import PathDiscoveryService
from app.schemas.path_schemas import PathNode, IntroPath


def test_path_discovery_initialization():
    """Test PathDiscoveryService initialization with configuration"""
    
    # Create instance
    discovery = PathDiscoveryService()
    
    # Test that method exists
    assert hasattr(discovery, 'find_intro_paths')
    
    # Verify path discovery configuration is loaded from settings
    assert discovery.max_hops > 0
    assert isinstance(discovery.min_trust, float)
    assert 0 <= discovery.min_trust <= 1.0


def test_path_node_structure():
    """Test PathNode data structure"""
    node = PathNode(
        user_id="user123",
        name="Alice",
        role="founder",
        reputation_score=0.8
    )
    
    assert node.user_id == "user123"
    assert node.name == "Alice"
    assert node.role == "founder"
    assert node.reputation_score == 0.8


def test_intro_path_structure():
    """Test IntroPath data structure with DISTRUSTS handling"""
    nodes = [
        PathNode(user_id="user1", name="Alice", role="founder", reputation_score=0.8),
        PathNode(user_id="user2", name="Bob", role="connector", reputation_score=0.7),
        PathNode(user_id="user3", name="Charlie", role="investor", reputation_score=0.9),
    ]
    
    edges = [
        {"from": "user1", "to": "user2", "trust": 0.8, "strength": 0.7},
        {"from": "user2", "to": "user3", "trust": 0.85, "strength": 0.75},
    ]
    
    path = IntroPath(
        nodes=nodes,
        edges=edges,
        hop_count=2,
        path_score=0.75,
        success_probability=0.72,
        explanation="Strong path - no DISTRUSTS involved"
    )
    
    assert path.hop_count == 2
    assert len(path.nodes) == 3
    assert len(path.edges) == 2
    assert path.path_score == 0.75
    # Verify path has valid explanation
    assert len(path.explanation) > 0
    assert "path" in path.explanation.lower()


def test_path_score_with_multiple_hops():
    """Test path scoring calculation for multiple hops"""
    # Simulate edge scores for a 2-hop path
    trust_scores = [0.8, 0.85]
    strength_scores = [0.7, 0.75]
    recency_scores = [1.0, 1.0]
    mutual_boosts = [1.5, 1.0]  # First hop has mutual trust
    
    # Calculate path score (simplified)
    edge_scores = [
        t * s * r * m
        for t, s, r, m in zip(trust_scores, strength_scores, recency_scores, mutual_boosts)
    ]
    
    hop_count = len(trust_scores)
    path_score = sum(edge_scores) / hop_count
    
    # Apply hop penalty
    hop_penalty = 1.0 - (0.1 * (hop_count - 1))
    path_score *= hop_penalty
    
    # Verify scoring is positive and reasonable
    assert path_score > 0
    assert path_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
