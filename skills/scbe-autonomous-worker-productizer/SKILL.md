---
name: scbe-autonomous-worker-productizer
description: Turn SCBE automation, autonomous worker, and revenue-system notes into concrete offers, workflow packs, pilot plans, or SaaS-facing product packets. Use when Codex needs to package Notion automation pages into buyer-ready offerings, n8n/Zapier workflow designs, flock-backed worker systems, or implementation roadmaps tied to existing SCBE repo surfaces.
---

# SCBE Autonomous Worker Productizer

## Overview

Use this skill to convert SCBE automation notes into something sellable or deployable. Start from the Notion worker/product pages, then bind them to repo surfaces such as flock orchestration, `/saas` routes, governance checks, and monetization scripts.

## Quick Start

1. Emit a starter product packet:

```powershell
python skills/scbe-autonomous-worker-productizer/scripts/build_worker_offer_packet.py --repo-root . --mode pilot
```

2. Read the generated outputs:
- `artifacts/worker_productization/pilot_packet.json`
- `artifacts/worker_productization/pilot_packet.md`

## Workflow

1. Choose the packaging mode first.
- `pilot`: scoped paid evaluation
- `workflow-pack`: automation deliverable for n8n/Zapier/Notion
- `saas`: product surface backed by `/saas`
- `service`: ongoing managed automation engagement

2. Start from the right Notion pages.
- Read `references/source_pages.md`.
- Treat the worker/revenue pages as the product input set.
- Treat the deep-tech pages as trust and differentiation support, not the main offer copy.

3. Map the idea to repo surfaces.
- Flock orchestration: `src/symphonic_cipher/scbe_aethermoore/flock_shepherd.py`
- SaaS API: `src/api/saas_routes.py`, `src/api/main.py`
- Tests: `tests/test_saas_api.py`, `tests/test_flock_shepherd.py`
- Monetization and pilot scripts: see `references/offer_shapes.md`

4. Separate buyer value from implementation details.
- buyer
- problem
- promise
- workflow lanes
- approval/governance gates
- delivery artifacts
- proof surfaces in the repo

5. Keep the packaging honest.
- If the repo only supports demo-grade in-memory tenancy, say that.
- If a worker flow depends on external connectors not wired here, call that out as integration work.
- Use the Notion product pages for shape, not for unverified certainty.

6. Produce deterministic outputs.
- JSON plan for machine reuse
- Markdown packet for human review
- next build steps tied to repo paths

## Pairings

- Pair with `$scbe-claim-to-code-evidence` when the offer needs deeper proof.
- Pair with `$skill-synthesis` when the work spans product, automation, browser, and deploy lanes.
- Pair with `$scbe-admin-autopilot` when the goal is always-on execution or recurring workflow loops.

## Output Contract

Return:
- chosen packaging mode
- target buyer and promise
- worker lanes and connectors
- repo proof surfaces
- blockers and next implementation steps
- artifact paths for JSON and markdown outputs

## Resources

- `references/source_pages.md`: Notion pages to use for worker/product packaging
- `references/offer_shapes.md`: output modes and recommended repo surfaces
- `scripts/build_worker_offer_packet.py`: generate a starter worker product packet
