from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "build_representation_kaleidoscope.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_representation_kaleidoscope", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_kaleidoscope_groups_same_concept_across_language_lenses() -> None:
    module = _load_module()
    report = module.build_kaleidoscope(
        [
            ROOT / "training-data" / "sft" / "coding_system_full_v1_train.sft.jsonl",
            ROOT / "training-data" / "sft" / "coding_system_full_v1_holdout.sft.jsonl",
        ]
    )

    assert report["schema_version"] == "scbe_representation_kaleidoscope_v1"
    assert report["coverage"]["concept_count"] >= 8
    assert report["coverage"]["complete_language_frames"] == report["coverage"]["concept_count"]

    add = next(frame for frame in report["frames"] if frame["concept_id"] == "add")
    assert set(add["languages"]) == {"c", "haskell", "julia", "python", "rust", "typescript"}
    assert add["semantic_invariant_ok"] is True
    assert "autosearch_research_loop" in add["representation_axes"]
    assert add["autosearch"]["local_queries"]
    assert all(lens["binary"]["source_sha256"] for lens in add["lenses"])


def test_kaleidoscope_markdown_writer_emits_lens_table(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_kaleidoscope(
        [ROOT / "training-data" / "sft" / "coding_system_full_v1_train.sft.jsonl"]
    )
    out = tmp_path / "kaleidoscope.md"
    module.write_markdown(report, out)
    body = out.read_text(encoding="utf-8")
    assert "SCBE Representation Kaleidoscope" in body
    assert "| Lens | Language | Mode | Phase | SHA-256 | Code preview |" in body
