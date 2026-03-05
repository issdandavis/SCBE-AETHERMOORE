# 2026-03-04 Dual-Side Loop Self-Improvement Plan

Owner lane for this draft: `Worker C / Skill-Corkscrew`

## Objective

Create a compact, repeatable dual-side multi-agent loop with strict composition contracts and explicit approval gates so verification and implementation stay synchronized.

## Composition Contract

1. Two-side model:
   - Side A (`Build/Execution`): implement scoped changes in owned files only.
   - Side B (`Verification/Self-Improvement`): verify skills/tooling, check gates, and publish improvement notes.
2. Required packet for every worker update:
   - `callsign`
   - `ownership`
   - `intent`
   - `files_touched` (absolute paths)
   - `commands_run` (or `none`)
   - `result_state` (`done`, `blocked`, `needs-approval`)
3. Ownership guardrails:
   - No edits outside declared owned files.
   - Ignore unrelated worktree edits.
   - Escalate immediately with exact blocker if ownership collision occurs.
4. Evidence minimum:
   - At least one command-level proof for each verified claim.
   - For skill claims: include `SKILL.md` path evidence and tooling output evidence.

## Approval Gates

1. Gate A - Scope Lock:
   - Confirm task, owned files, and forbidden actions.
   - Fail condition: ambiguous ownership or install/write request without approval.
2. Gate B - Pre-Action Control:
   - For install/overwrite/publish actions, require explicit user approval.
   - If no approval, remain in verification/report mode only.
3. Gate C - Post-Action Evidence:
   - Attach command evidence and output summary for each task objective.
   - Fail condition: claim without reproducible command trace.
4. Gate D - Merge-Ready Review:
   - Verify deliverable includes summary, blockers, and recommended next loop.
   - Fail condition: missing next-loop contract updates.

## Next Loop Template (Compact)

1. Re-run skill availability verification at loop start.
2. Compare with previous loop snapshot and flag drift.
3. Execute scoped task work under Gate B constraints.
4. Publish lane report with command evidence and gate pass/fail matrix.
5. Record one concrete process improvement for the following loop.

## Immediate Recommendations

1. Standardize a shared worker report schema across all lanes this sprint.
2. Add a binary `approval-required` field to every operation packet.
3. Keep one rolling `gate failures` section so repeated blockers become automation targets.
