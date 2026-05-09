from __future__ import annotations

import json
from pathlib import Path

from scripts.revenue.daily_cash_sprint import generate_packet, run_continuous


def test_daily_cash_sprint_generates_packet(tmp_path: Path) -> None:
    paths = generate_packet(
        offer_id="local_ai_command_center_setup",
        minutes=20,
        out_root=tmp_path,
    )

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["queue"].exists()

    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert report["minutes"] == 20
    assert report["offer"]["offer_id"] == "local_ai_command_center_setup"
    assert report["offer"]["title"] == "GeoSeal CLI Agent Bus Setup"
    assert "agent bus" in report["offer"]["promise"]
    assert report["send_goal"] == {"dm": 5, "email": 2, "public_post": 1}
    assert len(report["outreach_drafts"]) == 3

    queue_lines = paths["queue"].read_text(encoding="utf-8").strip().splitlines()
    assert len(queue_lines) == 3
    assert all("text" in json.loads(line) for line in queue_lines)


def test_daily_cash_sprint_generates_governance_snapshot_offer(tmp_path: Path) -> None:
    paths = generate_packet(
        offer_id="ai_governance_snapshot",
        minutes=20,
        out_root=tmp_path,
    )

    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert report["offer"]["offer_id"] == "ai_governance_snapshot"
    assert report["offer"]["title"] == "AI Governance Snapshot"
    assert report["offer"]["price_floor_usd"] == 500
    assert report["offer"]["price_anchor_usd"] == 500

    drafts = report["outreach_drafts"]
    assert len(drafts) == 3
    assert any("https://buy.stripe.com/eVqeVeaWu79ZgJi11Ydby0j" in draft["text"] for draft in drafts)
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "2-page findings memo" in markdown
    assert "Price: $500\n" in markdown
    assert "$500-$500" not in markdown


def test_daily_cash_sprint_generates_tip_jar_offer(tmp_path: Path) -> None:
    paths = generate_packet(
        offer_id="tip_jar",
        minutes=10,
        out_root=tmp_path,
    )

    report = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert report["offer"]["offer_id"] == "tip_jar"
    assert report["offer"]["price_floor_usd"] == 5
    assert report["offer"]["price_anchor_usd"] == 5
    assert any("https://buy.stripe.com/3cI00k9Sqbqf50A11Ydby0k" in draft["text"] for draft in report["outreach_drafts"])

    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Price: $5\n" in markdown
    assert "$5-$5" not in markdown


def test_daily_cash_sprint_continuous_advances_to_next_task(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    first = run_continuous(
        offer_id="local_ai_command_center_setup",
        minutes=20,
        out_root=tmp_path,
        state_path=state_path,
        max_steps=1,
        reset=True,
    )
    assert first["completed_count"] == 1
    assert first["remaining_count"] == 5

    second = run_continuous(
        offer_id="local_ai_command_center_setup",
        minutes=20,
        out_root=tmp_path,
        state_path=state_path,
        max_steps=1,
    )
    assert second["completed_count"] == 2
    assert second["remaining_count"] == 4

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert [task["state"] for task in state["tasks"][:2]] == ["DONE", "DONE"]
    assert state["tasks"][2]["state"] == "PENDING"


def test_daily_cash_sprint_cycles_when_complete(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    first = run_continuous(
        offer_id="local_ai_command_center_setup",
        minutes=20,
        out_root=tmp_path,
        state_path=state_path,
        max_steps=6,
        reset=True,
    )
    assert first["completed_count"] == 6
    assert first["remaining_count"] == 0

    second = run_continuous(
        offer_id="local_ai_command_center_setup",
        minutes=20,
        out_root=tmp_path,
        state_path=state_path,
        max_steps=1,
        cycle_when_complete=True,
    )
    assert second["cycle_index"] == 1
    assert second["completed_count"] == 1
    assert second["remaining_count"] == 5

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["cycle_history"][0]["completed_count"] == 6
    assert state["tasks"][0]["state"] == "DONE"
    assert state["tasks"][1]["state"] == "PENDING"
