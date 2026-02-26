"""Kafka Event Consumer"""

from typing import Callable, Dict, Any
import json
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

class KafkaEventConsumer:
    """Kafka event consumer for subscribing to events"""
    
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.consumer = None
        self.handlers: Dict[str, Callable] = {}
    
    def connect(self):
        """Connect to Kafka and subscribe to topics"""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers.split(','),
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info(f"✅ Subscribed to Kafka topics: {self.topics}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {str(e)}")
            raise
    
    def close(self):
        """Close Kafka consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("🔌 Closed Kafka consumer")
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register event handler
        
        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        self.handlers[event_type] = handler
        logger.info(f"📝 Registered handler for: {event_type}")
    
    async def start_consuming(self):
        """Start consuming events"""
        if not self.consumer:
            raise RuntimeError("Consumer not connected")
        
        logger.info("🎧 Starting event consumer...")
        
        try:
            for message in self.consumer:
                event = message.value
                event_type = event.get("event_type")
                
                logger.info(f"📥 Received event: {event_type} from {message.topic}")
                
                # Find and execute handler
                handler = self.handlers.get(event_type)
                if handler:
                    try:
                        await handler(event.get("data", {}))
                    except Exception as e:
                        logger.error(f"❌ Handler error for {event_type}: {str(e)}")
                else:
                    logger.warning(f"⚠️  No handler registered for: {event_type}")
                    
        except KafkaError as e:
            logger.error(f"❌ Consumer error: {str(e)}")
            raise
