#!/usr/bin/env bash
# render-diagrams.sh — Render Mermaid diagrams to SVG for Layer 13 visual audits.
#
# Usage:
#   ./scripts/render-diagrams.sh          # Render all .mmd files in docs/
#   ./scripts/render-diagrams.sh dag.mmd  # Render a specific file
#
# Requires: @mermaid-js/mermaid-cli (npx mmdc)
#   npm install -g @mermaid-js/mermaid-cli   # or use npx

set -euo pipefail

DOCS_DIR="$(cd "$(dirname "$0")/../docs" && pwd)"
OUT_DIR="$DOCS_DIR"

render_one() {
  local input="$1"
  local base
  base="$(basename "$input" .mmd)"
  local output="$OUT_DIR/${base}.svg"

  echo "  Rendering: $input → $output"
  npx -y @mermaid-js/mermaid-cli mmdc -i "$input" -o "$output" -b transparent 2>/dev/null \
    && echo "  ✓ $base.svg" \
    || echo "  ✗ Failed: $base (is @mermaid-js/mermaid-cli installed?)"
}

if [ $# -gt 0 ]; then
  # Render specific file(s)
  for f in "$@"; do
    if [ -f "$DOCS_DIR/$f" ]; then
      render_one "$DOCS_DIR/$f"
    elif [ -f "$f" ]; then
      render_one "$f"
    else
      echo "  ✗ Not found: $f"
    fi
  done
else
  # Render all .mmd files in docs/
  echo "Rendering all Mermaid diagrams in $DOCS_DIR..."
  found=0
  for mmd in "$DOCS_DIR"/*.mmd; do
    [ -f "$mmd" ] || continue
    render_one "$mmd"
    found=$((found + 1))
  done
  if [ "$found" -eq 0 ]; then
    echo "  No .mmd files found in $DOCS_DIR"
  else
    echo "Done. Rendered $found diagram(s)."
  fi
fi
