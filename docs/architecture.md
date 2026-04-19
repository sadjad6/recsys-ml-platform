# Architecture — Real-Time Recommendation System

## 1. System Overview

A production-grade, microservices-based recommendation platform that ingests streaming user interactions via Kafka, processes data through Spark (batch + streaming), trains and serves ML models via a multi-stage pipeline (candidate generation → ranking → re-ranking), supports online learning and A/B testing, and is fully observable through Prometheus + Grafana.

**Core principles:**

- Every service is independently deployable, containerized (Docker), and orchestrated (Kubernetes)
- Data flows are separated into hot (streaming) and cold (batch) paths
- ML models are versioned, tracked (MLflow), and served behind an experimentation layer
- Observability is first-class: every service exposes Prometheus metrics

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                        │
│                     Streamlit Frontend (port 8501)                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (FastAPI)                               │
│                     Routing · Auth · Rate Limiting                           │
│                          port 8000                                           │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────────────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────┐
│ User   │ │ Event  │ │ Rec    │ │ Model  │ │ Experimentation│
│Service │ │Service │ │Service │ │Service │ │ Service        │
│:8001   │ │:8002   │ │:8003   │ │:8004   │ │ :8005          │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───────┬────────┘
    │          │          │          │               │
    ▼          ▼          ▼          ▼               │
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│Postgres│ │ Kafka  │ │ Redis  │ │ MLflow │◄────────┘
│        │ │        │ │ Cache  │ │Registry│
└────────┘ └───┬────┘ └────────┘ └────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│Spark   │ │Spark   │ │Feature │
│Batch   │ │Stream  │ │Store   │
│Pipeline│ │Pipeline│ │(Parquet│
│        │ │        │ │/Delta) │
└───┬────┘ └───┬────┘ └────────┘
    │          │
    ▼          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING STACK                                     │
│              Prometheus (scrape) ──► Grafana (dashboards)                    │
│              Evidently (drift detection reports)                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION                                        │
│                     Apache Airflow (DAGs)                                    │
│         ingestion · feature eng · training · eval · deploy                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### 3.1 Hot Path (Streaming)

```
User Action → Streamlit → API Gateway → Event Service → Kafka (topic: user-events)
                                                              │
                                                              ▼
                                                   Spark Structured Streaming
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼               ▼               ▼
                                        Feature Store   Online Learning   Real-time
                                        (update)        (incremental)     Aggregates
```

1. User interacts (click, view, rate) via Streamlit
2. Event Service validates and publishes to Kafka topic `user-events`
3. Spark Structured Streaming consumes events in micro-batches
4. Streaming pipeline computes recency, frequency, and user/item aggregates
5. Updated features are written to the Feature Store (Parquet/Delta)
6. Online Learning module incrementally updates user embeddings

### 3.2 Cold Path (Batch)

```
Airflow DAG (scheduled)
    │
    ├──► Spark Batch: full feature engineering
    ├──► Model Training (ALS + ranking model)
    ├──► MLflow: log metrics, register model
    ├──► Evidently: generate drift report
    └──► Model Service: reload latest model
```

1. Airflow triggers batch DAG on schedule (e.g., daily)
2. Spark batch pipeline builds full training dataset from Feature Store
3. Candidate generation (ALS) and ranking model are trained
4. MLflow tracks parameters, metrics, artifacts; best model is registered
5. Evidently generates data/model drift reports
6. Model Service picks up the new registered model version

---

## 4. Microservices Interactions

### Request Flow: Get Recommendations

```
Streamlit → API Gateway → Recommendation Service
                               │
                               ├──► Experimentation Service (/assign-group)
                               │         → returns: experiment_group (A or B)
                               │
                               ├──► Model Service (/predict)
                               │         → uses model version based on group
                               │         → Stage 1: Candidate Gen (ALS)
                               │         → Stage 2: Ranking
                               │         → Stage 3: Re-ranking
                               │
                               ├──► Redis (check cache)
                               │
                               └──► Return ranked recommendations
```

### Request Flow: Ingest Event

```
Streamlit → API Gateway → Event Service
                               │
                               ├──► Validate payload
                               ├──► Kafka Producer → topic: user-events
                               └──► Return 202 Accepted
```

### Service Dependencies

| Service                | Depends On                                    |
|------------------------|-----------------------------------------------|
| API Gateway            | All downstream services                       |
| User Service           | PostgreSQL                                    |
| Event Service          | Kafka                                         |
| Recommendation Service | Model Service, Experimentation Service, Redis |
| Model Service          | MLflow Model Registry, Feature Store          |
| Experimentation Service| PostgreSQL                                    |

---

## 5. A/B Testing Design

### Architecture

