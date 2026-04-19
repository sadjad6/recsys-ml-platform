"""
Model Service Configuration.
"""

from services.shared.config import BaseServiceConfig


class ModelServiceConfig(BaseServiceConfig):
    """Configuration for Model Service."""
    mlflow_tracking_uri: str = "http://mlflow:5000"
    model_refresh_interval_seconds: int = 300  # 5 minutes
    default_num_candidates: int = 100
    default_num_recommendations: int = 10


settings = ModelServiceConfig(service_name="model-service", port=8004)
