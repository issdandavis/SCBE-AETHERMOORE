# Monorepo Split Notice — 2026-04

In April 2026, SCBE-AETHERMOORE was split from a single 80+ directory monorepo into a focused set of smaller repos. Each satellite has its own release cadence, clone footprint, and documentation.

## Where did things go?

| Old location | New repo |
|---|---|
| `agents/`, `hydra/`, `mcp/` | [scbe-agents](https://github.com/issdandavis/scbe-agents) |
| `tools/stasm/`, `tools/stvm/` | [scbe-tongues-toolchain](https://github.com/issdandavis/scbe-tongues-toolchain) |
| `experiments/` | [scbe-experiments](https://github.com/issdandavis/scbe-experiments) |
| `training/` | [scbe-training-lab](https://github.com/issdandavis/scbe-training-lab) |
| `docs/` (high-value subset) | [scbe-docs-archive](https://github.com/issdandavis/scbe-docs-archive) |

## Is any data lost?

No. The pre-split state of this repo is preserved at the tag `v-monolith-final`:

```bash
git checkout v-monolith-final
```

The tag points at the last commit before the split and contains every file that ever existed in the monolith.

## Why split?

- **80+ top-level directories** had become hard to navigate
- **ML engineers** wanted to clone only the training lab on HF/Colab without pulling the whole framework
- **Research reviewers** wanted to verify experiments without cloning 224 MB
- **Docs** were triggering test runs every time they changed
- **HYDRA agents** and **Sacred Tongue toolchain** each had logical boundaries that deserved their own release cadence

## What stays in SCBE-AETHERMOORE?

- `symphonic_cipher/` — the core Python package
- `src/`, `packages/`, `api/`, `runtime/` — framework plumbing
- `tests/` — the 6-tier test pyramid (L1 basic → L6 adversarial)
- `workflows/` — CI + n8n automation
- `ui/`, `aether-app/` — thin demo surfaces
- Top-level configs, CLAUDE.md, README.md, LICENSE

The full 9-repo ecosystem map lives at [aethermoore.com](https://aethermoore.com/).
