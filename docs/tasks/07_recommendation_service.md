# Task 07: Recommendation Service & Model Service

## Goal

Build the Recommendation Service (orchestrates the recommendation pipeline, caches results in Redis) and the Model Service (loads models from MLflow, runs inference).

## Context

These two services deliver the core value: recommendations. The Recommendation Service is the orchestrator — it calls the Experimentation Service for A/B group assignment, the Model Service for inference, and Redis for caching. The Model Service wraps the multi-stage pipeline (ALS → ranking → re-ranking) and serves predictions.

## Requirements

### Functional
- Recommendation Service: orchestrate recommendation flow, cache in Redis
- Model Service: load models from MLflow registry, run multi-stage inference
- Support loading different model versions for A/B testing
- Cache recommendations with configurable TTL (default: 5 minutes)

### Technical Constraints
- FastAPI for both services
- Redis for caching (mandatory per spec)
- Models loaded from MLflow Model Registry
- Both services must expose `/health` and `/metrics`

## Implementation Steps

### Step 1: Model Service

Create `services/model-service/`:

```
services/model-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── model_loader.py    # Load models from MLflow
│   ├── inference.py       # Multi-stage pipeline
│   └── config.py
├── Dockerfile
└── requirements.txt
```

Endpoints:
- `GET /health` — returns loaded model versions
- `POST /predict` — run inference for a user

`POST /predict` request:
```json
{
  "user_id": "user_123",
  "model_version": "production",  // or specific version number
  "num_recommendations": 10
}
```

`POST /predict` response:
```json
{
  "user_id": "user_123",
  "recommendations": [
    {"item_id": "item_1", "score": 0.95, "rank": 1},
    {"item_id": "item_2", "score": 0.87, "rank": 2}
  ],
  "model_version": "3",
  "inference_time_ms": 45.2,
  "stages": {
    "candidate_generation_ms": 15.1,
    "ranking_ms": 22.3,
    "reranking_ms": 7.8
  }
}
```

Model loading:
- On startup, load "Production" stage models from MLflow
- Support loading specific versions by version number (for A/B testing)
- Cache loaded models in memory (do not reload on every request)
- Periodic refresh check: every 5 minutes, check if registry has newer version

### Step 2: Recommendation Service

Create `services/recommendation-service/`:

```
services/recommendation-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── orchestrator.py    # Orchestrates the flow
│   ├── cache.py           # Redis caching logic
│   └── config.py
├── Dockerfile
└── requirements.txt
```

Endpoints:
- `GET /health`
- `GET /recommendations?user_id=X&num=10` — get recommendations

Orchestration flow in `orchestrator.py`:
1. Check Redis cache for `user_id`
2. If cache hit → return cached recommendations
3. If cache miss:
   a. Call Experimentation Service: `GET /assign-group?user_id=X`
   b. Determine model version from experiment group
   c. Call Model Service: `POST /predict` with model version
   d. Cache result in Redis with TTL
   e. Return recommendations

`GET /recommendations` response:
```json
{
  "user_id": "user_123",
  "recommendations": [...],
  "experiment_group": "B",
  "model_version": "3",
  "cache_hit": false,
  "total_time_ms": 52.1
}
```

### Step 3: Redis Configuration

Add Redis to `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

Cache key format: `recs:{user_id}:{experiment_group}`
TTL: 300 seconds (5 minutes)

### Step 4: Add Services to Docker Compose

Add both services with proper dependencies:
- Model Service depends on: mlflow, postgres
- Recommendation Service depends on: model-service, experimentation-service, redis

## Deliverables

| File | Purpose |
|------|---------|
| `services/model-service/` | Model inference service |
| `services/recommendation-service/` | Recommendation orchestrator |
| 2× `Dockerfile` | Service containers |
| Updated `docker-compose.yml` | Both services + Redis |

## Validation

1. Start services: `docker-compose up -d model-service recommendation-service redis`
2. Model Service health: `curl http://localhost:8004/health` → shows loaded model versions
3. Direct prediction: `POST http://localhost:8004/predict` → returns recommendations
4. Recommendation flow: `GET http://localhost:8003/recommendations?user_id=user_1` → full response
5. Cache test: call twice → second call returns `cache_hit: true` with lower latency
6. Verify Prometheus metrics: latency histogram, cache hit rate gauge
7. Verify different model versions are called for different experiment groups
