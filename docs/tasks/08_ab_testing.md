# Task 08: A/B Testing Framework

## Goal

Build the Experimentation Service and integrate it with the Recommendation Service to support production-grade A/B testing between model versions.

## Context

A/B testing is critical for validating model improvements in production. The Experimentation Service deterministically assigns users to experiment groups. The Recommendation Service routes each request to the correct model version based on the group. Metrics (CTR, engagement) are tracked per group for statistical comparison.

## Requirements

### Functional
- Deterministic user-to-group assignment (hash-based)
- Experiment CRUD: create, activate, deactivate, list
- Metrics tracking per experiment group (CTR, engagement, conversion)
- Integration with Recommendation Service routing
- Support multiple concurrent experiments

### Technical Constraints
- FastAPI service
- PostgreSQL for experiment configuration and results storage
- Deterministic: `hash(user_id + experiment_id) % 100` for bucket assignment
- Same user must always get the same group (sticky assignment)

## Implementation Steps

### Step 1: Experimentation Service

Create `services/experimentation-service/`:

```
services/experimentation-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── models.py          # SQLAlchemy models
│   ├── database.py
│   ├── assignment.py      # Hash-based bucketing logic
│   ├── metrics.py         # Metrics aggregation
│   └── config.py
├── Dockerfile
└── requirements.txt
```

### Step 2: Database Models

Create in `models.py`:

```python
class Experiment:
    experiment_id: str       # PK
    name: str
    description: str
    status: str              # "active" | "paused" | "completed"
    traffic_percentage: int  # 0-100, percentage of traffic in experiment
    control_model_version: int
    treatment_model_version: int
    created_at: datetime
    updated_at: datetime

class ExperimentAssignment:
    user_id: str
    experiment_id: str
    group: str               # "control" | "treatment"
    assigned_at: datetime

class ExperimentMetric:
    experiment_id: str
    group: str
    metric_name: str         # "ctr", "engagement", "conversion"
    metric_value: float
    sample_size: int
    timestamp: datetime
```

### Step 3: Assignment Logic

Create in `assignment.py`:

```python
def assign_user_to_group(user_id: str, experiment_id: str, traffic_pct: int) -> str:
    """Deterministic hash-based assignment.

    1. Compute hash: hashlib.sha256(f"{user_id}:{experiment_id}").hexdigest()
    2. Convert first 8 hex chars to int
    3. Bucket = hash_int % 100
    4. If bucket >= traffic_pct → "excluded" (not in experiment)
    5. If bucket < traffic_pct / 2 → "control"
    6. Else → "treatment"
    """
```

Properties:
- Deterministic: same input always produces same output
- Uniform: hash function distributes evenly
- Orthogonal: different experiment_ids produce independent assignments

### Step 4: Endpoints

- `GET /health`
- `GET /assign-group?user_id=X&experiment_id=Y` → `{"group": "control", "model_version": 2}`
- `POST /experiments` → create experiment
- `GET /experiments` → list all experiments
- `GET /experiments/{id}` → experiment details with current metrics
- `PUT /experiments/{id}` → update experiment (activate/pause)
- `POST /experiments/{id}/metrics` → record a metric event

### Step 5: Metrics Collection

Create in `metrics.py`:

```python
def record_metric(experiment_id: str, group: str, metric_name: str, value: float) -> None
    """Record a single metric event (e.g., click happened → CTR numerator +1)."""

def get_experiment_metrics(experiment_id: str) -> dict:
    """Aggregate metrics per group.
    Returns:
      {
        "control": {"ctr": 0.032, "engagement": 0.15, "sample_size": 5000},
        "treatment": {"ctr": 0.041, "engagement": 0.18, "sample_size": 4800}
      }
    """

def check_significance(control_metrics: dict, treatment_metrics: dict) -> dict:
    """Run basic statistical significance test (chi-squared for CTR).
    Returns: {"significant": true, "p_value": 0.023, "confidence": 0.95}
    """
```

### Step 6: Integration with Recommendation Service

Update `services/recommendation-service/app/orchestrator.py`:

```python
# In get_recommendations():
# 1. Call experimentation service: GET /assign-group?user_id=X&experiment_id=active_exp
# 2. Extract model_version from response
# 3. Pass model_version to Model Service /predict call
# 4. After user interacts, call POST /experiments/{id}/metrics to record outcome
```

## Deliverables

| File | Purpose |
|------|---------|
| `services/experimentation-service/` | Full A/B testing service |
| `Dockerfile` | Service container |
| Updated `services/recommendation-service/` | A/B routing integration |
| Updated `docker-compose.yml` | Experimentation service |

## Validation

1. Start service: `docker-compose up -d experimentation-service`
2. Create experiment: `POST /experiments` → 201
3. Assign user: `GET /assign-group?user_id=user_1&experiment_id=exp_1` → returns group
4. Assign same user again → returns same group (sticky)
5. Assign 1000 different users → verify ~50/50 split between control/treatment
6. Record metrics: `POST /experiments/exp_1/metrics` → 200
7. Get experiment results: `GET /experiments/exp_1` → shows metrics per group
8. End-to-end: get recommendations → verify response includes `experiment_group`
9. Verify different users in different groups get different model versions
