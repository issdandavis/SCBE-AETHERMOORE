# CLAUDE.md

Guidance for Claude Code in this repository.

## Project Overview

**SCBE-AETHERMOORE** — AI safety/governance framework using hyperbolic geometry (Poincare ball model) for exponential cost scaling of adversarial behavior. **14-layer security pipeline** with post-quantum crypto.

**Core innovation**: adversarial intent costs exponentially more the further it drifts from safe operation, making attacks computationally infeasible.

| Aspect | Details |
|--------|---------|
| Languages | TypeScript (canonical), Python (reference), Rust (experimental) |
| Node / Python | >= 18.0.0 / >= 3.11 (also 3.12-3.14) |
| Test | Vitest (TS), pytest (Python), Playwright (E2E), Cargo (Rust) |
| Property | fast-check (TS), Hypothesis (Python) |
| API | FastAPI + Uvicorn (Python), Express 5 (TypeScript) |
| Package | 4.0.3 (npm + PyPI synced); entry `./dist/src/index.js` |

Common commands live in `package.json` scripts. Discover with `npm run` or `cat package.json`.

## Pre-Push Verification (CI Replication)

```bash
# 1. TypeScript: build + lint + test (~30s)
npm run build && npm run lint && npm test

# 2. Python: exact CI command (-x stops on first failure)
PYTHONPATH=. python -m pytest tests/ -v --ignore=tests/node_modules -x

# 3. Python formatting (must pass)
black --check --target-version py311 --line-length 120 src/ tests/ hydra/
flake8 --max-line-length 120 src/ tests/ hydra/

# Quick smoke (~5s)
PYTHONPATH=. python -m pytest tests/ -x -q \
  --ignore=tests/node_modules \
  --ignore=tests/aetherbrowser/test_integration.py \
  --ignore=tests/aetherbrowser/test_red_zone_integration.py \
  -m "not slow"
```

### CI Gotchas

- **`PYTHONPATH=.`** required so `import src.foo` and `import symphonic_cipher` resolve.
- **`SCBE_FORCE_SKIP_LIBOQS`**: no longer needed (liboqs-python 0.14.1 + liboqs C 0.15.0 installed). Stays as fallback in source for environments without C bindings; do not set by default.
- **Hanging tests**: `tests/aetherbrowser/test_integration.py` and `test_red_zone_integration.py` need Playwright browsers; `--ignore` locally if not installed.
- **Provider SDKs**: `tests/aetherbrowser/test_provider_executor.py` needs `openai` + `huggingface_hub` (in `requirements.txt`).
- **Formatting**: CI rejects unformatted code. Run `black --target-version py311 --line-length 120` and `npm run format` on new files.
- **Unused imports**: TS compilation catches these — `npm run build` before pushing.

## Critical Gotcha: Dual `symphonic_cipher` Packages

Two `symphonic_cipher/` directories with **different** math:

| Location | Formula | Purpose |
|----------|---------|---------|
| Root `symphonic_cipher/` | `H(d,R) = R^(d²)` | Exponential cost multiplier |
| `src/symphonic_cipher/` | `H(d,pd) = 1/(1+d+2*pd)` | Bounded safety score in (0,1] |

Many tests do `sys.path.insert(0, "src/")`, so `import symphonic_cipher` resolves to the `src/` version. Both packages expose variant tags:

```python
import symphonic_cipher
if symphonic_cipher._IS_SAFETY_SCORE: ...   # True = src/ variant
if symphonic_cipher._VARIANT == "root": ... # "root" or "src"
```

Be explicit in new tests. `tests/conftest.py` adds project root to `sys.path` and patches `ai_brain` aliases.

## liboqs PQC Migration

Algorithm renames: `Dilithium3` → `ML-DSA-65`, `Kyber768` → `ML-KEM-768`. Use `_select_dsa_algorithm()` / `_select_kem_algorithm()` helpers — they try the new name first, fall back to old.

## Architecture

### 14-Layer Pipeline

| Layer | Function | Key file |
|---|---|---|
| L1-2 | Complex context → realification | `src/harmonic/pipeline14.ts` |
| L3-4 | Weighted transform → Poincare embedding | `languesMetric.ts`, `pipeline14.ts` |
| L5 | Hyperbolic distance `dH = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))` | `hyperbolic.ts` |
| L6-7 | Breathing transform + Mobius phase | `hyperbolic.ts`, `adaptiveNavigator.ts` |
| L8 | Multi-well realms (Hamiltonian CFI) | `hamiltonianCFI.ts` |
| L9-10 | Spectral + spin coherence (FFT) | `spectral/index.ts` |
| L11 | Triadic temporal distance | `causality_axiom.py` |
| L12 | Harmonic wall `H(d,pd) = 1/(1+d_H+2*pd)` | `harmonicScaling.ts` |
| L13 | Risk decision: ALLOW / QUARANTINE / ESCALATE / DENY | swarm governance |
| L14 | Audio axis (FFT telemetry) | `audioAxis.ts`, `vacuumAcoustics.ts` |

### Quantum Axiom Mesh

