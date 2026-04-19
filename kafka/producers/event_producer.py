"""
RecSys ML Platform — Kafka Event Producer.

Simulates realistic e-commerce user interactions and publishes them
to the `user-events` Kafka topic. Designed for both local development
and containerized execution.

Distribution:
    - 60% view events
    - 30% click events
    - 10% rating events

Usage:
    python -m producers.event_producer
    python -m producers.event_producer --eps 20 --duration 60
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from typing import NoReturn

# Resolve naming conflict: local kafka/ dir shadows kafka-python-ng.
# We temporarily remove the project root from sys.path to import the real kafka package.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_KAFKA_PKG_DIR = os.path.dirname(_SCRIPT_DIR)  # kafka/ directory
_PROJECT_ROOT = os.path.dirname(_KAFKA_PKG_DIR)  # project root

# Remove project root and kafka dir temporarily to import kafka-python-ng
_original_path = sys.path.copy()
sys.path = [p for p in sys.path if os.path.abspath(p) not in {_PROJECT_ROOT, _KAFKA_PKG_DIR}]

from kafka import KafkaProducer  # type: ignore[import-untyped]  # noqa: E402
from kafka.errors import KafkaError  # type: ignore[import-untyped]  # noqa: E402

# Restore path and add kafka dir for schema imports
sys.path = _original_path
if _KAFKA_PKG_DIR not in sys.path:
    sys.path.insert(0, _KAFKA_PKG_DIR)

from schemas.event_schema import EventType, UserEvent  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("event-producer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EVENT_TYPE_WEIGHTS: list[tuple[EventType, float]] = [
    (EventType.VIEW, 0.60),
    (EventType.CLICK, 0.30),
    (EventType.RATING, 0.10),
]

ITEM_CATEGORIES: list[str] = [
    "electronics", "clothing", "books", "home", "sports",
    "beauty", "toys", "food", "automotive", "garden",
]

DEVICE_TYPES: list[str] = ["mobile", "desktop", "tablet"]

PAGE_TYPES: list[str] = [
    "home", "search", "category", "product_detail",
    "recommendations", "cart",
]


@dataclass(frozen=True)
class ProducerConfig:
    """Configuration for the event producer."""

    bootstrap_servers: str
    topic: str
    events_per_second: float
    num_users: int
    num_items: int
    duration_seconds: int  # 0 = infinite


def _parse_args() -> ProducerConfig:
    """Parse CLI arguments and environment variables."""
    parser = argparse.ArgumentParser(
        description="Kafka event producer for RecSys ML Platform",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=float(os.getenv("PRODUCER_EVENTS_PER_SECOND", "10")),
        help="Events per second (default: 10)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=int(os.getenv("PRODUCER_DURATION_SECONDS", "0")),
        help="Duration in seconds, 0 = infinite (default: 0)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=int(os.getenv("PRODUCER_NUM_USERS", "1000")),
        help="Number of simulated users (default: 1000)",
    )
    parser.add_argument(
        "--items",
        type=int,
        default=int(os.getenv("PRODUCER_NUM_ITEMS", "500")),
        help="Number of simulated items (default: 500)",
    )
    args = parser.parse_args()

    return ProducerConfig(
        bootstrap_servers=os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092",
        ),
        topic=os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events"),
        events_per_second=args.eps,
        num_users=args.users,
        num_items=args.items,
        duration_seconds=args.duration,
    )


def _pick_event_type() -> EventType:
    """Select event type based on configured distribution."""
    types, weights = zip(*EVENT_TYPE_WEIGHTS)
    return random.choices(types, weights=weights, k=1)[0]


def _generate_user_id(num_users: int) -> str:
    """Generate a user ID with power-law-like distribution.

    A small fraction of users generate most of the traffic,
    mimicking real e-commerce behavior.
    """
    # Power-law: top 20% users generate 80% of events
    if random.random() < 0.80:
        user_idx = random.randint(1, max(1, int(num_users * 0.20)))
    else:
        user_idx = random.randint(1, num_users)
    return f"user_{user_idx:04d}"


def _generate_item_id(num_items: int) -> str:
    """Generate an item ID with popularity bias.

    Popular items (top 10%) get 50% of interactions.
    """
    if random.random() < 0.50:
        item_idx = random.randint(1, max(1, int(num_items * 0.10)))
    else:
        item_idx = random.randint(1, num_items)
    return f"item_{item_idx:04d}"


def _generate_event(num_users: int, num_items: int) -> UserEvent:
    """Generate a single realistic user interaction event."""
    event_type = _pick_event_type()
    rating = round(random.uniform(1.0, 5.0), 1) if event_type == EventType.RATING else None

    return UserEvent(
        user_id=_generate_user_id(num_users),
        item_id=_generate_item_id(num_items),
        event_type=event_type,
        rating=rating,
        metadata={
            "category": random.choice(ITEM_CATEGORIES),
            "device": random.choice(DEVICE_TYPES),
            "page": random.choice(PAGE_TYPES),
            "session_id": f"session_{random.randint(1, 10000):05d}",
        },
    )


def _create_producer(bootstrap_servers: str) -> KafkaProducer:
    """Create a Kafka producer with retry logic."""
    max_retries = 10
    retry_delay = 3.0

    for attempt in range(1, max_retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=None,  # We serialize manually via Pydantic
                acks="all",
                retries=3,
                retry_backoff_ms=500,
                max_in_flight_requests_per_connection=5,
                linger_ms=10,
                batch_size=16384,
                compression_type="gzip",
            )
            logger.info(
                "Connected to Kafka at %s (attempt %d)",
                bootstrap_servers,
                attempt,
            )
            return producer
        except KafkaError as exc:
            if attempt == max_retries:
                logger.error(
                    "Failed to connect to Kafka after %d attempts",
                    max_retries,
                )
                raise
            logger.warning(
                "Kafka connection failed (attempt %d/%d): %s. Retrying in %.0fs...",
                attempt,
                max_retries,
                exc,
                retry_delay,
            )
            time.sleep(retry_delay)

    # Unreachable, but satisfies type checker
    msg = "Failed to create Kafka producer"
    raise RuntimeError(msg)


def _on_send_success(record_metadata: object) -> None:
    """Callback for successful message delivery."""
    logger.debug(
        "Delivered: topic=%s partition=%s offset=%s",
        getattr(record_metadata, "topic", "?"),
        getattr(record_metadata, "partition", "?"),
        getattr(record_metadata, "offset", "?"),
    )


def _on_send_error(exc: Exception) -> None:
    """Callback for failed message delivery."""
    logger.error("Delivery failed: %s", exc)


def run_producer(config: ProducerConfig) -> None:
    """Main producer loop — generates and publishes events."""
    producer = _create_producer(config.bootstrap_servers)

    # Graceful shutdown
    shutdown_requested = False

    def _handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown_requested
        logger.info("Shutdown signal received (signal=%d)", signum)
        shutdown_requested = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    interval = 1.0 / config.events_per_second if config.events_per_second > 0 else 0
    total_sent = 0
    total_errors = 0
    start_time = time.monotonic()

    logger.info(
        "Starting event production: %.1f events/sec, %d users, %d items, topic=%s",
        config.events_per_second,
        config.num_users,
        config.num_items,
        config.topic,
    )

    try:
        while not shutdown_requested:
            # Check duration limit
            elapsed = time.monotonic() - start_time
            if config.duration_seconds > 0 and elapsed >= config.duration_seconds:
                logger.info(
                    "Duration limit reached (%.0fs). Stopping.",
                    config.duration_seconds,
                )
                break

            event = _generate_event(config.num_users, config.num_items)

            try:
                future = producer.send(
                    config.topic,
                    value=event.to_json_bytes(),
                    key=event.user_id.encode("utf-8"),
                )
                future.add_callback(_on_send_success)
                future.add_errback(_on_send_error)
                total_sent += 1
            except KafkaError as exc:
                total_errors += 1
                logger.error("Failed to send event: %s", exc)

            # Progress logging every 100 events
            if total_sent % 100 == 0 and total_sent > 0:
                rate = total_sent / (time.monotonic() - start_time)
                logger.info(
                    "Progress: sent=%d errors=%d rate=%.1f/sec elapsed=%.0fs",
                    total_sent,
                    total_errors,
                    rate,
                    time.monotonic() - start_time,
                )

            if interval > 0:
                time.sleep(interval)

    finally:
        logger.info("Flushing remaining messages...")
        producer.flush(timeout=10)
        producer.close(timeout=5)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Producer stopped. total_sent=%d errors=%d duration=%.1fs avg_rate=%.1f/sec",
            total_sent,
            total_errors,
            elapsed,
            total_sent / elapsed if elapsed > 0 else 0,
        )


def main() -> None:
    """Entry point."""
    config = _parse_args()
    run_producer(config)


if __name__ == "__main__":
    main()
