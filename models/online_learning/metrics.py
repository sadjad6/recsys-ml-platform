"""
Online Learning Prometheus Metrics.
"""

from prometheus_client import Counter, Histogram, Gauge

# Embedding metrics
EMBEDDING_UPDATE_LATENCY = Histogram(
    "embedding_update_latency_seconds",
    "Time taken to compute and update user embeddings",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

EMBEDDING_STALENESS = Gauge(
    "embedding_staleness_seconds",
    "Time since last embedding update per user"
)

# Feature metrics
FEATURE_UPDATE_LATENCY = Histogram(
    "feature_update_latency_seconds",
    "Time taken to update user/item features in the store",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)

# Retraining metrics
RETRAIN_TRIGGER_TOTAL = Counter(
    "retrain_trigger_total",
    "Total number of warm-start retrains triggered"
)

ONLINE_EVENTS_PROCESSED = Counter(
    "online_events_processed_total",
    "Total number of online events processed"
)
