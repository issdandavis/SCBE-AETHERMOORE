from __future__ import annotations

import json
from pathlib import Path

from scripts.revenue.build_workflow_snapshot_autopromo import build_packet


def test_workflow_snapshot_autopromo_generates_reviewable_packet(tmp_path: Path) -> None:
    paths = build_packet(tmp_path)

    assert paths["packet"].exists()
    assert paths["drafts"].exists()
    assert paths["send_plan"].exists()
    assert paths["markdown"].exists()
    assert paths["queue"].exists()
    assert paths["x_ops_queue"].exists()
    assert paths["bluesky_queue"].exists()

    packet = json.loads(paths["packet"].read_text(encoding="utf-8"))
    assert packet["schema"] == "scbe-workflow-snapshot-autopromo-v1"
    assert packet["offer"]["id"] == "workflow_snapshot_starter"
    assert packet["offer"]["price_label"] == "$99 starter"
    assert packet["offer"]["cash_app"] == "$IzzyDDavis7"
    assert packet["offer"]["proof_url"].endswith("/workflow-snapshot.html")
    assert "connector_status" in packet

    draft_ids = {draft["id"] for draft in packet["campaign_items"]}
    assert {
        "x_thread",
        "linkedin_post",
        "reddit_sideproject",
        "github_discussion",
        "hf_community",
        "email_warm",
    } <= draft_ids
    assert all(draft["risk"] in {"low", "medium"} for draft in packet["campaign_items"])
    assert all(draft["status"] == "ready_to_publish" for draft in packet["campaign_items"])
    assert all(draft["quality_gate"]["passed"] for draft in packet["campaign_items"])

    send_plan = json.loads(paths["send_plan"].read_text(encoding="utf-8"))
    assert send_plan["status"] == "ready_to_publish_when_connector_is_available"
    assert "Do not mass-send cold private messages." in send_plan["principles"]
    assert send_plan["daily_budget_minutes"] == 20

    queue_lines = paths["queue"].read_text(encoding="utf-8").strip().splitlines()
    assert len(queue_lines) == len(packet["campaign_items"])
    assert all(json.loads(line)["status"] == "ready_to_publish" for line in queue_lines)

    x_ops = json.loads(paths["x_ops_queue"].read_text(encoding="utf-8"))
    assert len(x_ops["items"]) >= 3
    assert all(item["action"] == "post" for item in x_ops["items"])

    bluesky = json.loads(paths["bluesky_queue"].read_text(encoding="utf-8"))
    assert len(bluesky["items"]) >= 1
    assert all(item["platform"] == "bluesky" for item in bluesky["items"])


def test_workflow_snapshot_autopromo_markdown_contains_direct_action_copy(tmp_path: Path) -> None:
    paths = build_packet(tmp_path)
    markdown = paths["markdown"].read_text(encoding="utf-8")

    assert "Workflow Snapshot Autopromo Packet" in markdown
    assert "This packet turns the live offer into an autonomous marketing campaign" in markdown
    assert "https://aethermoore.com/SCBE-AETHERMOORE/workflow-snapshot.html" in markdown
    assert "$IzzyDDavis7" in markdown
    assert "the queue can be consumed by an automation runner" in markdown
