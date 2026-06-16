#!/usr/bin/env bash
# Build + run the GeoSeal gate sandbox in a throwaway container.
#
# Anything a test passes through the gate only ever touches this container,
# which is removed on exit (--rm). Network is disabled, all caps dropped, and
# privilege escalation blocked — so a runaway command cannot reach the host or
# the network. Pass extra args to override the default command, e.g.:
#   scripts/sandbox/run-geoseal-gate-sandbox.sh python scripts/sandbox/sandbox_exec_smoke.py
set -euo pipefail

cd "$(dirname "$0")/../.."   # repo root
IMAGE="scbe-geoseal-gate-sandbox"

echo "[sandbox] building $IMAGE ..."
docker build -f scripts/sandbox/Dockerfile.geoseal-gate -t "$IMAGE" .

echo "[sandbox] running (isolated: --rm --network none --cap-drop ALL) ..."
docker run --rm \
  --network none \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 256 \
  "$IMAGE" "$@"
