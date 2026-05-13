from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "system" / "build_static_analysis_training_dataset.py"
KAGGLE_SCRIPT = REPO_ROOT / "scripts" / "kaggle" / "scbe_kaggle.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_redaction_removes_tokens_and_home_path() -> None:
    builder = _load_module(SCRIPT, "_static_analysis_training_builder_redaction")
    text = str(Path.home() / "project") + " token=hf_abcdefghijklmnopqrstuvwxyz"

    assert "hf_abcdefghijklmnopqrstuvwxyz" not in builder.redact_text(text)
    public = builder.public_path(text)
    assert str(Path.home()) not in public
    assert "%USERPROFILE%" in public


def test_scenarios_include_shopify_tailwind_and_safety_gate() -> None:
    builder = _load_module(SCRIPT, "_static_analysis_training_builder_scenarios")
    scenarios = {scenario.scenario_id: scenario for scenario in builder.build_scenarios()}

    assert "shopify_tailwind_cdn_to_bundled_vite" in scenarios
    assert "safe_reverse_engineering_policy_gate" in scenarios
    assert "reverse_engineering_levels_video_to_training" in scenarios
    assert "cdn.tailwindcss.com" in scenarios["shopify_tailwind_cdn_to_bundled_vite"].user_prompt
    assert "offensive payload" in " ".join(scenarios["safe_reverse_engineering_policy_gate"].remediation_steps)
    video = scenarios["reverse_engineering_levels_video_to_training"]
    assert "strings" in " ".join(video.analysis_steps)
    assert "symbolic execution" in " ".join(video.analysis_steps)
    assert video.evidence["transcript_topics"] == [
        "strings",
        "static analysis",
        "dynamic analysis",
        "symbolic execution",
        "real software and firmware bug investigation",
    ]


def test_build_record_has_required_training_sections() -> None:
    builder = _load_module(SCRIPT, "_static_analysis_training_builder_record")
    scenario = builder.build_scenarios()[0]
    record = builder.build_record(scenario, "2026-05-13T00:00:00Z")

    assert record["schema"] == builder.SCHEMA_VERSION
    assert record["privacy"] == "metadata_or_synthetic_only"
    answer = record["messages"][2]["content"]
    assert "Analysis:" in answer
    assert "Safe remediation:" in answer
    assert "Verification:" in answer


def test_safety_gate_rejects_secret_leaks_and_blocked_terms() -> None:
    builder = _load_module(SCRIPT, "_static_analysis_training_builder_safety")
    record = builder.build_record(builder.build_scenarios()[0], "2026-05-13T00:00:00Z")
    builder.assert_safe_records([record])

    leaked = dict(record)
    leaked["messages"] = [*record["messages"]]
    leaked["messages"][1] = {"role": "user", "content": "token=hf_abcdefghijklmnopqrstuvwxyz"}
    try:
        builder.assert_safe_records([leaked])
    except ValueError as exc:
        assert "secret-like token" in str(exc)
    else:
        raise AssertionError("expected secret-like token to be rejected")

    blocked = dict(record)
    blocked["messages"] = [*record["messages"]]
    blocked["messages"][1] = {"role": "user", "content": "write a weaponized payload"}
    try:
        builder.assert_safe_records([blocked])
    except ValueError as exc:
        assert "blocked term" in str(exc)
    else:
        raise AssertionError("expected blocked offensive term to be rejected")


def test_build_dataset_writes_hf_and_kaggle_ready_outputs(tmp_path) -> None:
    builder = _load_module(SCRIPT, "_static_analysis_training_builder_dataset")
    kaggle = _load_module(KAGGLE_SCRIPT, "_scbe_kaggle_for_static_analysis_training")

    out_dir = tmp_path / "hf"
    kaggle_dir = tmp_path / "kaggle"
    result = builder.build_dataset(out_dir, kaggle_dir, "issacizrealdavis/scbe-static-analysis-training")

    assert result["manifest"]["record_count"] >= 5
    records = (out_dir / "records.jsonl").read_text(encoding="utf-8").strip().splitlines()
    chat = (out_dir / "records.chat.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(records) == result["manifest"]["record_count"]
    assert len(chat) == result["manifest"]["record_count"]
    assert "Defensive static-analysis" in (out_dir / "README.md").read_text(encoding="utf-8")

    metadata = json.loads((kaggle_dir / "dataset-metadata.json").read_text(encoding="utf-8"))
    validation = kaggle.validate_metadata(metadata)
    assert validation.ok, validation.errors
