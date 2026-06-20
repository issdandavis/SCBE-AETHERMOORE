"""Tests for scripts/encoding/parallel_augment_sft.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "encoding" / "parallel_augment_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_parallel_augment_sft", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aug():
    return _load_module()


def _make_corpus(tmp_path: Path, files: dict[str, list[dict]]) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    for name, rows in files.items():
        (src / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# Single-worker mode (no multiprocessing) — fast, deterministic
# ---------------------------------------------------------------------------


def test_single_worker_run(aug, tmp_path: Path) -> None:
    src = _make_corpus(
        tmp_path,
        {
            "a.sft.jsonl": [{"messages": [{"role": "user", "content": "hello"}]}],
            "b.sft.jsonl": [{"messages": [{"role": "user", "content": "world"}]}],
        },
    )
    out = tmp_path / "out"
    results, summary = aug.run(input_dir=src, output_dir=out, workers=1)

    assert summary["files"] == 2
    assert summary["records_in"] == 2
    assert summary["records_out"] == 2
    assert summary["bundles_added"] == 2
    assert summary["errors"] == 0
    assert summary["workers"] == 1

    a_out = out / "a.dense.jsonl"
    b_out = out / "b.dense.jsonl"
    assert a_out.exists()
    assert b_out.exists()

    rec = json.loads(a_out.read_text(encoding="utf-8").splitlines()[0])
    assert rec["dense_bundle"]["byte_length"] == 5
    assert rec["dense_bundle"]["views"]["hex"] == "68656c6c6f"


def test_records_without_target_pass_through_unchanged(aug, tmp_path: Path) -> None:
    src = _make_corpus(
        tmp_path,
        {
            "a.sft.jsonl": [
                {"messages": [{"role": "user", "content": "x"}]},
                {"messages": [{"role": "system", "content": "no user turn"}]},
            ]
        },
    )
    out = tmp_path / "out"
    _, summary = aug.run(input_dir=src, output_dir=out, workers=1)
    assert summary["records_in"] == 2
    assert summary["records_out"] == 2
    assert summary["bundles_added"] == 1  # only the user-turn record

    rows = [
        json.loads(line) for line in (out / "a.dense.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert "dense_bundle" in rows[0]
    assert "dense_bundle" not in rows[1]


def test_empty_input_dir_returns_empty_summary(aug, tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    results, summary = aug.run(input_dir=src, output_dir=out, workers=1)
    assert results == []
    assert summary["files"] == 0
    assert summary["records_in"] == 0


# ---------------------------------------------------------------------------
# Output naming
# ---------------------------------------------------------------------------


def test_output_path_for_handles_three_extensions(aug, tmp_path: Path) -> None:
    in_dir = tmp_path / "src"
    out_dir = tmp_path / "out"
    cases = [
        ("foo.sft.jsonl", "foo.dense.jsonl"),
        ("bar.jsonl", "bar.dense.jsonl"),
        ("weird.txt", "weird.txt.dense.jsonl"),
    ]
    for input_name, expected in cases:
        path = in_dir / input_name
        result = aug._output_path_for(path, in_dir, out_dir, ".dense.jsonl")
        assert result == out_dir / expected


# ---------------------------------------------------------------------------
# Workers parameter clamping
# ---------------------------------------------------------------------------


def test_worker_count_clamped_to_file_count(aug, tmp_path: Path) -> None:
    """If we ask for 32 workers but only have 1 file, only 1 worker runs."""
    src = _make_corpus(tmp_path, {"only.sft.jsonl": [{"messages": [{"role": "user", "content": "x"}]}]})
    out = tmp_path / "out"
    _, summary = aug.run(input_dir=src, output_dir=out, workers=32)
    assert summary["workers"] == 1


# ---------------------------------------------------------------------------
# CLI exit codes
# ---------------------------------------------------------------------------


def test_cli_missing_input_dir_returns_2(aug, tmp_path: Path) -> None:
    rc = aug.main(["--input-dir", str(tmp_path / "nope"), "--output-dir", str(tmp_path / "out"), "--quiet"])
    assert rc == 2


def test_cli_quiet_path_runs(aug, tmp_path: Path, capsys) -> None:
    src = _make_corpus(tmp_path, {"a.sft.jsonl": [{"messages": [{"role": "user", "content": "x"}]}]})
    out = tmp_path / "out"
    rc = aug.main(["--input-dir", str(src), "--output-dir", str(out), "--workers", "1", "--quiet"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "DONE:" in captured.out
