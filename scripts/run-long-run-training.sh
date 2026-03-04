#!/usr/bin/env bash
set -euo pipefail

HOURS="${1:-8}"
shift || true

python scripts/long_run_training_bootstrap.py \
  --plan training/long_run_multicloud_training_plan.json \
  --hours "$HOURS" \
  "$@"
