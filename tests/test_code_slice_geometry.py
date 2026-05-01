from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "system" / "code_slice_geometry.py"


def load_module():
    spec = importlib.util.spec_from_file_location("_code_slice_geometry_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_builds_phase_lens_slices_with_binary_fallback():
    module = load_module()
    report = module.build_report("code slice agent tool calling harness", attempts=2, status="in_progress")

    assert report["coverage"]["slice_count"] == len(module.DESIRED_FLOW) * 3
    assert "binary" in report["coverage"]["lenses"]
    assert report["coverage"]["max_expansion_factor"] > 1
    assert any("transport_packet" in row["low_dim_slot"] for row in report["slices"])


def test_command_packets_have_allowed_paths_and_verify():
    module = load_module()
    slices = module.build_slices("stitch python and typescript tool commands", attempts=1, status="planned")

    first = slices[0]
    assert first.command_structure["allowed_paths"]
    assert "verify" in first.command_structure["commands"]
    assert first.training_marker["record_type"] == "code_slice_geometry"


def test_cli_check_outputs_valid_json():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/code_slice_geometry.py",
            "--goal",
            "code slice agent tool calling harness",
            "--attempts",
            "2",
            "--status",
            "in_progress",
            "--check",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["slice_count"] == 21
