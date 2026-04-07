# Repo Split Blueprint — SCBE-AETHERMOORE

**Created**: April 5, 2026
**Status**: BLUEPRINT — Ready for execution
**Based on**: `THREE_REPO_SPLIT_PLAN.md` (April 3) + fresh audit (April 5)
**Author**: Issac D Davis + Claude

---

## Executive Summary

Split one 7,894-file monorepo into **3 focused repos** after a **pre-flight cleanup** that removes ~4.5 GB of ballast. The split preserves full git history per directory via `git filter-repo`.

| Repo | GitHub Name | Purpose | Est. Files |
|------|-------------|---------|------------|
| **Core** | `SCBE-AETHERMOORE` | Engine + governance + fleet + API + deploy | ~2,800 |
| **Web** | `aethermoorgames-web` | Website + apps + demos + commerce + content | ~1,600 |
| **Labs** | `scbe-aethermoore-labs` | Training + research + notes + experiments + DARPA | ~2,200 |

Plus ~1,300 infra files (tests, scripts, CI, config, k8s) stay in Core.

---

## Current State (April 5, 2026)

```
Repository: SCBE-AETHERMOORE
Branch:     site-publish-v4 (active), main (7,957 commits)
Tracked:    7,894 files
Untracked:  160 files (mostly new training JSONL)
.git/:      1.9 GB
Disk total: ~8.5 GB (including node_modules, .git, untracked)
```

### Size Hotspots (on-disk)

| Path | Size | Tracked? | Action |
|------|------|----------|--------|
| `_staging/` | 1.6 GB | No | Delete (temp build artifacts) |
| `.git/` | 1.9 GB | N/A | Will shrink after filter-repo |
| `training/` | 1.7 GB | Partial | Moves to Labs |
| `training-data/` | 1.5 GB | Partial | Moves to Labs |
| `artifacts/` | 975 MB | Partial | Clean before split |
| `kokoro-v1.0.onnx` | 311 MB | No | Delete or move to HF |
| `models/` | 233 MB | No | Delete or move to HF |
| `voices-v1.0.bin` | 27 MB | No | Delete or move to HF |
| `node_modules/` | ~500 MB | No | Regenerated per repo |

---

## Phase 0: Pre-Flight Cleanup

**Goal**: Remove ballast before the split so each child repo starts clean.

### 0.1 Delete untracked binary blobs

```bash
# These are NOT tracked in git — safe to delete
rm -f kokoro-v1.0.onnx voices-v1.0.bin
rm -rf _staging/
rm -rf models/

# Verify nothing tracked was lost
git status
```

**Upload to HF first if you want to keep them:**
```bash
# Optional: push ONNX model to HF before deleting
huggingface-cli upload issdandavis/scbe-aethermoore-assets kokoro-v1.0.onnx
huggingface-cli upload issdandavis/scbe-aethermoore-assets voices-v1.0.bin
```

### 0.2 Clean artifacts/ (tracked portion)

```bash
# Check what's actually tracked in artifacts/
git ls-files -- artifacts/ | wc -l
git ls-files -- artifacts/ | head -50

# Remove large binary artifacts that shouldn't be in git
# (display drivers, GFX installers, storage_ship blobs)
# Review the list before running:
git ls-files -- artifacts/ | grep -E '\.(exe|zip|bin|tar|gz|onnx)$'

# Remove from tracking (keeps local copy):
git rm --cached artifacts/gfx_win_101.2140.exe 2>/dev/null
git rm -r --cached artifacts/display-driver-backup/ 2>/dev/null
git rm -r --cached artifacts/storage_ship/ 2>/dev/null

# Add to .gitignore
echo "" >> .gitignore
echo "# Large binary artifacts (moved to external storage)" >> .gitignore
echo "artifacts/storage_ship/" >> .gitignore
echo "artifacts/display-driver-backup/" >> .gitignore
echo "artifacts/*.exe" >> .gitignore
echo "artifacts/gfx2140-unpacked/" >> .gitignore
```

### 0.3 Verify docs-build-smoke is gone

```bash
# Already in .gitignore. Verify not tracked:
git ls-files -- docs-build-smoke/ | wc -l
# If > 0:
git rm -r --cached docs-build-smoke/
```

