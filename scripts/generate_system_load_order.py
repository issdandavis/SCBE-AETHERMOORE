#!/usr/bin/env python3
"""
Generate a full-system deterministic load-order review.

Outputs:
  - docs/SYSTEM_LOAD_ORDER_FULL.json
  - docs/SYSTEM_LOAD_ORDER_REVIEW.md

The report includes every tracked git file. Runtime source files
(.py/.ts/.tsx/.js/.jsx/.mjs/.cjs) are ordered by dependency graph
with SCC (cycle) handling. Remaining tracked files are appended in
deterministic lexical order.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
import ast
import json
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
JSON_OUT = DOCS_DIR / "SYSTEM_LOAD_ORDER_FULL.json"
MD_OUT = DOCS_DIR / "SYSTEM_LOAD_ORDER_REVIEW.md"

SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
TS_JS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

TS_IMPORT_PATTERNS = [
    re.compile(r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]"""),
    re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)"""),
    re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)"""),
]

PY_MAIN_PATTERN = re.compile(r"""if\s+__name__\s*==\s*["']__main__["']""")


@dataclass(frozen=True)
class SccInfo:
    id: int
    files: tuple[str, ...]
    has_self_loop: bool

    @property
    def in_cycle(self) -> bool:
        return len(self.files) > 1 or self.has_self_loop


def _run_git_ls_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return sorted(files)


def _language_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".py":
        return "python"
    if ext in TS_JS_EXTS:
        return "tsjs"
    return "other"


def _module_name_from_path(path: str) -> str | None:
    p = Path(path)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _build_py_module_index(py_files: Iterable[str]) -> dict[str, str]:
    mod_to_paths: dict[str, list[str]] = defaultdict(list)
    for path in py_files:
        mod = _module_name_from_path(path)
        if mod:
            mod_to_paths[mod].append(path)
    resolved: dict[str, str] = {}
    for mod, paths in mod_to_paths.items():
        resolved[mod] = sorted(paths)[0]
    return resolved


def _resolve_py_module_to_file(mod: str, module_index: dict[str, str]) -> str | None:
    if not mod:
        return None
    candidate = mod
    while candidate:
        hit = module_index.get(candidate)
        if hit:
            return hit
        if "." not in candidate:
            break
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _read_text(path: str) -> str:
    abs_path = ROOT / path
    try:
        return abs_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return abs_path.read_text(encoding="latin-1", errors="ignore")


def _parse_python_imports(path: str, module_index: dict[str, str]) -> tuple[set[str], int]:
    text = _read_text(path)
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError:
        return set(), 0

    current_mod = _module_name_from_path(path) or ""
    current_pkg = current_mod.rsplit(".", 1)[0] if "." in current_mod else ""
    unresolved = 0
    deps: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve_py_module_to_file(alias.name, module_index)
                if target:
                    deps.add(target)
                else:
                    unresolved += 1
        elif isinstance(node, ast.ImportFrom):
            base_mod = ""
            if node.level and node.level > 0:
                pkg_parts = current_pkg.split(".") if current_pkg else []
                if node.level - 1 > len(pkg_parts):
                    unresolved += 1
                    continue
                prefix_parts = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                if node.module:
                    base_mod = ".".join(prefix_parts + node.module.split("."))
                else:
                    base_mod = ".".join(prefix_parts)
            else:
                base_mod = node.module or ""

            candidates: set[str] = set()
            if base_mod:
                candidates.add(base_mod)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if base_mod:
                    candidates.add(f"{base_mod}.{alias.name}")
                else:
                    candidates.add(alias.name)

            resolved_any = False
            for mod in candidates:
                target = _resolve_py_module_to_file(mod, module_index)
                if target:
                    deps.add(target)
                    resolved_any = True
            if not resolved_any and candidates:
                unresolved += 1

    deps.discard(path)
    return deps, unresolved


