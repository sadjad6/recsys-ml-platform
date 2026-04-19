# Task 01: Kafka Event Streaming Infrastructure

## Goal

Set up Apache Kafka as the event streaming backbone. Create topics, implement event producers that simulate real-time user interactions, and define event schemas.

## Context

Kafka is the foundation of the data pipeline. Every downstream system (Spark streaming, online learning, monitoring) consumes from Kafka topics. This must be production-ready: schema-validated, partitioned for throughput, and containerized.

## Requirements

### Functional
- Kafka cluster running with Zookeeper
- Topic `user-events` for user interactions (clicks, views, ratings)
- Topic `recommendations-served` for tracking served recommendations
- Event producer simulating realistic e-commerce interactions
- Event schema with validation

### Technical Constraints
- Must use Apache Kafka (mandatory per spec)
- Must be containerized with Docker
- Must be included in `docker-compose.yml`
- Events must include: `user_id`, `item_id`, `event_type`, `timestamp`, `metadata`

## Implementation Steps

### Step 1: Kafka Docker Configuration

Create `docker-compose.yml` (partial — Kafka services):

```yaml
# Services: zookeeper, kafka
# Zookeeper: port 2181
# Kafka: port 9092
# Environment: KAFKA_ADVERTISED_LISTENERS, KAFKA_ZOOKEEPER_CONNECT
# Volumes: named volumes for persistence
```

Files to create:
- `docker-compose.yml` (add zookeeper + kafka services)

### Step 2: Topic Definitions

Create topic initialization script:

```
kafka/topics/create_topics.sh
```

Topics:
- `user-events`: 3 partitions, replication factor 1 (local dev)
- `recommendations-served`: 3 partitions, replication factor 1

### Step 3: Event Schema

Define event schema in:

```
kafka/schemas/event_schema.py
```

Schema (Pydantic model):
```python
class UserEvent:
    event_id: str        # UUID
    user_id: str
    item_id: str
    event_type: str      # click | view | rating
    rating: float | None # Only for rating events
    timestamp: str       # ISO 8601
    metadata: dict       # Additional context
```

### Step 4: Event Producer

Create producer that simulates realistic interactions:

```
kafka/producers/event_producer.py
```

Requirements:
- Configurable throughput (events per second)
- Realistic user/item ID distributions
- Event type distribution: 60% views, 30% clicks, 10% ratings
- Use `confluent-kafka` or `kafka-python` library
- JSON serialization with schema validation

### Step 5: Event Consumer (verification)

Create a test consumer for validation:

```
kafka/consumers/test_consumer.py
```

## Deliverables

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Zookeeper + Kafka services |
| `kafka/topics/create_topics.sh` | Topic initialization |
| `kafka/schemas/event_schema.py` | Event Pydantic models |
| `kafka/producers/event_producer.py` | Simulated event producer |
| `kafka/consumers/test_consumer.py` | Verification consumer |
| `kafka/Dockerfile` | Container for producer scripts |

## Validation

1. `docker-compose up -d zookeeper kafka` — both containers healthy
2. Run `create_topics.sh` — topics created without errors
3. Run producer — events appear in Kafka
4. Run test consumer — events are received and deserialize correctly
5. Verify topic partitions: `kafka-topics.sh --describe --topic user-events`
6. Verify message count: produce 100 events, consume 100 events