### 0.4 Remove dead directories

```bash
# These are empty or near-empty — remove if tracked
for d in ok/ output/ backups/ sealed_blobs/ test-install/ \
         aetherbrowse/ spiralverse-protocol/ scbe-aethermoore/ Microsoft/; do
  count=$(git ls-files -- "$d" | wc -l)
  if [ "$count" -gt 0 ] && [ "$count" -lt 5 ]; then
    echo "$d has $count tracked files — review:"
    git ls-files -- "$d"
  fi
done
```

### 0.5 Commit cleanup

```bash
git add -A .gitignore
git commit -m "chore: pre-split cleanup — untrack binary blobs, update .gitignore

Removes display driver backups, GFX installers, and storage_ship blobs
from git tracking. Files preserved locally but excluded from split.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### 0.6 Merge to main

```bash
# All cleanup should land on main before the split
git checkout main
git merge site-publish-v4 --no-ff -m "merge: pre-split cleanup from site-publish-v4"
git push origin main
```

---

## Phase 1: Create Web Repo (`aethermoorgames-web`)

### 1.1 Fresh clone + filter

```bash
cd /c/Users/issda
git clone SCBE-AETHERMOORE aethermoorgames-web
cd aethermoorgames-web

# Install git-filter-repo if needed:
pip install git-filter-repo

git filter-repo \
  --path app/ \
  --path apps/ \
  --path articles/ \
  --path assets/ \
  --path automation/social/ \
  --path aether-browser/ \
  --path ai-ide/ \
  --path conference-app/ \
  --path content/ \
  --path dashboard/ \
  --path demo/ \
  --path demos/ \
  --path desktop/ \
  --path docs-build-smoke/ \
  --path game/ \
  --path kindle-app/ \
  --path products/ \
  --path public/ \
  --path scbe-visual-system/ \
  --path shopify/ \
  --path spaces/ \
  --path spiral-word-app/ \
  --path ui/ \
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
  --path src/polly_pump/ \
  --path docs/05-industry-guides/ \
  --path docs/blog/ \
  --path docs/news/ \
  --path docs/product/ \
  --path docs/product-manual/ \
  --path docs/products/ \
  --path docs/static/
```

### 1.2 Initialize web repo

```bash
# Create new package.json for the web repo
cat > package.json << 'EOF'
{
  "name": "aethermoorgames-web",
  "version": "1.0.0",
  "private": true,
  "description": "AetherMoor Games — web surfaces, apps, and commerce",
  "dependencies": {
    "scbe-aethermoore": "^3.3.0"
  }
}
EOF

# Create README
cat > README.md << 'EOF'
# AetherMoor Games — Web

Website, apps, demos, and commerce surfaces for the AetherMoor universe.

Depends on [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) core engine via npm.
EOF

# Push to GitHub
gh repo create issdandavis/aethermoorgames-web --public --source=. --push
```

### 1.3 Verify

```bash
# Should have ~1,600 files
git ls-files | wc -l

# No core engine code should be present
ls src/harmonic/ 2>/dev/null && echo "FAIL: core code leaked" || echo "PASS"
ls training/ 2>/dev/null && echo "FAIL: training leaked" || echo "PASS"
```

---

## Phase 2: Create Labs Repo (`scbe-aethermoore-labs`)

### 2.1 Fresh clone + filter

```bash
cd /c/Users/issda
git clone SCBE-AETHERMOORE scbe-aethermoore-labs
cd scbe-aethermoore-labs

git filter-repo \
  --path training/ \
  --path training-data/ \
  --path artifacts/ \
  --path deliverables/ \
  --path examples/ \
  --path experiments/ \
  --path experimental/ \
  --path exports/ \
  --path external/ \
  --path external_repos/ \
  --path notebooks/ \
  --path notes/ \
  --path paper/ \
  --path phdm-21d-embedding/ \
  --path physics_sim/ \
  --path plugins/ \
  --path prototype/ \
  --path references/ \
  --path skills/ \
  --path src/training/ \
  --path src/artifacts/ \
  --path src/physics_sim/ \
  --path src/science_packs/ \
  --path src/experimental/ \
  --path src/code_prism/ \
  --path docs/research/ \
  --path docs/specs/ \
  --path docs/core-theorems/ \
  --path docs/darpa/ \
  --path docs/map-room/ \
  --path docs/theories-untested/ \
  --path docs/paper/ \
  --path docs/tested-results/ \
  --path docs/eval/ \
  --path docs/plans/
