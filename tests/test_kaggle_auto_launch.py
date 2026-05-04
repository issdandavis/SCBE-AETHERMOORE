from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "kaggle_auto" / "launch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("kaggle_auto_launch", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_kernel_config(script: str) -> dict:
    marker = "KERNEL_CONFIG = '"
    start = script.index(marker) + len(marker)
    end = script.index("'\n# ==================================================", start)
    return json.loads(script[start:end])


def test_geoseal_stage6_repair_round_targets_profile_dataset_and_repo() -> None:
    module = _load_module()
    config = module.ROUNDS["geoseal-stage6-repair-v7"]

    assert config["base_model"] == "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    assert config["hf_dataset_repo"] == "issdandavis/scbe-coding-agent-sft-stage6-repair-v7"
    assert config["kaggle_dataset"] == "issacizrealdavis/scbe-coding-agent-stage6-repair-v7"
    assert config["hf_repo"] == "issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-kaggle"
    assert "atomic_workflow_stage6_repair_train.sft.jsonl" in config["files"]


def test_generated_kernel_config_preserves_t4_safe_stage6_settings() -> None:
    module = _load_module()

    script = module.generate_kernel_script("geoseal-stage6-repair-v7", module.ROUNDS["geoseal-stage6-repair-v7"])
    payload = _extract_kernel_config(script)

    assert payload["hf_dataset_repo"] == "issdandavis/scbe-coding-agent-sft-stage6-repair-v7"
    assert payload["kaggle_dataset"] == "issacizrealdavis/scbe-coding-agent-stage6-repair-v7"
    assert payload["batch_size"] == 1
    assert payload["grad_accum"] == 16
    assert payload["max_length"] == 768
    assert payload["max_steps"] == 360
    assert payload["learning_rate"] == 8e-5
    assert payload["max_records"] == 3950


def test_tokenizer_probe_kernel_is_status_instrumented() -> None:
    module = _load_module()

    script = module.tokenizer_probe_script()

    assert "TOKENIZERS_PARALLELISM" in script
    assert "downloading_tokenizer_config" in script
    assert "snapshot_tokenizer_files" in script
    assert "loading_slow_tokenizer" in script
    assert "loading_fast_tokenizer" in script
    assert "ERROR.json" in script


def test_kaggle_cli_runner_uses_utf8_replacement(monkeypatch) -> None:
    module = _load_module()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="ref,title\nuser/polly-auto,smart quote \u201d\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module._run_kaggle(["kernels", "list", "--mine", "--csv"])

    assert result.returncode == 0
    assert calls == [
        (
            ["kaggle", "kernels", "list", "--mine", "--csv"],
            {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"},
        )
    ]


def test_list_mine_rows_handles_unicode_csv(monkeypatch) -> None:
    module = _load_module()

    def fake_run_kaggle(args):
        assert args == ["kernels", "list", "--mine", "--csv"]
        return subprocess.CompletedProcess(
            ["kaggle", *args],
            0,
            stdout="ref,title\nissacizrealdavis/polly-auto-coding-approval-metrics-v1,AI \u2014 ready\n",
            stderr="",
        )

    monkeypatch.setattr(module, "_run_kaggle", fake_run_kaggle)

    rows = module.list_mine_rows()

    assert rows == [
        {
            "ref": "issacizrealdavis/polly-auto-coding-approval-metrics-v1",
            "title": "AI \u2014 ready",
        }
    ]


def test_configure_console_encoding_is_fail_soft(monkeypatch) -> None:
    module = _load_module()
    calls = []

    class FakeStream:
        def reconfigure(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(module.sys, "stdout", FakeStream())
    monkeypatch.setattr(module.sys, "stderr", FakeStream())

    module._configure_console_encoding()

    assert calls == [
        {"encoding": "utf-8", "errors": "replace"},
        {"encoding": "utf-8", "errors": "replace"},
    ]
