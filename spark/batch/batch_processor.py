"""
RecSys ML Platform — Spark Batch Processor.

Reads the streaming feature store, aggregates historical data,
and prepares the full training dataset for model training.
"""

import os
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, avg, max as spark_max

FEATURE_STORE_PATH = "/app/data/feature_store/streaming"
TRAINING_DATASETS_PATH = "/app/data/training_datasets"

def create_spark_session() -> SparkSession:
    """Initialize Spark session for batch processing."""
    return SparkSession.builder \
        .appName("RecSys_Batch_Processor") \
        .getOrCreate()

def process_batch(spark: SparkSession) -> None:
    """Read feature store and output a training dataset version."""
    # Ensure the feature store exists (might fail if streaming job hasn't written yet)
    try:
        features_df = spark.read.parquet(FEATURE_STORE_PATH)
    except Exception as e:
        print(f"Warning: Could not read feature store. Is it populated? {e}")
        return

    # Compute comprehensive features for training:
    # E.g., user total interactions, item total interactions, average rating
    training_df = features_df.groupBy("user_id", "item_id").agg(
        spark_sum("user_event_count_1h").alias("total_user_interactions"),
        spark_sum("item_popularity_1h").alias("total_item_interactions"),
        spark_max("user_last_event_time").alias("last_interaction_time"),
        avg("user_avg_rating").alias("avg_rating")
    )

    # Output versioned training dataset
    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(TRAINING_DATASETS_PATH, f"v{version}")

    print(f"Writing training dataset to {output_path}")
    
    training_df.write \
        .mode("overwrite") \
        .parquet(output_path)
    
    print(f"Batch processing complete. Dataset version: {version}")

if __name__ == "__main__":
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    process_batch(spark)
