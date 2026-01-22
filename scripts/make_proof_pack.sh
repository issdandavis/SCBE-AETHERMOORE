#!/usr/bin/env bash
set -euo pipefail

# =============================
# SCBE-AETHERMOORE Proof Pack
# =============================
# Generates reproducible evidence of system functionality
# for compliance, audits, and demonstrations.

# ---- Dependency validation
# Check for required commands and exit early with clear error messages if missing
check_dependencies() {
  local missing_deps=()
  local required_commands=("git" "node" "npm" "python3" "tar")
  local optional_commands=("pytest")
  
  # Check required commands
  for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing_deps+=("$cmd")
    fi
  done
  
  # If critical dependencies are missing, fail early
  if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "ERROR: Missing required dependencies:" >&2
    for dep in "${missing_deps[@]}"; do
      echo "  - $dep" >&2
    done
    echo "" >&2
    echo "Please install the missing dependencies before running this script." >&2
    exit 1
  fi
  
  # Warn about optional dependencies
  for cmd in "${optional_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      # Check if pytest is available as Python module
      if [ "$cmd" = "pytest" ]; then
        if ! python3 -m pytest --version >/dev/null 2>&1; then
          echo "WARNING: pytest not found as command or Python module. Python tests will be skipped." >&2
        fi
      else
        echo "WARNING: Optional command '$cmd' not found. Some features may be limited." >&2
      fi
    fi
  done
}

# Validate all dependencies before proceeding
check_dependencies

STAMP="$(date +"%Y-%m-%d_%H%M%S")"
OUTDIR="docs/evidence/${STAMP}"
mkdir -p "${OUTDIR}"

WARN="${OUTDIR}/warnings.txt"
touch "${WARN}"

log() { echo "[$(date +"%H:%M:%S")] $*"; }
w()   { echo "WARNING: $*" | tee -a "${WARN}" >&2; }

# ---- Basic repo/system fingerprints
log "Writing system + repo info..."
{
  echo "=== PROOF PACK ==="
  echo "timestamp_local=${STAMP}"
  echo
  echo "=== OS ==="
  (uname -a) 2>/dev/null || true
  echo
  echo "=== USER / PWD ==="
  (whoami) 2>/dev/null || true
  (pwd) 2>/dev/null || true
  echo
  echo "=== GIT ==="
  if command -v git >/dev/null 2>&1; then
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 && {
      echo "commit=$(git rev-parse HEAD 2>/dev/null || true)"
      echo "branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
      echo "status:"
      git status --porcelain 2>/dev/null || true
    }
  else
    echo "git_not_found"
  fi
  echo
  echo "=== NODE ==="
  (node -v) 2>/dev/null || echo "node_not_found"
  (npm -v) 2>/dev/null || echo "npm_not_found"
  echo
  echo "=== PYTHON ==="
  (python3 -V) 2>/dev/null || echo "python3_not_found"
  (pip3 -V) 2>/dev/null || echo "pip3_not_found"
} > "${OUTDIR}/system_info.txt"

# ---- Dependency snapshots (helpful for reproducibility)
log "Capturing dependency snapshots (best effort)..."
{
  echo "=== npm ls --depth=0 ==="
  if command -v npm >/dev/null 2>&1; then
    npm ls --depth=0 2>&1 || true
  else
    echo "npm_not_found"
  fi
} > "${OUTDIR}/npm_deps.txt"

{
  echo "=== pip freeze ==="
  if command -v pip3 >/dev/null 2>&1; then
    pip3 freeze 2>&1 || true
  else
    echo "pip3_not_found"
  fi
} > "${OUTDIR}/pip_freeze.txt"

# ---- Run TypeScript/Node tests
if [ -f "package.json" ]; then
  log "Running npm test..."
  START="$(date +%s)"
  set +e
  npm test > "${OUTDIR}/npm_test_output.txt" 2>&1
  RC=$?
  set -e
  END="$(date +%s)"
  echo "exit_code=${RC}" > "${OUTDIR}/npm_test_exit_code.txt"
  echo "duration_seconds=$((END-START))" > "${OUTDIR}/npm_test_duration.txt"
  if [ "${RC}" -ne 0 ]; then
    w "npm test failed (exit code ${RC}). See ${OUTDIR}/npm_test_output.txt"
  fi
else
  w "package.json not found; skipping npm test"
fi

# ---- Run Python tests (pytest)
if command -v pytest >/dev/null 2>&1 || [ -d "tests" ]; then
  log "Running pytest..."
  START="$(date +%s)"
  set +e
  if command -v pytest >/dev/null 2>&1; then
    pytest -q > "${OUTDIR}/pytest_output.txt" 2>&1
    RC=$?
  else
    python3 -m pytest -q > "${OUTDIR}/pytest_output.txt" 2>&1
    RC=$?
  fi
  set -e
  END="$(date +%s)"
  echo "exit_code=${RC}" > "${OUTDIR}/pytest_exit_code.txt"
  echo "duration_seconds=$((END-START))" > "${OUTDIR}/pytest_duration.txt"
  if [ "${RC}" -ne 0 ]; then
    w "pytest failed (exit code ${RC}). See ${OUTDIR}/pytest_output.txt"
  fi
else
  w "pytest not found and no tests/ directory; skipping pytest"
fi

# ---- Run the memory shard demo (find the demo script)
DEMO=""
if [ -f "demo_memory_shard.py" ]; then
  DEMO="demo_memory_shard.py"
elif [ -f "aws-lambda-simple-web-app/demo_memory_shard.py" ]; then
  DEMO="aws-lambda-simple-web-app/demo_memory_shard.py"
fi

if [ -n "${DEMO}" ]; then
  log "Running demo: ${DEMO}"
  set +e
  python3 "${DEMO}" > "${OUTDIR}/demo_memory_shard_output.txt" 2>&1
  RC=$?
  set -e
  echo "exit_code=${RC}" > "${OUTDIR}/demo_memory_shard_exit_code.txt"
  if [ "${RC}" -ne 0 ]; then
    w "demo_memory_shard.py failed (exit code ${RC}). See ${OUTDIR}/demo_memory_shard_output.txt"
  fi
else
  w "demo_memory_shard.py not found (looked in repo root and aws-lambda-simple-web-app/)."
fi

# ---- Optional: zip it for sharing
log "Creating tar.gz archive..."
tar -czf "${OUTDIR}.tar.gz" -C "docs/evidence" "${STAMP}" 2>/dev/null || w "tar failed; you can zip manually"

log "DONE."
log "Proof pack folder: ${OUTDIR}"
log "Archive (if created): ${OUTDIR}.tar.gz"
if [ -s "${WARN}" ]; then
  log "Warnings recorded in: ${WARN}"
fi
