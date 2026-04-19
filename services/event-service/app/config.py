"""
Event Service Configuration.
"""

from services.shared.config import BaseServiceConfig

class EventServiceConfig(BaseServiceConfig):
    """Configuration for Event Service."""
    kafka_topic: str = "user-events"

settings = EventServiceConfig(service_name="event-service", port=8002)
