#!/usr/bin/env bash
# ============================================================
# SCBE-AETHERMOORE Bootstrap
# ============================================================
# Sets up both TypeScript and Python environments, runs a
# health check, and confirms everything is ready.
#
# Usage:
#   chmod +x bootstrap.sh && ./bootstrap.sh
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        SCBE-AETHERMOORE Bootstrap                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# ---------- Node.js ----------
echo "▸ Checking Node.js..."
if command -v node &>/dev/null; then
  NODE_VER=$(node -v)
  NODE_MAJOR=$(echo "$NODE_VER" | sed 's/v\([0-9]*\).*/\1/')
  if [ "$NODE_MAJOR" -ge 18 ]; then
    ok "Node.js $NODE_VER"
  else
    fail "Node.js $NODE_VER (need >= 18)"
    ERRORS=$((ERRORS+1))
  fi
else
  fail "Node.js not found"
  ERRORS=$((ERRORS+1))
fi

# ---------- Python ----------
echo "▸ Checking Python..."
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PY_VER=$("$cmd" --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$("$cmd" -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MAJOR" -ge 11 ]; then
      ok "Python $PY_VER ($cmd)"
      PYTHON="$cmd"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  warn "Python >= 3.11 not found (optional — TypeScript SDK still works)"
fi

# ---------- npm install ----------
echo ""
echo "▸ Installing Node.js dependencies..."
if npm install --prefer-offline 2>/dev/null; then
  ok "npm install"
else
  fail "npm install failed"
  ERRORS=$((ERRORS+1))
fi

# ---------- TypeScript build ----------
echo ""
echo "▸ Building TypeScript..."
if npm run build 2>/dev/null; then
  ok "TypeScript build"
else
  fail "TypeScript build failed"
  ERRORS=$((ERRORS+1))
fi

# ---------- Python deps (optional) ----------
if [ -n "$PYTHON" ]; then
  echo ""
  echo "▸ Installing Python dependencies..."
  if $PYTHON -m pip install -r requirements.txt -q 2>/dev/null; then
    ok "Python dependencies"
  else
    warn "Some Python deps failed (PQC libs may need system packages)"
    # Try core deps only
    $PYTHON -m pip install numpy scipy fastapi uvicorn pydantic -q 2>/dev/null && \
      ok "Core Python deps installed" || warn "Core Python deps failed"
  fi
fi

# ---------- Tests ----------
echo ""
echo "▸ Running smoke tests..."
if npx vitest run --reporter=dot 2>&1 | tail -3 | grep -q "passed"; then
  PASS_COUNT=$(npx vitest run --reporter=dot 2>&1 | grep -oP '\d+ passed' | head -1)
  ok "TypeScript tests ($PASS_COUNT)"
else
  warn "Some TypeScript tests failed (non-critical)"
fi

# ---------- Health check ----------
echo ""
echo "▸ Running SDK health check..."
HEALTH=$(node -e "
  const { SCBE } = require('./dist/src/api/index.js');
  const s = new SCBE();
  const r = s.evaluateRisk({ action: 'test', source: 'internal' });
  console.log(JSON.stringify({ decision: r.decision, score: r.score.toFixed(4) }));
" 2>/dev/null || echo "FAIL")

if echo "$HEALTH" | grep -q "decision"; then
  ok "SDK health check: $HEALTH"
else
  fail "SDK health check failed"
  ERRORS=$((ERRORS+1))
fi

# ---------- Summary ----------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ERRORS" -eq 0 ]; then
  echo -e "${GREEN}Ready!${NC} SCBE-AETHERMOORE is set up."
  echo ""
  echo "Quick start:"
  echo "  node examples/quickstart.js        # Try the SDK"
  echo "  npm test                           # Run full test suite"
  echo ""
  if [ -n "$PYTHON" ]; then
    echo "  $PYTHON -m uvicorn src.api.main:app --reload --port 8000  # Start API"
    echo ""
  fi
else
  echo -e "${RED}$ERRORS error(s) found.${NC} Check output above."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
