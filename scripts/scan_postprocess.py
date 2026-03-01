"""
Post-process a repo_scanner.py run into:
1) a priority "clean vs risky vs archive" folder/file map
2) an automatic task list (highest-risk / highest-leverage first)

Usage:
  python scripts/scan_postprocess.py \
    --scan-dir artifacts/repo_scans/20260301T063019Z-full_codebase \
    --out-dir  artifacts/repo_scans/20260301T063019Z-full_codebase/postprocess \
    --format   all

Inputs expected in --scan-dir:
  - scan_manifest.json
  - scan_summary.json (optional)

Outputs (in --out-dir):
  - folder_map.json
  - folder_map.md
  - tasks.json
  - tasks.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_RISK_PATTERNS = [
    # Secrets / creds
    (r"AKIA[0-9A-Z]{16}", "aws_access_key_id"),
    (r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----", "private_key_block"),
    (r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]", "inline_secret_assignment"),
    (r"(?i)\b(bearer)\s+[a-z0-9\-_\.=]{12,}", "bearer_token"),
    # Dangerous ops / bypasses
    (r"(?i)\b(disable|bypass|skip)\b.*\b(govern|policy|guard|safety)\b", "governance_bypass_language"),
    (r"(?i)\beval\(", "python_eval"),
    (r"(?i)\bexec\(", "python_exec"),
    # Network / shell
    (r"(?i)\bsubprocess\.(run|popen|call)\b", "subprocess_usage"),
    (r"(?i)\bos\.system\(", "os_system"),
]

DEFAULT_RISK_PATH_HINTS = [
    # Likely high-impact / security-sensitive
    (re.compile(r"(^|/)(auth|oauth|token|keys?)(/|$)", re.I), "auth_keys_area"),
    (re.compile(r"(^|/)(governance|policy|guardrails?)(/|$)", re.I), "governance_core"),
    (re.compile(r"(^|/)(gateway|proxy|api)(/|$)", re.I), "api_surface"),
    (re.compile(r"(^|/)(connectors?|octo_armor|fleet)(/|$)", re.I), "connectors_surface"),
    (re.compile(r"(^|/)(scripts)(/|$)", re.I), "scripts_ops"),
]

DEFAULT_ARCHIVE_PATH_HINTS = [
    re.compile(r"(^|/)(__pycache__|node_modules|dist|build|\.venv|\.git)(/|$)", re.I),
    re.compile(r"(^|/)(artifacts|archive|backups?|tmp|logs?)(/|$)", re.I),
    re.compile(r"(^|/)(docs/08-reference/archive)(/|$)", re.I),
]

DEFAULT_CLEAN_PATH_HINTS = [
    re.compile(r"(^|/)(src)(/|$)", re.I),
    re.compile(r"(^|/)(tests)(/|$)", re.I),
]


@dataclass
class FileRow:
    path: str
    size_bytes: int
    ext: str
    kind: str
    content_hash: Optional[str] = None


@dataclass
class FileClassification:
    path: str
    category: str  # clean | risky | archive
    score: float
    reasons: List[str]


@dataclass
class FolderRollup:
    folder: str
    clean: int
    risky: int
    archive: int
    total: int
    top_reasons: List[str]


@dataclass
class TaskItem:
    id: str
    priority: int
    title: str
    rationale: str
    suggested_files: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)


def _write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _infer_kind(ext: str) -> str:
    ext = ext.lower()
    if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".ps1", ".sh", ".bat", ".cmd"):
        return "code"
    if ext in (".md", ".txt", ".rst"):
        return "doc"
    if ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"):
        return "config"
    return "other"


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def _folder_of(path: str) -> str:
    p = _normalize_path(path)
    if "/" not in p:
        return "."
    return p.rsplit("/", 1)[0] or "."


def _load_manifest(scan_dir: Path) -> List[FileRow]:
    manifest_path = scan_dir / "scan_manifest.json"
    data = _read_json(manifest_path)

    # Flexible parsing: accept either {"files":[...]} or plain list
    rows = data["files"] if isinstance(data, dict) and "files" in data else data
    out: List[FileRow] = []
    for r in rows:
        path = _normalize_path(r.get("path") or r.get("filepath") or r.get("file") or "")
        if not path:
            continue
        size = int(r.get("size_bytes") or r.get("size") or 0)
        ext = r.get("ext") or os.path.splitext(path)[1]
        ch = r.get("content_hash") or r.get("hash")
        kind = r.get("kind") or _infer_kind(ext)
        out.append(FileRow(path=path, size_bytes=size, ext=ext, kind=kind, content_hash=ch))
    return out


def _classify_file(
    row: FileRow,
    risky_path_hints=DEFAULT_RISK_PATH_HINTS,
    archive_path_hints=DEFAULT_ARCHIVE_PATH_HINTS,
    clean_path_hints=DEFAULT_CLEAN_PATH_HINTS,
) -> FileClassification:
    """
    Classify by path-based heuristics + size.
    (Content-pattern checks are optional and can be added later by reading file text;
     we keep this postprocess lightweight and deterministic on manifest-only.)
    """
    path = row.path
    reasons: List[str] = []
    score = 0.0

    # Archive detection (strong)
    for rx in archive_path_hints:
        if rx.search(path):
            reasons.append("archive_path_hint")
            score += 0.9
            return FileClassification(path=path, category="archive", score=min(score, 1.0), reasons=reasons)

    # Risk hints by folder area
    is_high_risk_path = False
    for rx, tag in risky_path_hints:
        if rx.search(path):
            reasons.append(tag)
            score += 0.25
            if tag == "governance_core":
                score += 0.10
                is_high_risk_path = True

    # Scripts are riskier than library code
    if "/scripts/" in f"/{path}/".lower():
        reasons.append("script_area")
        score += 0.15

    # Config files can contain secrets
    if row.kind == "config" or row.ext.lower() in (".env",):
        reasons.append("config_file")
        score += 0.20

    # Very large source files often hide complexity / attack surface
    if row.kind == "code" and row.size_bytes > 200_000:
        reasons.append("large_code_file")
        score += 0.15

    # Clean hints
    is_clean_area = any(rx.search(path) for rx in clean_path_hints)
    if is_clean_area:
        reasons.append("clean_area")
        score -= 0.10  # reduce risk slightly

    # Decide category
    # - If score high -> risky
    # - If clearly in clean areas and low score -> clean
    if is_high_risk_path or score >= 0.30:
        category = "risky"
    else:
        category = "clean" if is_clean_area else "clean"

    score = float(max(0.0, min(score, 1.0)))
    return FileClassification(path=path, category=category, score=score, reasons=reasons)


def build_folder_map(classifications: List[FileClassification]) -> Tuple[List[FolderRollup], Dict[str, Any]]:
    folder_counts = defaultdict(lambda: {"clean": 0, "risky": 0, "archive": 0, "reasons": defaultdict(int)})
    for c in classifications:
        folder = _folder_of(c.path)
        folder_counts[folder][c.category] += 1
        for r in c.reasons:
            folder_counts[folder]["reasons"][r] += 1

    rollups: List[FolderRollup] = []
    for folder, d in folder_counts.items():
        total = d["clean"] + d["risky"] + d["archive"]
        top = sorted(d["reasons"].items(), key=lambda kv: kv[1], reverse=True)[:5]
        rollups.append(
            FolderRollup(
                folder=folder,
                clean=d["clean"],
                risky=d["risky"],
                archive=d["archive"],
                total=total,
                top_reasons=[f"{k} ({v})" for k, v in top],
            )
        )

    # Sort: risky density then total
    def key(fr: FolderRollup) -> Tuple[float, int]:
        density = fr.risky / max(fr.total, 1)
        return (-density, -fr.risky)

    rollups.sort(key=key)

    summary = {
        "generated_at": _utc_now_iso(),
        "folders": len(rollups),
        "totals": {
            "clean": sum(r.clean for r in rollups),
            "risky": sum(r.risky for r in rollups),
            "archive": sum(r.archive for r in rollups),
        },
    }
    return rollups, summary


def propose_tasks(classifications: List[FileClassification]) -> List[TaskItem]:
    """
    Produce a practical, money-first + security-first task list from the scan.
    This is heuristic: it looks for hot areas by path and proposes actionable next steps.
    """
    risky_files = [c for c in classifications if c.category == "risky"]
    by_reason = defaultdict(list)
    for c in risky_files:
        for r in c.reasons:
            by_reason[r].append(c.path)

    def top_files(reason: str, limit: int = 12) -> List[str]:
        paths = sorted(set(by_reason.get(reason, [])))
        return paths[:limit]

    tasks: List[TaskItem] = []

    # 1) Governance bypass / core surfaces audit
    tasks.append(
        TaskItem(
            id="T01",
            priority=1,
            title="Governance choke-point audit (L13 decision paths)",
            rationale=(
                "Identify every path that can call tools/LLMs/connectors without passing through "
                "a single authoritative ALLOW/QUARANTINE/DENY (and ESCALATE if present). "
                "This is the highest-leverage safety + product trust work."
            ),
            suggested_files=top_files("governance_core") + top_files("api_surface") + top_files("connectors_surface"),
        )
    )

    # 2) Secrets/config hygiene
    tasks.append(
        TaskItem(
            id="T02",
            priority=2,
            title="Config + secret hygiene pass (prevent accidental credential leakage)",
            rationale=(
                "Scan config/script areas for embedded secrets and ensure .env / keys never "
                "enter artifacts or receipts. Add CI checks if missing."
            ),
            suggested_files=top_files("config_file") + top_files("script_area") + top_files("auth_keys_area"),
        )
    )

    # 3) Public API contract
    tasks.append(
        TaskItem(
            id="T03",
            priority=3,
            title="Public API contract hardening (OpenAPI + signed receipts)",
            rationale=(
                "Turn L12/L13 into a sellable SKU: stable request/response schema + signed governance receipts. "
                "Add schema snapshot tests to lock the contract."
            ),
            suggested_files=top_files("api_surface") + top_files("governance_core"),
        )
    )

    # 4) Operational scripts hardening
    tasks.append(
        TaskItem(
            id="T04",
            priority=4,
            title="Ops/scripts hardening (least-privilege + safe defaults)",
            rationale=(
                "Scripts are often the real attack surface. Ensure scripts that start gateways/connectors "
                "enforce governance and do not run unsafe defaults."
            ),
            suggested_files=top_files("scripts_ops") + top_files("script_area"),
        )
    )

    # De-duplicate suggested files and trim
    for t in tasks:
        t.suggested_files = list(dict.fromkeys([_normalize_path(p) for p in t.suggested_files]))[:25]

    return tasks


def render_folder_map_md(rollups: List[FolderRollup], summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Repo Scan Postprocess — Folder Map")
    lines.append("")
    lines.append(f"- generated_at: `{summary['generated_at']}`")
    lines.append(f"- folders: **{summary['folders']}**")
    lines.append(
        f"- totals: clean={summary['totals']['clean']} | risky={summary['totals']['risky']} | archive={summary['totals']['archive']}"
    )
    lines.append("")
    lines.append("## Highest-risk folders (by risky density)")
    lines.append("")
    lines.append("| folder | risky | clean | archive | total | top reasons |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for r in rollups[:40]:
        lines.append(
            f"| `{r.folder}` | {r.risky} | {r.clean} | {r.archive} | {r.total} | {', '.join(r.top_reasons) if r.top_reasons else ''} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_tasks_md(tasks: List[TaskItem]) -> str:
    lines = []
    lines.append("# Repo Scan Postprocess — Task List")
    lines.append("")
    lines.append(f"- generated_at: `{_utc_now_iso()}`")
    lines.append("")
    for t in sorted(tasks, key=lambda x: x.priority):
        lines.append(f"## {t.id} (P{t.priority}) — {t.title}")
        lines.append("")
        lines.append(t.rationale)
        lines.append("")
        if t.suggested_files:
            lines.append("Suggested files/folders:")
            for p in t.suggested_files:
                lines.append(f"- `{p}`")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True, help="Path to a repo_scanner.py output directory (contains scan_manifest.json).")
    ap.add_argument("--out-dir", required=True, help="Where to write postprocess outputs.")
    ap.add_argument("--format", default="all", choices=["all", "json", "md"], help="Output formats to emit.")
    args = ap.parse_args()

    scan_dir = Path(args.scan_dir)
    out_dir = Path(args.out_dir)

    files = _load_manifest(scan_dir)
    classifications = [_classify_file(r) for r in files]

    rollups, summary = build_folder_map(classifications)
    tasks = propose_tasks(classifications)

    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": _utc_now_iso(),
        "scan_dir": str(scan_dir).replace("\\", "/"),
        "summary": summary,
        "classifications": [asdict(c) for c in classifications],
    }
    folder_map_payload = {
        "generated_at": _utc_now_iso(),
        "summary": summary,
        "folders": [asdict(r) for r in rollups],
    }
    tasks_payload = {
        "generated_at": _utc_now_iso(),
        "tasks": [asdict(t) for t in sorted(tasks, key=lambda x: x.priority)],
    }

    if args.format in ("all", "json"):
        _write_json(out_dir / "folder_map.json", folder_map_payload)
        _write_json(out_dir / "tasks.json", tasks_payload)

    if args.format in ("all", "md"):
        _write_text(out_dir / "folder_map.md", render_folder_map_md(rollups, summary))
        _write_text(out_dir / "tasks.md", render_tasks_md(tasks))

    # Always write a compact index.json for pipelines
    _write_json(out_dir / "postprocess_index.json", {"folder_map": "folder_map.json", "tasks": "tasks.json"})

    # Persist lightweight payload for downstream tooling
    _write_json(out_dir / "scan_postprocess_results.json", payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
