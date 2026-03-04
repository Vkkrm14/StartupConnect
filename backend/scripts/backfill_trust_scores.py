"""
Backfill trust scores for all existing TRUSTS edges using the current formula.

Run this after deploying the updated trust_scoring.py to fix any stale
hardcoded scores (e.g. from seed data seeded before the formula was written).

Usage (inside the graph-service container):
    docker compose exec graph-service python scripts/backfill_trust_scores.py
"""

import asyncio
import logging
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/shared")

from app.core.graph_client import graph_client
from app.services.trust_scoring import trust_scoring_service
from gremlin_python.process.graph_traversal import __

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


async def backfill():
    g = graph_client.get_traversal()

    logger.info("🔍 Fetching all TRUSTS edges from JanusGraph...")

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

    logger.info(f"📊 Found {len(edges)} TRUSTS edges to backfill")

    updated = 0
    skipped = 0
    failed  = 0

    for edge in edges:
        from_id          = edge['from_user_id']
        to_id            = edge['to_user_id']
        old_score        = edge['old_score']
        interaction_count = int(edge['interaction_count'] or 0)
        successful_intros = int(edge['successful_intros'] or 0)
        last_interaction  = edge.get('last_interaction_at')
        last_ts           = float(last_interaction) if last_interaction else None

        try:
            # Recalculate using the formula directly (no extra graph query)
            new_score = trust_scoring_service.compute_score(
                interaction_count=interaction_count,
                successful_intros=successful_intros,
                last_interaction_at=last_ts
            )

            if abs(new_score - float(old_score)) < 0.0001:
                skipped += 1
                continue

            # Write new score back
            g.V().has('User', 'user_id', from_id) \
                .outE('TRUSTS') \
                .where(__.inV().has('User', 'user_id', to_id)) \
                .property('trust_score', new_score) \
                .iterate()

            logger.info(
                f"  ✅ {from_id[:8]}… → {to_id[:8]}…  "
                f"interactions={interaction_count}  intros={successful_intros}  "
                f"old={float(old_score):.4f} → new={new_score:.4f}"
            )
            updated += 1

        except Exception as e:
            logger.error(f"  ❌ {from_id} → {to_id}: {e}")
            failed += 1

    # Refresh reputation scores for every user touched
    logger.info("\n🔄 Refreshing reputation scores for all users...")
    users = g.V().hasLabel('User').values('user_id').toList()
    rep_updated = 0
    for user_id in users:
        try:
            await trust_scoring_service.update_reputation_score(user_id)
            rep_updated += 1
        except Exception as e:
            logger.warning(f"  ⚠️  Reputation update failed for {user_id}: {e}")

    logger.info(
        f"\n{'='*55}\n"
        f"  TRUSTS edges  : {len(edges)}\n"
        f"  Updated       : {updated}\n"
        f"  Skipped (same): {skipped}\n"
        f"  Failed        : {failed}\n"
        f"  Reputations   : {rep_updated}/{len(users)} users refreshed\n"
        f"{'='*55}"
    )


if __name__ == "__main__":
    asyncio.run(backfill())
