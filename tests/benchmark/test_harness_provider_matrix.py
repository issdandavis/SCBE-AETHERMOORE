from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.benchmark.harness_provider_matrix import build_provider_matrix

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_provider_matrix_reports_lane_switch_costs() -> None:
    report = build_provider_matrix(["ollama:a", "deepseek:b", "ollama:c"])

    assert report["schema_version"] == "scbe_harness_provider_matrix_v1"
    assert report["model_count"] == 3
    cross = next(pair for pair in report["pairs"] if pair["lane_path"] == ["ollama", "deepseek"])
    assert cross["signal_required"] is True
    assert cross["ok_without_signal"] is False
    assert cross["ok_with_recommended_signal"] is True

    same = next(pair for pair in report["pairs"] if pair["lane_path"] == ["ollama", "ollama"])
    assert same["signal_required"] is False
    assert same["cost"] == 0
    assert report["provider_count"] >= 18
    assert report["providers"]["groq"]["pricing_tier"] == "free-tier"
    assert report["providers"]["gemini"]["chat_url"].endswith("/openai/chat/completions")
    assert report["providers"]["nvidia"]["chat_url"] == "https://integrate.api.nvidia.com/v1/chat/completions"


def test_provider_matrix_surfaces_pricing_capabilities_and_docs() -> None:
    report = build_provider_matrix(["groq:llama-3.3-70b-versatile", "gemini:gemini-2.5-flash"])

    groq = report["models"][0]
    gemini = report["models"][1]
    assert groq["provider"] == "groq"
    assert groq["pricing_tier"] == "free-tier"
    assert "fast-inference" in groq["capabilities"]
    assert gemini["provider"] == "gemini"
    assert gemini["docs_url"].startswith("https://ai.google.dev/")


def test_provider_matrix_cli_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/harness_provider_matrix.py",
            "--models",
            "ollama:a,deepseek:b",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["model_count"] == 2
    assert report["pairs"][0]["signal_required"] is True
