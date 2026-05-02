# Release And Revenue Path - 2026-05-02

## Release Trunk

This release should stay scoped to the narrow trunk that already has guards:

| Surface | Where it releases | Purpose | Gate |
|---|---|---|---|
| npm package | npm registry as `scbe-aethermoore` | TypeScript SDK and `geoseal` / `scbe-geoseal` CLI | `npm run publish:check:strict` |
| Python package | PyPI as `scbe-aethermoore` | Python runtime and operator console scripts | `python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist` |
| GitHub Pages docs | `docs/` publish surface | Public proof, support, product explanation, checkout CTAs | `python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html --require-checkout` |
| Agentic harness | repo-local CLI/scripts first | AI-to-AI packet routing, provider matrix, terminal operator surface | `python scripts/ci/harness_release_readiness.py --json` |

Backend API, frontend app, Docker/deploy, training data, and buyer deliverables are separate release objects. Do not claim them as production-ready in this release unless their own smoke gates pass.

## How We Get Paid

Package registries do not pay us directly. npm and PyPI are distribution and trust surfaces.

The current cash rail is Stripe:

| Offer | Current rail | Price | Source |
|---|---|---:|---|
| AI Governance Toolkit | hosted Stripe payment link | `$29` one-time | `docs/index.html` |
| Training Vault | hosted Stripe payment link | `$29` one-time | `docs/index.html` |
| STARTER SaaS/API tier | Stripe Checkout session | `$99/month` | `api/billing/tiers.py` |
| PRO SaaS/API tier | Stripe Checkout session | `$499/month` | `api/billing/tiers.py` |
| ENTERPRISE | custom sales | custom | `api/billing/tiers.py` |

The paid path for the near-term release is:

1. Open-source package release builds trust and installability.
2. Docs route buyers to Stripe-hosted checkout links.
3. Buyer delivery stays separate under fulfillment artifacts or product packs.
4. SaaS/API subscriptions use `POST /v1/billing/public-checkout` once the backend is deployed and price IDs are real.

## Required Environment For SaaS Billing

Production billing is not clean until these are configured outside the repo:

| Variable | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe API access |
| `STRIPE_WEBHOOK_SECRET` | webhook signature verification |
| `STRIPE_PRICE_STARTER` | live Starter price id |
| `STRIPE_PRICE_PRO` | live Pro price id |
| `SCBE_BILLING_BASE_URL` | public checkout return URL base |
| `SCBE_OWNER_API_TOKEN` | owner-only purchase/admin checks |

Do not put any of these values in Git.

## Release Clean Definition

A clean release means:

1. The exact release files are intentionally staged.
2. npm tarball guard passes.
3. PyPI dist guard passes.
4. Docs publish surface has required pages and no test checkout links.
5. Harness release readiness reports no missing files and no generated package candidates.
6. `ready_to_publish` can remain false while work is uncommitted; it should only flip after staging/committing the intended release set.

## Sunday Finale Sequence

```powershell
npm run publish:check:strict
python scripts/pypi_dist_guard.py --dist-dir artifacts/pypi-dist
python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html --require-checkout
python scripts/ci/harness_release_readiness.py --json
```

Then decide:

- Publish npm/PyPI package release.
- Push docs page if checkout links are correct.
- Keep buyer fulfillment as a separate package approval step.
- Keep SaaS billing in preview until live backend deployment and webhook smoke pass.
