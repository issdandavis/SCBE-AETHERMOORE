#!/usr/bin/env python3
"""Audit every exact Python dependency surface without installing the project.

The repository contains several independent requirements files and a uv lock.
Auditing the runner's installed environment misses those files entirely. This
command discovers registry-backed exact pins, audits each unique package/version
once with pip-audit, maps findings back to every source file, and emits one
machine-readable report. VCS/editable and range-only requirements are inventoried
as skipped because they do not identify an auditable registry version.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Iterable

PACKAGE_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
EXACT_REQUIREMENT = re.compile(rf"^(?P<name>{PACKAGE_NAME})(?:\[[^\]]+\])?\s*==\s*(?P<version>[^\s;#]+)")
DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "archive",
        "artifacts",
        "cloud-archive",
        "dist",
        "external",
        "external_repos",
        "node_modules",
        "site-packages",
        "training-data",
        "venv",
        "_quarantine",
    }
)


def normalize_package_name(name: str) -> str:
    """Return the canonical comparison form from PEP 503."""

    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True, order=True)
class Pin:
    name: str
    version: str

    @property
    def key(self) -> tuple[str, str]:
        return (normalize_package_name(self.name), self.version)


@dataclass(frozen=True)
class Surface:
    path: str
    kind: str
    pins: tuple[Pin, ...]
    skipped: dict[str, int]


def _logical_requirement_lines(text: str) -> list[str]:
    lines: list[str] = []
    buffer = ""
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped and not buffer:
            continue
        if stripped.startswith("#") and not buffer:
            continue

        continued = stripped.endswith("\\")
        segment = stripped[:-1].rstrip() if continued else stripped
        buffer = f"{buffer} {segment}".strip()
        if not continued:
            if buffer:
                lines.append(buffer)
            buffer = ""

    if buffer:
        lines.append(buffer)
    return lines


def parse_requirements(path: Path, root: Path) -> Surface:
    pins: dict[tuple[str, str], Pin] = {}
    skipped: Counter[str] = Counter()

    for line in _logical_requirement_lines(path.read_text(encoding="utf-8")):
        lowered = line.lower()
        if lowered.startswith(("-e ", "--editable ")) or " @ git+" in lowered or lowered.startswith("git+"):
            skipped["vcs_or_editable"] += 1
            continue
        if " @ " in line:
            skipped["direct_url"] += 1
            continue
        if line.startswith("-"):
            skipped["option_or_include"] += 1
            continue

        match = EXACT_REQUIREMENT.match(line)
        if match is None or match.group("version").endswith(".*"):
            skipped["range_or_unpinned"] += 1
            continue

        pin = Pin(normalize_package_name(match.group("name")), match.group("version"))
        pins[pin.key] = pin

    return Surface(
        path=path.relative_to(root).as_posix(),
        kind="requirements",
        pins=tuple(sorted(pins.values())),
        skipped=dict(sorted(skipped.items())),
    )


def parse_uv_lock(path: Path, root: Path) -> Surface:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    pins: dict[tuple[str, str], Pin] = {}
    skipped: Counter[str] = Counter()

    for package in data.get("package", []):
        if not isinstance(package, dict):
            skipped["malformed_entry"] += 1
            continue
        name = package.get("name")
        version = package.get("version")
        source = package.get("source")
        if not isinstance(name, str) or not isinstance(version, str):
            skipped["non_registry"] += 1
            continue
        if not isinstance(source, dict) or not isinstance(source.get("registry"), str):
            skipped["non_registry"] += 1
            continue

        pin = Pin(normalize_package_name(name), version)
        pins[pin.key] = pin

    return Surface(
        path=path.relative_to(root).as_posix(),
        kind="uv-lock",
        pins=tuple(sorted(pins.values())),
        skipped=dict(sorted(skipped.items())),
    )


def discover_surfaces(
    root: Path,
    excluded_directories: Iterable[str] = DEFAULT_EXCLUDED_DIRECTORIES,
) -> list[Surface]:
    """Discover active exact-pin surfaces below *root*."""

    root = root.resolve()
    excluded = set(excluded_directories)
    paths: list[Path] = []

    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in excluded)
        for filename in sorted(files):
            lowered = filename.lower()
            if lowered == "uv.lock" or (lowered.endswith(".txt") and "requirements" in lowered):
                paths.append(Path(current) / filename)

    surfaces = []
    for path in sorted(paths):
        if path.name.lower() == "uv.lock":
            surfaces.append(parse_uv_lock(path, root))
        else:
            surfaces.append(parse_requirements(path, root))
    return surfaces


def unique_pins(surfaces: Iterable[Surface]) -> list[Pin]:
    inventory: dict[tuple[str, str], Pin] = {}
    for surface in surfaces:
        for pin in surface.pins:
            inventory[pin.key] = pin
    return sorted(inventory.values())


def resolve_pip_audit_command(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    candidates = ("pip-audit.exe", "pip-audit") if os.name == "nt" else ("pip-audit",)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("pip-audit was not found on PATH")


def partition_pins(pins: Iterable[Pin]) -> list[list[Pin]]:
    """Split pins into batches with at most one version of each package name."""

    batches: list[list[Pin]] = []
    names_by_batch: list[set[str]] = []
    for pin in sorted(pins):
        normalized = normalize_package_name(pin.name)
        for index, names in enumerate(names_by_batch):
            if normalized not in names:
                batches[index].append(pin)
                names.add(normalized)
                break
        else:
            batches.append([pin])
            names_by_batch.append({normalized})
    return batches


def run_pip_audit(pins: list[Pin], command: str, timeout_seconds: int) -> tuple[dict[str, Any], list[str]]:
    """Audit *pins* in one registry query and return the JSON payload plus errors."""

    if not pins:
        return {"dependencies": [], "fixes": []}, []

    errors: list[str] = []
    combined: dict[str, Any] = {"dependencies": [], "fixes": []}
    batches = partition_pins(pins)
    for batch_number, batch in enumerate(batches, start=1):
        with tempfile.TemporaryDirectory(prefix="scbe-pip-audit-") as temporary_directory:
            requirements = Path(temporary_directory) / "exact-pins.txt"
            requirements.write_text(
                "".join(f"{pin.name}=={pin.version}\n" for pin in batch),
                encoding="utf-8",
            )
            try:
                completed = subprocess.run(
                    [
                        command,
                        "--requirement",
                        str(requirements),
                        "--no-deps",
                        "--disable-pip",
                        "--strict",
                        "--progress-spinner",
                        "off",
                        "--desc",
                        "off",
                        "--aliases",
                        "off",
                        "--format",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                errors.append(f"pip-audit batch {batch_number}/{len(batches)} timed out after {timeout_seconds}s")
                continue
            except OSError as exc:
                errors.append(f"pip-audit batch {batch_number}/{len(batches)} could not start: {exc}")
                continue

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "no diagnostic"
            errors.append(f"pip-audit batch {batch_number}/{len(batches)} returned invalid JSON: {exc}; {detail}")
            continue

        if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
            errors.append(f"pip-audit batch {batch_number}/{len(batches)} JSON lacked a dependencies list")
            continue
        combined["dependencies"].extend(payload["dependencies"])
        if isinstance(payload.get("fixes"), list):
            combined["fixes"].extend(payload["fixes"])
        if completed.returncode not in (0, 1):
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "no diagnostic"
            errors.append(
                f"pip-audit batch {batch_number}/{len(batches)} failed with exit {completed.returncode}: {detail}"
            )

    return combined, errors


def index_audit_payload(
    payload: dict[str, Any],
    expected_pins: Iterable[Pin],
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[str]]:
    findings: dict[tuple[str, str], list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    errors: list[str] = []

    for dependency in payload.get("dependencies", []):
        if not isinstance(dependency, dict):
            errors.append("pip-audit returned a malformed dependency entry")
            continue
        name = dependency.get("name")
        version = dependency.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            errors.append(f"pip-audit skipped an unversioned dependency: {name!r}")
            continue
        key = (normalize_package_name(name), version)
        seen.add(key)
        raw_vulnerabilities = dependency.get("vulns", [])
        if not isinstance(raw_vulnerabilities, list):
            errors.append(f"pip-audit returned malformed vulnerabilities for {name}=={version}")
            continue
        rows = []
        seen_vulnerabilities: set[tuple[str, tuple[str, ...]]] = set()
        for vulnerability in raw_vulnerabilities:
            if not isinstance(vulnerability, dict):
                continue
            vulnerability_id = str(vulnerability.get("id", "unknown"))
            fix_versions = tuple(str(value) for value in vulnerability.get("fix_versions", []))
            fingerprint = (vulnerability_id, fix_versions)
            if fingerprint in seen_vulnerabilities:
                continue
            seen_vulnerabilities.add(fingerprint)
            rows.append(
                {
                    "id": vulnerability_id,
                    "fix_versions": list(fix_versions),
                }
            )
        findings[key] = rows

    missing = sorted(pin for pin in expected_pins if pin.key not in seen)
    for pin in missing:
        errors.append(f"pip-audit did not return {pin.name}=={pin.version}")
    return findings, errors


def build_surface_results(
    surfaces: Iterable[Surface],
    findings: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    results = []
    for surface in surfaces:
        rows = []
        vulnerable_packages = 0
        for pin in surface.pins:
            vulnerabilities = findings.get(pin.key, [])
            if vulnerabilities:
                vulnerable_packages += 1
                rows.append(
                    {
                        "name": pin.name,
                        "version": pin.version,
                        "vulnerabilities": vulnerabilities,
                    }
                )
        results.append(
            {
                "path": surface.path,
                "kind": surface.kind,
                "pin_count": len(surface.pins),
                "skipped": surface.skipped,
                "vulnerable_packages": vulnerable_packages,
                "vulnerabilities": sum(len(row["vulnerabilities"]) for row in rows),
                "findings": rows,
            }
        )
    return results


def markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "## Python dependency audit",
        "",
        "| Surface | Exact pins | Vulnerable packages | Advisories | Skipped | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for surface in report["surfaces"]:
        skipped = sum(surface["skipped"].values())
        status = "clean" if surface["vulnerabilities"] == 0 else "review"
        lines.append(
            f"| `{surface['path']}` | {surface['pin_count']} | {surface['vulnerable_packages']} | "
            f"{surface['vulnerabilities']} | {skipped} | {status} |"
        )
    totals = report["totals"]
    lines.append(
        f"| **Unique total** | **{totals['unique_pins']}** | **{totals['vulnerable_packages']}** | "
        f"**{totals['vulnerabilities']}** | **{totals['skipped_entries']}** | **{report['status']}** |"
    )
    if report["errors"]:
        lines.extend(("", "Scanner errors:", *[f"- {error}" for error in report["errors"]]))
    return "\n".join(lines) + "\n"


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--report", type=Path, help="Write the aggregate JSON report here")
    parser.add_argument("--pip-audit", help="Explicit pip-audit executable")
    parser.add_argument("--timeout", type=int, default=300, help="Audit timeout in seconds")
    parser.add_argument("--list", action="store_true", help="List discovered surfaces without auditing")
    parser.add_argument("--advisory", action="store_true", help="Do not fail solely because vulnerabilities were found")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    surfaces = discover_surfaces(root)

    if args.list:
        for surface in surfaces:
            print(f"{surface.path}\t{surface.kind}\t{len(surface.pins)}")
        return 0

    pins = unique_pins(surfaces)
    errors: list[str] = []
    try:
        command = resolve_pip_audit_command(args.pip_audit)
    except FileNotFoundError as exc:
        command = ""
        errors.append(str(exc))

    payload: dict[str, Any] = {}
    if command:
        payload, audit_errors = run_pip_audit(pins, command, args.timeout)
        errors.extend(audit_errors)

    findings: dict[tuple[str, str], list[dict[str, Any]]] = {}
    if payload:
        findings, index_errors = index_audit_payload(payload, pins)
        errors.extend(index_errors)

    surface_results = build_surface_results(surfaces, findings)
    vulnerable = {key: value for key, value in findings.items() if value}
    totals = {
        "surfaces": len(surface_results),
        "unique_pins": len(pins),
        "vulnerable_packages": len(vulnerable),
        "vulnerabilities": sum(len(value) for value in vulnerable.values()),
        "skipped_entries": sum(sum(surface.skipped.values()) for surface in surfaces),
        "scanner_errors": len(errors),
    }
    status = "error" if errors else ("vulnerable" if vulnerable else "clean")
    report = {
        "schema": "scbe.pip-audit-all.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "totals": totals,
        "surfaces": surface_results,
        "errors": errors,
    }

    summary = markdown_summary(report)
    print(summary, end="")
    if args.report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        write_json_atomic(report_path, report)
        print(f"report: {report_path}")

    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        with Path(github_summary).open("a", encoding="utf-8") as stream:
            stream.write(summary)

    if errors:
        return 2
    if vulnerable and not args.advisory:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
