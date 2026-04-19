# Runbook — Real-Time Recommendation System

## 1. Starting the System (Docker Compose)

### Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- 16 GB RAM minimum (Spark + Kafka are memory-intensive)
- Ports available: 8000-8005, 8501, 9090, 3000, 5000, 5432, 6379, 9092

### Start All Services

```bash
# Clone and navigate
cd recommendation-system

# Create environment file
cp .env.example .env

# Start infrastructure first
docker-compose up -d zookeeper kafka postgres redis mlflow

# Wait for infrastructure readiness (30s)
sleep 30

# Start application services
docker-compose up -d api-gateway user-service event-service \
  recommendation-service model-service experimentation-service

# Start processing layer
docker-compose up -d spark-master spark-worker airflow-webserver airflow-scheduler

# Start monitoring
docker-compose up -d prometheus grafana

# Start frontend
docker-compose up -d streamlit
```

### Verify All Services

```bash
# Check all containers are running
docker-compose ps

# Health checks
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # User Service
curl http://localhost:8002/health  # Event Service
curl http://localhost:8003/health  # Recommendation Service
curl http://localhost:8004/health  # Model Service
curl http://localhost:8005/health  # Experimentation Service
```

### Stop All Services

```bash
docker-compose down          # Stop containers
docker-compose down -v       # Stop + remove volumes (data loss)
```

---

## 2. Kubernetes Deployment

### Prerequisites

- `kubectl` configured with cluster access
- Container images pushed to registry

### Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy secrets and config
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/configmaps/

# Deploy infrastructure
kubectl apply -f k8s/deployments/kafka.yaml
kubectl apply -f k8s/deployments/postgres.yaml
kubectl apply -f k8s/deployments/redis.yaml
kubectl apply -f k8s/services/

# Wait for infra readiness
kubectl wait --for=condition=ready pod -l app=kafka --timeout=120s
kubectl wait --for=condition=ready pod -l app=postgres --timeout=60s

# Deploy application services
kubectl apply -f k8s/deployments/

# Deploy ingress
kubectl apply -f k8s/ingress/

# Verify
kubectl get pods -n recsys
kubectl get svc -n recsys
```

### Scaling

```bash
# Scale recommendation service
kubectl scale deployment recommendation-service --replicas=3 -n recsys

# Apply HPA
kubectl apply -f k8s/hpa/recommendation-service-hpa.yaml
```

---

## 3. Debugging Failures

### Service Won't Start

| Symptom | Check | Fix |
|---------|-------|-----|
| Container exits immediately | `docker logs <container>` | Check env vars, port conflicts |
| Health check fails | `curl localhost:<port>/health` | Check dependency services are up |
| Connection refused | `docker network ls` | Ensure services are on same network |
| OOM killed | `docker stats` | Increase Docker memory limit |

### Kafka Issues

```bash
# Check Kafka broker status
docker exec -it kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# List topics
docker exec -it kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Check consumer lag
docker exec -it kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group spark-streaming-group

# Reset consumer offset (CAUTION)
docker exec -it kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group spark-streaming-group \
  --topic user-events \
  --reset-offsets --to-earliest --execute
```

### Spark Job Failures

```bash
# Check Spark UI
open http://localhost:8080  # Spark Master UI

# Check streaming job logs
docker logs spark-worker --tail 200

# Common issues:
# - OOM: Increase spark.executor.memory
# - Kafka connection: Verify bootstrap.servers config
# - Schema mismatch: Check event schema version
```

### Database Issues

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U recsys -d recsys_db

# Check connections
SELECT count(*) FROM pg_stat_activity;

# Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;
```

### Redis Issues

```bash
# Connect to Redis CLI
docker exec -it redis redis-cli

# Check memory
INFO memory

# Check key count
DBSIZE

# Flush cache (CAUTION)
FLUSHDB
```

---

## 4. Model Retraining

### Manual Retraining

```bash
# Trigger Airflow DAG
curl -X POST http://localhost:8080/api/v1/dags/model_training_dag/dagRuns \
  -H "Content-Type: application/json" \
  -d '{"conf": {}}'
```

### Retraining Workflow

1. Airflow triggers batch feature engineering (Spark)
2. Training dataset is prepared from Feature Store
3. ALS candidate generation model is trained
4. Ranking model is trained
5. Models are evaluated against holdout set
6. If metrics improve, models are registered in MLflow
7. Model Service picks up new version on next health check

### Verify Retraining

```bash
# Check MLflow for new model versions
curl http://localhost:5000/api/2.0/mlflow/registered-models/get?name=recommendation-model

# Check Model Service is using latest version
curl http://localhost:8004/health  # Returns loaded model version
```

