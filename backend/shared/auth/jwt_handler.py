"""JWT Token Handler"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError
import os

class JWTHandler:
    """JWT token creation and validation"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours
        self.refresh_token_expire_days = 30
    
    def create_access_token(
        self,
        user_id: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def verify_token(self, token: str) -> bool:
        """Verify if token is valid"""
        try:
            self.decode_token(token)
            return True
        except ValueError:
            return False

# Singleton instance
jwt_handler = JWTHandler()

# Convenience functions for backward compatibility
def create_access_token(user_id: str, role: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create JWT access token"""
    return jwt_handler.create_access_token(user_id, role, additional_claims)

def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token"""
    return jwt_handler.create_refresh_token(user_id)

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    return jwt_handler.decode_token(token)

def verify_token(token: str) -> bool:
    """Verify if token is valid"""
    return jwt_handler.verify_token(token)
