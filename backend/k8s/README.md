# Kubernetes Deployment Guide

## Prerequisites
- Docker installed
- Kubernetes cluster (minikube, GKE, EKS, AKS)
- kubectl configured

## Steps to Deploy

### 1. Build Docker Images
```bash
cd auth-user-service
docker build -t your-registry/auth-user-service:latest .

cd ../ai-call-service
docker build -t your-registry/ai-call-service:latest .

cd ../campaign-leads-service
docker build -t your-registry/campaign-leads-service:latest .

cd ../integrations-service
docker build -t your-registry/integrations-service:latest .
```

### 2. Push Images to Registry
```bash
docker push your-registry/auth-user-service:latest
docker push your-registry/ai-call-service:latest
docker push your-registry/campaign-leads-service:latest
docker push your-registry/integrations-service:latest
```

### 3. Apply Kubernetes Manifests
```bash
kubectl apply -f k8s/
```

### 4. Verify Deployment
```bash
kubectl get pods
kubectl get services
```

### 5. Access Services
```bash
# Port forward to access locally
kubectl port-forward service/auth-user-service 8001:8001
kubectl port-forward service/ai-call-service 8002:8002
kubectl port-forward service/campaign-leads-service 8003:8003
kubectl port-forward service/integrations-service 8004:8004
```

## Local Development with Docker Compose
```bash
docker-compose up --build
```

## Notes
- Replace `your-registry` with your actual Docker registry (Docker Hub, GCR, ECR)
- Update secrets and environment variables in deployment files before production
- Consider using ConfigMaps and Secrets for sensitive data
