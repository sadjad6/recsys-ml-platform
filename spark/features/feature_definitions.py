"""
RecSys ML Platform — Feature Definitions.

Defines the structure and schema for the Feature Store, separating
features into User, Item, and Interaction categories.
"""

from pyspark.sql.types import (
    ArrayType,
    FloatType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

user_features_schema = StructType([
    StructField("user_id", StringType(), False),
    StructField("total_interactions", IntegerType(), True),
    StructField("total_clicks", IntegerType(), True),
    StructField("total_views", IntegerType(), True),
    StructField("total_ratings", IntegerType(), True),
    StructField("avg_rating_given", FloatType(), True),
    StructField("interaction_days", IntegerType(), True),
    StructField("favorite_categories", ArrayType(StringType()), True),
    StructField("last_active_timestamp", TimestampType(), True),
])

item_features_schema = StructType([
    StructField("item_id", StringType(), False),
    StructField("total_views", IntegerType(), True),
    StructField("total_clicks", IntegerType(), True),
    StructField("click_through_rate", FloatType(), True),
    StructField("avg_rating_received", FloatType(), True),
    StructField("rating_count", IntegerType(), True),
    StructField("category", StringType(), True),
    StructField("created_timestamp", TimestampType(), True),
])

interaction_features_schema = StructType([
    StructField("user_id", StringType(), False),
    StructField("item_id", StringType(), False),
    StructField("interaction_count", IntegerType(), True),
    StructField("last_interaction_type", StringType(), True),
    StructField("time_since_last_interaction", FloatType(), True),  # hours
    StructField("user_item_rating", FloatType(), True),
])
