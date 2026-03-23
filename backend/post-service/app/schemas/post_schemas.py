from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    startup_id: str
    title: str = Field(..., min_length=3, max_length=120)
    body: str = Field(..., min_length=10, max_length=2000)
    tags: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return [tag.lower().strip()[:30] for tag in v if tag.strip()]

    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v):
        if len(v) > 5:
            raise ValueError("Maximum 5 media URLs allowed")
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=120)
    body: Optional[str] = Field(None, min_length=10, max_length=2000)
    tags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        if v is not None:
            return [tag.lower().strip()[:30] for tag in v if tag.strip()]
        return v

    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError("Maximum 5 media URLs allowed")
        return v


class PostResponse(BaseModel):
    post_id: str
    startup_id: str
    startup_name: str
    author_user_id: str
    author_name: str
    title: str
    body: str
    tags: List[str]
    media_urls: List[str]
    like_count: int
    comment_count: int
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class PostFeedResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    comment_id: str
    post_id: str
    author_user_id: str
    author_name: str
    body: str
    created_at: datetime
    updated_at: datetime
