from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "build_training_surface_sync_plan.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_training_surface_sync_plan_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_profile_plan_marks_existing_dataset_files_ready(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    data_dir = tmp_path / "training-data" / "sft"
    data_dir.mkdir(parents=True)
    (data_dir / "train.jsonl").write_text('{"messages":[]}\n', encoding="utf-8")
    (data_dir / "eval.jsonl").write_text('{"messages":[]}\n', encoding="utf-8")
    profile_path = tmp_path / "config" / "model_training" / "profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "ready-profile",
                "base_model": "Qwen/example",
                "dataset": {
                    "root": "training-data/sft",
                    "train_files": ["train.jsonl"],
                    "eval_files": ["eval.jsonl"],
                },
                "hub": {
                    "dataset_repo": "owner/dataset",
                    "adapter_repo": "owner/adapter",
                },
                "execution": {"recommended_target": "hf-jobs", "hf_flavor": "t4-small"},
            }
        ),
        encoding="utf-8",
    )

    plan = module.build_profile_plan(profile_path)

    assert plan["safe_to_dispatch"] is True
    assert plan["missing_files"] == []
    assert "hf upload owner/dataset training-data/sft/train.jsonl train.jsonl --repo-type dataset" in {
        item["upload_command"] for item in plan["dataset_files"]
    }
    assert "dispatch_coding_agent_hf_job.py plan" in plan["preflight_command"]


def test_build_profile_plan_blocks_missing_dataset_repo(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    data_dir = tmp_path / "training-data" / "sft"
    data_dir.mkdir(parents=True)
    (data_dir / "train.jsonl").write_text('{"messages":[]}\n', encoding="utf-8")
    profile_path = tmp_path / "config" / "model_training" / "profile.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "missing-dataset-repo",
                "base_model": "Qwen/example",
                "dataset": {"root": "training-data/sft", "train_files": ["train.jsonl"]},
                "hub": {"adapter_repo": "owner/adapter"},
            }
        ),
        encoding="utf-8",
    )

    plan = module.build_profile_plan(profile_path)

    assert plan["safe_to_dispatch"] is False
    assert plan["missing_config"] == ["hub.dataset_repo"]
    assert plan["dataset_files"][0]["upload_command"] == "BLOCKED: profile hub.dataset_repo is missing"


def test_build_sync_plan_filters_ready_specialist_profiles(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_load_kaggle_rounds", lambda: {})

    data_dir = tmp_path / "training-data" / "sft"
    data_dir.mkdir(parents=True)
    (data_dir / "train.jsonl").write_text('{"messages":[]}\n', encoding="utf-8")

    profile_path = tmp_path / "config" / "model_training" / "operator.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "operator",
                "base_model": "Qwen/example",
                "dataset": {"root": "training-data/sft", "train_files": ["train.jsonl"]},
                "hub": {"dataset_repo": "owner/dataset", "adapter_repo": "owner/adapter"},
            }
        ),
        encoding="utf-8",
    )
    source_plan = tmp_path / "consolidation_plan.json"
    source_plan.write_text(
        json.dumps(
            {
                "specialists": [
                    {
                        "status": "ready_for_training",
                        "profile_candidates": ["config/model_training/operator.json"],
                    },
                    {
                        "status": "blocked_no_train_records",
                        "profile_candidates": ["config/model_training/blocked.json"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    plan = module.build_sync_plan(source_plan)

    assert [item["profile_id"] for item in plan["profile_jobs"]] == ["operator"]
    assert "config/model_training/blocked.json" in plan["missing_profile_candidates"]


def test_render_markdown_includes_dispatch_and_kaggle_commands() -> None:
    module = _load_module()
    plan = {
        "generated_at_utc": "2026-04-26T00:00:00+00:00",
        "rule": "no launch by default",
        "local_preflight_commands": ["python local.py"],
        "profile_jobs": [
            {
                "profile_id": "operator",
                "safe_to_dispatch": True,
                "profile_path": "config/profile.json",
                "base_model": "Qwen/example",
                "dataset_repo": "owner/dataset",
                "adapter_repo": "owner/adapter",
                "missing_files": [],
                "dataset_files": [
                    {
                        "upload_command": "hf upload owner/dataset training-data/sft/train.jsonl train.jsonl --repo-type dataset",
                        "split": "train",
                        "exists": True,
                    }
                ],
                "preflight_command": "python plan.py",
                "dispatch_command": "python dispatch.py",
            }
        ],
        "missing_profile_candidates": [],
        "kaggle_rounds": [
            {
                "round": "geoseal",
                "description": "round",
                "base_model": "Qwen/example",
                "hf_repo": "owner/model",
                "launch_command": "python kaggle.py",
                "status_command": "python status.py",
                "pull_command": "python pull.py",
            }
        ],
        "post_run_commands": ["python verify.py"],
    }

    markdown = module.render_markdown(plan)

    assert "HF" not in markdown[:10]
    assert "hf upload owner/dataset" in markdown
    assert "python dispatch.py" in markdown
    assert "python kaggle.py" in markdown


def test_render_markdown_labels_config_blocked_uploads() -> None:
    module = _load_module()
    plan = {
        "generated_at_utc": "2026-04-26T00:00:00+00:00",
        "rule": "no launch by default",
        "local_preflight_commands": [],
        "profile_jobs": [
            {
                "profile_id": "blocked",
                "safe_to_dispatch": False,
                "profile_path": "config/profile.json",
                "base_model": "Qwen/example",
                "dataset_repo": "",
                "adapter_repo": "owner/adapter",
                "missing_files": [],
                "missing_config": ["hub.dataset_repo"],
                "dataset_files": [
                    {
                        "upload_command": "BLOCKED: profile hub.dataset_repo is missing",
                        "split": "train",
                        "exists": True,
                    }
                ],
                "preflight_command": "python plan.py",
                "dispatch_command": "python dispatch.py",
            }
        ],
        "missing_profile_candidates": [],
        "kaggle_rounds": [],
        "post_run_commands": [],
    }

    markdown = module.render_markdown(plan)

    assert "CONFIG-BLOCKED" in markdown
