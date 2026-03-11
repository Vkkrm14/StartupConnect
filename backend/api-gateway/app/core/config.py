from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Service Configuration
    ENV: str = "development"
    SERVICE_NAME: str = "api-gateway"
    
    # Service URLs
    GRAPH_SERVICE_URL: str = "http://graph-service:8001"
    WORKFLOW_SERVICE_URL: str = "http://workflow-service:8002"
    SEARCH_SERVICE_URL: str = "http://search-service:8003"
    MESSAGING_SERVICE_URL: str = "http://messaging-service:8004"
    POST_SERVICE_URL: str = "http://post-service:8005"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379"
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://trustgraph:trustgraph_secure_2024@mongodb:27017/trustgraph_db"
    
    # Kafka Configuration (optional)
    KAFKA_BOOTSTRAP_SERVERS: Optional[str] = None
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]  # Allow all origins in development
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()
