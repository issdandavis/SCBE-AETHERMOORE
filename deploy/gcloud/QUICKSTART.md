# SCBE Mesh Foundry — Google Cloud Free Tier Quickstart

## One-Command Deploy

From your terminal (Git Bash), inside the SCBE-AETHERMOORE directory:

```bash
bash deploy/gcloud/deploy_free_vm.sh
```

This creates a free VM, installs everything, and starts the bridge.

## What You Get (for $0/month)

- **e2-micro VM**: 2 shared vCPU, 1GB RAM, 30GB disk (always-free)
- **SCBE Bridge API**: Running 24/7 on port 8001
- **Watchdog**: Checks health every 5 minutes, sends Telegram alerts
- **Auto-restart**: systemd restarts the bridge if it crashes

## Daily Commands (run from your PC terminal)

```bash
# Check if your server is running
curl http://YOUR_IP:8001/health

# SSH into your server
gcloud compute ssh scbe-mesh-foundry --zone=us-central1-a

# View live logs
gcloud compute ssh scbe-mesh-foundry --zone=us-central1-a \
  --command='sudo journalctl -u scbe-bridge -f'

# Restart the bridge
gcloud compute ssh scbe-mesh-foundry --zone=us-central1-a \
  --command='sudo systemctl restart scbe-bridge'

# Stop the VM (if you need to save resources)
gcloud compute instances stop scbe-mesh-foundry --zone=us-central1-a

# Start it back up
gcloud compute instances start scbe-mesh-foundry --zone=us-central1-a
```

## Set Up Telegram Alerts

1. Create a Telegram bot: message @BotFather, send /newbot, save the token
2. Get your chat ID: message @userinfobot
3. SSH in and configure:

```bash
gcloud compute ssh scbe-mesh-foundry --zone=us-central1-a

# Then on the server:
sudo systemctl edit scbe-watchdog
# Add these lines:
# [Service]
# Environment=SCBE_TELEGRAM_BOT_TOKEN=your_bot_token_here
# Environment=SCBE_TELEGRAM_CHAT_ID=your_chat_id_here

sudo systemctl restart scbe-watchdog.timer
```

## Set Billing Alerts (DO THIS FIRST)

Go to: https://console.cloud.google.com/billing

Create budget alerts at:
- $5 (warning)
- $10 (warning)
- $25 (hard stop — you should never hit this on free tier)

## What's Free vs Paid

| Resource | Free Tier | Your Usage |
|----------|-----------|------------|
| e2-micro VM | 1 instance 24/7 | 1 instance |
| Standard disk | 30 GB | 30 GB |
| Outbound data | 1 GB/month | ~200 MB |
| Cloud Storage | 5 GB | Not used yet |

As long as you stick to ONE e2-micro in us-central1, you pay nothing.

## Upgrade Path (When You Get Clients)

```bash
# Upgrade to e2-small (2GB RAM) — $6.11/month
gcloud compute instances set-machine-type scbe-mesh-foundry \
  --machine-type=e2-small --zone=us-central1-a

# Upgrade to e2-medium (4GB RAM) — $24.46/month
gcloud compute instances set-machine-type scbe-mesh-foundry \
  --machine-type=e2-medium --zone=us-central1-a
```

You need to stop the VM first, change type, then start it again.