Implementations in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`:

1. **Unitarity** (L2,4,7) — norm preservation
2. **Locality** (L3,8) — spatial bounds
3. **Causality** (L6,11,13) — time-ordering
4. **Symmetry** (L5,9,10,12) — gauge invariance
5. **Composition** (L1,14) — pipeline integrity

### Sacred Tongues (Langues Metric)

6 dimensions, golden-ratio weights: **KO** 1.00, **AV** 1.62, **RU** 2.62, **CA** 4.24, **UM** 6.85, **DR** 11.09. Each has a 16×16 token grid (256 tokens/lang).

### Multi-Agent Coordination

| System | Path | Purpose |
|---|---|---|
| HYDRA | `hydra/` | Orchestrator: Spine, Heads, Limbs, Ledger, BFT consensus |
| Fleet | `src/fleet/` | Agent registry, dispatch, governance, swarm |
| Juggling Scheduler | `src/fleet/juggling-scheduler.ts` + `hydra/juggling_scheduler.py` | Physics-based task-flight (FlightState: HELD→THROWN→CAUGHT→VALIDATING→DONE) |
| Red/Blue Arena | `src/security-engine/redblue-arena.ts` | Adversarial model-vs-model sims; provider-agnostic |

## Test Architecture

**Tiers** (TS): L1-basic, L2-unit, L3-integration, L4-property (fast-check, 100+ iterations), L5-security, L6-adversarial.

**File naming**: TS = `{module}.{tier}.test.ts`; Python = `test_{module}.py`.

**Vitest** (`vitest.config.ts`): node env, glob `tests/**/*.test.ts`, excludes `node_modules|dist|e2e|scbe-aethermoore`, 30s timeout, 80%/70% coverage targets.

**pytest** (`pytest.ini`): `asyncio_mode=auto`, `--strict-markers`, source `src`, 80%/70% coverage.

**pytest markers**:
- Tier: `enterprise`, `professional`, `homebrew`
- Domain: `quantum`, `ai_safety`, `agentic`, `compliance`, `stress`, `security`, `formal`, `integration`, `property`, `slow`, `unit`, `perf`, `benchmark`
- Component: `api`, `crypto`, `math`, `governance`, `pqc`

## Code Style

- **TypeScript** (`.prettierrc`): semicolons, single quotes, 100-char lines, 2-space indent, ES5 trailing commas.
- **Python**: Black 120, flake8 120, Google docstrings, type hints on all functions.
- **File header** (TS):
  ```typescript
  /**
   * @file filename.ts
   * @module harmonic/module-name
   * @layer Layer X, Layer Y
   */
  ```
- Add axiom comments where applicable: `// A4: Clamping`, `# A2: Unitarity check`.

## Development Guidelines

**Dual implementation**: TypeScript canonical (production); update TS first, then Python. Parity tests in `tests/cross-language/` and `tests/interop/`.

**When adding features**: tag `@layer`, document axiom, write tier-correct tests, update CHANGELOG, keep TS/Python in sync, run pre-push verification.

**When adding AI providers**: `ModelProvider` enum requires updates in **4 files**:
1. `src/aetherbrowser/router.py` — enum + `MODEL_COST_TIER` + `PROVIDER_ENV_VARS` + `PROVIDER_FAMILY`
2. `src/aetherbrowser/provider_executor.py` — `_MODEL_ID_DEFAULTS` + `PROVIDER_PACKAGES` + adapter method + registration
3. `requirements.txt` — provider SDK package
4. `tests/aetherbrowser/test_command_planner.py` — `enabled_providers` dicts that enumerate all providers

## Commit Convention

```
feat(harmonic): add layer X
fix(crypto): timing attack in envelope
test(harmonic): property-based tests
refactor(spectral): optimize FFT
docs(api): update endpoint docs
chore(deps): bump dependency
```

## npm Package Exports

`scbe-aethermoore` (main) + subpath exports `/harmonic`, `/symphonic`, `/crypto`, `/spiralverse`, `/tokenizer`, `/phdm`, `/ai_brain`, `/governance`.

## Python Package (PyPI)

Installable from `src/`: `code_prism`, `symphonic_cipher`, `api`, `crypto`, `harmonic`, `spiralverse`, `minimal`, `storage`. CLIs: `scbe-convert-to-sft`, `scbe-code-prism`.

## CI/CD

53 workflows in `.github/workflows/`. Core: `ci.yml`, `scbe-gates.yml`, `scbe-tests.yml`. Publishing: `npm-publish.yml`, `release.yml`, `docker-publish.yml`. Discover with `ls .github/workflows/`.

Dockerfiles: `Dockerfile` (main multi-stage Node→liboqs→Python 3.11 runtime, ports 8080+3000), `Dockerfile.api`, `Dockerfile.cloudrun`, `Dockerfile.gateway`, `Dockerfile.research`. Compose: `docker-compose{,.api,.unified,.local}.yml`.

## Key Documentation

| File | Purpose |
|---|---|
| `LAYER_INDEX.md` | 14-layer architecture reference |
| `SPEC.md` | SCBE Kernel Specification (canonical) |
| `SYSTEM_ARCHITECTURE.md` / `ARCHITECTURE.md` | Detailed / high-level architecture |
| `docs/LANGUES_WEIGHTING_SYSTEM.md` | Langues metric deep dive |
| `docs/hydra/ARCHITECTURE.md` | HYDRA orchestration |
| `docs/AETHERBROWSE_BLUEPRINT.md` | AetherBrowse browser agent |
| `docs/API.md` / `docs/INTEGRATIONS.md` / `docs/RUNBOOK.md` | API / integrations / ops |
| `docs/CORE_AXIOMS_CANONICAL_INDEX.md` | Axiom reference |
| `docs/PUBLISHING.md` | Safe release flow |

For project structure, use `Glob` (e.g. `src/**/*.ts`, `agents/*.py`) — directory tree is not maintained here.
