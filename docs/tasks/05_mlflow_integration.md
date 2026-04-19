# Task 05: MLflow Integration

## Goal

Integrate MLflow for experiment tracking, model versioning, artifact storage, and model registry. Enable reproducible training runs and support A/B testing through model version management.

## Context

MLflow is the central ML lifecycle manager. Every training run logs parameters, metrics, and artifacts. The model registry manages version transitions (Staging → Production). The Model Service loads models from the registry, and A/B testing uses different registered versions.

## Requirements

### Functional
- MLflow tracking server running and accessible
- All training runs logged with parameters, metrics, and artifacts
- Model registry with named models and version staging
- Support for loading specific model versions at inference time
- Evidently drift reports stored as MLflow artifacts

### Technical Constraints
- MLflow (mandatory per spec)
- Backend store: PostgreSQL (shared instance)
- Artifact store: local filesystem (`mlflow/artifacts/`)
- Must be containerized

## Implementation Steps

### Step 1: MLflow Server Setup

Add to `docker-compose.yml`:

```yaml
mlflow:
  image: ghcr.io/mlflow/mlflow:v2.16.0
  ports:
    - "5000:5000"
  environment:
    - MLFLOW_BACKEND_STORE_URI=postgresql://mlflow:mlflow@postgres:5432/mlflow
    - MLFLOW_DEFAULT_ARTIFACT_ROOT=/mlflow/artifacts
  volumes:
    - mlflow_artifacts:/mlflow/artifacts
  depends_on:
    - postgres
```

Create MLflow database in PostgreSQL init script.

### Step 2: Training Integration

Update `models/candidate_generation/als_model.py`:

```python
# Wrap training with MLflow:
# 1. mlflow.set_experiment("candidate-generation")
# 2. mlflow.start_run()
# 3. mlflow.log_params({"rank": 64, "maxIter": 15, ...})
# 4. Train model
# 5. mlflow.log_metrics({"precision_at_100": 0.xx, "recall_at_100": 0.xx})
# 6. mlflow.spark.log_model(model, "als_model")
# 7. mlflow.end_run()
```

Update `models/ranking/ranking_model.py`:

```python
# 1. mlflow.set_experiment("ranking-model")
# 2. mlflow.start_run()
# 3. mlflow.log_params({"n_estimators": 200, "max_depth": 6, ...})
# 4. Train model
# 5. mlflow.log_metrics({"auc_roc": 0.xx, "ndcg_10": 0.xx})
# 6. mlflow.sklearn.log_model(model, "ranking_model")  # or lightgbm
# 7. Log feature importance as artifact
# 8. mlflow.end_run()
```

### Step 3: Model Registry

Create `models/registry/model_manager.py`:

```python
class ModelManager:
    def register_model(name: str, run_id: str, version_desc: str) -> ModelVersion
    def transition_stage(name: str, version: int, stage: str) -> None
    def get_production_model(name: str) -> Model
    def get_model_by_version(name: str, version: int) -> Model
    def list_versions(name: str) -> list[ModelVersion]
```

Registered model names:
- `recommendation-als` — ALS candidate generation
- `recommendation-ranking` — Ranking model
- `recommendation-pipeline` — Full pipeline wrapper

### Step 4: Airflow Training DAG

Create `airflow/dags/model_training_dag.py`:

```python
# Schedule: daily at 04:00 UTC (after feature engineering at 02:00)
# Tasks:
#   1. check_training_data (sensor — wait for latest dataset)
#   2. train_als_model (PythonOperator)
#   3. evaluate_als_model (PythonOperator)
#   4. train_ranking_model (PythonOperator)
#   5. evaluate_ranking_model (PythonOperator)
#   6. compare_with_production (PythonOperator — check if new > current)
#   7. register_model (PythonOperator — conditional on improvement)
#   8. run_drift_detection (PythonOperator — Evidently)
#   9. notify_completion (PythonOperator)
```

### Step 5: Drift Detection Integration

Create `models/drift/drift_detector.py`:

```python
# Uses Evidently library
# 1. Load reference data (training data)
# 2. Load current data (latest Feature Store snapshot)
# 3. Generate DataDriftReport
# 4. Generate PredictionDriftReport
# 5. Save HTML reports
# 6. Log reports as MLflow artifacts
# 7. Return drift score (boolean: significant drift detected)
```

## Deliverables

| File | Purpose |
|------|---------|
| `models/registry/model_manager.py` | Model registry wrapper |
| `models/drift/drift_detector.py` | Evidently drift detection |
| `airflow/dags/model_training_dag.py` | Training orchestration DAG |
| Updated `models/candidate_generation/als_model.py` | MLflow logging |
| Updated `models/ranking/ranking_model.py` | MLflow logging |
| Updated `docker-compose.yml` | MLflow server service |

## Validation

1. Start MLflow: `docker-compose up -d mlflow`
2. Access MLflow UI at `http://localhost:5000`
3. Run a training job — verify experiment and run appear in UI
4. Check logged params, metrics, and artifacts in the run
5. Register model — verify it appears in Model Registry
6. Transition model to "Production" stage — verify stage change
7. Load model from registry programmatically — verify inference works
8. Run drift detection — verify HTML report is generated and logged
