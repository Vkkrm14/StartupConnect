import logging
import os
import uuid
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles

from app.core.config import settings

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024

    def _ensure_dir(self, conversation_id: str) -> Path:
        path = self.upload_dir / conversation_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def store_image(
        self,
        conversation_id: str,
        encrypted_data: bytes,
        file_extension: str = "enc",
    ) -> dict:
        if len(encrypted_data) > self.max_size:
            raise ValueError(f"Image exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB")

        directory = self._ensure_dir(conversation_id)
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{file_extension}"
        filepath = directory / filename

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(encrypted_data)

        logger.info(f"Stored encrypted image: {filepath}")
        return {
            "file_id": file_id,
            "filename": filename,
            "conversation_id": conversation_id,
            "size_bytes": len(encrypted_data),
            "stored_at": datetime.utcnow().isoformat(),
        }

    async def get_image(self, conversation_id: str, file_id: str) -> Optional[bytes]:
        directory = self.upload_dir / conversation_id
        if not directory.exists():
            return None

        for filepath in directory.iterdir():
            if filepath.stem == file_id:
                async with aiofiles.open(filepath, "rb") as f:
                    return await f.read()
        return None

    async def delete_image(self, conversation_id: str, file_id: str) -> bool:
        directory = self.upload_dir / conversation_id
        if not directory.exists():
            return False

        for filepath in directory.iterdir():
            if filepath.stem == file_id:
                filepath.unlink()
                logger.info(f"Deleted image: {filepath}")
                return True
        return False

    async def cleanup_old_images(self, max_age_days: Optional[int] = None):
        age_limit = max_age_days or settings.IMAGE_CLEANUP_DAYS
        cutoff = datetime.utcnow() - timedelta(days=age_limit)
        removed_count = 0

        if not self.upload_dir.exists():
            return removed_count

        for conversation_dir in self.upload_dir.iterdir():
            if not conversation_dir.is_dir():
                continue
            for filepath in conversation_dir.iterdir():
                if filepath.is_file():
                    mtime = datetime.utcfromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff:
                        filepath.unlink()
                        removed_count += 1

            if not any(conversation_dir.iterdir()):
                conversation_dir.rmdir()

        logger.info(f"Cleaned up {removed_count} old image files")
        return removed_count

    def get_storage_stats(self) -> dict:
        if not self.upload_dir.exists():
            return {"total_files": 0, "total_size_bytes": 0, "conversations": 0}

        total_files = 0
        total_size = 0
        conversations = 0

        for conversation_dir in self.upload_dir.iterdir():
            if conversation_dir.is_dir():
                conversations += 1
                for filepath in conversation_dir.iterdir():
                    if filepath.is_file():
                        total_files += 1
                        total_size += filepath.stat().st_size

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "conversations": conversations,
        }


image_service = ImageService()
