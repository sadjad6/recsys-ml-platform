"""
RecSys ML Platform — Batch Feature Engineering Job.

Reads raw events, computes historical aggregations for User, Item,
and Interaction features, and stores them in the Feature Store.
"""

import argparse
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    count,
    sum as spark_sum,
    when,
    avg,
    countDistinct,
    max as spark_max,
    to_date,
    collect_list,
    datediff,
    current_timestamp
)
from pyspark.sql.window import Window

RAW_DATA_PATH = "/app/data/raw_events/"
FEATURE_STORE_PATH = "/app/data/feature_store/"

def create_spark_session() -> SparkSession:
    return SparkSession.builder \
        .appName("RecSys_Feature_Engineering") \
        .getOrCreate()

def compute_user_features(df):
    """Computes aggregated features per user."""
    # Compute basic aggregations
    user_aggs = df.groupBy("user_id").agg(
        count("*").alias("total_interactions"),
        spark_sum(when(col("event_type") == "click", 1).otherwise(0)).alias("total_clicks"),
        spark_sum(when(col("event_type") == "view", 1).otherwise(0)).alias("total_views"),
        spark_sum(when(col("event_type") == "rating", 1).otherwise(0)).alias("total_ratings"),
        avg(col("rating")).alias("avg_rating_given"),
        countDistinct(to_date(col("timestamp"))).alias("interaction_days"),
        spark_max("timestamp").alias("last_active_timestamp")
    )
    # Simple placeholder for favorite categories (could use window functions for top N)
    # Here we just take distinct categories the user interacted with.
    categories = df.filter(col("metadata").isNotNull()).selectExpr(
        "user_id", "get_json_object(metadata, '$.category') as category"
    ).filter(col("category").isNotNull()).groupBy("user_id").agg(
        collect_list("category").alias("favorite_categories")
    )
    
    return user_aggs.join(categories, "user_id", "left")

def compute_item_features(df):
    """Computes aggregated features per item."""
    item_aggs = df.groupBy("item_id").agg(
        spark_sum(when(col("event_type") == "view", 1).otherwise(0)).alias("total_views"),
        spark_sum(when(col("event_type") == "click", 1).otherwise(0)).alias("total_clicks"),
        avg(col("rating")).alias("avg_rating_received"),
        count(col("rating")).alias("rating_count")
    )
    
    # Calculate CTR safely
    item_aggs = item_aggs.withColumn(
        "click_through_rate", 
        when(col("total_views") > 0, col("total_clicks") / col("total_views")).otherwise(0.0)
    )
    return item_aggs

def compute_interaction_features(df):
    """Computes features for specific user-item pairs."""
    window_spec = Window.partitionBy("user_id", "item_id").orderBy(col("timestamp").desc())
    
    # Get the latest interaction type and time per pair
    latest_interactions = df.withColumn("row_number", count("*").over(window_spec)) \
        .filter(col("row_number") == 1) \
        .select(
            col("user_id"),
            col("item_id"),
            col("event_type").alias("last_interaction_type"),
            datediff(current_timestamp(), col("timestamp")).alias("time_since_last_interaction_days")
        )
    
    # Aggregate counts and average rating for the pair
    pair_aggs = df.groupBy("user_id", "item_id").agg(
        count("*").alias("interaction_count"),
        avg("rating").alias("user_item_rating")
    )
    
    # Time since last interaction in hours (approximate from days for simplicity here, 
    # but ideally done accurately with unix_timestamp)
    latest_interactions = latest_interactions.withColumn(
        "time_since_last_interaction", col("time_since_last_interaction_days") * 24.0
    ).drop("time_since_last_interaction_days")
    
    return pair_aggs.join(latest_interactions, ["user_id", "item_id"], "left")

def run(date_str: str):
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # In production, we'd read just the new partition or the entire history up to date_str.
    try:
        df = spark.read.parquet(RAW_DATA_PATH)
    except Exception as e:
        print(f"Failed to read raw data: {e}")
        return

    # Compute features
    user_features = compute_user_features(df)
    item_features = compute_item_features(df)
    interaction_features = compute_interaction_features(df)

    # Write to Feature Store (overwrite the specific partition or whole table)
    user_features.write.mode("overwrite").parquet(f"{FEATURE_STORE_PATH}/user_features")
    item_features.write.mode("overwrite").parquet(f"{FEATURE_STORE_PATH}/item_features")
    interaction_features.write.mode("overwrite").parquet(f"{FEATURE_STORE_PATH}/interaction_features")
    
    print("Feature engineering completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    run(args.date)
