#!/usr/bin/env bash
# Setup GitHub labels for SCBE-AETHERMOORE
# Usage: ./scripts/setup-github-labels.sh [owner/repo]
# Requires: gh CLI authenticated

set -euo pipefail

REPO="${1:-issdandavis/SCBE-AETHERMOORE}"

echo "Setting up labels for $REPO..."

create_label() {
  local name="$1" color="$2" description="$3"
  gh label create "$name" --color "$color" --description "$description" --repo "$REPO" --force 2>/dev/null \
    && echo "  + $name" \
    || echo "  ~ $name (exists)"
}

# ── Type labels ──────────────────────────────────────────────
echo "Creating type labels..."
create_label "bug"              "d73a4a" "Something isn't working"
create_label "enhancement"      "a2eeef" "New feature or request"
create_label "documentation"    "0075ca" "Improvements or additions to docs"
create_label "question"         "d876e3" "Further information is requested"
create_label "security"         "e11d48" "Security vulnerability or concern"
create_label "performance"      "f9d0c4" "Performance improvement"
create_label "refactor"         "c5def5" "Code restructuring without behavior change"
create_label "tech-debt"        "fef2c0" "Technical debt to address"

# ── Priority labels ──────────────────────────────────────────
echo "Creating priority labels..."
create_label "priority: critical" "b60205" "Blocking — must fix immediately"
create_label "priority: high"     "d93f0b" "Important — fix soon"
create_label "priority: medium"   "fbca04" "Normal priority"
create_label "priority: low"      "0e8a16" "Nice to have"

# ── Status labels ────────────────────────────────────────────
echo "Creating status labels..."
create_label "needs-triage"     "ededed" "Needs initial assessment"
create_label "needs-review"     "fbca04" "Awaiting code review"
create_label "blocked"          "b60205" "Blocked by external dependency"
create_label "in-progress"      "1d76db" "Actively being worked on"
create_label "ready-for-merge"  "0e8a16" "Approved and ready to merge"
create_label "wontfix"          "ffffff" "This will not be worked on"
create_label "duplicate"        "cfd3d7" "This issue or PR already exists"

# ── Pipeline layer labels ────────────────────────────────────
echo "Creating pipeline layer labels..."
create_label "layer:1-2"        "bfd4f2" "L1-2: Context realification"
create_label "layer:3-4"        "bfdadc" "L3-4: Weighted transform + Poincare"
create_label "layer:5-6"        "d4c5f9" "L5-6: Hyperbolic distance + breathing"
create_label "layer:7-8"        "c9b1ff" "L7-8: Mobius phase + Hamiltonian CFI"
create_label "layer:9-10"       "f9c513" "L9-10: Spectral + spin coherence"
create_label "layer:11-12"      "f97583" "L11-12: Temporal + harmonic wall"
create_label "layer:13-14"      "e36209" "L13-14: Risk decision + audio axis"

# ── Component labels ─────────────────────────────────────────
echo "Creating component labels..."
create_label "harmonic"         "1d76db" "Harmonic pipeline (14-layer)"
create_label "crypto"           "5319e7" "Cryptography / PQC"
create_label "spectral"         "006b75" "FFT spectral analysis"
create_label "symphonic"        "b60205" "Symphonic cipher"
create_label "spiralverse"      "0052cc" "Spiralverse protocol"
create_label "fleet"            "e99695" "Multi-agent fleet"
create_label "governance"       "c2e0c6" "Governance / risk decisions"
create_label "ai-brain"         "d4c5f9" "21D AI brain mapping"
create_label "sacred-tongues"   "f9d0c4" "Six sacred tongues tokenizer"
create_label "api"              "0075ca" "REST API (FastAPI / Express)"
create_label "network"          "bfdadc" "Network / SpaceTor"
create_label "agentic"          "c5def5" "Agent framework"
create_label "web-agent"        "5319e7" "Browser / web automation"

# ── Language labels ──────────────────────────────────────────
echo "Creating language labels..."
create_label "typescript"       "3178c6" "TypeScript code"
create_label "python"           "3572a5" "Python code"

# ── Infrastructure labels ────────────────────────────────────
echo "Creating infrastructure labels..."
create_label "ci"               "ededed" "CI/CD pipelines"
create_label "docker"           "0db7ed" "Docker / containers"
create_label "dependencies"     "0366d6" "Dependency updates"

# ── Axiom labels ─────────────────────────────────────────────
echo "Creating axiom labels..."
create_label "axiom:unitarity"    "bfd4f2" "A1: Norm preservation"
create_label "axiom:locality"     "d4c5f9" "A2: Spatial bounds"
create_label "axiom:causality"    "f9c513" "A3: Time-ordering"
create_label "axiom:symmetry"     "f97583" "A4: Gauge invariance"
create_label "axiom:composition"  "c9b1ff" "A5: Pipeline integrity"

echo ""
echo "Done! Labels configured for $REPO"
