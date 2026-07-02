import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "system" / "procedural_system_map.py"


def load_module():
    spec = importlib.util.spec_from_file_location("procedural_system_map", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_seed_file(root: Path) -> Path:
    seed_path = root / "config" / "system" / "procedural_system_map_seeds.json"
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(
        json.dumps(
            {
                "schema": "scbe_procedural_system_map_seeds_v1",
                "map_name": "Test Map",
                "world_seed": "test-world",
                "global_exclude_globs": ["**/__pycache__/**"],
                "seeds": [
                    {
                        "id": "runtime",
                        "label": "Runtime Zone",
                        "biome": "runtime",
                        "status": "active",
                        "purpose": "Test runtime files.",
                        "tags": ["runtime", "api"],
                        "roots": ["src", "tests"],
                        "include_globs": ["*.py"],
                        "exclude_globs": [],
                        "max_depth": 2,
                        "max_files": 20,
                    },
                    {
                        "id": "missing",
                        "label": "Missing Zone",
                        "biome": "void",
                        "status": "active",
                        "purpose": "Missing root detection.",
                        "tags": ["runtime"],
                        "roots": ["does-not-exist"],
                        "include_globs": ["*.py"],
                        "exclude_globs": [],
                        "max_depth": 1,
                        "max_files": 5,
                    },
                    {
                        "id": "generated",
                        "label": "Generated Zone",
                        "biome": "generated",
                        "status": "noisy",
                        "purpose": "Generated output should not create cleanup noise just because it is capped.",
                        "tags": ["generated"],
                        "roots": ["src"],
                        "include_globs": ["*.py"],
                        "exclude_globs": [],
                        "max_depth": 2,
                        "max_files": 1,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return seed_path


def make_repo(root: Path) -> Path:
    (root / "src" / "api").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "api" / "main.py").write_text("def app():\n    return 'ok'\n", encoding="utf-8")
    (root / "tests" / "test_api.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return write_seed_file(root)


def test_build_world_from_seed_regions(tmp_path: Path) -> None:
    module = load_module()
    seed_path = make_repo(tmp_path)

    world = module.build_world(tmp_path, seed_path)

    assert world["schema"] == "scbe_procedural_system_map_v1"
    assert world["summary"]["regions"] == 3
    assert world["summary"]["cells"] == 3
    assert world["summary"]["missing_roots"] == 1
    assert len(world["world_digest"]) == 64

    runtime = next(region for region in world["regions"] if region["id"] == "runtime")
    assert runtime["health"] == "verified"
    assert runtime["counts"]["roles"]["runtime"] == 1
    assert runtime["counts"]["roles"]["test"] == 1
    assert runtime["coord"] == module.coord_for("test-world", "runtime")

    generated = next(region for region in world["regions"] if region["id"] == "generated")
    assert generated["health"] == "noisy"
    assert not any("generated" in action for action in world["next_actions"])

    markdown = module.render_markdown(world)
    assert "# Test Map" in markdown
    assert "Runtime Zone" in markdown
    assert "Generated Next Actions" in markdown


def test_cli_writes_and_checks_digest(tmp_path: Path) -> None:
    seed_path = make_repo(tmp_path)
    markdown_path = tmp_path / "docs" / "ops" / "map.md"
    json_path = tmp_path / "docs" / "ops" / "map.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--seeds",
            str(seed_path),
            "--markdown",
            str(markdown_path),
            "--json-output",
            str(json_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert markdown_path.exists()
    assert json_path.exists()
    assert json.loads(result.stdout)["ok"] is True

    check = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--seeds",
            str(seed_path),
            "--markdown",
            str(markdown_path),
            "--json-output",
            str(json_path),
            "--check",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )
    assert check.returncode == 0, check.stderr
    assert "map digest is current" in check.stdout
