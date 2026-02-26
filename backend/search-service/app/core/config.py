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
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
