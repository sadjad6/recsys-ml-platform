"""
Validation tests for Kafka event schemas.

Covers happy path + edge cases per project testing standards.
"""

from __future__ import annotations

import sys
import os

# Add kafka/ directory to path for direct schema imports
_KAFKA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KAFKA_DIR not in sys.path:
    sys.path.insert(0, _KAFKA_DIR)

from pydantic import ValidationError
from schemas.event_schema import EventType, RecommendationServedEvent, UserEvent


def test_view_event_creation() -> None:
    """Valid view event should be created without rating."""
    event = UserEvent(
        user_id="user_0001",
        item_id="item_0042",
        event_type=EventType.VIEW,
    )
    assert event.user_id == "user_0001"
    assert event.item_id == "item_0042"
    assert event.event_type == EventType.VIEW
    assert event.rating is None
    assert event.event_id  # UUID should be auto-generated
    assert event.timestamp  # Timestamp should be auto-generated
    print("PASS: view event creation")


def test_click_event_creation() -> None:
    """Valid click event should be created without rating."""
    event = UserEvent(
        user_id="user_0002",
        item_id="item_0010",
        event_type=EventType.CLICK,
    )
    assert event.event_type == EventType.CLICK
    assert event.rating is None
    print("PASS: click event creation")


def test_rating_event_creation() -> None:
    """Valid rating event requires a rating value."""
    event = UserEvent(
        user_id="user_0003",
        item_id="item_0099",
        event_type=EventType.RATING,
        rating=4.5,
    )
    assert event.event_type == EventType.RATING
    assert event.rating == 4.5
    print("PASS: rating event creation")


def test_rating_event_without_rating_fails() -> None:
    """Rating event without rating value should fail validation."""
    try:
        UserEvent(
            user_id="user_0001",
            item_id="item_0001",
            event_type=EventType.RATING,
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("PASS: rating event without rating correctly rejected")


def test_view_event_with_rating_fails() -> None:
    """View event with rating value should fail validation."""
    try:
        UserEvent(
            user_id="user_0001",
            item_id="item_0001",
            event_type=EventType.VIEW,
            rating=3.0,
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("PASS: view event with rating correctly rejected")


def test_rating_out_of_range_fails() -> None:
    """Rating outside 1.0-5.0 should fail validation."""
    try:
        UserEvent(
            user_id="user_0001",
            item_id="item_0001",
            event_type=EventType.RATING,
            rating=6.0,
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("PASS: out-of-range rating correctly rejected")


def test_empty_user_id_fails() -> None:
    """Empty user_id should fail validation."""
    try:
        UserEvent(
            user_id="",
            item_id="item_0001",
            event_type=EventType.VIEW,
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("PASS: empty user_id correctly rejected")


def test_json_roundtrip() -> None:
    """Event should survive JSON serialization roundtrip."""
    original = UserEvent(
        user_id="user_0042",
        item_id="item_0007",
        event_type=EventType.CLICK,
        metadata={"device": "mobile", "page": "home"},
    )
    json_bytes = original.to_json_bytes()
    restored = UserEvent.from_json_bytes(json_bytes)

    assert restored.user_id == original.user_id
    assert restored.item_id == original.item_id
    assert restored.event_type == original.event_type
    assert restored.event_id == original.event_id
    assert restored.metadata == original.metadata
    print("PASS: JSON roundtrip")


def test_recommendation_served_event() -> None:
    """RecommendationServedEvent should serialize correctly."""
    event = RecommendationServedEvent(
        user_id="user_0001",
        recommended_items=["item_001", "item_002", "item_003"],
        model_version="v1.0",
        experiment_group="B",
        experiment_id="exp_001",
        latency_ms=42.5,
    )
    assert len(event.recommended_items) == 3
    assert event.experiment_group == "B"

    restored = RecommendationServedEvent.from_json_bytes(event.to_json_bytes())
    assert restored.recommended_items == event.recommended_items
    print("PASS: recommendation served event")


def test_recommendation_served_empty_items_fails() -> None:
    """RecommendationServedEvent with empty items should fail."""
    try:
        RecommendationServedEvent(
            user_id="user_0001",
            recommended_items=[],
            model_version="v1.0",
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        print("PASS: empty recommended_items correctly rejected")


if __name__ == "__main__":
    tests = [
        test_view_event_creation,
        test_click_event_creation,
        test_rating_event_creation,
        test_rating_event_without_rating_fails,
        test_view_event_with_rating_fails,
        test_rating_out_of_range_fails,
        test_empty_user_id_fails,
        test_json_roundtrip,
        test_recommendation_served_event,
        test_recommendation_served_empty_items_fails,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            print(f"FAIL: {test_fn.__name__} — {exc}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Schema Tests: {passed} passed, {failed} failed")
    print(f"{'=' * 50}")

    if failed > 0:
        sys.exit(1)
