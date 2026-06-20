# Merge, CI parity, and stash playbook

Use this when landing **`feat/agent-bus-spaceready`** (or follow-on agent-bus work) and draining local **stash** queues without colliding with `main`.

## 1. Open or refresh the PR

As of the last check, there was **no open PR** with head `feat/agent-bus-spaceready`. Create one from the branch tip:

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
git fetch origin
git checkout feat/agent-bus-spaceready
git pull origin feat/agent-bus-spaceready
gh pr create --base main --head feat/agent-bus-spaceready --title "feat(agent-bus): spaceready routing, harness, GeoSeal, compliance lanes" --body-file docs/ops/PR_BODY_feat_agent_bus_spaceready.md
```

Adjust title/body if the branch scope changed. Prefer **one merge thesis** per PR; split only if review load forces it (e.g. billing vs agent-bus vs docs).

## 2. CI parity vs local skips

- **PR path (`ci.yml`)**: Node build + tests, Python via `scripts/system/run_core_python_checks.py` (curated smoke). That script includes **`tests/crypto/`** and other fixed paths—so **PQC-adjacent tests in that tree run in CI** even if you skip broader suites locally.
- **Full `pytest tests/`**: used in reusable gates / overnight workflows; not identical to the curated PR lane. If you need **full parity** before merge, run:

  ```powershell
  $env:PYTHONPATH='.'
  python scripts/system/run_core_python_checks.py
  ```

  For a broader sweep (still excludes known-heavy optional paths):

  ```powershell
  $env:PYTHONPATH='.'
  python scripts/system/run_core_python_checks.py --full
  ```

- **Crypto**: CI installs **liboqs** in `ci.yml` before Python deps—match that when debugging Linux-only failures.

## 3. Process stash@{0} and stash@{1} safely

Current naming (typical):

| Index | Message |
|-------|---------|
| `stash@{0}` | `work-in-progress/articles-bedtime-campaign-2026-04-29` |
| `stash@{1}` | `work-in-progress/hydra-tentacle-dispatch-2026-04-29` |

**Do not** `stash pop` onto a dirty tree. Recommended pattern:

1. Commit or stash current work on `feat/agent-bus-spaceready`.
2. **Branch from stash** (keeps stash intact until you verify):

   ```powershell
   git stash branch review/articles-bedtime stash@{0}
   # run tests, commit, push, open small PR or cherry-pick to main feature branch
   git checkout feat/agent-bus-spaceready
   ```

3. Repeat for `stash@{1}` with a distinct branch name (e.g. `review/hydra-tentacle-dispatch`).

After a branch is merged or cherry-picked, **drop** the stash only if empty:

```powershell
git stash drop stash@{0}
```

## 4. Post-merge hardening checklist

- **Production**: set `STRIPE_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY`, `SCBE_BILLING_BASE_URL`, `SCBE_OWNER_API_TOKEN`, and persist **`SCBE_BILLING_DB_PATH`** on durable disk (see `docs/ops/OPERATOR_SHIPPING_RAIL.md`).
- **Version bump**: when cutting a release, move `[Unreleased]` items in `CHANGELOG.md` under a dated version and align `package.json` / `pyproject.toml` per `docs/PUBLISHING.md`.

## 5. Website / profitability (optional track)

`aethermoore.com` CTA and trust copy are **out of band** for the merge train unless bundled explicitly—track as a separate PR or site branch after the feature branch is green.
