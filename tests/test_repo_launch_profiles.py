from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = _load_module("repo_launch_preflight_test", "scripts/system/repo_launch_preflight.py")
launch_profile = _load_module("launch_profile_test", "scripts/system/launch_profile.py")


def test_all_launch_profiles_have_existing_required_paths():
    for profile in preflight.PROFILE_REQUIRED_PATHS:
        assert preflight.check_profile_paths(profile) == []


def test_training_profile_uses_existing_review_entrypoint():
    command_paths = [
        item
        for command in launch_profile.PROFILES["training"].commands
        for item in command
        if item.endswith(".py")
    ]

    assert "scripts/system/review_training_runs.py" in command_paths
    assert "scripts/system/training_terminal.py" not in command_paths
