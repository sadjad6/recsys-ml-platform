"""
RecSys ML Platform — Dataset Preparation Job.

Joins user, item, and interaction features to prepare the
final versioned training dataset. Applies negative sampling (4:1)
and splits data into train (80%), validation (10%), and test (10%).
"""

import argparse
import os
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, rand

FEATURE_STORE_PATH = "/app/data/feature_store"
TRAINING_DATASETS_PATH = "/app/data/training_datasets"

def create_spark_session() -> SparkSession:
    return SparkSession.builder \
        .appName("RecSys_Prepare_Training_Data") \
        .getOrCreate()

def run(version: str):
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    try:
        user_features = spark.read.parquet(f"{FEATURE_STORE_PATH}/user_features")
        item_features = spark.read.parquet(f"{FEATURE_STORE_PATH}/item_features")
        interaction_features = spark.read.parquet(f"{FEATURE_STORE_PATH}/interaction_features")
    except Exception as e:
        print(f"Failed to read feature store: {e}")
        return

    # 1. Join Features (Positives)
    # These are pairs where an interaction occurred
    positives = interaction_features \
        .join(user_features, "user_id", "left") \
        .join(item_features, "item_id", "left") \
        .withColumn("label", lit(1))

    # 2. Create Negative Samples (4:1 ratio)
    # We cross join a sample of users and items that didn't interact.
    # In a real system, this is done more efficiently than a full cross join,
    # but for this pipeline we'll approximate a random pairing.
    
    # We sample ~4x the number of positive interactions
    positive_count = positives.count()
    if positive_count == 0:
        print("No positive interactions found. Exiting.")
        return

    # A simple negative sampling approach for Spark:
    # Get distinct users and items, sample them, and cross join.
    # Then subtract actual interactions (anti-join).
    user_sample = user_features.select("user_id").sample(withReplacement=True, fraction=0.1)
    item_sample = item_features.select("item_id").sample(withReplacement=True, fraction=0.1)
    
    potential_negatives = user_sample.crossJoin(item_sample)
    
    # Remove true positives
    negatives = potential_negatives.join(
        interaction_features, 
        on=["user_id", "item_id"], 
        how="left_anti"
    )
    
    # Limit to 4x positive count
    negatives = negatives.orderBy(rand()).limit(positive_count * 4)
    
    # Join features onto negatives
    negatives = negatives \
        .join(user_features, "user_id", "left") \
        .join(item_features, "item_id", "left") \
        .withColumn("label", lit(0)) \
        .withColumn("interaction_count", lit(0)) \
        .withColumn("last_interaction_type", lit("none")) \
        .withColumn("time_since_last_interaction", lit(-1.0)) \
        .withColumn("user_item_rating", lit(None).cast("float"))

    # 3. Combine and shuffle
    # Use select with exact same column order
    cols = positives.columns
    negatives = negatives.select(*cols)
    
    dataset = positives.unionByName(negatives).orderBy(rand())

    # 4. Split: 80% train, 10% validation, 10% test
    train, val, test = dataset.randomSplit([0.8, 0.1, 0.1], seed=42)

    # 5. Output
    output_dir = os.path.join(TRAINING_DATASETS_PATH, f"v{version}")
    
    print(f"Writing training dataset to {output_dir}")
    train.write.mode("overwrite").parquet(f"{output_dir}/train.parquet")
    val.write.mode("overwrite").parquet(f"{output_dir}/val.parquet")
    test.write.mode("overwrite").parquet(f"{output_dir}/test.parquet")
    print("Dataset preparation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=str, default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()
    run(args.version)
