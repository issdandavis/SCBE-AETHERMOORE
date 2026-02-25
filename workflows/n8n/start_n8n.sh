#!/usr/bin/env bash
# =============================================================================
# Start SCBE n8n + FastAPI Bridge
# =============================================================================
# Usage:  bash workflows/n8n/start_n8n.sh
# Starts: 1) FastAPI bridge on port 8001
#         2) n8n on port 5678 with all env vars
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
  echo "[SCBE] Loading .env from $PROJECT_ROOT/.env"
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
else
  echo "[SCBE] WARNING: No .env found at $PROJECT_ROOT/.env"
fi

# n8n-specific env vars (expose project vars as n8n $env.*)
export N8N_DEFAULT_BINARY_DATA_MODE=filesystem
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false
export N8N_RUNNERS_ENABLED=false

echo "[SCBE] Starting FastAPI bridge on port 8001..."
cd "$PROJECT_ROOT"
python -m uvicorn workflows.n8n.scbe_n8n_bridge:app \
  --host 127.0.0.1 --port 8001 --log-level info &
BRIDGE_PID=$!
echo "[SCBE] Bridge PID: $BRIDGE_PID"

# Wait for bridge health
sleep 2
for i in 1 2 3 4 5; do
  if curl -sf http://127.0.0.1:8001/health > /dev/null 2>&1; then
    echo "[SCBE] Bridge is healthy"
    break
  fi
  echo "[SCBE] Waiting for bridge... ($i/5)"
  sleep 1
done

echo "[SCBE] Starting n8n on port 5678..."
n8n start &
N8N_PID=$!
echo "[SCBE] n8n PID: $N8N_PID"

# Trap cleanup
cleanup() {
  echo "[SCBE] Shutting down..."
  kill $BRIDGE_PID 2>/dev/null || true
  kill $N8N_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "=========================================="
echo "  SCBE n8n Stack Running"
echo "=========================================="
echo "  Bridge:  http://127.0.0.1:8001/health"
echo "  n8n UI:  http://127.0.0.1:5678"
echo "=========================================="
echo "  Press Ctrl+C to stop all services"
echo "=========================================="

wait
