"""Edge CRUD operations"""

from typing import Optional, List
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

# Role-based connection rules — defines which roles can initiate trust edges
ALLOWED_TRUST_CONNECTIONS = {
    'founder':   ['investor', 'mentor', 'connector', 'founder'],
    'investor':  ['founder', 'connector', 'investor'],
    'mentor':    ['founder', 'connector'],
    'connector': ['founder', 'investor', 'mentor', 'connector'],
}

# Cooldown (seconds) between automatic trust score recalculations
RECALC_COOLDOWN_SECONDS = 3600  # 1 hour


class EdgeService:
    """Service for managing graph edges"""

    # ── Helper: normalize Gremlin valueMap output ──
    @staticmethod
    def _normalize_edge(raw: dict) -> dict:
        """Convert Gremlin valueMap output to a clean, JSON-serialisable dict.
        Gremlin wraps every property value in a list, e.g.
        {'trust_score': [0.7], T.id: 123}  →  {'trust_score': 0.7, 'id': 123}
        """
        result = {}
        for k, v in raw.items():
            key = k.name if hasattr(k, 'name') else str(k)
            # Unwrap single-element lists
            if isinstance(v, list) and len(v) == 1:
                result[key] = v[0]
            else:
                result[key] = v
        return result

    @staticmethod
    def _extract_edge_value(raw: dict, key: str, default=None):
        value = raw.get(key, default)
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def _get_trust_edges(self, g, from_user_id: str, to_user_id: str) -> list:
        return (
            g.V().has('User', 'user_id', from_user_id)
            .outE('TRUSTS')
            .where(__.inV().has('User', 'user_id', to_user_id))
            .valueMap(True)
            .toList()
        )

    def _set_mutual_flag(self, g, from_user_id: str, to_user_id: str, is_mutual: bool) -> None:
        (
            g.V().has('User', 'user_id', from_user_id)
            .outE('TRUSTS')
            .where(__.inV().has('User', 'user_id', to_user_id))
            .property('is_mutual', is_mutual)
            .iterate()
        )

    def _sync_mutual_flags(self, g, user_a_id: str, user_b_id: str) -> bool:
        forward_accepted = bool(
            g.V().has('User', 'user_id', user_a_id)
            .outE('TRUSTS').has('status', 'accepted')
            .where(__.inV().has('User', 'user_id', user_b_id))
            .toList()
        )
        reverse_accepted = bool(
            g.V().has('User', 'user_id', user_b_id)
            .outE('TRUSTS').has('status', 'accepted')
            .where(__.inV().has('User', 'user_id', user_a_id))
            .toList()
        )
        is_mutual = forward_accepted and reverse_accepted
        self._set_mutual_flag(g, user_a_id, user_b_id, is_mutual)
        self._set_mutual_flag(g, user_b_id, user_a_id, is_mutual)
        return is_mutual

    def _ensure_trust_edge(
        self,
        g,
        from_user_id: str,
        to_user_id: str,
        *,
        status: str,
        strength_score: float = 0.5,
        domain_tags: Optional[List[str]] = None,
    ) -> None:
        existing_edges = self._get_trust_edges(g, from_user_id, to_user_id)
        now_ts = int(datetime.utcnow().timestamp())

        if existing_edges:
            traversal = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .property('status', status)
                .property('updated_at', now_ts)
            )
            if status == 'accepted':
                traversal = traversal.property('accepted_at', now_ts)
            traversal.iterate()
            return

        edge_id = str(uuid.uuid4())
        trust_score = trust_scoring_service.compute_score(
            interaction_count=0,
            successful_intros=0,
            last_interaction_at=None,
        )

        (
            g.V().has('User', 'user_id', from_user_id)
            .addE('TRUSTS')
            .to(__.V().has('User', 'user_id', to_user_id))
            .property('edge_id', edge_id)
            .property('trust_score', trust_score)
            .property('strength_score', strength_score)
            .property('recency_score', 1.0)
            .property('interaction_count', 0)
            .property('endorsement_count', 0)
            .property('successful_intros', 0)
            .property('interaction_decay_factor', 1.0)
            .property('is_mutual', False)
            .property('status', status)
            .property('created_at', now_ts)
            .property('accepted_at', now_ts if status == 'accepted' else None)
            .iterate()
        )

        for tag in domain_tags or []:
            g.E().has('edge_id', edge_id).property('domain_tags', tag).iterate()

    # ── Helper: validate role-based connection rules ──
    def _validate_trust_roles(self, from_user_id: str, to_user_id: str) -> None:
        """Raise ValueError if the sender's role is not allowed to connect to the receiver's role."""
        g = graph_client.get_traversal()
        try:
            from_role_list = (
                g.V().has('User', 'user_id', from_user_id)
                .values('role_primary')
                .toList()
            )
            to_role_list = (
                g.V().has('User', 'user_id', to_user_id)
                .values('role_primary')
                .toList()
            )
            if not from_role_list or not to_role_list:
                raise ValueError("One or both users not found")

            from_role = from_role_list[0].lower()
            to_role = to_role_list[0].lower()

            allowed = ALLOWED_TRUST_CONNECTIONS.get(from_role, [])
            if to_role not in allowed:
                raise ValueError(
                    f"Role '{from_role}' cannot send trust requests to role '{to_role}'"
                )
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"⚠️ Role validation skipped (non-fatal): {e}")
    
    async def create_trusts_edge(self, edge_data: TrustsEdgeCreate) -> TrustsEdgeResponse:
        """Create a TRUSTS edge between two users"""
        g = graph_client.get_traversal()
        
        # ── Self-loop prevention ──
        if edge_data.from_user_id == edge_data.to_user_id:
            raise ValueError("User cannot create a trust edge to themselves")
        
        # ── Role-based connection validation ──
        self._validate_trust_roles(edge_data.from_user_id, edge_data.to_user_id)
        
        # ── Duplicate edge prevention ──
        existing = (
            g.V().has('User', 'user_id', edge_data.from_user_id)
            .outE('TRUSTS')
            .where(__.inV().has('User', 'user_id', edge_data.to_user_id))
            .toList()
        )
        if existing:
            raise ValueError(
                f"TRUSTS edge already exists from {edge_data.from_user_id} to {edge_data.to_user_id}"
            )
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            initial_interaction_count = 0
            initial_successful_intros = 0
            initial_recency_score = 1.0

            # Calculate score from server-owned counters — never trust raw input
            calculated_score = trust_scoring_service.compute_score(
                interaction_count=initial_interaction_count,
                successful_intros=initial_successful_intros,
                last_interaction_at=None   # brand-new edge; no recency yet
            )

            traversal = (
                g.V().has('User', 'user_id', edge_data.from_user_id)
                .addE('TRUSTS')
                .to(__.V().has('User', 'user_id', edge_data.to_user_id))
                .property('edge_id', edge_id)
                .property('trust_score', calculated_score)
                .property('strength_score', edge_data.strength_score)
                .property('recency_score', initial_recency_score)
                .property('interaction_count', initial_interaction_count)
                .property('endorsement_count', edge_data.endorsement_count)
                .property('successful_intros', initial_successful_intros)
                .property('interaction_decay_factor', 1.0)
                .property('is_mutual', False)
                .property('status', 'pending')
                .property('created_at', int(created_at.timestamp()))
            )
            traversal.iterate()
            
            # Add domain tags to the edge
            if edge_data.domain_tags:
                for tag in edge_data.domain_tags:
                    g.E().has('edge_id', edge_id).property('domain_tags', tag).iterate()
            
            logger.info(
                f"✅ Created TRUSTS edge: {edge_data.from_user_id} → {edge_data.to_user_id} (pending connection request)"
            )
            
            return TrustsEdgeResponse(
                edge_id=edge_id,
                from_user_id=edge_data.from_user_id,
                to_user_id=edge_data.to_user_id,
                trust_score=calculated_score,
                strength_score=edge_data.strength_score,
                recency_score=initial_recency_score,
                interaction_count=initial_interaction_count,
                endorsement_count=edge_data.endorsement_count,
                domain_tags=edge_data.domain_tags,
                successful_intros=initial_successful_intros,
                is_mutual=False,
                status='pending',
                last_interaction_at=None,
                created_at=created_at
            )
            
        except StopIteration:
            raise ValueError("One or both users not found")
        except Exception as e:
            logger.error(f"❌ Failed to create TRUSTS edge: {str(e)}")
            raise
    
    # ── Connection request / approval flow ──
    async def accept_trusts_edge(self, from_user_id: str, to_user_id: str) -> bool:
        """Accept a pending TRUSTS edge.
        'from_user_id' = the person who SENT the request.
        'to_user_id'   = the RECEIVER who is accepting (i.e. the current user).
        We query from the receiver's perspective using inE().
        """
        g = graph_client.get_traversal()
        try:
            # Receiver looks at incoming pending edges from sender
            edge = (
                g.V().has('User', 'user_id', to_user_id)
                .inE('TRUSTS')
                .has('status', 'pending')
                .where(__.outV().has('User', 'user_id', from_user_id))
                .valueMap(True)
                .toList()
            )
            if not edge:
                return False
            pending_edge = edge[0]
            reverse_strength = float(self._extract_edge_value(pending_edge, 'strength_score', 0.5) or 0.5)
            reverse_domain_tags = pending_edge.get('domain_tags', []) or []
            
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .property('status', 'accepted') \
                .property('accepted_at', int(datetime.utcnow().timestamp())) \
                .iterate()

            self._ensure_trust_edge(
                g,
                to_user_id,
                from_user_id,
                status='accepted',
                strength_score=reverse_strength,
                domain_tags=reverse_domain_tags,
            )
            self._sync_mutual_flags(g, from_user_id, to_user_id)

            await trust_scoring_service.update_reputation_score(from_user_id)
            await trust_scoring_service.update_reputation_score(to_user_id)
            
            logger.info(f"✅ Accepted TRUSTS edge: {from_user_id} → {to_user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to accept TRUSTS edge: {str(e)}")
            return False
    
    async def reject_trusts_edge(self, from_user_id: str, to_user_id: str) -> bool:
        """Reject a pending TRUSTS edge.
        'from_user_id' = the person who SENT the request.
        'to_user_id'   = the RECEIVER who is rejecting.
        """
        g = graph_client.get_traversal()
        try:
            # Receiver looks at incoming pending edges from sender
            edge = (
                g.V().has('User', 'user_id', to_user_id)
                .inE('TRUSTS')
                .has('status', 'pending')
                .where(__.outV().has('User', 'user_id', from_user_id))
                .toList()
            )
            if not edge:
                return False
            
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .property('status', 'rejected') \
                .property('is_mutual', False) \
                .property('rejected_at', int(datetime.utcnow().timestamp())) \
                .iterate()

            self._sync_mutual_flags(g, from_user_id, to_user_id)

            await trust_scoring_service.update_reputation_score(from_user_id)
            await trust_scoring_service.update_reputation_score(to_user_id)
            
            logger.info(f"✅ Rejected TRUSTS edge: {from_user_id} → {to_user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reject TRUSTS edge: {str(e)}")
            return False
    
    async def get_pending_requests(self, user_id: str) -> list:
        """Get all pending TRUSTS edges where this user is the receiver.
        Returns normalised dicts (not raw Gremlin valueMap output).
        """
        g = graph_client.get_traversal()
        try:
            raw_pending = (
                g.V().has('User', 'user_id', user_id)
                .inE('TRUSTS')
                .has('status', 'pending')
                .valueMap(True)
                .toList()
            )
            return [self._normalize_edge(e) for e in raw_pending]
        except Exception as e:
            logger.error(f"❌ Failed to get pending requests: {str(e)}")
            return []

    # ── HIGH PRIORITY: Edge deletion ──
    async def delete_trusts_edge(self, from_user_id: str, to_user_id: str) -> bool:
        """Delete a mutual connection between two users.
        Removes TRUSTS edges in both directions so the connection disappears for both users."""
        g = graph_client.get_traversal()
        try:
            edge_exists = bool(self._get_trust_edges(g, from_user_id, to_user_id))
            reverse_exists = bool(self._get_trust_edges(g, to_user_id, from_user_id))
            if not edge_exists and not reverse_exists:
                return False
            
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .drop() \
                .iterate()

            g.V().has('User', 'user_id', to_user_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', from_user_id)) \
                .drop() \
                .iterate()

            await trust_scoring_service.update_reputation_score(from_user_id)
            await trust_scoring_service.update_reputation_score(to_user_id)
            
            logger.info(
                f"🗑️ TRUSTS connection removed: {from_user_id} ↔ {to_user_id} "
                f"at {datetime.utcnow().isoformat()} (audit)"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete TRUSTS edge: {str(e)}")
            return False
    
    async def delete_founded_edge(self, user_id: str, startup_id: str) -> bool:
        """Delete a FOUNDED edge between a user and startup"""
        g = graph_client.get_traversal()
        try:
            edge = (
                g.V().has('User', 'user_id', user_id)
                .outE('FOUNDED')
                .where(__.inV().has('Startup', 'startup_id', startup_id))
                .toList()
            )
            if not edge:
                return False
            
            g.V().has('User', 'user_id', user_id) \
                .outE('FOUNDED') \
                .where(__.inV().has('Startup', 'startup_id', startup_id)) \
                .drop() \
                .iterate()
            
            logger.info(f"✅ Deleted FOUNDED edge: {user_id} → {startup_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete FOUNDED edge: {str(e)}")
            return False
    
    async def delete_invested_in_edge(self, investor_id: str, startup_id: str) -> bool:
        """Delete an INVESTED_IN edge between an investor and startup"""
        g = graph_client.get_traversal()
        try:
            edge = (
                g.V().has('User', 'user_id', investor_id)
                .outE('INVESTED_IN')
                .where(__.inV().has('Startup', 'startup_id', startup_id))
                .toList()
            )
            if not edge:
                return False
            
            g.V().has('User', 'user_id', investor_id) \
                .outE('INVESTED_IN') \
                .where(__.inV().has('Startup', 'startup_id', startup_id)) \
                .drop() \
                .iterate()
            
            logger.info(f"✅ Deleted INVESTED_IN edge: {investor_id} → {startup_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete INVESTED_IN edge: {str(e)}")
            return False
    
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
                .outE('TRUSTS').has('status', 'accepted') \
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
            # Safe fetch — .toList() instead of .next() to avoid StopIteration crash
            edge_list = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .toList()
            )
            if not edge_list:
                raise ValueError(f"No TRUSTS edge found from {from_user_id} to {to_user_id}")
            edge_data = edge_list[0]
            
            current_count = edge_data.get('successful_intros', [0])[0]
            
            # Update count and last interaction timestamp
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS').has('status', 'accepted') \
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
    
    # ── Interaction count → score sync (with recalc cooldown) ──
    async def increment_interaction_count(
        self,
        from_user_id: str,
        to_user_id: str
    ) -> bool:
        """Increment interaction count on edge and auto-recalculate trust score.
        Call this whenever a meaningful interaction occurs (e.g., message, meeting).
        Trust score is only recalculated if the last update was > RECALC_COOLDOWN_SECONDS ago."""
        g = graph_client.get_traversal()
        
        try:
            # Safe fetch — .toList() instead of .next() to avoid StopIteration crash
            edge_list = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .toList()
            )
            if not edge_list:
                raise ValueError(f"No TRUSTS edge found from {from_user_id} to {to_user_id}")
            edge_data = edge_list[0]
            
            current_count = edge_data.get('interaction_count', [0])[0]
            now = int(datetime.utcnow().timestamp())
            
            # Update count, reset decay factor, and set last interaction time
            g.V().has('User', 'user_id', from_user_id) \
                .outE('TRUSTS').has('status', 'accepted') \
                .where(__.inV().has('User', 'user_id', to_user_id)) \
                .property('interaction_count', current_count + 1) \
                .property('interaction_decay_factor', 1.0) \
                .property('last_interaction_at', now) \
                .iterate()
            
            # Recalculate trust score only if cooldown has elapsed
            last_updated = edge_data.get('updated_at', [0])[0]
            if isinstance(last_updated, list):
                last_updated = last_updated[0] if last_updated else 0
            if (now - int(last_updated)) > RECALC_COOLDOWN_SECONDS:
                await self.update_trust_score(from_user_id, to_user_id)
            else:
                logger.info("⏭️ Skipping trust score recalc — within cooldown window")
            
            logger.info(
                f"✅ Incremented interaction count: {from_user_id} → {to_user_id} (new count: {current_count + 1})"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to increment interaction count: {str(e)}")
            return False
    
    # ── List trust edges for a user ──
    async def get_user_trust_edges(
        self,
        user_id: str,
        status: Optional[str] = None,
        direction: str = 'out'
    ) -> list:
        """Get all TRUSTS edges for a user with optional status and direction filter.
        
        Args:
            user_id:   The user whose edges to fetch.
            status:    Optional filter — 'pending', 'accepted', 'rejected'.
            direction: 'out' (sent), 'in' (received), or 'both'.
        """
        g = graph_client.get_traversal()
        try:
            base = g.V().has('User', 'user_id', user_id)
            
            if direction == 'in':
                traversal = base.inE('TRUSTS')
            elif direction == 'both':
                traversal = base.bothE('TRUSTS')
            else:
                traversal = base.outE('TRUSTS')
            
            if status:
                traversal = traversal.has('status', status)
            
            raw = traversal.valueMap(True).toList()
            return [self._normalize_edge(e) for e in raw]
        except Exception as e:
            logger.error(f"❌ Failed to get trust edges for {user_id}: {str(e)}")
            return []

    async def has_accepted_trust_edge(self, from_user_id: str, to_user_id: str) -> bool:
        g = graph_client.get_traversal()
        try:
            return bool(
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .toList()
            )
        except Exception as e:
            logger.error(f"❌ Failed to check accepted TRUSTS edge: {str(e)}")
            return False

    async def create_founded_edge(self, edge_data: FoundedEdgeCreate) -> FoundedEdgeResponse:
        """Create a FOUNDED edge (User → Startup)"""
        g = graph_client.get_traversal()
        
        # ── Duplicate edge prevention ──
        existing = (
            g.V().has('User', 'user_id', edge_data.user_id)
            .outE('FOUNDED')
            .where(__.inV().has('Startup', 'startup_id', edge_data.startup_id))
            .toList()
        )
        if existing:
            raise ValueError(
                f"FOUNDED edge already exists: {edge_data.user_id} → {edge_data.startup_id}"
            )
        
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
        
        # ── Duplicate edge prevention ──
        existing = (
            g.V().has('User', 'user_id', edge_data.investor_id)
            .outE('INVESTED_IN')
            .where(__.inV().has('Startup', 'startup_id', edge_data.startup_id))
            .toList()
        )
        if existing:
            raise ValueError(
                f"INVESTED_IN edge already exists: {edge_data.investor_id} → {edge_data.startup_id}"
            )
        
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
            # ── HIGH PRIORITY: Duplicate edge prevention ──
            existing = (
                g.V().has('User', 'user_id', user_id)
                .outE('MEMBER_OF')
                .where(__.inV().has('Organization', 'org_id', org_id))
                .toList()
            )
            if existing:
                raise ValueError(f"MEMBER_OF edge already exists: {user_id} → {org_id}")
            
            # ── MEDIUM PRIORITY: Fixed — use has() steps instead of .next() ──
            g.V().has('User', 'user_id', user_id) \
                .addE('MEMBER_OF') \
                .to(__.V().has('Organization', 'org_id', org_id)) \
                .property('edge_id', edge_id) \
                .property('role', role) \
                .property('start_date', int(start_date.timestamp()) if start_date else None) \
                .property('active', active) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
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
        """Create a WORKED_WITH edge (User ↔ User, bidirectional)"""
        g = graph_client.get_traversal()
        
        # ── HIGH PRIORITY: Self-loop prevention ──
        if user_id_1 == user_id_2:
            raise ValueError("User cannot create a WORKED_WITH edge with themselves")
        
        # ── HIGH PRIORITY: Duplicate edge prevention (check both directions) ──
        existing = (
            g.V().has('User', 'user_id', user_id_1)
            .bothE('WORKED_WITH')
            .where(__.bothV().has('User', 'user_id', user_id_2))
            .toList()
        )
        if existing:
            raise ValueError(
                f"WORKED_WITH relationship already exists between {user_id_1} and {user_id_2}"
            )
        
        edge_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        try:
            # ── MEDIUM PRIORITY: Fixed — use has() steps instead of .next() ──
            # Forward edge
            g.V().has('User', 'user_id', user_id_1) \
                .addE('WORKED_WITH') \
                .to(__.V().has('User', 'user_id', user_id_2)) \
                .property('edge_id', edge_id) \
                .property('context', context) \
                .property('start_date', int(start_date.timestamp()) if start_date else None) \
                .property('end_date', int(end_date.timestamp()) if end_date else None) \
                .property('created_at', int(created_at.timestamp())) \
                .iterate()
            
            # Reverse edge (bidirectional)
            reverse_edge_id = str(uuid.uuid4())
            g.V().has('User', 'user_id', user_id_2) \
                .addE('WORKED_WITH') \
                .to(__.V().has('User', 'user_id', user_id_1)) \
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
