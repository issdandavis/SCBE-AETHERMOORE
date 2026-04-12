from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def test_repo_ships_ollama_agentic_handler_profile() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--repo-root",
            str(ROOT),
            "model",
            "show-config",
            "--profile",
            "ollama-agentic-handler",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    profile = payload["profile"]

    assert payload["schema_version"] == "scbe_model_profile_v1"
    assert profile["profile_id"] == "ollama-agentic-handler"
    assert profile["base_model"] == "Qwen/Qwen2.5-Coder-7B-Instruct"
    assert profile["hub"]["token_env"] == "HF_TOKEN"
    assert profile["execution"]["default_emit_path"].endswith("ollama-agentic-handler-train.py")
    assert profile["runtime"]["provider"] == "ollama"
    assert profile["runtime"]["model"] == "qwen2.5-coder:7b"
    assert profile["runtime"]["base_url"] == "http://localhost:11434/v1"
