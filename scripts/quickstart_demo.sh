#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SCBE_BASE_URL:-http://localhost:8000}"
API_KEY="${SCBE_API_KEY:-dev-key-local}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd python3

json_field() {
  local json_input="$1"
  local expr="$2"
  JSON_INPUT="$json_input" python3 -c "import json, os; obj=json.loads(os.environ['JSON_INPUT']); print(${expr})"
}

echo "=== SCBE Monetization Quickstart Demo ==="
echo "Base URL: ${BASE_URL}"

echo
printf '[1/5] Health check\n'
curl -sS "${BASE_URL}/v1/health" | python3 -m json.tool

echo
printf '[2/5] Register sample agents\n'
register_agent() {
  local payload="$1"
  curl -sS -X POST "${BASE_URL}/v1/agents" \
    -H "Content-Type: application/json" \
    -H "SCBE_api_key: ${API_KEY}" \
    -d "${payload}" >/dev/null
}

register_agent '{"agent_id":"ops-safe-001","name":"Ops Safe","role":"operations","initial_trust":0.92}'
register_agent '{"agent_id":"analyst-mid-002","name":"Analyst Mid","role":"analyst","initial_trust":0.58}'
register_agent '{"agent_id":"contractor-risk-003","name":"Contractor Risk","role":"contractor","initial_trust":0.25}'

echo "Registered 3 agents."

echo
printf '[3/5] Send 3 sample agent actions to /v1/authorize\n'

risky_total=0
risky_blocked_or_quarantined=0

authorize_action() {
  local label="$1"
  local payload="$2"

  local response
  response=$(curl -sS -X POST "${BASE_URL}/v1/authorize" \
    -H "Content-Type: application/json" \
    -H "SCBE_api_key: ${API_KEY}" \
    -d "${payload}")

  local decision score decision_id sensitivity
  decision=$(json_field "$response" "obj.get('decision','')")
  score=$(json_field "$response" "obj.get('score','')")
  decision_id=$(json_field "$response" "obj.get('decision_id','')")
  sensitivity=$(json_field "$payload" "obj.get('context',{}).get('sensitivity',0)")

  echo
  echo "--- ${label} ---"
  echo "decision=${decision} score=${score} decision_id=${decision_id}"

  if python3 - <<PY
s=${sensitivity}
import sys
sys.exit(0 if float(s) >= 0.7 else 1)
PY
  then
    risky_total=$((risky_total + 1))
    if [[ "${decision}" != "ALLOW" ]]; then
      risky_blocked_or_quarantined=$((risky_blocked_or_quarantined + 1))
    fi
  fi

  local audit
  audit=$(curl -sS "${BASE_URL}/v1/audit/${decision_id}" -H "SCBE_api_key: ${API_KEY}")
  echo "Audit snapshot (${decision_id}):"
  echo "decision=$(json_field "$audit" "obj.get('decision','')") score=$(json_field "$audit" "obj.get('score','')") agent=$(json_field "$audit" "obj.get('agent_id','')") action=$(json_field "$audit" "obj.get('action','')") target=$(json_field "$audit" "obj.get('target','')")"
}

authorize_action "Action 1: expected low-risk read" '{"agent_id":"ops-safe-001","action":"READ","target":"ops_dashboard","context":{"sensitivity":0.2}}'
authorize_action "Action 2: medium-risk export" '{"agent_id":"analyst-mid-002","action":"EXPORT","target":"finance_summary","context":{"sensitivity":0.6}}'
authorize_action "Action 3: high-risk execution" '{"agent_id":"contractor-risk-003","action":"EXECUTE","target":"prod_payment_router","context":{"sensitivity":0.95}}'

echo
printf '[4/5] Run fleet scenario\n'
fleet_response=$(curl -sS -X POST "${BASE_URL}/v1/fleet/run-scenario" \
  -H "Content-Type: application/json" \
  -H "SCBE_api_key: ${API_KEY}" \
  -d '{
    "scenario_name": "monetization-quickstart",
    "agents": [
      {"agent_id": "ops-safe-001", "name": "Ops Safe", "role": "operations", "initial_trust": 0.92},
      {"agent_id": "analyst-mid-002", "name": "Analyst Mid", "role": "analyst", "initial_trust": 0.58},
      {"agent_id": "contractor-risk-003", "name": "Contractor Risk", "role": "contractor", "initial_trust": 0.25}
    ],
    "actions": [
      {"agent_id": "ops-safe-001", "action": "READ", "target": "ops_dashboard", "sensitivity": 0.2},
      {"agent_id": "analyst-mid-002", "action": "WRITE", "target": "governance_policy", "sensitivity": 0.7},
      {"agent_id": "contractor-risk-003", "action": "EXECUTE", "target": "prod_payment_router", "sensitivity": 0.95}
    ]
  }')

echo "Fleet summary:"
echo "  total_actions=$(json_field "$fleet_response" "obj.get('summary',{}).get('total_actions')") allowed=$(json_field "$fleet_response" "obj.get('summary',{}).get('allowed')") denied=$(json_field "$fleet_response" "obj.get('summary',{}).get('denied')") quarantined=$(json_field "$fleet_response" "obj.get('summary',{}).get('quarantined')")"
echo "  avg_score=$(json_field "$fleet_response" "obj.get('metrics',{}).get('avg_score')") allow_rate=$(json_field "$fleet_response" "obj.get('metrics',{}).get('allow_rate')") elapsed_ms=$(json_field "$fleet_response" "obj.get('metrics',{}).get('elapsed_ms')")"

echo
printf '[5/5] Value proof metric\n'
if [[ ${risky_total} -eq 0 ]]; then
  echo "VALUE PROOF: no risky actions (sensitivity >= 0.7) were included in this run"
else
  proof_pct=$(python3 - <<PY
blocked=${risky_blocked_or_quarantined}
total=${risky_total}
print(round((blocked/total)*100, 1))
PY
)
  echo "VALUE PROOF: risky actions blocked/quarantined = ${risky_blocked_or_quarantined}/${risky_total} (${proof_pct}%)"
fi

echo
echo "Demo complete."
