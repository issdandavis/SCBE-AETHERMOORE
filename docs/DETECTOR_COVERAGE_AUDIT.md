# Detector Coverage Audit

**Date:** 2026-06-11 · **Scope:** every enforcement point in the repo · **Status:** local working doc

## The axiom under audit

> "You either find out they get broken or followed, or you don't. If you don't, you have failed the user."

A rule's failure mode is not violation — it is **undetected** violation. So every enforcement
point must answer one question: *if this rule were broken, bypassed, or silently disabled,
what durable channel would tell us?* This repo's own history is the case for the audit:
ring-descent ran fail-open with a test blessing the bug; GeoSeal's recursive-delete regex was
dead for months; L13's SNAP tier is unreachable. All three were "we didn't find out" failures
caught only by manual archaeology.

## Rubric

| Verdict | Meaning |
|---|---|
| **WITNESSED** | Violation/denial automatically produces a durable record (file/ledger/chain) |
| **PARTIAL** | Durable record possible but conditional, optional, or caller's responsibility |
| **BLIND** | In-memory verdict / raised exception only — process exit erases all evidence |
| **DEAD-LETTER** | Durable evidence is produced or producible, but nothing consumes it |

**Liveness column:** does any test assert the deny *fires AND is recorded*? (The ring-descent
lesson: a test that asserts the wrong thing is worse than no test.)

## Zone A — Geometry gates (the island's water)

| Enforcement point | Location | Verdict | Notes |
|---|---|---|---|
| L13 tier decision (ALLOW/REVIEW/DENY on d*) | `fourteen_layer_pipeline.py:596` | **BLIND** | Returns `RiskAssessment`; persistence is caller's problem |
| L4 boundary quarantine (ball-edge bump) | `fourteen_layer_pipeline.py:880` | **BLIND** | Folded into d*; no record that the bump fired |
| `/v1/governance/scan` DENY | `src/api/main.py:620-635` | **PARTIAL** | Increments in-memory `metrics_store.total_denials`; gated `/metrics` endpoint; **lost on restart** |
| `/retrieve-memory` DENY → noise | `src/api/main.py:1046-1061` | **PARTIAL** | Same in-memory counter; fail-to-noise has no attempt-witness |
| L14 audio axis (decodes risk from sound) | `fourteen_layer_pipeline.py:652` | **DEAD-LETTER** | Proven to carry the decision (layer_role_bench) — no consumer or recorder exists |

## Zone B — Execution gates (the drones' hard rules)

| Enforcement point | Location | Verdict | Notes |
|---|---|---|---|
| GeoSeal exec gate (deny dangerous commands) | `src/crypto/geoseal_execution_gate.py:380` | **PARTIAL → best-wired gate in repo** | Sealed HMAC audit to `.scbe/geoseal_exec_audit.sealed.jsonl`, called by gate + 3 CLI sites. BUT `append_sealed_exec_audit` **silently returns False with no secret env** (`:251-252`) — no unsealed fallback, no warning. `audit_written` flag is honest if anyone reads it |
| RuntimeGate (flow run-next DENY-block) | `src/governance/runtime_gate.py` | **PARTIAL** | Receipt *signals* feed an in-memory accumulator (`:1110,1119`); durable only via `scbe flow` workspace receipts. Direct/library callers get no witness |
| Agent-bus workspace audit chain | `packages/agent-bus`, lineage reader `agent-bus-py/.../lineage.py` | **WITNESSED** | JSON receipts at `receipt_path`, incl. `gate_decision` + trap_dispatch; the exemplar the other gates should copy |
| Pre-commit secret scan | `scripts/hooks/pre-commit:100-109` | **PARTIAL** | Terminal print only; `--no-verify` bypass is locally undetectable; CI `security-checks.yml` is the only backstop |
| Sacred Eggs ring descent (fail-closed) | `src/crypto/sacred_eggs.py` | **PARTIAL** | Fail-to-noise denies correctly (3 regression tests) but a failed descent attempt leaves **no attempt record** |
| Aether MFA escalation bridge | `packages/aether-mfa/` | **PARTIAL** | Holds QUARANTINE→MFA (22 tests); approvals/denials in memory, no durable approval log |

## Zone C — API surface (the portals)

Scout-verified (file:line per scout report). The pattern is uniform: **raise-and-forget**.

