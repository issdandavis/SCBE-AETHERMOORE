from scripts.system.goal_race_loop import build_packets, build_scoreboard


def test_build_packets_forms_dependency_chain():
    packets = build_packets(
        "Ship AetherBrowse article lane", "money", ["prospector", "builder", "closer"]
    )
    assert len(packets) == 4
    assert packets[0].dependencies == []
    assert packets[1].dependencies == [packets[0].task_id]
    assert packets[2].dependencies == [packets[1].task_id]
    assert packets[3].dependencies == [packets[2].task_id]


def test_checkpoint_phases_are_marked():
    packets = build_packets(
        "Fix browser publish lane", "browser", ["navigator", "operator", "verifier"]
    )
    flagged = {packet.phase_id for packet in packets if packet.checkpoint}
    assert "verify" in flagged
    assert "repair" in flagged


def test_scoreboard_counts_tasks_per_lane():
    packets = build_packets(
        "Draft Medium and Substack lane", "story", ["weaver", "forger", "editor"]
    )
    scoreboard = build_scoreboard(
        "Draft Medium and Substack lane",
        "story",
        packets,
        ["weaver", "forger", "editor"],
        "run-1",
    )
    assert scoreboard["total_tasks"] == len(packets)
    assert any(lane["lane"] == "weaver" for lane in scoreboard["lanes"])
    assert scoreboard["checkpoint_tasks"] >= 1


def test_publish_mode_emits_skill_hints():
    packets = build_packets(
        "Publish Amazon-linked story post",
        "publish",
        ["writer", "operator", "reviewer"],
    )
    assert packets[0].phase_id == "draft"
    assert "article-posting-ops" in packets[0].recommended_skills
    assert any(packet.phase_id == "publish" for packet in packets)
