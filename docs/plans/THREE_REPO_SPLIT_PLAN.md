# 3-Repo Split Plan — SCBE-AETHERMOORE

**Created**: April 3, 2026
**Status**: PLAN — Awaiting user confirmation before execution
**Current state**: 8,403 tracked files, 683 MiB repo, 45 local branches

---

## Overview

Split the monorepo into 3 focused repos:

| Repo | Purpose | Estimated Files |
|---|---|---|
| **SCBE-AETHERMOORE** | Core engine + governance + fleet + deployment | ~2,500 |
| **aethermoorgames-web** | Website + demos + apps + commerce | ~1,800 |
| **scbe-aethermoore-labs** | Training + research + experiments + data | ~2,400 |

Plus ~1,600 files in shared infra (tests, scripts, docs, CI) that stay in core.

---

## Current File Count by Category

### Core Engine (~2,500 files → Repo 1)
```
src/harmonic/           71 files   # 14-layer pipeline (CORE)
src/symphonic_cipher/  209 files   # Python reference impl (CORE)
src/crypto/             33 files   # PQC primitives
src/fleet/              49 files   # Fleet management
src/governance/         18 files   # Governance module
src/ai_brain/           26 files   # 21D brain mapping
src/spiralverse/        17 files   # Spiralverse protocol
src/symphonic/          13 files   # TS symphonic cipher
src/spectral/            1 file    # FFT coherence
src/tokenizer/           3 files   # Sacred Tongues
src/security/            4 files   # Security
src/security-engine/     7 files   # Security engine
src/selfHealing/         5 files   # Self-healing
src/network/             5 files   # Network (SpaceTor)
src/spaceTor/            4 files   # SpaceTor router
src/m4mesh/             13 files   # M4 mesh
src/gateway/             7 files   # API gateway
src/api/                14 files   # REST API
src/core/                3 files   # Core
src/kernel/              6 files   # Kernel
src/mcp_server/          3 files   # MCP server
src/agent/               5 files   # Agent
src/agentic/            11 files   # Agentic
src/agent_comms/         5 files   # Agent comms
src/ai_orchestration/   10 files   # AI orchestration
src/cloud/               4 files   # Cloud
src/storage/             8 files   # Storage
src/integrations/        3 files   # Integrations
src/licensing/           5 files   # Licensing
src/minimal/             6 files   # Minimal
src/rollout/             2 files   # Rollout
src/flow_router/         4 files   # Flow router
src/cognitive_governance/ 5 files  # Cognitive governance
src/cddm/               6 files   # CDDM
src/knowledge/          21 files   # Knowledge
src/pqc/                 1 file    # PQC
src/metrics/             1 file    # Metrics
src/memory/              1 file    # Memory
src/errors/              1 file    # Errors
src/constants/           1 file    # Constants
src/utils/               1 file    # Utils
src/primitives/          3 files   # Primitives
src/lattice/             2 files   # Lattice
src/notarize/            2 files   # Notarize
src/sealed_blobs/        1 file    # Sealed blobs
src/scbe/                1 file    # SCBE
src/polly_pump/          7 files   # Polly pump
src/aaoe/                6 files   # AAOE
src/aethermoore_math/    2 files   # Math
symphonic_cipher/       96 files   # Python package root
packages/kernel/        ~30 files  # Kernel package
packages/sixtongues/    ~20 files  # SixTongues package
packages/scbe-aethermoore-cli/ ~7 files
agents/                 54 files   # Agent implementations
hydra/                  38 files   # Hydra orchestration
api/                    24 files   # API layer
python/                 45 files   # Python implementations
mcp/                    15 files   # MCP server
```

### Infrastructure (stays in Repo 1)
```
tests/                 618 files   # All tests
scripts/               511 files   # Automation scripts
.github/workflows/      53 files   # CI/CD
config/                 37 files   # Configuration
k8s/                    13 files   # Kubernetes
deploy/                 12 files   # Deploy scripts
aws/                     6 files   # AWS
services/                4 files   # Services
schemas/                20 files   # Schemas
policies/               11 files   # Policies
benchmarks/             26 files   # Benchmarks
tools/                  23 files   # Utility tools
bin/                     2 files   # Binaries
rust/                    4 files   # Rust scbe_core
proto/                   1 file    # Protobuf
lexicons/                4 files   # Lexicons
workflows/              27 files   # n8n workflows
```

