from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "fiction_quality_benchmark.py"
CONFIG_PATH = ROOT / "config" / "eval" / "fiction_quality_benchmark.v1.json"
SEED_PATH = ROOT / "training-data" / "evals" / "fiction_quality_seed.jsonl"
BLIND_ROUND_PATH = ROOT / "scripts" / "benchmark" / "fiction_quality_blind_round.py"
BOOK_SWEEP_PATH = ROOT / "scripts" / "benchmark" / "book_quality_sweep.py"
REFERENCE_SWEEP_PATH = ROOT / "scripts" / "benchmark" / "reference_book_quality_sweep.py"
AI_DETECTION_COMPARISON_PATH = ROOT / "scripts" / "benchmark" / "ai_detection_comparison.py"
WRITING_RUBRIC_COUNCIL_PATH = ROOT / "scripts" / "benchmark" / "writing_rubric_council.py"
PACKAGE_JSON_PATH = ROOT / "packages" / "scbe-fiction-quality" / "package.json"
PACKAGE_BIN_PATH = ROOT / "packages" / "scbe-fiction-quality" / "bin" / "scbe-fiction-quality.cjs"


def _load_module():
    spec = importlib.util.spec_from_file_location("fiction_quality_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_seed_rows_score_and_flag_generic_ai_weirdness() -> None:
    module = _load_module()
    config = module.load_config(CONFIG_PATH)
    rows = module.load_jsonl(SEED_PATH)

    results = [module.score_row(row, config) for row in rows]
    by_id = {row["id"]: row for row in results}

    assert by_id["fq_seed_001"]["score"] > by_id["fq_seed_002"]["score"]
    assert by_id["fq_seed_002"]["decision"] == "HOLD"
    assert by_id["fq_seed_002"]["diagnostics"]["forbidden_hits"]
    assert by_id["fq_seed_003"]["decision"] == "PASS"
    assert "null_space_structure" in by_id["fq_seed_001"]["dimension_scores"]
    assert by_id["fq_seed_001"]["diagnostics"]["null_space_marker_hits"]["boundary"]
    assert "thought_track_composition" in by_id["fq_seed_001"]["dimension_scores"]
    assert by_id["fq_seed_001"]["diagnostics"]["thought_track_sheet"]["track_coverage"] >= 3
    assert (
        by_id["fq_seed_002"]["ai_detection"]["ai_likelihood_score"]
        > by_id["fq_seed_001"]["ai_detection"]["ai_likelihood_score"]
    )
    assert by_id["fq_seed_002"]["ai_detection"]["label"] in {"mixed_or_uncertain", "likely_ai_generated"}


def test_alliteration_pressure_is_scored_without_banning_sound() -> None:
    module = _load_module()
    row = {
        "id": "alliteration_test",
        "prompt": "Write a grounded sentence.",
        "response": "Soft silver static settled, then Mara shut the panel and breathed.",
        "constraints": {"min_words": 8, "max_words": 40, "required_terms": ["Mara"]},
    }

    result = module.score_row(row, module.load_config(CONFIG_PATH))

    assert result["diagnostics"]["alliteration"]["runs"] >= 1
    assert result["dimension_scores"]["rhythm_and_sound_control"] >= 7.0


def test_thought_track_sheet_scores_chord_progression() -> None:
    module = _load_module()
    row = {
        "id": "thought_track_test",
        "prompt": "Write a grounded micro-scene.",
        "response": (
            "Rain hit the glass while Mara remembered the old rule. "
            "She reached for the handle, stopped, and listened. "
            "Then she chose the safer door and breathed."
        ),
        "constraints": {"min_words": 20, "max_words": 80, "required_terms": ["Mara"]},
    }

    result = module.score_row(row, module.load_config(CONFIG_PATH))
    sheet = result["diagnostics"]["thought_track_sheet"]

    assert sheet["track_coverage"] >= 4
    assert sheet["has_resolution"] is True
    assert result["dimension_scores"]["thought_track_composition"] >= 7.0


def test_benchmark_writes_report(tmp_path: Path) -> None:
    module = _load_module()

    payload = module.run_benchmark(input_path=SEED_PATH, config_path=CONFIG_PATH, output_root=tmp_path)

    assert payload["schema_version"] == "scbe_fiction_quality_benchmark_report_v1"
    assert payload["row_count"] == 3
    assert payload["pass_count"] >= 1
    assert Path(payload["artifact_paths"]["json"]).exists()
    assert Path(payload["artifact_paths"]["markdown"]).exists()


def test_cli_runs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/fiction_quality_benchmark.py",
            "--input",
            str(SEED_PATH),
            "--config",
            str(CONFIG_PATH),
            "--output-root",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["kaggle_shape"]["submission_columns"] == ["id", "score"]


def test_blind_round_scores_public_ai_and_own_book_in_same_run(tmp_path: Path) -> None:
    module = _load_module()
    spec = importlib.util.spec_from_file_location("fiction_quality_blind_round", BLIND_ROUND_PATH)
    assert spec and spec.loader
    blind_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = blind_module
    spec.loader.exec_module(blind_module)

    payload = blind_module.run_blind_round(config_path=CONFIG_PATH, output_root=tmp_path)

    assert payload["sample_count"] == 8
    assert payload["groups"]["public_domain"]["count"] == 5
    assert payload["groups"]["known_ai_writing"]["count"] == 2
    assert payload["groups"]["own_book"]["count"] == 1
    assert "ai_likelihood_average" in payload["groups"]["public_domain"]
    assert "false_positive_or_uncertain_count" in payload["groups"]["public_domain"]
    assert len(payload["ranking"]) == 8
    assert all("blind_id" in row for row in payload["rows"])
    assert all("ai_detection_label" in row for row in payload["rows"])
    assert any(row["reveal"]["source_id"] == "own_six_tongues_ch01" for row in payload["rows"])
    assert (tmp_path / "fiction_quality_blind_round_latest.json").exists()


def test_blind_round_cli_runs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/fiction_quality_blind_round.py",
            "--config",
            str(CONFIG_PATH),
            "--output-root",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert {"public_domain", "known_ai_writing", "own_book"} == set(payload["groups"])


def test_fiction_quality_package_metadata_ready_for_npm() -> None:
    payload = json.loads(PACKAGE_JSON_PATH.read_text(encoding="utf-8"))

    assert payload["name"] == "scbe-fiction-quality"
    assert payload["bin"]["scbe-fiction-quality"] == "bin/scbe-fiction-quality.cjs"
    assert payload["repository"]["directory"] == "packages/scbe-fiction-quality"
    assert "fiction" in payload["keywords"]
    assert "benchmark" in payload["keywords"]
    assert PACKAGE_BIN_PATH.exists()


def test_fiction_quality_node_wrapper_help() -> None:
    if shutil.which("node") is None:
        return

    proc = subprocess.run(
        ["node", str(PACKAGE_BIN_PATH), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=30,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "scbe-fiction-quality" in proc.stdout
    assert "blind-round" in proc.stdout


def test_book_quality_sweep_cli_runs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(BOOK_SWEEP_PATH),
            "--book-root",
            "content/book/reader-edition",
            "--output-root",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_book_quality_sweep_v1"
    assert payload["sample_count"] >= 3
    assert payload["weakest_samples"]
    assert payload["highest_ai_likelihood_samples"]


def test_reference_book_splitter_uses_chapter_headings(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("reference_book_quality_sweep", REFERENCE_SWEEP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    sample = """*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE ***\n\nLetter 1\nOne.\n\nChapter 1\nTwo.\n\n*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE ***"""
    clean = module._strip_gutenberg_boilerplate(sample)
    chapters = module._split_chapters(clean)

    assert [name for name, _ in chapters] == ["001-letter-1.md", "002-chapter-1.md"]


def test_reference_book_sweep_keeps_generic_book_latest_separate(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("reference_book_quality_sweep", REFERENCE_SWEEP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module._download_text = lambda _url: (
        "*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE ***\n\n"
        "Letter 1\nRain hit the glass while Mara remembered the old rule. "
        "She reached for the handle, stopped, listened, and chose the safer door.\n\n"
        "Chapter 1\nThe road bent under the storm. The witness raised a lantern, "
        "marked the boundary, and waited for the answer.\n\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE ***"
    )

    payload = module.run_reference_sweep(
        source_url="https://example.test/sample.txt",
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "out",
        title="Sample",
        author="Test Author",
        refresh=True,
    )

    assert payload["report_summary"]["sample_count"] == 2
    assert (tmp_path / "out" / "reference_book_quality_sweep_latest.json").exists()
    assert not (tmp_path / "out" / "book_quality_sweep_latest.json").exists()
    assert (tmp_path / "cache" / "sweep" / "book_quality_sweep_latest.json").exists()


def test_ai_detection_comparison_reports_reference_false_positive_floor(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("ai_detection_comparison", AI_DETECTION_COMPARISON_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    own_path = tmp_path / "own.json"
    reference_path = tmp_path / "reference.json"
    blind_round_path = tmp_path / "blind.json"
    own_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "id": "own:opening",
                        "score": 70.0,
                        "ai_likelihood_score": 12.0,
                        "ai_detection_label": "likely_human_or_human_edited",
                        "passage": "Rain hit the glass. Mara chose the safer door.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    reference_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "id": "reference:opening",
                        "score": 68.0,
                        "ai_likelihood_score": 25.0,
                        "ai_detection_label": "likely_human_or_human_edited",
                        "passage": "It was on a dreary night that the work approached its end.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    blind_round_path.write_text(
        json.dumps(
            {
                "groups": {
                    "known_ai_writing": {"false_negative_count": 1, "ai_likelihood_average": 47.0},
                    "public_domain": {"false_positive_or_uncertain_count": 0, "ai_likelihood_average": 23.0},
                }
            }
        ),
        encoding="utf-8",
    )

    payload = module.compare_detection(
        own_path=own_path,
        reference_path=reference_path,
        blind_round_path=blind_round_path,
        output_root=tmp_path / "out",
        detector="local",
    )

    assert payload["detector_status"]["ok"] is True
    assert payload["summaries"]["reference_book"]["average_ai_likelihood"] == 25.0
    assert payload["comparison"]["own_minus_reference_ai_likelihood"] == -13.0
    assert payload["calibration_gate"]["status"] == "UNDER_SENSITIVE"
    assert (tmp_path / "out" / "ai_detection_comparison_local_latest.json").exists()


def test_writing_rubric_council_separates_quality_detection_and_mimicry(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("writing_rubric_council", WRITING_RUBRIC_COUNCIL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    own_path = tmp_path / "own.json"
    reference_path = tmp_path / "reference.json"
    detection_path = tmp_path / "detection.json"
    blind_round_path = tmp_path / "blind.json"
    own_path.write_text(
        json.dumps(
            {
                "chapter_summary": {"own.md": {"minimum_score": 66.0, "average_ai_likelihood": 18.0}},
                "rows": [{"id": "own:full", "score": 74.0, "ai_likelihood_score": 32.0, "chapter_path": "own.md"}],
            }
        ),
        encoding="utf-8",
    )
    reference_path.write_text(
        json.dumps(
            {
                "chapter_summary": {"ref.md": {"minimum_score": 61.0, "average_ai_likelihood": 22.0}},
                "rows": [{"id": "ref:full", "score": 68.0, "ai_likelihood_score": 24.0, "chapter_path": "ref.md"}],
            }
        ),
        encoding="utf-8",
    )
    detection_path.write_text(
        json.dumps(
            {
                "calibration_gate": {
                    "status": "UNDER_SENSITIVE",
                    "known_ai_false_negative_count": 1,
                    "public_domain_false_positive_or_uncertain_count": 0,
                },
                "summaries": {
                    "own_book": {"average_ai_likelihood": 32.0},
                    "reference_book": {"average_ai_likelihood": 24.0},
                },
            }
        ),
        encoding="utf-8",
    )
    blind_round_path.write_text(
        json.dumps(
            {
                "groups": {
                    "known_ai_writing": {"false_negative_count": 1, "ai_likelihood_average": 50.0},
                    "public_domain": {"false_positive_or_uncertain_count": 0, "ai_likelihood_average": 24.0},
                }
            }
        ),
        encoding="utf-8",
    )

    payload = module.run_council(
        own_path=own_path,
        reference_path=reference_path,
        detection_path=detection_path,
        blind_round_path=blind_round_path,
        output_root=tmp_path / "out",
    )

    assert payload["promotion_decision"] == "PROMOTE_QUALITY_GATE_ONLY"
    assert payload["decisions"]["quality_editor"] == "PASS"
    assert payload["decisions"]["detector_skeptic"] == "FAIL"
    assert payload["mimicry_boundary"]["humanity"].startswith("A detector cannot prove")
    assert "instrument panel" in payload["mimicry_boundary"]["embodiment"]
    assert payload["triangulation_target"]["imagination_lane"].startswith("REWARD")
    assert (tmp_path / "out" / "writing_rubric_council_latest.json").exists()
