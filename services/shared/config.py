"""
RecSys ML Platform — Shared Configuration Utilities.
"""

from pydantic_settings import BaseSettings

class BaseServiceConfig(BaseSettings):
    """Base configuration class for all microservices."""
    service_name: str
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Common dependencies
    redis_url: str = "redis://redis:6379/0"
    kafka_brokers: str = "kafka:9092"
    postgres_url: str = "postgresql+asyncpg://recsys:recsys@postgres:5432/recsys"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
