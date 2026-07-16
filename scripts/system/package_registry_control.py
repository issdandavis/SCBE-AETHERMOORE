#!/usr/bin/env python3
"""Controlled package registry inventory for the SCBE project graph.

This tool is intentionally read-only. It compares local npm/PyPI manifests to
public registry metadata and writes a release-control ledger. It never builds,
bumps, uploads, or publishes packages.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "package_registry_control" / "latest"
DEFAULT_PROFILE_ROSTER = Path(r"C:\Users\issda\SCBE_LOCAL_REPO_ROSTER.csv")


@dataclass
class LocalPackage:
    repo: str
    path: str
    manager: str
    manifest: str
    name: str
    version: str
    private: bool
    repository: str | None


@dataclass
class RegistryStatus:
    manager: str
    name: str
    status: str
    version: str | None = None
    latest: str | None = None
    modified: str | None = None
    url: str | None = None
    error: str | None = None


@dataclass
class PackageFinding:
    local: LocalPackage
    registry: RegistryStatus
    release_state: str
    blockers: list[str]
    next_commands: list[str]


def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    resolved = list(cmd)
    executable = shutil.which(resolved[0])
    if executable:
        resolved[0] = executable
    return subprocess.run(resolved, cwd=str(cwd), text=True, capture_output=True, timeout=timeout, check=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_package_json(repo: str, root: Path) -> LocalPackage | None:
    path = root / "package.json"
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    name = str(data.get("name") or "").strip()
    version = str(data.get("version") or "").strip()
    if not name or not version:
        return None
    repository = data.get("repository")
    repo_url = repository.get("url") if isinstance(repository, dict) else None
    return LocalPackage(
        repo=repo,
        path=str(root),
        manager="npm",
        manifest=str(path),
        name=name,
        version=version,
        private=bool(data.get("private", False)),
        repository=repo_url,
    )


def parse_pyproject(repo: str, root: Path) -> LocalPackage | None:
    path = root / "pyproject.toml"
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return None
    project = data.get("project") or {}
    if not isinstance(project, dict):
        return None
    name = str(project.get("name") or "").strip()
    version = str(project.get("version") or "").strip()
    if not name or not version:
        return None
    urls = project.get("urls") or {}
    repo_url = urls.get("Repository") if isinstance(urls, dict) else None
    return LocalPackage(
        repo=repo,
        path=str(root),
        manager="pypi",
        manifest=str(path),
        name=name,
        version=version,
        private=False,
        repository=repo_url,
    )


def read_roster(path: Path) -> list[tuple[str, Path]]:
    if not path.exists():
        return []
    rows: list[tuple[str, Path]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_path = (row.get("Path") or "").strip()
            name = (row.get("Name") or Path(raw_path).name).strip()
            if raw_path:
                rows.append((name, Path(raw_path)))
    return rows


def local_packages(include_roster: bool, roster_path: Path) -> list[LocalPackage]:
    roots: list[tuple[str, Path]] = [("SCBE-AETHERMOORE", ROOT)]
    if include_roster:
        roots.extend(read_roster(roster_path))

    seen: set[tuple[str, str]] = set()
    packages: list[LocalPackage] = []
    for repo, root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for parser in (parse_package_json, parse_pyproject):
            package = parser(repo, root)
            if not package:
                continue
            key = (package.manager, package.manifest)
            if key in seen:
                continue
            seen.add(key)
            packages.append(package)
    return sorted(packages, key=lambda item: (item.manager, item.name, item.path))


def npm_auth_status() -> dict[str, Any]:
    proc = run(["npm", "whoami"], timeout=20)
    return {
        "ok": proc.returncode == 0,
        "whoami": proc.stdout.strip() if proc.returncode == 0 else None,
        "error": (proc.stderr or proc.stdout).strip() if proc.returncode != 0 else None,
    }


def npm_view(name: str) -> RegistryStatus:
    proc = run(
        ["npm", "view", name, "name", "version", "dist-tags.latest", "time.modified", "repository.url", "license", "--json"],
        timeout=30,
    )
    if proc.returncode != 0:
        text = (proc.stderr or proc.stdout).strip()
        status = "not_found" if "E404" in text or "Not Found" in text else "error"
        return RegistryStatus(manager="npm", name=name, status=status, error=text[:1000])
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return RegistryStatus(manager="npm", name=name, status="error", error=str(exc))
    return RegistryStatus(
        manager="npm",
        name=name,
        status="found",
        version=data.get("version"),
        latest=data.get("dist-tags.latest"),
        modified=data.get("time.modified"),
        url=data.get("repository.url"),
    )


def pypi_view(name: str) -> RegistryStatus:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        status = "not_found" if exc.code == 404 else "error"
        return RegistryStatus(manager="pypi", name=name, status=status, error=f"HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return RegistryStatus(manager="pypi", name=name, status="error", error=str(exc))
    info = data.get("info") or {}
    return RegistryStatus(
        manager="pypi",
        name=name,
        status="found",
        version=info.get("version"),
        latest=info.get("version"),
        modified=None,
        url=info.get("package_url") or info.get("project_url") or url,
    )


def version_tuple(version: str | None) -> tuple[int, ...] | None:
    if not version:
        return None
    parts: list[int] = []
    for chunk in version.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            break
    return tuple(parts) if parts else None


def compare_versions(local: str, remote: str | None) -> str:
    local_v = version_tuple(local)
    remote_v = version_tuple(remote)
    if remote_v is None:
        return "unpublished"
    if local_v is None:
        return "unknown"
    if local_v > remote_v:
        return "local_ahead"
    if local_v == remote_v:
        return "in_sync"
    return "local_behind"


def next_commands(package: LocalPackage, release_state: str) -> list[str]:
    if package.private:
        return []
    if package.name != "scbe-aethermoore":
        return []
    if release_state not in {"local_ahead", "in_sync"}:
        return []
    if package.manager == "npm":
        return [
            "npm run publish:check:strict",
            "npm run publish:smoke:consumer",
            "npm publish --dry-run",
            "npm publish",
        ]
    return [
        "npm run publish:pypi:build",
        "npm run publish:pypi:check",
        "python -m twine check artifacts/pypi-dist/*",
        "python -m twine upload artifacts/pypi-dist/*",
    ]


def build_findings(packages: list[LocalPackage], auth: dict[str, Any]) -> list[PackageFinding]:
    duplicate_keys: dict[tuple[str, str], list[LocalPackage]] = {}
    for package in packages:
        duplicate_keys.setdefault((package.manager, package.name), []).append(package)

    findings: list[PackageFinding] = []
    registry_cache: dict[tuple[str, str], RegistryStatus] = {}
    for package in packages:
        if package.manager == "npm":
            registry = registry_cache.setdefault(("npm", package.name), npm_view(package.name))
        else:
            registry = registry_cache.setdefault(("pypi", package.name), pypi_view(package.name))

        release_state = compare_versions(package.version, registry.version if registry.status == "found" else None)
        if registry.status == "not_found":
            release_state = "unpublished"
        elif registry.status == "error":
            release_state = "registry_error"

        blockers: list[str] = []
        if package.private:
            blockers.append("local package.json marks package private")
        if package.manager == "npm" and not auth.get("ok"):
            blockers.append("npm auth is not usable locally; run npm login before publish")
        siblings = duplicate_keys.get((package.manager, package.name), [])
        if len(siblings) > 1:
            canonical = str(ROOT)
            if Path(package.path).resolve() != ROOT.resolve():
                blockers.append(f"duplicate local package name; publish only from canonical root {canonical}")
        if release_state == "local_behind":
            blockers.append("local version is behind registry version")
        if registry.status == "error":
            blockers.append("registry metadata query failed")

        findings.append(
            PackageFinding(
                local=package,
                registry=registry,
                release_state=release_state,
                blockers=blockers,
                next_commands=next_commands(package, release_state),
            )
        )
    return findings


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append("# SCBE Package Registry Control Ledger")
    lines.append("")
    lines.append(f"Generated: {payload['generated_at']}")
    lines.append("")
    lines.append("## Registry Auth")
    lines.append("")
    auth = payload["npm_auth"]
    lines.append(f"- npm auth ok: `{auth['ok']}`")
    if auth.get("whoami"):
        lines.append(f"- npm user: `{auth['whoami']}`")
    if auth.get("error"):
        lines.append(f"- npm auth error: `{auth['error']}`")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for item in payload["findings"]:
        local = item["local"]
        registry = item["registry"]
        lines.append(f"### {local['manager']} `{local['name']}` from `{local['repo']}`")
        lines.append("")
        lines.append(f"- local: `{local['version']}` at `{local['path']}`")
        lines.append(f"- registry status: `{registry['status']}`")
        if registry.get("version"):
            lines.append(f"- registry version: `{registry['version']}`")
        if registry.get("url"):
            lines.append(f"- registry URL: {registry['url']}")
        lines.append(f"- release state: `{item['release_state']}`")
        if item["blockers"]:
            lines.append("- blockers:")
            for blocker in item["blockers"]:
                lines.append(f"  - {blocker}")
        else:
            lines.append("- blockers: none found by this read-only inventory")
        if item["next_commands"]:
            lines.append("- next allowed commands:")
            for command in item["next_commands"]:
                lines.append(f"  - `{command}`")
        lines.append("")
    lines.append("## Controlled Release Rule")
    lines.append("")
    lines.append("Publish only from `C:\\Users\\issda\\SCBE-AETHERMOORE`, never from audit or worktree mirrors.")
    lines.append("Run guards first, inspect their artifacts, then publish one registry at a time.")
    lines.append("This ledger is read-only and does not prove package contents are safe; it only tells us what to check next.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only npm/PyPI registry control ledger.")
    parser.add_argument("--include-roster", action="store_true", help="Include shallow local git repo roster packages.")
    parser.add_argument("--roster", type=Path, default=DEFAULT_PROFILE_ROSTER, help="CSV created by SCBE repo inventory.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for ledger artifacts.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary.")
    args = parser.parse_args(argv)

    packages = local_packages(include_roster=args.include_roster, roster_path=args.roster)
    auth = npm_auth_status()
    findings = build_findings(packages, auth)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "scbe_package_registry_control_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "npm_auth": auth,
        "findings": [asdict(finding) for finding in findings],
    }
    json_path = out_dir / "package_registry_control.json"
    md_path = out_dir / "package_registry_control.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(payload, md_path)

    summary = {
        "ok": True,
        "packages": len(findings),
        "local_ahead": sum(1 for f in findings if f.release_state == "local_ahead"),
        "in_sync": sum(1 for f in findings if f.release_state == "in_sync"),
        "unpublished": sum(1 for f in findings if f.release_state == "unpublished"),
        "blocked": sum(1 for f in findings if f.blockers),
        "npm_auth_ok": bool(auth.get("ok")),
        "json": str(json_path),
        "markdown": str(md_path),
    }
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"[package-registry-control] wrote {json_path}")
        print(f"[package-registry-control] wrote {md_path}")
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
