# Package Registry Changelog - 2026-05-30

This is a registry-backed release note for SCBE packages. It compares the
versions merged on `origin/main` against npm and PyPI as of 2026-05-30.

## Registry Snapshot

| Package | Registry | Published latest | Repo version on `origin/main` | Status |
| --- | --- | ---: | ---: | --- |
| `scbe-aethermoore` | npm | `4.1.3` | `4.2.1` | Publish pending |
| `scbe-aethermoore` | PyPI | `4.2.0` | `4.2.1` | Patch publish pending |
| `scbe-aethermoore-cli` | npm | `4.4.0` | `4.4.0` | Version aligned; unreleased code after publish |
| `scbe-agent-bus` | npm | `0.4.1` | `0.4.1` | Version aligned; unreleased code after publish |
| `scbe-agent-bus` | PyPI | `0.3.0` | `0.3.0` | Version aligned |
| `scbe-polly-pad-cli` | npm | Not published | `0.1.0` | First publish pending |
| `scbe-polly-pad-cli` | PyPI | Not published | N/A | Optional Python wrapper not present |
| `scbe-bookforge` | PyPI | Not published | `0.1.0` | First publish pending |
| `@scbe/kernel` | npm | Not published | private | Internal package |
| `@scbe/workflow-engine` | npm | Not published | private | Internal package |

Registry evidence commands:

```powershell
npm view scbe-aethermoore version dist-tags time.modified time.created --json
npm view scbe-aethermoore-cli version dist-tags time.modified time.created --json
npm view scbe-agent-bus version dist-tags time.modified time.created --json
npm view scbe-polly-pad-cli version time --json
$script = @'
import json, urllib.request
for name in ["scbe-aethermoore", "scbe-agent-bus", "scbe-bookforge", "scbe-polly-pad-cli"]:
    print(name, json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json"))["info"]["version"])
'@
$script | python -
```

## Main Package: `scbe-aethermoore`

### `4.2.1` - Merged, publish pending

The repo is ahead of both registries. `origin/main` has `4.2.1` in both
`package.json` and `pyproject.toml`, but npm is still at `4.1.3` and PyPI is
at `4.2.0`.

Highlights since the npm `4.1.3` publish:

- Added OIDC trusted publisher release plumbing and browser binary resolver.
- Added benchmark evidence hub commands and local benchmark lanes.
- Added real-model task corpus and real-patch fixture benchmark lanes.
- Added ARC-AGI-2 local baseline pretest lane.
- Hardened Python dependencies after vulnerability review.
- Added longform bridge command surface on the public CLI side.

Publish action:

- Publish npm `scbe-aethermoore@4.2.1`.
- Publish PyPI `scbe-aethermoore==4.2.1`.
- Verify both registries with `npm view` and PyPI JSON after publish.

## CLI Package: `scbe-aethermoore-cli`

### `4.4.0` - Published, unreleased changes present

npm and repo version numbers match at `4.4.0`, but `origin/main` has CLI
commits after the 2026-05-26 registry publish. Treat the next CLI publish as
either `4.4.1` for patch-level command additions or `4.5.0` if the longform
bridge is marketed as a user-facing feature release.

Recent merged changes:

- Added benchmark evidence lanes and evidence hub commands.
- Added YouTube package review utility.
- Improved operator utility surface.
- Added longform bridge command surface.
- Wired benchmark command entrypoints such as `scbe bench longform`.

Publish action:

- Decide next version: recommended `4.5.0` if longform bridge lands as a
  feature, otherwise `4.4.1`.
- Run `npm test` in `packages/cli`.
- Pack with `npm pack --dry-run` and confirm no generated or secret files are
  included.

## Agent Bus Package: `scbe-agent-bus`

### `0.4.1` - Published, unreleased changes present

npm and repo version numbers match at `0.4.1`, but the bus has many merged
post-publish features. Treat the next npm publish as a feature release.

Recent merged changes:

- RuntimeGate durable state and governance gates.
- Free-first provider health matrix and squad routing policy.
- Headless rubix browser benchmark and rubix browser planning adapter.
- ResumePacket, ToolLoopDetector, ReactionChain, and BoardFields.
- Star-path routing benchmark, vector-field navigation benchmark, and sparse
  search-space router.
- Tool factory validation/registry and tool registry bridge.
- StationManifest, KeeperAgent, ControlIntent, Polly Operator, HandoffPacket,
  and station-cycle integration.
- Research API tools, semantic sphere benchmark, compass planner, trajectory
  state gate, and multi-field pathfinding improvements.

Publish action:

- Recommended next npm version: `0.5.0`.
- Keep PyPI `scbe-agent-bus==0.3.0` unchanged unless the Python wrapper changed.
- Run package-local checks:

```powershell
cd packages/agent-bus
npm run build
npm test
npm run typecheck
npm pack --dry-run
```

## Polly Pad CLI: `scbe-polly-pad-cli`

### `0.1.0` - Merged, first publish pending

`origin/main` contains `packages/polly-pad-cli/package.json` with
`scbe-polly-pad-cli@0.1.0`, but npm has no published package under
`scbe-polly-pad-cli`, `@scbe/polly-pad-cli`, or `scbe-polly-pad`.

Merged feature surface:

- `polly init`, task state, recipes, handoff, attach/detach, snapshots, shell,
  and doctor commands.
- Hash-chained audit receipts with `polly audit list/verify/export`.
- Tool registry bridge to governed tools from `tools.json`.
- Cross-language hex/binary packets, reversible patch bundles, runtime
  execution checks, and pathfinding benchmark commands.
- Free-first model routing, Ollama Cloud support, Hugging Face fallback, and
  PowerShell script surface.

Publish action:

- First npm publish: `scbe-polly-pad-cli@0.1.0`.
- Confirm package contents with:

```powershell
cd packages/polly-pad-cli
npm test
npm pack --dry-run
```

## Python Packages

### `scbe-aethermoore`

PyPI latest is `4.2.0`; repo version is `4.2.1`. Publish a patch release after
confirming the wheel/sdist contents.

### `scbe-agent-bus`

PyPI latest and repo version both read `0.3.0`. No version bump is required
unless the Python wrapper gets new behavior.

### `scbe-bookforge`

Repo has `packages/bookforge/pyproject.toml` at `0.1.0`, but no PyPI package is
published. Treat it as a first-publish candidate only after a package-content
review.

## Recommended Release Order

1. `scbe-aethermoore@4.2.1` on npm and `scbe-aethermoore==4.2.1` on PyPI to
   remove registry drift.
2. `scbe-agent-bus@0.5.0` on npm for the station, reaction-chain, browser,
   pathfinding, and tool-factory feature wave.
3. `scbe-aethermoore-cli@4.5.0` on npm if the longform command surface is
   included in the public CLI release.
4. `scbe-polly-pad-cli@0.1.0` first npm publish after dry-run package review.
5. `scbe-bookforge==0.1.0` only if the package is ready for public support.

## Claim Boundary for Public Changelogs

Use evidence language:

- Say "published latest", "repo version", "merged", "publish pending", and
  "verified with registry queries".
- Avoid saying a feature is live for users until the matching package version is
  published and install-tested from the registry.
- Keep benchmark claims tied to commands, commit hashes, and artifacts.
