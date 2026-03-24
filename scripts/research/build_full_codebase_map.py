#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "research"
REPORT_PATH = REPO_ROOT / "docs" / "research" / "FULL_CODEBASE_RESEARCH_2026-03-23.md"
JSON_PATH = ARTIFACT_DIR / "full_codebase_map.json"
CSV_PATH = ARTIFACT_DIR / "full_codebase_map.csv"
LANE_JSON_PATH = ARTIFACT_DIR / "full_codebase_lane_stats.json"

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".next",
}

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".ps1",
    ".sh",
    ".bat",
    ".cmd",
    ".mjs",
    ".cjs",
    ".html",
    ".css",
    ".svg",
    ".csv",
    ".sql",
    ".ipynb",
    ".tex",
    ".spec",
    ".lock",
    ".env.example",
}

ACTIVE_LANE_DESCRIPTIONS = {
    "src/harmonic": "14-layer harmonic pipeline, hyperbolic geometry, wall and projection math.",
    "src/ai_brain": "AI cognition and embedding-adjacent reasoning modules.",
    "src/crypto": "TypeScript cryptography, envelopes, replay guards, key derivation, integrity layers.",
    "src/governance": "Decision policy, offline governance, gating, risk handling.",
    "src/tokenizer": "Tokenization and language-front-door components for SCBE inputs.",
    "src/tongues": "Tongue-specific language machinery and symbolic language structures.",
    "src/symphonic": "Symphonic cipher and musical/harmonic integration lane.",
    "src/symphonic_cipher": "Cipher-specific implementation lane tied to symphonic constructs.",
    "src/api": "Newer FastAPI control plane, HYDRA routes, SaaS, mesh, billing.",
    "api": "Older production-governance API with authorization, persistence, metering, audit.",
    "scripts": "Operational control plane, automation, research tooling, deployment, and daily workflows.",
    "tests": "Regression, adversarial, interoperability, and validation suites.",
    "docs": "Specs, research notes, product documentation, and operational guides.",
    "src/storage": "Storage backends, sealed blobs, persistence helpers.",
    "src/memory": "Memory and sealing related modules.",
    "src/security": "Security-specific runtime and policy support modules.",
    "src/security-engine": "Security engine exports and implementation glue.",
    "src/network": "Network, routing, contact graph, and distributed communication pieces.",
    "src/spaceTor": "Space communications, routing, trust, and onion-style orbital networking.",
    "src/m4mesh": "M4 mesh and SMEAR operator mathematics.",
    "src/spiralverse": "Intent-auth, communication, and Spiralverse language plane.",
    "src/physics_sim": "Physics-oriented simulation lane.",
    "artifacts": "Generated evidence, reports, outputs, and experiment products.",
    "training-data": "Corpora, datasets, and training-oriented source material.",
    "deploy": "Cloud deployment assets and runtime packaging.",
    "k8s": "Kubernetes manifests and orchestration assets.",
}

REPRESENTATIVE_ENTRYPOINTS = {
    "src/harmonic": ["src/index.ts", "src/harmonic/index.ts"],
    "src/ai_brain": ["src/index.ts", "src/ai_brain/index.ts"],
    "src/crypto": ["src/index.ts", "src/crypto/index.ts"],
    "src/governance": ["src/index.ts", "src/governance/index.ts"],
    "src/tokenizer": ["src/tokenizer/index.ts"],
    "src/api": ["src/api/main.py"],
    "api": ["api/main.py"],
    "scripts": ["scripts/hydra_command_center.ps1"],
    "tests": ["tests/adversarial/scbe_harness.py"],
    "docs": ["README.md", "docs/LANGUES_WEIGHTING_SYSTEM.md", "SPEC.md"],
}

PY_SYMBOL_RE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
TS_SYMBOL_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|const|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
PS1_SYMBOL_RE = re.compile(r"^function\s+([A-Za-z_][A-Za-z0-9_-]*)", re.MULTILINE)


