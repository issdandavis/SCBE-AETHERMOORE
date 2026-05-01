"""Contract tests for the GeoShell App Store registry.

The registry at ``scbe-visual-system/apps-registry.json`` is consumed by
``scbe-visual-system/lib/apps-registry-loader.ts``. Any change to the
registry's shape must keep these tests passing so the React shell never
hits an undefined tile or a dangling service binding at runtime.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "scbe-visual-system" / "apps-registry.json"

# Allowed appId values mirrored from scbe-visual-system/types.ts. Keeping
# this list in sync is part of the contract.
_ALLOWED_APP_IDS = {
    "home",
    "mail",
    "slides",
    "snake",
    "folder",
    "notepad",
    "automator",
    "code",
    "sudoku",
    "wordle",
    "security",
    "cryptolab",
    "defense",
    "agents",
    "overseer",
    "fleet",
    "knowledge",
    "pollypad",
    "service",
    "appstore",
}

_TAILWIND_BG_RE = re.compile(r"^bg-[a-z0-9\-/_\[\]\:]+(\s+[a-z0-9\-/_\[\]\:]+)*$")


@pytest.fixture(scope="module")
def registry() -> dict:
    assert REGISTRY.exists(), f"registry missing: {REGISTRY}"
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_has_required_top_level(registry: dict) -> None:
    assert registry["schema_version"] == "geoshell_apps_registry_v1"
    assert registry["shell_name"] == "GeoShell"
    assert isinstance(registry["categories"], list)
    assert len(registry["categories"]) >= 1


def test_every_category_has_label_and_at_least_one_tile(registry: dict) -> None:
    for cat in registry["categories"]:
        assert isinstance(cat["id"], str) and cat["id"]
        assert isinstance(cat["label"], str) and cat["label"]
        assert isinstance(cat["tiles"], list)
        assert len(cat["tiles"]) >= 1, f"empty category: {cat['id']}"


def test_every_tile_has_required_fields(registry: dict) -> None:
    for cat in registry["categories"]:
        for tile in cat["tiles"]:
            assert "id" in tile and tile["id"], f"tile in {cat['id']} missing id"
            assert "name" in tile and tile["name"], f"tile {tile.get('id')} missing name"
            assert tile.get("appId") in _ALLOWED_APP_IDS, (
                f"tile {tile['id']} has unknown appId={tile.get('appId')!r}; "
                f"update _ALLOWED_APP_IDS or types.ts"
            )
            if tile.get("bgColor"):
                assert _TAILWIND_BG_RE.match(tile["bgColor"]), (
                    f"tile {tile['id']} bgColor not a tailwind class: {tile['bgColor']!r}"
                )


def test_tile_ids_are_globally_unique(registry: dict) -> None:
    ids: list[str] = []
    for cat in registry["categories"]:
        for tile in cat["tiles"]:
            ids.append(tile["id"])
    assert len(ids) == len(set(ids)), f"duplicate tile ids: {sorted(ids)}"


def test_service_tiles_have_complete_binding(registry: dict) -> None:
    for cat in registry["categories"]:
        for tile in cat["tiles"]:
            if tile.get("appId") != "service":
                continue
            binding = tile.get("service")
            assert binding, f"service tile {tile['id']} missing 'service' binding"
            assert binding.get("kind") == "http", (
                f"service tile {tile['id']} kind must be 'http' (got {binding.get('kind')!r})"
            )
            assert isinstance(binding.get("defaultUrl"), str) and binding["defaultUrl"], (
                f"service tile {tile['id']} missing defaultUrl"
            )
            if "envUrl" in binding:
                env = binding["envUrl"]
                assert isinstance(env, str) and env.isupper(), (
                    f"service tile {tile['id']} envUrl must be UPPER_SNAKE: {env!r}"
                )
            if "openInExternal" in binding:
                assert isinstance(binding["openInExternal"], bool)
            if "description" in binding:
                assert isinstance(binding["description"], str) and binding["description"]


def test_loader_typescript_appid_matches_registry(registry: dict) -> None:
    """Cross-check that types.ts AppId enum covers every appId in the registry."""

    types_ts = (REPO / "scbe-visual-system" / "types.ts").read_text(encoding="utf-8")
    used_ids = {tile["appId"] for cat in registry["categories"] for tile in cat["tiles"]}
    for app_id in used_ids:
        # We expect the literal `'app_id'` to appear in the AppId union.
        assert f"'{app_id}'" in types_ts, (
            f"appId {app_id!r} used in registry but missing from types.ts AppId union"
        )


def test_required_tile_categories_present(registry: dict) -> None:
    """Locks the canonical category set for the shell."""

    cat_ids = {c["id"] for c in registry["categories"]}
    required = {"security", "ai-workspace", "games", "services", "discovery"}
    assert required.issubset(cat_ids), f"missing canonical categories: {required - cat_ids}"


def test_appstore_tile_exists(registry: dict) -> None:
    """The App Store tile is the entry point; without it users cannot discover other tiles."""

    tile_ids = {tile["id"] for cat in registry["categories"] for tile in cat["tiles"]}
    assert "appstore" in tile_ids, "App Store tile missing from registry"


def test_critical_service_tiles_present(registry: dict) -> None:
    """Spiral Word and GeoSeal are first-class services per Phase 5."""

    tile_ids = {tile["id"] for cat in registry["categories"] for tile in cat["tiles"]}
    for must_exist in ("spiralword", "geoseal"):
        assert must_exist in tile_ids, f"required service tile missing: {must_exist}"


_APP_TSX = REPO / "scbe-visual-system" / "App.tsx"
_LOADER_TS = REPO / "scbe-visual-system" / "lib" / "apps-registry-loader.ts"


def test_app_tsx_renders_every_appid_used_in_registry(registry: dict) -> None:
    """Every appId in the registry must have a render branch in App.tsx.

    This prevents the "broken tile" bug where the user clicks a tile and
    nothing happens because App.tsx falls through the if/else chain.
    """

    app_tsx = _APP_TSX.read_text(encoding="utf-8")
    used_app_ids = {tile["appId"] for cat in registry["categories"] for tile in cat["tiles"]}
    used_app_ids.discard("folder")  # folders use the type === 'folder' branch
    for app_id in used_app_ids:
        # Match the literal `appId === 'foo'` exactly to avoid false positives.
        needle = f"win.item.appId === '{app_id}'"
        assert needle in app_tsx, (
            f"App.tsx is missing a render branch for appId {app_id!r}; "
            f"expected to find: {needle}"
        )


def test_loader_allowed_app_ids_matches_types(registry: dict) -> None:
    """The hand-maintained allow list inside apps-registry-loader.ts must
    match the AppId union in types.ts. This is the third copy of the same
    enum (types.ts, the loader, the test); keeping all three aligned
    prevents the loader from silently coercing unknown appIds to 'notepad'."""

    types_ts = (REPO / "scbe-visual-system" / "types.ts").read_text(encoding="utf-8")
    loader_ts = _LOADER_TS.read_text(encoding="utf-8")

    type_union = set(re.findall(r"\|\s*'([a-z]+)'", types_ts))
    loader_allowed = set(re.findall(r"'([a-z]+)'", loader_ts))
    # The loader file has many quoted strings; restrict to ones that also
    # appear in the registry plus the canonical AppId members. Compare the
    # intersection against the type union so a missing entry surfaces.
    loader_intersection = loader_allowed & type_union
    missing = type_union - loader_intersection
    assert not missing, (
        f"AppId values present in types.ts but missing from "
        f"apps-registry-loader.ts allow list: {sorted(missing)}"
    )
