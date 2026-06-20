# Repo Mining CLI Utility Candidates - 2026-05-30

Purpose: identify useful, publishable SCBE CLI features already present in nearby repos, then prioritize imports that improve day-to-day operator value without pulling in sensitive systems.

## Top Candidates

| Priority | Source repo | Files reviewed | Reusable primitive | SCBE CLI hook | Claim boundary |
| --- | --- | --- | --- | --- | --- |
| 1 | `C:\Users\issda\aethermoore-youtube-automation` | `src/aether_youtube_automation/review.py`, `package.py`, `cli.py`, `tests/test_review.py` | Deterministic YouTube package review: title, description, tags, privacy, script length | `scbe youtube review <package.json> --json` | Local package readiness gate, not YouTube upload automation by itself |
| 2 | `C:\Users\issda\aetherbrowser` | `src/aetherbrowser/hyperlane_py.py`, `agents.py`, `page_analyzer.py`, `src/extension/components/ZoneApproval.js` | Permission-zone browser routing, task-to-agent decomposition, local page analysis | `scbe browser gate --url <url> --action <action> --agent <id> --json` | Browser-control safety fixture, not a WebArena leaderboard score |
| 3 | `external_repos/ai-workflow-architect` | `server/services/free-models-config.ts`, `providerAdapters.ts`, `docs/FREE_AI_IMPLEMENTATION_GUIDE.md` | Free-first provider capability routing and cost estimates | `scbe models route --capability code --json` | Provider catalog is time-sensitive and must be refreshed before public pricing claims |
| 4 | `external_repos/spiralverse-protocol` | `src/fleet/agent-registry.ts`, `SAFE_MODE_PROGRESSION.md`, `docs/SPACE_DEBRIS_FLEET.md` | Agent trust registry, safe-mode staging, fleet capability assignment | `scbe agent registry demo/status --json` | Governance/fleet simulation lineage, not operational drone/autonomy certification |
| 5 | `external_repos/scbe-security-gate` | Older math/security prototype docs and Python kernels | Prior security/provenance primitives and immune-system language | Patent/provenance support docs and security tests | Historical/prototype support, not current production implementation until ported and tested |

## Immediate Import Rule

Prefer small deterministic utilities that can be ported into `packages/cli` without depending on sibling checkouts. The CLI should remain publishable from npm and useful to a fresh user.

## First Import

`scbe youtube review` is the first candidate because it is:

- Small enough to port directly.
- Useful for writing and YouTube package work.
- Deterministic and testable.
- Aligned with the "execution, not just advice" CLI direction.

## Next Branch Candidates

1. `feat(cli-youtube-review)` - package readiness gate for creator workflow.
2. `feat(browser-permission-gate)` - a CLI wrapper around AetherBrowser zone logic.
3. `feat/model-route-cost-table` - free-first model routing status and cost estimates.
4. `feat/agent-trust-registry` - local agent/fleet registry demo with trust vectors.
5. `feat/repo-provenance-index` - machine-readable provenance map tying imported ideas back to repo, file, test, and commit.
