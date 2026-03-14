from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from src.gacha_isekai import training as gacha_training


ROOT = Path(__file__).resolve().parents[1]


def _load_module(relative_path: str, module_name: str, extra_paths: list[Path] | None = None):
    if extra_paths:
        for extra in extra_paths:
            extra_str = str(extra)
            if extra_str not in sys.path:
                sys.path.insert(0, extra_str)
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


playwriter_lane_runner = _load_module(
    "scripts/system/playwriter_lane_runner.py",
    "playwriter_lane_runner_batch3",
)
gov_contract_scan = _load_module(
    "skills/scbe-government-contract-intelligence/scripts/gov_contract_scan.py",
    "gov_contract_scan_batch3",
)
agentic_web_tool = _load_module(
    "scripts/agentic_web_tool.py",
    "agentic_web_tool_batch3",
)
npc_brain = _load_module(
    "demo/npc_brain.py",
    "npc_brain_batch3",
)
spiralword_ai_ports = _load_module(
    "spiral-word-app/ai_ports.py",
    "spiralword_ai_ports_batch3",
    extra_paths=[ROOT / "spiral-word-app"],
)
spiralword_app = _load_module(
    "spiral-word-app/app.py",
    "spiralword_app_batch3",
    extra_paths=[ROOT / "spiral-word-app"],
)


def test_parser_based_html_text_extractors_strip_malformed_script_tags() -> None:
    html = "<div>Alpha<script>alert(1)</script >Beta<style>body{color:red}</style><p>Gamma</p></div>"

    excerpt = playwriter_lane_runner._extract_text_excerpt(html)
    gov_text = gov_contract_scan._to_text(html)
    plain = agentic_web_tool._html_to_plain_text(html)

    for value in (excerpt, gov_text, plain):
        assert "alert(1)" not in value
        assert "color:red" not in value
        assert "Alpha" in value or "alpha" in value
        assert "Beta" in value or "beta" in value
        assert "Gamma" in value or "gamma" in value


def test_npc_and_training_sanitizers_strip_script_payloads() -> None:
    raw = "<SCRIPT>alert('xss')</SCRIPT >safe text"

    npc_text = npc_brain.NPCBrain._sanitize_response(raw)
    training_text = gacha_training._sanitize_training_text(raw)

    assert "alert" not in npc_text.lower()
    assert "safe text" in npc_text.lower()
    assert "alert" not in training_text.lower()
    assert "safe text" in training_text.lower()


def test_spiralword_public_ai_errors_are_generic() -> None:
    def boom_provider(prompt: str, options: dict | None = None) -> str:
        raise RuntimeError("secret trace path")

    registry = spiralword_ai_ports.AIPortRegistry()
    registry.register("boom", boom_provider)

    result = registry.call("hello world", provider="boom")
    payload = spiralword_app._public_ai_result_payload(result)

    assert result == "[ERROR] Provider boom failed"
    assert payload == {"status": "error", "message": "AI provider request failed"}