### Web/Interface (~1,800 files → Repo 2: aethermoorgames-web)
```
docs-build-smoke/      637 files   # TRACKED BUILD OUTPUT (should be .gitignored)
kindle-app/            584 files   # Kindle app
content/               250 files   # Content articles
scbe-visual-system/     59 files   # Visual system
demo/                   45 files   # Demo scripts
conference-app/         40 files   # Conference app
public/                 33 files   # Public assets
apps/                   18 files   # Sub-apps
products/               14 files   # Product files
articles/               13 files   # Articles
demos/                  12 files   # Demo files
spiral-word-app/         9 files   # Spiral word app
desktop/                 8 files   # Desktop app
automation/social/       8 files   # Social automation
aether-browser/          7 files   # Aether browser
shopify/                 1 file    # Shopify
spaces/                  5 files   # Spaces
app/                     5 files   # App
ai-ide/                 16 files   # AI IDE
dashboard/               2 files   # Dashboard
ui/                      3 files   # UI components
assets/                  2 files   # Assets
src/browser/            20 files   # Browser code
src/extension/          20 files   # Extension code
src/extension-bridge/    6 files   # Extension bridge
src/aetherbrowser/      13 files   # AetherBrowser
src/game/               13 files   # Game
src/gacha_isekai/        9 files   # Gacha
src/video/              11 files   # Video
src/word-addin/          2 files   # Word add-in
src/aetherwiki/          1 file    # AetherWiki
src/aethercode/          1 file    # AetherCode
game/                    5 files   # Game
```

### Research/Training (~2,400 files → Repo 3: scbe-aethermoore-labs)
```
training/             1265 files   # Training orchestration
training-data/         399 files   # SFT/DPO data
external/              470 files   # External repos/data
notes/                 188 files   # Research notes
skills/                 91 files   # Skill implementations
examples/               59 files   # Example modules
deliverables/           25 files   # Deliverables
prototype/              25 files   # Prototypes
notebooks/              19 files   # Jupyter notebooks
experiments/            16 files   # Experiments
plugins/                14 files   # Plugins
artifacts/              44 files   # Artifacts
external_repos/          8 files   # External repos
exports/                 8 files   # Exports
references/              3 files   # References
experimental/            3 files   # Experimental
physics_sim/             5 files   # Physics sim
paper/                   1 file    # Paper
phdm-21d-embedding/      1 file    # PHDM embedding
src/training/            5 files   # Training code
src/artifacts/          20 files   # Artifacts code
src/physics_sim/        12 files   # Physics sim
src/science_packs/       1 file    # Science packs
src/experimental/        1 file    # Experimental
src/code_prism/          8 files   # Code prism
```

### Documentation split
```
# Stays in Repo 1 (core docs):
docs/00-overview/
docs/01-architecture/
docs/03-deployment/
docs/06-integration/
docs/08-reference/
docs/patent/
docs/proposals/
docs/API.md, ARCHITECTURE.md, etc. (core reference docs)

# Moves to Repo 2 (web docs):
docs/05-industry-guides/
docs/blog/
docs/news/
docs/product/
docs/product-manual/
docs/products/
docs/pricing.html, redteam.html, etc.

# Moves to Repo 3 (research docs):
docs/research/
docs/specs/
docs/core-theorems/
docs/map-room/
docs/theories-untested/
docs/paper/
docs/tested-results/
docs/eval/
```

---

## Package Boundaries (Freeze These)

### 1. npm runtime package: `packages/kernel/`
```json
{
  "name": "scbe-aethermoore",
  "main": "./dist/src/index.js",
  "files": ["dist/", "README.md", "LICENSE"],
  "exports": {
    ".": "./dist/src/index.js",
    "./harmonic": "./dist/src/harmonic/index.js",
    "./crypto": "./dist/src/crypto/index.js",
    "./symphonic": "./dist/src/symphonic/index.js"
  }
}
```

### 2. Python runtime package: `symphonic_cipher/`
```toml
[project]
name = "scbe-aethermoore"

[tool.setuptools.packages.find]
include = ["symphonic_cipher*", "scbe_aethermoore*"]
exclude = ["tests*", "docs*", "notebooks*", "training*", "artifacts*"]
```

### 3. Python CLI package: `packages/sixtongues/`
Standalone helper for Sacred Tongues operations.

### 4. DANGER: `src/package.json` and `src/pyproject.toml`
These create an accidental package boundary inside `src/`.
**Action**: Set `src/package.json` to `"private": true` or remove entirely.

---

## Migration Sequence

### Phase 0: Pre-flight (before any split)
1. Fix expired `GH_TOKEN` — revoke/regenerate PAT at https://github.com/settings/tokens
2. Set `src/package.json` → `"private": true`
3. Add `docs-build-smoke/` to `.gitignore` (637 tracked build files)
4. Remove tracked empty directories
5. Commit all cleanup changes

