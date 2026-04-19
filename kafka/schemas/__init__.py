# kafka/schemas/__init__.py
"""Kafka event schemas package."""

from .event_schema import (
    EventType,
    RecommendationServedEvent,
    UserEvent,
)

__all__ = ["EventType", "RecommendationServedEvent", "UserEvent"]