### Rollback Model

```bash
# In MLflow, transition previous version to Production
curl -X POST http://localhost:5000/api/2.0/mlflow/model-versions/transition-stage \
  -H "Content-Type: application/json" \
  -d '{"name": "recommendation-model", "version": "1", "stage": "Production"}'

# Restart Model Service to pick up change
docker-compose restart model-service
```

---

## 5. Monitoring (Prometheus + Grafana)

### Access Dashboards

| Tool | URL | Credentials |
|------|-----|-------------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Airflow | http://localhost:8080 | admin / admin |
| MLflow | http://localhost:5000 | — |
| Spark Master | http://localhost:8080 | — |

### Key Prometheus Queries

```promql
# Request rate per service
rate(http_requests_total[5m])

# P95 latency per endpoint
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_errors_total[5m]) / rate(http_requests_total[5m])

# Kafka consumer lag
kafka_consumer_lag

# Model inference latency
histogram_quantile(0.99, rate(model_inference_seconds_bucket[5m]))
```

### Grafana Dashboard Setup

1. Navigate to http://localhost:3000
2. Add Prometheus data source: `http://prometheus:9090`
3. Import dashboards from `monitoring/grafana/dashboards/`
4. Verify all panels are receiving data

### Alerting Rules

Critical alerts configured in `monitoring/prometheus/alert_rules.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | error_rate > 5% for 5m | critical |
| HighLatency | p95_latency > 500ms for 5m | warning |
| KafkaLagHigh | consumer_lag > 10000 for 10m | warning |
| ServiceDown | up == 0 for 1m | critical |
| ModelStale | model_age_hours > 48 | warning |

---

## 6. Common Failure Scenarios and Fixes

### Scenario 1: Recommendations Return Empty

**Symptoms:** `/recommendations` returns empty list  
**Root Causes:**
1. No trained model in MLflow registry
2. Redis cache is empty and Model Service is down
3. Feature Store has no data for the user

**Fix:**
```bash
# 1. Check Model Service
curl http://localhost:8004/health

# 2. Check if model exists in MLflow
curl http://localhost:5000/api/2.0/mlflow/registered-models/list

# 3. If no model, trigger training
# (see Section 4: Model Retraining)

# 4. Check Redis
docker exec -it redis redis-cli DBSIZE
```

### Scenario 2: Events Not Flowing

**Symptoms:** Events submitted but not appearing in Feature Store  
**Root Causes:**
1. Kafka producer failing silently
2. Spark Streaming job crashed
3. Feature Store write permissions

**Fix:**
```bash
# 1. Check Event Service logs
docker logs event-service --tail 50

# 2. Verify Kafka topic has messages
docker exec -it kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic user-events --from-beginning --max-messages 5

# 3. Check Spark Streaming job
docker logs spark-worker --tail 100

# 4. Restart Spark Streaming if crashed
docker-compose restart spark-worker
```

### Scenario 3: High Latency on Recommendations

**Symptoms:** `/recommendations` takes > 1s  
**Root Causes:**
1. Redis cache miss (cold cache)
2. Model Service overloaded
3. Experimentation Service slow

**Fix:**
```bash
# 1. Check cache hit rate
curl http://localhost:8003/metrics | grep cache_hit

# 2. Check Model Service latency
curl http://localhost:8004/metrics | grep inference

# 3. Scale Model Service
docker-compose up -d --scale model-service=3
```

### Scenario 4: A/B Test Metrics Not Updating

**Symptoms:** Experiment dashboard shows stale metrics  
**Root Causes:**
1. Event Service not tagging events with experiment group
2. Metrics aggregation pipeline not running

**Fix:**
```bash
# 1. Check experiment assignment
curl "http://localhost:8005/assign-group?user_id=test_user&experiment_id=exp_1"

# 2. Verify events include experiment metadata
docker exec -it kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic user-events --from-beginning --max-messages 1

# 3. Check Experimentation Service logs
docker logs experimentation-service --tail 50
```

### Scenario 5: Drift Detected

**Symptoms:** Evidently report shows significant data drift  
**Root Causes:**
1. Data distribution shift (seasonal, new users)
2. Schema change in upstream events

**Fix:**
```bash
# 1. Review Evidently report (stored in MLflow artifacts)
# Navigate to MLflow UI → latest run → artifacts → drift_report.html

# 2. If drift is significant, trigger retraining
# (see Section 4: Model Retraining)

# 3. If schema change, update Feature Pipeline schemas
# Then rebuild Feature Store
```
