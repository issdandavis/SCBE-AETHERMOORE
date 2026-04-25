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
