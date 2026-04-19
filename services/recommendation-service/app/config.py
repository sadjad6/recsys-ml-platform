"""
Recommendation Service Configuration.
"""

from services.shared.config import BaseServiceConfig


class RecommendationServiceConfig(BaseServiceConfig):
    """Configuration for Recommendation Service."""
    model_service_url: str = "http://model-service:8004"
    experimentation_service_url: str = "http://experimentation-service:8005"
    cache_ttl_seconds: int = 300  # 5 minutes


settings = RecommendationServiceConfig(service_name="recommendation-service", port=8003)
