# Task 12: Kubernetes Deployment

## Goal

Create production-grade Kubernetes manifests for all services. Define Deployments, Services, ConfigMaps, Secrets, Horizontal Pod Autoscalers, and an Ingress. Ensure the system is deployable, scalable, and self-healing.

## Context

Kubernetes is the production deployment target. While Docker Compose handles local dev, K8s provides scaling, rolling updates, health-based restarts, and secrets management. Every service must have liveness/readiness probes, resource limits, and proper configuration injection.

## Requirements

### Functional
- All services deployable to a Kubernetes cluster
- Proper service discovery (ClusterIP services)
- External access via Ingress (API Gateway + Streamlit)
- Configuration via ConfigMaps (non-sensitive) and Secrets (credentials)
- Auto-scaling for Recommendation and Model services
- Liveness and readiness probes for all pods

### Technical Constraints
- Kubernetes manifests (mandatory per spec)
- Must define: Deployments, Services, ConfigMaps, Secrets
- Resource requests and limits for all containers
- Rolling update strategy for zero-downtime deployments

## Implementation Steps

### Step 1: Namespace

Create `k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: recsys
  labels:
    app.kubernetes.io/part-of: recommendation-system
```

### Step 2: ConfigMaps

Create `k8s/configmaps/app-config.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: recsys
data:
  KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  MLFLOW_TRACKING_URI: "http://mlflow:5000"
  POSTGRES_HOST: "postgres"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "recsys_db"
  LOG_LEVEL: "INFO"
  FEATURE_STORE_PATH: "/data/feature_store"
```

Create `k8s/configmaps/prometheus-config.yaml`:

```yaml
# Mount prometheus.yml as a ConfigMap
# Reference monitoring/prometheus/prometheus.yml content
```

### Step 3: Secrets

Create `k8s/secrets/db-credentials.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: recsys
type: Opaque
data:
  POSTGRES_USER: cmVjc3lz          # base64 encoded
  POSTGRES_PASSWORD: <base64>       # base64 encoded
  MLFLOW_DB_URI: <base64>           # base64 encoded
```

### Step 4: Infrastructure Deployments

Create deployments for stateful infrastructure:

**`k8s/deployments/kafka.yaml`**:
- Zookeeper + Kafka as StatefulSet (for stable network identity)
- Persistent volume for Kafka data
- Resource limits: 1 CPU, 2Gi memory

**`k8s/deployments/postgres.yaml`**:
- Single-replica StatefulSet
- PersistentVolumeClaim: 10Gi
- Resource limits: 500m CPU, 1Gi memory

**`k8s/deployments/redis.yaml`**:
- Single-replica Deployment
- Resource limits: 250m CPU, 512Mi memory

**`k8s/deployments/mlflow.yaml`**:
- Single-replica Deployment
- Depends on PostgreSQL (via init container or startup probe)
- Resource limits: 500m CPU, 1Gi memory

### Step 5: Application Deployments

For each service, create a Deployment with this template structure:

**`k8s/deployments/api-gateway.yaml`** (example pattern for all services):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: recsys
  labels:
    app: api-gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-gateway
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: api-gateway
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      containers:
        - name: api-gateway
          image: recsys/api-gateway:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: db-credentials
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 30
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

Create similar deployments for:
- `k8s/deployments/user-service.yaml` (1 replica)
- `k8s/deployments/event-service.yaml` (2 replicas)
- `k8s/deployments/recommendation-service.yaml` (2 replicas)
- `k8s/deployments/model-service.yaml` (2 replicas)
- `k8s/deployments/experimentation-service.yaml` (1 replica)
- `k8s/deployments/streamlit.yaml` (1 replica)

### Step 6: Kubernetes Services

Create ClusterIP services for internal communication:

**`k8s/services/`** — one file per service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: recsys
spec:
  type: ClusterIP
  selector:
    app: api-gateway
  ports:
    - port: 8000
      targetPort: 8000
```

Services to create:
- `api-gateway-svc.yaml` (ClusterIP)
- `user-service-svc.yaml` (ClusterIP)
- `event-service-svc.yaml` (ClusterIP)
- `recommendation-service-svc.yaml` (ClusterIP)
- `model-service-svc.yaml` (ClusterIP)
- `experimentation-service-svc.yaml` (ClusterIP)
- `kafka-svc.yaml` (ClusterIP, headless for StatefulSet)
- `postgres-svc.yaml` (ClusterIP)
- `redis-svc.yaml` (ClusterIP)
- `mlflow-svc.yaml` (ClusterIP)
- `prometheus-svc.yaml` (ClusterIP)
- `grafana-svc.yaml` (ClusterIP)

### Step 7: Horizontal Pod Autoscaler

Create `k8s/hpa/recommendation-service-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: recommendation-service-hpa
  namespace: recsys
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: recommendation-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

Create similar HPA for `model-service`.

### Step 8: Ingress

Create `k8s/ingress/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: recsys-ingress
  namespace: recsys
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: recsys.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: streamlit
                port:
                  number: 8501
          - path: /grafana
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 3000
```

### Step 9: Deployment Script

Create `k8s/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "Deploying RecSys to Kubernetes..."

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/configmaps/

echo "Deploying infrastructure..."
kubectl apply -f k8s/deployments/postgres.yaml
kubectl apply -f k8s/deployments/kafka.yaml
kubectl apply -f k8s/deployments/redis.yaml
kubectl apply -f k8s/deployments/mlflow.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n recsys --timeout=120s
kubectl wait --for=condition=ready pod -l app=kafka -n recsys --timeout=120s

echo "Deploying application services..."
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/

echo "Deploying autoscalers..."
kubectl apply -f k8s/hpa/

echo "Deploying ingress..."
kubectl apply -f k8s/ingress/

echo "Verifying deployment..."
kubectl get pods -n recsys
kubectl get svc -n recsys

echo "Deployment complete!"
```

## Deliverables

| File | Purpose |
|------|---------|
| `k8s/namespace.yaml` | Namespace definition |
| `k8s/configmaps/app-config.yaml` | Application configuration |
| `k8s/configmaps/prometheus-config.yaml` | Prometheus configuration |
| `k8s/secrets/db-credentials.yaml` | Database credentials |
| `k8s/deployments/*.yaml` | All service deployments (12+ files) |
| `k8s/services/*.yaml` | All K8s services (12+ files) |
| `k8s/hpa/*.yaml` | Autoscaler definitions |
| `k8s/ingress/ingress.yaml` | Ingress routing |
| `k8s/deploy.sh` | Deployment script |

## Validation

1. Run `k8s/deploy.sh` against a cluster (minikube or kind for local testing)
2. `kubectl get pods -n recsys` → all pods Running, READY
3. `kubectl get svc -n recsys` → all services have ClusterIPs
4. Port-forward API Gateway: `kubectl port-forward svc/api-gateway 8000:8000 -n recsys`
5. Health check: `curl http://localhost:8000/health` → all services healthy
6. Port-forward Grafana: verify dashboards load
7. Scale test: `kubectl scale deployment recommendation-service --replicas=5 -n recsys` → pods scale
8. HPA test: generate load → verify HPA scales pods automatically
9. Rolling update: change image tag → verify zero-downtime update
10. Self-healing: `kubectl delete pod <pod-name> -n recsys` → pod auto-recreated
11. Verify liveness probes: stop a service process → pod restarts automatically