def _resolve_ts_spec(path: str, spec: str, tracked_set: set[str]) -> str | None:
    base_candidates: list[Path] = []
    file_dir = (ROOT / path).parent

    if spec.startswith("."):
        base_candidates.append((file_dir / spec).resolve())
    elif spec.startswith("@/"):
        base_candidates.append((ROOT / "src" / spec[2:]).resolve())
    elif spec.startswith("src/"):
        base_candidates.append((ROOT / spec).resolve())
    elif spec.startswith("/"):
        base_candidates.append((ROOT / spec[1:]).resolve())
    else:
        # Package import; treat as external unless it happens to resolve to tracked root path.
        base_candidates.append((ROOT / spec).resolve())

    possible_exts = ["", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
    for base in base_candidates:
        for ext in possible_exts:
            candidate = base if not ext else Path(f"{base}{ext}")
            try:
                rel = candidate.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if rel in tracked_set:
                return rel
        for idx_ext in [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]:
            idx = base / f"index{idx_ext}"
            try:
                rel = idx.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if rel in tracked_set:
                return rel
    return None


def _parse_ts_imports(path: str, tracked_set: set[str]) -> tuple[set[str], int]:
    text = _read_text(path)
    deps: set[str] = set()
    unresolved = 0

    for pattern in TS_IMPORT_PATTERNS:
        for match in pattern.finditer(text):
            spec = match.group(1).strip()
            if not spec or spec.startswith(("node:", "http:", "https:")):
                continue
            target = _resolve_ts_spec(path, spec, tracked_set)
            if target and Path(target).suffix.lower() in SOURCE_EXTS:
                deps.add(target)
            else:
                unresolved += 1

    deps.discard(path)
    return deps, unresolved


def _build_graph(source_files: list[str], tracked_set: set[str]) -> tuple[dict[str, set[str]], dict[str, int]]:
    graph: dict[str, set[str]] = {path: set() for path in source_files}
    unresolved_by_lang = {"python": 0, "tsjs": 0}

    py_files = [p for p in source_files if p.endswith(".py")]
    module_index = _build_py_module_index(py_files)

    for path in source_files:
        lang = _language_for(path)
        if lang == "python":
            deps, unresolved = _parse_python_imports(path, module_index)
            graph[path].update(dep for dep in deps if dep in graph)
            unresolved_by_lang["python"] += unresolved
        elif lang == "tsjs":
            deps, unresolved = _parse_ts_imports(path, tracked_set)
            graph[path].update(dep for dep in deps if dep in graph)
            unresolved_by_lang["tsjs"] += unresolved

    return graph, unresolved_by_lang


def _tarjan_scc(graph: dict[str, set[str]]) -> list[SccInfo]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    result: list[SccInfo] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in sorted(graph[v]):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            comp: list[str] = []
            has_self_loop = False
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            comp_sorted = tuple(sorted(comp))
            if len(comp_sorted) == 1:
                node = comp_sorted[0]
                has_self_loop = node in graph[node]
            result.append(SccInfo(id=len(result), files=comp_sorted, has_self_loop=has_self_loop))

    for node in sorted(graph):
        if node not in indices:
            strongconnect(node)

    return result


def _topological_component_order(graph: dict[str, set[str]], sccs: list[SccInfo]) -> tuple[list[int], dict[str, int]]:
    file_to_comp: dict[str, int] = {}
    for scc in sccs:
        for path in scc.files:
            file_to_comp[path] = scc.id

    # Build dependency-first DAG between components:
    # if A depends on B (A -> B), we add B -> A
    dag: dict[int, set[int]] = {scc.id: set() for scc in sccs}
    indeg: dict[int, int] = {scc.id: 0 for scc in sccs}
    for src, deps in graph.items():
        c_src = file_to_comp[src]
        for dep in deps:
            c_dep = file_to_comp[dep]
            if c_src == c_dep:
                continue
            if c_src not in dag[c_dep]:
                dag[c_dep].add(c_src)
                indeg[c_src] += 1

    comp_key = {scc.id: scc.files[0] for scc in sccs}
    ready = deque(sorted([cid for cid, d in indeg.items() if d == 0], key=lambda c: comp_key[c]))
    ordered: list[int] = []

    while ready:
        cid = ready.popleft()
        ordered.append(cid)
        for nxt in sorted(dag[cid], key=lambda c: comp_key[c]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                # Maintain deterministic lexical behavior.
                insert_at = 0
                while insert_at < len(ready) and comp_key[ready[insert_at]] <= comp_key[nxt]:
                    insert_at += 1
                ready.insert(insert_at, nxt)

    # Fallback (should not happen with SCC DAG) for completeness.
    if len(ordered) != len(sccs):
        remaining = [scc.id for scc in sccs if scc.id not in set(ordered)]
        ordered.extend(sorted(remaining, key=lambda c: comp_key[c]))

    return ordered, file_to_comp


def _find_entrypoints(tracked_files: list[str]) -> list[str]:
    tracked_set = set(tracked_files)
    candidates = [
        "src/index.ts",
        "src/api/server.ts",
        "src/api/index.ts",
        "src/api/main.py",
        "api/main.py",
        "six-tongues-cli.py",
        "scbe-cli.py",
        "enhanced_scbe_cli.py",
        "scripts/linux_kernel_antivirus_monitor.py",
        "scripts/spiral_engine_game_sim.py",
    ]
    found = [c for c in candidates if c in tracked_set]

    py_mains: list[str] = []
    excluded_prefixes = (
        "tests/",
        "docs/",
        "archive/",
        ".kiro/",
        "SCBE-AETHERMOORE-v3.0.0/",
    )
    included_prefixes = ("scripts/", "api/", "agents/", "src/")
    for path in tracked_files:
        if not path.endswith(".py"):
            continue
        if path.startswith(excluded_prefixes) or "/tests/" in path:
            continue
        if "/" in path and not path.startswith(included_prefixes):
            continue
        text = _read_text(path)
        if PY_MAIN_PATTERN.search(text):
            py_mains.append(path)
    for path in sorted(py_mains):
        if path not in found:
            found.append(path)
    return found


def main() -> int:
    tracked_files = _run_git_ls_files()
    tracked_set = set(tracked_files)

    source_files = [p for p in tracked_files if Path(p).suffix.lower() in SOURCE_EXTS]
    graph, unresolved_by_lang = _build_graph(source_files, tracked_set)
    dep_edges = sum(len(v) for v in graph.values())

    sccs = _tarjan_scc(graph)
    scc_by_id = {scc.id: scc for scc in sccs}
    comp_order, file_to_comp = _topological_component_order(graph, sccs)

    ordered_source: list[str] = []
    cycle_components: list[SccInfo] = []
    for cid in comp_order:
        scc = scc_by_id[cid]
        if scc.in_cycle:
            cycle_components.append(scc)
        ordered_source.extend(sorted(scc.files))

    ordered_source_set = set(ordered_source)
    non_source = [p for p in tracked_files if p not in ordered_source_set]

    entrypoints = _find_entrypoints(tracked_files)

    source_records: list[dict[str, object]] = []
    for idx, path in enumerate(ordered_source, start=1):
        cid = file_to_comp[path]
        scc = scc_by_id[cid]
        source_records.append(
            {
                "index": idx,
                "path": path,
                "language": _language_for(path),
                "component_id": cid,
                "in_cycle": scc.in_cycle,
                "dependency_count": len(graph[path]),
            }
        )

    full_records: list[dict[str, object]] = []
    n_source = len(source_records)
    for rec in source_records:
        full_records.append(
            {
                "index": rec["index"],
                "path": rec["path"],
                "phase": "runtime_source",
                "language": rec["language"],
                "component_id": rec["component_id"],
                "in_cycle": rec["in_cycle"],
            }
        )
    for j, path in enumerate(non_source, start=1):
        full_records.append(
            {
                "index": n_source + j,
                "path": path,
                "phase": "non_source",
                "language": _language_for(path),
                "component_id": None,
                "in_cycle": False,
            }
        )

    cycle_payload = [
        {
            "component_id": scc.id,
            "size": len(scc.files),
            "files": list(scc.files),
        }
        for scc in sorted(cycle_components, key=lambda c: (len(c.files), c.files[0]), reverse=True)
    ]

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "repo_root": str(ROOT),
        "totals": {
            "tracked_files": len(tracked_files),
            "source_files": len(source_files),
            "python_source_files": sum(1 for p in source_files if p.endswith(".py")),
            "ts_js_source_files": sum(1 for p in source_files if Path(p).suffix.lower() in TS_JS_EXTS),
            "dependency_edges": dep_edges,
            "scc_components": len(sccs),
            "cycle_components": len(cycle_components),
        },
        "unresolved_import_estimates": unresolved_by_lang,
        "entrypoints": entrypoints,
        "source_load_order": source_records,
        "cycle_components": cycle_payload,
        "full_file_order": full_records,
    }

    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cycle_lines = "\n".join(
        [
            f"- `component {c['component_id']}` size `{c['size']}`: `{c['files'][0]}`"
            for c in cycle_payload[:20]
        ]
    )
    if not cycle_lines:
        cycle_lines = "- none"

    top_source_preview = "\n".join(
        [
            f"{rec['index']}. `{rec['path']}` ({rec['language']})"
            for rec in source_records[:40]
        ]
    )
    if not top_source_preview:
        top_source_preview = "No source files found."

    md = f"""# Full System Review: Deterministic Load Order

Generated: `{payload["generated_at_utc"]}`

## Scope

- Total tracked files: `{payload["totals"]["tracked_files"]}`
- Runtime source files ordered by dependency graph: `{payload["totals"]["source_files"]}`
- Python sources: `{payload["totals"]["python_source_files"]}`
- TS/JS sources: `{payload["totals"]["ts_js_source_files"]}`
- Dependency edges: `{payload["totals"]["dependency_edges"]}`
- SCC components: `{payload["totals"]["scc_components"]}`
- Cycle components: `{payload["totals"]["cycle_components"]}`

## Entrypoints Considered

{chr(10).join([f"- `{ep}`" for ep in entrypoints]) if entrypoints else "- none detected"}

## Cycle Highlights (Top 20)

{cycle_lines}

## Source Load Order Preview (First 40)

{top_source_preview}

## Full Ordered Manifest

See `docs/SYSTEM_LOAD_ORDER_FULL.json` for the complete ordered list of every tracked file:

- `source_load_order`: dependency-first runtime order for all source files.
- `full_file_order`: every tracked file, with source first then non-source lexical order.
"""
    MD_OUT.write_text(md, encoding="utf-8")

    print(f"Wrote {JSON_OUT}")
    print(f"Wrote {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
