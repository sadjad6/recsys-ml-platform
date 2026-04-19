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

    # Initialize online learning components
    # Using mock redis and fake paths for the scope of this implementation
    from models.online_learning.feature_updater import OnlineFeatureUpdater
    from models.online_learning.embedding_updater import IncrementalEmbeddingUpdater
    from models.online_learning.retrain_trigger import RetrainingTrigger, RetrainingConfig
    from models.online_learning.metrics import ONLINE_EVENTS_PROCESSED, EMBEDDING_UPDATE_LATENCY
    import time
    
    feature_updater = OnlineFeatureUpdater()
    # In a real environment, we'd mount the models volume to the spark streaming container
    embedding_updater = IncrementalEmbeddingUpdater(item_factors_path="/app/data/models/latest/item_factors")
    retrain_trigger = RetrainingTrigger(config=RetrainingConfig())

    def process_micro_batch(df, epoch_id):
        """Process a single micro-batch of streaming events."""
        # df is a PySpark DataFrame representing the micro-batch
        # We can convert to pandas for online learning updates if small enough, 
        # or use mapInPandas for distributed processing.
        # For simplicity, if count is > 0, we collect or process directly.
        
        count = df.count()
        if count == 0:
            return
            
        print(f"Processing micro-batch {epoch_id} with {count} events...")
        ONLINE_EVENTS_PROCESSED.inc(count)
        
        # 1. Update Features
        # For a production system with Spark, we would use df.foreachPartition
        # but for demonstration we'll collect.
        pdf = df.toPandas()
        
        # We need original events to update features/embeddings
        # Note: the df passed here is the result of `agg_stream`, not `parsed_stream`.
        # To get raw events, we should ideally hook into parsed_stream.
        # Since we are aggregating here, we just use the aggregates to update features.
        
        # The aggregated DF has user_id, item_id, user_event_count_1h, etc.
        user_interactions = {}
        for _, row in pdf.iterrows():
            user_id = row['user_id']
            item_id = row['item_id']
            
            # Simulated event dict
            event = {
                "rating": row['user_avg_rating'], 
                "timestamp": row['user_last_event_time'].timestamp() if row['user_last_event_time'] else 0
            }
            
            # Update features
            feature_updater.update_user_features(user_id, event)
            feature_updater.update_item_features(item_id, event)
            
            # Track interactions for embedding updates
            if user_id not in user_interactions:
                user_interactions[user_id] = []
            # We assume a weight/rating based on count
            user_interactions[user_id].append((item_id, row['user_avg_rating'] or 1.0))
            
        # 2. Incremental Embedding Updates
        start_time = time.time()
        updated_embeddings = embedding_updater.batch_update(user_interactions)
        latency = time.time() - start_time
        EMBEDDING_UPDATE_LATENCY.observe(latency)
        
        # 3. Retraining Trigger
        retrain_trigger.record_events(count)
        retrain_trigger.check_and_trigger(current_drift_score=0.1) # Mock drift score
        
        # 4. Save aggregates to Parquet as before
        # Note: We must write the dataframe manually since we intercepted it
        df.write.format("parquet").mode("append").save(FEATURE_STORE_PATH)

    # 6. Write to Feature Store and trigger Online Learning (foreachBatch)
    query = output_stream.writeStream \
        .foreachBatch(process_micro_batch) \
        .trigger(processingTime="30 seconds") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    # Start Prometheus metrics server for online learning
    try:
        from prometheus_client import start_http_server
        start_http_server(8008)
    except ImportError:
        pass
        
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    process_stream(spark)
