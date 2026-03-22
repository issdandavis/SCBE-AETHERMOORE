from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ai_bridge = _load_module("test_batch5_ai_bridge", "scripts/system/ai_bridge.py")
codebase_to_sft = _load_module("test_batch5_codebase_to_sft", "scripts/codebase_to_sft.py")


def test_lore_strip_copies_use_dom_rendering_and_safe_url_helper():
    for relative_path in (
        "docs/arena.html",
        "public/index.html",
        "public/arena.html",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert 'title="${escHtml' not in text
        assert 'alt="${escHtml' not in text
        assert "safeLoreImageUrl" in text
        assert "document.createElement('img')" in text


def test_kindle_browse_uses_dom_construction_for_dynamic_lists():
    text = (ROOT / "kindle-app/www/browse.html").read_text(encoding="utf-8")
    assert 'document.getElementById(containerId).innerHTML' not in text
    assert 'document.getElementById("recentList").innerHTML' not in text
    assert 'strip.innerHTML' not in text
    assert "createLinkTile" in text
    assert "createRecentItem" in text
    assert "createTabChip" in text


def test_ai_bridge_write_log_uses_allowlisted_root_and_safe_filename(tmp_path, monkeypatch):
    monkeypatch.setenv("SCBE_ALLOWED_VAULT_ROOTS", str(tmp_path))

    log_path = ai_bridge.write_log(
        str(tmp_path),
        "hf",
        "../gpt/4o:preview",
        "test prompt",
        "test response",
    )

    assert log_path.exists()
    assert log_path.is_relative_to(tmp_path)
    assert ".." not in log_path.name
    assert ":" not in log_path.name
    assert "gpt_4o_preview" in log_path.name


def test_codebase_to_sft_extract_py_docstrings_uses_ast_and_handles_invalid(tmp_path):
    module_doc = "Module docstring " + ("A" * 120)
    class_doc = "Class docstring " + ("B" * 120)
    func_doc = "Function docstring " + ("C" * 120)

    valid_source = (
        "#!/usr/bin/env python3\n"
        + ("\n" * 1500)
        + f"'''{module_doc}'''\n\n"
        + "class Example:\n"
        + f"    '''{class_doc}'''\n"
        + "    pass\n\n"
        + "def compute():\n"
        + f"    '''{func_doc}'''\n"
        + "    return 1\n"
    )
    valid_path = tmp_path / "example_module.py"
    valid_path.write_text(valid_source, encoding="utf-8")

    sections = codebase_to_sft.extract_py_docstrings(valid_path)
    headings = {heading for heading, _ in sections}

    assert "Module: example_module" in headings
    assert "Function/Class: Example" in headings
    assert "Function/Class: compute" in headings

    invalid_path = tmp_path / "broken_module.py"
    invalid_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    assert codebase_to_sft.extract_py_docstrings(invalid_path) == []
