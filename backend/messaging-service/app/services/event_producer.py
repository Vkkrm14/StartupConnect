import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.core.config import settings

logger = logging.getLogger(__name__)

TOPIC_MESSAGE_EVENTS = "messaging-events"
TOPIC_NOTIFICATION_EVENTS = "notification-events"
TOPIC_AUDIT_LOG = "messaging-audit"


class MessageEventProducer:
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None

    def connect(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                max_in_flight_requests_per_connection=1,
            )
            logger.info("Kafka producer connected")
        except KafkaError as e:
            logger.error(f"Failed to connect Kafka producer: {e}")

    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()

    def _publish(self, topic: str, key: Optional[str], event: dict) -> bool:
        if not self.producer:
            logger.warning("Kafka producer not connected, dropping event")
            return False
        try:
            future = self.producer.send(topic, value=event, key=key)
            future.get(timeout=10)
            return True
        except KafkaError as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False

    async def emit_message_sent(self, message: dict, recipient_id: str = None):
        event = {
            "event_type": "message_sent",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id":      message["message_id"],
                "conversation_id": message["conversation_id"],
                "sender_id":       message["sender_id"],
                "recipient_id":    recipient_id,          # needed for trust score update
                "message_type":    message["message_type"],
                "created_at":      message["created_at"],
            },
        }
        self._publish(TOPIC_MESSAGE_EVENTS, message["conversation_id"], event)

        notification = {
            "event_type": "new_message_notification",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "conversation_id": message["conversation_id"],
                "sender_id": message["sender_id"],
                "message_type": message["message_type"],
            },
        }
        self._publish(TOPIC_NOTIFICATION_EVENTS, message["conversation_id"], notification)

    async def emit_message_read(self, conversation_id: str, user_id: str, message_id: str):
        event = {
            "event_type": "message_read",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "message_id": message_id,
            },
        }
        self._publish(TOPIC_MESSAGE_EVENTS, conversation_id, event)

    async def emit_conversation_created(self, conversation: dict):
        event = {
            "event_type": "conversation_created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "conversation_id": conversation["conversation_id"],
                "participants": conversation["participants"],
            },
        }
        self._publish(TOPIC_MESSAGE_EVENTS, conversation["conversation_id"], event)

    async def emit_image_uploaded(self, conversation_id: str, sender_id: str, file_id: str):
        event = {
            "event_type": "image_uploaded",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "file_id": file_id,
            },
        }
        self._publish(TOPIC_MESSAGE_EVENTS, conversation_id, event)

    async def emit_user_blocked(self, blocker_id: str, blocked_id: str):
        event = {
            "event_type": "user_blocked",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "blocker_id": blocker_id,
                "blocked_id": blocked_id,
            },
        }
        self._publish(TOPIC_AUDIT_LOG, blocker_id, event)

    async def emit_audit_event(self, event_type: str, user_id: str, details: dict):
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"user_id": user_id, **details},
        }
        self._publish(TOPIC_AUDIT_LOG, user_id, event)


event_producer = MessageEventProducer()
