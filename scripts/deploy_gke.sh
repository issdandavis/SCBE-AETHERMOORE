#!/usr/bin/env bash
# SCBE-AETHERMOORE GKE Deploy Script
# Usage: ./scripts/deploy_gke.sh [image-tag]
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - kubectl configured for target cluster
#   - Docker running
set -euo pipefail

PROJECT_ID="gen-lang-client-0103521392"
GKE_CLUSTER="scbe-aethermoore-cluster"
GKE_ZONE="us-central1"
IMAGE="gcr.io/${PROJECT_ID}/scbe-aethermoore"
NAMESPACE="scbe-aethermoore"
TAG="${1:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

echo "=========================================="
echo "  SCBE-AETHERMOORE GKE Deploy"
echo "  Image: ${IMAGE}:${TAG}"
echo "=========================================="

# 1. Configure docker for GCR
echo "[1/6] Configuring Docker for GCR..."
gcloud auth configure-docker --quiet

# 2. Build
echo "[2/6] Building Docker image..."
docker build -f Dockerfile.api -t "${IMAGE}:${TAG}" -t "${IMAGE}:latest" .

# 3. Push
echo "[3/6] Pushing to GCR..."
docker push "${IMAGE}:${TAG}"
docker push "${IMAGE}:latest"

# 4. Get cluster credentials
echo "[4/6] Getting GKE credentials..."
gcloud container clusters get-credentials "${GKE_CLUSTER}" --zone "${GKE_ZONE}" --project "${PROJECT_ID}"

# 5. Apply manifests
echo "[5/6] Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml

# Create secrets if they don't exist
if ! kubectl get secret scbe-secrets -n "${NAMESPACE}" &>/dev/null; then
    echo "  Creating scbe-secrets (set SCBE_API_KEY and HF_TOKEN env vars)..."
    kubectl create secret generic scbe-secrets \
        -n "${NAMESPACE}" \
        --from-literal=api-key="${SCBE_API_KEY:-changeme}" \
        --from-literal=hf-token="${HF_TOKEN:-}"
fi

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Update image tag
kubectl set image deployment/scbe-aethermoore \
    scbe-api="${IMAGE}:${TAG}" \
    -n "${NAMESPACE}"

# 6. Wait for rollout
echo "[6/6] Waiting for rollout..."
kubectl rollout status deployment/scbe-aethermoore -n "${NAMESPACE}" --timeout=300s

echo ""
echo "=========================================="
echo "  Deploy complete!"
echo "=========================================="
echo ""
kubectl get pods -n "${NAMESPACE}"
echo ""

# Show external IP
EXTERNAL_IP=$(kubectl get svc scbe-aethermoore-service -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
echo "External IP: ${EXTERNAL_IP}"
if [ "${EXTERNAL_IP}" != "pending" ] && [ -n "${EXTERNAL_IP}" ]; then
    echo "Health: http://${EXTERNAL_IP}/v1/health"
    echo "Docs:   http://${EXTERNAL_IP}/docs"
    echo "Mesh:   http://${EXTERNAL_IP}/mesh/stats"
fi
