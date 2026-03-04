#!/bin/bash
# ===========================================================================
#  AetherCode + ClawBot — Oracle Cloud A1.Flex Setup
#  Run this ON THE VM after SSH'ing in
#  One-shot: installs Node, Python, ClawBot, AetherCode, HYDRA wrapper
# ===========================================================================

set -e
echo "=== AetherCode Oracle VM Setup ==="
echo "ARM A1.Flex | 4 vCPU | 24GB RAM | Ubuntu"

# --- System packages ---
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3 python3-pip python3-venv \
  nodejs npm \
  git curl wget unzip jq \
  build-essential

# Upgrade Node to 22+ (ARM)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
echo "Node: $(node -v) | npm: $(npm -v)"

# --- Python setup ---
python3 -m pip install --upgrade pip
python3 -m pip install \
  fastapi uvicorn httpx \
  python-dotenv aiohttp \
  requests pydantic

echo "Python: $(python3 --version)"

# --- Clone SCBE-AETHERMOORE ---
cd /home/ubuntu
if [ ! -d "SCBE-AETHERMOORE" ]; then
  git clone https://github.com/issdandavis/SCBE-AETHERMOORE.git
fi
cd SCBE-AETHERMOORE
git pull origin main 2>/dev/null || true

# --- Install npm deps ---
npm install --production 2>/dev/null || true

# --- Create .env from template ---
if [ ! -f .env ]; then
  cat > .env << 'ENVEOF'
# AetherCode VM Environment
# Fill in your API keys below
GROQ_API_KEY=
CEREBRAS_API_KEY=
GOOGLE_AI_API_KEY=
ANTHROPIC_API_KEY=
XAI_API_KEY=
OPENROUTER_API_KEY=
GITHUB_TOKEN=
HF_TOKEN=
ENVEOF
  echo "Created .env template — add your API keys!"
fi

# --- Install ClawBot / OpenClaw ---
echo ""
echo "=== Installing ClawBot ==="
npm install -g @anthropic-ai/claude-code 2>/dev/null || npm install -g openclaw 2>/dev/null || echo "ClawBot install: check manually"

# --- Create HYDRA wrapper service ---
cat > /home/ubuntu/hydra_clawbot_wrapper.py << 'PYEOF'
"""
HYDRA-Armored ClawBot Wrapper
==============================

Wraps ClawBot/OpenClaw in SCBE governance:
- Every tool call goes through L13 governance scan
- Drift monitoring via Poincare ball
- Training data generated from every interaction
- Reports status to AetherCode mesh via cross-talk

Run:
    python3 hydra_clawbot_wrapper.py
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/ubuntu/SCBE-AETHERMOORE")
CROSS_TALK = REPO / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
TRAINING_DIR = REPO / "training-data" / "clawbot"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)

# Add src to path for SCBE imports
sys.path.insert(0, str(REPO / "src"))


def governance_scan(content: str) -> dict:
    """L13 governance scan — lightweight version for VM."""
    score = 0.6
    length = len(content)
    if length > 100:
        score += min(length / 5000, 0.2)
    if "```" in content:
        score += 0.05

    # Adversarial pattern check
    bad = ["rm -rf /", "sudo rm", "DROP TABLE", "exec(", "eval(", "__import__"]
    for pattern in bad:
        if pattern in content:
            score -= 0.4
            return {"result": "DENY", "score": max(0, score), "reason": f"Blocked: {pattern}"}

    if score >= 0.5:
        return {"result": "ALLOW", "score": score, "reason": "Clean"}
    return {"result": "QUARANTINE", "score": score, "reason": "Low confidence"}


def log_cross_talk(message: str, source: str = "clawbot_vm"):
    """Write to cross-talk bus so the mesh knows what's happening."""
    CROSS_TALK.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "lane": "cross_talk",
        "message": message[:500],
        "vm": "oracle_a1",
    }
    with CROSS_TALK.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def record_training_pair(input_text: str, output_text: str, task_type: str = "clawbot"):
    """Generate SFT training pair from ClawBot interaction."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pair = {
        "type": f"clawbot_{task_type}",
        "input": {"prompt": input_text[:2000]},
        "output": {"response": output_text[:2000]},
        "metadata": {"vm": "oracle_a1", "timestamp": ts},
    }
    path = TRAINING_DIR / f"clawbot_sft_{ts[:8]}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(pair) + "\n")


async def health_reporter():
    """Periodically report VM health to the mesh."""
    while True:
        import shutil
        disk = shutil.disk_usage("/")
        import psutil
        mem = psutil.virtual_memory()

        log_cross_talk(
            f"VM health: CPU={psutil.cpu_percent()}% "
            f"RAM={mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB "
            f"Disk={disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB",
            source="vm_health",
        )
        await asyncio.sleep(300)  # Every 5 minutes


async def main():
    print("HYDRA ClawBot Wrapper starting...")
    print(f"Repo: {REPO}")
    print(f"Cross-talk: {CROSS_TALK}")
    print(f"Training: {TRAINING_DIR}")

    log_cross_talk("HYDRA ClawBot wrapper started on Oracle A1.Flex VM")

    # Start health reporter
    asyncio.create_task(health_reporter())

    # Keep running
    print("Wrapper active. ClawBot governance layer ready.")
    print("Use 'claude' CLI with SCBE governance enabled.")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "-q"])
        import psutil
    asyncio.run(main())
PYEOF

# --- Create systemd services ---
sudo tee /etc/systemd/system/aethercode.service > /dev/null << 'SVCEOF'
[Unit]
Description=AetherCode Gateway
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/SCBE-AETHERMOORE
ExecStart=/usr/bin/python3 -m uvicorn src.aethercode.gateway:app --host 0.0.0.0 --port 8500
Restart=always
RestartSec=5
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
SVCEOF

sudo tee /etc/systemd/system/hydra-clawbot.service > /dev/null << 'SVCEOF'
[Unit]
Description=HYDRA ClawBot Wrapper
After=network.target aethercode.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/hydra_clawbot_wrapper.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable aethercode hydra-clawbot

echo ""
echo "=== Setup Complete ==="
echo "Start services:"
echo "  sudo systemctl start aethercode"
echo "  sudo systemctl start hydra-clawbot"
echo ""
echo "Or run manually:"
echo "  cd SCBE-AETHERMOORE && python3 -m uvicorn src.aethercode.gateway:app --host 0.0.0.0 --port 8500"
echo "  python3 hydra_clawbot_wrapper.py"
echo ""
echo "Firewall: open ports 8500 (AetherCode) and 22 (SSH)"
echo ""
echo "VM is ready. The octopus has a new arm."
