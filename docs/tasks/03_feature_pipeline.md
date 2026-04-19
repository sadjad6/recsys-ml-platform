# Task 03: Feature Pipeline & Airflow Orchestration

## Goal

Build the complete feature engineering pipeline and orchestrate it with Apache Airflow DAGs. This covers both streaming feature updates (already built in Task 02) and batch feature preparation for model training.

## Context

The Feature Pipeline is the bridge between raw events and ML models. It produces two outputs: (1) a continuously-updated Feature Store for real-time serving and (2) versioned training datasets for batch model training. Airflow orchestrates the batch path end-to-end.

## Requirements

### Functional
- Feature Store with user features, item features, and interaction features
- Versioned training datasets for reproducible model training
- Airflow DAGs for: data ingestion, feature engineering, training trigger
- Idempotent pipeline runs (re-runnable without side effects)

### Technical Constraints
- Apache Airflow for orchestration (mandatory per spec)
- Feature Store format: Parquet or Delta Lake
- DAGs must be modular and production-like
- Airflow must be containerized

## Implementation Steps

### Step 1: Feature Store Schema Design

Create `spark/features/feature_definitions.py`:

**User Features:**
- `user_id` (string)
- `total_interactions` (int)
- `total_clicks` (int)
- `total_views` (int)
- `total_ratings` (int)
- `avg_rating_given` (float)
- `interaction_days` (int) — number of distinct active days
- `favorite_categories` (list[str]) — top 3 categories by interaction count
- `last_active_timestamp` (timestamp)

**Item Features:**
- `item_id` (string)
- `total_views` (int)
- `total_clicks` (int)
- `click_through_rate` (float)
- `avg_rating_received` (float)
- `rating_count` (int)
- `category` (string)
- `created_timestamp` (timestamp)

**Interaction Features (for ranking model):**
- `user_id` (string)
- `item_id` (string)
- `interaction_count` (int)
- `last_interaction_type` (string)
- `time_since_last_interaction` (float) — hours
- `user_item_rating` (float | None)

### Step 2: Batch Feature Engineering Job

Create `spark/batch/feature_engineering.py`:

1. Read raw events from `data/raw_events/`
2. Compute user features (group by user_id, aggregate)
3. Compute item features (group by item_id, aggregate)
4. Compute interaction features (group by user_id + item_id)
5. Write to Feature Store:
   - `data/feature_store/user_features/`
   - `data/feature_store/item_features/`
   - `data/feature_store/interaction_features/`
6. Write versioned training dataset:
   - `data/training_datasets/v{YYYYMMDD}/`

### Step 3: Dataset Preparation Job

Create `spark/batch/prepare_training_data.py`:

1. Join user features + item features + interaction features
2. Create positive samples (interactions that happened)
3. Create negative samples (random user-item pairs without interaction)
4. Negative sampling ratio: 4:1 (4 negatives per positive)
5. Split: 80% train, 10% validation, 10% test
6. Output: `data/training_datasets/v{version}/{train,val,test}.parquet`

### Step 4: Airflow Docker Configuration

Add to `docker-compose.yml`:
- `airflow-webserver` (port 8080)
- `airflow-scheduler`
- Shared volume for DAGs: `airflow/dags/`
- PostgreSQL as Airflow metadata backend (shared or separate instance)

Create `airflow/Dockerfile` with:
- Apache Airflow 2.7+
- PySpark, MLflow, Evidently dependencies
- DAG folder mounted

### Step 5: Airflow DAGs

Create `airflow/dags/feature_engineering_dag.py`:

```python
# Schedule: daily at 02:00 UTC
# Tasks:
#   1. check_raw_data_available (sensor)
#   2. run_feature_engineering (SparkSubmitOperator)
#   3. prepare_training_data (SparkSubmitOperator)
#   4. validate_data_quality (PythonOperator — basic checks)
#   5. notify_completion (PythonOperator — log/webhook)
```

Create `airflow/dags/data_ingestion_dag.py`:

```python
# Schedule: hourly
# Tasks:
#   1. export_kafka_to_raw (dump Kafka topic to Parquet)
#   2. deduplicate_events
#   3. validate_schema
```

### Step 6: Data Quality Checks

Create `airflow/plugins/data_quality.py`:

- Check for null values in critical columns
- Check row counts (minimum threshold)
- Check for duplicate event IDs
- Check timestamp ranges (no future timestamps)

## Deliverables

| File | Purpose |
|------|---------|
| `spark/features/feature_definitions.py` | Feature schema definitions |
| `spark/batch/feature_engineering.py` | Batch feature computation |
| `spark/batch/prepare_training_data.py` | Training dataset preparation |
| `airflow/dags/feature_engineering_dag.py` | Feature pipeline DAG |
| `airflow/dags/data_ingestion_dag.py` | Data ingestion DAG |
| `airflow/plugins/data_quality.py` | Data quality validators |
| `airflow/Dockerfile` | Airflow container |
| Updated `docker-compose.yml` | Airflow services |

## Validation

1. Start Airflow: `docker-compose up -d airflow-webserver airflow-scheduler`
2. Access Airflow UI at `http://localhost:8080`
3. Trigger `data_ingestion_dag` manually — verify raw data lands in `data/raw_events/`
4. Trigger `feature_engineering_dag` manually — verify Feature Store is populated
5. Check training dataset: read Parquet, verify train/val/test splits exist
6. Verify data quality checks pass (no nulls, correct schema)
7. Verify DAG dependencies render correctly in Airflow UI graph view
