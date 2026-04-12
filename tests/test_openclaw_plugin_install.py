from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import subprocess


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "system" / "install_openclaw_scbe_plugin.py"
SPEC = importlib.util.spec_from_file_location("install_openclaw_scbe_plugin", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_patch_openclaw_config_enables_plugin_and_preserves_existing_entries() -> None:
    original = {
        "plugins": {
            "allow": ["openclaw-web-search"],
            "entries": {
                "openclaw-web-search": {"enabled": True},
            },
        }
    }

    patched = MODULE.patch_openclaw_config(
        original,
        repo_root=Path("C:/Users/issda/SCBE-AETHERMOORE"),
        install_path=Path("C:/Users/issda/.openclaw/extensions/scbe-system-tools"),
        python_bin="python",
        timeout_ms=90000,
        default_provider="hf",
        default_local_base_url="http://localhost:1234/v1",
        default_ollama_base_url="http://localhost:11434/v1",
    )

    assert patched["plugins"]["enabled"] is True
    assert "openclaw-web-search" in patched["plugins"]["allow"]
    assert MODULE.PLUGIN_ID in patched["plugins"]["allow"]
    assert patched["plugins"]["entries"][MODULE.PLUGIN_ID]["enabled"] is True
    assert Path(patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["repoRoot"]) == Path(
        "C:/Users/issda/SCBE-AETHERMOORE"
    )
    assert patched["plugins"]["installs"][MODULE.PLUGIN_ID]["source"] == "path"
    assert Path(patched["plugins"]["installs"][MODULE.PLUGIN_ID]["installPath"]) == Path(
        "C:/Users/issda/.openclaw/extensions/scbe-system-tools"
    )
    assert Path(patched["plugins"]["installs"][MODULE.PLUGIN_ID]["spec"]) == Path(
        "C:/Users/issda/SCBE-AETHERMOORE/extensions/openclaw-scbe-system-tools"
    )
    assert patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["pythonBin"] == "python"
    assert patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["timeoutMs"] == 90000
    assert patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["defaultProvider"] == "hf"
    assert (
        patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["defaultLocalBaseUrl"]
        == "http://localhost:1234/v1"
    )
    assert (
        patched["plugins"]["entries"][MODULE.PLUGIN_ID]["config"]["defaultOllamaBaseUrl"]
        == "http://localhost:11434/v1"
    )


def test_build_install_plan_targets_global_openclaw_home() -> None:
    plan = MODULE.build_install_plan(
        Path("C:/Users/issda/SCBE-AETHERMOORE"),
        openclaw_home=Path("C:/Users/test/.openclaw"),
        python_bin="py",
        timeout_ms=12345,
        default_provider="hf",
        default_local_base_url="http://localhost:1234/v1",
        default_ollama_base_url="http://localhost:11434/v1",
        method="copy",
    )

    assert Path(plan.extension_dir) == Path("C:/Users/test/.openclaw/extensions/scbe-system-tools")
    assert Path(plan.config_path) == Path("C:/Users/test/.openclaw/openclaw.json")
    assert plan.python_bin == "py"
    assert plan.timeout_ms == 12345
    assert plan.default_provider == "hf"
    assert plan.default_local_base_url == "http://localhost:1234/v1"
    assert plan.default_ollama_base_url == "http://localhost:11434/v1"
    assert plan.method == "copy"


def test_cli_install_plugin_uses_supported_subprocess_kwargs(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(MODULE.shutil, "which", lambda name: "C:/Users/test/AppData/Roaming/npm/openclaw.cmd" if name == "openclaw.cmd" else None)
    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    MODULE.cli_install_plugin(Path("C:/Users/issda/SCBE-AETHERMOORE/extensions/openclaw-scbe-system-tools"))

    assert captured["args"][0][:3] == ["C:/Users/test/AppData/Roaming/npm/openclaw.cmd", "plugins", "install"]
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["capture_output"] is True
    assert "windowsHide" not in captured["kwargs"]
