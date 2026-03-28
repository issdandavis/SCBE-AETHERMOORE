# GitLab Pond Integration (SCBE)

This repo uses GitLab as a second “pond” (lore/research/evidence) alongside GitHub (code/product). The value is the **flow**, not consolidation.

## Secrets (never commit)

- GitLab token lives in: `config/connector_oauth/.env.connector.oauth`
- Variable name: `GITLAB_TOKEN`
- All scripts read the token locally and never print it.

## Meridian flush (read-only)

Purpose: detect “blockages” cheaply before spending full energy on debugging or pushes.

```powershell
pwsh -NoProfile -File "scripts/gitlab/pond_flush.ps1" `
  -GitLabRepoUrl "https://gitlab.com/<group>/<project>.git" `
  -CheckGhAuth
```

What it checks:

- local time + timezone (for audit coherence)
- token validity (`/api/v4/user`)
- project reachability (`/api/v4/projects/:id`)
- optional `gh auth status`

## Mirror push (GitHub -> GitLab)

Purpose: push the local repo state into a GitLab repo without exposing tokens.

```powershell
pwsh -NoProfile -File "scripts/gitlab/mirror_push.ps1" `
  -GitLabRepoUrl "https://gitlab.com/<group>/<project>.git" `
  -Branch "main"
```

Full mirror (rare):

```powershell
pwsh -NoProfile -File "scripts/gitlab/mirror_push.ps1" `
  -GitLabRepoUrl "https://gitlab.com/<group>/<project>.git" `
  -PushAllBranchesAndTags
```

## Smoke test (create/find project, flush, push, verify)

This is the fastest “both ends” validation:

```powershell
pwsh -NoProfile -File "scripts/gitlab/smoke_test.ps1" `
  -ProjectName "scbe-pond-mirror-test" `
  -Visibility "private" `
  -Branch "mirror-smoke"
```

Optional flags:

- `-SkipCreate` (fail if project doesn’t exist)
- `-SkipPush` (read-only smoke)
- `-CheckGhAuth` (prints `gh auth status`)

## Self-healing notes

- `GitLab Auth: FAIL`: token missing/expired/scope wrong. Fix `GITLAB_TOKEN` in the env file.
- `Project not found`: wrong path or token lacks access. Verify group/project path.
- `git push` fails: script sanitizes errors; rerun pond flush to ensure the target repo is reachable.

## Known limitations (current)

- `mirror_push.ps1` authenticates git-over-HTTPS by embedding the token in the remote URL (`https://oauth2:<token>@…`). This is the simplest working method, but it can leak via process argv inspection or shell history. Errors are sanitized, but argv exposure still exists.
- `smoke_test.ps1` now emits a `SUMMARY_JSON=...` line; it is not yet a formal schema used by CI.

## Improvement backlog (next hardening)

- Prefer a non-argv auth mechanism (Git Credential Manager / askpass) to avoid token-in-URL entirely.
- Standardize milestone strings (`Auth OK`, `Project OK`, `Pond Flush OK`, `Mirror Push Done`, `Verify OK`) for easy log assertions.
- Add explicit branch-tip equality check (remote tip SHA == local HEAD) for verify.
- Add retry/backoff around GitLab API calls.

## Where this fits with the GitHub skills

- If a PR’s CI is failing, do a pond flush first if the change involved mirroring/lore/evidence.
- If PR review asks to “move long evidence off GitHub Pages”, keep canonical long-form in GitLab and publish a stable excerpt + entrypoint on GitHub Pages.
