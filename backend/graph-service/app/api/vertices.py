from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging

from app.schemas.vertex_schemas import (
    UserCreate, UserResponse,
    StartupCreate, StartupResponse,
    OrganizationCreate, OrganizationResponse
)
from app.services.vertex_service import VertexService

router = APIRouter()
logger = logging.getLogger(__name__)
vertex_service = VertexService()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """
    Create a new User vertex in the graph
    
    **Multi-role support**: Users can have primary + secondary roles
    """
    try:
        return await vertex_service.create_user(user_data)
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get User by ID"""
    user = await vertex_service.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return user

@router.post("/startups", response_model=StartupResponse, status_code=status.HTTP_201_CREATED)
async def create_startup(startup_data: StartupCreate):
    """Create a new Startup vertex"""
    try:
        return await vertex_service.create_startup(startup_data)
    except Exception as e:
        logger.error(f"Create startup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
