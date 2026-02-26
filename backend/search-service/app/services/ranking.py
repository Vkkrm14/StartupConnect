"""Graph-aware ranking for search results"""

from typing import List, Dict, Any
import logging
import httpx

logger = logging.getLogger(__name__)

class RankingService:
    """
    Enhances search results with graph-based signals
    
    Takes Elasticsearch results and re-ranks based on:
    - Trust network proximity
    - Mutual connections
    - Domain expertise overlap
    - Reputation scores
    """
    
    def __init__(self, graph_service_url: str = "http://graph-service:8001"):
        self.graph_service_url = graph_service_url
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def rank_users_by_proximity(
        self,
        search_results: List[Dict[str, Any]],
        current_user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Re-rank search results based on trust network proximity
        
        Users closer in the trust graph get higher scores
        """
        
        # For each result, check if there's a path to current user
        ranked_results = []
        
        for result in search_results:
            target_user_id = result["user_id"]
            
            # Skip self
            if target_user_id == current_user_id:
                result["proximity_score"] = 0.0
                result["connection_degree"] = 0
                ranked_results.append(result)
                continue
            
            # Check graph connection
            try:
                # Call graph service to find shortest path
                response = await self.http_client.post(
                    f"{self.graph_service_url}/api/v1/paths/discover",
                    json={
                        "founder_id": current_user_id,
                        "investor_id": target_user_id,
                        "max_paths": 1
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    paths = data.get("paths", [])
                    
                    if paths:
                        path = paths[0]
                        hop_count = path["hop_count"]
                        path_score = path["path_score"]
                        
                        # Calculate proximity score (inverse of hops)
                        proximity_score = path_score / (hop_count + 1)
                        
                        result["proximity_score"] = proximity_score
                        result["connection_degree"] = hop_count
                        result["trust_path_exists"] = True
                    else:
                        result["proximity_score"] = 0.0
                        result["connection_degree"] = None
                        result["trust_path_exists"] = False
                else:
                    result["proximity_score"] = 0.0
                    result["connection_degree"] = None
                    result["trust_path_exists"] = False
                    
            except Exception as e:
                logger.warning(f"Graph service call failed: {str(e)}")
                result["proximity_score"] = 0.0
                result["connection_degree"] = None
                result["trust_path_exists"] = False
            
            ranked_results.append(result)
        
        # Re-rank: combine original score with proximity
        for result in ranked_results:
            original_score = result.get("score", 1.0)
            proximity_score = result.get("proximity_score", 0.0)
            reputation = result.get("reputation_score", 0.5)
            
            # Weighted combination
            result["final_score"] = (
                original_score * 0.5 +  # ES relevance
                proximity_score * 100 * 0.3 +  # Graph proximity
                reputation * 10 * 0.2  # Reputation
            )
        
        # Sort by final score
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return ranked_results
    
    async def get_mutual_connections(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> List[str]:
        """
        Find mutual connections between two users
        
        Returns list of user IDs who are connected to both
        """
        
        # This requires a graph query for common neighbors
        # Placeholder implementation
        
        return []
    
    async def get_domain_overlap_score(
        self,
        user_id: str,
        target_domains: List[str]
    ) -> float:
        """
        Calculate domain expertise overlap score
        
        Returns score 0-1 based on how much user's domains
        overlap with target domains
        """
        
        # TODO: Get user's domain tags from graph
        # Calculate Jaccard similarity
        
        return 0.0
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