```

### 2.2 Initialize labs repo

```bash
cat > requirements.txt << 'EOF'
scbe-aethermoore>=3.3.0
huggingface-hub>=0.20.0
datasets>=2.16.0
transformers>=4.36.0
torch>=2.1.0
pytest>=7.4.0
hypothesis>=6.90.0
EOF

cat > README.md << 'EOF'
# SCBE-AETHERMOORE Labs

Training data, research notes, experiments, and the Snake Pipeline.

Depends on [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) core engine via pip.

## Key Directories

- `training/` — Snake Pipeline, auto_marker, SFT generation
- `training-data/` — JSONL datasets (SFT, DPO)
- `notes/` — Research notes and round-table sessions
- `docs/darpa/` — DARPA CLARA proposal materials
- `docs/specs/` — Technical specifications
- `skills/` — Skill implementations
- `experiments/` — Active experiments
EOF

gh repo create issdandavis/scbe-aethermoore-labs --public --source=. --push
```

### 2.3 Verify

```bash
git ls-files | wc -l  # ~2,200

ls src/harmonic/ 2>/dev/null && echo "FAIL: core code leaked" || echo "PASS"
ls kindle-app/ 2>/dev/null && echo "FAIL: web code leaked" || echo "PASS"
```

---

## Phase 3: Clean Core Repo (`SCBE-AETHERMOORE`)

**WARNING**: This is the destructive phase. Only run AFTER Phase 1 and 2 repos are pushed and verified.

### 3.1 Remove web surfaces from core

```bash
cd /c/Users/issda/SCBE-AETHERMOORE

# Web surfaces
git rm -r \
  app/ apps/ articles/ assets/ automation/social/ \
  aether-browser/ ai-ide/ conference-app/ \
  dashboard/ demo/ demos/ desktop/ \
  game/ kindle-app/ products/ \
  scbe-visual-system/ shopify/ spaces/ \
  spiral-word-app/ ui/ \
  src/browser/ src/extension/ src/extension-bridge/ \
  src/aetherbrowser/ src/game/ src/gacha_isekai/ \
  src/video/ src/word-addin/ src/aetherwiki/ src/aethercode/ \
  2>/dev/null

# Web docs
git rm -r \
  docs/05-industry-guides/ docs/blog/ docs/news/ \
  docs/product/ docs/product-manual/ docs/products/ \
  2>/dev/null
```

### 3.2 Remove research/training surfaces from core

```bash
git rm -r \
  training/ training-data/ artifacts/ \
  deliverables/ examples/ experiments/ experimental/ \
  exports/ external/ external_repos/ \
  notebooks/ notes/ paper/ phdm-21d-embedding/ \
  physics_sim/ plugins/ prototype/ references/ skills/ \
  src/training/ src/artifacts/ src/physics_sim/ \
  src/science_packs/ src/experimental/ src/code_prism/ \
  2>/dev/null

# Research docs
git rm -r \
  docs/research/ docs/specs/ docs/core-theorems/ \
  docs/darpa/ docs/map-room/ docs/theories-untested/ \
  docs/paper/ docs/tested-results/ docs/eval/ docs/plans/ \
  2>/dev/null
```

### 3.3 Remove dead directories

```bash
git rm -r \
  ok/ output/ backups/ sealed_blobs/ test-install/ \
  aetherbrowse/ spiralverse-protocol/ scbe-aethermoore/ \
  Microsoft/ build/ \
  2>/dev/null
```

### 3.4 Commit

```bash
git add -A
git commit -m "feat(repo): split monorepo — web and labs extracted to separate repos

Web surfaces → github.com/issdandavis/aethermoorgames-web
Research/training → github.com/issdandavis/scbe-aethermoore-labs

Core repo now contains only: engine, governance, fleet, API,
deployment, tests, scripts, CI, and documentation.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

### 3.5 Verify core

