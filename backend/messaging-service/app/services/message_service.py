import logging
import uuid
import base64
import json
from datetime import datetime
from typing import Optional, List, Tuple

from cassandra.query import SimpleStatement

from app.core.cassandra import cassandra_client
from app.core.config import settings

logger = logging.getLogger(__name__)

INSERT_MESSAGE = """
    INSERT INTO messages_by_conversation
    (conversation_id, message_ts, message_id, sender_id, encrypted_payload, encrypted_key, message_type, metadata, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

INSERT_MESSAGE_BY_ID = """
    INSERT INTO message_by_id
    (message_id, conversation_id, sender_id, message_ts, encrypted_payload, encrypted_key, message_type, metadata, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

SELECT_MESSAGES = """
    SELECT message_id, sender_id, encrypted_payload, encrypted_key, message_type, metadata, message_ts, created_at
    FROM messages_by_conversation
    WHERE conversation_id = %s
"""

SELECT_MESSAGES_BEFORE = """
    SELECT message_id, sender_id, encrypted_payload, encrypted_key, message_type, metadata, message_ts, created_at
    FROM messages_by_conversation
    WHERE conversation_id = %s AND message_ts < %s
"""

SELECT_MESSAGE_BY_ID = """
    SELECT message_id, conversation_id, sender_id, message_ts, encrypted_payload, encrypted_key, message_type, metadata, created_at
    FROM message_by_id
    WHERE message_id = %s
"""


class MessageService:
    def __init__(self):
        self.session = None

    def _get_session(self):
        if not self.session:
            self.session = cassandra_client.get_session()
        return self.session

    async def store_message(
        self,
        conversation_id: str,
        sender_id: str,
        encrypted_payload: str,
        message_type: str,
        encrypted_key: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        session = self._get_session()
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()
        payload_bytes = base64.b64decode(encrypted_payload)
        metadata_str = json.dumps(metadata) if metadata else None

        session.execute(
            INSERT_MESSAGE,
            (
                conversation_id,
                now,
                message_id,
                sender_id,
                payload_bytes,
                encrypted_key,
                message_type,
                metadata_str,
                now,
            ),
        )

        session.execute(
            INSERT_MESSAGE_BY_ID,
            (
                message_id,
                conversation_id,
                sender_id,
                now,
                payload_bytes,
                encrypted_key,
                message_type,
                metadata_str,
                now,
            ),
        )

        return {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "encrypted_payload": encrypted_payload,
            "encrypted_key": encrypted_key,
            "message_type": message_type,
            "metadata": metadata,
            "created_at": now.isoformat(),
        }

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = None,
        before: Optional[str] = None,
    ) -> Tuple[List[dict], bool]:
        session = self._get_session()
        page_size = limit or settings.MESSAGE_PAGE_SIZE
        fetch_count = page_size + 1

        if before:
            cursor_time = datetime.fromisoformat(before)
            stmt = SimpleStatement(
                SELECT_MESSAGES_BEFORE + " ORDER BY message_ts DESC LIMIT %s",
                fetch_size=fetch_count,
            )
            rows = session.execute(stmt, (conversation_id, cursor_time, fetch_count))
        else:
            stmt = SimpleStatement(
                SELECT_MESSAGES + " ORDER BY message_ts DESC LIMIT %s",
                fetch_size=fetch_count,
            )
            rows = session.execute(stmt, (conversation_id, fetch_count))

        results = list(rows)
        has_more = len(results) > page_size
        if has_more:
            results = results[:page_size]

        messages = []
        for row in results:
            payload_b64 = base64.b64encode(row.encrypted_payload).decode() if row.encrypted_payload else ""
            meta = json.loads(row.metadata) if row.metadata else None
            messages.append({
                "message_id": row.message_id,
                "conversation_id": conversation_id,
                "sender_id": row.sender_id,
                "encrypted_payload": payload_b64,
                "encrypted_key": row.encrypted_key,
                "message_type": row.message_type,
                "metadata": meta,
                "created_at": row.message_ts.isoformat() if row.message_ts else None,
            })

        return messages, has_more

    async def get_message_by_id(self, message_id: str) -> Optional[dict]:
        session = self._get_session()
        stmt = SimpleStatement(SELECT_MESSAGE_BY_ID)
        rows = session.execute(stmt, (message_id,))
        row = rows.one()
        if not row:
            return None
        payload_b64 = base64.b64encode(row.encrypted_payload).decode() if row.encrypted_payload else ""
        meta = json.loads(row.metadata) if row.metadata else None
        return {
            "message_id": row.message_id,
            "conversation_id": row.conversation_id,
            "sender_id": row.sender_id,
            "encrypted_payload": payload_b64,
            "encrypted_key": row.encrypted_key,
            "message_type": row.message_type,
            "metadata": meta,
            "created_at": row.message_ts.isoformat() if row.message_ts else None,
        }


message_service = MessageService()