| Enforcement point | Location | Verdict | Notes |
|---|---|---|---|
| `verify_api_key` 401 — six route families | `main.py:604`, `hydra_routes.py:109`, `llm_routes.py:28`, `free_llm_routes.py:58`, `saas_routes.py:50`, `geoseal_service.py:89` | **BLIND** | HTTPException only; `logging.getLogger("scbe.api")` has **no file handler**. Zero durable record of any auth failure, ever |
| Rate limiter 429 | `main.py:205-215` | **BLIND** | In-memory window; denials not even counted in metrics (successes are) |
| `SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK` bypass | `stripe_billing.py:331-335` | **BLIND — worst in repo** | Signature verification skipped with **zero log, zero record, zero test**. A prod deploy with this flag set is undetectable from inside the system |
| `SCBE_ALLOW_DEMO_KEYS` fallback | `auth_config.py:43-45` | **PARTIAL** | One startup `logger.warning`, never repeated, no file handler — demo keys live in prod would surface nowhere |
| Owner token 401 (`/billing/purchases`) | `stripe_billing.py:119-123` | **BLIND** | No record of attempts |
| Connector signing key unset → unsigned payloads | `main.py:746-754` | **PARTIAL** | Startup warning only; per-dispatch unsigned sends unrecorded |
| Agent mismatch 403, goal/connector ownership 404s | `main.py:1069,1446,1536-1611` | **BLIND** | No record of cross-agent/cross-owner probing — exactly the recon you'd want to see |

## Zone D — Agent fleet (the drones themselves)

Scout-verified. Every gate returns a verdict object; **none writes anywhere**.

| Enforcement point | Location | Verdict |
|---|---|---|
| Antivirus membrane verdicts + turnstile actions | `agents/antivirus_membrane.py:90-156` | **BLIND** |
| Kernel gate KILL/HONEYPOT/`block_execution` | `agents/kernel_antivirus_gate.py:261-276` | **BLIND** |
| Extension gate permission lockdown | `agents/extension_gate.py:171-248` | **BLIND** |
| Hyperbolic scanner QUARANTINE | `agents/hyperbolic_scanner.py:37` | **BLIND** |
| PQC key auditor QUARANTINE | `agents/pqc_key_auditor.py:41-65` | **BLIND** |
| Browser agent quarantine queue + action log | `agents/browser_agent.py:512-551` | **BLIND** (in-memory list/queue, lost on exit) |
| HYDRA turnstile HONEYPOT escalation | `hydra/turnstile.py:52-58` | **BLIND** (advisory) |
| **HYDRA Ledger** — SQLite, HMAC-signed, thread-safe | `hydra/ledger.py:248-285` | **DEAD-LETTER** | Fully built tamper-evident ledger; **zero enforcement gates call it** |

## Score

~24 enforcement points audited: **1 WITNESSED · 8 PARTIAL · 13 BLIND · 2 DEAD-LETTER cameras**
(hydra Ledger, `src/util_logging.py` JSONL infra — both built, both unwired; L14 audio a third).

## Headline findings

1. **The cameras exist; they are not wired to the gates.** A signed SQLite ledger
   (`hydra/ledger.py`), a JSONL logging utility (`src/util_logging.py`), a sealed audit
   appender (GeoSeal), and a working receipt chain (agent-bus) all exist. 13 of 24 gates
   write to none of them.
2. **Bypass flags are invisible.** `SCBE_ALLOW_UNSIGNED_STRIPE_WEBHOOK` disables signature
   checking with no record at all; `SCBE_ALLOW_DEMO_KEYS` warns once at startup. Per the
   axiom, these are pre-failed: if abused, we structurally cannot find out.
3. **Auth probing is unrecordable.** Every 401/403/429 across six route families evaporates.
   An attacker enumerating keys, owners, or agents leaves no trace by design.
4. **Tests bless verdicts, not witnesses.** Deny-path tests assert the decision value; none
   asserts a record was written. The ring-descent bug pattern, system-wide.
5. **GeoSeal's silent skip.** The best-wired gate still drops its witness silently when the
   audit secret env is missing (`return False`) instead of writing unsealed or warning.

## Ranked fixes (cheap → structural)

1. **One witness sink** — a `gate_witness(record)` helper (JSONL via `util_logging`, optional
   hydra-Ledger backend) called from every deny/quarantine/bypass path. The fleet gates need
   one line each; the API needs it in the HTTPException path for 401/403/429.
2. **Loud bypass flags** — every *use* (not just startup) of an `SCBE_ALLOW_*` override emits
   a witness record + ERROR log. ~10 lines total across 3 files.
3. **GeoSeal no-secret fallback** — write an unsealed record rather than nothing; never skip
   silently.
4. **Witness liveness tests** — extend each existing deny-path test with "and a witness row
   exists." Turns this whole audit into CI.
5. **Persist the denial metrics** — flush `metrics_store` counters to JSONL on increment or
   shutdown.

## Verification notes

Verified live by me: GeoSeal audit conditionality + callers, RuntimeGate in-memory receipts,
pre-commit behavior, L13/L14 (foliation probe + layer_role_bench). Scout-verified with
file:line: Zones C and D (two read-only Explore agents, reports 2026-06-11). From memory with
tests: agent-bus receipts, MFA bridge, Sacred Eggs fail-to-noise.
