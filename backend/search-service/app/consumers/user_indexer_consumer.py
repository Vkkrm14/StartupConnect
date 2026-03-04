"""Kafka consumer for indexing users in Elasticsearch"""

import asyncio
import logging
import sys
sys.path.append("/app/shared")
from messaging.kafka_consumer import KafkaEventConsumer

from app.core.config import settings
from app.services.indexer import indexer_service

logger = logging.getLogger(__name__)

async def handle_user_created(data: dict):
    """Handle user_created event - index user in Elasticsearch"""
    try:
        user_id = data.get("user_id")
        if not user_id:
            logger.error("user_created event missing user_id")
            return
        
        # Prepare user document for indexing
        user_doc = {
            "user_id": user_id,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "role_primary": data.get("role_primary", ""),
            "domain_tags": data.get("domain_tags", []),
            "geography": data.get("geography"),
            "reputation_score": data.get("reputation_score", 0.0),
        }
        
        # Index in Elasticsearch
        await indexer_service.index_user(user_doc)
        logger.info(f"✅ Indexed user {user_id} in Elasticsearch")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle user_created event: {e}")

async def handle_startup_created(data: dict):
    """Handle startup_created event - index startup in Elasticsearch"""
    try:
        startup_id = data.get("startup_id")
        if not startup_id:
            logger.error("startup_created event missing startup_id")
            return
        
        # Prepare startup document for indexing
        startup_doc = {
            "startup_id": startup_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "domain_tags": data.get("domain_tags", []),
            "stage": data.get("stage"),
            "geography": data.get("geography"),
            "founded_date": data.get("founded_date"),
        }
        
        # Index in Elasticsearch
        await indexer_service.index_startup(startup_doc)
        logger.info(f"✅ Indexed startup {startup_id} in Elasticsearch")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle startup_created event: {e}")

async def handle_profile_updated(data: dict):
    """Handle profile_updated event - reindex user"""
    try:
        user_id = data.get("user_id")
        if not user_id:
            return
        
        user_doc = {
            "user_id": user_id,
            "name": data.get("name"),
            "bio": data.get("bio"),
            "domain_tags": data.get("domain_tags", []),
            "geography": data.get("geography"),
        }
        
        # Remove None values
        user_doc = {k: v for k, v in user_doc.items() if v is not None}
        
        await indexer_service.index_user(user_doc)
        logger.info(f"✅ Reindexed user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle profile_updated event: {e}")

async def main():
    """Start Kafka consumer for search indexing"""
    consumer = KafkaEventConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="search-indexer-group",
        topics=["user-events", "startup-events"]
    )
    
    # Register event handlers
    consumer.register_handler("user_created", handle_user_created)
    consumer.register_handler("startup_created", handle_startup_created)
    consumer.register_handler("profile_updated", handle_profile_updated)
    
    logger.info("🎧 Starting search indexer consumer...")
    
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
