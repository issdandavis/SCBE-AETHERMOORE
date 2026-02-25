#!/usr/bin/env bash
# Import all SCBE workflow JSON files into n8n
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[SCBE] Importing n8n workflows..."
for f in "$SCRIPT_DIR"/*.workflow.json; do
  name=$(basename "$f")
  echo "  -> $name"
  n8n import:workflow --input="$f" 2>&1 || echo "    WARN: import failed for $name"
done
echo "[SCBE] Done. Open http://127.0.0.1:5678 to activate workflows."
