from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


scbe_system_cli = _load_module("test_scbe_system_cli_security", "scripts/scbe-system-cli.py")


def test_notebooklm_fallback_persists_prompt_metadata_only(tmp_path: Path) -> None:
    result = scbe_system_cli._notebooklm_fallback(
        {"agent_id": "notebooklm-main", "notebook_url": "https://notebooklm.google.com/notebook/demo"},
        "super secret password prompt",
        tmp_path,
    )

    payload = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert "prompt" not in payload
    assert payload["prompt_metadata"]["present"] is True
    assert payload["prompt_metadata"]["length"] == len("super secret password prompt")


def test_write_agent_call_result_sanitizes_content_and_raw(tmp_path: Path) -> None:
    output_path = scbe_system_cli._write_agent_call_result(
        tmp_path,
        "codex",
        {
            "ok": True,
            "agent_id": "codex",
            "content": "sensitive model response",
            "raw": {"token": "secret", "message": "hidden"},
            "prompt": "top secret prompt",
        },
    )

    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert "content" not in payload
    assert "raw" not in payload
    assert "prompt" not in payload
    assert payload["content_metadata"]["pbkdf2_sha256"]
    assert payload["prompt_metadata"]["length"] == len("top secret prompt")


def test_visual_system_html2canvas_script_uses_sri() -> None:
    html = (ROOT / "scbe-visual-system" / "index.html").read_text(encoding="utf-8")
    assert 'html2canvas.min.js' in html
    assert 'integrity="sha384-ZZ1pncU3bQe8y31yfZdMFdSpttDoPmOZg2wguVK9almUodir1PghgT0eY7Mrty8H"' in html
    assert 'crossorigin="anonymous"' in html
