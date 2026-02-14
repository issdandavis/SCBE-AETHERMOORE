"""Lightweight tenant metering for billable usage exports."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from threading import Lock
from typing import Dict, List, Optional

GOVERNANCE_EVALUATIONS = "governance_evaluations"
WORKFLOW_EXECUTIONS = "workflow_executions"
AUDIT_REPORT_GENERATIONS = "audit_report_generations"

BILLABLE_METRICS = {
    GOVERNANCE_EVALUATIONS,
    WORKFLOW_EXECUTIONS,
    AUDIT_REPORT_GENERATIONS,
}


@dataclass(frozen=True)
class MonthlyUsageRow:
    tenant_id: str
    month: str
    metric_name: str
    count: int


class MeteringStore:
    """SQLite-backed daily aggregate store keyed by tenant/date/metric."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or os.getenv("SCBE_METERING_DB_PATH", "./scbe_metering.db")
        self._lock = Lock()
        self._ensure_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tenant_daily_usage (
                    tenant_id TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (tenant_id, usage_date, metric_name)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tenant_daily_usage_month
                ON tenant_daily_usage (usage_date, tenant_id, metric_name)
                """
            )
            conn.commit()

    def increment_metric(
        self,
        tenant_id: str,
        metric_name: str,
        when: Optional[datetime] = None,
        amount: int = 1,
    ) -> None:
        if metric_name not in BILLABLE_METRICS:
            raise ValueError(f"Unsupported billing metric: {metric_name}")
        if amount <= 0:
            raise ValueError("amount must be > 0")

        usage_date = (when or datetime.utcnow()).date().isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO tenant_daily_usage (tenant_id, usage_date, metric_name, count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(tenant_id, usage_date, metric_name)
                    DO UPDATE SET count = count + excluded.count
                    """,
                    (tenant_id, usage_date, metric_name, amount),
                )
                conn.commit()

    def export_monthly_usage(
        self,
        year: int,
        month: int,
        tenant_id: Optional[str] = None,
    ) -> List[MonthlyUsageRow]:
        month_prefix = date(year, month, 1).strftime("%Y-%m")
        params = [f"{month_prefix}%"]
        query = (
            """
            SELECT tenant_id, metric_name, COALESCE(SUM(count), 0) as total_count
            FROM tenant_daily_usage
            WHERE usage_date LIKE ?
            """
        )
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)

        query += " GROUP BY tenant_id, metric_name ORDER BY tenant_id, metric_name"

        with self._connect() as conn:
            cursor = conn.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [
            MonthlyUsageRow(
                tenant_id=row[0],
                month=month_prefix,
                metric_name=row[1],
                count=int(row[2]),
            )
            for row in rows
        ]


metering_store = MeteringStore()


def export_monthly_billable_usage(year: int, month: int, tenant_id: Optional[str] = None) -> Dict[str, object]:
    rows = metering_store.export_monthly_usage(year=year, month=month, tenant_id=tenant_id)
    totals = {metric: 0 for metric in sorted(BILLABLE_METRICS)}
    for row in rows:
        totals[row.metric_name] = totals.get(row.metric_name, 0) + row.count

    return {
        "month": f"{year:04d}-{month:02d}",
        "tenant_id": tenant_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rows": [row.__dict__ for row in rows],
        "totals": totals,
    }
