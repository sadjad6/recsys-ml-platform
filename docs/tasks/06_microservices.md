# Task 06: Core Microservices (API Gateway, User Service, Event Service)

## Goal

Build the foundational FastAPI microservices: API Gateway for routing, User Service for user management, and Event Service for event ingestion into Kafka.

## Context

These three services form the backbone of the serving layer. The API Gateway is the single entry point for all clients. The User Service manages user data in PostgreSQL. The Event Service validates and publishes user interactions to Kafka, feeding the entire streaming pipeline.

## Requirements

### Functional
- API Gateway: routing, rate limiting, health aggregation
- User Service: CRUD for users, backed by PostgreSQL
- Event Service: validate events, publish to Kafka
- All services: `/health` endpoint, `/metrics` endpoint (Prometheus), structured logging, retry logic

### Technical Constraints
- FastAPI (mandatory per spec)
- Each service in its own folder under `services/`
- Each service independently containerized
- PostgreSQL for User Service storage
- Kafka for Event Service publishing

## Implementation Steps

### Step 1: Shared Utilities

Create `services/shared/`:

- `services/shared/config.py` — environment-based configuration loader (no inline secrets)
- `services/shared/logging_config.py` — structured JSON logging setup
- `services/shared/metrics.py` — Prometheus middleware (request count, latency, errors)
- `services/shared/health.py` — health check response model
- `services/shared/retry.py` — retry decorator with exponential backoff

### Step 2: API Gateway

Create `services/api-gateway/`:

```
services/api-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, mount routes
│   ├── routes.py          # Proxy routes to downstream services
│   ├── middleware.py       # Rate limiting, request ID injection
│   └── config.py          # Service URLs from env
├── Dockerfile
└── requirements.txt
```

Routes:
- `GET /health` → aggregate health of all downstream services
- `POST /api/v1/events` → proxy to Event Service
- `GET /api/v1/recommendations` → proxy to Recommendation Service
- `GET /api/v1/users/{user_id}` → proxy to User Service
- `GET /api/v1/experiments/assign` → proxy to Experimentation Service

Rate limiting: token bucket, 100 requests/minute per IP.

### Step 3: User Service

Create `services/user-service/`:

```
services/user-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py          # Pydantic request/response
│   ├── database.py         # DB session management
│   └── config.py
├── Dockerfile
└── requirements.txt
```

Endpoints:
- `GET /health`
- `GET /users` — list users (paginated)
- `GET /users/{user_id}` — get user details
- `POST /users` — create user
- `GET /users/{user_id}/history` — interaction history

Database model:
```python
class User:
    user_id: str  # PK
    username: str
    email: str
    created_at: datetime
    preferences: dict  # JSON field
```

### Step 4: Event Service

Create `services/event-service/`:

```
services/event-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py          # Event validation (Pydantic)
│   ├── producer.py         # Kafka producer wrapper
│   └── config.py
├── Dockerfile
└── requirements.txt
```

Endpoints:
- `GET /health`
- `POST /event` — validate and publish event to Kafka

Event flow:
1. Receive event payload
2. Validate against Pydantic schema (event_type, user_id, item_id required)
3. Enrich: add `event_id` (UUID), `received_at` timestamp
4. Publish to Kafka topic `user-events`
5. Return `202 Accepted` with `event_id`

Error handling:
- Kafka unavailable → retry 3x with exponential backoff → return 503
- Invalid payload → return 422 with validation errors

### Step 5: Docker Configuration

Create Dockerfile for each service:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 800X
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "800X"]
```

Add all three services to `docker-compose.yml`.

## Deliverables

| File | Purpose |
|------|---------|
| `services/shared/` | Shared utilities (config, logging, metrics, retry) |
| `services/api-gateway/` | API Gateway service |
| `services/user-service/` | User management service |
| `services/event-service/` | Event ingestion service |
| 3× `Dockerfile` | Service containers |
| Updated `docker-compose.yml` | All three services |

## Validation

1. Start all services: `docker-compose up -d api-gateway user-service event-service`
2. Health checks pass: `curl http://localhost:8000/health`
3. Create user via API Gateway: `POST /api/v1/users` → 201
4. Get user: `GET /api/v1/users/{id}` → 200 with user data
5. Submit event: `POST /api/v1/events` → 202
6. Verify event in Kafka: consume from `user-events` topic
7. Check Prometheus metrics: `curl http://localhost:8001/metrics` → valid Prometheus format
8. Test rate limiting: send 101 requests rapidly → 429 on 101st
9. Test error handling: submit invalid event → 422 with details