@dataclass
class FileRecord:
    path: str
    aspect: str
    lane: str
    state: str
    extension: str
    bytes: int
    lines: int
    text: bool
    sha16: str
    summary: str
    symbols: list[str]


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            sample = handle.read(2048)
        return b"\x00" not in sample
    except OSError:
        return False


def sha16(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def classify_state(parts: tuple[str, ...]) -> str:
    joined = "/".join(parts)
    lower = joined.lower()
    if joined.startswith("tests/"):
        return "test"
    if joined.startswith("artifacts/") or joined.startswith("dist/"):
        return "generated"
    if "archive" in lower or lower.startswith("docs/archive"):
        return "archive"
    if joined.startswith("training-data/"):
        return "dataset"
    if joined.startswith("docs/"):
        return "documentation"
    if joined.startswith("scripts/"):
        return "operations"
    return "active"


def classify_aspect(path: Path) -> str:
    parts = path.parts
    if not parts:
        return "root"
    if parts[0] == "src" and len(parts) > 1:
        return f"src/{parts[1]}"
    if parts[0] == "tests" and len(parts) > 1:
        return f"tests/{parts[1]}"
    return parts[0]


def classify_lane(aspect: str) -> str:
    if aspect.startswith("src/"):
        return (
            "core"
            if aspect
            in {
                "src/harmonic",
                "src/crypto",
                "src/governance",
                "src/tokenizer",
                "src/tongues",
                "src/symphonic",
                "src/symphonic_cipher",
                "src/ai_brain",
            }
            else "runtime"
        )
    if aspect == "api":
        return "runtime"
    if aspect == "scripts":
        return "operations"
    if aspect.startswith("tests/") or aspect == "tests":
        return "validation"
    if aspect == "docs":
        return "documentation"
    if aspect in {"artifacts", "dist"}:
        return "generated"
    if aspect == "training-data":
        return "dataset"
    return "support"


def extract_summary(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:200]
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return stripped.strip("\"' ")[:200]
        if (
            stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
            or stripped.startswith("--")
        ):
            return stripped.lstrip("/*- ")[:200]
        return stripped[:200]
    return ""


def extract_symbols(path: Path, text: str) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return PY_SYMBOL_RE.findall(text)[:12]
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return TS_SYMBOL_RE.findall(text)[:12]
    if suffix == ".ps1":
        return PS1_SYMBOL_RE.findall(text)[:12]
    return []


def walk_files(root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(current_root) / name


def build_records() -> list[FileRecord]:
    records: list[FileRecord] = []
    for absolute in walk_files(REPO_ROOT):
        if not absolute.exists():
            continue
        relative = absolute.relative_to(REPO_ROOT)
        parts = relative.parts
        try:
            text_flag = is_text_file(absolute)
            size = absolute.stat().st_size
        except OSError:
            continue
        line_count = 0
        summary = ""
        symbols: list[str] = []
        if text_flag:
            try:
                text = absolute.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            line_count = text.count("\n") + (1 if text else 0)
            summary = extract_summary(text)
            symbols = extract_symbols(relative, text)
        aspect = classify_aspect(relative)
        try:
            digest = sha16(absolute)
        except OSError:
            continue
        records.append(
            FileRecord(
                path=relative.as_posix(),
                aspect=aspect,
                lane=classify_lane(aspect),
                state=classify_state(parts),
                extension=absolute.suffix.lower(),
                bytes=size,
                lines=line_count,
                text=text_flag,
                sha16=digest,
                summary=summary,
                symbols=symbols,
            )
        )
    records.sort(key=lambda item: item.path)
    return records


def lane_stats(records: list[FileRecord]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)
    for record in records:
        grouped[record.aspect].append(record)

    stats: dict[str, dict[str, object]] = {}
    for aspect, items in sorted(grouped.items()):
        ext_counter = Counter(item.extension or "<none>" for item in items)
        lane_counter = Counter(item.lane for item in items)
        state_counter = Counter(item.state for item in items)
        stats[aspect] = {
            "files": len(items),
            "text_files": sum(1 for item in items if item.text),
            "bytes": sum(item.bytes for item in items),
            "lines": sum(item.lines for item in items),
            "lanes": dict(lane_counter),
            "states": dict(state_counter),
            "top_extensions": ext_counter.most_common(6),
            "description": ACTIVE_LANE_DESCRIPTIONS.get(aspect, "Aspect discovered during full-file scan."),
            "representative_entrypoints": REPRESENTATIVE_ENTRYPOINTS.get(aspect, items[:3] and [items[0].path] or []),
        }
    return stats


def format_table(rows: list[tuple[str, int, int, int, str]]) -> str:
    header = "| Aspect | Files | Lines | Bytes | Notes |\n|---|---:|---:|---:|---|"
    lines = [header]
    for aspect, files, line_count, byte_count, notes in rows:
        lines.append(f"| `{aspect}` | {files} | {line_count} | {byte_count} | {notes} |")
    return "\n".join(lines)


def write_outputs(records: list[FileRecord], stats: dict[str, dict[str, object]]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "repo_root": str(REPO_ROOT),
                "file_count": len(records),
                "records": [asdict(record) for record in records],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["path", "aspect", "lane", "state", "extension", "bytes", "lines", "text", "sha16", "summary", "symbols"]
        )
        for record in records:
            writer.writerow(
                [
                    record.path,
                    record.aspect,
                    record.lane,
                    record.state,
                    record.extension,
                    record.bytes,
                    record.lines,
                    str(record.text),
                    record.sha16,
                    record.summary,
                    "; ".join(record.symbols),
                ]
            )

    LANE_JSON_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    aspect_rows = []
    for aspect, data in sorted(stats.items(), key=lambda item: item[1]["lines"], reverse=True)[:30]:
        aspect_rows.append(
            (
                aspect,
                int(data["files"]),
                int(data["lines"]),
                int(data["bytes"]),
                str(data["description"]),
            )
        )

    largest_text = sorted((r for r in records if r.text), key=lambda item: item.lines, reverse=True)[:25]
    by_lane = Counter(record.lane for record in records)
    by_state = Counter(record.state for record in records)
    by_ext = Counter(record.extension or "<none>" for record in records)

    report = []
    report.append("# Full Codebase Research Map — 2026-03-23")
    report.append("")
    report.append("## Scope")
    report.append("")
    report.append(
        "This report is the repo-wide map for `SCBE-AETHERMOORE` generated from a full file scan. It covers every file under the repository root except VCS internals and transient caches such as `.git`, `node_modules`, and `__pycache__`."
    )
    report.append("")
    report.append("The goal is two-layered:")
    report.append("")
    report.append("1. Provide a human research summary of the active system lanes.")
    report.append("2. Provide exhaustive machine-readable file inventories in JSON and CSV.")
    report.append("")
    report.append("## Repo Identity")
    report.append("")
    report.append(
        "SCBE-AETHERMOORE is a hybrid monorepo spanning a TypeScript governance and crypto core, Python API/runtime services, operator scripts, dataset and artifact lanes, and extensive documentation/research surfaces."
    )
    report.append("")
    report.append("## Totals")
    report.append("")
    report.append(f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`")
    report.append(f"- Total files mapped: `{len(records)}`")
    report.append(f"- Text files: `{sum(1 for record in records if record.text)}`")
    report.append(f"- Total mapped lines: `{sum(record.lines for record in records)}`")
    report.append(f"- Total mapped bytes: `{sum(record.bytes for record in records)}`")
    report.append("")
    report.append("## Lane Distribution")
    report.append("")
    for lane, count in sorted(by_lane.items()):
        report.append(f"- `{lane}`: `{count}` files")
    report.append("")
    report.append("## State Distribution")
    report.append("")
    for state, count in sorted(by_state.items()):
        report.append(f"- `{state}`: `{count}` files")
    report.append("")
    report.append("## Dominant Aspects By Line Count")
    report.append("")
    report.append(format_table(aspect_rows))
    report.append("")
    report.append("## System-Aspects Research Summary")
    report.append("")
    for aspect, data in sorted(stats.items(), key=lambda item: item[1]["lines"], reverse=True)[:40]:
        report.append(f"### {aspect}")
        report.append("")
        report.append(f"- Description: {data['description']}")
        report.append(f"- Files: `{data['files']}`")
        report.append(f"- Lines: `{data['lines']}`")
        report.append(f"- Bytes: `{data['bytes']}`")
        report.append(f"- Top extensions: `{data['top_extensions']}`")
        report.append(f"- Representative entrypoints: `{data['representative_entrypoints']}`")
        report.append("")
    report.append("## Largest Text Files")
    report.append("")
    report.append("| Path | Lines | Summary |\n|---|---:|---|")
    for record in largest_text:
        summary = record.summary.replace("|", "/")[:120]
        report.append(f"| `{record.path}` | {record.lines} | {summary} |")
    report.append("")
    report.append("## Extension Distribution")
    report.append("")
    report.append("| Extension | Count |\n|---|---:|")
    for ext, count in by_ext.most_common(25):
        report.append(f"| `{ext}` | {count} |")
    report.append("")
    report.append("## Research Conclusions")
    report.append("")
    report.append(
        "1. The repo is not one product surface; it is a mesh of core math, runtime services, operator control, research, and content pipelines."
    )
    report.append(
        "2. The TypeScript core and Python runtime lanes coexist rather than cleanly replacing one another; both must be mapped when making claims about the system."
    )
    report.append("3. `scripts/` is a real operational control plane, not just glue code.")
    report.append(
        "4. `docs/`, `artifacts/`, and `training-data/` are substantial parts of system knowledge, but they should be separated from proof of runtime behavior."
    )
    report.append(
        "5. Any future benchmark or architecture claim should cite both the canonical core lane and the exact runtime lane used."
    )
    report.append("")
    report.append("## Exhaustive Inventory Artifacts")
    report.append("")
    report.append(f"- JSON map: `{JSON_PATH.relative_to(REPO_ROOT).as_posix()}`")
    report.append(f"- CSV map: `{CSV_PATH.relative_to(REPO_ROOT).as_posix()}`")
    report.append(f"- Lane stats: `{LANE_JSON_PATH.relative_to(REPO_ROOT).as_posix()}`")
    report.append("")
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    records = build_records()
    stats = lane_stats(records)
    write_outputs(records, stats)

    total_lines = sum(record.lines for record in records)
    total_bytes = sum(record.bytes for record in records)
    by_lane = Counter(record.lane for record in records)
    largest_aspects = sorted(stats.items(), key=lambda item: item[1]["lines"], reverse=True)[:10]

    print("=" * 100)
    print(f"{'FULL CODEBASE MAP COMPLETE':^100}")
    print("=" * 100)
    print(f"Files mapped: {len(records)}")
    print(f"Text files: {sum(1 for record in records if record.text)}")
    print(f"Total lines: {total_lines}")
    print(f"Total bytes: {total_bytes}")
    print("Lane counts:")
    for lane, count in sorted(by_lane.items()):
        print(f"  {lane}: {count}")
    print("Top aspects by line count:")
    for aspect, data in largest_aspects:
        print(f"  {aspect}: {data['files']} files, {data['lines']} lines")
    print(f"Saved: {REPORT_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(f"Saved: {JSON_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(f"Saved: {CSV_PATH.relative_to(REPO_ROOT).as_posix()}")
    print(f"Saved: {LANE_JSON_PATH.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
