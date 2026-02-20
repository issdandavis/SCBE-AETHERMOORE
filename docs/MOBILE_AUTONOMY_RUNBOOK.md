# Mobile Autonomy Runbook

Date: 2026-02-20  
Scope: Operate SCBE agents from phone app and execute goal-driven workflows

## Goal

Enable a phone app to submit goals (for example, online store operations), monitor progress, approve high-risk actions, and receive completion/audit updates.

## Implemented Control Plane (MVP)

API file: `src/api/main.py`

Endpoints:

- `POST /mobile/goals`
  - Submit a goal with channel profile (`store_ops`, `web_research`, `content_ops`, `custom`)
- `GET /mobile/goals`
  - List recent goals for authenticated user
- `GET /mobile/goals/{goal_id}`
  - Get current state, step progress, and event log
- `POST /mobile/goals/{goal_id}/advance`
  - Execute next step in the plan
- `POST /mobile/goals/{goal_id}/approve`
  - Approve high-risk steps from phone

## Safety Model

- High-risk steps are blocked when `require_human_for_high_risk=true`.
- Explicit approval is required to continue.
- Every step writes deterministic events for auditability.

## Phone App Flow

1. User submits goal from mobile app:
   - "Run storefront operations for today and process pending messages."
2. App polls `GET /mobile/goals/{id}` for status.
3. When status becomes `review_required`, app prompts user to approve.
4. App calls `POST /mobile/goals/{id}/approve`.
5. App resumes execution via `POST /mobile/goals/{id}/advance`.
6. Goal reaches `completed`; app displays summary.

## E-commerce Channel Pattern (`store_ops`)

Generated step plan:

1. `collect_store_state` (low risk)
2. `prioritize_orders_and_messages` (medium risk)
3. `execute_catalog_or_fulfillment_changes` (high risk)
4. `publish_daily_report` (low risk)

## Next Integration Steps (to reach full automation)

1. Replace simulated step execution with worker adapters:
   - Shopify admin adapter
   - Email/helpdesk adapter
   - Ad platform adapter
2. Add OAuth + scoped capability tokens per store/account.
3. Add approval policies by action type and spend threshold.
4. Add webhook push to phone app for real-time status events.
5. Add immutable audit sink (S3 + signed event hash chain).

## Local Test

```bash
python -m pytest -q tests/test_mobile_goal_api.py
```

## Example API Key Header

`x-api-key: demo_key_12345`

