"""Trust scoring and reputation calculation"""

from typing import Dict, List
import logging
from datetime import datetime, timedelta
from gremlin_python.process.traversal import P
from gremlin_python.process.graph_traversal import __

from app.core.graph_client import graph_client

logger = logging.getLogger(__name__)

class TrustScoringService:
    """
    Service for calculating and updating trust scores

    Trust scoring factors:
    - Interaction count      → up to +0.40
    - Successful intro rate  → up to +0.40
    - Recency of interaction → up to +0.20 (90-day window)

    Trust must be EARNED — base score is 0.0 for brand-new relationships.
    """

    @staticmethod
    def compute_score(
        interaction_count: int,
        successful_intros: int,
        last_interaction_at: float = None
    ) -> float:
        """
        Pure function: compute trust score from raw edge counters.
        No graph query — safe to call before or after edge creation.

        Formula:
          interaction_bonus = min(interaction_count / 20, 1.0) * 0.40
          success_bonus     = min(successful_intros  / 10, 1.0) * 0.40
          recency_bonus     = up to 0.20, decays linearly over 90 days
        """
        interaction_bonus = min(interaction_count / 20.0, 1.0) * 0.40
        success_bonus     = min(successful_intros  / 10.0, 1.0) * 0.40

        recency_bonus = 0.0
        if last_interaction_at:
            days_since = (datetime.utcnow().timestamp() - last_interaction_at) / 86400
            if days_since <= 90:
                recency_bonus = (1 - days_since / 90) * 0.20

        return round(
            min(interaction_bonus + success_bonus + recency_bonus, 1.0),
            4
        )
    
    async def calculate_trust_score(
        self,
        from_user_id: str,
        to_user_id: str
    ) -> float:
        """
        Read edge counters from JanusGraph and return the computed trust score.
        Delegates the actual formula to the pure compute_score() method.
        """
        g = graph_client.get_traversal()

        try:
            edge_data = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .next()
            )

            interaction_count    = edge_data.get('interaction_count',  [0])[0]
            successful_intros    = edge_data.get('successful_intros',  [0])[0]
            last_interaction_raw = edge_data.get('last_interaction_at', [None])[0]
            last_interaction_at  = float(last_interaction_raw) if last_interaction_raw else None

            return self.compute_score(
                interaction_count=interaction_count,
                successful_intros=successful_intros,
                last_interaction_at=last_interaction_at
            )

        except StopIteration:
            # No edge exists yet — zero trust, must be earned
            return 0.0
        except Exception as e:
            logger.error(f"❌ Failed to calculate trust score: {str(e)}")
            return 0.0
    
    async def update_reputation_score(self, user_id: str) -> float:
        """
        Calculate and update user's reputation score
        
        Based on:
        - Outgoing trust scores
        - Successful intro rate
        - Network centrality
        """
        g = graph_client.get_traversal()
        
        try:
            # Get all outgoing TRUSTS edges
            outgoing_edges = (
                g.V().has('User', 'user_id', user_id)
                .outE('TRUSTS')
                .valueMap(True)
                .toList()
            )
            
            if not outgoing_edges:
                reputation = 0.0
            else:
                # Average trust score
                avg_trust = sum(
                    e.get('trust_score', [0.5])[0] for e in outgoing_edges
                ) / len(outgoing_edges)
                
                # Successful intro rate
                total_intros = sum(e.get('interaction_count', [0])[0] for e in outgoing_edges)
                successful = sum(e.get('successful_intros', [0])[0] for e in outgoing_edges)
                
                success_rate = successful / total_intros if total_intros > 0 else 0.5
                
                # Weighted reputation
                reputation = (avg_trust * 0.6) + (success_rate * 0.4)
            
            # Update vertex
            g.V().has('User', 'user_id', user_id) \
                .property('reputation_score', reputation) \
                .iterate()
            
            logger.info(f"✅ Updated reputation for {user_id}: {reputation:.3f}")
            return round(reputation, 3)
            
        except Exception as e:
            logger.error(f"❌ Failed to update reputation: {str(e)}")
            return 0.5
    
    async def decay_trust_scores(self, days_threshold: int = 180):
        """
        Apply time decay to trust scores for inactive relationships
        
        Edges with no interaction for > days_threshold get reduced recency_score
        """
        g = graph_client.get_traversal()
        threshold_timestamp = (
            datetime.utcnow() - timedelta(days=days_threshold)
        ).timestamp()
        
        try:
            # Find and update stale edges
            stale_edges = (
                g.E().hasLabel('TRUSTS')
                .has('last_interaction_at', P.lt(threshold_timestamp))
                .toList()
            )
            
            # Update each stale edge
            for edge in stale_edges:
                edge_id = edge.id
                g.E(edge_id).property('recency_score', 0.1).iterate()
            
            decayed_count = len(stale_edges)
            
            logger.info(f"✅ Applied decay to {decayed_count} stale trust edges")
            return decayed_count
            
        except Exception as e:
            logger.error(f"❌ Failed to decay trust scores: {str(e)}")
            return 0
    
    async def calculate_network_centrality(self, user_id: str) -> Dict[str, float]:
        """
        Calculate centrality metrics for a user
        
        Returns:
            - degree_centrality: Number of connections
            - betweenness_centrality: Bridge between communities (approximation)
            - trust_weighted_degree: Sum of trust scores
        """
        g = graph_client.get_traversal()
        
        try:
            # Degree centrality
            out_degree = g.V().has('User', 'user_id', user_id).outE('TRUSTS').count().next()
            in_degree = g.V().has('User', 'user_id', user_id).inE('TRUSTS').count().next()
            total_degree = out_degree + in_degree
            
            # Trust-weighted degree
            trust_sum = (
                g.V().has('User', 'user_id', user_id)
                .outE('TRUSTS')
                .values('trust_score')
                .sum()
                .next()
            )
            
            # Approximate betweenness: count paths that go through this user
            # (Simplified metric - full betweenness is computationally expensive)
            betweenness_approx = (
                g.V().has('User', 'user_id', user_id)
                .both('TRUSTS')
                .dedup()
                .count()
                .next()
            )
            
            return {
                "degree_centrality": total_degree,
                "out_degree": out_degree,
                "in_degree": in_degree,
                "trust_weighted_degree": round(trust_sum, 3),
                "betweenness_centrality_approx": betweenness_approx
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate centrality: {str(e)}")
            return {
                "degree_centrality": 0,
                "out_degree": 0,
                "in_degree": 0,
                "trust_weighted_degree": 0.0,
                "betweenness_centrality_approx": 0
            }
    
    async def boost_trust_for_successful_intro(
        self,
        path_user_ids: List[str],
        boost_amount: float = 0.05
    ):
        """
        Boost trust scores along a path after successful intro
        
        Args:
            path_user_ids: List of user IDs in the intro path
            boost_amount: Amount to boost each edge's trust score
        """
        g = graph_client.get_traversal()
        
        try:
            updated_count = 0
            
            # Update each edge in the path
            for i in range(len(path_user_ids) - 1):
                from_id = path_user_ids[i]
                to_id = path_user_ids[i + 1]
                
                # Get current edge data
                edge_data = (
                    g.V().has('User', 'user_id', from_id)
                    .outE('TRUSTS')
                    .where(__.inV().has('User', 'user_id', to_id))
                    .valueMap(True)
                    .next()
                )
                
                current_intros = edge_data.get('successful_intros', [0])[0]
                
                # First update counters so formula uses fresh values
                g.V().has('User', 'user_id', from_id) \
                    .outE('TRUSTS') \
                    .where(__.inV().has('User', 'user_id', to_id)) \
                    .property('successful_intros', current_intros + 1) \
                    .property('last_interaction_at', datetime.utcnow().timestamp()) \
                    .iterate()
                
                # Recalculate score using the formula (not a flat boost)
                new_score = await self.calculate_trust_score(from_id, to_id)
                
                # Persist the recalculated score
                g.V().has('User', 'user_id', from_id) \
                    .outE('TRUSTS') \
                    .where(__.inV().has('User', 'user_id', to_id)) \
                    .property('trust_score', new_score) \
                    .iterate()
                
                updated_count += 1
            
            logger.info(f"✅ Boosted trust along path: {updated_count} edges updated")
            
            # Update reputation scores for all users in path
            for user_id in path_user_ids:
                await self.update_reputation_score(user_id)
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Failed to boost trust: {str(e)}")
            return 0

# Singleton instance
trust_scoring_service = TrustScoringService()
