from __future__ import annotations

import math
from pathlib import Path

import pytest

from scripts.apollo import obsidian_vault_sync as ovs


def _build_note(name: str, folder: str, content: str) -> ovs.VaultNote:
    headings = ["Overview"]
    tags = ["semantic-gravity"]
    tongue = ovs.classify_tongue(name, folder, content)
    profile = ovs.compute_tongue_profile(name, folder, headings, tags, content, tongue)
    subjects, tasks, relations = ovs.extract_semantic_labels(name, folder, headings, tags, content)
    return ovs.VaultNote(
        path=f"{name}.md",
        name=name,
        folder=folder,
        size=len(content),
        headings=headings,
        tags=tags,
        outgoing_links=[],
        incoming_links=[],
        content_hash="synthetic",
        word_count=len(content.split()),
        tongue=tongue,
        tongue_profile=profile,
        primary_weight_phi=round(ovs.TONGUE_PHI_WEIGHTS[tongue], 6),
        semantic_mass_phi=ovs.compute_semantic_mass(profile),
        tongue_sector_degrees=ovs.TONGUE_SECTORS_DEGREES[tongue],
        tongue_sector_radians=round(ovs.TONGUE_SECTORS_RADIANS[tongue], 6),
        subjects=subjects,
        tasks=tasks,
        relations=relations,
    )


def test_compute_tongue_profile_is_normalized_and_primary_biased() -> None:
    profile = ovs.compute_tongue_profile(
        name="Governance Relay",
        folder="Agents/Operations",
        headings=["Governance Relay Overview"],
        tags=["governance", "agent"],
        content="This workflow routes agent intent through governance and session flow.",
        primary_tongue="KO",
    )

    assert set(profile) == set(ovs.TONGUE_ORDER)
    assert all(value >= 0.0 for value in profile.values())
    assert pytest.approx(sum(profile.values()), rel=0, abs=1e-5) == 1.0
    assert profile["KO"] == max(profile.values())


def test_tongue_sectors_match_six_equal_phi_weighted_sectors() -> None:
    assert ovs.TONGUE_SECTORS_DEGREES == {
        "KO": 0.0,
        "AV": 60.0,
        "RU": 120.0,
        "CA": 180.0,
        "UM": 240.0,
        "DR": 300.0,
    }
    assert ovs.TONGUE_SECTORS_RADIANS["KO"] == 0.0
    assert ovs.TONGUE_SECTORS_RADIANS["CA"] == pytest.approx(math.pi, abs=1e-9)
    assert ovs.TONGUE_PHI_WEIGHTS["DR"] > ovs.TONGUE_PHI_WEIGHTS["UM"] > ovs.TONGUE_PHI_WEIGHTS["CA"]


def test_shared_tongue_weight_is_symmetric_and_bounded() -> None:
    profile_a = {"KO": 0.5, "AV": 0.5, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0}
    profile_b = {"KO": 0.25, "AV": 0.75, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0}

    shared_ab = ovs.compute_shared_tongue_weight(profile_a, profile_b)
    shared_ba = ovs.compute_shared_tongue_weight(profile_b, profile_a)

    assert shared_ab == shared_ba
    assert 0.0 <= shared_ab <= max(ovs.TONGUE_PHI_WEIGHTS.values())

    concentrated = {"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 1.0}
    assert ovs.compute_shared_tongue_weight(concentrated, concentrated) == pytest.approx(
        ovs.TONGUE_PHI_WEIGHTS["DR"], abs=1e-6
    )


def test_semantic_gravity_is_symmetric_and_monotonic_with_overlap() -> None:
    anchor = _build_note(
        "Governance Kernel",
        "Architecture",
        "governance policy gate route audit structure system layer framework",
    )
    close_neighbor = _build_note(
        "Governance Audit Bridge",
        "Architecture",
        "governance audit route policy structure system framework bridge linked",
    )
    weak_neighbor = _build_note(
        "Story Fragment",
        "Lore",
        "narrative character world story chapter dialogue scene",
    )

    strong_metrics = ovs.compute_semantic_gravity(anchor, close_neighbor)
    strong_metrics_reverse = ovs.compute_semantic_gravity(close_neighbor, anchor)
    weak_metrics = ovs.compute_semantic_gravity(anchor, weak_neighbor)

    assert strong_metrics == strong_metrics_reverse
    assert strong_metrics["semantic_overlap"] > weak_metrics["semantic_overlap"]
    assert strong_metrics["semantic_gravity"] > weak_metrics["semantic_gravity"]

    explicit_metrics = ovs.compute_semantic_gravity(anchor, weak_neighbor, explicit_link=True)
    assert explicit_metrics["semantic_gravity"] > weak_metrics["semantic_gravity"]


def test_build_graph_preserves_legacy_stats_and_emits_semantic_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    architecture_dir = tmp_path / "Architecture"
    langues_dir = tmp_path / "Langues"
    research_dir = tmp_path / "Research"
    architecture_dir.mkdir()
    langues_dir.mkdir()
    research_dir.mkdir()

    (architecture_dir / "Governance Mesh.md").write_text(
        """
# Governance Mesh
This governance workflow routes agent sessions and audit steps through a structural framework.
It references [[Tokenizer Note]] and [[Research Pack]] for implementation and verification.
#governance #agent
""".strip(),
        encoding="utf-8",
    )
    (langues_dir / "Tokenizer Note.md").write_text(
        """
# Tokenizer Note
This tokenizer computes language metrics, graph relations, and implementation details for governance routing.
#tongue #tokenizer
""".strip(),
        encoding="utf-8",
    )
    (research_dir / "Research Pack.md").write_text(
        """
# Research Pack
This benchmark and evaluation report verifies training data quality and experiment scoring.
#research #training
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(ovs, "VAULT_PATH", tmp_path)
    notes = ovs.scan_vault()
    graph = ovs.build_graph(notes)

    assert graph["stats"]["total_notes"] == 3
    assert graph["stats"]["total_links"] == 2
    assert "semantic_links" in graph["stats"]
    assert "tongue_weights_phi" in graph
    assert "tongue_sectors" in graph
    assert graph["stats"]["max_semantic_gravity"] > 0.0

    governance_node = next(node for node in graph["nodes"] if node["id"] == "Governance Mesh")
    assert "subjects" in governance_node
    assert "tasks" in governance_node
    assert "relations" in governance_node
    assert "null_space_score" in governance_node
    assert governance_node["semantic_mass_phi"] > 0.0

    explicit_edges = [edge for edge in graph["edges"] if edge["edge_kind"] == "explicit_link"]
    semantic_edges = [edge for edge in graph["edges"] if edge["edge_kind"] == "semantic_overlap"]
    assert len(explicit_edges) == 2
    assert explicit_edges[0]["semantic_gravity"] > 0.0
    assert all(edge["semantic_gravity"] >= ovs.SEMANTIC_EDGE_MIN_GRAVITY for edge in semantic_edges)

    if graph["null_space_paths"]:
        assert graph["null_space_paths"][0]["null_space_flux"] >= 0.0