```bash
git ls-files | wc -l  # Should be ~2,800 + infra

# Core engine should still work
npm run build
npm test
python -m pytest tests/ -x --timeout=60

# Check no broken imports
grep -r "from training\." src/ --include="*.py" | head -5
grep -r "from artifacts\." src/ --include="*.py" | head -5
```

---

## Phase 4: Inter-Repo Wiring

### Core publishes:

```
npm: scbe-aethermoore@3.3.0 (from packages/kernel/)
PyPI: scbe-aethermoore@3.3.0 (from symphonic_cipher/)
```

### Web consumes:

```json
// aethermoorgames-web/package.json
{ "dependencies": { "scbe-aethermoore": "^3.3.0" } }
```

### Labs consumes:

```
# scbe-aethermoore-labs/requirements.txt
scbe-aethermoore>=3.3.0
```

### Shared schemas:

`schemas/` stays in Core, published as part of the npm package. Types exported via `scbe-aethermoore/types`.

### Git submodules (OPTIONAL — only if cross-repo imports are needed during dev):

```bash
# In labs repo, add core as submodule for dev imports
cd /c/Users/issda/scbe-aethermoore-labs
git submodule add https://github.com/issdandavis/SCBE-AETHERMOORE.git core
```

---

## Phase 5: CI/CD Updates

### Core repo workflows to keep (trim the rest):

```
KEEP (core pipeline):
  ci.yml, scbe.yml, scbe-gates.yml, scbe-tests.yml
  scbe-reusable-gates.yml
  npm-publish.yml, auto-publish.yml
  release-and-deploy.yml, release.yml
  docker-publish.yml
  security-checks.yml, weekly-security-audit.yml
  conflict-marker-guard.yml
  deploy-aws.yml, deploy-eks.yml, deploy-gke.yml
  pages-deploy.yml
  auto-merge.yml, auto-merge-enable.yml
  auto-changelog.yml

MOVE TO LABS:
  huggingface-sync.yml
  vertex-training.yml
  nightly-multicloud-training.yml
  notion-to-dataset.yml
  cloud-kernel-data-pipeline.yml

MOVE TO WEB:
  pages-deploy.yml (copy, not move — both repos may need it)
  daily-social-updates.yml

REVIEW (may be redundant):
  auto-triage.yml, auto-resolve-conflicts.yml
  daily-review.yml, daily_ops.yml
  nightly-connector-health.yml
  notion-sync.yml
```

### New CI for web repo:

```yaml
# aethermoorgames-web/.github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run build
      - run: npm test
```

### New CI for labs repo:

```yaml
# scbe-aethermoore-labs/.github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v --timeout=120
```

---

## Phase 6: Post-Split Checklist

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Core builds | `npm run build` | 0 errors |
| 2 | Core TS tests pass | `npm test` | All green |
| 3 | Core Python tests pass | `python -m pytest tests/ -x` | All green |
| 4 | No broken imports in core | `grep -r "from training" src/` | 0 results |
| 5 | Web repo file count | `git ls-files \| wc -l` | ~1,600 |
| 6 | Labs repo file count | `git ls-files \| wc -l` | ~2,200 |
| 7 | Core repo file count | `git ls-files \| wc -l` | ~2,800 |
| 8 | No binary blobs in any repo | `find . -size +50M -not -path './.git/*'` | 0 results |
| 9 | npm package still publishable | `npm run publish:dryrun` | Success |
| 10 | PyPI package still publishable | `python -m build --sdist` | Success |
| 11 | CI passes on all 3 repos | GitHub Actions | All green |
| 12 | DARPA docs in labs | `ls docs/darpa/` in labs | Present |

---

## What Stays Where — Quick Reference

### Core (`SCBE-AETHERMOORE`)

