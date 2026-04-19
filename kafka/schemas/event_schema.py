"""
RecSys ML Platform — Kafka Event Schemas.

Pydantic models defining the canonical event schemas for the
recommendation system's Kafka topics. All producers and consumers
MUST use these schemas for serialization/deserialization.

Topics:
    - user-events: UserEvent
    - recommendations-served: RecommendationServedEvent
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EventType(str, Enum):
    """Supported user interaction event types."""

    VIEW = "view"
    CLICK = "click"
    RATING = "rating"


class UserEvent(BaseModel):
    """Schema for user interaction events published to `user-events` topic.

    Attributes:
        event_id: Unique event identifier (UUID v4).
        user_id: User who performed the interaction.
        item_id: Item that was interacted with.
        event_type: Type of interaction (view, click, rating).
        rating: Numerical rating (1.0-5.0), only for rating events.
        timestamp: ISO 8601 timestamp of the event.
        metadata: Additional context (e.g., page, session, device).
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier (UUID v4)",
    )
    user_id: str = Field(
        ...,
        min_length=1,
        description="User who performed the interaction",
    )
    item_id: str = Field(
        ...,
        min_length=1,
        description="Item that was interacted with",
    )
    event_type: EventType = Field(
        ...,
        description="Type of interaction",
    )
    rating: float | None = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Rating value (1.0-5.0), only for rating events",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event context",
    )

    @model_validator(mode="after")
    def validate_rating_consistency(self) -> UserEvent:
        """Ensure rating is present for rating events and absent for others."""
        if self.event_type == EventType.RATING and self.rating is None:
            msg = "Rating is required for rating events"
            raise ValueError(msg)
        if self.event_type != EventType.RATING and self.rating is not None:
            msg = "Rating should only be set for rating events"
            raise ValueError(msg)
        return self

    def to_json_bytes(self) -> bytes:
        """Serialize to JSON bytes for Kafka producer."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> UserEvent:
        """Deserialize from JSON bytes consumed from Kafka."""
        return cls.model_validate_json(data)


class RecommendationServedEvent(BaseModel):
    """Schema for recommendation serving events published to
    `recommendations-served` topic.

    Tracks which recommendations were served to users, enabling
    A/B testing metrics and offline evaluation.

    Attributes:
        event_id: Unique event identifier (UUID v4).
        user_id: User who received the recommendations.
        recommended_items: Ordered list of recommended item IDs.
        model_version: Model version used for inference.
        experiment_group: A/B test group assignment (e.g., 'A', 'B').
        experiment_id: Experiment identifier.
        timestamp: ISO 8601 timestamp.
        latency_ms: Inference latency in milliseconds.
        metadata: Additional context.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event identifier (UUID v4)",
    )
    user_id: str = Field(
        ...,
        min_length=1,
        description="User who received recommendations",
    )
    recommended_items: list[str] = Field(
        ...,
        min_length=1,
        description="Ordered list of recommended item IDs",
    )
    model_version: str = Field(
        ...,
        description="Model version used for inference",
    )
    experiment_group: str = Field(
        default="control",
        description="A/B test group assignment",
    )
    experiment_id: str | None = Field(
        default=None,
        description="Experiment identifier",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Inference latency in milliseconds",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )

    def to_json_bytes(self) -> bytes:
        """Serialize to JSON bytes for Kafka producer."""
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> RecommendationServedEvent:
        """Deserialize from JSON bytes consumed from Kafka."""
        return cls.model_validate_json(data)
