# 🚀 Setup & Deployment Guide — RecSys ML Platform

This document provides step-by-step instructions to set up, configure, and run the RecSys ML Platform from scratch on your local machine.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Environment Configuration](#3-environment-configuration)
4. [Directory & Data Preparation](#4-directory--data-preparation)
5. [Starting Infrastructure Services](#5-starting-infrastructure-services)
6. [Starting Application Services](#6-starting-application-services)
7. [Starting the Full Stack](#7-starting-the-full-stack)
8. [Verifying Services](#8-verifying-services)
9. [Creating an A/B Experiment](#9-creating-an-ab-experiment)
10. [Running the Kafka Event Producer](#10-running-the-kafka-event-producer)
11. [Submitting a Spark Streaming Job](#11-submitting-a-spark-streaming-job)
12. [Accessing Monitoring Dashboards](#12-accessing-monitoring-dashboards)
13. [Kubernetes Deployment](#13-kubernetes-deployment)
14. [Troubleshooting](#14-troubleshooting)
15. [Shutting Down](#15-shutting-down)

---

## 1. Prerequisites

Ensure the following software is installed on your machine before proceeding:

| Tool              | Minimum Version | Purpose                    | Installation Link                                    |
|-------------------|-----------------|----------------------------|------------------------------------------------------|
| **Docker**        | 24.0+           | Container runtime          | https://docs.docker.com/get-docker/                  |
| **Docker Compose**| v2.20+          | Multi-container orchestration | Bundled with Docker Desktop                        |
| **Git**           | 2.30+           | Version control            | https://git-scm.com/                                 |
| **Python**        | 3.12+           | Local scripting (optional) | https://www.python.org/downloads/                    |
| **kubectl**       | 1.28+ (optional)| Kubernetes CLI             | https://kubernetes.io/docs/tasks/tools/              |
| **Minikube**      | 1.32+ (optional)| Local K8s cluster          | https://minikube.sigs.k8s.io/docs/start/             |

### System Requirements

- **RAM**: At least **12 GB** available (16 GB recommended). The full stack runs 15+ containers.
- **Disk**: At least **10 GB** free for Docker images and volumes.
- **CPU**: 4+ cores recommended.

> **Windows Users**: Use Docker Desktop with WSL 2 backend enabled for best performance. Ensure WSL 2 memory allocation is set to at least 8 GB in `%USERPROFILE%\.wslconfig`:
> ```ini
> [wsl2]
> memory=8GB
> processors=4
> ```

---

## 2. Clone the Repository

```bash
git clone https://github.com/sadjad6/recsys-ml-platform.git
cd recsys-ml-platform
```

---

## 3. Environment Configuration

### 3.1 Create the `.env` File

The project ships with a `.env.example` template. Copy it:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

### 3.2 Review and Adjust Variables

Open `.env` in your editor and review the following sections. **The defaults work out-of-the-box for local development**, but you may need to adjust them for your environment:

#### Kafka Configuration

```dotenv
KAFKA_BROKER_ID=1
KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_BOOTSTRAP_SERVERS_HOST=localhost:9092
```

> **When to change**: Only if you're running Kafka outside Docker or have port conflicts on `9092`.

#### PostgreSQL Credentials

```dotenv
POSTGRES_USER=recsys
POSTGRES_PASSWORD=recsys_secret
POSTGRES_DB=recsys_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

> **⚠ IMPORTANT**: If you change `POSTGRES_USER` or `POSTGRES_PASSWORD`, you must also update the connection strings for the services that reference them directly in `docker-compose.yml`:
> - `user-service` → `POSTGRES_URL`
> - `experimentation-service` → `DATABASE_URL`
> - `mlflow` → `MLFLOW_BACKEND_STORE_URI`
> - `airflow-webserver` and `airflow-scheduler` → `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`

#### Redis Configuration

```dotenv
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

> **When to change**: Only if port `6379` is already in use on your machine.

#### MLflow Configuration

```dotenv
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://recsys:recsys_secret@postgres:5432/mlflow_db
MLFLOW_ARTIFACT_ROOT=/mlflow/artifacts
```

> **When to change**: These are internal Docker network addresses and generally don't need modification.

#### Service Ports

```dotenv
API_GATEWAY_PORT=8000
USER_SERVICE_PORT=8001
EVENT_SERVICE_PORT=8002
RECOMMENDATION_SERVICE_PORT=8003
MODEL_SERVICE_PORT=8004
EXPERIMENTATION_SERVICE_PORT=8005
STREAMLIT_PORT=8501
```

> **When to change**: If any of these ports (8000–8005, 8501) are occupied by other applications on your host.  
> **If you change a port**, update the corresponding `ports:` mapping in `docker-compose.yml` (e.g., change `"8000:8000"` to `"9000:8000"`). Only change the **host** port (left side).

#### Monitoring Configuration

```dotenv
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

> **⚠ SECURITY**: Change `GRAFANA_ADMIN_PASSWORD` for any non-local deployment.

#### Spark Configuration

```dotenv
SPARK_MASTER_URL=spark://spark-master:7077
SPARK_MASTER_WEBUI_PORT=8090
```

> **When to change**: Only if port `8080` (Spark Master WebUI) or `7077` conflicts with other services.

#### Kafka Producer (Simulation) Settings

```dotenv
PRODUCER_EVENTS_PER_SECOND=10
PRODUCER_NUM_USERS=1000
PRODUCER_NUM_ITEMS=500
PRODUCER_BATCH_SIZE=100
```

> **Adjusting load**: Lower `PRODUCER_EVENTS_PER_SECOND` on machines with less RAM. Raise it for stress testing.

---

## 4. Directory & Data Preparation

Create the necessary data directory that Spark and Airflow mount:

```bash
# Linux / macOS
mkdir -p data/feature_store data/training_datasets data/raw

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path data/feature_store, data/training_datasets, data/raw
```

This `data/` directory is bind-mounted into Spark, Airflow, and model training containers.

---

## 5. Starting Infrastructure Services

It is recommended to start infrastructure first, then the application layer. This ensures databases and message brokers are ready before microservices try to connect.

### Step 1: Start Core Infrastructure

```bash
docker compose up -d zookeeper kafka postgres redis mlflow
```

Wait for all services to become healthy:

```bash
docker compose ps
```

Ensure `kafka`, `postgres`, and `zookeeper` show `healthy` status before proceeding. This typically takes 30–60 seconds.

### Step 2: Initialize Kafka Topics

The `kafka-init` service runs automatically when Kafka is healthy, but you can run it manually:

```bash
docker compose up kafka-init
```

Verify topics were created:

```bash
docker exec recsys-kafka kafka-topics --list --bootstrap-server localhost:9092
```

Expected output:
```
user-events
recommendations-served
```

### Step 3: Start Airflow

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

On first startup, Airflow will initialize its database and create an admin user (`admin`/`admin`). This takes 1–2 minutes.

- **Airflow UI**: http://localhost:8080 (user: `admin`, password: `admin`)

### Step 4: Start Spark

```bash
docker compose up -d spark-master spark-worker
```

- **Spark Master UI**: http://localhost:8080

> **Note**: Both Airflow and Spark use port 8080 by default. If running both, change one of them in `docker-compose.yml`.

---

## 6. Starting Application Services

Once infrastructure is ready, start the microservices:

```bash
docker compose up -d api-gateway user-service event-service model-service recommendation-service experimentation-service
```

Then start the frontend and monitoring:

```bash
docker compose up -d streamlit prometheus grafana kafka-exporter
```

---

## 7. Starting the Full Stack

If you prefer to start everything at once (after ensuring your `.env` is configured):

```bash
docker compose up -d
```

> **Note**: The `kafka-producer` service is behind a Docker Compose profile and will NOT start automatically. See [Section 10](#10-running-the-kafka-event-producer) for how to start it.

To watch all logs in real time:

```bash
docker compose logs -f
```

To check overall status:

```bash
docker compose ps
```

---

## 8. Verifying Services

After all containers are running, verify each service is healthy:

| Service                  | Health Check URL                                    | Expected Response            |
|--------------------------|-----------------------------------------------------|------------------------------|
| API Gateway              | http://localhost:8000/health                        | `{"service": "api-gateway", "status": "healthy"}` |
| User Service             | http://localhost:8001/health                        | `{"service": "user-service", "status": "healthy"}` |
| Event Service            | http://localhost:8002/health                        | `{"service": "event-service", "status": "healthy"}` |
| Recommendation Service   | http://localhost:8003/health                        | `{"service": "recommendation-service", "status": "healthy"}` |
| Model Service            | http://localhost:8004/health                        | `{"service": "model-service", "status": "healthy"}` |
| Experimentation Service  | http://localhost:8005/health                        | `{"service": "experimentation-service", "status": "healthy"}` |
| Streamlit Frontend       | http://localhost:8501                               | Streamlit UI loads           |
| MLflow                   | http://localhost:5000                               | MLflow UI loads              |
| Prometheus               | http://localhost:9090/targets                       | Scrape targets listed        |
| Grafana                  | http://localhost:3000                               | Login page (admin/admin)     |

Quick check with `curl` (or PowerShell `Invoke-WebRequest`):

```bash
# Linux / macOS
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Windows PowerShell
Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content
```

### API Documentation (Swagger UI)

Each FastAPI service auto-generates interactive API docs:

- http://localhost:8000/docs — API Gateway
- http://localhost:8001/docs — User Service
- http://localhost:8002/docs — Event Service
- http://localhost:8003/docs — Recommendation Service
- http://localhost:8004/docs — Model Service
- http://localhost:8005/docs — Experimentation Service

---

## 9. Creating an A/B Experiment

Before the recommendation flow works with A/B testing, you need to create an experiment:

```bash
curl -X POST http://localhost:8005/api/v1/experiments/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "model-comparison-v1",
    "description": "Compare baseline ALS vs. improved ranking model",
    "control_model_version": "production",
    "treatment_model_version": "challenger-v2",
    "traffic_percentage": 50,
    "status": "active"
  }'
```

Verify assignment works:

```bash
curl "http://localhost:8005/api/v1/experiments/assign?user_id=user_123"
```

Expected output:
```json
{"group": "control", "model_version": "production"}
```

---

## 10. Running the Kafka Event Producer

The producer simulates real-time user interactions (clicks, views, ratings). It is in a Docker Compose profile to avoid automatic startup:

```bash
docker compose --profile producer up -d kafka-producer
```

Check producer logs:

```bash
docker compose logs -f kafka-producer
```

You should see events being published every second. To verify events are arriving in Kafka:

```bash
docker exec recsys-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic user-events \
  --from-beginning \
  --max-messages 5
```

---

## 11. Submitting a Spark Streaming Job

To start the Spark Structured Streaming pipeline that consumes from Kafka:

```bash
docker exec recsys-spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /app/spark/streaming/stream_processor.py
```

This will:
1. Consume events from the `user-events` Kafka topic
2. Compute streaming features (recency, frequency, aggregates)
3. Trigger online learning updates (embedding + feature store)
4. Write processed features to the feature store

---

## 12. Accessing Monitoring Dashboards

### Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin` (or whatever you set in `.env`)
3. Navigate to **Dashboards** → **Browse**
4. Four pre-provisioned dashboards are available:
   - **API Performance** — Request latency, throughput, error rates
   - **Kafka Monitoring** — Consumer lag, message throughput
   - **Model Performance** — Inference latency by stage, predictions/sec
   - **System Health** — CPU, memory, service uptime

### Prometheus

1. Open http://localhost:9090
2. Go to **Status** → **Targets** to verify all scrape targets are `UP`
3. Try a query: `rate(http_requests_total[5m])` to see request rates

### Airflow DAGs

1. Open http://localhost:8080
2. Login with `admin` / `admin`
3. You should see 4 DAGs:
   - `data_ingestion_dag` — Scheduled data ingestion
   - `feature_engineering_dag` — Batch feature engineering
   - `model_training_dag` — ALS + ranking training → MLflow registration → Model Service reload
   - `warm_start_retrain_dag` — Drift-triggered warm-start retraining

To manually trigger a DAG, click the **Play** button on the DAG row.

---

## 13. Kubernetes Deployment

### Prerequisites

- A running Kubernetes cluster (`minikube start` for local)
- `kubectl` configured to point to the cluster

### Build and Push Docker Images

Before deploying to K8s, build the application images:

```bash
# Build all service images
docker compose build

# Tag for your registry (example with a local registry)
docker tag recsys/api-gateway:latest localhost:5000/recsys/api-gateway:latest
docker push localhost:5000/recsys/api-gateway:latest
# ... repeat for each service
```

> **Minikube shortcut**: Use `eval $(minikube docker-env)` to build directly into Minikube's Docker daemon, avoiding the need for a registry.

### Deploy

```bash
# From the project root
cd k8s
bash deploy.sh
```

### Update /etc/hosts

Add the Ingress hostname to your hosts file:

```bash
# Linux / macOS
echo "127.0.0.1 recsys.local" | sudo tee -a /etc/hosts

# Windows (Run as Administrator)
Add-Content C:\Windows\System32\drivers\etc\hosts "127.0.0.1 recsys.local"
```

### Verify

```bash
kubectl get pods -n recsys
kubectl get svc -n recsys
kubectl get ingress -n recsys
```

### Access

- **Frontend**: http://recsys.local
- **API**: http://recsys.local/api
- **Grafana**: http://recsys.local/grafana

---

## 14. Troubleshooting

### Container won't start / exits immediately

```bash
docker compose logs <service-name>
```

Common causes:
- **PostgreSQL not ready**: Increase `start_period` in health checks
- **Port conflicts**: Another process is using the port. Check with `netstat -tlnp` (Linux) or `Get-NetTCPConnection -LocalPort 8000` (PowerShell)
- **Out of memory**: Reduce `SPARK_WORKER_MEMORY` or stop unused services

### Kafka "broker not available"

Kafka needs 20–30 seconds after startup. If services start before Kafka is healthy:

```bash
docker compose restart event-service kafka-producer
```

### MLflow "connection refused"

MLflow depends on PostgreSQL. Ensure `postgres` is healthy first:

```bash
docker compose restart mlflow
```

### Airflow "database not initialized"

On first run, the webserver container initializes the DB. If it fails:

```bash
docker exec recsys-airflow-webserver airflow db init
docker compose restart airflow-webserver airflow-scheduler
```

### Services can't find each other

All services must be on the `recsys-network` Docker network. Verify:

```bash
docker network inspect recsys-network
```

### Reset everything (clean slate)

```bash
docker compose down -v    # Removes containers AND volumes (data loss!)
docker compose up -d      # Fresh start
```

---

## 15. Shutting Down

### Stop all services (keep data)

```bash
docker compose down
```

### Stop all services AND delete data volumes

```bash
docker compose down -v
```

### Stop specific services

```bash
docker compose stop streamlit grafana prometheus
```

---

## Quick Reference: Port Map

| Port  | Service                  |
|-------|--------------------------|
| 2181  | Zookeeper                |
| 3000  | Grafana                  |
| 5000  | MLflow                   |
| 6379  | Redis                    |
| 7077  | Spark Master (RPC)       |
| 8000  | API Gateway              |
| 8001  | User Service             |
| 8002  | Event Service            |
| 8003  | Recommendation Service   |
| 8004  | Model Service            |
| 8005  | Experimentation Service  |
| 8080  | Spark Master WebUI / Airflow |
| 8081  | Spark Worker WebUI       |
| 8501  | Streamlit Frontend       |
| 9090  | Prometheus               |
| 9092  | Kafka (host access)      |
| 9308  | Kafka Exporter           |
