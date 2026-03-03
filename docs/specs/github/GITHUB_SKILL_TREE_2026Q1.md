# GitHub Skill Tree (2026 Q1)

Status: Draft  
Scope: SCBE-AETHERMOORE GitHub operations and release automation

## Why This Tree

Build a single GitHub-first capability map so agents can execute repo operations without context thrash, especially around CI, reviews, and releases.

## Research Snapshot (GitHub Releases)

This tree is aligned to current GitHub release surfaces:

1. GitHub release workflow and generated release notes are first-class release features.
2. Release publication can be automated from GitHub Actions.
3. Release discussions can be enabled to centralize feedback.
4. Immutable releases are now part of the GitHub release model and should be treated as a hardening option.

Primary references:

- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes
- https://docs.github.com/en/actions/tutorials/create-actions/create-a-composite-action
- https://docs.github.com/en/repositories/releasing-projects-on-github/linking-a-discussion-to-a-release
- https://github.blog/changelog/2025-10-23-immutable-releases-are-now-generally-available/

## Skill Tree

```text
L0 Foundation
  L1 Repo Operations
    L2 Collaboration (PR/Review/Comments)
      L3 CI and Checks
        L4 Release Engineering
          L5 Security and Compliance
            L6 Portfolio and Org Ops
```

## Layer Definitions and Skill Mapping

| Layer | Capability | Existing skills in workspace | Skill gap to add |
|---|---|---|---|
| L0 | Auth, context, repo targeting, branch hygiene | `scbe-gh-powershell-workflow`, `scbe-github-systems` | `gh-foundation-boot` |
| L1 | Branch/PR lifecycle, issue triage, repo inspection | `scbe-gh-powershell-workflow` | `gh-repo-operations-core` |
| L2 | Review handling, comment resolution, review loops | `gh-address-comments` | `gh-review-policy-gate` |
| L3 | CI failure triage, run logs, fix loops | `gh-fix-ci` | `gh-ci-root-cause-playbook` |
| L4 | Release note generation, tag strategy, publish gates | `scbe-npm-prepublish-autopublish` | `gh-release-orchestrator` |
| L5 | Provenance, dependency/security checks, audit trail | (partial via repo scripts) | `gh-security-release-guard` |
| L6 | Multi-repo coordination and execution planning | `multi-agent-orchestrator`, `multi-agent-review-gate` | `gh-org-control-plane` |

## Release-Focused Branch (Priority)

Use this branch as the first automation target.

1. `gh-release-orchestrator`  
Goal: Create and publish deterministic releases from tags with generated notes and optional release discussions.

2. `gh-security-release-guard`  
Goal: Enforce pre-release checks for dependency risk, artifact integrity, and publish policy.

3. `gh-ci-root-cause-playbook`  
Goal: Standardize failure triage into repeatable repair loops before release cut.

4. `gh-review-policy-gate`  
Goal: Require review and checklist completion before release branch merge.

## Proposed Trigger Phrases (for Skill Routing)

| Skill | Trigger examples |
|---|---|
| `gh-foundation-boot` | "setup gh for this repo", "check auth and remotes" |
| `gh-repo-operations-core` | "open PR", "triage issues", "inspect branch state" |
| `gh-review-policy-gate` | "address review comments", "enforce review gate" |
| `gh-ci-root-cause-playbook` | "why did checks fail", "fix GitHub Actions failure" |
| `gh-release-orchestrator` | "cut a release", "generate release notes and publish" |
| `gh-security-release-guard` | "run release security checks", "block unsafe publish" |
| `gh-org-control-plane` | "coordinate releases across repos", "org-wide release board" |

## Minimal Implementation Backlog

1. Add a dedicated release runbook skill scaffold:
- Name: `gh-release-orchestrator`
- Scope: tag -> release notes -> publish -> post-release verification
- Inputs: repo, tag, target branch, notes mode (auto/manual), discussion category

2. Add release guard wrapper:
- `scripts/run_release_guard.ps1` (missing today)
- Run sequence: `npm ci` -> `npm run publish:prepare` -> `npm test` -> `npm run publish:check:strict`

3. Wire workflow parity:
- Ensure `.github/workflows/auto-publish.yml` uses the same local guard sequence.
- Remove or use unused `workflow_dispatch.inputs.version`.

4. Add immutable release policy decision:
- Adopt or explicitly defer immutable releases in release governance doc.

## Current Readiness Verdict

- GitHub packaging/release automation state: **partial**
- Existing gates are good but not fully operational in clean environment without dependency bootstrap and a single release guard wrapper.
- Next best move: implement `gh-release-orchestrator` + `scripts/run_release_guard.ps1` and treat that as the L4 foundation.
