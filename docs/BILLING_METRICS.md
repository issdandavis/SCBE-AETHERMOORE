# Billing Metrics

SCBE-AETHERMOORE uses lightweight tenant metering for billable usage reporting.

## Metered metrics

Daily usage is stored as `(tenant_id, date, metric_name, count)` for these metric names:

- `governance_evaluations`
  - Incremented once per successful `/v1/authorize` request.
  - Represents a single governance evaluation through the 14-layer pipeline.

- `workflow_executions`
  - Incremented once per successful `/v1/fleet/run-scenario` request.
  - Represents execution of one fleet workflow scenario.

- `audit_report_generations`
  - Incremented once per successful `/v1/audit/report` request.
  - Represents generation of an audit summary report for a tenant.

## Monthly billable usage exports

Two internal mechanisms are available:

1. API endpoint: `GET /v1/internal/billing/monthly-usage?year=YYYY&month=MM`
   - Returns tenant monthly totals by metric.
   - By default, results are scoped to the authenticated tenant.
   - Use `include_all_tenants=true` for cross-tenant finance exports.

2. Report command:

```bash
python scripts/export_monthly_billable_usage.py --year 2026 --month 1 --pretty
```

Optional tenant scope:

```bash
python scripts/export_monthly_billable_usage.py --year 2026 --month 1 --tenant-id tenant_0 --pretty
```
