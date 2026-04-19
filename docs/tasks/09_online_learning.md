# Task 09: Online Learning System

## Goal

Implement near real-time model adaptation using streaming data. Update user embeddings incrementally, refresh the feature store in real-time, and trigger warm-start retraining when drift thresholds are exceeded.

## Context

Online learning is a critical differentiator. Without it, recommendations go stale between batch retraining cycles (typically daily). With online learning, the system adapts to new user behavior within minutes. This task builds on top of the Spark Streaming pipeline (Task 02) and the model training pipeline (Task 04).

## Requirements

### Functional
- Incremental user embedding updates as new interactions arrive
- Real-time feature store refresh (streaming features)
- Warm-start retraining triggered by drift detection or data volume thresholds
- Adaptation latency target: < 5 minutes from event to updated capability
- Metrics: embedding staleness, adaptation latency, retraining frequency

### Technical Constraints
- Built on Spark Structured Streaming (same infrastructure as Task 02)
- ALS embeddings must support incremental updates
- Must not destabilize the production model during updates
- Feature Store updates must be atomic (no partial writes)

## Implementation Steps

### Step 1: Incremental Embedding Update Module

Create `models/online_learning/embedding_updater.py`:

```python
class IncrementalEmbeddingUpdater:
    """Updates user embeddings without full ALS retraining.

    Approach: For a user with new interactions, solve for the user's
    factor vector while holding item factors fixed.

    u_new = (Y^T Y + λI)^{-1} Y^T r_u

    Where:
    - Y = item factor matrix (fixed from last full training)
    - r_u = user's interaction vector (updated with new events)
    - λ = regularization parameter
    """

    def __init__(self, item_factors: np.ndarray, reg_param: float = 0.1):
        ...

    def update_user_embedding(
        self, user_id: str, new_interactions: list[tuple[str, float]]
    ) -> np.ndarray:
        """Compute updated user embedding given new interactions."""

    def batch_update(
        self, user_interactions: dict[str, list[tuple[str, float]]]
    ) -> dict[str, np.ndarray]:
        """Update embeddings for multiple users efficiently."""
```

### Step 2: Online Feature Updater

Create `models/online_learning/feature_updater.py`:

```python
class OnlineFeatureUpdater:
    """Updates streaming features in the Feature Store."""

    def update_user_features(self, user_id: str, event: UserEvent) -> None:
        """Incrementally update user-level features:
        - Increment interaction count
        - Update recency (last_active_timestamp)
        - Recompute running average rating
        - Update frequency (events per day)
        """

    def update_item_features(self, item_id: str, event: UserEvent) -> None:
        """Incrementally update item-level features:
        - Increment view/click count
        - Recompute CTR
        - Update avg rating
        """
```

### Step 3: Warm-Start Retraining Trigger

Create `models/online_learning/retrain_trigger.py`:

```python
class RetrainingTrigger:
    """Decides when to trigger a full model retrain with warm start."""

    def __init__(self, config: RetrainingConfig):
        self.new_event_threshold = config.new_event_threshold  # e.g., 10000
        self.drift_score_threshold = config.drift_score_threshold  # e.g., 0.3
        self.max_hours_since_retrain = config.max_hours_since_retrain  # e.g., 48

    def should_retrain(self, stats: SystemStats) -> tuple[bool, str]:
        """Returns (should_retrain, reason).

        Triggers:
        1. New events since last training > threshold
        2. Drift score from Evidently > threshold
        3. Hours since last retrain > max_hours
        """

    def trigger_retrain(self) -> None:
        """Trigger Airflow DAG for warm-start retraining.

        Warm start: use current embeddings as initialization for ALS,
        reducing convergence time by ~60%.
        """
```

### Step 4: Integration with Spark Streaming

Update `spark/streaming/stream_processor.py`:

Add a `foreachBatch` handler that:
1. Processes micro-batch of events
2. Calls `IncrementalEmbeddingUpdater.batch_update()` for affected users
3. Calls `OnlineFeatureUpdater` for feature store refresh
4. Calls `RetrainingTrigger.should_retrain()` to check thresholds
5. If retrain triggered, calls Airflow API to start warm-start DAG

### Step 5: Online Learning Metrics

Create `models/online_learning/metrics.py`:

Expose Prometheus metrics:
- `embedding_update_latency_seconds` (Histogram)
- `embedding_staleness_seconds` (Gauge) — time since last embedding update per user
- `feature_update_latency_seconds` (Histogram)
- `retrain_trigger_total` (Counter) — number of retrains triggered
- `online_events_processed_total` (Counter)

### Step 6: Airflow Warm-Start DAG

Create `airflow/dags/warm_start_retrain_dag.py`:

```python
# Trigger: manual or API call from retrain_trigger
# Tasks:
#   1. load_current_embeddings (load latest user/item factors)
#   2. train_als_warm_start (ALS with initialModel parameter)
#   3. train_ranking_model (retrain ranking with new features)
#   4. evaluate_models (compare with current production)
#   5. register_if_improved (conditional registration)
```

## Deliverables

| File | Purpose |
|------|---------|
| `models/online_learning/embedding_updater.py` | Incremental ALS updates |
| `models/online_learning/feature_updater.py` | Real-time feature refresh |
| `models/online_learning/retrain_trigger.py` | Warm-start trigger logic |
| `models/online_learning/metrics.py` | Online learning metrics |
| `airflow/dags/warm_start_retrain_dag.py` | Warm-start retraining DAG |
| Updated `spark/streaming/stream_processor.py` | Online learning integration |

## Validation

1. Send 100 events for a single user → verify embedding changes
2. Compare old vs new embedding → cosine similarity < 1.0 (it changed)
3. Check feature store → user features updated within 5 minutes
4. Send 10,000+ events → verify retrain trigger fires
5. Verify warm-start DAG completes successfully
6. Compare warm-start training time vs cold-start → should be ~40% faster
7. Check Prometheus metrics → embedding_update_latency < 1s
8. End-to-end: send events → get new recommendations → verify they reflect new behavior
