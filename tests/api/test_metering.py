from datetime import datetime

from api.metering import (
    AUDIT_REPORT_GENERATIONS,
    GOVERNANCE_EVALUATIONS,
    WORKFLOW_EXECUTIONS,
    MeteringStore,
)


def test_metering_store_daily_aggregate_upsert(tmp_path):
    store = MeteringStore(str(tmp_path / "metering.db"))

    when = datetime(2026, 1, 15, 10, 30)
    store.increment_metric("tenant_a", GOVERNANCE_EVALUATIONS, when=when)
    store.increment_metric("tenant_a", GOVERNANCE_EVALUATIONS, when=when, amount=2)

    rows = store.export_monthly_usage(2026, 1, tenant_id="tenant_a")
    assert len(rows) == 1
    assert rows[0].metric_name == GOVERNANCE_EVALUATIONS
    assert rows[0].count == 3


def test_metering_store_exports_multiple_metrics(tmp_path):
    store = MeteringStore(str(tmp_path / "metering.db"))

    store.increment_metric("tenant_a", GOVERNANCE_EVALUATIONS, when=datetime(2026, 1, 2))
    store.increment_metric("tenant_a", WORKFLOW_EXECUTIONS, when=datetime(2026, 1, 3), amount=4)
    store.increment_metric("tenant_b", AUDIT_REPORT_GENERATIONS, when=datetime(2026, 1, 4), amount=2)

    jan_rows = store.export_monthly_usage(2026, 1)
    actual = {(r.tenant_id, r.metric_name): r.count for r in jan_rows}

    assert actual[("tenant_a", GOVERNANCE_EVALUATIONS)] == 1
    assert actual[("tenant_a", WORKFLOW_EXECUTIONS)] == 4
    assert actual[("tenant_b", AUDIT_REPORT_GENERATIONS)] == 2
