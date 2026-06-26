#!/bin/sh
# One-command SCBE verification setup for any cloud shell with python+node (Codespaces / Cloud Shell / PWD).
#   curl -fsSL https://raw.githubusercontent.com/issdandavis/SCBE-AETHERMOORE/main/cloud/bootstrap.sh | sh
set -e
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python

echo "[1/3] clone SCBE (public)"
if [ -d scbe ]; then (cd scbe && git pull --ff-only || true); else
  git clone --depth 1 https://github.com/issdandavis/SCBE-AETHERMOORE.git scbe; fi
cd scbe

echo "[2/3] install python deps"
$PY -m pip install --quiet --user numpy requests pytest 2>/dev/null \
  || $PY -m pip install --quiet numpy requests pytest

echo "[3/3] run the verification vessels"
node --version
$PY -m pytest tests/crypto -q || true
echo "READY -- scbe verification env at $(pwd) (cloud VM, no host disk)."
