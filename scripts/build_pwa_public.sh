#!/bin/bash
# Build public/ directory for Firebase PWA hosting
# Run from repo root: bash scripts/build_pwa_public.sh

set -e
SRC="src/aethercode"
OUT="public"

echo "Building PWA public/ from $SRC..."

# Copy main app
cp "$SRC/arena.html" "$OUT/index.html"
cp "$SRC/arena.html" "$OUT/arena.html"
cp "$SRC/manifest.json" "$OUT/manifest.json"
cp "$SRC/sw.js" "$OUT/sw.js"

# Copy icons if they exist
if [ -d "$SRC/static/icons" ]; then
  mkdir -p "$OUT/static/icons"
  cp "$SRC/static/icons/"* "$OUT/static/icons/"
fi

echo "Done! public/ is ready for: firebase deploy --only hosting"
