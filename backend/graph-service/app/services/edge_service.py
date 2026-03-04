"""Edge CRUD operations"""

from typing import Optional
import uuid
from datetime import datetime
import logging

from gremlin_python import statics
from gremlin_python.process.graph_traversal import __
from app.core.graph_client import graph_client
from app.schemas.edge_schemas import (
    TrustsEdgeCreate, TrustsEdgeResponse,
    FoundedEdgeCreate, FoundedEdgeResponse,
    InvestedInEdgeCreate, InvestedInEdgeResponse
)
from app.services.trust_scoring import trust_scoring_service

logger = logging.getLogger(__name__)

class EdgeService:
    """Service for managing graph edges"""
    
    async def create_trusts_edge(self, edge_data: TrustsEdgeCreate) -> TrustsEdgeResponse:
        """Create a TRUSTS edge between two users"""
        g = graph_client.get_traversal()
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # Calculate score from the provided counters — never trust raw input
            calculated_score = trust_scoring_service.compute_score(
                interaction_count=edge_data.interaction_count,
                successful_intros=edge_data.successful_intros if hasattr(edge_data, 'successful_intros') else 0,
                last_interaction_at=None   # brand-new edge; no recency yet
            )

            # Create edge directly using has() steps (avoids materializing vertex objects)
            g.V().has('User', 'user_id', edge_data.from_user_id) \
                .addE('TRUSTS') \
                .to(__.V().has('User', 'user_id', edge_data.to_user_id)) \
                .property('edge_id', edge_id) \
                .property('trust_score', calculated_score) \
                .property('strength_score', edge_data.strength_score) \
                .property('recency_score', edge_data.recency_score) \
                .property('interaction_count', edge_data.interaction_count) \
                .property('endorsement_count', edge_data.endorsement_count) \
                .property('successful_intros', 0) \
                .property('interaction_decay_factor', 1.0) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
            # Add domain tags to the edge
            if edge_data.domain_tags:
                for tag in edge_data.domain_tags:
                    g.E().has('edge_id', edge_id).property('domain_tags', tag).iterate()
            
            logger.info(
                f"✅ Created TRUSTS edge: {edge_data.from_user_id} → {edge_data.to_user_id}"
            )
            
            return TrustsEdgeResponse(
                edge_id=edge_id,
                from_user_id=edge_data.from_user_id,
                to_user_id=edge_data.to_user_id,
                trust_score=calculated_score,
                strength_score=edge_data.strength_score,
                recency_score=edge_data.recency_score,
                interaction_count=edge_data.interaction_count,
                endorsement_count=edge_data.endorsement_count,
                domain_tags=edge_data.domain_tags,
                successful_intros=0,
                last_interaction_at=None,
                created_at=created_at
            )
            
        except StopIteration:
            raise ValueError("One or both users not found")
        except Exception as e:
            logger.error(f"❌ Failed to create TRUSTS edge: {str(e)}")
            raise
    
    async def update_trust_score(
        self,
        from_user_id: str,
        to_user_id: str,
        new_trust_score: Optional[float] = None
    ) -> bool:
        """Update trust score on an existing edge.
        If new_trust_score is None, recalculates using the scoring formula.
        """
        g = graph_client.get_traversal()
        
        try:
            # Auto-recalculate if no score explicitly provided
            if new_trust_score is None:
                new_trust_score = await trust_scoring_service.calculate_trust_score(
                    from_user_id, to_user_id
                )
                logger.info(
                    f"🔄 Auto-recalculated trust score: {from_user_id} → {to_user_id} = {new_trust_score}"
                )

            # Find and update edge
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .property('trust_score', new_trust_score) \
                .property('updated_at', int(datetime.utcnow().timestamp())) \
                .iterate()
            
            logger.info(
                f"✅ Updated trust score: {from_user_id} → {to_user_id} = {new_trust_score}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update trust score: {str(e)}")
            return False
    
    async def increment_successful_intros(
        self,
        from_user_id: str,
        to_user_id: str
    ) -> bool:
        """Increment successful intro count on edge"""
        g = graph_client.get_traversal()
        
        try:
            # Get current count
            edge_data = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .next()
            )
            
            current_count = edge_data.get('successful_intros', [0])[0]
            
            # Update count and last interaction timestamp
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .property('successful_intros', current_count + 1) \
                .property('last_interaction_at', int(datetime.utcnow().timestamp())) \
                .iterate()

            # Sync trust score using formula now that counters have changed
            await self.update_trust_score(from_user_id, to_user_id)

            logger.info(
                f"✅ Incremented successful intros: {from_user_id} → {to_user_id}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to increment successful intros: {str(e)}")
            return False
    
    async def create_founded_edge(self, edge_data: FoundedEdgeCreate) -> FoundedEdgeResponse:
        """Create a FOUNDED edge (User → Startup)"""
        g = graph_client.get_traversal()
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # Create edge directly using has() steps (avoids materializing vertex objects)
            g.V().has('User', 'user_id', edge_data.user_id) \
                .addE('FOUNDED') \
                .to(__.V().has('Startup', 'startup_id', edge_data.startup_id)) \
                .property('edge_id', edge_id) \
                .property('role', edge_data.role) \
                .property('start_date', int(edge_data.start_date.timestamp()) if edge_data.start_date else None) \
                .property('active', edge_data.active) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
            logger.info(
                f"✅ Created FOUNDED edge: {edge_data.user_id} → {edge_data.startup_id}"
            )
            
            return FoundedEdgeResponse(
                edge_id=edge_id,
                user_id=edge_data.user_id,
                startup_id=edge_data.startup_id,
                role=edge_data.role,
                start_date=edge_data.start_date,
                active=edge_data.active,
                created_at=created_at
            )
            
        except StopIteration:
            raise ValueError("User or startup not found")
        except Exception as e:
            logger.error(f"❌ Failed to create FOUNDED edge: {str(e)}")
            raise

    async def create_invested_in_edge(self, edge_data: InvestedInEdgeCreate) -> InvestedInEdgeResponse:
        """Create an INVESTED_IN edge (Investor → Startup)"""
        g = graph_client.get_traversal()
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # Create edge directly using has() steps (avoids materializing vertex objects)
            g.V().has('User', 'user_id', edge_data.investor_id) \
                .addE('INVESTED_IN') \
                .to(__.V().has('Startup', 'startup_id', edge_data.startup_id)) \
                .property('edge_id', edge_id) \
                .property('round', edge_data.round) \
                .property('amount_range', edge_data.amount_range) \
                .property('year', edge_data.year) \
                .property('visibility', edge_data.visibility) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
            logger.info(
                f"✅ Created INVESTED_IN edge: {edge_data.investor_id} → {edge_data.startup_id}"
            )
            
            return InvestedInEdgeResponse(
                edge_id=edge_id,
                investor_id=edge_data.investor_id,
                startup_id=edge_data.startup_id,
                round=edge_data.round,
                amount_range=edge_data.amount_range,
                year=edge_data.year,
                visibility=edge_data.visibility,
                created_at=created_at
            )
            
        except StopIteration:
            raise ValueError("Investor or startup not found")
        except Exception as e:
            logger.error(f"❌ Failed to create INVESTED_IN edge: {str(e)}")
            raise
    
    async def create_member_of_edge(
        self,
        user_id: str,
        org_id: str,
        role: str = "member",
        start_date: Optional[datetime] = None,
        active: bool = True
    ) -> dict:
        """Create a MEMBER_OF edge (User → Organization)"""
        g = graph_client.get_traversal()
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # Get user and organization vertices
            user_vertex = g.V().has('User', 'user_id', user_id).next()
            org_vertex = g.V().has('Organization', 'org_id', org_id).next()
            
            # Create edge
            edge = (
                g.V(user_vertex)
                .addE('MEMBER_OF')
                .to(org_vertex)
                .property('edge_id', edge_id)
                .property('role', role)
                .property('start_date', int(start_date.timestamp()) if start_date else None)
                .property('active', active)
                .property('created_at', int(created_at.timestamp()))
                .next()
            )
            
            logger.info(f"✅ Created MEMBER_OF edge: {user_id} → {org_id}")
            
            return {
                "edge_id": edge_id,
                "user_id": user_id,
                "org_id": org_id,
                "role": role,
                "start_date": start_date,
                "active": active,
                "created_at": created_at
            }
            
        except StopIteration:
            raise ValueError("User or organization not found")
        except Exception as e:
            logger.error(f"❌ Failed to create MEMBER_OF edge: {str(e)}")
            raise
    
    async def create_worked_with_edge(
        self,
        user_id_1: str,
        user_id_2: str,
        context: str = "",  # e.g., "Co-founders at StartupX"
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Create a WORKED_WITH edge (User → User)"""
        g = graph_client.get_traversal()
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # Get both user vertices
            user1_vertex = g.V().has('User', 'user_id', user_id_1).next()
            user2_vertex = g.V().has('User', 'user_id', user_id_2).next()
            
            # Create bidirectional edges
            edge = (
                g.V(user1_vertex)
                .addE('WORKED_WITH')
                .to(user2_vertex)
                .property('edge_id', edge_id)
                .property('context', context)
                .property('start_date', int(start_date.timestamp()) if start_date else None)
                .property('end_date', int(end_date.timestamp()) if end_date else None)
                .property('created_at', int(created_at.timestamp()))
                .next()
            )
            
            # Create reverse edge (bidirectional)
            reverse_edge_id = str(uuid.uuid4())
            g.V(user2_vertex) \
                .addE('WORKED_WITH') \
                .to(user1_vertex) \
                .property('edge_id', reverse_edge_id) \
                .property('context', context) \
                .property('start_date', int(start_date.timestamp()) if start_date else None) \
                .property('end_date', int(end_date.timestamp()) if end_date else None) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
            logger.info(f"✅ Created WORKED_WITH edges: {user_id_1} ↔ {user_id_2}")
            
            return {
                "edge_id": edge_id,
                "user_id_1": user_id_1,
                "user_id_2": user_id_2,
                "context": context,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": created_at
            }
            
        except StopIteration:
            raise ValueError("One or both users not found")
        except Exception as e:
            logger.error(f"❌ Failed to create WORKED_WITH edge: {str(e)}")
            raise
