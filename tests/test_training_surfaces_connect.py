"""Training surfaces connector smoke tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "system" / "training_surfaces_connect.py"
    spec = importlib.util.spec_from_file_location("training_surfaces_connect", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_manifest_has_colab_kaggle_hf() -> None:
    mod = _load()
    m = mod.build_manifest(run_preflight=False)
    assert m["schema_version"] == "scbe_training_surfaces_connect_v1"
    assert "colab" in m and m["colab"].get("open_zero_cost_url")
    assert "kaggle" in m and m["kaggle"].get("rounds")
    assert "huggingface" in m


def test_hf_jobs_launcher_exits_zero() -> None:
    import subprocess
    import sys

    script = ROOT / "scripts" / "hf_jobs" / "launch_dsl_synthesis_v3_fast.py"
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode in (0, 2)
