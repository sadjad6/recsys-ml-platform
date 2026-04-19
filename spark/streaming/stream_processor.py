"""
RecSys ML Platform — Spark Streaming Processor.

Consumes events from Kafka `user-events` topic, computes real-time
aggregates (recency, frequency, item popularity), and writes to the
Feature Store (Parquet) with micro-batching.
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    window,
    avg,
    count,
    max as spark_max,
    expr
)
from schemas.feature_schema import kafka_event_schema

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events")
CHECKPOINT_DIR = "/app/data/checkpoints/streaming"
FEATURE_STORE_PATH = "/app/data/feature_store/streaming"

def create_spark_session() -> SparkSession:
    """Initialize Spark session with Kafka integration."""
    return SparkSession.builder \
        .appName("RecSys_Streaming_Processor") \
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR) \
        .getOrCreate()

def process_stream(spark: SparkSession) -> None:
    """Define and start the streaming pipeline."""
    # 1. Read from Kafka
    raw_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    # 2. Parse JSON
    parsed_stream = raw_stream \
        .selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), kafka_event_schema).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", col("timestamp").cast("timestamp"))

    # 3. Apply Watermarking (handle late data up to 10 minutes)
    watermarked_stream = parsed_stream.withWatermark("timestamp", "10 minutes")

    # 4. Compute 1-hour window aggregates
    # We group by user, item, and 1 hour window.
    # We compute user counts, item counts, max timestamp, and average rating.
    agg_stream = watermarked_stream.groupBy(
        window(col("timestamp"), "1 hour"),
        col("user_id"),
        col("item_id")
    ).agg(
        count(col("event_id")).alias("interaction_count_1h"),
        spark_max(col("timestamp")).alias("user_last_event_time"),
        avg(col("rating")).alias("user_avg_rating")
    )

    # 5. Format Output
    output_stream = agg_stream.select(
        col("user_id"),
        col("item_id"),
        col("interaction_count_1h").alias("user_event_count_1h"),
        col("interaction_count_1h").alias("item_popularity_1h"),  # Simplified proxy
        col("user_last_event_time"),
        col("user_avg_rating"),
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end")
    )

    # 6. Write to Feature Store (Parquet/append mode)
    query = output_stream.writeStream \
        .format("parquet") \
        .option("path", FEATURE_STORE_PATH) \
        .outputMode("append") \
        .trigger(processingTime="30 seconds") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    process_stream(spark)
