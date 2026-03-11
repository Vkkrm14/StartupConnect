from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List
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

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role: founder, investor, connector"),
    limit: int = Query(100, le=200)
):
    """List all users, optionally filtered by role"""
    try:
        return await vertex_service.list_users(role=role, limit=limit)
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

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

@router.get("/users/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str):
    """Get User by email address"""
    user = await vertex_service.get_user_by_email(email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found"
        )
    
    return user

@router.get("/users/{user_id}/connections", response_model=List[UserResponse])
async def get_user_connections(user_id: str):
    """Get all users that this user is mutually connected to"""
    try:
        return await vertex_service.get_connections(user_id)
    except Exception as e:
        logger.error(f"Get connections error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/users/{user_id}/startups/founded")
async def get_user_founded_startups(user_id: str):
    """Get all startups where this user has an active FOUNDED edge.
    Used by post-service for authorization."""
    try:
        return await vertex_service.get_founded_startups(user_id)
    except Exception as e:
        logger.error(f"Get founded startups error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

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
