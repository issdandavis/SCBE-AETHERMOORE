#!/usr/bin/env bash
# =============================================================================
# AetherNet AI Social Platform — Deploy to Cloud Run
# =============================================================================
# Usage:
#   ./deploy/aethernet/deploy.sh
#   ./deploy/aethernet/deploy.sh --skip-build   # redeploy existing image
#
# Prerequisites:
#   - gcloud CLI authenticated (gcloud auth login)
#   - Docker daemon running (for local builds) OR use Cloud Build
#   - Firebase service-account JSON stored in Secret Manager
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
PROJECT_ID="issac-ai-vtfqup"
FIREBASE_PROJECT_ID="studio-6928670609-fdd4c"
REGION="us-central1"
SERVICE_NAME="aethernet"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DOCKERFILE="deploy/aethernet/Dockerfile"

# Secret names in GCP Secret Manager
SECRET_FIREBASE="firebase-service-account-json"
SECRET_API_KEYS="scbe-api-keys"

SKIP_BUILD=false
for arg in "$@"; do
    case "$arg" in
        --skip-build) SKIP_BUILD=true ;;
    esac
done

# ---------------------------------------------------------------------------
#  Banner
# ---------------------------------------------------------------------------
echo "========================================================"
echo "  AetherNet AI Social Platform — Cloud Run Deployment"
echo "========================================================"
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "  Service:  ${SERVICE_NAME}"
echo "  Image:    ${IMAGE_NAME}:latest"
echo ""

# ---------------------------------------------------------------------------
#  Step 0: Set active project
# ---------------------------------------------------------------------------
gcloud config set project "${PROJECT_ID}" --quiet

# ---------------------------------------------------------------------------
#  Step 1: Enable required APIs
# ---------------------------------------------------------------------------
echo "[1/6] Enabling required GCP APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

# ---------------------------------------------------------------------------
#  Step 2: Ensure secrets exist in Secret Manager
# ---------------------------------------------------------------------------
echo "[2/6] Checking Secret Manager entries..."

if ! gcloud secrets describe "${SECRET_FIREBASE}" --project="${PROJECT_ID}" &>/dev/null; then
    echo ""
    echo "  WARNING: Secret '${SECRET_FIREBASE}' does not exist."
    echo "  Create it with:"
    echo ""
    echo "    gcloud secrets create ${SECRET_FIREBASE} --project=${PROJECT_ID}"
    echo "    gcloud secrets versions add ${SECRET_FIREBASE} \\"
    echo "        --data-file=secrets/firebase-service-account.json \\"
    echo "        --project=${PROJECT_ID}"
    echo ""
    echo "  Then re-run this script."
    exit 1
fi

if ! gcloud secrets describe "${SECRET_API_KEYS}" --project="${PROJECT_ID}" &>/dev/null; then
    echo ""
    echo "  Creating '${SECRET_API_KEYS}' with a random key..."
    echo -n "$(openssl rand -hex 32)" | \
        gcloud secrets create "${SECRET_API_KEYS}" \
            --data-file=- \
            --project="${PROJECT_ID}"
fi

echo "  Secrets OK."

# ---------------------------------------------------------------------------
#  Step 3: Grant Cloud Run service account access to secrets
# ---------------------------------------------------------------------------
echo "[3/6] Granting Secret Manager access to Cloud Run SA..."

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in "${SECRET_FIREBASE}" "${SECRET_API_KEYS}"; do
    gcloud secrets add-iam-policy-binding "${SECRET}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}" \
        --quiet 2>/dev/null || true
done

# ---------------------------------------------------------------------------
#  Step 4: Build & push image
# ---------------------------------------------------------------------------
if [ "${SKIP_BUILD}" = false ]; then
    echo "[4/6] Building and pushing image via Cloud Build..."

    # Ensure we run from the repo root (build context)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
    cd "${REPO_ROOT}"

    gcloud builds submit \
        --tag "${IMAGE_NAME}:latest" \
        --project="${PROJECT_ID}" \
        --timeout="900s" \
        --gcs-log-dir="gs://${PROJECT_ID}_cloudbuild/logs" \
        . \
        --ignore-file=.gcloudignore 2>/dev/null || \
    gcloud builds submit \
        --tag "${IMAGE_NAME}:latest" \
        --project="${PROJECT_ID}" \
        --timeout="900s" \
        .
else
    echo "[4/6] Skipping build (--skip-build)."
fi

# ---------------------------------------------------------------------------
#  Step 5: Deploy to Cloud Run
# ---------------------------------------------------------------------------
echo "[5/6] Deploying to Cloud Run..."

gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --port 8300 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 80 \
    --set-env-vars "\
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID},\
SCBE_ENV=production,\
PYTHONUNBUFFERED=1" \
    --set-secrets "\
FIREBASE_SERVICE_ACCOUNT_KEY=${SECRET_FIREBASE}:latest,\
SCBE_API_KEYS=${SECRET_API_KEYS}:latest" \
    --project="${PROJECT_ID}"

# ---------------------------------------------------------------------------
#  Step 6: Print service URL and test commands
# ---------------------------------------------------------------------------
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "========================================================"
echo "  Deployment Complete"
echo "========================================================"
echo ""
echo "  Service URL: ${SERVICE_URL}"
echo ""
echo "  Test endpoints:"
echo "    Health:      curl ${SERVICE_URL}/health"
echo "    Dashboard:   ${SERVICE_URL}/dashboard"
echo "    Register:    curl -X POST ${SERVICE_URL}/api/register \\"
echo "                   -H 'Content-Type: application/json' \\"
echo "                   -d '{\"agent_id\":\"test-01\",\"agent_name\":\"TestBot\"}'"
echo "    Feed:        curl ${SERVICE_URL}/api/feed"
echo "    Stats:       curl ${SERVICE_URL}/api/stats"
echo ""
