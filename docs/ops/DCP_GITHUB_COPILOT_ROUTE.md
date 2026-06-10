# DCP GitHub + Copilot Route

Status: operating route.
Last updated: 2026-05-23.

This route turns "fix it and push it" into a Deploy Condition Packet (DCP). The DCP is the sealed envelope: tools are scoped, secrets stay local, completion gates are explicit, and the watcher receipt is written before dispatch.

Copilot is allowed as a proposer/explainer. It is not allowed to decide completion.

## Route Spine

```text
human goal
  -> DCP envelope
  -> proposed operation pieces
  -> Tetris-tree route lock
  -> local patch / command execution
  -> diff/lint/test gate pieces
  -> GitHub PR piece
  -> CI watcher receipt piece
  -> merge verification piece
  -> sync main
  -> prune branch
```

The important line: external tools can propose, SCBE verifies.

## Tetris-Tree Operation

The route is not "do every suggested command in order." Models and tools propose pieces. The system decides whether each piece locks into a route slot.

```text
piece proposed: Copilot suggests a shell command
slot available: candidate-proposal slot
lock checks: lane match + required artifacts + tool trust + risk capacity + geometry fit
result: locked piece can advance; loose piece is discarded or sent to triage
```

The default PR tree has four slots:

| Slot | Accepted piece lane | Required state | Output |
| --- | --- | --- | --- |
| `inspect` | `inspect` | clean root intent | `repo_state` |
| `propose` | `propose` | `repo_state` | `candidate_patch` |
| `verify` | `verify` | `candidate_patch` | `local_gate_report` |
| `publish` | `publish` | `local_gate_report` | `pr_number`, `watcher_receipt` |

The lock is geometric but mechanical: each piece and slot carries `(context_fit, verification_fit, safety_fit)`. The score also includes risk capacity and lane compatibility. A proposal that sounds good but does not fit the slot does not execute.

This is the difference between chat and an operating system:

- chat gives you pieces,
- DCP defines the board,
- Tetris-tree routing decides lock-in,
- completion gates decide whether the locked route actually worked.

## Approved Tool Roles

| Tool | Role | Scope | Completion authority |
| --- | --- | --- | --- |
| `git` | branch, diff, commit, sync, prune | allowed | no |
| `gh` | PRs, issues, workflow runs, CI logs | allowed | no |
| GitHub MCP | issue/PR/repo API route through Codex | restricted | no |
| Copilot CLI | suggest commands, explain failures, propose candidate patches | restricted | no |
| shell | run local gates and repo scripts | restricted | no |
| DCP gates | decide whether the route can advance | deterministic | yes |

Secrets that must stay local:

- `CODEX_GITHUB_PERSONAL_ACCESS_TOKEN`
- `.env`
- `config/connector_oauth/.env.connector.oauth`
- `.home/.codex`

Do not paste secrets into Copilot prompts, issue bodies, PR bodies, or logs.

## PowerShell Commands

Start from a clean root:

```powershell
git status --short --branch
git fetch origin --prune
git switch main
git reset --hard refs/remotes/origin/main
```

Create a branch:

```powershell
git switch -c feat/example-dcp-route
```

Optional Copilot proposer route:

```powershell
gh extension list
gh extension install github/gh-copilot
gh copilot suggest "fix the failing lint with the smallest safe patch" --target shell
gh copilot explain "the pytest failure output or GitHub Actions failure snippet"
```

The Copilot output is only a candidate. Apply only the part that survives review.

Run local gates:

```powershell
git diff --check HEAD
npm run lint
python -m pytest tests\agentic\test_dcp.py tests\agentic\test_dcp_routes.py -q
npx vitest run tests/cross-language/nsm-primes-parity.test.ts
```

Commit and push:

```powershell
git add src\agentic\dcp_routes.py tests\agentic\test_dcp_routes.py docs\ops\DCP_GITHUB_COPILOT_ROUTE.md
git commit -m "feat(agentic): add DCP GitHub Copilot route"
git push -u origin feat/example-dcp-route
```

Open a PR:

```powershell
gh pr create --head feat/example-dcp-route --base main --title "feat(agentic): add DCP GitHub Copilot route" --body-file .scbe\ops\pr_body.md
```

Stamp/watch the downstream state:

```powershell
gh pr view --json number,url,state,statusCheckRollup,mergeCommit
gh run view <run-id> --json status,conclusion,url,jobs
gh run watch <run-id> --interval 10
```

If a check fails:

```powershell
gh run view <run-id> --log
gh pr checks <pr-number>
```

After merge and late checks are green:

```powershell
git fetch origin --prune
git switch main
git reset --hard refs/remotes/origin/main
git branch -d feat/example-dcp-route
git push origin --delete feat/example-dcp-route
git status --short --branch
```

## Python Route Builder

The executable route factories live in `src/agentic/dcp_routes.py`.

Example:

```python
from src.agentic.dcp_routes import create_github_pr_dcp

dcp = create_github_pr_dcp(
    intent="fix CI and ship a clean PR",
    branch="fix/ci-route",
    title="fix(ci): route cleanup",
    test_commands=[
        "python -m pytest tests/agentic/test_dcp.py tests/agentic/test_dcp_routes.py -q",
        "npm run lint",
    ],
)

print(dcp.watcher_receipt.watch_command)
```

Tetris-tree route example:

```python
from src.agentic.dcp_routes import (
    TETRIS_TREE_PR_PIECES,
    TETRIS_TREE_PR_SLOTS,
    approved_agentic_tools,
    route_tetris_tree,
)

decisions = route_tetris_tree(
    TETRIS_TREE_PR_PIECES,
    TETRIS_TREE_PR_SLOTS,
    approved_agentic_tools(include_copilot=True),
)

assert all(decision.locked for decision in decisions)
```

## Completion Rule

A task is not complete at commit, push, PR creation, or auto-merge.

It is complete only when:

1. local gates pass,
2. PR exists with evidence,
3. GitHub checks finish green,
4. merged commit is visible on `origin/main`,
5. local `main` is synced,
6. feature branch is pruned,
7. final local smoke still passes.

That is operation fullness. Anything earlier is a stage, not completion.
