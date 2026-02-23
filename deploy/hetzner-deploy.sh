#!/usr/bin/env bash
# =============================================================================
# SCBE-AETHERMOORE — Hetzner VPS Deployment Script
# =============================================================================
#
# Prerequisites:
#   - Hetzner CX22 (2 vCPU, 4GB RAM, ~$4.55/mo) with Ubuntu 22.04
#   - Domain pointed to the VPS IP via Cloudflare DNS
#   - SSH access configured
#
# Usage:
#   ssh root@YOUR_VPS_IP < deploy/hetzner-deploy.sh
#
# Or run locally on the VPS:
#   bash deploy/hetzner-deploy.sh
#
# Part of SCBE-AETHERMOORE (USPTO #63/961,403)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
#  Configuration (override with env vars)
# ---------------------------------------------------------------------------

DOMAIN="${SCBE_DOMAIN:-api.scbe-aethermoore.com}"
EMAIL="${SCBE_EMAIL:-admin@scbe-aethermoore.com}"
APP_DIR="/opt/scbe-api"
REPO_URL="https://github.com/issdandavis/SCBE-AETHERMOORE.git"

echo "============================================================"
echo "SCBE-AETHERMOORE Deployment"
echo "  Domain: ${DOMAIN}"
echo "  Email:  ${EMAIL}"
echo "============================================================"

# ---------------------------------------------------------------------------
#  1. System Setup
# ---------------------------------------------------------------------------

echo "[1/6] Updating system..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq docker.io docker-compose-plugin curl git ufw

# Enable Docker
systemctl enable docker
systemctl start docker

# ---------------------------------------------------------------------------
#  2. Firewall
# ---------------------------------------------------------------------------

echo "[2/6] Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ---------------------------------------------------------------------------
#  3. Clone/Update Repo
# ---------------------------------------------------------------------------

echo "[3/6] Setting up application..."
if [ -d "${APP_DIR}" ]; then
    cd "${APP_DIR}"
    git pull origin main
else
    git clone "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
fi

# ---------------------------------------------------------------------------
#  4. Environment File
# ---------------------------------------------------------------------------

echo "[4/6] Checking environment..."
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "ERROR: .env file not found at ${APP_DIR}/.env"
    echo "Create it from the template: cp deploy/.env.template ${APP_DIR}/.env"
    echo "Then edit with your actual API keys."
    exit 1
fi

# ---------------------------------------------------------------------------
#  5. Build & Deploy
# ---------------------------------------------------------------------------

echo "[5/6] Building and deploying..."
docker compose -f docker-compose.api.yml up -d --build

# Wait for health check
echo "Waiting for API to start..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/v1/health > /dev/null 2>&1; then
        echo "  API is healthy!"
        break
    fi
    sleep 2
done

# ---------------------------------------------------------------------------
#  6. Caddy Reverse Proxy (auto-HTTPS)
# ---------------------------------------------------------------------------

echo "[6/6] Setting up Caddy reverse proxy..."

# Install Caddy if not present
if ! command -v caddy &> /dev/null; then
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq caddy
fi

# Configure Caddy
cat > /etc/caddy/Caddyfile << EOF
${DOMAIN} {
    reverse_proxy localhost:8080

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }

    log {
        output file /var/log/caddy/scbe-api.log
    }
}
EOF

mkdir -p /var/log/caddy
systemctl enable caddy
systemctl restart caddy

# ---------------------------------------------------------------------------
#  Done
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "Deployment complete!"
echo ""
echo "  API:     https://${DOMAIN}/v1/health"
echo "  Logs:    docker compose -f docker-compose.api.yml logs -f"
echo "  Restart: docker compose -f docker-compose.api.yml restart"
echo "  Status:  docker compose -f docker-compose.api.yml ps"
echo ""
echo "  Caddy logs: /var/log/caddy/scbe-api.log"
echo "============================================================"
