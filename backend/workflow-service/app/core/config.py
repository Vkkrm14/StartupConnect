from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Service Configuration
    ENV: str = "development"
    SERVICE_NAME: str = "workflow-service"
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://trustgraph:trustgraph_secure_2024@mongodb:27017/trustgraph_db"
    MONGODB_DB_NAME: str = "trustgraph_db"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379"
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "redpanda:29092"
    KAFKA_TOPIC_INTRO_EVENTS: str = "intro-events"
    
    # Email Settings
    EMAIL_ENABLED: bool = False  # Set to True in production
    EMAIL_FROM: str = "noreply@trustgraph.io"
    SMTP_HOST: str = ""  # e.g., "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Push Notifications
    PUSH_ENABLED: bool = False  # Set to True when FCM is configured
    FCM_SERVER_KEY: str = ""  # Firebase Cloud Messaging server key
    
    # Internal service URLs
    GRAPH_SERVICE_URL: str = "http://graph-service:8001"

    # App URLs
    WEB_APP_URL: str = "http://localhost:3000"
    MOBILE_APP_URL_SCHEME: str = "trustgraph://"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://localhost:8002"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()
