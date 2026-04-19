# Task 04: Multi-Stage Model Training Pipeline

## Goal

Implement the 3-stage recommendation pipeline: ALS candidate generation, ranking model, and re-ranking logic. Train models on versioned datasets and produce serialized model artifacts.

## Context

This is the core ML value of the system. The multi-stage pipeline follows industry patterns (YouTube, Netflix): ALS narrows the full item catalog to ~100 candidates, the ranking model scores them precisely, and re-ranking applies business rules (diversity, freshness).

## Requirements

### Functional
- Stage 1: ALS collaborative filtering for candidate generation (PySpark MLlib)
- Stage 2: Ranking model using user + item + interaction features
- Stage 3: Re-ranking with diversity and popularity adjustment
- Models must be serializable and loadable by the Model Service
- Evaluation metrics: NDCG@K, Precision@K, Recall@K, MAP

### Technical Constraints
- ALS must use PySpark MLlib (mandatory per spec)
- Ranking model: LightGBM or XGBoost (gradient boosting)
- Training data from `data/training_datasets/v{version}/`
- Model artifacts saved to `models/` directory

## Implementation Steps

### Step 1: Candidate Generation (ALS)

Create `models/candidate_generation/als_model.py`:

1. Load training data (user-item interaction matrix)
2. Configure ALS parameters:
   - `rank`: 64 (embedding dimension)
   - `maxIter`: 15
   - `regParam`: 0.1
   - `implicitPrefs`: True (for implicit feedback)
   - `coldStartStrategy`: "drop"
3. Train ALS model using PySpark MLlib
4. Extract user factors and item factors (embeddings)
5. Save model: `models/candidate_generation/als_model/`
6. Save embeddings: `models/candidate_generation/embeddings/`
7. Evaluate: Precision@100, Recall@100

### Step 2: Ranking Model

Create `models/ranking/ranking_model.py`:

1. Load candidate pairs from ALS output + features from Feature Store
2. Build feature vector per (user, item) pair:
   - User features: total_interactions, avg_rating, interaction_days, etc.
   - Item features: total_views, CTR, avg_rating, etc.
   - Interaction features: interaction_count, time_since_last, etc.
   - ALS features: user-item dot product score from embeddings
3. Train LightGBM/XGBoost classifier:
   - Target: binary (interacted = 1, not interacted = 0)
   - Cross-validation: 5-fold
4. Save model: `models/ranking/ranking_model.joblib`
5. Save feature importance: `models/ranking/feature_importance.json`
6. Evaluate: AUC-ROC, NDCG@10, Precision@10

### Step 3: Re-Ranking Logic

Create `models/reranking/reranker.py`:

1. Accept ranked list from Stage 2
2. Apply Maximal Marginal Relevance (MMR) for diversity:
   - `lambda_param`: 0.7 (trade-off relevance vs. diversity)
   - Diversity measured by item category spread
3. Apply popularity dampening:
   - Penalize items above 90th percentile popularity
   - Boost items below 30th percentile (cold-start items)
4. Return final re-ranked list of top K items (default K=10)

### Step 4: Pipeline Orchestrator

Create `models/pipeline.py`:

1. Full inference pipeline: `user_id → [recommendations]`
2. Stage 1: ALS → top 100 candidates
3. Stage 2: Ranking model → score and sort candidates
4. Stage 3: Re-ranking → final top 10
5. Return list of `(item_id, score)` tuples

### Step 5: Evaluation Module

Create `models/evaluation/evaluator.py`:

Metrics:
- `ndcg_at_k(predictions, actuals, k)` → float
- `precision_at_k(predictions, actuals, k)` → float
- `recall_at_k(predictions, actuals, k)` → float
- `mean_average_precision(predictions, actuals)` → float
- `coverage(predictions, item_catalog)` → float (% of items recommended)
- `diversity(predictions)` → float (intra-list diversity)

## Deliverables

| File | Purpose |
|------|---------|
| `models/candidate_generation/als_model.py` | ALS training |
| `models/ranking/ranking_model.py` | Ranking model training |
| `models/reranking/reranker.py` | Re-ranking logic |
| `models/pipeline.py` | Full inference pipeline |
| `models/evaluation/evaluator.py` | Evaluation metrics |
| `models/__init__.py` | Package init |

## Validation

1. Train ALS on sample data — model saves without error
2. Extract embeddings — verify dimensions (num_users × 64, num_items × 64)
3. Train ranking model — AUC-ROC > 0.7 on validation set
4. Run full pipeline for a test user — returns 10 recommendations
5. Evaluate on test set — NDCG@10 > 0.1 (baseline threshold)
6. Verify re-ranking changes the order from pure ranking output
7. Verify diversity metric improves after re-ranking vs. before
