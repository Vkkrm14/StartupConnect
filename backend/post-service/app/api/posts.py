import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from shared.auth.dependencies import get_current_user, CurrentUser
from app.schemas.post_schemas import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostFeedResponse,
)
from app.services.post_service import post_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/posts", tags=["posts"])


@router.get("/feed", response_model=PostFeedResponse)
async def get_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    startup_id: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get paginated post feed — visible to all authenticated users."""
    result = await post_service.get_feed(
        page=page, page_size=page_size, startup_id=startup_id, tag=tag
    )
    return result


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a single post by ID."""
    post = await post_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a post — only founders with an active FOUNDED edge can post."""
    try:
        post = await post_service.create_post(current_user.user_id, data.model_dump())
        return post
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    data: PostUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update a post — author only."""
    try:
        updated = await post_service.update_post(
            post_id, current_user.user_id, data.model_dump(exclude_unset=True)
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Post not found")
        return updated
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Soft-delete a post — author only."""
    try:
        deleted = await post_service.delete_post(post_id, current_user.user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Post not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_post(
    post_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Like a post — any authenticated user."""
    try:
        await post_service.like_post(post_id, current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_post(
    post_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Remove like from a post — any authenticated user."""
    await post_service.unlike_post(post_id, current_user.user_id)
