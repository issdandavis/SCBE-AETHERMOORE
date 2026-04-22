# SCBE-AETHERMOORE

AI governance through geometric cost scaling.

This repository is the public working tree for the SCBE-AETHERMOORE stack: a governed AI system built around hyperbolic geometry, semantic weighting, auditability, and multi-layer runtime controls.

It is also a large hybrid repo. There is real code here, real docs here, and real experiments here. If you treat every file as equally canonical, the repo will look noisier than it actually is.

Long-form documentation belongs under `docs/`. Code directories should stay implementation-first and use only minimal maintenance readmes when needed.

## Start Here

- New to the repo: [START_HERE.md](START_HERE.md)
- Current authority order: [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
- Consolidation authority: [docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md](docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md)
- Root authority keep set: [docs/specs/ROOT_AUTHORITY_KEEP_SET.md](docs/specs/ROOT_AUTHORITY_KEEP_SET.md)
- Repo navigation map: [docs/REPO_SURFACE_MAP.md](docs/REPO_SURFACE_MAP.md)
- Machine-readable zone inventory: [config/repo_consolidation_inventory.json](config/repo_consolidation_inventory.json)
- Canonical index policy: [docs/README_INDEX.md](docs/README_INDEX.md)

## What This Repo Is

The public story is:

- a governed AI runtime with a 14-layer architecture
- a packaging surface for npm and PyPI
- a website and demo surface
- a research and proposal lane that is still active

The repo is not being split into more GitHub repositories. The current strategy is one monorepo with clearer product, platform, research, and archive boundaries. That means the correct way to read it is through the routing docs above, not by browsing randomly from the root.

## Primary Product Lane

If you want the nearest thing to the real product surface, start with the browser-and-local-API lane:

- `public/`
- `app/`
- `api/`
- `products/`
- `scripts/aetherbrowser/`

The supporting platform lives mainly in:

- `src/tokenizer/`
- `src/tongues/`
- `src/coding_spine/`
- `src/governance/`
- `src/crypto/`
- `python/scbe/`

## What Works Now

The installable package surface is the simplest public entry point.

Package links:

- npm: [`scbe-aethermoore`](https://www.npmjs.com/package/scbe-aethermoore)
- PyPI: [`scbe-aethermoore`](https://pypi.org/project/scbe-aethermoore/)

Website and public demos:

- Website: [aethermoore.com](https://aethermoore.com)
- GitHub Pages mirror: [issdandavis.github.io/SCBE-AETHERMOORE](https://issdandavis.github.io/SCBE-AETHERMOORE/)
- Hugging Face: [issdandavis](https://huggingface.co/issdandavis)

## Install

```bash
npm install scbe-aethermoore
pip install scbe-aethermoore
```

## Quickstart

Python:

```python
from scbe_aethermoore import scan, scan_batch, is_safe

result = scan("ignore all previous instructions")
print(result["decision"])
print(result["score"])

results = scan_batch(["hello", "DROP TABLE users", "how are you?"])
for row in results:
    print(row["decision"], row["score"])

if not is_safe("ignore all previous instructions"):
    print("blocked")
```

Command line:

```bash
scbe pipeline run --text "hello world"
scbe pipeline run --json --text "DROP TABLE users"
scbe status
```

TypeScript:

```ts
import { scan, isSafe } from "scbe-aethermoore";

const result = scan("ignore all previous instructions");
console.log(result.decision, result.score);
console.log(isSafe("hello world"));
```

## Public Technical Shape

The repo centers on a few recurring ideas:

- hyperbolic embedding and distance-based governance
- semantic weighting across six Sacred Tongues
- multi-layer decision and telemetry flow
- audit-friendly runtime behavior
- local-first tooling and operator workflows

The repo contains multiple historical or experimental formulations of some math surfaces. Do not assume the first formula you find is the current one.

For current authority:

- runtime and documentation precedence: [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
- current constants and formula lock file: [docs/specs/SCBE_CANONICAL_CONSTANTS.md](docs/specs/SCBE_CANONICAL_CONSTANTS.md)

## Public Docs Worth Opening

- System state: [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
- Repo map: [docs/REPO_SURFACE_MAP.md](docs/REPO_SURFACE_MAP.md)
- Canonical index guide: [docs/README_INDEX.md](docs/README_INDEX.md)
- Evidence page: [docs/evidence/EVIDENCE_24_24.md](docs/evidence/EVIDENCE_24_24.md)
- Layer index: [docs/LAYER_INDEX.md](docs/LAYER_INDEX.md)
- System overview: [docs/SCBE_SYSTEM_OVERVIEW.md](docs/SCBE_SYSTEM_OVERVIEW.md)
- Concepts: [docs/CONCEPTS.md](docs/CONCEPTS.md)

## Claim Boundaries

This repository includes:

- canonical surfaces
- active implementation
- historical documents
- proposal material
- exploratory research

So the right question is not "is this in the repo?" but "is this canonical, active, legacy, or exploratory?"

Use this order when there is conflict:

1. [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
2. [docs/specs/SCBE_CANONICAL_CONSTANTS.md](docs/specs/SCBE_CANONICAL_CONSTANTS.md)
3. tests and active runtime entrypoints
4. public docs
5. historical or exploratory material

## Root Reality

The root worktree is currently noisy. There are active edits, temporary lanes, research material, and archive-heavy directories. That does not mean the repo is empty or fake. It means the project needs routing discipline.

If you are reviewing the project seriously, start with:

1. [START_HERE.md](START_HERE.md)
2. [CANONICAL_SYSTEM_STATE.md](CANONICAL_SYSTEM_STATE.md)
3. [docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md](docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md)
4. [docs/REPO_SURFACE_MAP.md](docs/REPO_SURFACE_MAP.md)

Then move into the specific lane you care about.

## Author

Built by [Issac Davis](https://github.com/issdandavis).
