# Task 02: Spark Streaming Pipeline

## Goal

Build a Spark Structured Streaming pipeline that consumes events from Kafka, performs real-time feature engineering, and writes enriched features to the Feature Store.

## Context

This is the hot path of the data pipeline. It bridges Kafka (event ingestion) and the Feature Store (consumed by ML models). The streaming pipeline must handle continuous event streams with low latency while computing user/item aggregates.

## Requirements

### Functional
- Consume from Kafka topic `user-events` using Spark Structured Streaming
- Compute streaming features: recency, frequency, user/item aggregates
- Write enriched features to Feature Store (Parquet/Delta, partitioned by date)
- Handle late-arriving events with watermarking
- Checkpoint for fault tolerance

### Technical Constraints
- Must use Apache Spark (PySpark) — mandatory per spec
- Must be containerized (Spark Master + Worker)
- Micro-batch processing (trigger interval: 30s–60s)
- Feature Store path: `data/feature_store/`

## Implementation Steps

### Step 1: Spark Docker Configuration

Add to `docker-compose.yml`:
- `spark-master` (port 8080 for UI, 7077 for cluster)
- `spark-worker` (connects to master)

Use official `bitnami/spark` or `apache/spark` images.

### Step 2: Streaming Job

Create `spark/streaming/stream_processor.py`:

1. Initialize SparkSession with Kafka package
2. Read from Kafka: `spark.readStream.format("kafka")`
3. Parse JSON events using schema
4. Compute windowed aggregates:
   - `user_event_count_1h`: count of events per user in last 1 hour
   - `user_event_count_24h`: count per user in last 24 hours
   - `item_popularity_1h`: count of events per item in last 1 hour
   - `user_last_event_time`: most recent event timestamp
   - `user_avg_rating`: running average of user ratings
5. Apply watermark: 10 minutes
6. Write to Feature Store: `foreachBatch` → Parquet/Delta with `append` mode
7. Enable checkpointing: `data/checkpoints/streaming/`

### Step 3: Feature Schema

Create `spark/schemas/feature_schema.py`:

Define output feature schema:
```python
streaming_features = StructType([
    StructField("user_id", StringType()),
    StructField("item_id", StringType()),
    StructField("user_event_count_1h", IntegerType()),
    StructField("user_event_count_24h", IntegerType()),
    StructField("item_popularity_1h", IntegerType()),
    StructField("user_last_event_time", TimestampType()),
    StructField("user_avg_rating", FloatType()),
    StructField("window_start", TimestampType()),
    StructField("window_end", TimestampType()),
])
```

### Step 4: Batch Pipeline Foundation

Create `spark/batch/batch_processor.py`:

1. Read full event history from Feature Store
2. Compute comprehensive features for training:
   - User-level: total interactions, avg rating, category preferences
   - Item-level: total views, CTR, avg rating
   - Interaction-level: time since last interaction, interaction sequence
3. Output versioned training dataset: `data/training_datasets/v{version}/`

### Step 5: Submit Script

Create `spark/submit_streaming.sh`:

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  streaming/stream_processor.py
```

## Deliverables

| File | Purpose |
|------|---------|
| `spark/streaming/stream_processor.py` | Streaming feature pipeline |
| `spark/batch/batch_processor.py` | Batch feature pipeline |
| `spark/schemas/feature_schema.py` | Feature schemas |
| `spark/submit_streaming.sh` | Spark submit script |
| `spark/Dockerfile` | Spark job container |
| Updated `docker-compose.yml` | Spark master + worker services |

## Validation

1. Start Kafka + Spark: `docker-compose up -d kafka spark-master spark-worker`
2. Run event producer to generate events
3. Submit streaming job
4. Verify Feature Store directory is populated: `ls data/feature_store/`
5. Check Spark UI (port 8080) — streaming job is active with batches processing
6. Verify feature quality: read Parquet, check for null values and correct aggregates
7. Stop and restart streaming job — verify it resumes from checkpoint
