from gremlin_python.process.traversal import P, Order
from gremlin_python.process.graph_traversal import __
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime, timedelta

from app.core.graph_client import graph_client
from app.core.config import settings
from app.schemas.path_schemas import IntroPath, PathNode

logger = logging.getLogger(__name__)

def _extract_value(data, key, default, value_type=str):
    """
    Helper to extract values from Gremlin results that may be in different formats.
    
    GraphBinary wraps values in lists: {'name': ['Alice']}
    GraphSON returns plain values: {'name': 'Alice'}
    
    This function handles both formats.
    """
    value = data.get(key, default)
    
    # If it's a list, extract the first element
    if isinstance(value, list):
        value = value[0] if value else default
    
    # Convert to the desired type
    try:
        if value_type == float:
            return float(value) if value is not None else float(default)
        elif value_type == int:
            return int(value) if value is not None else int(default)
        else:
            return str(value) if value is not None else str(default)
    except (ValueError, TypeError):
        return default

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
        2. Use .emit() to capture paths of all lengths (1-4 hops)
        3. Filter by min trust score
        4. Score paths by: trust × strength × recency × mutual_boost
        5. Return top N ranked paths
        
        Now uses GraphSON serializer which supports Path objects - enabling
        efficient single-query multi-hop discovery instead of multiple queries.
        """
        g = graph_client.get_traversal()
        
        def find_paths_multihop():
            """
            Find multi-hop paths using Gremlin's .path() step.
            
            With GraphSON serializer, this now works efficiently in a single query!
            
            Strategy: Query each hop level separately (1-hop, 2-hop, etc.) and combine results.
            This is still much more efficient than the old approach of querying each vertex/edge.
            """
            all_paths = []
            
            try:
                # Find paths of each length from 1 to max_hops
                for hop_count in range(1, self.max_hops + 1):
                    try:
                        paths_at_hop = (
                            g.V().has('User', 'user_id', founder_id)
                            .repeat(__.out('TRUSTS'))
                            .times(hop_count)
                            .has('User', 'user_id', investor_id)
                            .path().by('user_id')
                            .toList()
                        )
                        
                        if paths_at_hop:
                            logger.info(f"Found {len(paths_at_hop)} path(s) at {hop_count}-hop level")
                            for path in paths_at_hop:
                                # Convert Path object to list of user_ids
                                user_ids = [str(uid) for uid in path]
                                all_paths.append(user_ids)
                    
                    except Exception as e:
                        logger.error(f"Error finding {hop_count}-hop paths: {e}")
                        continue
                
                logger.info(f"Total paths found: {len(all_paths)}")
                return all_paths[:max_paths * 3]  # Return extra for filtering
                
            except Exception as e:
                logger.error(f"Multi-hop path discovery failed: {e}")
                return []
        
        try:
            # Run in executor to avoid event loop issues
            loop = asyncio.get_running_loop()
            paths_user_ids = await loop.run_in_executor(None, find_paths_multihop)
            
            if not paths_user_ids:
                logger.info(f"No paths found from {founder_id} to {investor_id}")
                return []
            
            logger.info(f"Scoring {len(paths_user_ids)} path(s)...")
            
            # Score and rank paths
            scored_paths = []
            for idx, path_ids in enumerate(paths_user_ids):
                try:
                    intro_path = await self._score_path(path_ids, domain_filter, g)
                    if intro_path:
                        scored_paths.append(intro_path)
                except Exception as e:
                    logger.error(f"Failed to score path {idx + 1}: {str(e)}")
                    continue
            
            # Sort by path score (descending)
            scored_paths.sort(key=lambda x: x.path_score, reverse=True)
            
            logger.info(
                f"Returning top {min(len(scored_paths), max_paths)} path(s) "
                f"from {founder_id} to {investor_id}"
            )
            
            return scored_paths[:max_paths]
            
        except Exception as e:
            logger.error(f"Path discovery error: {str(e)}")
            raise
    
    async def _score_path(
        self,
        path_user_ids: List[str],
        domain_filter: Optional[str] = None,
        g = None
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
        
        if g is None:
            g = graph_client.get_traversal()
        
        loop = asyncio.get_running_loop()
        
        for i, user_id in enumerate(path_user_ids):
            # Query vertex properties separately to avoid serialization issues
            def get_vertex_data():
                return (
                    g.V().has('User', 'user_id', user_id)
                    .valueMap('user_id', 'name', 'role_primary', 'reputation_score')
                    .next()
                )
            
            vertex_data = await loop.run_in_executor(None, get_vertex_data)
            
            # Extract vertex properties (handles both GraphBinary and GraphSON formats)
            node = PathNode(
                user_id=_extract_value(vertex_data, 'user_id', user_id, str),
                name=_extract_value(vertex_data, 'name', 'Unknown', str),
                role=_extract_value(vertex_data, 'role_primary', '', str),
                reputation_score=_extract_value(vertex_data, 'reputation_score', 0.0, float)
            )
            nodes.append(node)
            
            # Get edge data between consecutive nodes
            if i > 0:
                from_id = nodes[i-1].user_id
                to_id = node.user_id
                
                # Query edge properties
                def get_edge_props():
                    return (
                        g.V().has('User', 'user_id', from_id)
                        .outE('TRUSTS')
                        .where(__.inV().has('User', 'user_id', to_id))
                        .valueMap(True)
                        .next()
                    )
                
                edge_props = await loop.run_in_executor(None, get_edge_props)
                
                # Extract edge properties (handles both GraphBinary and GraphSON formats)
                trust_score = _extract_value(edge_props, 'trust_score', 0.5, float)
                strength_score = _extract_value(edge_props, 'strength_score', 0.5, float)
                recency_score = _extract_value(edge_props, 'recency_score', 1.0, float)
                
                # Check for mutual trust (bidirectional)
                def check_mutual():
                    return (
                        g.V().has('User', 'user_id', to_id)
                        .outE('TRUSTS')
                        .where(__.inV().has('User', 'user_id', from_id))
                        .hasNext()
                    )
                
                mutual_exists = await loop.run_in_executor(None, check_mutual)
                
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
