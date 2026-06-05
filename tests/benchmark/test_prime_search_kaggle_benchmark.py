from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "prime_search_kaggle_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("prime_search_kaggle_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_score_submission_prefers_perfect_ranker() -> None:
    module = _load_module()
    solution = [
        {"id": "a", "is_twin_prime": 1},
        {"id": "b", "is_twin_prime": 0},
        {"id": "c", "is_twin_prime": 1},
    ]
    perfect = [
        {"id": "a", "score": 1.0},
        {"id": "b", "score": 0.0},
        {"id": "c", "score": 0.9},
    ]
    weak = [
        {"id": "a", "score": 0.1},
        {"id": "b", "score": 1.0},
        {"id": "c", "score": 0.0},
    ]

    assert module.score_submission_rows(solution, perfect)["average_precision"] == 1.0
    assert module.score_submission_rows(solution, weak)["average_precision"] < 1.0


def test_build_assets_keeps_test_labels_hidden(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_assets(
        out_dir=tmp_path,
        seed_limit=100,
        limit=300,
        split=180,
        bins=24,
        top=20,
        kaggle_id="issacizrealdavis/scbe-prime-search-benchmark-test",
        title="SCBE Prime Search Benchmark Test",
        kaggle_profile_url=None,
    )

    public_dir = Path(report["paths"]["public_dataset"])
    scoring_dir = Path(report["paths"]["local_scoring"])
    assert report["schema_version"] == module.SCHEMA_VERSION
    assert report["summary"]["decision"] == "READY"
    assert (public_dir / "dataset-metadata.json").exists()
    assert (public_dir / "README.md").exists()
    assert (public_dir / "USER_PROFILE.md").exists()
    assert (public_dir / "PROFILE.md").exists()
    assert (public_dir / "benchmark_studio" / "prime_search_branch_ranker_task.py").exists()
    assert (scoring_dir / "solution.csv").exists()
    assert (scoring_dir / "baselines" / "abc_product.csv").exists()
    assert (tmp_path / "kaggle_code" / "kernel.py").exists()
    assert (tmp_path / "kaggle_code" / "kernel-metadata.json").exists()
    assert report["kaggle"]["owner"] == "issacizrealdavis"
    assert report["kaggle"]["owner_profile_url"] == "https://www.kaggle.com/issacizrealdavis"

    train_rows = _read_csv(public_dir / "train.csv")
    test_rows = _read_csv(public_dir / "test.csv")
    sample_rows = _read_csv(public_dir / "sample_submission.csv")
    assert "is_twin_prime" in train_rows[0]
    assert "is_twin_prime" not in test_rows[0]
    assert set(sample_rows[0]) == {"id", "score"}
    assert report["summary"]["test_positive_count"] > 0


def test_cli_build_and_score_smoke(tmp_path: Path) -> None:
    build = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--out-dir",
            str(tmp_path),
            "--seed-limit",
            "100",
            "--limit",
            "300",
            "--split",
            "180",
            "--bins",
            "24",
            "--top",
            "20",
            "--kaggle-profile-url",
            "https://www.kaggle.com/issacizrealdavis",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=90,
    )
    assert build.returncode == 0, build.stderr
    report = json.loads(build.stdout)
    assert report["summary"]["decision"] == "READY"

    score = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--out-dir",
            str(tmp_path),
            "--score-submission",
            str(tmp_path / "local_scoring" / "baselines" / "abc_product.csv"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    assert score.returncode == 0, score.stderr
    metrics = json.loads(score.stdout)
    assert metrics["row_count"] == report["summary"]["test_count"]
    assert 0.0 <= metrics["average_precision"] <= 1.0
