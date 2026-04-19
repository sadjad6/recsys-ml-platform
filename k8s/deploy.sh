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
