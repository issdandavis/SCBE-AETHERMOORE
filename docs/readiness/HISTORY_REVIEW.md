# Change history and movement of the system

Baseline reviewed on 2026-10-07: main at
112d5d3be200d634bb0ae3a535516742bb75b301. This review distinguishes a change landing in source
from a release being built and from that release reaching a live host.

## Initial September catalog

Reporting calendar for this first catalog: America/Los_Angeles, September 1 inclusive through
October 1 exclusive. This is an explicit reporting convention, not an assertion about hosting timezone.
The excluded base is the last first-parent landing before the interval; the included head is the
last first-parent landing within it.

- Excluded base: 8da05e527381cc92a105ca6d20db6e44992b6d88.
- Included head: 07d3e7b527e2bee0641394d9cc20761e0cbb927e.
- **49 commits / 49 first-parent landings / 174 distinct changed paths**.
- [Complete readable catalog](history/2026-09.md).
- [Machine-readable catalog with every changed path and parent SHA](history/2026-09.json).
- [GitHub comparison](https://github.com/issdandavis/SCBE-AETHERMOORE/compare/8da05e527381cc92a105ca6d20db6e44992b6d88...07d3e7b527e2bee0641394d9cc20761e0cbb927e).

Area counts overlap and are heuristic. Commit counts measure activity, not quality or readiness.
Squashed PRs appear as their landed commits; this is a main-ancestry catalog, not every abandoned
branch or every PR-internal commit. Full JSON path lists make category omissions reviewable.

## What moved in September

| Landed change | Movement of the system | Remaining readiness evidence |
| --- | --- | --- |
| [4eca43b / #2829](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/4eca43b) | Public site reframed around verifiable AI systems and an evidence ledger | Check published content against shipped features; presentation is not runtime evidence |
| [ef8ecdf / #2845](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/ef8ecdf) | Vercel Git deployment disabled as a manual publishing/cost control | Document manual owner, build receipt, rollback and published revision |
| [c1db242 / #2840](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/c1db242) | Quality checks and package-content boundaries tightened | Re-test the exact release wheel/tarball outside the source checkout |
| [7153bec / #2857](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/7153bec) | Authorization decision contracts, mathematical runtime boundaries, formal artifacts and negative tests strengthened across 63 changed files | Keep evidence tied to named runtime/formula regimes and actual deployment artifact; limited proofs do not cover every service |
| [7f9ffe2 / #2859](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/7f9ffe2) | Braid vault, signature and RWP2 authentication paths hardened across 20 changed files | Real-backend, tamper, replay and wrong-domain checks in the chosen package/container |
| [672e800 / #2879](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/672e800) | Electron preload/sidepanel bridge and extension browser API fallback repaired | Installed desktop smoke on each supported OS and approval/IPC boundary checks |
| [2314a8e / #2880](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/2314a8e) | Version 4.3.2 packaging and installed-consumer CI improve confidence in distributed artifacts | Verify actual registry artifact/version and target-host use; merged packaging does not prove publication |
| [423b09a / #2881](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/423b09a) | macOS frozen-runtime import packaging repaired | Re-run signed/packaged app launch on the supported host |
| [c3da7a7 / #2885](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/c3da7a7) | Tests aligned to binding Layer 13 refusal behavior | Treat as test alignment, not an additional runtime feature |
| Remaining catalog entries | Dependency updates, website checks, packaging/CI follow-ups and maintenance | Keep updater failures and subapp compatibility separate from feature completion |

Interpretation from the inspected changes: September moved the repo toward explicit authorization
contracts and tests of the artifacts users actually install. The largest remaining deployment gap
is proving those contracts in each selected running product, including packaging dependencies,
persistent state, provider behavior and recovery.

The workflow-consolidation merge #2784 landed August 31 and is outside this September interval.
Older source-map references calling it a draft are stale.

## Partial October catalog

This is a checkpoint, not a completed October monthly review:

- Excluded base: 07d3e7b527e2bee0641394d9cc20761e0cbb927e.
- Included head: 112d5d3be200d634bb0ae3a535516742bb75b301, committed October 6 UTC.
- **6 commits / 6 first-parent landings / 10 distinct changed paths**.
- [Readable catalog](history/2026-10-06-partial.md) and [full JSON](history/2026-10-06-partial.json).

All six subjects are dependency update changes: pip security packages/virtualenv, Fastify busboy,
Vitest toolchain, and grouped npm packages. No new deployed runtime feature is inferred from them.
Do not count this partial interval twice when the complete October report is produced.

[PR #2904](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/2904) remains a draft proposal
outside the reviewed main ancestry. Its neural Egg evidence gate must not be included as a shipped
capability or as completed production calibration.

## Generate the next catalog

Use [scripts/ops/change_catalog.py](../../scripts/ops/change_catalog.py) in a checkout with complete
history for the desired interval. It uses local Git only and never fetches, publishes, deploys, or
changes refs. Obtain missing history through the normal authorized Git workflow before generating.

~~~sh
python scripts/ops/change_catalog.py \
  --repository issdandavis/SCBE-AETHERMOORE \
  --base 8da05e527381cc92a105ca6d20db6e44992b6d88 \
  --head 07d3e7b527e2bee0641394d9cc20761e0cbb927e \
  --output docs/readiness/history/2026-09
~~~

For a new month, select new full base/head SHAs and a new output name; do not overwrite a previous
review casually. On the first-parent history, find the landing immediately before the start and the
last landing before the end. Examine timestamps/order rather than trusting a count returned by a
date-filtered query. Explicit commit boundaries are authoritative. If timestamps are non-monotonic,
document the discrepancy and the chosen landing boundary.

The utility inventories every commit reachable in base..head, marks first-parent landings, and
compares each commit's changed paths with its first parent. A side-branch commit authored earlier
can correctly appear when it first becomes reachable during the interval. Do not sum merged branch
diffs as if they were distinct net additions. The utility rejects invalid SHAs, non-ancestor ranges
and selected ranges crossing shallow boundaries; it cannot reconstruct missing history for you.

For a month with no landings, base=head is a valid zero-change report. Compare the month's head with
the previous report's head so there are no unexplained gaps. Keep companion repos in separate files
with their own boundaries; only include activated dependencies in the required monthly work.

## Human review appended to each catalog

Record the reporting interval/timezone, repo, exact boundaries, reviewer and review date. Then write:

1. What behavior, contract, trust boundary, dependency, user flow or ownership changed?
2. Which evidence was added, removed or weakened? What failures/skips remain?
3. Which package versions/tags and deployed SHAs actually contain the change?
4. What migration, rollback, compatibility or operator task follows?
5. Which changes are proposals, experiments, maintenance or archive-only?
6. Which recurring missions should be opened or carried forward?

A six-month HIS-02 review combines the monthly narratives, architecture/contract drift, release
provenance, historical secret-scan completion and deprecation decisions. Historical secrets belong
in a restricted incident process with revocation first; this guide does not authorize a force-push
or destructive history cleanup.
