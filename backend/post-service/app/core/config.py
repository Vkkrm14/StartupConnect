from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"
    SERVICE_NAME: str = "post-service"
    SERVICE_PORT: int = 8005

    MONGODB_URL: str = "mongodb://trustgraph:trustgraph_secure_2024@mongodb:27017/trustgraph_db?authSource=admin"
    MONGODB_DB_NAME: str = "trustgraph_db"

    REDIS_URL: str = "redis://redis:6379"

    GRAPH_SERVICE_URL: str = "http://graph-service:8001"

    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    MAX_POSTS_PER_DAY: int = 10
    POST_RATE_LIMIT_WINDOW: int = 86400  # 24 hours in seconds

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
