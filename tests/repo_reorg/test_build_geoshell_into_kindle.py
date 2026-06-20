"""Contract tests for ``scripts/repo_reorg/build_geoshell_into_kindle.py``.

These tests do **not** invoke ``npm install`` or ``npm run build``. They lock
the script's wiring (paths, argparse, manifest schema) so that the GeoShell ->
Kindle pipeline can never silently target the wrong source/destination, and
so the manifest the Kindle app reads stays compatible.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "repo_reorg" / "build_geoshell_into_kindle.py"


def _load() -> ModuleType:
    """Load the build script as a module without executing main()."""

    spec = importlib.util.spec_from_file_location("build_geoshell_into_kindle", SCRIPT)
    assert spec and spec.loader, f"could not load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return _load()


def test_source_path_is_scbe_visual_system(mod: ModuleType) -> None:
    """Pipeline must read from scbe-visual-system; otherwise it would build
    the wrong UI into the Kindle app."""

    assert mod.SRC == REPO / "scbe-visual-system"


def test_destination_is_kindle_app_geoshell(mod: ModuleType) -> None:
    """Pipeline must write to kindle-app/www/geoshell/; the Kindle app
    Capacitor wrapper expects that exact path."""

    assert mod.DST == REPO / "kindle-app" / "www" / "geoshell"


def test_dist_path_is_inside_source(mod: ModuleType) -> None:
    """We never want the script to mirror something outside scbe-visual-system."""

    assert mod.DIST.is_relative_to(mod.SRC)
    assert mod.DIST.name == "dist"


def test_argparse_accepts_skip_install(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--skip-install`` is the contract the npm wrapper script depends on."""

    captured: dict[str, object] = {}

    def fake_install(skip: bool) -> None:
        captured["install_skip"] = skip

    def fake_build() -> None:
        captured["built"] = True

    def fake_mirror() -> None:
        captured["mirrored"] = True

    def fake_manifest() -> None:
        captured["manifest"] = True

    monkeypatch.setattr(mod, "install", fake_install)
    monkeypatch.setattr(mod, "build", fake_build)
    monkeypatch.setattr(mod, "mirror", fake_mirror)
    monkeypatch.setattr(mod, "write_manifest", fake_manifest)
    monkeypatch.setattr(sys, "argv", ["build_geoshell_into_kindle.py", "--skip-install"])

    rc = mod.main()
    assert rc == 0
    assert captured == {
        "install_skip": True,
        "built": True,
        "mirrored": True,
        "manifest": True,
    }


def test_write_manifest_schema_is_versioned(mod: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Kindle app reads geoshell-manifest.json. If we rename a key
    or drop the schema_version, native code breaks. Lock the schema."""

    fake_dst = tmp_path / "kindle-app" / "www" / "geoshell"
    fake_dst.mkdir(parents=True)
    monkeypatch.setattr(mod, "DST", fake_dst)
    monkeypatch.setattr(mod, "REPO", tmp_path)

    mod.write_manifest()

    manifest_file = fake_dst.parent / "geoshell-manifest.json"
    assert manifest_file.exists(), "manifest file was not written"

    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert data["schema_version"] == "geoshell_kindle_manifest_v1"
    assert data["geoshell_path"] == "geoshell/index.html"
    assert data["registry_path"] == "geoshell/apps-registry.json"
    assert data["build_root"] == "scbe-visual-system"


def test_has_npm_script_helper_reads_real_package_json(mod: ModuleType) -> None:
    """The build step gates on ``_has_npm_script('build')``. If the
    scbe-visual-system package.json ever loses its 'build' script, this
    test fails fast instead of waiting for a CI build."""

    assert mod._has_npm_script("build"), (
        "scbe-visual-system/package.json must define a 'build' script "
        "so the GeoShell -> Kindle pipeline can produce dist/"
    )
