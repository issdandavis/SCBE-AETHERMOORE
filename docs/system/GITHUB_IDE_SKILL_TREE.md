# GitHub IDE Skill Tree (2D + 3D)

This is a GitHub-first operator tree for choosing the right IDE lane while
keeping Codespaces as the shared execution spine.

## Core Rule

- Use `github_codespaces` as default execution lane.
- Use external IDEs when they have stronger authoring UX for the task.
- Return commits, diffs, and release actions through GitHub lanes.

## Tier 1: Foundation (Always On)

1. Repo operations (`git`, `gh`, branch + PR flow)
2. Devcontainer and Codespaces boot/readiness
3. CI rerun, status triage, and release hygiene

Command:

```powershell
python scripts/system/github_dual_tentacle_router.py --event-type workflow_run --task "triage ci and rerun in codespace"
```

## Tier 2: 2D Product IDE Paths

1. `github_codespaces` (native)
2. `firebase_studio` (import + bridge back to GitHub)
3. `gitpod` (ephemeral workspace bridge)
4. `replit` (rapid import/prototype bridge)
5. `stackblitz` (frontend browser sandbox bridge)

When to use:

- API/product code, docs, tests, integration work, publishing pipelines.

## Tier 3: 3D Authoring IDE Paths

1. `playcanvas_editor` (3D web scenes + live collaboration)
2. `babylonjs_editor` (3D web authoring + export templates)
3. `unity_devops_uvcs` (3D production + build automation + version control bridge)

When to use:

- Scene editing, asset-heavy workflows, real-time visual design loops.

## Tier 4: Router-Based Selection

Use the router to select a platform based on task + mode.

2D example:

```powershell
python scripts/system/github_ide_mesh_router.py --task "ship firebase auth prototype with github repo import" --mode 2d --require-codespaces
```

3D example:

```powershell
python scripts/system/github_ide_mesh_router.py --task "build 3d web scene and sync scripts to github" --mode 3d --prefer playcanvas_editor --require-codespaces
```

Spiralverse-governed example:

```powershell
python scripts/system/github_ide_mesh_router.py --task "integrate spiralverse" --mode auto --require-codespaces
```

Outputs:

- GitHub lanes:
  - `artifacts/agent_comm/github_lanes/webhook_lane.jsonl`
  - `artifacts/agent_comm/github_lanes/cli_lane.jsonl`
  - `artifacts/agent_comm/github_lanes/codespaces_lane.jsonl`
  - `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
- IDE selection log:
  - `artifacts/agent_comm/ide_mesh/ide_decisions.jsonl`
  - `artifacts/agent_comm/ide_mesh/telemetry.jsonl`

## Spiralverse Governance Overlay

1. Layer 5: 6D tongue-vector distance (`KO/AV/RU/CA/UM/DR`) between task and IDE profiles.
2. Layer 9: Resonant gate check with dissonant containment.
3. Layer 11: Roundtable multi-tongue quorum for high-risk/codespaces tasks.
4. Layer 12: Telemetry records tongue, frequency, distance, and gate outcomes.
5. Layer 14: Signed route envelope digest for auditable route integrity.

## Tier 5: Governance

1. Never put secrets/tokens in lane payloads.
2. Keep repo visibility policy aligned with `config/governance/repo_sectioning_policy.json`.
3. Route private-sensitive tasks only through private repos + controlled runners.

## Files Backing This Tree

- `config/governance/ide_platform_matrix.json`
- `scripts/system/github_ide_mesh_router.py`
- `scripts/system/github_dual_tentacle_router.py`
- `scripts/system/github_webhook_server.py`

## Official Source Links

- GitHub Codespaces docs: <https://docs.github.com/en/codespaces>
- GitHub Codespaces quickstart: <https://docs.github.com/en/codespaces/getting-started/quickstart>
- Firebase Studio docs: <https://firebase.google.com/docs/studio>
- Firebase Studio GitHub import flow: <https://firebase.google.com/docs/studio/get-started-import>
- Replit GitHub import/use docs:
  <https://docs.replit.com/replit-workspace/using-git-on-replit/running-github-repositories-replit>
- StackBlitz importing projects:
  <https://developer.stackblitz.com/guides/user-guide/importing-projects>
- Gitpod source control overview: <https://www.gitpod.io/docs/gitpod/source-control/overview>
- PlayCanvas VS Code extension and collaboration docs:
  <https://developer.playcanvas.com/user-manual/editor/scripting/vscode-extension/>
- Babylon.js Editor docs: <https://editor.babylonjs.com/documentation>
- Unity Build Automation + version control:
  <https://docs.unity.com/build-automation/get-started-with-build-automation/connect-your-version-control-system/>
