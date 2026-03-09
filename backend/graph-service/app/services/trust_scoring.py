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
    def _unwrap_value(value, default=None):
        if isinstance(value, list):
            return value[0] if value else default
        return value if value is not None else default

    @staticmethod
    def compute_score(
        interaction_count: int,
        successful_intros: int,
        last_interaction_at: float = None,
        interaction_decay_factor: float = 1.0
    ) -> float:
        """
        Pure function: compute trust score from raw edge counters.
        No graph query — safe to call before or after edge creation.

        Formula:
          effective_interactions = interaction_count * interaction_decay_factor
          interaction_bonus = min(effective_interactions / 20, 1.0) * 0.40
          success_bonus     = min(successful_intros  / 10, 1.0) * 0.40
          recency_bonus     = up to 0.20, decays linearly over 90 days

        interaction_decay_factor (0.0–1.0):
          - Starts at 1.0 (full weight) when a message is sent
          - Multiplied by 0.6 each day (40% reduction per day)
          - Resets to 1.0 when a new message is received
        """
        effective_interactions = interaction_count * max(0.0, min(interaction_decay_factor, 1.0))
        interaction_bonus = min(effective_interactions / 20.0, 1.0) * 0.40
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

    @staticmethod
    def compute_recency_score(last_interaction_at: float = None) -> float:
        """
        Standalone helper: compute the recency_score edge property (0.0–1.0).

        Distinct from recency_bonus in compute_score():
          - recency_bonus  : contributes up to +0.20 to trust_score
          - recency_score  : 0–1.0 multiplier used by path_discovery scoring

        Formula (same decay window as recency_bonus):
          recency_score = max(0, 1 - days_since / 90)

          days_since → recency_score
          0          → 1.00   (just interacted)
          30 days    → 0.67
          60 days    → 0.33
          90+ days   → 0.00   (fully decayed)
        """
        if not last_interaction_at:
            return 1.0  # brand-new edge — no interaction yet, no penalty
        days_since = (datetime.utcnow().timestamp() - last_interaction_at) / 86400
        return round(max(0.0, 1.0 - days_since / 90.0), 4)

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
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .next()
            )

            interaction_count = self._unwrap_value(edge_data.get('interaction_count'), 0)
            successful_intros = self._unwrap_value(edge_data.get('successful_intros'), 0)
            last_interaction_raw = self._unwrap_value(edge_data.get('last_interaction_at'), None)
            decay_factor_raw = self._unwrap_value(edge_data.get('interaction_decay_factor'), 1.0)
            last_interaction_at      = float(last_interaction_raw) if last_interaction_raw else None
            interaction_decay_factor = float(decay_factor_raw) if decay_factor_raw is not None else 1.0

            return self.compute_score(
                interaction_count=interaction_count,
                successful_intros=successful_intros,
                last_interaction_at=last_interaction_at,
                interaction_decay_factor=interaction_decay_factor
            )

        except StopIteration:
            # No edge exists yet — zero trust, must be earned
            return 0.0
        except Exception as e:
            logger.error(f"❌ Failed to calculate trust score: {str(e)}")
            return 0.0

    async def record_interaction(
        self,
        from_user_id: str,
        to_user_id: str,
    ) -> dict:
        """
        Called when two connected users exchange a message.

        Behaviour:
          - Only acts if a TRUSTS edge already exists (trust must be explicitly created).
          - Rate-limited to 1 interaction credit per hour per direction pair.
          - Increments interaction_count and resets interaction_decay_factor to 1.0
            (fresh daily activity; decay job will reduce it overnight).
          - Recomputes and persists trust_score + reputation_score.
        """
        g = graph_client.get_traversal()

        try:
            edge_data = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .next()
            )
        except StopIteration:
            return {"status": "no_edge",
                    "message": f"No TRUSTS edge from {from_user_id} to {to_user_id}"}
        except Exception as e:
            logger.error(f"❌ record_interaction lookup failed: {e}")
            return {"status": "error", "message": str(e)}

        # ── Rate-limit: 1 credit per hour ─────────────────────────────────────
        last_raw = self._unwrap_value(edge_data.get('last_interaction_at'), None)
        if last_raw:
            hours_since = (datetime.utcnow().timestamp() - float(last_raw)) / 3600
            if hours_since < 1.0:
                return {
                    "status": "rate_limited",
                    "retry_after_hours": round(1.0 - hours_since, 2)
                }

        now = datetime.utcnow().timestamp()
        new_count = int(self._unwrap_value(edge_data.get('interaction_count'), 0)) + 1
        intros = int(self._unwrap_value(edge_data.get('successful_intros'), 0))

        # recency_score = 1.0 on interaction (just interacted — full freshness)
        new_recency = self.compute_recency_score(now)  # days_since=0 → 1.0

        # ── Update edge counters; reset decay factor + recency to 1.0 ─────────
        (
            g.V().has('User', 'user_id', from_user_id)
            .outE('TRUSTS').has('status', 'accepted')
            .where(__.inV().has('User', 'user_id', to_user_id))
            .property('interaction_count',       new_count)
            .property('last_interaction_at',      now)
            .property('interaction_decay_factor', 1.0)
            .property('recency_score',            new_recency)
            .iterate()
        )

        # ── Recompute trust score ─────────────────────────────────────────────
        new_trust = self.compute_score(
            interaction_count=new_count,
            successful_intros=intros,
            last_interaction_at=now,
            interaction_decay_factor=1.0
        )
        (
            g.V().has('User', 'user_id', from_user_id)
            .outE('TRUSTS').has('status', 'accepted')
            .where(__.inV().has('User', 'user_id', to_user_id))
            .property('trust_score', new_trust)
            .iterate()
        )

        await self.update_reputation_score(from_user_id)

        logger.info(
            f"✅ Interaction recorded {from_user_id}→{to_user_id}: "
            f"count={new_count}, trust={new_trust:.4f}"
        )
        return {
            "status":                  "updated",
            "from_user_id":            from_user_id,
            "to_user_id":              to_user_id,
            "new_interaction_count":   new_count,
            "new_trust_score":         new_trust,
        }

    async def daily_interaction_decay(self) -> int:
        """
        Scheduled job — run once at the start of each day.

        Reduces the interaction_decay_factor by 40% for every TRUSTS edge
        that did NOT receive a message today (i.e. last_interaction_at < today midnight).
        Then recomputes and persists the affected trust scores.

        Formula applied per edge:
          interaction_decay_factor *= 0.6   (60% retained, 40% lost)

        Effect on interaction_bonus:
          If factor was 1.0 → becomes 0.60  (−40%)
          If factor was 0.6 → becomes 0.36  (−40% again)
          Asymptotically reaches 0 — a silent pair eventually loses all
          interaction bonus, even if their raw interaction_count is high.

        Edges that received a message today are SKIPPED (their factor was
        already reset to 1.0 by record_interaction).
        """
        g = graph_client.get_traversal()

        today_midnight = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()

        try:
            all_edges = (
                g.E().hasLabel('TRUSTS').has('status', 'accepted')
                .project('edge_id', 'from_uid', 'to_uid',
                         'interaction_count', 'successful_intros',
                         'last_interaction_at', 'interaction_decay_factor')
                .by(__.id())
                .by(__.outV().values('user_id'))
                .by(__.inV().values('user_id'))
                .by(__.coalesce(__.values('interaction_count'),   __.constant(0)))
                .by(__.coalesce(__.values('successful_intros'),   __.constant(0)))
                .by(__.coalesce(__.values('last_interaction_at'), __.constant(0.0)))
                .by(__.coalesce(__.values('interaction_decay_factor'), __.constant(1.0)))
                .toList()
            )

            decayed_count = 0
            for edge in all_edges:
                last_ts = float(edge.get('last_interaction_at', 0) or 0)

                # Skip edges that had activity since today midnight
                if last_ts >= today_midnight:
                    continue

                old_factor  = float(edge.get('interaction_decay_factor', 1.0) or 1.0)
                new_factor  = round(old_factor * 0.6, 6)   # 40% reduction

                from_uid    = str(edge['from_uid'])
                to_uid      = str(edge['to_uid'])
                count       = int(edge.get('interaction_count', 0) or 0)
                intros      = int(edge.get('successful_intros', 0) or 0)
                last_ts_val = last_ts if last_ts > 0 else None

                # Persist decayed factor
                (
                    g.V().has('User', 'user_id', from_uid)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', to_uid))
                    .property('interaction_decay_factor', new_factor)
                    .iterate()
                )

                # Recompute and persist trust score
                new_trust = self.compute_score(
                    interaction_count=count,
                    successful_intros=intros,
                    last_interaction_at=last_ts_val,
                    interaction_decay_factor=new_factor
                )
                (
                    g.V().has('User', 'user_id', from_uid)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', to_uid))
                    .property('trust_score', new_trust)
                    .iterate()
                )

                decayed_count += 1

            logger.info(
                f"✅ Daily interaction decay applied to {decayed_count} edges "
                f"(factor ×0.6, 40% reduction)"
            )
            return decayed_count

        except Exception as e:
            logger.error(f"❌ daily_interaction_decay failed: {e}")
            return 0
    
    async def update_reputation_score(self, user_id: str) -> float:
        """
        Calculate and update user's reputation score.

        4-component formula (weights sum to 1.0):
          rep = avg_outgoing_trust  * 0.35
              + intro_success_rate  * 0.30
              + trust_weighted_in   * 0.20   (how much trusted peers trust you)
              + vouch_score         * 0.15
        """
        g = graph_client.get_traversal()

        try:
            # ── Outgoing edge stats ────────────────────────────────────────────
            outgoing_edges = (
                g.V().has('User', 'user_id', user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .valueMap(True)
                .toList()
            )

            if not outgoing_edges:
                avg_trust    = 0.0
                success_rate = 0.0
            else:
                avg_trust = sum(
                    float(self._unwrap_value(e.get('trust_score'), 0.0)) for e in outgoing_edges
                ) / len(outgoing_edges)

                total_interactions = sum(
                    int(self._unwrap_value(e.get('interaction_count'), 0))
                    for e in outgoing_edges
                )
                total_successful = sum(
                    int(self._unwrap_value(e.get('successful_intros'), 0))
                    for e in outgoing_edges
                )
                success_denominator = max(total_interactions, total_successful, 1)
                success_rate = min(total_successful / success_denominator, 1.0)

            # ── Trust-weighted in-degree (who trusts you, weighted by their score) ─
            incoming_edges = (
                g.V().has('User', 'user_id', user_id)
                .inE('TRUSTS').has('status', 'accepted')
                .valueMap(True)
                .toList()
            )
            if not incoming_edges:
                trust_weighted_in = 0.0
            else:
                trust_weighted_in = min(
                    sum(float(self._unwrap_value(e.get('trust_score'), 0.0))
                        for e in incoming_edges) / len(incoming_edges),
                    1.0
                )

            # ── Vouch score ────────────────────────────────────────────────────
            vouch_score = await self.compute_vouch_score(user_id)

            reputation = min(max(
                avg_trust        * 0.35
                + success_rate   * 0.30
                + trust_weighted_in * 0.20
                + vouch_score    * 0.15,
                0.0
            ), 1.0)

            # Update vertex
            g.V().has('User', 'user_id', user_id) \
                .property('reputation_score', reputation) \
                .iterate()

            logger.info(f"✅ Updated reputation for {user_id}: {reputation:.3f}")
            return round(reputation, 3)

        except Exception as e:
            logger.error(f"❌ Failed to update reputation: {str(e)}")
            return 0.0
    
    async def decay_trust_scores(self, days_threshold: int = 180):
        """
        Scheduled job — run once daily alongside daily_interaction_decay.

        Recomputes recency_score for ALL TRUSTS edges using the live
        compute_recency_score() formula (not a binary flip to 0.1):

          recency_score = max(0, 1 - days_since_last_interaction / 90)

        Edges that have had NO interaction within `days_threshold` (default 180)
        are additionally hard-floored at 0.0 to signal a dead relationship.

        Also recomputes trust_score on any edge whose recency_score changed,
        keeping the stored value in sync with reality.
        """
        g = graph_client.get_traversal()

        try:
            all_edges = (
                g.E().hasLabel('TRUSTS').has('status', 'accepted')
                .project('from_uid', 'to_uid',
                         'last_interaction_at', 'interaction_count',
                         'successful_intros',   'interaction_decay_factor')
                .by(__.outV().values('user_id'))
                .by(__.inV().values('user_id'))
                .by(__.coalesce(__.values('last_interaction_at'), __.constant(None)))
                .by(__.coalesce(__.values('interaction_count'),   __.constant(0)))
                .by(__.coalesce(__.values('successful_intros'),   __.constant(0)))
                .by(__.coalesce(__.values('interaction_decay_factor'), __.constant(1.0)))
                .toList()
            )

            threshold_ts = (
                datetime.utcnow() - timedelta(days=days_threshold)
            ).timestamp()

            updated_count = 0
            for edge in all_edges:
                last_ts_raw = edge.get('last_interaction_at')
                last_ts     = float(last_ts_raw) if last_ts_raw else None
                from_uid    = str(edge['from_uid'])
                to_uid      = str(edge['to_uid'])

                # Compute fresh recency_score using live formula
                new_recency = self.compute_recency_score(last_ts)

                # Hard-floor dead relationships to 0.0
                if last_ts and last_ts < threshold_ts:
                    new_recency = 0.0

                # Recompute trust_score with updated recency
                count        = int(edge.get('interaction_count',        0) or 0)
                intros       = int(edge.get('successful_intros',        0) or 0)
                decay_factor = float(edge.get('interaction_decay_factor', 1.0) or 1.0)
                new_trust    = self.compute_score(
                    interaction_count=count,
                    successful_intros=intros,
                    last_interaction_at=last_ts,
                    interaction_decay_factor=decay_factor
                )

                (
                    g.V().has('User', 'user_id', from_uid)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', to_uid))
                    .property('recency_score', new_recency)
                    .property('trust_score',   new_trust)
                    .iterate()
                )
                updated_count += 1

            logger.info(
                f"✅ decay_trust_scores: {updated_count} edges recency scores refreshed"
            )
            return updated_count

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
            out_degree = g.V().has('User', 'user_id', user_id).outE('TRUSTS').has('status', 'accepted').count().next()
            in_degree = g.V().has('User', 'user_id', user_id).inE('TRUSTS').has('status', 'accepted').count().next()
            total_degree = out_degree + in_degree
            
            # Trust-weighted degree
            trust_sum = (
                g.V().has('User', 'user_id', user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .values('trust_score')
                .sum()
                .next()
            )
            
            # Approximate betweenness: count paths that go through this user
            # (Simplified metric - full betweenness is computationally expensive)
            betweenness_approx = (
                g.V().has('User', 'user_id', user_id)
                .bothE('TRUSTS').has('status', 'accepted').bothV()
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
                edge_list = (
                    g.V().has('User', 'user_id', from_id)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', to_id))
                    .valueMap(True)
                    .toList()
                )
                if not edge_list:
                    logger.warning(
                        f"Skipping trust boost for missing accepted edge {from_id}→{to_id}"
                    )
                    continue
                edge_data = edge_list[0]
                
                current_intros = edge_data.get('successful_intros', [0])[0]
                
                # First update counters so formula uses fresh values
                now_ts      = datetime.utcnow().timestamp()
                new_recency = self.compute_recency_score(now_ts)  # 1.0 (just interacted)
                g.V().has('User', 'user_id', from_id) \
                    .outE('TRUSTS').has('status', 'accepted') \
                    .where(__.inV().has('User', 'user_id', to_id)) \
                    .property('successful_intros',    current_intros + 1) \
                    .property('last_interaction_at',  now_ts) \
                    .property('recency_score',         new_recency) \
                    .iterate()
                
                # Recalculate score using the formula (not a flat boost)
                new_score = await self.calculate_trust_score(from_id, to_id)
                
                # Persist the recalculated score
                g.V().has('User', 'user_id', from_id) \
                    .outE('TRUSTS').has('status', 'accepted') \
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

    # ═══════════════════════════════════════════════════════════════
    # VOUCH SCORE
    # ═══════════════════════════════════════════════════════════════

    async def compute_vouch_score(self, user_id: str) -> float:
        """
        Compute a vouch score (0.0–1.0) for a user from their VOUCHES edges.

        Formula:
          vouch_score = mean(vouch_strength over active vouches), capped at 1.0
          Returns 0.0 if no vouches.

        The score is bounded to 0.10 maximum contribution in reputation_score
        to prevent vouch-farming from dominating.
        """
        g = graph_client.get_traversal()
        try:
            vouches = (
                g.V().has('User', 'user_id', user_id)
                .inE('VOUCHES')
                .has('is_revoked', False)
                .valueMap(True)
                .toList()
            )
            if not vouches:
                return 0.0
            total_strength = sum(
                float(self._unwrap_value(v.get('vouch_strength'), 0.5))
                for v in vouches
            )
            return round(min(total_strength / len(vouches), 1.0), 4)
        except Exception as e:
            logger.error(f"❌ compute_vouch_score failed: {e}")
            return 0.0

    # ═══════════════════════════════════════════════════════════════
    # ANTI-GAMING: SUSPICION FLAG
    # ═══════════════════════════════════════════════════════════════

    async def check_and_flag_suspicion(
        self, from_user_id: str, to_user_id: str
    ) -> bool:
        """
        Detect and flag suspicious reciprocal trust edges.

        A pair is flagged when ALL of:
          - Both trust scores are similarly high: |T(A→B) - T(B→A)| < 0.05
          - Total interaction count across both edges is < 3
            (high trust but no real interaction history → likely fabricated)

        Sets suspicion_flag = True on both edges.
        Flagged edges are excluded from path discovery traversal.
        Returns True if suspicion was detected and flagged.
        """
        g = graph_client.get_traversal()
        try:
            fwd = (
                g.V().has('User', 'user_id', from_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', to_user_id))
                .valueMap(True)
                .toList()
            )
            rev = (
                g.V().has('User', 'user_id', to_user_id)
                .outE('TRUSTS').has('status', 'accepted')
                .where(__.inV().has('User', 'user_id', from_user_id))
                .valueMap(True)
                .toList()
            )
            if not fwd or not rev:
                return False

            t_fwd = float(self._unwrap_value(fwd[0].get('trust_score'), 0.0))
            t_rev = float(self._unwrap_value(rev[0].get('trust_score'), 0.0))
            n_fwd = int(self._unwrap_value(fwd[0].get('interaction_count'), 0))
            n_rev = int(self._unwrap_value(rev[0].get('interaction_count'), 0))

            is_suspicious = (abs(t_fwd - t_rev) < 0.05) and ((n_fwd + n_rev) < 3)

            if is_suspicious:
                (
                    g.V().has('User', 'user_id', from_user_id)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', to_user_id))
                    .property('suspicion_flag', True)
                    .iterate()
                )
                (
                    g.V().has('User', 'user_id', to_user_id)
                    .outE('TRUSTS').has('status', 'accepted')
                    .where(__.inV().has('User', 'user_id', from_user_id))
                    .property('suspicion_flag', True)
                    .iterate()
                )
                logger.warning(
                    f"⚠️ Suspicion flagged: {from_user_id} ↔ {to_user_id} "
                    f"(T_fwd={t_fwd:.3f}, T_rev={t_rev:.3f}, interactions={n_fwd + n_rev})"
                )
            return is_suspicious

        except Exception as e:
            logger.error(f"❌ check_and_flag_suspicion failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # EIGENTRUST — GLOBAL RANK BATCH JOB
    # ═══════════════════════════════════════════════════════════════

    async def compute_eigen_trust_ranks(self) -> int:
        """
        Compute a global EigenTrust rank for every user and persist it as
        `eigen_trust_rank` on User vertices.

        Algorithm (power iteration, ~50 steps):
          1. Build normalized transition matrix C where
               C[j→i] = T(j→i) / Σ_k T(j→k)
          2. Start with uniform rank vector t[i] = 1/N
          3. Iterate: t_new[i] = Σ_j C[j→i] * t[j]
          4. Re-normalize after each step.
          5. After convergence, persist t[i] to each User vertex.

        A high eigen_trust_rank means many high-trust nodes transitively
        point to this user — a robust Sybil-resistant reputation signal.
        """
        g = graph_client.get_traversal()
        try:
            all_edges = (
                g.E().hasLabel('TRUSTS').has('status', 'accepted')
                .project('from_uid', 'to_uid', 'trust_score')
                .by(__.outV().values('user_id'))
                .by(__.inV().values('user_id'))
                .by(__.coalesce(__.values('trust_score'), __.constant(0.0)))
                .toList()
            )

            if not all_edges:
                logger.info("⚠️ EigenTrust: no accepted TRUSTS edges found — skipping")
                return 0

            # Build out-weight sums per node
            out_weights: Dict[str, float] = {}
            all_users: set = set()
            for e in all_edges:
                src = str(e['from_uid'])
                dst = str(e['to_uid'])
                t   = float(e.get('trust_score') or 0.0)
                out_weights[src] = out_weights.get(src, 0.0) + t
                all_users.add(src)
                all_users.add(dst)

            # Normalized transition weights: C[src→dst]
            transitions: Dict[tuple, float] = {}
            for e in all_edges:
                src   = str(e['from_uid'])
                dst   = str(e['to_uid'])
                t     = float(e.get('trust_score') or 0.0)
                denom = out_weights.get(src, 0.0)
                if denom > 0:
                    transitions[(src, dst)] = t / denom

            n = len(all_users)
            rank: Dict[str, float] = {u: 1.0 / n for u in all_users}

            # Power iteration
            for _ in range(50):
                new_rank: Dict[str, float] = {u: 0.0 for u in all_users}
                for (src, dst), weight in transitions.items():
                    new_rank[dst] = new_rank.get(dst, 0.0) + weight * rank.get(src, 0.0)
                total = sum(new_rank.values()) or 1.0
                rank = {u: v / total for u, v in new_rank.items()}

            # Persist to User vertices
            updated = 0
            for uid, eigen_rank in rank.items():
                try:
                    g.V().has('User', 'user_id', uid) \
                        .property('eigen_trust_rank', round(eigen_rank, 6)) \
                        .iterate()
                    updated += 1
                except Exception:
                    pass

            logger.info(f"✅ EigenTrust ranks computed and stored for {updated} users")
            return updated

        except Exception as e:
            logger.error(f"❌ compute_eigen_trust_ranks failed: {e}")
            return 0

# Singleton instance
trust_scoring_service = TrustScoringService()
