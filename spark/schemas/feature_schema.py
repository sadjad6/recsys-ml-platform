"""
RecSys ML Platform — Spark Feature Schemas.

Defines the PySpark StructType schemas for reading Kafka JSON
and defining the output schemas for feature store writing.
"""

from pyspark.sql.types import (
    FloatType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Schema for parsing the JSON payload from Kafka 'user-events'
kafka_event_schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("item_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("rating", FloatType(), True),
    StructField("timestamp", StringType(), True),
    StructField("metadata", StringType(), True),  # JSON string or nested StructType
])

# Schema for the output streaming features written to Parquet/Delta
streaming_features_schema = StructType([
    StructField("user_id", StringType(), True),
    StructField("item_id", StringType(), True),
    StructField("user_event_count_1h", IntegerType(), True),
    StructField("user_event_count_24h", IntegerType(), True),
    StructField("item_popularity_1h", IntegerType(), True),
    StructField("user_last_event_time", TimestampType(), True),
    StructField("user_avg_rating", FloatType(), True),
    StructField("window_start", TimestampType(), True),
    StructField("window_end", TimestampType(), True),
])
