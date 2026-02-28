#!/bin/bash
# SCBE Mesh Foundry — Windows-compatible deploy wrapper
# Handles the gcloud path-with-spaces issue on Git Bash
set -euo pipefail

GC='/c/Users/issda/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd'
PROJECT="issac-ai-vtfqup"
ZONE="us-central1-a"
VM="scbe-mesh-foundry"

echo ""
echo "=== SCBE Mesh Foundry Deploy ==="
echo "Project: $PROJECT | Zone: $ZONE | VM: $VM"
echo ""

# Step 1: Firewall
echo "[1/5] Creating firewall rule..."
"$GC" compute firewall-rules create allow-scbe-bridge \
    --project="$PROJECT" \
    --direction=INGRESS --priority=1000 --network=default \
    --action=ALLOW --rules=tcp:8001 \
    --source-ranges="0.0.0.0/0" \
    --target-tags=scbe-server \
    --description="SCBE governance bridge API" \
    --quiet 2>&1 || echo "  (firewall rule may already exist — OK)"

# Step 2: Create VM
echo "[2/5] Creating free-tier VM..."
"$GC" compute instances create "$VM" \
    --project="$PROJECT" \
    --zone="$ZONE" \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --tags=scbe-server \
    --quiet 2>&1 || echo "  (VM may already exist — OK)"

echo "  Waiting 45s for VM to boot..."
sleep 45

# Step 3: Get external IP
echo "[3/5] Getting VM IP..."
EXTERNAL_IP=$("$GC" compute instances describe "$VM" \
    --zone="$ZONE" --project="$PROJECT" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>&1)
echo "  External IP: $EXTERNAL_IP"

# Step 4: Build the deploy bundle
echo "[4/5] Building deploy bundle..."
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUNDLE="/tmp/scbe_deploy"
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/src/browser"
mkdir -p "$BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent"
mkdir -p "$BUNDLE/workflows/n8n"
mkdir -p "$BUNDLE/agents"

# Core files only (~200KB total)
cp "$REPO_ROOT/workflows/n8n/scbe_n8n_bridge.py" "$BUNDLE/workflows/n8n/" 2>/dev/null || true
cp "$REPO_ROOT/src/browser/polly_vision.py" "$BUNDLE/src/browser/" 2>/dev/null || true
cp "$REPO_ROOT/src/browser/hydra_hand.py" "$BUNDLE/src/browser/" 2>/dev/null || true
cp "$REPO_ROOT/src/browser/research_funnel.py" "$BUNDLE/src/browser/" 2>/dev/null || true
cp "$REPO_ROOT/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py" \
   "$BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/" 2>/dev/null || true
cp "$REPO_ROOT/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/browser_swarm.py" \
   "$BUNDLE/src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/" 2>/dev/null || true
cp "$REPO_ROOT/agents/swarm_browser.py" "$BUNDLE/agents/" 2>/dev/null || true
cp "$REPO_ROOT/agents/antivirus_membrane.py" "$BUNDLE/agents/" 2>/dev/null || true
cp "$REPO_ROOT/package.json" "$BUNDLE/" 2>/dev/null || true

# Create __init__.py files for Python packages
for d in src src/browser workflows workflows/n8n agents \
         src/symphonic_cipher src/symphonic_cipher/scbe_aethermoore \
         src/symphonic_cipher/scbe_aethermoore/concept_blocks \
         src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent; do
    touch "$BUNDLE/$d/__init__.py" 2>/dev/null || true
done

# requirements.txt
cat > "$BUNDLE/requirements.txt" << 'EOF'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
requests>=2.31.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
numpy>=1.26.0
EOF

# Setup script that runs on the VM
cat > "$BUNDLE/setup.sh" << 'SETUP'
#!/bin/bash
set -euo pipefail
echo "=== SCBE Server Setup ==="

# Install packages
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv curl 2>/dev/null || true

# Create app dir
sudo mkdir -p /opt/scbe
sudo cp -r /tmp/scbe_deploy/* /opt/scbe/
sudo chmod -R 755 /opt/scbe

# Python venv
python3 -m venv /opt/scbe/venv
/opt/scbe/venv/bin/pip install --quiet --upgrade pip
/opt/scbe/venv/bin/pip install --quiet -r /opt/scbe/requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/scbe-bridge.service > /dev/null << 'SVC'
[Unit]
Description=SCBE Mesh Foundry Bridge
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/scbe
ExecStart=/opt/scbe/venv/bin/python -m uvicorn workflows.n8n.scbe_n8n_bridge:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/scbe
[Install]
WantedBy=multi-user.target
SVC

sudo systemctl daemon-reload
sudo systemctl enable scbe-bridge
sudo systemctl start scbe-bridge

sleep 3
echo ""
echo "=== Bridge Status ==="
sudo systemctl status scbe-bridge --no-pager | head -8
echo ""
echo "=== Health Check ==="
curl -s http://127.0.0.1:8001/health 2>/dev/null || echo "(bridge starting up...)"
echo ""
echo "=== DONE ==="
SETUP
chmod +x "$BUNDLE/setup.sh"

echo "  Bundle size: $(du -sh "$BUNDLE" | cut -f1)"

# Step 5: Upload and run setup
echo "[5/5] Uploading to VM and running setup..."
"$GC" compute scp --recurse "$BUNDLE" "$VM":/tmp/scbe_deploy \
    --zone="$ZONE" --project="$PROJECT" --quiet 2>&1

echo "  Running server setup on VM..."
"$GC" compute ssh "$VM" --zone="$ZONE" --project="$PROJECT" \
    --command="bash /tmp/scbe_deploy/setup.sh" --quiet 2>&1

# Done
echo ""
echo "=========================================="
echo "  DEPLOY COMPLETE"
echo "=========================================="
echo ""
echo "  Your server: http://$EXTERNAL_IP:8001"
echo "  Health:      http://$EXTERNAL_IP:8001/health"
echo "  Governance:  http://$EXTERNAL_IP:8001/v1/governance/scan"
echo ""
echo "  SSH:    gcloud compute ssh $VM --zone=$ZONE"
echo "  Logs:   gcloud compute ssh $VM --zone=$ZONE --command='sudo journalctl -u scbe-bridge -f'"
echo "  Stop:   gcloud compute instances stop $VM --zone=$ZONE"
echo "  Start:  gcloud compute instances start $VM --zone=$ZONE"
echo ""
echo "  Cost: \$0/month (e2-micro free tier)"
echo ""

rm -rf "$BUNDLE"
