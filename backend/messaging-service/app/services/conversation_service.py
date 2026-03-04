import logging
import uuid
from datetime import datetime
from typing import Optional, List

from app.core.mongodb import mongo_client

logger = logging.getLogger(__name__)


class ConversationService:
    def _get_db(self):
        return mongo_client.get_db()

    def _make_conversation_id(self, user_a: str, user_b: str) -> str:
        return ":".join(sorted([user_a, user_b]))

    async def get_or_create_conversation(self, user_id: str, participant_id: str) -> dict:
        db = self._get_db()
        conversation_id = self._make_conversation_id(user_id, participant_id)

        existing = await db.conversations.find_one({"conversation_id": conversation_id})
        if existing:
            existing["_id"] = str(existing["_id"])
            return existing

        now = datetime.utcnow()
        doc = {
            "conversation_id": conversation_id,
            "participants": sorted([user_id, participant_id]),
            "created_at": now,
            "updated_at": now,
            "last_message_preview": None,
            "last_message_at": None,
            "last_message_type": None,
        }
        await db.conversations.insert_one(doc)
        doc["_id"] = str(doc["_id"])
        return doc

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        db = self._get_db()
        doc = await db.conversations.find_one({"conversation_id": conversation_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_user_conversations(self, user_id: str, skip: int = 0, limit: int = 50) -> List[dict]:
        db = self._get_db()
        cursor = (
            db.conversations.find({"participants": user_id})
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    async def get_user_conversation_count(self, user_id: str) -> int:
        db = self._get_db()
        return await db.conversations.count_documents({"participants": user_id})

    async def update_last_message(
        self,
        conversation_id: str,
        message_type: str,
        timestamp: datetime,
        preview: Optional[str] = None,
    ):
        db = self._get_db()
        update = {
            "$set": {
                "updated_at": timestamp,
                "last_message_at": timestamp,
                "last_message_type": message_type,
                "last_message_preview": preview,
            }
        }
        await db.conversations.update_one(
            {"conversation_id": conversation_id}, update
        )

    async def is_participant(self, conversation_id: str, user_id: str) -> bool:
        db = self._get_db()
        doc = await db.conversations.find_one(
            {"conversation_id": conversation_id, "participants": user_id},
            {"_id": 1},
        )
        return doc is not None

    async def get_other_participant(self, conversation_id: str, user_id: str) -> Optional[str]:
        doc = await self.get_conversation(conversation_id)
        if not doc:
            return None
        participants = doc.get("participants", [])
        for p in participants:
            if p != user_id:
                return p
        return None

    # ---- Block list ----

    async def block_user(self, blocker_id: str, blocked_id: str):
        db = self._get_db()
        await db.user_blocks.update_one(
            {"blocker_id": blocker_id, "blocked_id": blocked_id},
            {
                "$set": {
                    "blocker_id": blocker_id,
                    "blocked_id": blocked_id,
                    "blocked_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

    async def unblock_user(self, blocker_id: str, blocked_id: str):
        db = self._get_db()
        await db.user_blocks.delete_one(
            {"blocker_id": blocker_id, "blocked_id": blocked_id}
        )

    async def is_blocked(self, user_a: str, user_b: str) -> bool:
        db = self._get_db()
        block = await db.user_blocks.find_one(
            {
                "$or": [
                    {"blocker_id": user_a, "blocked_id": user_b},
                    {"blocker_id": user_b, "blocked_id": user_a},
                ]
            }
        )
        return block is not None

    async def get_blocked_users(self, user_id: str) -> List[str]:
        db = self._get_db()
        cursor = db.user_blocks.find({"blocker_id": user_id})
        blocked = []
        async for doc in cursor:
            blocked.append(doc["blocked_id"])
        return blocked

    # ---- Encryption keys ----

    async def store_encryption_key(self, user_id: str, public_key: str, key_type: str = "x25519"):
        db = self._get_db()
        await db.user_encryption_keys.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "public_key": public_key,
                    "key_type": key_type,
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

    async def get_encryption_key(self, user_id: str) -> Optional[dict]:
        db = self._get_db()
        doc = await db.user_encryption_keys.find_one({"user_id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc


conversation_service = ConversationService()
