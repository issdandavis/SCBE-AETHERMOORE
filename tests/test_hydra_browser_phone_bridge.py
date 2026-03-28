from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_bridge_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "system" / "hydra_browser_phone_bridge.py"
    spec = importlib.util.spec_from_file_location("hydra_browser_phone_bridge_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load bridge module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_domain_from_url_normalizes_missing_scheme():
    bridge = _load_bridge_module()

    assert bridge.domain_from_url("github.com/issdandavis/SCBE-AETHERMOORE") == "github.com"


def test_build_host_action_script_targets_same_url():
    bridge = _load_bridge_module()

    script = bridge.build_host_action_script("http://10.0.2.2:8088/reader.html")

    assert [step["action"] for step in script] == ["navigate", "snapshot", "extract"]
    assert all(step["target"] == "http://10.0.2.2:8088/reader.html" for step in script)
