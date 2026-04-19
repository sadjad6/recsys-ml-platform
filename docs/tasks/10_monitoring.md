# Task 10: Monitoring & Observability (Prometheus + Grafana + Evidently)

## Goal

Implement full production observability: Prometheus metrics collection from every service, Grafana dashboards for visualization, alert rules for critical thresholds, and Evidently for ML-specific drift detection.

## Context

Monitoring is non-negotiable for production systems. Every FastAPI service already exposes a `/metrics` endpoint (set up in Task 06 shared utilities). This task configures Prometheus to scrape those endpoints, builds Grafana dashboards, defines alerting rules, and integrates Evidently drift reports into the monitoring flow.

## Requirements

### Functional
- Prometheus scrapes all services every 15 seconds
- Grafana dashboards: API performance, Kafka monitoring, model inference, system health
- Alert rules for: high error rate, high latency, service down, Kafka lag, model staleness
- Evidently drift reports generated on schedule and accessible via Grafana or MLflow

### Technical Constraints
- Prometheus + Grafana (mandatory per spec)
- Evidently for drift detection (mandatory per spec)
- Both must be containerized
- Dashboards must be provisioned automatically (no manual setup)

## Implementation Steps

### Step 1: Prometheus Configuration

Create `monitoring/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: "api-gateway"
    static_configs:
      - targets: ["api-gateway:8000"]

  - job_name: "user-service"
    static_configs:
      - targets: ["user-service:8001"]

  - job_name: "event-service"
    static_configs:
      - targets: ["event-service:8002"]

  - job_name: "recommendation-service"
    static_configs:
      - targets: ["recommendation-service:8003"]

  - job_name: "model-service"
    static_configs:
      - targets: ["model-service:8004"]

  - job_name: "experimentation-service"
    static_configs:
      - targets: ["experimentation-service:8005"]

  - job_name: "kafka"
    static_configs:
      - targets: ["kafka-exporter:9308"]
```

### Step 2: Alert Rules

Create `monitoring/prometheus/alert_rules.yml`:

```yaml
groups:
  - name: service_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5% on {{ $labels.job }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 500ms on {{ $labels.job }}"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"

      - alert: KafkaConsumerLagHigh
        expr: kafka_consumer_lag > 10000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag above 10k on {{ $labels.topic }}"

      - alert: ModelStale
        expr: (time() - model_last_loaded_timestamp) / 3600 > 48
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Model not refreshed in 48+ hours"
```

### Step 3: Grafana Dashboard — API Performance

Create `monitoring/grafana/dashboards/api_performance.json`:

Panels:
1. **Request Rate** — `rate(http_requests_total[5m])` per service (time series)
2. **P50/P95/P99 Latency** — `histogram_quantile` per endpoint (time series)
3. **Error Rate** — `rate(http_errors_total[5m])` per service (time series)
4. **Throughput** — `sum(rate(http_requests_total[5m]))` total (stat panel)
5. **Status Code Distribution** — `http_requests_total` by status code (pie chart)
6. **Top Slowest Endpoints** — sorted by P95 latency (table)

### Step 4: Grafana Dashboard — Kafka Monitoring

Create `monitoring/grafana/dashboards/kafka_monitoring.json`:

Panels:
1. **Consumer Lag** — `kafka_consumer_lag` by topic and group (time series)
2. **Messages In/Out** — `kafka_topic_messages_in_total` per topic (time series)
3. **Partition Count** — `kafka_topic_partitions` per topic (stat)
4. **Broker Status** — `kafka_broker_info` (table)

### Step 5: Grafana Dashboard — Model Performance

Create `monitoring/grafana/dashboards/model_performance.json`:

Panels:
1. **Inference Latency** — `model_inference_seconds` P50/P95/P99 (time series)
2. **Predictions per Second** — `rate(model_predictions_total[5m])` (time series)
3. **Cache Hit Rate** — `cache_hits / (cache_hits + cache_misses)` (gauge)
4. **Model Version** — currently loaded version (stat)
5. **Stage Breakdown** — candidate gen / ranking / reranking latency (stacked bar)
6. **A/B Test Metrics** — CTR per experiment group (time series)

### Step 6: Grafana Dashboard — System Health

Create `monitoring/grafana/dashboards/system_health.json`:

Panels:
1. **Service Status** — `up` metric per job (status map)
2. **Active Alerts** — current firing alerts (alert list)
3. **Container CPU** — process CPU usage per service (time series)
4. **Container Memory** — process memory usage per service (time series)

### Step 7: Grafana Auto-Provisioning

Create `monitoring/grafana/provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

Create `monitoring/grafana/provisioning/dashboards/dashboards.yml`:

```yaml
apiVersion: 1
providers:
  - name: "default"
    folder: "RecSys"
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

### Step 8: Docker Configuration

Add to `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:v2.50.0
  ports:
    - "9090:9090"
  volumes:
    - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    - ./monitoring/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml

grafana:
  image: grafana/grafana:10.3.0
  ports:
    - "3000:3000"
  volumes:
    - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin

kafka-exporter:
  image: danielqsj/kafka-exporter:latest
  command: ["--kafka.server=kafka:9092"]
  ports:
    - "9308:9308"
```

### Step 9: Evidently Drift Monitoring

Create `monitoring/evidently/drift_monitor.py`:

```python
# Scheduled via Airflow (daily after training)
# 1. Load reference dataset (last training data)
# 2. Load current dataset (latest Feature Store snapshot)
# 3. Generate reports:
#    - DataDriftPreset: feature distribution shifts
#    - TargetDriftPreset: prediction distribution shifts
#    - DataQualityPreset: missing values, duplicates
# 4. Save HTML reports to monitoring/evidently/reports/
# 5. Log reports as MLflow artifacts
# 6. If drift detected, push metric to Prometheus pushgateway
```

## Deliverables

| File | Purpose |
|------|---------|
| `monitoring/prometheus/prometheus.yml` | Scrape config |
| `monitoring/prometheus/alert_rules.yml` | Alert definitions |
| `monitoring/grafana/dashboards/api_performance.json` | API dashboard |
| `monitoring/grafana/dashboards/kafka_monitoring.json` | Kafka dashboard |
| `monitoring/grafana/dashboards/model_performance.json` | Model dashboard |
| `monitoring/grafana/dashboards/system_health.json` | System dashboard |
| `monitoring/grafana/provisioning/` | Auto-provisioning configs |
| `monitoring/evidently/drift_monitor.py` | Drift detection script |
| Updated `docker-compose.yml` | Prometheus + Grafana + Kafka exporter |

## Validation

1. Start monitoring: `docker-compose up -d prometheus grafana kafka-exporter`
2. Prometheus targets: `http://localhost:9090/targets` → all targets "UP"
3. Grafana login: `http://localhost:3000` (admin/admin)
4. Verify Prometheus data source is auto-configured
5. Verify all 4 dashboards are auto-provisioned and showing data
6. Generate traffic → verify dashboard panels update in real-time
7. Simulate error (stop a service) → verify ServiceDown alert fires
8. Run Evidently drift monitor → verify HTML report is generated
9. Check that drift metric appears in Prometheus
