from gremlin_python.process.traversal import P, Order
from gremlin_python.process.graph_traversal import __
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.core.graph_client import graph_client
from app.core.config import settings
from app.schemas.path_schemas import IntroPath, PathNode

logger = logging.getLogger(__name__)

class PathDiscoveryService:
    """
    Core pathfinding engine for discovering intro paths from Founder to Investor
    with trust-weighted scoring and mutual trust prioritization.
    """
    
    def __init__(self):
        self.max_hops = settings.MAX_INTRO_PATH_HOPS
        self.min_trust = settings.MIN_TRUST_SCORE
    
    async def find_intro_paths(
        self,
        founder_id: str,
        investor_id: str,
        max_paths: int = 5,
        domain_filter: Optional[str] = None
    ) -> List[IntroPath]:
        """
        Find top N intro paths from founder to investor.
        
        Algorithm:
        1. Traverse TRUSTS edges up to MAX_HOPS (default: 4)
        2. Filter by min trust score
        3. Prioritize mutual trust (bidirectional TRUSTS)
        4. Score paths by: trust × strength × recency × mutual_boost
        5. Return top N ranked paths
        """
        g = graph_client.get_traversal()
        
        try:
            # Find all paths within hop constraint
            paths_data = (
                g.V().has('User', 'user_id', founder_id)
                .repeat(
                    __.out('TRUSTS')
                    .simplePath()  # Avoid cycles
                )
                .until(
                    __.or_(
                        __.has('User', 'user_id', investor_id),
                        __.loops().is_(P.gte(self.max_hops))
                    )
                )
                .has('User', 'user_id', investor_id)
                .path()
                .by(__.valueMap(True))
                .limit(50)  # Get more candidates for scoring
                .toList()
            )
            
            if not paths_data:
                logger.info(f"No paths found from {founder_id} to {investor_id}")
                return []
            
            # Score and rank paths
            scored_paths = []
            for path_data in paths_data:
                intro_path = await self._score_path(path_data, domain_filter)
                if intro_path:
                    scored_paths.append(intro_path)
            
            # Sort by path score (descending)
            scored_paths.sort(key=lambda x: x.path_score, reverse=True)
            
            logger.info(
                f"Found {len(scored_paths)} valid paths from {founder_id} to {investor_id}"
            )
            
            return scored_paths[:max_paths]
            
        except Exception as e:
            logger.error(f"Path discovery error: {str(e)}")
            raise
    
    async def _score_path(
        self,
        path_data: List[Dict],
        domain_filter: Optional[str] = None
    ) -> Optional[IntroPath]:
        """
        Score a single path based on trust-weighted metrics.
        
        Scoring formula:
        path_score = Σ(trust × strength × recency × mutual_boost) / hop_count
        
        mutual_boost = 1.5 if bidirectional trust exists, else 1.0
        """
        nodes = []
        edges = []
        trust_scores = []
        recency_scores = []
        mutual_boosts = []
        
        g = graph_client.get_traversal()
        
        for i, vertex_data in enumerate(path_data):
            # Extract vertex properties
            node = PathNode(
                user_id=vertex_data.get('user_id', [''])[0],
                name=vertex_data.get('name', ['Unknown'])[0],
                role=vertex_data.get('role_primary', [''])[0],
                reputation_score=float(vertex_data.get('reputation_score', [0.5])[0])
            )
            nodes.append(node)
            
            # Get edge data between consecutive nodes
            if i > 0:
                from_id = nodes[i-1].user_id
                to_id = node.user_id
                
                # Query edge properties
                edge_props = (
                    g.V().has('User', 'user_id', from_id)
                    .outE('TRUSTS')
                    .where(__.inV().has('User', 'user_id', to_id))
                    .valueMap(True)
                    .next()
                )
                
                trust_score = float(edge_props.get('trust_score', [0.5])[0])
                strength_score = float(edge_props.get('strength_score', [0.5])[0])
                recency_score = float(edge_props.get('recency_score', [1.0])[0])
                
                # Check for mutual trust (bidirectional)
                mutual_exists = (
                    g.V().has('User', 'user_id', to_id)
                    .outE('TRUSTS')
                    .where(__.inV().has('User', 'user_id', from_id))
                    .hasNext()
                )
                
                mutual_boost = 1.5 if mutual_exists else 1.0
                
                # Domain relevance check
                if domain_filter:
                    domain_tags = edge_props.get('domain_tags', [])
                    if domain_filter.lower() not in [d.lower() for d in domain_tags]:
                        # Reduce score if domain doesn't match
                        trust_score *= 0.7
                
                # Store for aggregation
                trust_scores.append(trust_score)
                recency_scores.append(recency_score)
                mutual_boosts.append(mutual_boost)
                
                edges.append({
                    'from': from_id,
                    'to': to_id,
                    'trust': trust_score,
                    'strength': strength_score,
                    'recency': recency_score,
                    'mutual': mutual_exists
                })
        
        # Filter out low-trust paths
        if any(t < self.min_trust for t in trust_scores):
            return None
        
        # Calculate aggregate path score
        hop_count = len(nodes) - 1
        
        if hop_count == 0:
            return None
        
        # Weighted average with mutual trust boosting
        edge_scores = [
            t * r * m 
            for t, r, m in zip(trust_scores, recency_scores, mutual_boosts)
        ]
        
        path_score = sum(edge_scores) / hop_count
        
        # Apply hop penalty (shorter paths are better)
        hop_penalty = 1.0 - (0.1 * (hop_count - 1))
        path_score *= max(hop_penalty, 0.6)
        
        # Calculate success probability (simplified model)
        # Real implementation would use ML model trained on historical intro outcomes
        base_success = 0.5
        trust_factor = sum(trust_scores) / len(trust_scores)
        mutual_factor = sum(1 for m in mutual_boosts if m > 1.0) / len(mutual_boosts)
        
        success_probability = min(
            base_success * trust_factor * (1 + mutual_factor * 0.3),
            0.95
        )
        
        return IntroPath(
            nodes=nodes,
            edges=edges,
            hop_count=hop_count,
            path_score=round(path_score, 3),
            success_probability=round(success_probability, 3),
            explanation=self._generate_explanation(nodes, edges, path_score)
        )
    
    def _generate_explanation(
        self,
        nodes: List[PathNode],
        edges: List[Dict],
        path_score: float
    ) -> str:
        """Generate human-readable path explanation"""
        
        if len(nodes) < 2:
            return "Direct connection"
        
        mutual_count = sum(1 for e in edges if e.get('mutual', False))
        avg_trust = sum(e['trust'] for e in edges) / len(edges)
        
        explanation_parts = [
            f"{len(nodes)-1}-hop path",
            f"{mutual_count} mutual trust connections" if mutual_count > 0 else None,
            f"average trust: {avg_trust:.2f}",
        ]
        
        explanation = " • ".join(filter(None, explanation_parts))
        
        if path_score > 0.8:
            return f"🟢 **Strong path**: {explanation}"
        elif path_score > 0.6:
            return f"🟡 **Good path**: {explanation}"
        else:
            return f"🟠 **Moderate path**: {explanation}"
