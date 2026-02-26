"""Authentication API endpoints"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import httpx
import logging

from app.core.config import settings
import sys
sys.path.append("/app/shared")
from auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from messaging.kafka_producer import KafkaEventProducer

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

# Initialize Kafka producer
kafka_producer = None
if settings.KAFKA_BOOTSTRAP_SERVERS:
    try:
        kafka_producer = KafkaEventProducer(settings.KAFKA_BOOTSTRAP_SERVERS)
        kafka_producer.connect()
        logger.info("✅ Kafka producer connected")
    except Exception as e:
        logger.warning(f"⚠️ Kafka not available: {e}")

class RegisterRequest(BaseModel):
    """User registration request"""
    name: str
    email: EmailStr
    password: str
    role_primary: str  # founder, investor, connector
    domain_tags: list[str] = []
    geography: Optional[str] = None

class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    """
    Register a new user
    
    Creates user vertex in graph and returns JWT tokens
    """
    try:
        # Hash password (in production use bcrypt)
        import hashlib
        password_hash = hashlib.sha256(data.password.encode()).hexdigest()
        
        # Create user in graph service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users",
                json={
                    "name": data.name,
                    "email": data.email,
                    "password_hash": password_hash,
                    "role_primary": data.role_primary,
                    "domain_tags": data.domain_tags,
                    "geography": data.geography,
                    "reputation_score": 0.5,
                    "verification_status": "unverified"
                }
            )
            
            if response.status_code != 201:
                error_detail = response.json().get("detail", "Registration failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail
                )
            
            user_data = response.json()
            user_id = user_data["user_id"]
        
        # Generate JWT tokens
        access_token = create_access_token(
            data={"sub": user_id, "email": data.email, "role": data.role_primary}
        )
        refresh_token = create_refresh_token(
            data={"sub": user_id}
        )
        
        # Publish user_created event to Kafka
        if kafka_producer:
            try:
                await kafka_producer.publish_event(
                    topic="user-events",
                    event_type="user_created",
                    data={
                        "user_id": user_id,
                        "name": data.name,
                        "email": data.email,
                        "role_primary": data.role_primary,
                        "domain_tags": data.domain_tags,
                        "geography": data.geography
                    },
                    key=user_id
                )
            except Exception as e:
                logger.warning(f"Failed to publish user_created event: {e}")
        
        logger.info(f"✅ User registered: {user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    """
    User login
    
    Validates credentials and returns JWT tokens
    """
    try:
        # Hash password
        import hashlib
        password_hash = hashlib.sha256(data.password.encode()).hexdigest()
        
        # Verify credentials with graph service
        async with httpx.AsyncClient() as client:
            # Get user by email
            response = await client.get(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/by-email/{data.email}"
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            user_data = response.json()
            
            # Verify password
            if user_data.get("password_hash") != password_hash:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            user_id = user_data["user_id"]
            role = user_data["role_primary"]
        
        # Generate JWT tokens
        access_token = create_access_token(
            data={"sub": user_id, "email": data.email, "role": role}
        )
        refresh_token = create_refresh_token(
            data={"sub": user_id}
        )
        
        logger.info(f"✅ User logged in: {user_id}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token
    
    Accepts a refresh token and returns a new access token
    """
    try:
        # Decode refresh token
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user details
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            user_data = response.json()
        
        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": user_id,
                "email": user_data["email"],
                "role": user_data["role_primary"]
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me")
async def get_current_user(user_id: str = Depends(lambda: "dummy")):  # Will be replaced with proper dependency
    """
    Get current authenticated user
    
    Requires valid JWT token in Authorization header
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.GRAPH_SERVICE_URL}/api/v1/vertices/users/{user_id}"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return response.json()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
