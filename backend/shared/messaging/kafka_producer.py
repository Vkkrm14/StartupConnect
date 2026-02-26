"""Kafka Event Producer"""

from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    """Kafka event producer for publishing events"""
    
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[KafkaProducer] = None
    
    def connect(self):
        """Connect to Kafka cluster"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info(f"✅ Connected to Kafka: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {str(e)}")
            raise
    
    def close(self):
        """Close Kafka connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("🔌 Closed Kafka connection")
    
    async def publish_event(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Publish event to Kafka topic
        
        Args:
            topic: Kafka topic name
            event_type: Type of event (e.g., "intro_created", "trust_updated")
            data: Event payload
            key: Optional partition key
        
        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            logger.error("Kafka producer not connected")
            return False
        
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        try:
            future = self.producer.send(
                topic,
                value=event,
                key=key.encode('utf-8') if key else None
            )
            
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"📤 Published event: {event_type} to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"❌ Failed to publish event: {str(e)}")
            return False
    
    async def publish_intro_event(
        self,
        event_type: str,
        intro_id: str,
        data: Dict[str, Any]
    ):
        """Publish intro-related event"""
        await self.publish_event(
            topic="intro-events",
            event_type=event_type,
            data={
                "intro_id": intro_id,
                **data
            },
            key=intro_id
        )
    
    async def publish_trust_update(
        self,
        from_user_id: str,
        to_user_id: str,
        trust_score: float,
        reason: str
    ):
        """Publish trust score update event"""
        await self.publish_event(
            topic="trust-updates",
            event_type="trust_updated",
            data={
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "trust_score": trust_score,
                "reason": reason
            },
            key=f"{from_user_id}:{to_user_id}"
        )
