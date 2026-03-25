# 2026-03-24 Stability Guardrails

## Purpose

The system is no longer just a codebase. It can now publish, send outreach, update docs, and create external state.

The correct operating mode after that threshold is:

- high observability
- bounded automation
- explicit invariants
- narrow blast radius

This file defines the default guardrail mode until a stricter release harness exists.

## Reported current state

Reported in the session wrap on 2026-03-24:

- PR `#709` open
- `3` code-scanning alerts open
- `7` Bluesky posts live
- `2` outreach emails sent
- book live on Amazon
- chapters `1-3` free on GitHub Discussions `#704-706`
- publishing CLI working
- CI auto-fix active

Treat these as reported state until re-verified in a dedicated verification pass.

## Invariants

These must not change automatically.

1. Governance docs must not drift away from implementation behavior.
2. CI auto-fix must not modify security-critical files without human review.
3. Publishing commands must not post from unvalidated or unknown state.
4. Product manuals, delivery text, and actual bundles must describe the same package contents.
5. Auth, licensing, usage metering, and payment-adjacent logic require explicit human approval before mutation.
6. Workflow recursion or repeated posting loops must be treated as defects, not convenience.

## Security-critical change zones

The following zones are not safe targets for blind auto-fix:

- `src/crypto/`
- `api/`
- `aws/`
- `src/licensing/`
- payment links and checkout routes
- auth headers, API key extraction, or token handling
- publishing credentials and outbound automation rules

## Allowed automation scope

Automation is allowed by default only in these lower-risk categories:

- documentation wording
- non-security formatting cleanup
- test-only hygiene cleanup
- generation of reports, snapshots, inventories, and decision records
- dry-run publishing previews
- observability exports

## Guardrail mode

Until the next explicit release checkpoint, the system should be treated as running in `observability-first` mode.

### CI

- allow detection and reporting
- allow auto-fix only on bounded non-security categories
- block silent mutation of security-critical files

### Publishing

- allow manual command-triggered posts
- do not enable unattended repeating post loops
- require a single source page or offer target per campaign

### Outreach

- allow manually triggered sends
- do not auto-enroll new targets from scraped or inferred sources
- keep message families versioned

### Site

- deploy deterministic content only
- do not let stale docs or archive text become current buyer copy

## Release-valid state

A state is considered release-valid only if all of the following are true:

- open PR set is understood
- code-scanning state is understood
- live publishing surface is understood
- buyer manuals and local bundle agree
- support email and delivery path agree
- no recursive workflow trigger is active

## Minimal daily observation pass

1. Check open PRs.
2. Check code-scanning alert count.
3. Check last publishing actions.
4. Check whether manuals and bundle version still agree.
5. Check whether any automation touched a protected zone.

## Near-term stabilization tasks

1. Merge or resolve `#709` deliberately.
2. Clear or verify the remaining `3` code-scanning alerts.
3. Add a stronger release-state checklist before future automated publishing expansion.
4. Keep buyer bundle and manual surfaces versioned together.
