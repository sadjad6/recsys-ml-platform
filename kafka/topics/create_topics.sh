#!/bin/bash
# =============================================================================
# RecSys ML Platform — Kafka Topic Initialization
# =============================================================================
# Creates required Kafka topics for the recommendation system.
# Idempotent: safe to run multiple times (uses --if-not-exists).
#
# Usage:
#   docker exec -it recsys-kafka bash /create_topics.sh
#   OR automatically via kafka-init service in docker-compose
# =============================================================================

set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVERS:-kafka:29092}"
PARTITIONS="${KAFKA_TOPIC_PARTITIONS:-3}"
REPLICATION_FACTOR="${KAFKA_TOPIC_REPLICATION_FACTOR:-1}"

echo "============================================="
echo "  Kafka Topic Initialization"
echo "  Bootstrap: ${BOOTSTRAP_SERVER}"
echo "  Partitions: ${PARTITIONS}"
echo "  Replication Factor: ${REPLICATION_FACTOR}"
echo "============================================="

# Wait for Kafka to be fully ready
echo "[INFO] Waiting for Kafka broker to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until kafka-broker-api-versions --bootstrap-server "${BOOTSTRAP_SERVER}" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "${RETRY_COUNT}" -ge "${MAX_RETRIES}" ]; then
        echo "[ERROR] Kafka broker not ready after ${MAX_RETRIES} retries. Exiting."
        exit 1
    fi
    echo "[INFO] Kafka not ready yet (attempt ${RETRY_COUNT}/${MAX_RETRIES}). Retrying in 2s..."
    sleep 2
done
echo "[INFO] Kafka broker is ready."

# ---------------------------------------------------------------------------
# Topic: user-events
# Purpose: Captures all user interactions (clicks, views, ratings)
# Consumers: Spark Streaming, Online Learning, Monitoring
# ---------------------------------------------------------------------------
echo "[INFO] Creating topic: user-events"
kafka-topics --create \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --topic user-events \
    --partitions "${PARTITIONS}" \
    --replication-factor "${REPLICATION_FACTOR}" \
    --if-not-exists \
    --config retention.ms=604800000 \
    --config cleanup.policy=delete \
    --config max.message.bytes=1048576

# ---------------------------------------------------------------------------
# Topic: recommendations-served
# Purpose: Tracks which recommendations were served to users
# Consumers: A/B Testing metrics, Monitoring
# ---------------------------------------------------------------------------
echo "[INFO] Creating topic: recommendations-served"
kafka-topics --create \
    --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --topic recommendations-served \
    --partitions "${PARTITIONS}" \
    --replication-factor "${REPLICATION_FACTOR}" \
    --if-not-exists \
    --config retention.ms=604800000 \
    --config cleanup.policy=delete \
    --config max.message.bytes=1048576

# ---------------------------------------------------------------------------
# Verify topics
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Topic Verification"
echo "============================================="
echo ""

echo "[INFO] Listing all topics:"
kafka-topics --list --bootstrap-server "${BOOTSTRAP_SERVER}"
echo ""

echo "[INFO] Describing user-events:"
kafka-topics --describe --topic user-events --bootstrap-server "${BOOTSTRAP_SERVER}"
echo ""

echo "[INFO] Describing recommendations-served:"
kafka-topics --describe --topic recommendations-served --bootstrap-server "${BOOTSTRAP_SERVER}"
echo ""

echo "============================================="
echo "  Topic initialization complete!"
echo "============================================="
