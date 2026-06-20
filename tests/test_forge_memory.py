from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def test_forge_memory_honors_recipe_path_override(tmp_path, monkeypatch) -> None:
    recipe_path = tmp_path / "recipes.json"
    monkeypatch.setenv("FORGE_RECIPES_PATH", str(recipe_path))
    monkeypatch.syspath_prepend(str(SCRIPTS))

    forge_memory = importlib.import_module("forge_memory")
    forge_memory = importlib.reload(forge_memory)

    assert forge_memory.RECIPES == recipe_path
    assert forge_memory.load() == []

    forge_memory.save([{"intent": "x", "caps": ["add"], "moves": ["add"], "verified": True}])

    assert recipe_path.exists()
    assert forge_memory.load()[0]["intent"] == "x"
    assert not (SCRIPTS / "forge_recipes.json").read_text(encoding="utf-8").startswith('[{"intent": "x"')

    sys.modules.pop("forge_memory", None)
