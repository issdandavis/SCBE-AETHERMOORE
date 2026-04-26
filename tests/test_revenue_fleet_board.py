from __future__ import annotations

from pathlib import Path

from scripts.system.build_revenue_fleet_board import board_rows, parse_shortlist, write_outputs


def test_parse_shortlist_extracts_opportunities() -> None:
    markdown = """
## Bid-Now / Respond-Now Targets

### 1. Data Migration RFI

- Solicitation: `FA283426Q0001`
- Due: 2026-05-10 4:00 PM Eastern
- Agency: Air Force Life Cycle Management Center
- Fit: Good for data consolidation.
- Action: Respond with a small-business capability statement.
"""
    opportunities = parse_shortlist(markdown)

    assert len(opportunities) == 1
    assert opportunities[0].title == "Data Migration RFI"
    assert opportunities[0].solicitation == "FA283426Q0001"
    assert opportunities[0].section == "Bid-Now / Respond-Now Targets"


def test_board_rows_create_five_agentic_tasks_per_opportunity() -> None:
    markdown = """
## Bid-Now / Respond-Now Targets

### Engineering Pathway Courseware
- Solicitation: `HE125426QE033`
- Due: 2026-04-28
- Agency: Department of Defense Education Activity
- Fit: High priority courseware fit.
- Action: Build response.
"""
    opportunities = parse_shortlist(markdown)
    rows = board_rows(opportunities)

    assert len(rows) == 5
    assert {row["lane"] for row in rows} == {"capture", "qualification", "proof", "response", "followup"}
    assert rows[0]["priority"] == "P0"
    assert rows[0]["task_id"].startswith("HE125426QE033-01-")


def test_write_outputs_creates_json_csv_and_markdown(tmp_path: Path) -> None:
    markdown = """
## Sources-Sought

### Reference Data Management
- Solicitation: `TRANSCOM26D003`
- Due: 2026-05-04
- Agency: USTRANSCOM
- Fit: Strong reference-data fit.
- Action: Respond with a data-governance capability statement.
"""
    rows = board_rows(parse_shortlist(markdown))
    json_path, csv_path, md_path = write_outputs(rows, tmp_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()
    assert "TRANSCOM26D003" in md_path.read_text(encoding="utf-8")
