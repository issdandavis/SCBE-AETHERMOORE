#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
proof_root="${repo_root}/formal/lean"
receipt_dir="${HOME}/.cache/scbe-lean-proof"
receipt_path="${receipt_dir}/validation-$(date -u +%Y%m%dT%H%M%SZ).json"

cd "${proof_root}"
lake update
lake exe cache get \
  Mathlib.Data.Real.Sqrt \
  Mathlib.Algebra.BigOperators.Group.Finset.Basic \
  Mathlib.Tactic.Linarith \
  Mathlib.Tactic.Positivity \
  Mathlib.Tactic.Ring \
  Mathlib.Data.List.Basic \
  Mathlib.Logic.Equiv.List \
  Mathlib.Analysis.SpecialFunctions.Pow.Real

mkdir -p "${receipt_dir}"
python -X utf8 verify.py --output "${receipt_path}"

printf 'SCBE Lean proof lab is ready.\nReceipt: %s\n' "${receipt_path}"
