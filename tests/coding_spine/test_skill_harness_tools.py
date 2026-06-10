"""SKILL.md discovery and harness tool export."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1
from src.coding_spine.skill_harness_tools import (
    build_harness_skill_tools_v1,
    build_openai_style_skill_tools,
    discover_skills,
    _classify_function_area,
    _sanitize_tool_name,
)


def test_sanitize_tool_name() -> None:
    assert _sanitize_tool_name("scbe-postgres-lite-ops") == "scbe_skill_scbe_postgres_lite_ops"
    assert _sanitize_tool_name("scbe-postgres-lite-ops", area_abbrev="cli") == "scbe_cli_scbe_postgres_lite_ops"


def test_classify_function_area() -> None:
    assert _classify_function_area("scbe-copilot", "multi-agent code assistant", "") == "agent_tool"
    assert _classify_function_area("sam-search", "research SAM.gov opportunity intelligence", "") == "recon_tool"
    assert _classify_function_area("postgres-lite", "local command line database service", "") == "cli_tool"


def test_discover_skills_nested_under_claude_skills(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo harness skill.\n---\n\n# Body\n",
        encoding="utf-8",
    )
    skills = discover_skills(repo_root=tmp_path, max_skills=50)
    assert len(skills) == 1
    assert skills[0]["skill_id"] == "demo-skill"
    assert skills[0]["function_area"] == "agent_tool"
    assert skills[0]["invocation_kind"] == "tool_call"
    assert skills[0]["route_name"] == "Tool_call_agt_demo_skill"
    assert skills[0]["tool_name"] == "scbe_agt_demo_skill"
    assert skills[0]["skill_path"].replace("\\", "/").endswith(".claude/skills/demo-skill/SKILL.md")


def test_discover_flat_skill_root(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: root-skill\ndescription: Root level.\n---\n",
        encoding="utf-8",
    )
    skills = discover_skills(repo_root=tmp_path, max_skills=50)
    assert len(skills) == 1
    assert skills[0]["skill_id"] == "root-skill"


def test_discover_skills_parses_folded_frontmatter_description(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".agents" / "skills" / "folded"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: folded-skill\n"
        "description: >-\n"
        "  First sentence for the model.\n"
        "  Second sentence for routing.\n"
        "---\n",
        encoding="utf-8",
    )

    skills = discover_skills(repo_root=tmp_path, max_skills=50)

    assert len(skills) == 1
    assert skills[0]["description"] == "First sentence for the model. Second sentence for routing."


def test_discover_skills_dedupes_duplicate_tool_names(tmp_path: Path) -> None:
    for root_name in (".claude", ".agents"):
        skill_dir = tmp_path / root_name / "skills" / "dup"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: duplicate-skill\ndescription: Duplicate route.\n---\n",
            encoding="utf-8",
        )

    skills = discover_skills(repo_root=tmp_path, max_skills=50)
    names = [skill["tool_name"] for skill in skills]
    routes = [skill["route_name"] for skill in skills]

    assert len(skills) == 2
    assert len(set(names)) == 2
    assert len(set(routes)) == 2
    assert names == ["scbe_ops_duplicate_skill", "scbe_ops_duplicate_skill_2"]
    assert routes == ["Skill_lookup_ops_duplicate_skill", "Skill_lookup_ops_duplicate_skill_2"]


def test_openai_style_tools_match_skills(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".agents" / "skills" / "x"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: x\ndescription: Run multi-step agent automation.\n---\n", encoding="utf-8"
    )
    skills = discover_skills(repo_root=tmp_path)
    tools = build_openai_style_skill_tools(skills)
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "scbe_agt_x"
    assert "function_area=agent_tool" in tools[0]["function"]["description"]
    assert "parameters" in tools[0]["function"]


def test_openai_style_tools_excludes_lookup_routes(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "research-note"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: research-note\ndescription: Research and source lookup only.\n---\n",
        encoding="utf-8",
    )

    skills = discover_skills(repo_root=tmp_path)
    tools = build_openai_style_skill_tools(skills)

    assert skills[0]["invocation_kind"] == "skill_lookup"
    assert skills[0]["route_name"] == "Skill_lookup_rec_research_note"
    assert tools == []


def test_harness_manifest_includes_skill_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "manifest-test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: manifest-test\ndescription: For manifest.\n---\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.coding_spine.agent_tool_bridge.build_harness_skill_tools_v1",
        lambda repo_root=None: build_harness_skill_tools_v1(repo_root=tmp_path),
    )
    manifest = build_agent_harness_manifest_v1(inline_goal="test")
    assert "harness_skill_tools_v1" in manifest
    block = manifest["harness_skill_tools_v1"]
    assert block["schema_version"] == "scbe_harness_skill_tools_v1"
    assert block["discovered_count"] >= 1
    assert "function_area_counts" in block
    assert "skills_by_area" in block
    assert any(s["skill_id"] == "manifest-test" for s in block["skills"])
    assert "Skill_lookup_ops_manifest_test" in manifest["mcp_style_exports"]["skill_lookup_names"]
    assert "Skill_lookup_ops_manifest_test" in manifest["mcp_style_exports"]["skill_route_names"]


def test_geoseal_service_skill_tools_endpoint() -> None:
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post("/v1/geoseal/skill-tools", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    data = body["data"]
    assert data["schema_version"] == "scbe_harness_skill_tools_v1"
    assert "openai_style_tools" in data
