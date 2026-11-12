#!/usr/bin/env python3
"""Classify CI logs into bounded repair plans and apply the safe ones.

Safe applies are limited to two patterns that already showed up on main:

* a security-floor snapshot test expects an older purl than the lock resolved
* an npm audit high finding whose fix is a newer release of a known package

Everything else (live 404s, event-loop misuse, missing assets, optional
imports) is reported and left for a person. This script never lowers a floor.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FLOOR_SNAPSHOT = "tests/test_dependency_snapshot.py"
JOI_MANIFEST = "scbe-visual-system/package.json"
JOI_LOCK = "scbe-visual-system/package-lock.json"
JOI_FLOOR = ">=18.3.1"
JOI_OVERRIDE_ANCHOR = '"@xmldom/xmldom": "0.8.15"'

PURL_RE = re.compile(
    r"assert 'pkg:(?P<eco>pypi|npm)/(?P<name>[^@']+)@(?P<got>[^']+)'"
    r" == 'pkg:(?P<eco2>pypi|npm)/(?P<name2>[^@']+)@(?P<want>[^']+)'"
)
SMOKE_404_RE = re.compile(r"(https?://\S+)\s+HTTP\s+404", re.IGNORECASE)
ASYNCIO_RE = re.compile(r"asyncio\.run\(\) cannot be called from a running event loop")
ASSET_RE = re.compile(r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'")
OPTIONAL_IMPORT_RE = re.compile(r"ModuleNotFoundError: No module named '([^']+)'")


@dataclass
class Repair:
    kind: str
    safe: bool
    summary: str
    evidence: str
    file: str | None = None
    package: str | None = None
    expected: str | None = None
    resolved: str | None = None
    floor: str | None = None
    hold_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_version(value: str) -> tuple[int, ...] | None:
    parts: list[int] = []
    for piece in value.split("."):
        digits = ""
        for char in piece:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            return None
        parts.append(int(digits))
    return tuple(parts) if parts else None


def version_gt(left: str, right: str) -> bool:
    parsed_left = parse_version(left)
    parsed_right = parse_version(right)
    if not parsed_left or not parsed_right:
        return False
    width = max(len(parsed_left), len(parsed_right))
    parsed_left = parsed_left + (0,) * (width - len(parsed_left))
    parsed_right = parsed_right + (0,) * (width - len(parsed_right))
    return parsed_left > parsed_right


def classify_text(text: str) -> list[Repair]:
    """Return every repair this log can justify, safe ones first."""

    repairs: list[Repair] = []
    seen: set[tuple[str, str]] = set()

    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("schema") == "scbe.npm-audit-all.v1":
            repairs.extend(_npm_report_repairs(payload))

    for match in PURL_RE.finditer(text):
        if match.group("eco") != match.group("eco2") or match.group("name") != match.group("name2"):
            continue
        name = match.group("name")
        got = match.group("got")
        want = match.group("want")
        key = ("purl_floor_drift", f"{name}@{want}->{got}")
        if key in seen:
            continue
        seen.add(key)
        newer = version_gt(got, want)
        repairs.append(
            Repair(
                kind="purl_floor_drift",
                safe=newer and match.group("eco") == "pypi",
                summary=f"Raise the {name} lock snapshot from {want} to {got}",
                evidence=match.group(0),
                file=FLOOR_SNAPSHOT,
                package=name,
                expected=want,
                resolved=got,
                hold_reason=None
                if newer
                else "Resolved version is not newer than the snapshot. Refusing to lower a floor.",
            )
        )

    for match in SMOKE_404_RE.finditer(text):
        url = match.group(1).rstrip(").,")
        key = ("live_route_404", url)
        if key in seen:
            continue
        seen.add(key)
        repairs.append(
            Repair(
                kind="live_route_404",
                safe=False,
                summary=f"Live route returned 404: {url}",
                evidence=match.group(0),
                hold_reason=(
                    "A production 404 is not a pin bump. Check the deployed route table "
                    "before editing marketing copy or inventing a handler."
                ),
            )
        )

    if ASYNCIO_RE.search(text):
        repairs.append(
            Repair(
                kind="asyncio_run_in_loop",
                safe=False,
                summary="asyncio.run() called inside a running event loop",
                evidence=ASYNCIO_RE.search(text).group(0),
                hold_reason=(
                    "pytest-asyncio already owns the loop. Await the coroutine in the test "
                    "instead of calling asyncio.run()."
                ),
            )
        )

    for match in ASSET_RE.finditer(text):
        path = match.group(1)
        key = ("missing_asset", path)
        if key in seen:
            continue
        seen.add(key)
        repairs.append(
            Repair(
                kind="missing_asset",
                safe=False,
                summary=f"Test expected a file that is not in the tree: {path}",
                evidence=match.group(0),
                hold_reason="Do not invent the missing asset. Skip the test or restore the real file.",
            )
        )

    for match in OPTIONAL_IMPORT_RE.finditer(text):
        module = match.group(1)
        key = ("optional_import", module)
        if key in seen:
            continue
        seen.add(key)
        repairs.append(
            Repair(
                kind="optional_import",
                safe=False,
                summary=f"Optional import failed: {module}",
                evidence=match.group(0),
                hold_reason="Guard the import with importorskip. Do not add the dependency blindly.",
            )
        )

    repairs.sort(key=lambda repair: (not repair.safe, repair.kind, repair.summary))
    return repairs


def _npm_report_repairs(payload: dict[str, Any]) -> list[Repair]:
    repairs: list[Repair] = []
    for project in payload.get("projects") or []:
        if not isinstance(project, dict):
            continue
        project_path = str(project.get("path") or "")
        for finding in project.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            if finding.get("severity") != "high" or finding.get("name") != "joi":
                continue
            fix = finding.get("fix_available")
            if fix is not True:
                repairs.append(
                    Repair(
                        kind="npm_advisory_floor",
                        safe=False,
                        summary="joi is high, but the advisory fix is not a simple floor bump",
                        evidence=json.dumps(finding, sort_keys=True),
                        file=JOI_MANIFEST if project_path == "scbe-visual-system" else None,
                        package="joi",
                        hold_reason="Refusing a semver-major downgrade or an unknown fix.",
                    )
                )
                continue
            if project_path != "scbe-visual-system":
                repairs.append(
                    Repair(
                        kind="npm_advisory_floor",
                        safe=False,
                        summary=f"High joi finding in {project_path or 'unknown project'}",
                        evidence=json.dumps(finding, sort_keys=True),
                        package="joi",
                        hold_reason="Auto-pin is only enabled for scbe-visual-system.",
                    )
                )
                continue
            repairs.append(
                Repair(
                    kind="npm_advisory_floor",
                    safe=True,
                    summary="Pin joi to the patched 18.3 line in scbe-visual-system",
                    evidence=json.dumps(
                        {"name": "joi", "severity": "high", "range": finding.get("range"), "path": project_path},
                        sort_keys=True,
                    ),
                    file=JOI_MANIFEST,
                    package="joi",
                    floor=JOI_FLOOR,
                )
            )
    return repairs


def render_markdown(repairs: list[Repair]) -> str:
    if not repairs:
        return "## Fixer plan\n\nNo recognized repair pattern in this log.\n"
    lines = ["## Fixer plan", ""]
    for index, repair in enumerate(repairs, start=1):
        lines.append(f"### {index}. {repair.summary}")
        lines.append(f"- kind: `{repair.kind}`")
        lines.append(f"- safe to apply: {'yes' if repair.safe else 'no'}")
        if repair.file:
            lines.append(f"- file: `{repair.file}`")
        if repair.hold_reason:
            lines.append(f"- hold: {repair.hold_reason}")
        lines.append("")
        lines.append("```text")
        lines.append(repair.evidence)
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text and new in text:
        return True
    if text.count(old) != 1:
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def _apply_purl(root: Path, repair: Repair) -> bool:
    if not repair.safe or not repair.file or not repair.package or not repair.expected or not repair.resolved:
        return False
    if not version_gt(repair.resolved, repair.expected):
        return False
    path = root / repair.file
    if not path.is_file():
        return False
    old = f'"{repair.package}": "{repair.expected}"'
    new = f'"{repair.package}": "{repair.resolved}"'
    return _replace_once(path, old, new)


def _apply_joi_override(root: Path, repair: Repair) -> bool:
    path = root / JOI_MANIFEST
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    floor_line = f'"joi": "{repair.floor or JOI_FLOOR}"'
    existing = re.search(r'"joi"\s*:\s*"([^"]*)"', text)
    if existing:
        if existing.group(1) == (repair.floor or JOI_FLOOR):
            return True
        return _replace_once(path, existing.group(0), floor_line)
    if JOI_OVERRIDE_ANCHOR not in text:
        return False
    return _replace_once(path, JOI_OVERRIDE_ANCHOR, JOI_OVERRIDE_ANCHOR + ",\n    " + floor_line)


def _joi_meta(version_spec: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["npm", "view", f"joi@{version_spec}", "version", "dist.integrity", "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "npm view joi failed")
    payload = json.loads(completed.stdout)
    entries = payload if isinstance(payload, list) else [payload]

    def integrity_of(entry: dict[str, Any]) -> str:
        if isinstance(entry.get("dist.integrity"), str):
            return entry["dist.integrity"]
        dist = entry.get("dist")
        if isinstance(dist, dict) and isinstance(dist.get("integrity"), str):
            return dist["integrity"]
        raise RuntimeError("npm view joi did not return an integrity")

    best = max(entries, key=lambda entry: parse_version(str(entry.get("version", ""))) or ())
    version = str(best["version"])
    return {
        "version": version,
        "integrity": integrity_of(best),
        "resolved": f"https://registry.npmjs.org/joi/-/joi-{version}.tgz",
    }


def _apply_joi_lock(root: Path, meta: dict[str, Any]) -> bool:
    path = root / JOI_LOCK
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r'("node_modules/joi": \{\n\s*"version": ")([^"]+)(",\n\s*"resolved": ")([^"]+)(",\n\s*"integrity": ")([^"]+)(")',
        text,
    )
    if not match:
        return False
    current = match.group(2)
    if current == meta["version"] or version_gt(current, meta["version"]):
        return True
    replacement = (
        f'{match.group(1)}{meta["version"]}{match.group(3)}{meta["resolved"]}'
        f'{match.group(5)}{meta["integrity"]}{match.group(7)}'
    )
    updated = text[: match.start()] + replacement + text[match.end() :]
    path.write_text(updated, encoding="utf-8")
    return True


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def apply_repairs(repairs: list[Repair], root: Path = REPO_ROOT, joi_meta: dict[str, Any] | None = None) -> list[str]:
    """Apply every safe repair. Returns repo-relative paths that changed."""

    changed: list[str] = []
    for repair in repairs:
        if not repair.safe:
            continue
        watched = [repair.file] if repair.file else []
        if repair.kind == "npm_advisory_floor" and JOI_LOCK not in watched:
            watched.append(JOI_LOCK)
        before = {relative: _read(root / relative) for relative in watched}
        if repair.kind == "purl_floor_drift":
            ok = _apply_purl(root, repair)
        elif repair.kind == "npm_advisory_floor" and repair.package == "joi":
            ok = _apply_joi_override(root, repair) and _apply_joi_lock(
                root, joi_meta if joi_meta is not None else _joi_meta(repair.floor or JOI_FLOOR)
            )
        else:
            ok = False
        if not ok:
            raise RuntimeError(f"Refusing to apply {repair.kind}: target did not match exactly once")
        for relative in watched:
            if _read(root / relative) != before[relative] and relative not in changed:
                changed.append(relative)
    return changed


def _read_inputs(paths: list[str]) -> str:
    if not paths:
        return ""
    chunks = []
    for raw in paths:
        file_path = Path(raw)
        if file_path.is_file():
            chunks.append(file_path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Log files or an npm-audit-all JSON report")
    parser.add_argument("--apply", action="store_true", help="Apply safe repairs in the repo")
    parser.add_argument("--json", action="store_true", help="Print a JSON result")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    text = _read_inputs(args.paths)
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()
    repairs = classify_text(text)
    changed: list[str] = []
    error = None
    if args.apply:
        try:
            changed = apply_repairs(repairs, args.root)
        except RuntimeError as exc:
            error = str(exc)

    if args.json or args.apply:
        print(
            json.dumps(
                {
                    "changed": bool(changed),
                    "files": changed,
                    "error": error,
                    "repairs": [repair.to_dict() for repair in repairs],
                },
                indent=2,
            )
        )
    else:
        print(render_markdown(repairs), end="")
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
