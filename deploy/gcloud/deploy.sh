#!/bin/bash
# Deploy SCBE-AETHERMOORE to Google Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="${2:-us-central1}"
SERVICE_NAME="scbe-aethermoore"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "============================================"
echo "SCBE-AETHERMOORE Google Cloud Deployment"
echo "============================================"
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project="${PROJECT_ID}"

# Create API key secret if it doesn't exist
if ! gcloud secrets describe scbe-api-key --project="${PROJECT_ID}" &>/dev/null; then
    echo "Creating API key secret..."
    echo -n "$(openssl rand -hex 32)" | gcloud secrets create scbe-api-key \
        --data-file=- \
        --project="${PROJECT_ID}"
fi

# Build and push image
echo ""
echo "Building Docker image..."
gcloud builds submit \
    --tag "${IMAGE_NAME}:latest" \
    --project="${PROJECT_ID}" \
    .

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "SCBE_ENV=production,SCBE_LOG_LEVEL=INFO" \
    --set-secrets "SCBE_API_KEY=scbe-api-key:latest" \
    --project="${PROJECT_ID}"

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "============================================"
echo "Deployment Complete!"
echo "============================================"
echo ""
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test endpoints:"
echo "  Health:    curl ${SERVICE_URL}/v1/health"
echo "  Demo:      curl ${SERVICE_URL}/v1/demo/rogue-detection"
echo "  Authorize: curl -X POST ${SERVICE_URL}/v1/authorize -H 'Content-Type: application/json' -d '{\"action\":\"read\",\"resource\":\"data\"}'"
echo ""
