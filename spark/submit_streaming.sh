#!/bin/bash
# =============================================================================
# RecSys ML Platform — Spark Streaming Job Submission
# =============================================================================
# Submits the stream processor to the Spark Master cluster.
#
# Usage: ./submit_streaming.sh
# =============================================================================

# Ensure we are in the correct directory (where this script resides)
cd "$(dirname "$0")" || exit

echo "Submitting streaming job to Spark Master..."

spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --conf "spark.sql.streaming.checkpointLocation=/app/data/checkpoints/streaming" \
  --name "RecSys_Streaming_Processor" \
  streaming/stream_processor.py
