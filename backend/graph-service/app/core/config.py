from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Service Configuration
    ENV: str = "development"
    SERVICE_NAME: str = "graph-service"
    
    # JanusGraph Configuration
    JANUSGRAPH_URL: str = "ws://janusgraph:8182/gremlin"
    JANUSGRAPH_TRAVERSAL_SOURCE: str = "g"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379"
    CACHE_TTL: int = 3600  # 1 hour
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "redpanda:29092"
    KAFKA_TOPIC_TRUST_UPDATES: str = "trust-updates"
    KAFKA_TOPIC_INTRO_EVENTS: str = "intro-events"
    
    # Graph Constraints
    MAX_INTRO_PATH_HOPS: int = 4
    MIN_TRUST_SCORE: float = 0.3
    PATH_CACHE_TTL: int = 1800  # 30 minutes
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://localhost:8001"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()
