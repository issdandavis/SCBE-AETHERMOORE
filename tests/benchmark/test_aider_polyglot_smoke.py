from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "aider_polyglot_smoke.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aider_polyglot_smoke", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_aider_polyglot_plan_report_is_non_scoring(tmp_path: Path) -> None:
    module = _load_module()
    fake_aider = tmp_path / "aider"
    fake_polyglot = fake_aider / "tmp.benchmarks" / "polyglot-benchmark"
    report = module.build_report(
        aider_root=fake_aider,
        polyglot_root=fake_polyglot,
        output_root=tmp_path / "out",
        execute=False,
    )
    payload = report["payload"]

    assert payload["schema_version"] == "scbe_aider_polyglot_smoke_v1"
    assert payload["execute"] is False
    assert payload["download_polyglot"] is False
    assert payload["polyglot_repo_url"] == "https://github.com/Aider-AI/polyglot-benchmark.git"
    assert payload["full_scoring_ready"] is False
    assert "not a public leaderboard score" in payload["claim_allowed"]
    assert "Aider checkout is missing benchmark/benchmark.py." in payload["blockers"]
    assert Path(report["json"]).exists()
    assert Path(report["markdown"]).exists()


def test_aider_polyglot_language_inventory(tmp_path: Path) -> None:
    module = _load_module()
    polyglot = tmp_path / "polyglot-benchmark"
    for language in ["cpp", "go", "java", "javascript", "python", "rust"]:
        language_path = polyglot / language
        language_path.mkdir(parents=True)
        (language_path / "README.md").write_text(language, encoding="utf-8")

    inventory = module.inspect_polyglot(polyglot)

    assert inventory["present"] is True
    assert inventory["complete_language_set"] is True
    assert inventory["language_count"] == 6
    assert inventory["file_count"] == 6


def test_aider_polyglot_cli_plan_only(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/aider_polyglot_smoke.py",
            "--output-root",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode in {0, 1}
    payload = json.loads(proc.stdout)
    assert payload["execute"] is False
    assert payload["full_scoring_ready"] is False
    assert payload["json"].endswith("latest_aider_polyglot_smoke.json")
