"""
Kafka Producer Wrapper for Event Service.
"""

import json
import logging
from aiokafka import AIOKafkaProducer
from services.shared.retry import retry_with_backoff
from .config import settings

logger = logging.getLogger(__name__)

class EventProducer:
    def __init__(self):
        self.producer = None

    async def start(self):
        """Initialize and start the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_brokers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retry_backoff_ms=500,
                request_timeout_ms=10000
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.producer = None

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped.")

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    async def publish_event(self, event_dict: dict) -> bool:
        """Publish an event to Kafka."""
        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized.")
            
        try:
            # We can use event_id as key to ensure ordering per event if needed,
            # or user_id to ensure ordering per user. Using user_id is better for recsys.
            key = event_dict.get("user_id", "").encode('utf-8')
            
            await self.producer.send_and_wait(
                topic=settings.kafka_topic,
                value=event_dict,
                key=key
            )
            return True
        except Exception as e:
            logger.error(f"Error publishing event to Kafka: {e}")
            raise e

producer = EventProducer()
