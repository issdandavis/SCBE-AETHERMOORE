#!/bin/bash
# Setup Cloudflare Tunnel for SCBE AetherBrowser API
# This exposes your local API (port 8100) to the internet via HTTPS

set -e

TUNNEL_NAME="scbe-aetherbrowser"
CONFIG_DIR="$HOME/.cloudflared"
API_PORT="${AETHER_API_PORT:-8100}"

echo "=== SCBE Cloudflare Tunnel Setup ==="
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."
    curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
fi

# Authenticate
echo "Step 1: Authenticate with Cloudflare"
echo "This will open a browser. Choose the zone for aethermoore.com"
if [ ! -f "$CONFIG_DIR/cert.pem" ]; then
    cloudflared tunnel login
fi

# Create tunnel
echo ""
echo "Step 2: Creating tunnel: $TUNNEL_NAME"
TUNNEL_ID=$(cloudflared tunnel create "$TUNNEL_NAME" 2>/dev/null | grep -oP 'Created tunnel \K[a-z0-9-]+' || true)

if [ -z "$TUNNEL_ID" ]; then
    echo "Tunnel may already exist. Listing tunnels:"
    cloudflared tunnel list
    echo ""
    echo "Enter the tunnel ID from above:"
    read TUNNEL_ID
fi

# Write config
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/$TUNNEL_ID.json" << EOF
{
    "tunnel": "$TUNNEL_ID",
    "credentials-file": "$CONFIG_DIR/$TUNNEL_ID.json",
    "ingress": [
        {
            "hostname": "api.aethermoore.com",
            "service": "http://localhost:$API_PORT"
        },
        {
            "service": "http_status:404"
        }
    ]
}
EOF

# Create DNS record
echo ""
echo "Step 3: Creating DNS record api.aethermoore.com → tunnel"
cloudflared tunnel route dns "$TUNNEL_NAME" "api.aethermoore.com"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the tunnel:"
echo "  cloudflared tunnel run $TUNNEL_NAME"
echo ""
echo "To run as a service:"
echo "  sudo cloudflared service install"
echo "  sudo systemctl start cloudflared"
echo ""
echo "Your API will be available at: https://api.aethermoore.com"
echo ""
echo "Test the contact endpoint:"
echo "  curl -X POST https://api.aethermoore.com/api/contact \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"name\":\"Test\",\"email\":\"test@example.com\",\"subject\":\"Hello\",\"message\":\"Test message\"}'"
