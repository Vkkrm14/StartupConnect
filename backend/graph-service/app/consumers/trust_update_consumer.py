"""Kafka consumer for handling trust updates from intro completions"""

import asyncio
import logging
import sys
sys.path.append("/app/shared")
from messaging.kafka_consumer import KafkaEventConsumer

from app.core.config import settings
from app.services.trust_scoring import trust_scoring_service

logger = logging.getLogger(__name__)

async def handle_intro_completed(data: dict):
    """Handle intro_completed event - boost trust scores along path"""
    try:
        intro_id = data.get("intro_id")
        path_user_ids = data.get("path_user_ids", [])
        
        if not path_user_ids:
            logger.warning(f"intro_completed event for {intro_id} has no path_user_ids")
            return
        
        # Boost trust scores along the path
        await trust_scoring_service.boost_trust_for_successful_intro(
            path_user_ids=path_user_ids,
            boost_amount=0.05
        )
        
        logger.info(f"✅ Boosted trust scores for intro {intro_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle intro_completed event: {e}")

async def handle_trust_edge_created(data: dict):
    """Handle trust_edge_created event - update reputation scores"""
    try:
        from_user_id = data.get("from_user_id")
        to_user_id = data.get("to_user_id")
        
        if not from_user_id or not to_user_id:
            logger.warning("trust_edge_created event missing user IDs")
            return
        
        # Update reputation scores for both users
        await trust_scoring_service.update_reputation_score(from_user_id)
        await trust_scoring_service.update_reputation_score(to_user_id)
        
        logger.info(f"✅ Updated reputation scores for {from_user_id} and {to_user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle trust_edge_created event: {e}")

async def handle_message_sent(data: dict):
    """
    Handle message_sent event from messaging-service.

    Increments interaction_count on the TRUSTS edge (if it exists)
    between sender and recipient, then recomputes trust + reputation.

    Rate-limited to 1 credit per hour per sender→recipient pair so
    that spamming messages cannot artificially inflate trust scores.
    """
    try:
        sender_id    = data.get("sender_id")
        recipient_id = data.get("recipient_id")

        if not sender_id or not recipient_id:
            logger.warning(f"message_sent event missing sender/recipient: {data}")
            return

        result = await trust_scoring_service.record_interaction(
            from_user_id=sender_id,
            to_user_id=recipient_id,
        )

        if result["status"] == "updated":
            logger.info(
                f"✅ Interaction recorded {sender_id}→{recipient_id}: "
                f"count={result['new_interaction_count']}, "
                f"trust={result['new_trust_score']:.4f}"
            )
        elif result["status"] == "rate_limited":
            logger.debug(
                f"⏱ Interaction rate-limited {sender_id}→{recipient_id}: "
                f"retry in {result['retry_after_hours']:.2f}h"
            )
        elif result["status"] == "no_edge":
            logger.debug(
                f"ℹ No TRUSTS edge {sender_id}→{recipient_id}, skipping interaction credit"
            )

    except Exception as e:
        logger.error(f"❌ Failed to handle message_sent event: {e}")

async def main():
    """Start Kafka consumer for trust updates"""
    consumer = KafkaEventConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="trust-update-group",
        topics=["intro-events", "graph-events", "messaging-events"]
    )
    
    # Register event handlers
    consumer.register_handler("intro_completed",    handle_intro_completed)
    consumer.register_handler("trust_edge_created", handle_trust_edge_created)
    consumer.register_handler("message_sent",       handle_message_sent)
    
    logger.info("🎧 Starting trust update consumer...")
    
    try:
        consumer.connect()
        await consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("⚠️ Received interrupt, shutting down...")
    finally:
        consumer.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
