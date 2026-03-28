from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.system import research_training_bridge as bridge
from scripts import list_obsidian_vaults as vaults


def test_build_research_training_bundle_writes_expected_outputs(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "playwriter-arxiv.org-snapshot-session1.json").write_text(
        json.dumps(
            {
                "ok": True,
                "url": "https://arxiv.org/abs/2501.12345",
                "title": "[2501.12345] Hyperbolic Governance for Swarm Safety",
                "timestamp": "2026-03-18T07:00:00Z",
                "excerpt": "This paper studies hyperbolic governance and containment for multi-agent systems.",
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "playwriter-github.com-snapshot-session1.json").write_text(
        json.dumps({"url": "https://github.com/example/repo", "title": "ignore me"}),
        encoding="utf-8",
    )

    note_dir = tmp_path / "vault"
    note_dir.mkdir()
    (note_dir / "tower-note.md").write_text(
        "# Tower Training\n\n## Floors\n\nEach floor tests a different capability.\n\n- [ ] Add red gate floor\n",
        encoding="utf-8",
    )

    result = bridge.build_research_training_bundle(
        evidence_dir=evidence_dir,
        note_inputs=[note_dir],
        output_root=tmp_path / "out",
        bundle_name="tower-research",
        bundle_stamp="20260318T070000Z",
        dataset_repo="issdandavis/demo-dataset",
        model_repo="issdandavis/demo-model",
        max_excerpt_chars=240,
    )

    assert result["bundle_id"] == "tower-research-20260318T070000Z"
    assert result["counts"] == {"records": 2, "arxiv_evidence": 1, "obsidian_notes": 1}

    corpus_path = Path(result["corpus_path"])
    rows = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert {row["category"] for row in rows} == {
        "research_bridge_arxiv",
        "research_bridge_obsidian",
    }
    arxiv_row = next(row for row in rows if row["category"] == "research_bridge_arxiv")
    assert arxiv_row["metadata"]["arxiv_id"] == "2501.12345"
    note_row = next(row for row in rows if row["category"] == "research_bridge_obsidian")
    assert note_row["metadata"]["task_count"] == 1

    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["counts"]["records"] == 2
    assert len(manifest["sources"]) == 2

    hf_manifest = json.loads(Path(result["hf_training_manifest_path"]).read_text(encoding="utf-8"))
    assert hf_manifest["dataset_repo"] == "issdandavis/demo-dataset"
    assert hf_manifest["model_repo"] == "issdandavis/demo-model"
    assert "research_corpus.jsonl" in hf_manifest["suggested_local_command"]

    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Research Training Bridge Bundle" in report
    assert "Tower Training" in report

    staged_evidence = list((tmp_path / "out" / result["bundle_id"] / "sources" / "page_evidence").glob("*.json"))
    staged_notes = list((tmp_path / "out" / result["bundle_id"] / "sources" / "obsidian").glob("*.md"))
    assert len(staged_evidence) == 1
    assert len(staged_notes) == 1


def test_build_research_training_bundle_raises_on_empty_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No research sources were found"):
        bridge.build_research_training_bundle(
            evidence_dir=tmp_path / "missing-evidence",
            note_inputs=[tmp_path / "missing-vault"],
            output_root=tmp_path / "out",
            bundle_name="empty",
            bundle_stamp="20260318T080000Z",
        )


def test_build_research_training_bundle_can_use_active_vault_subdir(tmp_path: Path, monkeypatch) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "playwriter-arxiv.org-snapshot-session1.json").write_text(
        json.dumps(
            {
                "ok": True,
                "url": "https://arxiv.org/abs/2502.00001",
                "title": "[2502.00001] Signal Geometry",
                "timestamp": "2026-03-18T08:00:00Z",
                "excerpt": "A compact abstract.",
            }
        ),
        encoding="utf-8",
    )

    vault_root = tmp_path / "Avalon Files"
    (vault_root / "SCBE Research" / "Agent Ops").mkdir(parents=True)
    (vault_root / "SCBE Research" / "Agent Ops" / "session.md").write_text(
        "# Session\n\n## Notes\n\nBridge this into the training lane.\n",
        encoding="utf-8",
    )
    (vault_root / "IgnoreMe").mkdir()
    (vault_root / "IgnoreMe" / "other.md").write_text("# Ignore\n\nThis should not be ingested.\n", encoding="utf-8")

    monkeypatch.setattr(vaults, "active_vault_path", lambda config_path=None: vault_root)

    result = bridge.build_research_training_bundle(
        evidence_dir=evidence_dir,
        note_inputs=[],
        output_root=tmp_path / "out",
        bundle_name="active-vault",
        bundle_stamp="20260318T081500Z",
        use_active_vault=True,
        vault_subdirs=["SCBE Research"],
    )

    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["inputs"]["vault"]["active_vault_path"] == str(vault_root.resolve())
    assert manifest["inputs"]["vault"]["added_vault_paths"] == [str((vault_root / "SCBE Research").resolve())]

    rows = [
        json.loads(line)
        for line in Path(result["corpus_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2
    note_row = next(row for row in rows if row["category"] == "research_bridge_obsidian")
    assert note_row["metadata"]["source_file"].endswith("session.md")
    assert "IgnoreMe" not in note_row["metadata"]["source_file"]