```
src/                  # Engine code (minus browser/game/training)
  harmonic/           # 14-layer pipeline
  symphonic_cipher/   # Python reference
  crypto/             # PQC primitives
  fleet/              # Fleet management
  governance/         # Governance
  ai_brain/           # 21D brain mapping
  api/                # REST API
  gateway/            # API gateway
  ...                 # All other core src/ modules
symphonic_cipher/     # Root Python package
packages/             # kernel, sixtongues, cli
agents/               # Agent implementations
hydra/                # Hydra orchestration
api/                  # API layer
python/               # Python implementations
mcp/                  # MCP server
tests/                # ALL tests (they test core code)
scripts/              # Automation scripts
.github/workflows/    # CI/CD (trimmed)
config/               # Configuration
k8s/                  # Kubernetes
deploy/               # Deployment
rust/                 # Rust scbe_core
workflows/            # n8n workflows
schemas/              # Schemas
policies/             # Policies
benchmarks/           # Benchmarks
tools/                # Utilities
docs/                 # Core docs (architecture, API, deployment)
```

### Web (`aethermoorgames-web`)

```
app/                  # Main app
apps/                 # Sub-apps
kindle-app/           # Kindle reader
conference-app/       # Conference app
content/              # Content articles
public/               # Static assets
scbe-visual-system/   # Design system
demo/, demos/         # Demos
desktop/              # Desktop app
game/                 # Game
spiral-word-app/      # Spiral word game
ai-ide/               # AI IDE
ui/                   # UI components
products/             # Product pages
shopify/              # Commerce
spaces/               # HF spaces
src/browser/          # Browser code
src/extension/        # Extension
src/game/             # Game engine
src/gacha_isekai/     # Gacha
src/video/            # Video
src/polly_pump/       # Polly widget
docs/blog/            # Blog
docs/product/         # Product docs
docs/static/          # Static site files
```

### Labs (`scbe-aethermoore-labs`)

```
training/             # Snake Pipeline, auto_marker, SFT scripts
training-data/        # JSONL datasets
notes/                # Research notes, round-table sessions
skills/               # Skill implementations
experiments/          # Active experiments
notebooks/            # Jupyter notebooks
artifacts/            # Build/training artifacts
external/             # External data
plugins/              # Plugin system
prototype/            # Prototypes
examples/             # Example code
docs/darpa/           # DARPA CLARA proposal
docs/specs/           # Technical specs
docs/research/        # Research papers
docs/plans/           # Plans (including this blueprint)
docs/map-room/        # Source maps
src/code_prism/       # Code analysis
src/training/         # Training code
src/physics_sim/      # Physics simulation
```

---

## Execution Timeline

| Day | Phase | Duration | Notes |
|-----|-------|----------|-------|
| 1 | Phase 0: Pre-flight cleanup | 1 hour | Safe, reversible |
| 1 | Phase 1: Create web repo | 30 min | git filter-repo |
| 1 | Phase 2: Create labs repo | 30 min | git filter-repo |
| 2 | Phase 3: Clean core | 1 hour | DESTRUCTIVE — verify phases 1-2 first |
| 2 | Phase 4: Inter-repo wiring | 30 min | package.json, requirements.txt |
| 2 | Phase 5: CI/CD updates | 1 hour | Move/create workflows |
| 2 | Phase 6: Post-split checklist | 1 hour | Full verification |

**Total: ~5 hours across 2 sessions.**

---

## Rules

1. **Do NOT rewrite code during the split** — just move boundaries
2. **Do NOT delete the monorepo** — keep it as archive after split
3. **Do NOT split into more than 3 repos** — premature fragmentation
4. **Do NOT let training data leak into npm/PyPI packages** — check MANIFEST.in and .npmignore
5. **Do NOT expose fleet system in npm package** — internal only
6. **Compress, don't delete** — per Issac's standing rule
7. **Test the full alphabet** — run ALL tests on ALL repos, not spot checks

---

## Dependencies

| Tool | Version | Install |
|------|---------|---------|
| `git-filter-repo` | >= 2.38 | `pip install git-filter-repo` |
| `gh` (GitHub CLI) | >= 2.40 | `winget install GitHub.cli` |
| Node.js | >= 18 | Already installed |
| Python | >= 3.11 | Already installed |

---

## Rollback Plan

If anything goes wrong:
1. Web and Labs repos are created from clones — delete them on GitHub
2. Core repo changes are in commits — `git revert` the cleanup commits
3. The original monorepo is always the source of truth until all 3 repos pass Phase 6

The monorepo stays intact (with full history) regardless. The split is additive, not destructive, until Phase 3.
