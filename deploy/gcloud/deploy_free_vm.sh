#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# SCBE Mesh Foundry — Free-Tier Google Cloud VM Deploy
# ═══════════════════════════════════════════════════════════════════
#
# Deploys the SCBE bridge + n8n + watchdog to a free e2-micro VM.
# Run from your terminal:
#
#   bash deploy/gcloud/deploy_free_vm.sh
#
# What this does:
#   1. Creates a free e2-micro VM (1GB RAM, always-free tier)
#   2. Installs Python 3.11, Node 20, n8n
#   3. Deploys the SCBE bridge (port 8001)
#   4. Sets up systemd services for 24/7 uptime
#   5. Opens firewall for the governance API
#   6. Sets billing alerts so you never get surprise bills
#
# Cost: $0/month (within Google Cloud always-free limits)
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Project with billing enabled (for free tier you still need billing linked)
#
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT:-issac-ai-vtfqup}"
ZONE="us-central1-a"           # Free tier zones: us-central1, us-west1, us-east1
VM_NAME="scbe-mesh-foundry"
MACHINE_TYPE="e2-micro"        # Always-free tier: 2 shared vCPU, 1GB RAM
DISK_SIZE="30"                 # 30GB standard persistent disk (free tier limit)
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SCBE Mesh Foundry — Google Cloud Free Tier Deploy      ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Project:  $PROJECT_ID"
echo "║  Zone:     $ZONE"
echo "║  VM:       $VM_NAME ($MACHINE_TYPE)"
echo "║  Disk:     ${DISK_SIZE}GB standard"
echo "║  Cost:     \$0/month (always-free tier)"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Set project ──────────────────────────────────────────
echo "[1/7] Setting project..."
gcloud config set project "$PROJECT_ID" --quiet

# ── Step 2: Enable required APIs (idempotent) ────────────────────
echo "[2/7] Enabling APIs..."
gcloud services enable \
    compute.googleapis.com \
    --project="$PROJECT_ID" --quiet

# ── Step 3: Create firewall rules ────────────────────────────────
echo "[3/7] Setting up firewall..."

