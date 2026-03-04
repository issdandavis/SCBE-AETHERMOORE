#!/bin/bash
# Deploy SCBE AetherBrowse (browser agent API) to Google Cloud Run.
#
# Usage:
#   chmod +x deploy/gcloud/deploy_aetherbrowse.sh
#   ./deploy/gcloud/deploy_aetherbrowse.sh <PROJECT_ID> <REGION>

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="${2:-us-central1}"
SERVICE_NAME="scbe-aetherbrowse"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "============================================"
echo "SCBE AetherBrowse Cloud Run Deploy"
echo "============================================"
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"

if ! gcloud secrets describe scbe-browser-api-key --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating secret: scbe-browser-api-key"
  openssl rand -hex 32 | gcloud secrets create scbe-browser-api-key \
    --data-file=- \
    --project="${PROJECT_ID}"
fi

echo "Building image..."
gcloud builds submit \
  --tag "${IMAGE_NAME}:latest" \
  --project="${PROJECT_ID}" \
  --file deploy/gcloud/Dockerfile.aetherbrowse \
  .

echo "Deploying service..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:latest" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "SCBE_ENV=production,SCBE_LOG_LEVEL=INFO" \
  --set-secrets "SCBE_API_KEY=scbe-browser-api-key:latest,N8N_API_KEY=scbe-browser-api-key:latest" \
  --project="${PROJECT_ID}"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')"

echo ""
echo "Deployment complete."
echo "Service URL: ${SERVICE_URL}"
echo "Health URL:  ${SERVICE_URL}/health"
echo "Browse URL:  ${SERVICE_URL}/v1/integrations/n8n/browse"
echo ""
echo "Get API key:"
echo "  gcloud secrets versions access latest --secret=scbe-browser-api-key --project=${PROJECT_ID}"
