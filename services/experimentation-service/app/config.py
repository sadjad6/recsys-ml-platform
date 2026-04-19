"""
Experimentation Service Configuration.
"""

from services.shared.config import BaseServiceConfig


class ExperimentationServiceConfig(BaseServiceConfig):
    """Configuration for Experimentation Service."""
    database_url: str = "postgresql+asyncpg://recsys:recsys_pass@postgres:5432/recsys_db"
    
    # We will use PostgreSQL connection pooling
    db_pool_size: int = 10
    db_max_overflow: int = 20


settings = ExperimentationServiceConfig(service_name="experimentation-service", port=8005)
