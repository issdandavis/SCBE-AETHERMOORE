#!/usr/bin/env python3
"""Build an auto-updating procedural map of the SCBE repo.

The seed file defines broad regions. This script scans the live repo into
deterministic chunks and cells, then writes a human map and a machine JSON map.
Think Minecraft world generation, but for repo management: the seeds are stable,
the terrain comes from the files that exist right now.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEEDS = REPO_ROOT / "config" / "system" / "procedural_system_map_seeds.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs" / "ops" / "PROCEDURAL_SYSTEM_MAP.md"
DEFAULT_JSON = REPO_ROOT / "docs" / "ops" / "PROCEDURAL_SYSTEM_MAP.generated.json"

DEFAULT_EXCLUDE_DIRS = {
    ".cache",
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".npm-cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}

CODE_EXTENSIONS = {
    ".c",
    ".cjs",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hs",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".lua",
    ".mjs",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".swift",
    ".ts",
    ".tsx",
    ".zig",
}
DOC_EXTENSIONS = {".csv", ".html", ".md", ".rst", ".txt"}
CONFIG_EXTENSIONS = {".json", ".toml", ".yaml", ".yml"}
MAX_HASH_BYTES = 512 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def safe_path(root: Path, rel_path: str) -> Path:
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Seed path escapes repo root: {rel_path}") from exc
    return candidate


def has_glob(value: str) -> bool:
    return any(char in value for char in "*?[]")


def matches_any(rel_path: str, patterns: Iterable[str]) -> bool:
    name = Path(rel_path).name
    return any(fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(name, pattern) for pattern in patterns)


def is_excluded(rel_path: str, patterns: Iterable[str]) -> bool:
    parts = set(Path(rel_path).parts)
    return bool(parts & DEFAULT_EXCLUDE_DIRS) or matches_any(rel_path, patterns)


def is_included(rel_path: str, patterns: Iterable[str]) -> bool:
    return not patterns or matches_any(rel_path, patterns)


def classify_cell(rel_path: str) -> tuple[str, str]:
    path = Path(rel_path)
    ext = path.suffix.lower()
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()

    if "tests" in parts or name.startswith("test_") or name.endswith(".test.ts"):
        role = "test"
    elif "docs" in parts or "notes" in parts or "research" in parts or ext in DOC_EXTENSIONS:
        role = "doc"
    elif "config" in parts or ext in CONFIG_EXTENSIONS:
        role = "config"
    elif "artifacts" in parts or "dist" in parts or "training-data" in parts:
        role = "generated"
    elif "scripts" in parts or "agents" in parts:
        role = "operator"
    elif "api" in parts or "src" in parts or "python" in parts or ext in CODE_EXTENSIONS:
        role = "runtime"
    else:
        role = "support"

    if ext in CODE_EXTENSIONS:
        kind = "code"
    elif ext in DOC_EXTENSIONS:
        kind = "doc"
    elif ext in CONFIG_EXTENSIONS:
        kind = "config"
    else:
        kind = ext[1:] if ext else "unknown"

    return kind, role


def fingerprint_file(path: Path) -> str:
    stat = path.stat()
    hasher = hashlib.sha256()
    hasher.update(path.name.encode("utf-8", errors="replace"))
    hasher.update(str(stat.st_size).encode("ascii"))
    if stat.st_size <= MAX_HASH_BYTES:
        hasher.update(path.read_bytes())
    else:
        hasher.update(str(int(stat.st_mtime)).encode("ascii"))
    return hasher.hexdigest()[:16]


def coord_for(world_seed: str, *parts: str) -> dict[str, int]:
    digest = hashlib.sha256(("::".join((world_seed, *parts))).encode("utf-8")).digest()
    x = int.from_bytes(digest[:2], "big") % 4096 - 2048
    z = int.from_bytes(digest[2:4], "big") % 4096 - 2048
    return {"x": x, "z": z}


def expand_seed_roots(repo_root: Path, roots: list[str]) -> tuple[list[Path], list[str]]:
    expanded: list[Path] = []
    missing: list[str] = []
    for root_entry in roots:
        if has_glob(root_entry):
            matches = sorted(path for path in repo_root.glob(root_entry) if path.exists())
            if not matches:
                missing.append(root_entry)
            expanded.extend(matches)
            continue

        path = safe_path(repo_root, root_entry)
        if path.exists():
            expanded.append(path)
        else:
            missing.append(root_entry)
    return expanded, missing


def iter_seed_files(repo_root: Path, seed: dict[str, Any], global_excludes: list[str]) -> tuple[list[Path], list[str], bool]:
    roots, missing_roots = expand_seed_roots(repo_root, list(seed.get("roots", [])))
    include_globs = list(seed.get("include_globs", []))
    exclude_globs = [*global_excludes, *list(seed.get("exclude_globs", []))]
    max_depth = int(seed.get("max_depth", 2))
    max_files = int(seed.get("max_files", 100))
    files: list[Path] = []
    truncated = False

    for seed_root in roots:
        if seed_root.is_file():
            rel_path = rel_posix(repo_root, seed_root)
            if not is_excluded(rel_path, exclude_globs) and is_included(rel_path, include_globs):
                files.append(seed_root)
            continue

        for dirpath, dirnames, filenames in os.walk(seed_root):
            current_dir = Path(dirpath)
            rel_dir = current_dir.relative_to(seed_root)
            depth = 0 if str(rel_dir) == "." else len(rel_dir.parts)
            dirnames[:] = sorted(
                dirname
                for dirname in dirnames
                if not is_excluded(rel_posix(repo_root, current_dir / dirname), exclude_globs)
            )
            if depth >= max_depth:
                dirnames[:] = []

            for filename in sorted(filenames):
                path = current_dir / filename
                rel_path = rel_posix(repo_root, path)
                if is_excluded(rel_path, exclude_globs) or not is_included(rel_path, include_globs):
                    continue
                if len(files) >= max_files:
                    truncated = True
                    return files, missing_roots, truncated
                files.append(path)

    return sorted(set(files), key=lambda item: rel_posix(repo_root, item)), missing_roots, truncated


def build_cell(repo_root: Path, world_seed: str, region_id: str, path: Path) -> dict[str, Any]:
    rel_path = rel_posix(repo_root, path)
    kind, role = classify_cell(rel_path)
    stat = path.stat()
    return {
        "id": hashlib.sha256(f"{world_seed}:{region_id}:{rel_path}".encode("utf-8")).hexdigest()[:12],
        "path": rel_path,
        "kind": kind,
        "role": role,
        "size_bytes": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
        "fingerprint": fingerprint_file(path),
        "coord": coord_for(world_seed, region_id, rel_path),
    }


def region_health(seed: dict[str, Any], cells: list[dict[str, Any]], missing_roots: list[str], truncated: bool) -> str:
    roles = Counter(cell["role"] for cell in cells)
    status = str(seed.get("status", "active"))
    if missing_roots:
        return "degraded"
    if status == "noisy":
        return status
    if truncated:
        return "truncated"
    if status in {"noisy", "staging", "review"}:
        return status
    if not cells:
        return "empty"
    if roles["test"] > 0 and (roles["runtime"] > 0 or roles["operator"] > 0):
        return "verified"
    if roles["doc"] > max(3, roles["runtime"] + roles["operator"]):
        return "doc-heavy"
    return "mapped"


def build_region(repo_root: Path, world_seed: str, seed: dict[str, Any], global_excludes: list[str]) -> dict[str, Any]:
    files, missing_roots, truncated = iter_seed_files(repo_root, seed, global_excludes)
    cells = [build_cell(repo_root, world_seed, str(seed["id"]), path) for path in files]
    roles = Counter(cell["role"] for cell in cells)
    kinds = Counter(cell["kind"] for cell in cells)
    roots = list(seed.get("roots", []))
    return {
        "id": seed["id"],
        "label": seed.get("label", seed["id"]),
        "biome": seed.get("biome", "default"),
        "status": seed.get("status", "active"),
        "health": region_health(seed, cells, missing_roots, truncated),
        "purpose": seed.get("purpose", ""),
        "tags": list(seed.get("tags", [])),
        "coord": coord_for(world_seed, str(seed["id"])),
        "roots": roots,
        "missing_roots": missing_roots,
        "truncated": truncated,
        "counts": {
            "cells": len(cells),
            "roles": dict(sorted(roles.items())),
            "kinds": dict(sorted(kinds.items())),
            "bytes": sum(int(cell["size_bytes"]) for cell in cells),
        },
        "cells": cells,
    }


def load_coding_registry_overlay(repo_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    rel_path = config.get("registry_overlay", {}).get(
        "coding_system_registry",
        "docs/research/SCBE_CODING_SYSTEM_REGISTRY_2026-05-10.json",
    )
    path = safe_path(repo_root, rel_path)
    if not path.exists():
        return {"path": rel_path, "present": False, "systems": [], "summary": {}}

    payload = load_json(path)
    systems = []
    for system in payload.get("systems", []):
        coverage = system.get("coverage", {})
        systems.append(
            {
                "id": system.get("system_id"),
                "name": system.get("name"),
                "status": system.get("registry_status", "unknown"),
                "benchmark_role": system.get("benchmark_role", ""),
                "coverage": coverage,
                "missing_paths": [
                    item for item, present in system.get("path_status", {}).items() if present is False
                ],
            }
        )

    present = sum(1 for system in systems if system.get("coverage", {}).get("paths_present", 0) > 0)
    total_paths = sum(int(system.get("coverage", {}).get("paths_total", 0)) for system in systems)
    present_paths = sum(int(system.get("coverage", {}).get("paths_present", 0)) for system in systems)
    return {
        "path": rel_path,
        "present": True,
        "systems": systems,
        "summary": {
            "systems": len(systems),
            "systems_with_any_paths": present,
            "paths_present": present_paths,
            "paths_total": total_paths,
        },
    }


def build_edges(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for index, left in enumerate(regions):
        for right in regions[index + 1 :]:
            shared_tags = sorted(set(left.get("tags", [])) & set(right.get("tags", [])))
            if not shared_tags:
                continue
            edges.append(
                {
                    "from": left["id"],
                    "to": right["id"],
                    "shared_tags": shared_tags,
                    "weight": len(shared_tags),
                }
            )
    return sorted(edges, key=lambda edge: (-edge["weight"], edge["from"], edge["to"]))


def stable_world_digest(world: dict[str, Any]) -> str:
    stable = {
        "schema": world["schema"],
        "world_seed": world["world_seed"],
        "regions": [
            {
                "id": region["id"],
                "health": region["health"],
                "missing_roots": region["missing_roots"],
                "truncated": region["truncated"],
                "cells": [(cell["path"], cell["fingerprint"]) for cell in region["cells"]],
            }
            for region in world["regions"]
        ],
        "coding_registry": world["coding_registry"]["summary"],
    }
    raw = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def next_actions(world: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for region in world["regions"]:
        if region.get("status") == "noisy":
            continue
        if region["missing_roots"]:
            actions.append(f"Repair or remove missing roots for {region['id']}: {', '.join(region['missing_roots'])}")
        if region["truncated"]:
            actions.append(f"Split or raise max_files for {region['id']} so the chunk is not truncated.")
        roles = region["counts"]["roles"]
        code_cells = roles.get("runtime", 0) + roles.get("operator", 0)
        if code_cells and not roles.get("test", 0) and region.get("status") != "review":
            actions.append(f"Route at least one test/evidence cell into {region['id']}.")
    registry = world["coding_registry"]
    if registry.get("present") and registry.get("summary", {}).get("paths_present", 0) < registry.get("summary", {}).get(
        "paths_total",
        0,
    ):
        actions.append("Refresh the coding-system registry and repair dead path references.")
    if not actions:
        actions.append("No map repair actions generated; use --watch to keep the map current.")
    return actions[:12]


def build_world(repo_root: Path, seeds_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config = load_json(seeds_path)
    world_seed = str(config.get("world_seed", "scbe-procedural-map"))
    global_excludes = list(config.get("global_exclude_globs", []))
    regions = [build_region(repo_root, world_seed, seed, global_excludes) for seed in config.get("seeds", [])]
    world = {
        "schema": "scbe_procedural_system_map_v1",
        "generated_at": utc_now(),
        "source": "scripts/system/procedural_system_map.py",
        "seed_file": rel_posix(repo_root, seeds_path) if seeds_path.resolve().is_relative_to(repo_root) else str(seeds_path),
        "map_name": config.get("map_name", "SCBE Procedural System Map"),
        "world_seed": world_seed,
        "description": config.get("description", ""),
        "regions": regions,
        "edges": build_edges(regions),
        "coding_registry": load_coding_registry_overlay(repo_root, config),
    }
    world["summary"] = {
        "regions": len(regions),
        "cells": sum(region["counts"]["cells"] for region in regions),
        "missing_roots": sum(len(region["missing_roots"]) for region in regions),
        "truncated_regions": sum(1 for region in regions if region["truncated"]),
        "health": dict(sorted(Counter(region["health"] for region in regions).items())),
    }
    world["world_digest"] = stable_world_digest(world)
    world["next_actions"] = next_actions(world)
    return world


def render_markdown(world: dict[str, Any]) -> str:
    lines = [
        f"# {world['map_name']}",
        "",
        f"Generated: `{world['generated_at']}`",
        f"Source: `{world['source']}`",
        f"Seed file: `{world['seed_file']}`",
        f"World digest: `{world['world_digest']}`",
        "",
        "This file is generated from tracked seeds plus live repo files. Edit the seed file, not this output.",
        "",
        "## World Summary",
        "",
        "| Region | Biome | Health | Cells | Tests | Docs | Missing | Chunk |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for region in world["regions"]:
        roles = region["counts"]["roles"]
        coord = region["coord"]
        lines.append(
            "| {label} | `{biome}` | `{health}` | {cells} | {tests} | {docs} | {missing} | `{x},{z}` |".format(
                label=region["label"],
                biome=region["biome"],
                health=region["health"],
                cells=region["counts"]["cells"],
                tests=roles.get("test", 0),
                docs=roles.get("doc", 0),
                missing=len(region["missing_roots"]),
                x=coord["x"],
                z=coord["z"],
            )
        )

    lines.extend(["", "## Regions", ""])
    for region in world["regions"]:
        coord = region["coord"]
        lines.extend(
            [
                f"### {region['label']} (`{region['id']}`)",
                "",
                f"- Biome: `{region['biome']}`",
                f"- Health: `{region['health']}`",
                f"- Chunk coordinate: `{coord['x']},{coord['z']}`",
                f"- Purpose: {region['purpose']}",
                f"- Tags: {', '.join(f'`{tag}`' for tag in region['tags']) or '`none`'}",
                f"- Roots: {', '.join(f'`{root}`' for root in region['roots'])}",
            ]
        )
        if region["missing_roots"]:
            lines.append(f"- Missing roots: {', '.join(f'`{root}`' for root in region['missing_roots'])}")
        if region["truncated"]:
            lines.append("- Scan note: `truncated`")

        roles = region["counts"]["roles"]
        kinds = region["counts"]["kinds"]
        lines.append(f"- Roles: `{json.dumps(roles, sort_keys=True)}`")
        lines.append(f"- Kinds: `{json.dumps(kinds, sort_keys=True)}`")
        lines.append("")
        lines.append("Primary cells:")
        for cell in region["cells"][:12]:
            lines.append(f"- `{cell['path']}` ({cell['role']}/{cell['kind']}, `{cell['fingerprint']}`)")
        if len(region["cells"]) > 12:
            lines.append(f"- ... {len(region['cells']) - 12} more cells in generated JSON")
        lines.append("")

    registry = world["coding_registry"]
    lines.extend(["## Coding Registry Overlay", ""])
    if registry.get("present"):
        summary = registry.get("summary", {})
        lines.append(
            "- `{path}`: {systems} systems, {present}/{total} tracked paths present.".format(
                path=registry["path"],
                systems=summary.get("systems", 0),
                present=summary.get("paths_present", 0),
                total=summary.get("paths_total", 0),
            )
        )
        for system in registry.get("systems", [])[:10]:
            coverage = system.get("coverage", {})
            lines.append(
                f"- `{system['id']}`: {system['name']} "
                f"({coverage.get('paths_present', 0)}/{coverage.get('paths_total', 0)} paths)"
            )
    else:
        lines.append(f"- Registry missing at `{registry.get('path')}`.")

    lines.extend(["", "## Region Edges", ""])
    if world["edges"]:
        for edge in world["edges"][:20]:
            tags = ", ".join(f"`{tag}`" for tag in edge["shared_tags"])
            lines.append(f"- `{edge['from']}` -> `{edge['to']}` via {tags}")
    else:
        lines.append("- No shared-tag edges generated.")

    lines.extend(["", "## Generated Next Actions", ""])
    for action in world["next_actions"]:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(world: dict[str, Any], markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(world), encoding="utf-8")
    json_path.write_text(json.dumps(world, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def check_outputs(world: dict[str, Any], json_path: Path) -> tuple[bool, str]:
    if not json_path.exists():
        return False, f"missing generated JSON: {json_path}"
    current = load_json(json_path)
    if current.get("world_digest") != world["world_digest"]:
        return False, f"map drift: {current.get('world_digest')} != {world['world_digest']}"
    return True, "map digest is current"


def run_once(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    seeds_path = Path(args.seeds).resolve()
    markdown_path = Path(args.markdown).resolve()
    json_path = Path(args.json_output).resolve()
    world = build_world(repo_root, seeds_path)

    if args.check:
        ok, message = check_outputs(world, json_path)
        if not ok:
            raise SystemExit(message)
        if not args.print_json:
            print(message)
        return world

    if not args.dry_run:
        write_outputs(world, markdown_path, json_path)
    return world


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the procedural SCBE system map from tracked seeds.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--seeds", default=str(DEFAULT_SEEDS))
    parser.add_argument("--markdown", default=str(DEFAULT_MARKDOWN))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--dry-run", action="store_true", help="Build the map but do not write output files.")
    parser.add_argument("--check", action="store_true", help="Fail if the generated JSON digest is stale.")
    parser.add_argument("--watch", action="store_true", help="Keep rebuilding when the world digest changes.")
    parser.add_argument("--interval", type=float, default=10.0, help="Watch interval in seconds.")
    parser.add_argument("--json", action="store_true", dest="print_json", help="Print a compact JSON summary.")
    args = parser.parse_args()

    if args.watch and args.check:
        raise SystemExit("--watch and --check cannot be combined")

    if not args.watch:
        world = run_once(args)
        if args.print_json:
            print(json.dumps({"ok": True, "world_digest": world["world_digest"], "summary": world["summary"]}, indent=2))
        elif not args.check:
            print(f"wrote procedural system map: {world['world_digest']}")
        return 0

    last_digest = ""
    while True:
        world = run_once(args)
        if world["world_digest"] != last_digest:
            print(f"[{utc_now()}] updated procedural system map: {world['world_digest']}")
            last_digest = world["world_digest"]
        time.sleep(max(1.0, float(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