### Phase 1: Create Repo 2 (aethermoorgames-web)
```bash
# Fresh clone for web repo
git clone SCBE-AETHERMOORE aethermoorgames-web
cd aethermoorgames-web

# Keep only web surfaces
git filter-repo \
  --path app/ \
  --path apps/ \
  --path conference-app/ \
  --path content/ \
  --path dashboard/ \
  --path demo/ \
  --path demos/ \
  --path desktop/ \
  --path docs-build-smoke/ \
  --path kindle-app/ \
  --path public/ \
  --path products/ \
  --path scbe-visual-system/ \
  --path shopify/ \
  --path spaces/ \
  --path spiral-word-app/ \
  --path ui/ \
  --path assets/ \
  --path articles/ \
  --path automation/social/ \
  --path aether-browser/ \
  --path ai-ide/ \
  --path game/ \
  --path src/browser/ \
  --path src/extension/ \
  --path src/extension-bridge/ \
  --path src/aetherbrowser/ \
  --path src/game/ \
  --path src/gacha_isekai/ \
  --path src/video/ \
  --path src/word-addin/ \
  --path src/aetherwiki/ \
  --path src/aethercode/ \
  --path docs/05-industry-guides/ \
  --path docs/blog/ \
  --path docs/news/ \
  --path docs/product/ \
  --path docs/product-manual/ \
  --path docs/products/
```

### Phase 2: Create Repo 3 (scbe-aethermoore-labs)
```bash
git clone SCBE-AETHERMOORE scbe-aethermoore-labs
cd scbe-aethermoore-labs

git filter-repo \
  --path training/ \
  --path training-data/ \
  --path external/ \
  --path notes/ \
  --path skills/ \
  --path examples/ \
  --path deliverables/ \
  --path prototype/ \
  --path notebooks/ \
  --path experiments/ \
  --path experimental/ \
  --path exports/ \
  --path external_repos/ \
  --path artifacts/ \
  --path physics_sim/ \
  --path paper/ \
  --path phdm-21d-embedding/ \
  --path references/ \
  --path src/training/ \
  --path src/artifacts/ \
  --path src/physics_sim/ \
  --path src/science_packs/ \
  --path src/experimental/ \
  --path src/code_prism/ \
  --path docs/research/ \
  --path docs/specs/ \
  --path docs/core-theorems/ \
  --path docs/map-room/ \
  --path docs/theories-untested/ \
  --path docs/paper/ \
  --path docs/tested-results/ \
  --path docs/eval/
```

### Phase 3: Clean Repo 1 (core engine)
```bash
# After repos 2 and 3 are created and pushed,
# remove their directories from the core repo
# This is the most destructive step — do LAST

# Remove web surfaces
git rm -r app/ apps/ conference-app/ demo/ demos/ desktop/ \
  kindle-app/ scbe-visual-system/ shopify/ spaces/ spiral-word-app/ \
  ui/ dashboard/ aether-browser/ ai-ide/ game/ \
  docs-build-smoke/ automation/social/ \
  src/browser/ src/extension/ src/extension-bridge/ \
  src/aetherbrowser/ src/game/ src/gacha_isekai/ \
  src/video/ src/word-addin/ src/aetherwiki/ src/aethercode/

# Remove research surfaces
git rm -r training/ training-data/ external/ notes/ \
  examples/ deliverables/ prototype/ notebooks/ \
  experiments/ experimental/ exports/ external_repos/ \
  physics_sim/ paper/ phdm-21d-embedding/ \
  src/training/ src/artifacts/ src/physics_sim/ \
  src/science_packs/ src/experimental/ src/code_prism/
```

---

## Inter-Repo Wiring

### Core (Repo 1) publishes:
- npm: `scbe-aethermoore` (from packages/kernel/)
- PyPI: `scbe-aethermoore` (from symphonic_cipher/)

### Web (Repo 2) consumes:
```json
// package.json
{ "dependencies": { "scbe-aethermoore": "^3.3.0" } }
```

### Labs (Repo 3) consumes:
```bash
pip install scbe-aethermoore
```

### Shared types/schemas:
- `schemas/` stays in core, published as part of npm package
- Types exported via `scbe-aethermoore/types`

---

## Satellite Repos (already exist, don't merge back)
- `six-tongues-geoseal` — standalone GeoSeal
- `spiralverse-protocol` — standalone Spiralverse
- `scbe-aethermoore-demo` — can merge into aethermoorgames-web

---

## Immediate Guard Actions (before split)

1. **`src/package.json`** → add `"private": true`
2. **`.npmignore`** → verify it excludes training/, notebooks/, docs/, artifacts/
3. **`MANIFEST.in`** → verify it excludes Python packaging leaks
4. **`docs-build-smoke/`** → add to `.gitignore`, `git rm -r --cached`
5. **Binary files** → move GumRoad/*.zip and products/*.zip to GitHub Releases

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Import breakage after split | Run `npm test` and `pytest` on each repo after split |
| CI workflow references | Many workflows reference paths that will move — update after split |
| Cross-repo imports in src/ | Audit with `grep -r "from.*training\|from.*artifacts" src/` |
| History loss | git filter-repo preserves relevant history per directory |
| Users with existing clones | Announce split in CHANGELOG, update npm/PyPI README |

---

## What NOT To Do

- Do NOT split into more than 3 repos (premature fragmentation)
- Do NOT expose fleet system in npm package
- Do NOT let training data leak into pip/npm published packages
- Do NOT rewrite code during the split — just move boundaries
- Do NOT delete the monorepo — keep it as archive after split
