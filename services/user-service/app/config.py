"""
User Service Configuration.
"""

from services.shared.config import BaseServiceConfig

class UserServiceConfig(BaseServiceConfig):
    """Configuration for User Service."""
    pass # uses inherited postgres_url

settings = UserServiceConfig(service_name="user-service", port=8001)
