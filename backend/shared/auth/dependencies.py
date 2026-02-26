"""FastAPI authentication dependencies"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from pydantic import BaseModel

from .jwt_handler import jwt_handler

security = HTTPBearer()

class CurrentUser(BaseModel):
    """Current authenticated user"""
    user_id: str
    role: str
    email: Optional[str] = None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Extract and validate current user from JWT token
    
    Usage in endpoint:
        @app.get("/protected")
        async def protected_route(current_user: CurrentUser = Depends(get_current_user)):
            return {"user_id": current_user.user_id}
    """
    token = credentials.credentials
    
    try:
        payload = jwt_handler.decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        role = payload.get("role")
        
        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return CurrentUser(
            user_id=user_id,
            role=role,
            email=payload.get("email")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

def require_roles(allowed_roles: List[str]):
    """
    Dependency to require specific roles
    
    Usage:
        @app.get("/admin-only")
        async def admin_route(
            current_user: CurrentUser = Depends(require_roles(["admin", "moderator"]))
        ):
            return {"message": "Admin access granted"}
    """
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {allowed_roles}"
            )
        return current_user
    
    return role_checker
