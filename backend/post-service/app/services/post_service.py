import logging
import uuid
from datetime import datetime
from typing import Optional, List

import httpx
from pymongo import ReturnDocument

from app.core.config import settings
from app.core.database import mongo_client
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class PostService:

    # ── Graph-service helpers ──

    async def get_founded_startups(self, user_id: str) -> List[dict]:
        """Fetch startups the user has actively founded via graph-service."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}/startups/founded"
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_name(self, user_id: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}"
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("name", "Unknown")

    # ── CRUD ──

    async def create_post(
        self, user_id: str, data: dict
    ) -> dict:
        db = mongo_client.get_db()

        # Rate-limit check
        allowed = await redis_manager.check_rate_limit(
            user_id, settings.MAX_POSTS_PER_DAY, settings.POST_RATE_LIMIT_WINDOW
        )
        if not allowed:
            raise ValueError(
                f"Daily post limit ({settings.MAX_POSTS_PER_DAY}) reached. Try again tomorrow."
            )

        # Verify FOUNDED edge
        founded = await self.get_founded_startups(user_id)
        startup_match = next(
            (s for s in founded if s["startup_id"] == data["startup_id"]),
            None,
        )
        if not startup_match:
            raise PermissionError(
                "Only active founders of this startup can post updates"
            )

        author_name = await self.get_user_name(user_id)
        now = datetime.utcnow()
        post_id = str(uuid.uuid4())

        doc = {
            "post_id": post_id,
            "startup_id": data["startup_id"],
            "startup_name": startup_match.get("name", ""),
            "author_user_id": user_id,
            "author_name": author_name,
            "title": data["title"],
            "body": data["body"],
            "tags": data.get("tags", []),
            "media_urls": data.get("media_urls", []),
            "visibility": "public",
            "like_count": 0,
            "comment_count": 0,
            "is_pinned": False,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        await db.posts.insert_one(doc)
        logger.info(f"✅ Post created: {post_id} by {user_id} for startup {data['startup_id']}")
        doc.pop("_id", None)
        return doc

    async def get_feed(
        self,
        page: int = 1,
        page_size: int = 20,
        startup_id: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> dict:
        db = mongo_client.get_db()
        query: dict = {"is_deleted": False}
        if startup_id:
            query["startup_id"] = startup_id
        if tag:
            query["tags"] = tag.lower().strip()

        total = await db.posts.count_documents(query)
        skip = (page - 1) * page_size
        cursor = (
            db.posts.find(query, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        posts = await cursor.to_list(length=page_size)
        return {
            "posts": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_post(self, post_id: str) -> Optional[dict]:
        db = mongo_client.get_db()
        doc = await db.posts.find_one(
            {"post_id": post_id, "is_deleted": False}, {"_id": 0}
        )
        return doc

    async def update_post(
        self, post_id: str, user_id: str, updates: dict
    ) -> Optional[dict]:
        db = mongo_client.get_db()
        post = await db.posts.find_one({"post_id": post_id, "is_deleted": False})
        if not post:
            return None
        if post["author_user_id"] != user_id:
            raise PermissionError("Only the author can edit this post")

        set_fields = {"updated_at": datetime.utcnow()}
        for key in ("title", "body", "tags", "media_urls"):
            if key in updates and updates[key] is not None:
                set_fields[key] = updates[key]

        doc = await db.posts.find_one_and_update(
            {"post_id": post_id},
            {"$set": set_fields},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        return doc

    async def delete_post(self, post_id: str, user_id: str) -> bool:
        db = mongo_client.get_db()
        post = await db.posts.find_one({"post_id": post_id, "is_deleted": False})
        if not post:
            return False
        if post["author_user_id"] != user_id:
            raise PermissionError("Only the author can delete this post")

        await db.posts.update_one(
            {"post_id": post_id},
            {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
        )
        logger.info(f"🗑️ Post soft-deleted: {post_id} by {user_id}")
        return True

    # ── Likes ──

    async def like_post(self, post_id: str, user_id: str) -> bool:
        db = mongo_client.get_db()
        post = await db.posts.find_one({"post_id": post_id, "is_deleted": False})
        if not post:
            raise ValueError("Post not found")

        existing = await db.post_likes.find_one(
            {"post_id": post_id, "user_id": user_id}
        )
        if existing:
            return False  # already liked

        await db.post_likes.insert_one(
            {"post_id": post_id, "user_id": user_id, "created_at": datetime.utcnow()}
        )
        await db.posts.update_one(
            {"post_id": post_id}, {"$inc": {"like_count": 1}}
        )
        return True

    async def unlike_post(self, post_id: str, user_id: str) -> bool:
        db = mongo_client.get_db()
        result = await db.post_likes.delete_one(
            {"post_id": post_id, "user_id": user_id}
        )
        if result.deleted_count == 0:
            return False

        await db.posts.update_one(
            {"post_id": post_id, "like_count": {"$gt": 0}},
            {"$inc": {"like_count": -1}},
        )
        return True


post_service = PostService()
