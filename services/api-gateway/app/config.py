"""
API Gateway Configuration.
"""

from services.shared.config import BaseServiceConfig

class GatewayConfig(BaseServiceConfig):
    """Configuration for API Gateway mapping downstream services."""
    user_service_url: str = "http://user-service:8001"
    event_service_url: str = "http://event-service:8002"
    recommendation_service_url: str = "http://recommendation-service:8003"
    experimentation_service_url: str = "http://experimentation-service:8005"
    
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

settings = GatewayConfig(service_name="api-gateway", port=8000)
