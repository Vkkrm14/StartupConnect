import logging
import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
import io

from shared.auth.dependencies import get_current_user, CurrentUser
from app.services.image_service import image_service
from app.services.conversation_service import conversation_service
from app.services.event_producer import event_producer
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/images", tags=["images"])


@router.post("/upload/{conversation_id}")
async def upload_image(
    conversation_id: str,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    encrypted_data = await file.read()

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(encrypted_data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB",
        )

    if len(encrypted_data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    result = await image_service.store_image(
        conversation_id=conversation_id,
        encrypted_data=encrypted_data,
        file_extension="enc",
    )

    await event_producer.emit_image_uploaded(
        conversation_id, current_user.user_id, result["file_id"]
    )

    return {
        "file_id": result["file_id"],
        "conversation_id": conversation_id,
        "size_bytes": result["size_bytes"],
    }


@router.get("/download/{conversation_id}/{file_id}")
async def download_image(
    conversation_id: str,
    file_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    encrypted_data = await image_service.get_image(conversation_id, file_id)
    if not encrypted_data:
        raise HTTPException(status_code=404, detail="Image not found")

    return StreamingResponse(
        io.BytesIO(encrypted_data),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file_id}.enc",
            "Content-Length": str(len(encrypted_data)),
        },
    )


@router.delete("/{conversation_id}/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    conversation_id: str,
    file_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    is_participant = await conversation_service.is_participant(
        conversation_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a conversation participant")

    deleted = await image_service.delete_image(conversation_id, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")


@router.get("/storage/stats")
async def storage_stats(
    current_user: CurrentUser = Depends(get_current_user),
):
    return image_service.get_storage_stats()
