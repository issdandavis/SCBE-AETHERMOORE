#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Hydra Armor API — Deploy to Google Cloud Run (free tier)
# ═══════════════════════════════════════════════════════════════
#
# Deploys the Hydra Armor Governance-as-a-Service API as a
# standalone Cloud Run service. No browser, no Playwright —
# just the governance endpoints.
#
# Usage:
#   bash deploy/gcloud/deploy_hydra_armor.sh [PROJECT_ID] [REGION]
#
# Endpoints after deploy:
#   POST /v1/armor/verify       — Action-level governance check
#   POST /v1/hydra-armor        — Multi-head consensus on browser snapshot
#   GET  /v1/armor/health       — API health check
#   GET  /v1/armor/usage/{id}   — Usage stats per agent
#   GET  /health                — Runtime health
#
# Cost: $0/month within Cloud Run free tier (2M requests/month)
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${2:-us-central1}"
SERVICE_NAME="hydra-armor-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Hydra Armor API — Cloud Run Deploy          ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Project: ${PROJECT_ID}"
echo "║  Region:  ${REGION}"
echo "║  Service: ${SERVICE_NAME}"
echo "║  Cost:    \$0/month (free tier)"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Enable APIs
echo "[1/4] Enabling APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  --project="${PROJECT_ID}" --quiet

# Build
echo "[2/4] Building image..."
gcloud builds submit \
  --tag "${IMAGE_NAME}:latest" \
  --project="${PROJECT_ID}" \
  --file deploy/gcloud/Dockerfile.hydra-armor \
  .

# Deploy
echo "[3/4] Deploying service..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:latest" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --set-env-vars "SCBE_ENV=production" \
  --project="${PROJECT_ID}"

# Get URL
SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(status.url)')"

echo ""
echo "[4/4] Deploy complete!"
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  HYDRA ARMOR API LIVE                                ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Base URL: ${SERVICE_URL}"
echo "║                                                      ║"
echo "║  Endpoints:                                          ║"
echo "║    POST ${SERVICE_URL}/v1/armor/verify"
echo "║    POST ${SERVICE_URL}/v1/hydra-armor"
echo "║    GET  ${SERVICE_URL}/v1/armor/health"
echo "║    GET  ${SERVICE_URL}/health"
echo "║                                                      ║"
echo "║  Test it:                                            ║"
echo "║    curl ${SERVICE_URL}/v1/armor/health"
echo "║                                                      ║"
echo "║  Example verify call:                                ║"
echo "║    curl -X POST ${SERVICE_URL}/v1/armor/verify \\"
echo "║      -H 'Content-Type: application/json' \\"
echo "║      -d '{\"agent_id\":\"test\",\"action\":\"click\","
echo "║           \"selector\":\"#submit\",\"context\":\"test\"}'"
echo "╚══════════════════════════════════════════════════════╝"
