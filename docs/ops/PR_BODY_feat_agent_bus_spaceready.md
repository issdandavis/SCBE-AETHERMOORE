## Summary

Lands **agent-bus spaceready** work: routing/harness alignment, GeoSeal and coding-spine surfaces, compliance and evaluation lanes where applicable, with **merge-focused** scope (avoid mixing unrelated site-only edits).

## Scope (adjust to match actual commits)

- Agent router / task harness and **tool bridge** (`scbe_agent_tool_bridge_v1`) for SCBE-first external tools.
- GeoSeal CLI / service paths and **native tokenization** surfaces where implemented on this branch.
- **Stripe billing hardening** (if included): SQLite persistence, webhook signature policy, owner-gated purchases, dedupe/idempotency—see `CHANGELOG.md` `[Unreleased]`.

## Test evidence

- `npm run build` && `npm test` (TypeScript)
- `PYTHONPATH=. python scripts/system/run_core_python_checks.py`
- `PYTHONPATH=. python -m pytest tests/api/test_stripe_billing_hardening.py -v` (when billing changes present)

## Ops / env (post-merge)

- `SCBE_BILLING_DB_PATH` on persistent volume; `STRIPE_WEBHOOK_SECRET`; `SCBE_OWNER_API_TOKEN` for operator purchase reads.
- See `docs/ops/OPERATOR_SHIPPING_RAIL.md`.

## Rollback

Revert this PR; billing DB is optional SQLite—backup file before rollback if production purchases were recorded.
