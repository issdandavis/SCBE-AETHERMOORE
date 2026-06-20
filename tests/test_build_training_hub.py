"""Tests for the SCBE training hub builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "system" / "build_training_hub.py"
    spec = importlib.util.spec_from_file_location("build_training_hub", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_training_hub_manifest_has_surfaces_without_raw_hf_auth() -> None:
    mod = _load()
    hub = mod.build_hub(run_preflight=False)
    assert hub["schema_version"] == "scbe_training_hub_v1"
    assert "surfaces" in hub
    hf = hub["surfaces"]["huggingface"]["hub"]
    assert "HF_TOKEN_set" in hf
    assert "accessToken" not in repr(hf)
    assert "email" not in repr(hf).lower()


def test_training_hub_html_renders_operator_page() -> None:
    mod = _load()
    html = mod.render_html(mod.build_hub(run_preflight=False))
    assert "<title>SCBE Training Hub</title>" in html
    assert "Daily Stack" in html
    assert "certification or performance claim" in html
