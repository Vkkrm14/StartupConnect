from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Service Configuration
    ENV: str = "development"
    SERVICE_NAME: str = "search-service"
    
    # Elasticsearch Configuration
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://trustgraph:trustgraph_secure_2024@mongodb:27017/trustgraph_db"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379"
    
    # CORS
    CORS_ORIGINS: str = "http://100.70.53.90:3000,http://100.70.53.90:8000,http://100.70.53.90:8003"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()

