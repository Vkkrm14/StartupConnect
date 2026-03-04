from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    ENV: str = "development"
    SERVICE_NAME: str = "messaging-service"
    SERVICE_PORT: int = 8004

    CASSANDRA_HOSTS: str = "cassandra"
    CASSANDRA_PORT: int = 9042
    CASSANDRA_KEYSPACE: str = "messaging"
    CASSANDRA_REPLICATION_FACTOR: int = 1

    MONGODB_URL: str = "mongodb://trustgraph:trustgraph_secure_2024@mongodb:27017/trustgraph_db?authSource=admin"
    MONGODB_DB_NAME: str = "trustgraph_db"

    REDIS_URL: str = "redis://redis:6379"

    KAFKA_BOOTSTRAP_SERVERS: str = "redpanda:29092"

    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    MAX_IMAGE_SIZE_MB: int = 5
    UPLOAD_DIR: str = "/app/uploads/messages"

    MESSAGE_PAGE_SIZE: int = 50
    MAX_MESSAGE_SIZE_BYTES: int = 65536
    RATE_LIMIT_MESSAGES_PER_MINUTE: int = 60

    IMAGE_CLEANUP_DAYS: int = 90

    class Config:
        env_file = ".env"


settings = Settings()
