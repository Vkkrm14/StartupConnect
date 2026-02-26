"""Kafka consumer for handling intro workflow events"""

import asyncio
import logging
import sys
sys.path.append("/app/shared")
from messaging.kafka_consumer import KafkaEventConsumer

from app.core.config import settings
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

async def handle_intro_created(data: dict):
    """Handle intro_created event - send notification to first intermediary"""
    try:
        intro_id = data.get("intro_id")
        requester_id = data.get("requester_id")
        investor_id = data.get("investor_id")
        path_nodes = data.get("path_nodes", [])
        message = data.get("message")
        
        if not path_nodes:
            logger.warning(f"intro_created event for {intro_id} has no path_nodes")
            return
        
        # Send notification to first intermediary
        first_intermediary = path_nodes[0]
        await notification_service.send_intro_request_notification(
            intro_id=intro_id,
            requester_name=requester_id,
            target_name=investor_id,
            intermediary_id=first_intermediary,
            message=message
        )
        
        logger.info(f"✅ Sent intro_created notification for {intro_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle intro_created event: {e}")

async def handle_intro_approved(data: dict):
    """Handle intro_approved event - send notifications"""
    try:
        intro_id = data.get("intro_id")
        approver_id = data.get("approver_id")
        requester_id = data.get("requester_id")
        next_intermediary_id = data.get("next_intermediary_id")
        
        # Notify requester that intro was approved
        await notification_service.send_intro_approved_notification(
            intro_id=intro_id,
            requester_id=requester_id,
            approver_name=approver_id
        )
        
        # If there's a next intermediary, notify them
        if next_intermediary_id:
            await notification_service.send_intro_request_notification(
                intro_id=intro_id,
                requester_name=requester_id,
                target_name=data.get("investor_id", ""),
                intermediary_id=next_intermediary_id,
                message=data.get("message")
            )
        
        logger.info(f"✅ Sent intro_approved notifications for {intro_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle intro_approved event: {e}")

async def handle_intro_declined(data: dict):
    """Handle intro_declined event - send notification"""
    try:
        intro_id = data.get("intro_id")
        decliner_id = data.get("decliner_id")
        requester_id = data.get("requester_id")
        reason = data.get("reason")
        
        # Notify requester that intro was declined
        await notification_service.send_intro_declined_notification(
            intro_id=intro_id,
            requester_id=requester_id,
            decliner_name=decliner_id,
            reason=reason
        )
        
        logger.info(f"✅ Sent intro_declined notification for {intro_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle intro_declined event: {e}")

async def handle_intro_completed(data: dict):
    """Handle intro_completed event - send completion notifications"""
    try:
        intro_id = data.get("intro_id")
        requester_id = data.get("requester_id")
        investor_id = data.get("investor_id")
        path_user_ids = data.get("path_user_ids", [])
        
        # Notify requester
        await notification_service.send_intro_completed_notification(
            intro_id=intro_id,
            requester_id=requester_id,
            investor_name=investor_id
        )
        
        # Notify all intermediaries about trust boost
        for user_id in path_user_ids:
            if user_id not in [requester_id, investor_id]:
                await notification_service.send_trust_connection_notification(
                    user_id=user_id,
                    connection_name=requester_id,
                    trust_boost=0.05
                )
        
        logger.info(f"✅ Sent intro_completed notifications for {intro_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to handle intro_completed event: {e}")

async def main():
    """Start Kafka consumer for intro workflow events"""
    consumer = KafkaEventConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="intro-workflow-group",
        topics=["intro-events"]
    )
    
    # Register event handlers
    consumer.register_handler("intro_created", handle_intro_created)
    consumer.register_handler("intro_approved", handle_intro_approved)
    consumer.register_handler("intro_declined", handle_intro_declined)
    consumer.register_handler("intro_completed", handle_intro_completed)
    
    logger.info("🎧 Starting intro workflow consumer...")
    
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
