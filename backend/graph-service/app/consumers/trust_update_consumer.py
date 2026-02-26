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

async def main():
    """Start Kafka consumer for trust updates"""
    consumer = KafkaEventConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="trust-update-group",
        topics=["intro-events", "graph-events"]
    )
    
    # Register event handlers
    consumer.register_handler("intro_completed", handle_intro_completed)
    consumer.register_handler("trust_edge_created", handle_trust_edge_created)
    
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
