"""
Backfill trust scores for all existing TRUSTS edges.

Runs standalone on host - no app imports, no .env dependency.
Connects directly to JanusGraph via gremlin-python.

Usage:
    python backend/scripts/backfill_trust_scores.py
    python backend/scripts/backfill_trust_scores.py --url ws://100.70.53.90:8182/gremlin
"""

import argparse
import logging
from datetime import datetime

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.serializer import GraphBinarySerializersV1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ── Inline trust score formula (mirrors trust_scoring.py compute_score) ──────
def compute_score(
    interaction_count: int,
    successful_intros: int,
    last_interaction_at: float = None
) -> float:
    """
    interaction_bonus : min(interaction_count / 20, 1.0) * 0.40
    success_bonus     : min(successful_intros  / 10, 1.0) * 0.40
    recency_bonus     : up to 0.20, decays linearly over 90 days
    """
    interaction_bonus = min(interaction_count / 20.0, 1.0) * 0.40
    success_bonus     = min(successful_intros  / 10.0, 1.0) * 0.40

    recency_bonus = 0.0
    if last_interaction_at:
        days_since = (datetime.utcnow().timestamp() - last_interaction_at) / 86400
        if days_since <= 90:
            recency_bonus = (1 - days_since / 90) * 0.20

    return round(min(interaction_bonus + success_bonus + recency_bonus, 1.0), 4)


def backfill(janusgraph_url: str):
    logger.info(f"🔌 Connecting to JanusGraph at {janusgraph_url}")

    connection = DriverRemoteConnection(
        janusgraph_url, 'g',
        message_serializer=GraphBinarySerializersV1()
    )
    g = traversal().withRemote(connection)

    try:
        # ── Fetch all TRUSTS edges ────────────────────────────────────────────
        logger.info("🔍 Fetching all TRUSTS edges...")

        edges = (
            g.E().hasLabel('TRUSTS')
            .project('from_user_id', 'to_user_id', 'old_score',
                     'interaction_count', 'successful_intros', 'last_interaction_at')
            .by(__.outV().values('user_id'))
            .by(__.inV().values('user_id'))
            .by(__.values('trust_score'))
            .by(__.coalesce(__.values('interaction_count'),  __.constant(0)))
            .by(__.coalesce(__.values('successful_intros'),  __.constant(0)))
            .by(__.coalesce(__.values('last_interaction_at'), __.constant(None)))
            .toList()
        )

        logger.info(f"📊 Found {len(edges)} TRUSTS edges")

        if not edges:
            logger.info("Nothing to backfill.")
            return

        updated = 0
        skipped = 0
        failed  = 0

        for edge in edges:
            from_id           = edge['from_user_id']
            to_id             = edge['to_user_id']
            old_score         = float(edge['old_score'])
            interaction_count = int(edge['interaction_count'] or 0)
            successful_intros = int(edge['successful_intros'] or 0)
            last_ts_raw       = edge.get('last_interaction_at')
            last_ts           = float(last_ts_raw) if last_ts_raw else None

            try:
                new_score = compute_score(
                    interaction_count=interaction_count,
                    successful_intros=successful_intros,
                    last_interaction_at=last_ts
                )

                if abs(new_score - old_score) < 0.0001:
                    skipped += 1
                    continue

                g.V().has('User', 'user_id', from_id) \
                    .outE('TRUSTS') \
                    .where(__.inV().has('User', 'user_id', to_id)) \
                    .property('trust_score', new_score) \
                    .property('updated_at', int(datetime.utcnow().timestamp())) \
                    .iterate()

                logger.info(
                    f"  ✅ {from_id[:8]}…→{to_id[:8]}…  "
                    f"interactions={interaction_count}  intros={successful_intros}  "
                    f"{old_score:.4f} → {new_score:.4f}"
                )
                updated += 1

            except Exception as e:
                logger.error(f"  ❌ {from_id} → {to_id}: {e}")
                failed += 1

        # ── Refresh reputation scores ─────────────────────────────────────────
        logger.info("\n🔄 Refreshing reputation scores for all users...")

        user_ids = g.V().hasLabel('User').values('user_id').toList()
        rep_ok = 0

        for user_id in user_ids:
            try:
                outgoing = (
                    g.V().has('User', 'user_id', user_id)
                    .outE('TRUSTS')
                    .valueMap('trust_score', 'interaction_count', 'successful_intros')
                    .toList()
                )

                if not outgoing:
                    reputation = 0.0
                else:
                    def _v(val, default):
                        return val[0] if isinstance(val, list) else (val if val is not None else default)
                    avg_trust = sum(
                        float(_v(e.get('trust_score'), 0.0)) for e in outgoing
                    ) / len(outgoing)
                    total_interactions = sum(int(_v(e.get('interaction_count'), 0)) for e in outgoing)
                    total_successes    = sum(int(_v(e.get('successful_intros'),  0)) for e in outgoing)
                    success_rate = total_successes / total_interactions if total_interactions > 0 else 0.0
                    reputation = round((avg_trust * 0.6) + (success_rate * 0.4), 4)

                g.V().has('User', 'user_id', user_id) \
                    .property('reputation_score', reputation) \
                    .iterate()

                rep_ok += 1

            except Exception as e:
                logger.warning(f"  ⚠️  Reputation failed for {user_id}: {e}")

        logger.info(
            f"\n{'='*55}\n"
            f"  TRUSTS edges  : {len(edges)}\n"
            f"  Updated       : {updated}\n"
            f"  Skipped (same): {skipped}\n"
            f"  Failed        : {failed}\n"
            f"  Reputations   : {rep_ok}/{len(user_ids)} users refreshed\n"
            f"{'='*55}"
        )

    finally:
        connection.close()
        logger.info("🔌 Connection closed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill trust scores in JanusGraph")
    parser.add_argument(
        "--url",
        default="ws://100.70.53.90:8182/gremlin",
        help="JanusGraph Gremlin WebSocket URL (default: ws://100.70.53.90:8182/gremlin)"
    )
    args = parser.parse_args()
    backfill(args.url)