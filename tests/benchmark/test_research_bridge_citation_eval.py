from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "research_bridge_citation_eval.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("research_bridge_citation_eval_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(source_path: str, assistant: dict, *, url: str = "https://arxiv.org/abs/2410.01706") -> dict:
    prompt = (
        "Extract a source-grounded research training note. Preserve source identity.\n\n"
        "Source kind: arxiv_evidence\n"
        "Title: [2410.01706] Sable: a Performant, Efficient and Scalable Sequence Model for MARL\n"
        f"URL: {url}\n"
        "Snippet:\n"
        "{\"ok\": true, \"url\": \"https://arxiv.org/abs/2410.01706\", \"title\": \"[2410.01706] Sable\"}"
    )
    return {
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(assistant)},
        ],
        "metadata": {
            "dedupe_key": "abc",
            "source_path": source_path,
            "source_sha256": "deadbeef",
        },
    }


def test_score_research_record_preserves_arxiv_source(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    assistant = {
        "arxiv_id": "2410.01706",
        "inference_boundary": "Do not treat the source as confirmed beyond captured text.",
        "observed_evidence": '{"ok": true, "url": "https://arxiv.org/abs/2410.01706", "title": "[2410.01706] Sable"}',
        "source_kind": "arxiv_evidence",
        "title": "[2410.01706] Sable: a Performant, Efficient and Scalable Sequence Model for MARL",
        "url": "https://arxiv.org/abs/2410.01706",
        "verification_step": "Reopen the cited source before public use.",
    }

    score = module.score_research_record(_row("source.json", assistant))

    assert score["ok"] is True
    assert score["score"] == 1.0
    assert score["checks"]["arxiv_id_preserved"] is True


def test_score_research_record_fails_when_evidence_does_not_overlap_prompt(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "source.json").write_text("{}", encoding="utf-8")
    assistant = {
        "arxiv_id": "2410.01706",
        "inference_boundary": "Do not treat the source as confirmed beyond captured text.",
        "observed_evidence": "This text was not in the source prompt and should not pass.",
        "source_kind": "arxiv_evidence",
        "title": "[2410.01706] Sable: a Performant, Efficient and Scalable Sequence Model for MARL",
        "url": "https://arxiv.org/abs/2410.01706",
        "verification_step": "Reopen the cited source before public use.",
    }

    score = module.score_research_record(_row("source.json", assistant))

    assert score["ok"] is False
    assert score["checks"]["observed_evidence_overlaps_prompt"] is False


def test_blank_url_line_does_not_capture_snippet_label(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "note.md").write_text("# Note", encoding="utf-8")
    prompt = (
        "Extract a source-grounded research training note.\n\n"
        "Source kind: obsidian_markdown\n"
        "Title: Local Note\n"
        "URL: \n"
        "Snippet:\n"
        "# Note with enough observed evidence to overlap the source prompt."
    )
    row = {
        "messages": [
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "arxiv_id": None,
                        "inference_boundary": "Do not treat the source as confirmed beyond captured text.",
                        "observed_evidence": "# Note with enough observed evidence to overlap the source prompt.",
                        "source_kind": "obsidian_markdown",
                        "title": "Local Note",
                        "url": None,
                        "verification_step": "Reopen the staged source file.",
                    }
                ),
            },
        ],
        "metadata": {"dedupe_key": "note", "source_path": "note.md", "source_sha256": "abc"},
    }

    score = module.score_research_record(row)

    assert score["ok"] is True
    assert score["checks"]["url_preserved"] is True


def test_arxiv_id_not_required_for_obsidian_snippet_link(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "note.md").write_text("# Note", encoding="utf-8")
    prompt = (
        "Extract a source-grounded research training note.\n\n"
        "Source kind: obsidian_markdown\n"
        "Title: Reference Note\n"
        "URL: \n"
        "Snippet:\n"
        "A local note mentions https://arxiv.org/abs/2410.01706 as one reference."
    )
    row = {
        "messages": [
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "arxiv_id": None,
                        "inference_boundary": "Do not treat the source as confirmed beyond captured text.",
                        "observed_evidence": "A local note mentions https://arxiv.org/abs/2410.01706 as one reference.",
                        "source_kind": "obsidian_markdown",
                        "title": "Reference Note",
                        "url": None,
                        "verification_step": "Reopen the staged source file.",
                    }
                ),
            },
        ],
        "metadata": {"dedupe_key": "note", "source_path": "note.md", "source_sha256": "abc"},
    }

    score = module.score_research_record(row)

    assert score["ok"] is True
    assert score["checks"]["arxiv_id_preserved"] is True


def test_build_report_passes_valid_eval(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    (tmp_path / "source.json").write_text("{}", encoding="utf-8")
    assistant = {
        "arxiv_id": "2410.01706",
        "inference_boundary": "Do not treat the source as confirmed beyond captured text.",
        "observed_evidence": '{"ok": true, "url": "https://arxiv.org/abs/2410.01706", "title": "[2410.01706] Sable"}',
        "source_kind": "arxiv_evidence",
        "title": "[2410.01706] Sable: a Performant, Efficient and Scalable Sequence Model for MARL",
        "url": "https://arxiv.org/abs/2410.01706",
        "verification_step": "Reopen the cited source before public use.",
    }
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(json.dumps(_row("source.json", assistant)) + "\n", encoding="utf-8")

    report = module.build_report(eval_path=eval_path, output_dir=tmp_path / "out", run_id="research")

    assert report["decision"] == "PASS"
    assert report["score"] == 1.0
    assert (tmp_path / "out" / "research" / "report.json").exists()