```
               ┌──────────────────────┐
               │ Experimentation      │
               │ Service              │
               │                      │
  /assign ────►│ 1. Hash user_id      │
  -group       │ 2. Deterministic     │
               │    bucket (A/B)      │
               │ 3. Return group      │
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │ Recommendation Svc   │
               │                      │
               │ if group == A:       │
               │   model = baseline   │
               │ elif group == B:     │
               │   model = challenger │
               └──────────────────────┘
```

### Key Design Decisions

- **Deterministic assignment**: `hash(user_id + experiment_id) % 100` → bucket
- **Sticky assignment**: same user always sees the same model variant
- **Metrics tracked per group**: CTR, engagement, latency
- **Storage**: experiment configs and results in PostgreSQL
- **Statistical rigor**: track sample sizes for significance testing

---

## 6. Online Learning Design

```
Kafka (user-events) ──► Spark Streaming ──► Online Learning Module
                                                    │
                                        ┌───────────┼───────────┐
                                        ▼           ▼           ▼
                                  Update User   Update       Trigger
                                  Embeddings    Feature      Warm-Start
                                  (incremental) Store       Retraining
                                                            (threshold)
```

### Mechanism

1. **Incremental embedding updates**: as new interactions arrive, user embeddings are adjusted without full retraining
2. **Feature store refresh**: streaming features (recency, frequency) are updated in near real-time
3. **Warm-start retraining**: when drift is detected (via Evidently) or a threshold of new data is reached, a full retrain is triggered using the latest embeddings as initialization
4. **Latency target**: < 5 minutes from event to updated recommendation capability

---

## 7. Monitoring Flow

```
┌────────────────────────────────────────────────────────────┐
│                    Each FastAPI Service                      │
│                                                             │
│  prometheus_client → /metrics endpoint                      │
│  Counters: request_count, error_count                       │
│  Histograms: request_latency, inference_latency             │
└────────────────────┬───────────────────────────────────────┘
                     │ scrape (15s interval)
                     ▼
┌────────────────────────────────────────────────────────────┐
│                    Prometheus                               │
│                                                             │
│  Scrape targets: all services, Kafka exporter, Spark        │
│  Retention: 15d                                             │
│  Alert rules: high latency, error rate spikes               │
└────────────────────┬───────────────────────────────────────┘
                     │ data source
                     ▼
┌────────────────────────────────────────────────────────────┐
│                    Grafana                                   │
│                                                             │
│  Dashboards:                                                │
│  ├── API Performance (latency, throughput, errors)          │
│  ├── Kafka Monitoring (lag, throughput per topic)            │
│  ├── Model Performance (inference latency, predictions/sec) │
│  └── System Health (CPU, memory, disk)                      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                    Evidently                                │
│                                                             │
│  Scheduled by Airflow:                                      │
│  ├── Data drift report                                      │
│  ├── Prediction drift report                                │
│  └── Model quality report                                   │
└────────────────────────────────────────────────────────────┘
```

### Metrics per Service

| Metric                  | Type      | Labels                        |
|-------------------------|-----------|-------------------------------|
| `http_requests_total`   | Counter   | method, endpoint, status_code |
| `http_request_duration` | Histogram | method, endpoint              |
| `http_errors_total`     | Counter   | method, endpoint, error_type  |
| `model_inference_time`  | Histogram | model_version, stage          |
| `kafka_consumer_lag`    | Gauge     | topic, consumer_group         |
| `cache_hit_rate`        | Gauge     | service                       |

---

## 8. Deployment Topology

### 8.1 Local Development (Docker Compose)

```yaml
# docker-compose.yml defines:
services:
  - zookeeper
  - kafka
  - postgres
  - redis
  - mlflow
  - api-gateway
  - user-service
  - event-service
  - recommendation-service
  - model-service
  - experimentation-service
  - spark-master
  - spark-worker
  - airflow-webserver
  - airflow-scheduler
  - prometheus
  - grafana
  - streamlit
```

All services communicate via Docker network. Kafka and PostgreSQL use named volumes for persistence.

### 8.2 Kubernetes Deployment

```
k8s/
├── namespace.yaml
├── deployments/
│   ├── api-gateway.yaml
│   ├── user-service.yaml
│   ├── event-service.yaml
│   ├── recommendation-service.yaml
│   ├── model-service.yaml
│   ├── experimentation-service.yaml
│   └── streamlit.yaml
├── services/
│   ├── api-gateway-svc.yaml
│   ├── kafka-svc.yaml
│   └── ...
├── configmaps/
│   ├── app-config.yaml
│   └── prometheus-config.yaml
├── secrets/
│   └── db-credentials.yaml
└── ingress/
    └── ingress.yaml
```

**Key K8s patterns:**

- **Deployments**: replicas, resource limits, liveness/readiness probes
- **Services**: ClusterIP for internal, LoadBalancer/NodePort for external
- **ConfigMaps**: non-sensitive config (Kafka brokers, Redis host)
- **Secrets**: database credentials, API keys
- **HPA**: Horizontal Pod Autoscaler on Recommendation Service and Model Service
