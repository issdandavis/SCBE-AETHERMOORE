# Project Consolidation Review - 2026-05-07

Status: active review  
Goal: consolidate project, packages, website, and GitHub state into one launch-ready map.

## Executive Read

The project has real shippable surfaces now, but they are split across four lanes:

1. Product delivery: website pages, manuals, Stripe-oriented fulfillment, and buyer ZIPs.
2. Platform packages: root SCBE-AETHERMOORE packages, GeoSeal/CLI surfaces, and agent bus packages.
3. Training/evaluation: Hugging Face dispatch, coding evals, constrained decoding, radio/Layer 14 verifier, and gate reports.
4. Research prototypes: MAHSS/materials, PUF clustering, space-material concepts, and experimental demos.

The immediate launch blocker is not lack of product. It is source-of-truth drift: the live website, local `docs/` site, package registries, GitHub Actions, and buyer-delivery URLs do not all point to the same release story yet.

## Current Evidence

### Website

- Live `https://aethermoore.com/` returned HTTP 200.
- Live title: `Stop Your AI From Costing You a Lawsuit | SCBE-AETHERMOORE`.
- Live page contains Delivery, Stripe, GitHub, Hugging Face, Polly, and SCBE signals.
- Live page did not contain the exact `Buy the Toolkit` phrase.
- Local `docs/index.html` is a different product/training-vault oriented surface.
- `docs/` publish surface verification passed:
  - `docs/index.html`
  - `docs/product-manual/index.html`
  - `docs/product-manual/delivery-and-access.html`
  - `docs/product-manual/ai-governance-toolkit.html`
  - `docs/product-manual/training-vault.html`
  - `docs/offers/index.html`
  - checkout links present
- Website sales audit result: `6.0/10`.
- Website audit risks:
  - too many secondary calls to action
  - no visible hero product image
  - no final CTA
  - missing direct use-case/proof/comparison links from the reviewed local index page

### Product Delivery

Local product packaging works.

Generated verification artifacts:

- `artifacts/consolidation_review/packaged_check/SCBE_AI_Governance_Toolkit_v1.zip`
- `artifacts/consolidation_review/packaged_check/SCBE_AI_Security_Training_Vault_v1.zip`

Current packaged buyer files also exist:

- `products/packaged/SCBE_AI_Governance_Toolkit_v1.zip`
- `products/packaged/SCBE_AI_Security_Training_Vault_v1.zip`

Delivery code supports one-time products in `src/api/stripe_billing.py`, but production readiness depends on environment/config:

- `SCBE_TOOLKIT_DOWNLOAD_URL`
- `SCBE_TRAINING_VAULT_DOWNLOAD_URL`
- Stripe session metadata `scbe_product=toolkit` or `scbe_product=vault`
- SMTP delivery credentials for buyer emails

If those are missing, delivery can fall back to the latest GitHub release or fail to resolve the buyer product. That is acceptable for internal testing, not acceptable for paid customer delivery.

### Packages

Registry state checked on 2026-05-07:

- npm `scbe-aethermoore`: `4.0.7`
- npm `scbe-agent-bus`: `0.2.0`
- npm `scbe-aethermoore-cli`: `4.1.3`
- PyPI `scbe-agent-bus`: `0.2.0`
- PyPI `scbe-aethermoore`: `3.3.0`

Local root package versions:

- `package.json`: `scbe-aethermoore` `4.0.7`
- `pyproject.toml`: `scbe-aethermoore` `4.0.3`

Main drift:

- npm root package is current.
- PyPI root package is stale versus local `pyproject.toml`.
- `packages/geoseal-cli` exists locally but `npm view geoseal-cli` returned not found.

### GitHub And CI

Repository state:

- Public repo homepage points to `https://aethermoore.com`.
- Viewer permission is admin.
- Latest release: `scbe-agent-bus 0.2.0 (Python)`.
- Current branch is ahead of origin with local commits.

Workflow state checked on 2026-05-07:

