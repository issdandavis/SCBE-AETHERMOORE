# Agentic Vine Branch Workflow

Status: operating model.
Last updated: 2026-05-23.

This workflow keeps agentic Git work from turning into overwritten, compartmentalized branches. The model is not a traditional tree where each branch grows away from the trunk until merge day. It is closer to bamboo, bonsai, and vines: repeated nodes, living rings, visible roots, and flowers that map back to the root that fed them.

## Core Idea

Every agent branch must preserve a root-to-flower map:

```text
root intent -> branch lane -> action node -> verification ring -> merge flower -> cleanup/root update
```

The branch is not a private compartment. It is a temporary growth node on the shared system.

## Branch Lanes

| Lane | Prefix | Purpose | Merge condition |
| --- | --- | --- | --- |
| Feature vine | `feat/` | New behavior or new executable system surface. | Tests prove behavior and docs show how to use it. |
| Fix vine | `fix/` | Repair a broken behavior or CI failure. | Failing check turns green and regression exists where practical. |
| Style/format ring | `style/` | Formatting, lint, import cleanup, no behavior change. | Format/lint jobs pass; diff is mechanical. |
| Docs flower | `docs/` | Public/operator docs, claim fences, runbooks. | Claim status is clear; no unverified claim promoted. |
| Experiment shoot | `exp/` | Fenced R&D, prototype, measurement probe. | Explicit status says experimental; not merged into canonical architecture without evidence. |
| Bench ring | `bench/` | Benchmark harness, scorecard, evidence packet. | Score is reproducible or explicitly marked as smoke/planned. |

## Standard Agent Verbs

Agents should use the same verbs for every branch:

| Verb | Meaning | Required output |
| --- | --- | --- |
| `inspect` | Read current branch, dirty tree, PR state, relevant files. | Branch name, changed paths, open PR if any. |
| `pull` | Sync the root before adding new growth. | Confirm `main` or base ref is current. |
| `sprout` | Create a scoped branch from the correct root. | Branch name with lane prefix. |
| `shape` | Make the smallest useful change. | Changed file list. |
| `triage` | Convert failures into cause + next action. | Failure mode and recovery command. |
| `format` | Run repo formatting/lint gates before review. | Commands and pass/fail. |
| `review` | Check the diff against claim scope and tests. | Risk notes and missing evidence. |
| `push` | Push the branch and open/update PR. | PR number and URL. |
| `flower` | Merge only after checks are green or auto-merge does it. | Merge commit or PR state. |
| `prune` | Delete merged branch and sync local root. | Clean branch status. |

## Root-To-Flower Packet

Every non-trivial PR should be explainable as:

```json
{
  "root_intent": "what problem this branch solves",
  "branch_lane": "feat|fix|style|docs|exp|bench",
  "changed_paths": ["..."],
  "verification": ["commands that passed"],
  "claim_fences": ["what this does not prove"],
  "recovery_path": "what to run or revert if it fails",
  "merge_flower": "PR number or merge commit"
}
```

This is the branch version of the Aether Programmer Index: passes have quality; failures have solution paths; negative exploration is allowed only when recovery is visible.

## Vine Rules

1. Do not start from a stale root unless the point is conflict resolution.
2. Do not mix unrelated flowers on one vine. If a formatter fix follows a feature merge, use a `style/` ring branch.
3. Do not overwrite another agent's unmerged work. Inspect first, then branch from the right root.
4. Do not treat auto-merge as completion. Check the late CI status after merge.
5. Do not delete local evidence branches until the merge commit is visible on `origin/main`.
6. Do not promote experimental branches into canonical docs without an evidence gate.
7. Keep branch names boring enough for agents to route: `feat/aether-programmer-index`, `style/black-nsm-after-programmer-index`, `docs/vine-branch-workflow`.

## Bamboo Node Pattern

For multi-agent work, use short stacked nodes instead of one huge branch:

```text
docs/research-claim-gate
  -> style/python-lint-after-nsm
  -> feat/aether-programmer-index
  -> style/black-nsm-after-programmer-index
  -> docs/vine-branch-workflow
```

Each node is small. The system keeps growing because each node leaves the root cleaner for the next node.

## NSM / Experimental Work Fence

NSM geometric outputs such as row/column heat maps, phi-extrapolated empty sites, or "INSIDE -> HAVE" style matches are structural predictions from the current geometry. They are not proven semantic facts by themselves.

Allowed language:

- "The current NSM geometry predicts this slot."
- "This is a candidate sub-prime family."
- "This local run ranks the gap as high confidence."

Not allowed without external evidence or additional validation:

- "The geometry proved the semantic relationship."
- "This is publishable" as a standalone claim.
- "Wierzbicka left this unaddressed" without a citation and careful wording.

Experimental vines can be rich. Canonical flowers need evidence.
