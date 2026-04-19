import os
import textwrap

BASE_DIR = "k8s"
DIRS = [
    "configmaps",
    "secrets",
    "deployments",
    "services",
    "hpa",
    "ingress"
]

def create_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    for d in DIRS:
        os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

def write_file(path, content):
    with open(os.path.join(BASE_DIR, path), "w") as f:
        f.write(textwrap.dedent(content).strip() + "\n")

def generate():
    create_dirs()

    # Namespace
    write_file("namespace.yaml", """
        apiVersion: v1
        kind: Namespace
        metadata:
          name: recsys
          labels:
            app.kubernetes.io/part-of: recommendation-system
    """)

    # ConfigMaps
    write_file("configmaps/app-config.yaml", """
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
    """)

    write_file("configmaps/prometheus-config.yaml", """
        apiVersion: v1
        kind: ConfigMap
        metadata:
          name: prometheus-config
          namespace: recsys
        data:
          prometheus.yml: |
            global:
              scrape_interval: 15s
              evaluation_interval: 15s
            scrape_configs:
              - job_name: "kubernetes-pods"
                kubernetes_sd_configs:
                  - role: pod
                relabel_configs:
                  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                    action: keep
                    regex: true
                  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
                    action: replace
                    target_label: __metrics_path__
                    regex: (.+)
                  - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
                    action: replace
                    regex: ([^:]+)(?::\\d+)?;(\\d+)
                    replacement: $1:$2
                    target_label: __address__
                  - action: labelmap
                    regex: __meta_kubernetes_pod_label_(.+)
    """)

    # Secrets
    write_file("secrets/db-credentials.yaml", """
        apiVersion: v1
        kind: Secret
        metadata:
          name: db-credentials
          namespace: recsys
        type: Opaque
        data:
          POSTGRES_USER: cmVjc3lz          # recsys
          POSTGRES_PASSWORD: cmVjc3lzX3Bhc3M=  # recsys_pass
          MLFLOW_DB_URI: cG9zdGdyZXNxbDovL3JlY3N5czpyZWNzeXNfcGFzc0Bwb3N0Z3Jlczo1NDMyL3JlY3N5c19kYg==
    """)

    # --- Infrastructure Deployments ---
    infra = [
        ("kafka", 9092),
        ("postgres", 5432),
        ("redis", 6379),
        ("mlflow", 5000)
    ]
    for name, port in infra:
        write_file(f"deployments/{name}.yaml", f"""
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {name}
              namespace: recsys
              labels:
                app: {name}
            spec:
              replicas: 1
              selector:
                matchLabels:
                  app: {name}
              template:
                metadata:
                  labels:
                    app: {name}
                spec:
                  containers:
                    - name: {name}
                      image: {name}:latest
                      ports:
                        - containerPort: {port}
        """)
        write_file(f"services/{name}-svc.yaml", f"""
            apiVersion: v1
            kind: Service
            metadata:
              name: {name}
              namespace: recsys
            spec:
              type: ClusterIP
              selector:
                app: {name}
              ports:
                - port: {port}
                  targetPort: {port}
        """)

    # --- Application Deployments ---
    apps = [
        ("api-gateway", 8000, 2),
        ("user-service", 8001, 1),
        ("event-service", 8002, 2),
        ("recommendation-service", 8003, 2),
        ("model-service", 8004, 2),
        ("experimentation-service", 8005, 1),
        ("streamlit", 8501, 1)
    ]

    for name, port, replicas in apps:
        write_file(f"deployments/{name}.yaml", f"""
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {name}
              namespace: recsys
              labels:
                app: {name}
            spec:
              replicas: {replicas}
              selector:
                matchLabels:
                  app: {name}
              strategy:
                type: RollingUpdate
                rollingUpdate:
                  maxSurge: 1
                  maxUnavailable: 0
              template:
                metadata:
                  labels:
                    app: {name}
                  annotations:
                    prometheus.io/scrape: "true"
                    prometheus.io/port: "{port}"
                spec:
                  containers:
                    - name: {name}
                      image: recsys/{name}:latest
                      ports:
                        - containerPort: {port}
                      envFrom:
                        - configMapRef:
                            name: app-config
                        - secretRef:
                            name: db-credentials
                      resources:
                        requests:
                          cpu: 100m
                          memory: 256Mi
                        limits:
                          cpu: 500m
                          memory: 512Mi
                      livenessProbe:
                        httpGet:
                          path: /health
                          port: {port}
                        initialDelaySeconds: 15
                        periodSeconds: 30
                        failureThreshold: 3
                      readinessProbe:
                        httpGet:
                          path: /health
                          port: {port}
                        initialDelaySeconds: 5
                        periodSeconds: 10
        """)
        write_file(f"services/{name}-svc.yaml", f"""
            apiVersion: v1
            kind: Service
            metadata:
              name: {name}
              namespace: recsys
            spec:
              type: ClusterIP
              selector:
                app: {name}
              ports:
                - port: {port}
                  targetPort: {port}
        """)

    # --- Horizontal Pod Autoscalers ---
    for name in ["recommendation-service", "model-service"]:
        write_file(f"hpa/{name}-hpa.yaml", f"""
            apiVersion: autoscaling/v2
            kind: HorizontalPodAutoscaler
            metadata:
              name: {name}-hpa
              namespace: recsys
            spec:
              scaleTargetRef:
                apiVersion: apps/v1
                kind: Deployment
                name: {name}
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
        """)

    # --- Ingress ---
    write_file("ingress/ingress.yaml", """
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
    """)

    # --- Deployment Script ---
    write_file("deploy.sh", """
        #!/bin/bash
        set -e

        echo "Deploying RecSys to Kubernetes..."

        kubectl apply -f namespace.yaml
        kubectl apply -f secrets/
        kubectl apply -f configmaps/

        echo "Deploying infrastructure..."
        kubectl apply -f deployments/postgres.yaml
        kubectl apply -f deployments/kafka.yaml
        kubectl apply -f deployments/redis.yaml
        kubectl apply -f deployments/mlflow.yaml
        
        # Wait for infra to be ready
        # kubectl wait --for=condition=ready pod -l app=postgres -n recsys --timeout=120s
        # kubectl wait --for=condition=ready pod -l app=kafka -n recsys --timeout=120s

        echo "Deploying application services..."
        kubectl apply -f deployments/
        kubectl apply -f services/

        echo "Deploying autoscalers..."
        kubectl apply -f hpa/

        echo "Deploying ingress..."
        kubectl apply -f ingress/

        echo "Verifying deployment..."
        kubectl get pods -n recsys
        kubectl get svc -n recsys

        echo "Deployment complete!"
    """)

if __name__ == "__main__":
    generate()
    print("Kubernetes manifests generated successfully!")
