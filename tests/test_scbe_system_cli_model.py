from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def _run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _write_jsonl(path: Path, *rows: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def test_model_plan_reports_dataset_counts_from_profile(tmp_path: Path) -> None:
    dataset_root = tmp_path / "datasets"
    _write_jsonl(
        dataset_root / "train.jsonl",
        {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
        {"instruction": "write code", "output": "print('x')"},
    )
    _write_jsonl(
        dataset_root / "eval.jsonl",
        {"prompt": "sum two ints", "completion": "def add(a, b): return a + b"},
    )
    profile_path = tmp_path / "coder-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_model_training_profile_v1",
                "profile_id": "tmp-coder",
                "title": "Tmp coder profile",
                "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                "system_prompt": "You are a coding assistant.",
                "dataset": {
                    "root": str(dataset_root),
                    "train_files": ["train.jsonl"],
                    "eval_files": ["eval.jsonl"],
                },
                "training": {"output_dir": str(tmp_path / "runs" / "tmp-coder")},
                "execution": {"default_emit_path": str(tmp_path / "artifacts" / "tmp-coder-train.py")},
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    result = _run_cli("model", "plan", "--profile-path", str(profile_path), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_model_training_plan_v1"
    assert payload["profile_id"] == "tmp-coder"
    assert payload["total_train_rows"] == 2
    assert payload["total_eval_rows"] == 1
    assert payload["ready"] is True
    assert payload["train_datasets"][0]["sample_keys"] == ["messages"]


def test_model_train_emits_runnable_script(tmp_path: Path) -> None:
    dataset_root = tmp_path / "datasets"
    _write_jsonl(
        dataset_root / "train.jsonl",
        {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
    )
    profile_path = tmp_path / "coder-profile.json"
    emit_path = tmp_path / "artifacts" / "tmp-coder-train.py"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_model_training_profile_v1",
                "profile_id": "tmp-coder",
                "title": "Tmp coder profile",
                "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                "system_prompt": "You are a coding assistant.",
                "dataset": {
                    "root": str(dataset_root),
                    "train_files": ["train.jsonl"],
                    "eval_files": [],
                },
                "training": {"output_dir": str(tmp_path / "runs" / "tmp-coder")},
                "execution": {"default_emit_path": str(emit_path)},
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    result = _run_cli(
        "model",
        "train",
        "--profile-path",
        str(profile_path),
        "--emit-script",
        str(emit_path),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_model_train_v1"
    assert payload["executed"] is False
    assert Path(payload["script_path"]).exists()
    script_text = Path(payload["script_path"]).read_text(encoding="utf-8")
    assert "PROFILE =" in script_text
    assert "Qwen/Qwen2.5-Coder-7B-Instruct" in script_text
    assert "TRAIN_FILES =" in script_text
    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(Path(payload["script_path"]))],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compile_result.returncode == 0, compile_result.stderr


def _load_training_lane_module():
    module_path = ROOT / "scripts" / "model_training_lane.py"
    spec = importlib.util.spec_from_file_location("test_model_training_lane_runtime", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_training_preflight_recommends_non_local_when_runtime_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_training_lane_module()
    dataset_root = tmp_path / "datasets"
    _write_jsonl(
        dataset_root / "train.jsonl",
        {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
    )
    profile_path = tmp_path / "coder-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_model_training_profile_v1",
                "profile_id": "tmp-coder",
                "title": "Tmp coder profile",
                "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                "dataset": {
                    "root": str(dataset_root),
                    "train_files": ["train.jsonl"],
                    "eval_files": [],
                },
                "execution": {"recommended_target": "local-gpu-or-colab"},
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "_dependency_status", lambda name: {"name": name, "available": name != "unsloth"})
    monkeypatch.setattr(
        module,
        "_inspect_torch_runtime",
        lambda: {
            "available": True,
            "version": "test",
            "cuda_available": True,
            "device_count": 1,
            "devices": [{"index": 0, "name": "Tiny GPU", "total_vram_mb": 4096}],
            "total_vram_mb": 4096,
        },
    )
    monkeypatch.setattr(
        module,
        "_inspect_nvidia_smi",
        lambda: {
            "available": True,
            "devices": [{"index": 0, "name": "Tiny GPU", "total_vram_mb": 4096}],
            "total_vram_mb": 4096,
        },
    )
    monkeypatch.delenv("HF_TOKEN", raising=False)

    payload = module.build_training_preflight(ROOT, profile_path)
    assert payload["schema_version"] == "scbe_model_preflight_v1"
    assert payload["local"]["ready"] is False
    assert payload["decision"]["execution_target"] == "colab"
    assert "missing-dependency:unsloth" in payload["decision"]["rationale"]
    assert payload["toolchain"]["profile"]["exists"] is True
    assert payload["toolchain"]["colab_catalog"]["exists"] is True
    assert payload["toolchain"]["colab_notebooks"]["qlora"]["exists"] is True
    assert payload["next_steps"][0]["kind"] == "emit-script"
    assert payload["next_steps"][1]["kind"] == "colab-notebook"


def test_model_preflight_reports_execution_target(tmp_path: Path) -> None:
    dataset_root = tmp_path / "datasets"
    _write_jsonl(
        dataset_root / "train.jsonl",
        {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
    )
    profile_path = tmp_path / "coder-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_model_training_profile_v1",
                "profile_id": "tmp-coder",
                "title": "Tmp coder profile",
                "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                "dataset": {
                    "root": str(dataset_root),
                    "train_files": ["train.jsonl"],
                    "eval_files": [],
                },
                "execution": {"recommended_target": "local-gpu-or-colab"},
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    result = _run_cli("model", "preflight", "--profile-path", str(profile_path), "--json", timeout=120)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_model_preflight_v1"
    assert payload["profile_id"] == "tmp-coder"
    assert payload["decision"]["execution_target"] in {"local", "colab", "hf-jobs", "emit-only"}
    assert "dependencies" in payload
    assert "local" in payload
    assert "toolchain" in payload
    assert payload["next_steps"][0]["kind"] == "emit-script"
