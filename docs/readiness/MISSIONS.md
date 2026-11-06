# Recurring missions

[Live mission board](https://github.com/issdandavis/SCBE-AETHERMOORE/issues/2905) · [Catalog](mission_catalog.json) · [Deployment guide](README.md)

These missions recur like a game mission board: finish one cycle with evidence, then the next cycle
becomes due. They are ongoing maintenance obligations, not a checklist that permanently turns green.
“Bi-yearly” is interpreted here as **every six months**. Annual reviews remain separate.

## Mission menu

| ID | Mission | Recurrence | Objective | Typical effort |
| --- | --- | --- | --- | --- |
| OPS-01 | Watchtower | weekly | Reconcile CI, scheduled checks, incidents, and deployed versions. | 30 minutes |
| SEC-01 | Patch Patrol | weekly | Triage dependency updates and the existing rolling security scan. | 30 minutes |
| HIS-01 | Change Chronicle | monthly | Catalog the previous complete calendar month and explain how landed changes moved the system. | 60 minutes |
| REP-01 | Companion Sync | monthly | Reconcile source ownership, companion versions, extraction drift, and submodule pins. | 45 minutes |
| DR-01 | Restore Point | quarterly | Restore state and roll back a release in an isolated environment. | 90 minutes |
| KEY-01 | Keyring Review | quarterly | Review service identities, signing keys, scopes, expiry, revocation, and rotation procedure. | 60 minutes |
| EVAL-01 | Sensor Calibration | quarterly | Measure neural sensors and valence decisions against independent held-out cases. | 90 minutes |
| SEC-02 | Security Season | Every six months | Review attack boundaries across API, cryptography, browser, agents, storage, and billing. | half day |
| HIS-02 | History Expedition | Every six months | Review six months of changes, release provenance, old secrets, and architecture drift. | half day |
| ARC-01 | World Map Review | annual | Reconcile architecture, contracts, maintainers, supported runtimes, and archive decisions. | half day |
| SUP-01 | Supply and Recovery Review | annual | Review supply chain, licensing, provenance, recovery ownership, succession, and operating cost. | half day |
| REL-01 | Release Boss Gate | event | Approve one named deployment profile at one immutable revision before every release. | per release |
| INC-01 | Incident Response | event | Respond to compromise, data loss, or a severe regression immediately. | immediate |

## State and recurrence rules

1. The board lists every mission and its due date. Initial baseline reviews are due 2026-10-07
   until matching existing evidence is inspected; reuse valid work rather than doing it again.
2. Use at most one open issue per mission ID. A later due cycle updates the same unresolved issue.
   At most three new mission issues are created per controller run; all overdue work remains
   visible on the board. Incidents/release blockers come first, then security/recovery, then oldest due.
3. A mission moves due → active → evidence review → completed. Blocked is an explicit state with
   an owner and dependency. “Closed as stale” and “not planned” are not successful completion.
4. Completion requires evidence URLs, an outcome, a reviewer, completed_at and next_due.
   Weekly missions recur seven days after verified completion. Monthly/quarterly/semiannual/annual
   missions recur 1/3/6/12 calendar months later; clamp to the last valid day when needed.
5. HIS-01 reviews the previous complete calendar month using exact commit bounds, even if completion
   happens late. Track uncovered intervals separately so a delayed review cannot skip a month.
   HIS-02 covers the previous six complete months. REL-01 and INC-01 are event gates, not calendar waits.
6. The maintainer owns the catalog until a mission issue records a delegate. Automation can gather
   evidence and open work; it cannot manufacture approval or mark missing tests as passing.
7. Keep the board and recurring issues labeled enhancement, security, or another configured stale
   exemption. The current stale workflow exempts these issue labels. Verify labels after creation.
   Reopen accidental stale closures; record whether the work was actually completed.
8. Successful useful inputs, benign anomalies and confirmed attacks are separate evaluation sets.
   Useful evidence can improve regression tests after review. Do not auto-train, expand tool
   permissions or lower thresholds merely because a mission collected a new observation.

## Controller and persistence

A companion hosted task checks this GitHub board weekly and uses the versioned catalog to surface due
missions, reconcile evidence and prepare monthly history reviews. It reuses existing Actions evidence.
The task is separate from GitHub Actions: it depends on the connected GitHub app and an enabled task.
Its activation/last successful run is recorded on the live board; a stale board is UNKNOWN, not healthy.

Until the documentation PR is merged, the controller reads the published PR branch linked from the
board. After merge, main is authoritative. Preserve prior human edits and issue links. If the catalog
is missing or the source cannot be verified, report the gap instead of silently replacing the rules.

If the task is unavailable, the maintainer follows the same table manually. An enabled schedule is
not proof that every review ran. The weekly controller reports its last successful run and any
missed mission intervals. The maintainer should inspect this heartbeat monthly through normal
repository review; task failure cannot reliably notify through the failed task itself.

No new Actions cron workflow is introduced by this guide. GitHub scheduled workflows run from the
default branch and can be delayed; public inactive repositories can have schedules disabled.
Review [GitHub's documented schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
when investigating missing evidence.

## Existing scheduled work to reuse

These are configured schedules observed at the reviewed main SHA, not proof of recent success.
Times below are UTC from the workflow files.

| Existing workflow | Configured cadence | Mission use |
| --- | --- | --- |
| daily-secret-scan.yml | Daily 05:30, plus event triggers | SEC-01 / SEC-02; completed scan receipt, restricted handling of findings |
| weekly-security-scan.yml | Monday 06:00 | SEC-01; update existing “Security Scan - rolling” issue |
| secret-rotation-audit.yml | Sunday 03:00 | KEY-01; audit is not itself key rotation |
| codeql.yml | Sunday 21:29, plus event triggers | SEC-01; review actual analysis coverage/results |
| workflow-audit.yml | Monday 03:00 | OPS-01 / SEC-02 |
| nightly-python-full.yml | Daily 09:17 | OPS-01 / REL-01 |
| scbe-tests.yml | Sunday 03:00 | OPS-01 / REL-01 |
| weekly-repo-health.yml | Monday 06:00 | OPS-01; automatic closure of older reports is not verified completion |
| daily-repo-stats.yml | Daily 05:00 | HIS-01 supporting activity signal, not behavioral interpretation |
| weekly-link-check.yml | Monday 07:00 | P5 / OPS-01 |
| stale.yml | Daily 01:30 | Issue housekeeping; exempt the mission board |
| cloud-kernel-data-pipeline.yml | Monday 06:30 | Training profile only; data permissions and budget still required |
| overnight-pipeline.yml | Daily 10:00 | Active training/data profile only |
| weekly-hf-sync.yml | Monday 06:00 | Dataset profile only; do not publish unreviewed private data |
| website-betterment-automation.yml | Daily 10:35 | P5; review resulting content/proposals |
| weekly-gov-contracts-check.yml | Monday 06:00 | Business tracking; does not certify technical compliance |

Source directory: [.github/workflows](../../.github/workflows/). Link each review to the actual run
and its artifact, not merely the workflow definition. Missing scan reports and skipped critical tests
are unknown evidence. Existing rolling security issues should be reused rather than duplicated.

## Mission issue template

Title: [MISSION-ID] Mission name — cycle YYYY-MM-DD

~~~text
Profile / sections:
Owner:
Due:
Status: due | active | blocked | evidence review | completed
Scope and exact repo / commit / artifact:
Previous completed cycle:
Objective:
Evidence required:
Actual evidence URLs:
Findings and affected behavior:
Blocker / dependency / risk owner:
Acceptance result:
Reviewer:
Completed at:
Next due:
Follow-up issue(s):
~~~

Public issues contain redacted findings, hashes and links. Do not paste customer inputs, private
repo content, credentials or raw secret-scanner matches. Severe incidents use the repository's
security reporting process with a redacted pointer on the board.

## Evidence and acceptance by mission

### OPS-01: Watchtower

Evidence: Run URLs and timestamps; deployed SHA or explicitly unknown; owner for every failed or stale check.

Complete when: Every active profile has a current status; unknown is never green.

### SEC-01: Patch Patrol

Evidence: Completed scanner reports, updater failures, findings with severity/owner/due date or reviewed risk acceptance.

Complete when: Missing reports are UNKNOWN; reuse Security Scan - rolling instead of creating duplicate scan issues.

### HIS-01: Change Chronicle

Evidence: Excluded base and included head SHAs; complete Markdown/JSON catalogs; behavior/contract changes; unresolved deployment evidence.

Complete when: Separate landed commits, unmerged proposals, package releases, and deployed revisions; cover each activated companion separately.

### REP-01: Companion Sync

Evidence: Active dependency graph, repository/commit or artifact digest, compatibility receipt, owner and archive status.

Complete when: Each active dependency has one canonical implementation; archived pointers are resolved or the affected profile stays blocked.

### DR-01: Restore Point

Evidence: Backup ID, restore log, data/hash validation, elapsed time, measured RPO/RTO, rollback result.

Complete when: Recovered data and service behavior verified; a backup existing is insufficient.

### KEY-01: Keyring Review

Evidence: Redacted inventory of key IDs/owners/scopes; revocation and rotation drill; access review.

Complete when: No orphan credentials or unexplained privilege; rotate on compromise immediately, not only on the calendar.

### EVAL-01: Sensor Calibration

Evidence: Runtime/model/schema/dataset hashes; false positives/negatives by class; missing/NaN/replay/drift cases; threshold rationale.

Complete when: Benign drift and attacks evaluated separately; observations cannot silently update production models or trust.

### SEC-02: Security Season

Evidence: Updated threat model; negative authorization/replay/tamper tests; real-backend receipts; findings with owners.

Complete when: Critical findings resolved or deployment blocked; review scope and residual risk recorded, not a certification claim.

### HIS-02: History Expedition

Evidence: Six monthly catalogs; release/tag/deployed-SHA crosswalk; historical scan completion; migration/deprecation decisions.

Complete when: Every included interval has exact boundaries; no missing shallow history; no force-push or destructive history cleanup.

### ARC-01: World Map Review

Evidence: Current source map; profile-level dependency graph; contract/schema versions; named ownership and support windows.

Complete when: Code, documentation, released artifacts, and actual deployment profiles agree or have tracked gaps.

### SUP-01: Supply and Recovery Review

Evidence: SBOM/license review; upstream maintenance status; artifact provenance; recovery/access continuity drill; cost review.

Complete when: Active products have supported dependencies and a tested recovery owner; claims stay within measured evidence.

### REL-01: Release Boss Gate

Evidence: Exact commit and artifact digest; CI; installed-artifact tests; backend/auth/negative tests; target-host receipt; rollback.

Complete when: All gates in README pass for that profile; missing evidence prevents promotion.

### INC-01: Incident Response

Evidence: Containment timeline, redacted evidence, affected revisions, owner, recovery and follow-up verification.

Complete when: Containment and recovery verified; lessons create reviewed regressions; do not wait for a recurring mission.

## First-cycle priorities

- [REL-01 / P3, issue #2906](https://github.com/issdandavis/SCBE-AETHERMOORE/issues/2906): fix the missing agent-bus dependency in Dockerfile.api and prove clean-image startup.
- [REP-01 / P4, issue #2907](https://github.com/issdandavis/SCBE-AETHERMOORE/issues/2907): resolve the archived scbe-agents ownership loop before a full agent/MCP deployment.
- [SEC-01 / OPS-01, issue #2908](https://github.com/issdandavis/SCBE-AETHERMOORE/issues/2908): triage current updater failures and verify completed scanner artifacts.
- REP-01 / P2: resolve standalone browser provider/echo fallback and WebSocket authorization before exposure.
- HIS-01: the September main catalog and partial October checkpoint are attached; main interpretation is
  complete for those explicit bounds, while activated-companion catalogs and release/deployment crosswalks
  remain due. Do not mark the entire mission complete just because one catalog exists.