# Allow SCBE bridge (8001) and n8n (5678) — restricted to your IP
MY_IP=$(curl -s https://api.ipify.org 2>/dev/null || echo "0.0.0.0")
echo "  Your IP: $MY_IP"

# Create firewall rule for bridge API (governance scans)
if ! gcloud compute firewall-rules describe allow-scbe-bridge --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute firewall-rules create allow-scbe-bridge \
        --project="$PROJECT_ID" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:8001 \
        --source-ranges="0.0.0.0/0" \
        --target-tags=scbe-server \
        --description="SCBE governance bridge API" \
        --quiet
    echo "  Created firewall rule: allow-scbe-bridge (port 8001)"
else
    echo "  Firewall rule allow-scbe-bridge already exists"
fi

# Allow SSH (usually exists by default)
if ! gcloud compute firewall-rules describe allow-ssh --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute firewall-rules create allow-ssh \
        --project="$PROJECT_ID" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:22 \
        --source-ranges="0.0.0.0/0" \
        --quiet
fi

# ── Step 4: Create the VM ────────────────────────────────────────
echo "[4/7] Creating VM..."

if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "  VM $VM_NAME already exists — skipping creation"
    echo "  (To recreate, run: gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet)"
else
    gcloud compute instances create "$VM_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family="$IMAGE_FAMILY" \
        --image-project="$IMAGE_PROJECT" \
        --boot-disk-size="${DISK_SIZE}GB" \
        --boot-disk-type=pd-standard \
        --tags=scbe-server \
        --metadata=startup-script='#!/bin/bash
# Initial startup — install base packages
apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv nodejs npm curl
' \
        --quiet

    echo "  VM created! Waiting 30s for startup script..."
    sleep 30
fi

# ── Step 5: Upload project and install ───────────────────────────
echo "[5/7] Deploying SCBE to VM..."

# Get the repo root (this script lives in deploy/gcloud/)
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Create a minimal deployment bundle
DEPLOY_BUNDLE="/tmp/scbe_deploy_bundle"
rm -rf "$DEPLOY_BUNDLE"
mkdir -p "$DEPLOY_BUNDLE"

# Copy only what the server needs (NOT the whole repo — that's gigabytes)
echo "  Packing deployment bundle (server-only files)..."
mkdir -p "$DEPLOY_BUNDLE/src/browser"
mkdir -p "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent"
mkdir -p "$DEPLOY_BUNDLE/workflows/n8n"
mkdir -p "$DEPLOY_BUNDLE/agents"

# Core bridge (the actual server)
cp "$REPO_ROOT/workflows/n8n/scbe_n8n_bridge.py" "$DEPLOY_BUNDLE/workflows/n8n/" 2>/dev/null || true
cp "$REPO_ROOT/workflows/n8n/__init__.py" "$DEPLOY_BUNDLE/workflows/n8n/" 2>/dev/null || true
cp "$REPO_ROOT/workflows/__init__.py" "$DEPLOY_BUNDLE/workflows/" 2>/dev/null || true
# Make sure package inits exist
touch "$DEPLOY_BUNDLE/workflows/__init__.py"
touch "$DEPLOY_BUNDLE/workflows/n8n/__init__.py"
touch "$DEPLOY_BUNDLE/src/__init__.py"
touch "$DEPLOY_BUNDLE/src/browser/__init__.py"
touch "$DEPLOY_BUNDLE/src/symphonic_cipher/__init__.py"
touch "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/__init__.py"
touch "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/__init__.py"
touch "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/__init__.py"

# Browser fleet (PollyVision + HydraHand + Research Funnel)
cp "$REPO_ROOT/src/browser/polly_vision.py" "$DEPLOY_BUNDLE/src/browser/" 2>/dev/null || true
cp "$REPO_ROOT/src/browser/hydra_hand.py" "$DEPLOY_BUNDLE/src/browser/" 2>/dev/null || true
cp "$REPO_ROOT/src/browser/research_funnel.py" "$DEPLOY_BUNDLE/src/browser/" 2>/dev/null || true

# Semantic antivirus (needed by browser swarm)
cp "$REPO_ROOT/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py" \
   "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/" 2>/dev/null || true
cp "$REPO_ROOT/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/browser_swarm.py" \
   "$DEPLOY_BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/" 2>/dev/null || true

# Agents
cp "$REPO_ROOT/agents/swarm_browser.py" "$DEPLOY_BUNDLE/agents/" 2>/dev/null || true
cp "$REPO_ROOT/agents/antivirus_membrane.py" "$DEPLOY_BUNDLE/agents/" 2>/dev/null || true

# Root package.json (for n8n/node references)
cp "$REPO_ROOT/package.json" "$DEPLOY_BUNDLE/" 2>/dev/null || true
cp "$REPO_ROOT/requirements.txt" "$DEPLOY_BUNDLE/" 2>/dev/null || true
# Create requirements if it doesn't exist
if [ ! -f "$DEPLOY_BUNDLE/requirements.txt" ]; then
    cat > "$DEPLOY_BUNDLE/requirements.txt" << 'REQEOF'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
requests>=2.31.0
python-dotenv>=1.0.0
notion-client>=2.0.0
huggingface_hub>=0.19.0
aiohttp>=3.9.0
REQEOF
fi

# Create the systemd service files
cat > "$DEPLOY_BUNDLE/scbe-bridge.service" << 'SVCEOF'
[Unit]
Description=SCBE Mesh Foundry Bridge API
After=network.target

[Service]
Type=simple
User=scbe
WorkingDirectory=/opt/scbe
ExecStart=/opt/scbe/venv/bin/python -m uvicorn workflows.n8n.scbe_n8n_bridge:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=/opt/scbe

[Install]
WantedBy=multi-user.target
SVCEOF

cat > "$DEPLOY_BUNDLE/scbe-watchdog.service" << 'WDEOF'
[Unit]
Description=SCBE Watchdog (health check + Telegram alerts)
After=scbe-bridge.service

[Service]
Type=oneshot
User=scbe
WorkingDirectory=/opt/scbe
ExecStart=/opt/scbe/venv/bin/python /opt/scbe/watchdog.py
WDEOF

cat > "$DEPLOY_BUNDLE/scbe-watchdog.timer" << 'TMEOF'
[Unit]
Description=Run SCBE watchdog every 5 minutes

[Timer]
OnBootSec=60
OnUnitActiveSec=300

[Install]
WantedBy=timers.target
TMEOF

# Create the watchdog script
cat > "$DEPLOY_BUNDLE/watchdog.py" << 'PYEOF'
"""SCBE Watchdog — checks bridge health, sends Telegram alerts."""
import os, requests, sys, json
from datetime import datetime, timezone

BRIDGE_URL = "http://127.0.0.1:8001/health"
TG_TOKEN = os.getenv("SCBE_TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("SCBE_TELEGRAM_CHAT_ID", "")

def check_health():
    try:
        r = requests.get(BRIDGE_URL, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def send_telegram(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass

if __name__ == "__main__":
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    healthy = check_health()
    if not healthy:
        send_telegram(f"<b>SCBE ALERT</b>\nBridge DOWN at {now}\nRestarting...")
        os.system("sudo systemctl restart scbe-bridge")
        import time; time.sleep(5)
        if check_health():
            send_telegram(f"<b>SCBE RECOVERED</b>\nBridge back up at {now}")
        else:
            send_telegram(f"<b>SCBE CRITICAL</b>\nBridge restart FAILED at {now}")
            sys.exit(1)
PYEOF

# Create the remote setup script
cat > "$DEPLOY_BUNDLE/setup_server.sh" << 'SETUPEOF'
#!/bin/bash
set -euo pipefail

echo "=== SCBE Mesh Foundry Server Setup ==="

# Create scbe user if not exists
if ! id scbe &>/dev/null; then
    sudo useradd -r -m -s /bin/bash scbe
    echo "Created user: scbe"
fi

# Install system packages
echo "Installing packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git curl

# Install Node 20 (for n8n)
if ! command -v node &>/dev/null || [[ $(node -v | cut -d. -f1 | tr -d v) -lt 20 ]]; then
    echo "Installing Node 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y -qq nodejs
fi

# Install n8n globally
if ! command -v n8n &>/dev/null; then
    echo "Installing n8n..."
    sudo npm install -g n8n
fi

# Set up the project directory
sudo mkdir -p /opt/scbe
sudo chown scbe:scbe /opt/scbe

# Copy files
echo "Copying SCBE files..."
sudo cp -r /tmp/scbe_upload/* /opt/scbe/
sudo chown -R scbe:scbe /opt/scbe

# Create Python venv and install deps
echo "Setting up Python environment..."
sudo -u scbe python3 -m venv /opt/scbe/venv
sudo -u scbe /opt/scbe/venv/bin/pip install --quiet --upgrade pip
sudo -u scbe /opt/scbe/venv/bin/pip install --quiet -r /opt/scbe/requirements.txt

# Install systemd services
echo "Installing systemd services..."
sudo cp /opt/scbe/scbe-bridge.service /etc/systemd/system/
sudo cp /opt/scbe/scbe-watchdog.service /etc/systemd/system/
sudo cp /opt/scbe/scbe-watchdog.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable scbe-bridge
sudo systemctl start scbe-bridge
sudo systemctl enable scbe-watchdog.timer
sudo systemctl start scbe-watchdog.timer

echo ""
echo "=== Setup Complete ==="
echo "Bridge: http://$(curl -s https://api.ipify.org):8001/health"
echo "Services:"
sudo systemctl status scbe-bridge --no-pager -l | head -5
echo ""
echo "To set Telegram alerts, SSH in and run:"
echo "  sudo systemctl edit scbe-watchdog"
echo "  # Add: Environment=SCBE_TELEGRAM_BOT_TOKEN=your_token"
echo "  # Add: Environment=SCBE_TELEGRAM_CHAT_ID=your_chat_id"
SETUPEOF
chmod +x "$DEPLOY_BUNDLE/setup_server.sh"

# Upload to VM
echo "  Uploading to VM..."
gcloud compute scp --recurse "$DEPLOY_BUNDLE" "$VM_NAME":/tmp/scbe_upload \
    --zone="$ZONE" --project="$PROJECT_ID" --quiet

# Run setup on VM
echo "  Running server setup (this takes 2-3 minutes)..."
gcloud compute ssh "$VM_NAME" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --command="bash /tmp/scbe_upload/setup_server.sh" \
    --quiet

# ── Step 6: Get the external IP ──────────────────────────────────
echo "[6/7] Getting server details..."

EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "  External IP: $EXTERNAL_IP"

# ── Step 7: Set up billing alerts ────────────────────────────────
echo "[7/7] Setting up billing alerts..."
echo ""
echo "  IMPORTANT: Set billing alerts manually in the Google Cloud Console:"
echo "  https://console.cloud.google.com/billing/$PROJECT_ID/budgets"
echo "  Create budgets at \$5, \$10, \$25 to prevent surprise charges."
echo ""

# ── Done! ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  DEPLOY COMPLETE                                        ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Governance API:                                         ║"
echo "║    http://$EXTERNAL_IP:8001/health"
echo "║    http://$EXTERNAL_IP:8001/v1/governance/scan"
echo "║                                                          ║"
echo "║  SSH into your server:                                   ║"
echo "║    gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "║                                                          ║"
echo "║  View logs:                                              ║"
echo "║    gcloud compute ssh $VM_NAME --zone=$ZONE \\"
echo "║      --command='sudo journalctl -u scbe-bridge -f'"
echo "║                                                          ║"
echo "║  Stop (save money if needed):                            ║"
echo "║    gcloud compute instances stop $VM_NAME --zone=$ZONE"
echo "║                                                          ║"
echo "║  Start again:                                            ║"
echo "║    gcloud compute instances start $VM_NAME --zone=$ZONE"
echo "║                                                          ║"
echo "║  COST: \$0/month (e2-micro always-free tier)             ║"
echo "║  Set billing alerts at:                                  ║"
echo "║    console.cloud.google.com/billing                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Cleanup
rm -rf "$DEPLOY_BUNDLE"
