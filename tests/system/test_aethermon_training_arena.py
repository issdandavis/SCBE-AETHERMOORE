from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "aethermon_training_arena.py"


def load_module():
    spec = importlib.util.spec_from_file_location("aethermon_training_arena", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_policy_episode_completes_small_curriculum():
    arena = load_module()
    episode = arena.run_episode(42, max_ticks=40)
    assert episode["success"] is True
    assert episode["turns"] <= 40
    assert episode["final_observation"]["creature"]["xp"] >= 1
    assert episode["final_observation"]["creature"]["atk"] >= 7


def test_manifest_contains_godot_sprite_paths():
    arena = load_module()
    manifest = arena.write_sprite_assets()
    assert manifest["schema"] == "aethermon_godot_training_manifest_v1"
    assert manifest["sprites"]["kindlemote"]["path"].endswith("kindlemote.png")
    assert (arena.GODOT_AETHERMON_DIR / "sprites" / "kindlemote.png").exists()
