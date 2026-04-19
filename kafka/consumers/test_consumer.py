"""
RecSys ML Platform — Kafka Test Consumer.

Consumes events from the `user-events` topic, validates them against
the Pydantic schema, and prints statistics. Used for end-to-end
verification of the Kafka pipeline.

Usage:
    python -m consumers.test_consumer
    python -m consumers.test_consumer --max-messages 100 --timeout 30
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

# Resolve naming conflict: local kafka/ dir shadows kafka-python-ng.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_KAFKA_PKG_DIR = os.path.dirname(_SCRIPT_DIR)  # kafka/ directory
_PROJECT_ROOT = os.path.dirname(_KAFKA_PKG_DIR)  # project root

_original_path = sys.path.copy()
sys.path = [p for p in sys.path if os.path.abspath(p) not in {_PROJECT_ROOT, _KAFKA_PKG_DIR}]

from kafka import KafkaConsumer  # type: ignore[import-untyped]  # noqa: E402
from kafka.errors import KafkaError  # type: ignore[import-untyped]  # noqa: E402

sys.path = _original_path
if _KAFKA_PKG_DIR not in sys.path:
    sys.path.insert(0, _KAFKA_PKG_DIR)

from schemas.event_schema import UserEvent  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test-consumer")


@dataclass
class ConsumerStats:
    """Tracks consumption statistics."""

    total_received: int = 0
    total_valid: int = 0
    total_invalid: int = 0
    event_type_counts: Counter = field(default_factory=Counter)
    unique_users: set[str] = field(default_factory=set)
    unique_items: set[str] = field(default_factory=set)
    start_time: float = field(default_factory=time.monotonic)

    def report(self) -> str:
        """Generate a summary report."""
        elapsed = time.monotonic() - self.start_time
        rate = self.total_received / elapsed if elapsed > 0 else 0

        lines = [
            "",
            "=" * 55,
            "  Test Consumer — Final Report",
            "=" * 55,
            f"  Total received:   {self.total_received}",
            f"  Valid events:     {self.total_valid}",
            f"  Invalid events:   {self.total_invalid}",
            f"  Duration:         {elapsed:.1f}s",
            f"  Avg rate:         {rate:.1f} events/sec",
            f"  Unique users:     {len(self.unique_users)}",
            f"  Unique items:     {len(self.unique_items)}",
            "",
            "  Event Type Distribution:",
        ]
        for event_type, count in self.event_type_counts.most_common():
            pct = (count / self.total_received * 100) if self.total_received > 0 else 0
            lines.append(f"    {event_type:<10s} {count:>6d}  ({pct:.1f}%)")

        lines.extend(["", "=" * 55])
        return "\n".join(lines)


@dataclass(frozen=True)
class ConsumerConfig:
    """Configuration for the test consumer."""

    bootstrap_servers: str
    topic: str
    group_id: str
    max_messages: int  # 0 = infinite
    timeout_seconds: int  # 0 = infinite


def _parse_args() -> ConsumerConfig:
    """Parse CLI arguments and environment variables."""
    parser = argparse.ArgumentParser(
        description="Kafka test consumer for RecSys ML Platform",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=int(os.getenv("CONSUMER_MAX_MESSAGES", "0")),
        help="Max messages to consume, 0 = infinite (default: 0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("CONSUMER_TIMEOUT_SECONDS", "0")),
        help="Timeout in seconds, 0 = infinite (default: 0)",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        default=False,
        help="Consume from the beginning of the topic",
    )
    args = parser.parse_args()

    return ConsumerConfig(
        bootstrap_servers=os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092",
        ),
        topic=os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events"),
        group_id=os.getenv("CONSUMER_GROUP_ID", "test-consumer-group"),
        max_messages=args.max_messages,
        timeout_seconds=args.timeout,
    )


def _create_consumer(config: ConsumerConfig) -> KafkaConsumer:
    """Create a Kafka consumer with retry logic."""
    max_retries = 10
    retry_delay = 3.0

    for attempt in range(1, max_retries + 1):
        try:
            consumer = KafkaConsumer(
                config.topic,
                bootstrap_servers=config.bootstrap_servers,
                group_id=config.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                consumer_timeout_ms=10000,
                value_deserializer=None,  # Manual deserialization
            )
            logger.info(
                "Connected to Kafka at %s, topic=%s (attempt %d)",
                config.bootstrap_servers,
                config.topic,
                attempt,
            )
            return consumer
        except KafkaError as exc:
            if attempt == max_retries:
                logger.error(
                    "Failed to connect after %d attempts",
                    max_retries,
                )
                raise
            logger.warning(
                "Connection failed (attempt %d/%d): %s. Retrying in %.0fs...",
                attempt,
                max_retries,
                exc,
                retry_delay,
            )
            time.sleep(retry_delay)

    msg = "Failed to create Kafka consumer"
    raise RuntimeError(msg)


def run_consumer(config: ConsumerConfig) -> ConsumerStats:
    """Main consumer loop — receives and validates events."""
    consumer = _create_consumer(config)
    stats = ConsumerStats()

    # Graceful shutdown
    shutdown_requested = False

    def _handle_signal(signum: int, frame: object) -> None:
        nonlocal shutdown_requested
        logger.info("Shutdown signal received (signal=%d)", signum)
        shutdown_requested = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info(
        "Consuming from topic=%s (max_messages=%s, timeout=%ss)",
        config.topic,
        config.max_messages or "unlimited",
        config.timeout_seconds or "unlimited",
    )

    try:
        for message in consumer:
            if shutdown_requested:
                break

            # Check timeout
            elapsed = time.monotonic() - stats.start_time
            if config.timeout_seconds > 0 and elapsed >= config.timeout_seconds:
                logger.info("Timeout reached (%.0fs). Stopping.", elapsed)
                break

            stats.total_received += 1

            # Validate and deserialize
            try:
                event = UserEvent.from_json_bytes(message.value)
                stats.total_valid += 1
                stats.event_type_counts[event.event_type.value] += 1
                stats.unique_users.add(event.user_id)
                stats.unique_items.add(event.item_id)

                # Print first 5 events and every 50th event
                if stats.total_received <= 5 or stats.total_received % 50 == 0:
                    logger.info(
                        "[%d] %s | user=%s item=%s type=%s rating=%s",
                        stats.total_received,
                        event.event_id[:8],
                        event.user_id,
                        event.item_id,
                        event.event_type.value,
                        event.rating,
                    )
            except Exception as exc:
                stats.total_invalid += 1
                logger.warning(
                    "Invalid event at offset %d: %s",
                    message.offset,
                    exc,
                )

            # Check max messages
            if config.max_messages > 0 and stats.total_received >= config.max_messages:
                logger.info(
                    "Max messages reached (%d). Stopping.",
                    config.max_messages,
                )
                break

    except Exception as exc:
        logger.error("Consumer error: %s", exc)
    finally:
        consumer.close()

    return stats


def main() -> None:
    """Entry point."""
    config = _parse_args()
    stats = run_consumer(config)
    print(stats.report())

    # Exit with error if any invalid events
    if stats.total_invalid > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