- `overnight-pipeline.yml`: latest two runs succeeded.
- `daily-tests.yml`: latest runs failed on `main`.
- Latest daily-test failure root cause:
  - `tests/test_code_scanning_batch3.py` imported `spiral-word-app/app.py`.
  - `spiral-word-app/app.py` imported `governance`.
  - Linux CI resolved `governance` to `src/governance/__init__.py`, not `spiral-word-app/governance.py`.
  - Import failed because `src/governance` does not export `audit_log`.

Local verification:

```powershell
python -m pytest tests/test_code_scanning_batch3.py -q
```

Result:

```text
3 passed in 0.88s
```

The current working tree already contains the local import-path guard in `spiral-word-app/app.py` and test loader hardening in `tests/test_code_scanning_batch3.py`. The GitHub failure appears to be from `main` before that fix landed.

## Consolidation Model

Use four named shelves instead of one giant pile.

### Shelf 1 - Sellable Product

Purpose: customer-facing offer, purchase, instructions, delivery.

Keep here:

- `docs/index.html`
- `docs/offers/index.html`
- `docs/product-manual/`
- `products/packaged/`
- `src/api/stripe_billing.py`
- buyer delivery and support docs

Launch definition:

- customer can buy
- customer gets the correct ZIP quickly
- customer gets clear instructions
- support/failure path is documented

### Shelf 2 - Developer Platform

Purpose: installable tools and APIs.

Keep here:

- root npm package
- root PyPI package
- `packages/agent-bus`
- `packages/agent-bus-py`
- `packages/scbe-aethermoore-cli`
- `packages/geoseal-cli` if publishing is intended
- `src/crypto/`
- `src/api/`
- `src/harmonic/`

Launch definition:

- registry versions match local release intent
- README install commands work
- package links are accurate
- CLI examples run

### Shelf 3 - Training And Evaluation

Purpose: prove model behavior and produce training/eval artifacts.

Keep here:

- `scripts/eval/`
- `scripts/training_data/`
- `config/model_training/`
- training manifests
- constrained decoding reports
- Layer 14/radio verifier
- Hugging Face dispatch wrappers

Launch definition:

- gate results are summarized in one training status file
- failed/running jobs are separated from release claims
- eval claims include seed/count/confidence boundaries

### Shelf 4 - Research And Materials

Purpose: preserve experimental upside without confusing customers.

Keep here:

- MAHSS/materials work
- PUF clustering harness
- OpenSCAD emitter
- space-material concept stack
- experimental physics/math notes
- demo-only branches

Launch definition:

- labeled experimental
- no customer promises
- evidence artifacts linked separately from product manuals

## Priority Fixes

1. Push or merge the current import-path fix so `daily-tests.yml` stops failing on `main`.
2. Decide whether `aethermoore.com` should serve the Vercel API launch surface or the static `docs/` buyer surface. Right now live and local surfaces are not the same story.
3. Set buyer-only delivery URLs for Toolkit and Training Vault. Do not rely on the GitHub latest-release fallback for paid customers.
4. Align package registry story:
   - publish or explicitly defer PyPI `scbe-aethermoore` `4.0.3`
   - decide whether `geoseal-cli` should be published or removed from public-facing claims
5. Reduce homepage CTA clutter and add a final CTA.
6. Triage automation PR backlog after the daily-test fix lands.
7. Keep MAHSS/materials and radio/Layer 14 work as labeled research until it has customer-facing packaging.

## Recommended Next Sequence

1. Push the branch containing the daily-test import fix.
2. Re-run GitHub `daily-tests.yml` on the fixed branch or after merge to `main`.
3. Make `docs/` the canonical buyer surface unless there is a deliberate Vercel app reason not to.
4. Configure delivery URLs and Stripe metadata for the two paid offers.
5. Run a $0/test-mode checkout and verify buyer email/manual/download.
6. Update README and website to one clear offer:
   - buy Toolkit
   - buy Training Vault
   - install developer package
   - read product manual
7. Publish package updates only after the checkout path is verified.

## Bottom Line

This is consolidatable. The project is no longer missing core pieces; it is missing one clean release spine. The strongest spine is:

`website offer -> Stripe purchase -> buyer ZIP + manual -> installable package -> training/eval proof -> research appendix`

Anything that does not support that path should be labeled experimental or moved out of the customer-facing route.
