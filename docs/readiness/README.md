# Live deployment readiness

Maintainer: issdandavis. Review baseline: 2026-10-07. Main revision reviewed:
[112d5d3be200d634bb0ae3a535516742bb75b301](https://github.com/issdandavis/SCBE-AETHERMOORE/commit/112d5d3be200d634bb0ae3a535516742bb75b301).

This is a living release and maintenance guide for the monorepo and its public companion products.
It is a section-by-section review of entrypoints, contracts, packaging, deployment configuration,
existing checks, and recent history. It is not a line-by-line audit or proof of a live deployment.
“Companions” means related repositories and product lanes; no legal company structure is assumed.

**Current disposition: deployment approval is pending for every profile.** CI evidence exists,
but no target-host deployment, restore drill, production credential review, or billing transaction
was performed in this review. Two main-repository blockers were found: the API image omits an imported
package, and the full HYDRA/MCP ownership pointers lead to an archived repository.

## Use this guide

- [Live mission board](https://github.com/issdandavis/SCBE-AETHERMOORE/issues/2905) — current blockers, due missions, evidence, completion dates.
- [Recurring missions](MISSIONS.md) and [machine-readable catalog](mission_catalog.json).
- [Companion map](COMPANIONS.md) — what is required, optional, archived, or unresolved.
- [History review](HISTORY_REVIEW.md) — complete commit catalogs plus changes to system behavior.
- [Publishing guide](../PUBLISHING.md) — current package release procedure.
- [Canonical system state](../CANONICAL_SYSTEM_STATE.md) — named runtime and formula authority.

The issue board is the operational record. This document is the versioned procedure and baseline.
“Reviewed” below means inspected source/configuration, not deployed or certified. “Blocked” affects
the named profile, not every product. “Pending evidence” means no supported go decision yet.

## Choose a deployment profile first

| Profile | Scope and necessary components | Current gate |
| --- | --- | --- |
| P1: package consumers | Root npm/PyPI artifacts, chosen TS/Python runtime, crypto backend needed by the consumer | Installed-artifact CI exists; verify exact release artifacts and registry contents before promotion |
| P2: local Aether Workspace | Main AetherBrowser + AetherDesk + extension/Chrome + allowlisted tools + configured model providers | Run the product release gate on the intended host; standalone browser repo is an alternative extraction, not an automatic extra dependency |
| P3: hosted API | One explicit API entrypoint, agent-bus Python package, selected storage, real crypto backend where required, auth/ingress/monitoring | **Blocked: Dockerfile.api omits the agent-bus package imported by api/main.py** |
| P4: fleet/MCP | P3 requirements as applicable, full agent/MCP runtime, selected provider adapters, dispatch policy and receipts | **Blocked: main HYDRA/MCP docs point to archived scbe-agents, whose README points back to main** |
| P5: public site/commerce/demo | Chosen site host, API if advertised, billing webhook/fulfillment if enabled, public evidence links | Verify manual publishing path, webhook delivery/replay behavior, actual customer flow and support owner |

Do not enable every submodule or deploy the whole root to satisfy one profile. A profile manifest
must record repository and SHA, entrypoint, dependency/artifact versions, model/schema/policy versions,
backend, state stores, external services, owner, rollback target, and evidence links.

## Section-by-section review

### 1. Runtime mathematics and the 14-layer profiles

Sources: [canonical state](../CANONICAL_SYSTEM_STATE.md),
[TS pipeline](../../packages/kernel/src/pipeline14.ts),
[Python reference](../../src/scbe_14layer_reference.py),
[Python full pipeline](../../src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py).

TS_PIPELINE14, PY_REFERENCE14, PY_FULL14, and PUBLIC_SCAN are distinct contracts. L11/L13 and
bounded-score versus exponential-cost regimes must be named in evidence. A passing reference
test does not establish another runtime's behavior. Before release: capture input/schema bounds,
finite-domain handling, decision precedence, negative cases, and the actual selected runtime.
Proof artifacts cover their stated formal contracts, not all application behavior. Missions: REL-01, ARC-01.

### 2. Hyperbolic embeddings, sensors, and multi-sign valence

Sources: [AI brain exports](../../src/ai_brain/index.ts),
[kernel](../../src/kernel/), [neural/crypto runtime](../../src/symphonic_cipher/),
[embedding companion](https://github.com/issdandavis/phdm-21d-embedding).

Use dH/acosh, cross-frame residuals, valence, and sensor disagreement as measurable evidence about
input and state. Freeze the exact vector layout: the main brain's documented 21D partition and the
companion README's partition differ. Reject or quarantine missing, NaN, out-of-domain, stale, or
schema-mismatched evidence; test near-boundary acosh behavior and calibrated benign drift.
Record false positives and false negatives on held-out inputs, not only aggregate accuracy.
[PR #2904](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/2904) is an open draft at this baseline;
its optional neural Egg gate is **not present on the reviewed main revision**.
Missions: EVAL-01, SEC-02, REL-01.

### 3. Sacred Eggs, braid vault, multiweave, and cross-domain checks

Sources: [Sacred Eggs](../../src/crypto/sacred_eggs.py),
[braid vault](../../src/crypto/braid_vault.py),
[tri-bundle](../../src/crypto/tri_bundle.py),
[RWP2](../../src/spiralverse/rwp2_envelope.py),
[September integrity review](../security/HASH_AND_SIGNATURE_REVIEW_2026-09-18.md).

September changes strengthened authenticated vault/signature/envelope paths. Require tamper,
wrong-domain, wrong-key, replay, missing-witness, and malformed-input tests against the shipped
implementation. Bind frame/transform identity, canonical payload, schema, policy version and session
context into authenticated bytes before accepting cross-domain agreement. Invertible transport
weaving needs an exact round trip; agreeing geometry alone cannot authorize an action. Recovery
material and witness keys need separate owners/access rules where the threat model requires it.
Missions: KEY-01, SEC-02, REL-01.

### 4. Post-quantum backends and release evidence

Sources: [backend selection](../../src/crypto/pqc_liboqs.py),
[native smoke](../../scripts/security/native_liboqs_smoke.py),
[native workflow](../../.github/workflows/pqc-native-liboqs.yml),
[release workflow](../../.github/workflows/release.yml).

Identify the algorithm and backend actually loaded inside the released artifact/container. Distinguish
native liboqs, pure implementations, and simulation. Production profiles that claim real PQC must
forbid insecure fallback and exercise real signing/verification, tamper rejection, and any KEM path
they use. The native release gate is useful evidence but is not FIPS product validation.
Dockerfile.api explicitly skips native liboqs, so a host CI receipt cannot prove native behavior in that image.
Missions: SEC-02, REL-01.

### 5. Governance, authorization, and decision contracts

Sources: [governance](../../src/governance/),
[runtime gate](../../src/governance/runtime_gate.py),
[unified gateway](../../src/gateway/unified-api.ts).

Confirm which decision enum the selected adapter supports; the gateway authorization interface and
four-way runtime decisions must not silently collapse DEFER/QUARANTINE into ALLOW. Missing policy,
timeout, scanner error, malformed evidence and unknown principal must have explicit tested outcomes.
Test direct tool calls as well as the UI route. Approval receipts must identify the action actually executed.
Missions: SEC-02, EVAL-01, REL-01.

### 6. Spatial context, voxel storage, and audit history

Sources: [voxel store](../../src/governance/voxel_store.ts),
[context grid](../../src/kernel/context_grid.py), [governance audit](../../src/governance/).

Carry the earlier reported Merkle/hash-chain concerns as **verification obligations**, not a claim
that this documentation change fixes them. Require leaf/internal domain separation, unambiguous
tree shape, full-content hashing, stored replayable timestamps, canonical lengths/serialization,
and independent re-verification. Coordinate quantization and cell-boundary drift need defined tests.
A signed/hash-linked log still needs retention, access control, rollback detection, and recovery.
Missions: SEC-02, DR-01, HIS-02.

### 7. Python API and TypeScript gateway

Sources: [api/main.py](../../api/main.py), [src/api/main.py](../../src/api/main.py),
[gateway](../../src/gateway/), [API image](../../Dockerfile.api).

The two Python entrypoints serve different contracts. Name the one being shipped and list required
routers; optional imports can leave routes absent while a health endpoint remains green.
**Static blocker:** api/main.py imports scbe_agent_bus after adding packages/agent-bus-py/src to
its search path, but Dockerfile.api only copies api/ and src/ and does not install that package.
Fix packaging, then build a clean image and prove import/startup plus a governed request.
Also verify no-auth, wrong-key, expired/replayed request, rate limit, payload limit, and concurrent
failure cases. Container startup was not attempted in this review. Missions: REL-01, OPS-01.

### 8. Durable storage and backups

Sources: [API persistence](../../api/persistence.py),
[storage factory](../../src/storage/__init__.py), [compose stack](../../docker-compose.unified.yml).

Firebase persistence can be disabled when credentials are unavailable. Filesystem sealed storage
defaults to a local directory. An HTTP health response does not establish durable audit or blob
storage. Define the selected backend, mount, retention/deletion policy, quota, permissions,
encryption/key recovery and data export. Restore a known object and its audit links into an isolated
environment; record actual recovery time and recovery point. Missions: DR-01, KEY-01, REL-01.

### 9. AetherBrowser and extension

Sources: [browser runtime](../../src/aetherbrowser/),
[serve entrypoint](../../src/aetherbrowser/serve.py),
[extension](../../src/extension/), [quickstart](../PRODUCT_QUICKSTART.md).

Review browser/CDP access, origin checks, approval binding, navigation/download permissions,
tool allowlists and provider routing. Test approval expiry, reconnect/replay, interrupted actions,
provider failure and spend limits. Default local addresses are useful boundaries, not authorization
for exposing CDP/WebSocket endpoints publicly. Choose main or the standalone companion as the
shipping source and record the extraction/sync relationship. Missions: REP-01, SEC-02, REL-01.

### 10. AetherDesk and desktop packaging

Sources: [AetherDesk](../../aetherdesk/README.md),
[product release gate](../../scripts/system/product_surface_release_gate.py),
[workspace architecture](../product/AETHER_WORKSPACE_ARCHITECTURE.md), [desktop](../../desktop/).

Run npm run product:release-gate on the target host and retain the receipt under
artifacts/product_surface/. It starts the browser/workspace, verifies health and bounded tool
execution, and shuts the surface down. Review the receipt's scope: one successful action is not all
tool or provider coverage. Test approvals, preload/IPC isolation, installed app imports, quit/restart,
and supported OS packaging. Local write-pane/product-roadmap claims require implemented evidence.
Missions: REL-01, OPS-01.

### 11. HYDRA, agent bus, and MCP

Sources: [HYDRA](../../hydra/README.md), [MCP](../../mcp/README.md),
[Python agent bus](../../packages/agent-bus-py/src/scbe_agent_bus/),
[companion declarations](../../packages/agent-bus-py/src/scbe_agent_bus/companions.py).

**Ownership blocker:** both README pointers claim the full runtime was extracted to scbe-agents;
that repository is archived and says main is canonical. Resolve a maintained entrypoint before
shipping a full fleet/MCP profile. Existing geometry/storage code and a dry-run CLI are not proof
of live swarm execution. Verify dispatch authentication, per-agent/tool scope, cancellation, retry
idempotency, quotas, isolation, and append-only action receipts. Missions: REP-01, SEC-02, REL-01.

### 12. Root packages and consumer boundaries

Sources: [publishing](../PUBLISHING.md), [package.json](../../package.json),
[pyproject.toml](../../pyproject.toml), [CI](../../.github/workflows/ci.yml).

The reviewed manifests are 4.3.2. Build tools use Node 24, with installed root consumer checks on
Node 20; current publishing documentation specifies Node 20.19+ and Python 3.11+. Do not copy older
Node 18 quickstart or historical version text into a new release contract. Build the wheel from the
sdist, install artifacts outside the checkout, and verify exports, CLI entrypoints, package contents,
licenses and exact registry bytes. Each subpackage has its own delivery contract.
Missions: REL-01, SEC-01, ARC-01.

### 13. Containers, hosting, and network exposure

Sources: [API image](../../Dockerfile.api), [root image](../../Dockerfile),
[compose](../../docker-compose.unified.yml), [shim](../../services/scbe-shim/DEPLOY.md),
[Vercel configuration](../../vercel.json).

Compose binds service ports to loopback and requires configured API/Grafana secrets; audit any
production overrides. Verify each image target's actual command and built entrypoint, TLS/ingress,
health/readiness distinction, resource limits, persistent volumes, observability, cost caps, and
rollback digest. Vercel automatic Git deployment is deliberately disabled; document who runs the
manual release. Cloud Run, shim, HF Space, tunnel, and local compose are separate optional profiles.
No hosting console or deployed endpoint was inspected. Missions: REL-01, DR-01, OPS-01.

### 14. Public site, payments, and fulfillment

Sources: [site](../index.html), [Stripe webhook](../../api/billing/stripe_webhook.js),
[Netlify functions](../../netlify/), [product launch checks](../../scripts/system/product_launch_readiness.py).

Verify the public offer maps to an actually available product/version. Test signed raw-body webhook
handling, invalid/old signatures, duplicate delivery, persistent fulfillment idempotency, failed
dispatch/retry, customer access and refund/revocation in a test environment. The current webhook
intends to acknowledge a valid signature even when dispatch fails: prove a durable retry/repair path.
Link/offer checks alone do not establish payment or delivery readiness. Missions: REL-01, DR-01, SEC-02.

### 15. Training, datasets, and model updates

Sources: [training](../../training/), [training data](../../training-data/),
[research](../../research/), [embedding companion](COMPANIONS.md).

Keep model, dataset, policy and preprocessing versions in each evaluation receipt. Track provenance,
permission, retention, train/eval separation and contamination. Attack observations can become
reviewed regression fixtures; they must not automatically become trusted training targets.
Non-attacks can inform drift baselines after validation; accepted useful inputs remain subject to
the same provenance and privacy rules. Never place private payloads or credentials in a public
mission/history issue. Missions: EVAL-01, SEC-02, SUP-01.

### 16. CI, dependency maintenance, and secret scans

Sources: [CI](../../.github/workflows/ci.yml),
[weekly scan](../../.github/workflows/weekly-security-scan.yml),
[workflow audit](../../.github/workflows/workflow-audit.yml),
[dependency maintenance](../DEPENDENCY_MAINTENANCE.md).

The sampled main checks include successful Node/Python/package/product checks, alongside four
failed Dependabot check runs and two queued cloud-deployment checks. Those failures need triage;
they do not prove a production outage. The weekly scanner can finish while a report is missing,
so verify scanner execution/artifacts before interpreting zero findings as clean.
Branch-protection settings could not be read with the current integration (403); owner verification
of required checks, review policy and protected deployment environments remains pending.
Missions: OPS-01, SEC-01, SEC-02.

### 17. Research products, prototypes, mobile, and visual applications

Sources: [surface map](../REPO_SURFACE_MAP.md), [apps](../../apps/),
[consolidation inventory](../../config/repo_consolidation_inventory.json), [companion map](COMPANIONS.md).

Promote a prototype to an active profile only when it has a maintainer, installable artifact, explicit
entrypoint, tests, data contract, deployment recipe and support boundary. Demo benchmarks and
README examples are leads for evaluation, not production receipts. The embedding companion's
advertised PHDMEmbedder import is not present in its inspected source tree.
Conference/visual subapps have separate dependency manifests and compatibility gates.
Missions: REP-01, ARC-01, SUP-01.

### 18. Submodules, archived code, and documentation drift

Sources: [.gitmodules](../../.gitmodules), [companion inventory](COMPANIONS.md),
[source authority](../specs/MONOREPO_CONSOLIDATION_AUTHORITY.md).

Eleven configured submodule entries include duplicate protocol pointers, third-party tooling and
archived repositories. Presence is not a runtime dependency. For each activated submodule pin a
commit, review license/maintenance, and assign an owner. Older SYSTEM_MAP/consolidation/readiness
documents contain historical pointers; some old product:ship/product:readiness commands are absent
from the current package manifest. Reconcile them as documentation work; do not invent missing
commands or silently deploy from an archive. Missions: REP-01, HIS-02, ARC-01.

## Release Boss Gate: evidence required for a go decision

A release issue must include all seven gates for its named profile. A non-applicable gate needs an
explicit reason and reviewer. A scheduled check or checklist tick cannot supply absent evidence.

1. **Identity:** immutable commit(s), artifact digest, selected runtime/backend, schema/model/policy
   versions and dependency pins; exact source-to-artifact provenance.
2. **Build and contract:** current relevant CI, clean installed-artifact tests, required endpoint/tool
   availability and documented compatibility. Inspect failures and skipped critical tests.
3. **Security:** authorization-denial, tamper, replay, malformed/missing evidence, privilege boundaries
   and real crypto backend tests in the artifact that will run.
4. **Target rehearsal:** staged or target-host startup, representative useful work, failure handling,
   provider budget/routing, telemetry and audit durability, with a redacted receipt.
5. **Recovery:** isolated restore and rollback rehearsal for stateful changes, migration compatibility,
   measured recovery objectives and a known rollback digest.
6. **Operations:** owner/on-call contact, incident path, alert delivery, access review, retention,
   support scope and due recurring missions; unresolved risks assigned.
7. **Promotion:** owner approval of the exact profile/revision, protected release procedure, post-release
   version/health/functional check and rollback trigger. Deployment itself is a separately authorized action.

Suggested receipt fields: profile, source_shas, artifact_digests, environment, checked_at,
runtime_versions, backend, schema/model/policy versions, test/run URLs, negative cases, restore/rollback
evidence, findings, risk owner, reviewer, decision, next review date. Store secrets and sensitive
incident details in restricted systems; public receipts contain references and redacted outcomes.

## Baseline evidence and limits

- Inspected main at the revision above; public companion metadata/README/tree as described in COMPANIONS.
- [Main CI success](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/37419755239)
  and [nightly Python success](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/37491689798)
  were observed. These are historical run receipts, not perpetual green status.
- [Example failed Dependabot run](https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/37419792825)
  requires current triage; no specific vulnerability severity is inferred from a failed updater.
- The existing deployment_readiness_gate.py mainly checks file presence and limited offline/smoke
  paths. A pass does not replace the gates above.
- No production deployment, live billing transaction, secret rotation, history rewrite, model
  retraining, or companion repository modification is part of this documentation review.
- The commit catalog utility has focused tests for exact ancestry bounds, merge accounting,
  shallow-history rejection and safe Markdown output. The history catalogs preserve all paths
  for manual review; category assignment is heuristic.

## Maintenance and rollback of this guide

Update this guide and mission catalog through a reviewable PR when contracts or ownership change.
Append monthly catalogs; correct errors with a new commit and explanation. The issue board records
completion and next due dates. A draft PR or closed issue never counts as completed deployment work.
This guide introduces no application-runtime dependency and no additional GitHub Actions schedule.
Revert the documentation/utility commit to remove it; pause the companion scheduled task separately
if maintenance automation should stop.

Primary operational references:
[GitHub scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[dependency review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review).
