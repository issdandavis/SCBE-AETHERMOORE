#!/usr/bin/env python3
"""Install the repo-owned OpenClaw SCBE plugin into a local OpenClaw home."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


PLUGIN_ID = "scbe-system-tools"
DEFAULT_TIMEOUT_MS = 120_000


@dataclass
class InstallPlan:
    repo_root: str
    plugin_source: str
    openclaw_home: str
    extension_dir: str
    config_path: str
    backup_path: str
    python_bin: str
    timeout_ms: int
    default_provider: str
    default_local_base_url: str
    method: str


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def plugin_source_from_repo(repo_root: Path) -> Path:
    return repo_root / "extensions" / "openclaw-scbe-system-tools"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_openclaw_config(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    install_path: Path,
    python_bin: str,
    timeout_ms: int,
    default_provider: str,
    default_local_base_url: str,
) -> dict[str, Any]:
    patched = dict(payload)
    plugins = dict(patched.get("plugins") or {})
    plugins["enabled"] = True

    allow = list(plugins.get("allow") or [])
    if PLUGIN_ID not in allow:
        allow.append(PLUGIN_ID)
    plugins["allow"] = allow

    entries = dict(plugins.get("entries") or {})
    plugin_entry = dict(entries.get(PLUGIN_ID) or {})
    plugin_entry["enabled"] = True
    plugin_entry["config"] = {
        **dict(plugin_entry.get("config") or {}),
        "repoRoot": str(repo_root),
        "pythonBin": python_bin,
        "timeoutMs": timeout_ms,
        "defaultProvider": default_provider,
        "defaultLocalBaseUrl": default_local_base_url,
    }
    entries[PLUGIN_ID] = plugin_entry
    plugins["entries"] = entries

    installs = dict(plugins.get("installs") or {})
    installs[PLUGIN_ID] = {
        "installPath": str(install_path),
        "source": "path",
        "spec": str(repo_root / "extensions" / "openclaw-scbe-system-tools"),
    }
    plugins["installs"] = installs

    patched["plugins"] = plugins
    return patched


def build_install_plan(
    repo_root: Path,
    *,
    openclaw_home: Path,
    python_bin: str,
    timeout_ms: int,
    default_provider: str,
    default_local_base_url: str,
    method: str,
) -> InstallPlan:
    return InstallPlan(
        repo_root=str(repo_root),
        plugin_source=str(plugin_source_from_repo(repo_root)),
        openclaw_home=str(openclaw_home),
        extension_dir=str(openclaw_home / "extensions" / PLUGIN_ID),
        config_path=str(openclaw_home / "openclaw.json"),
        backup_path=str(openclaw_home / "openclaw.json.bak.scbe-system-tools"),
        python_bin=python_bin,
        timeout_ms=timeout_ms,
        default_provider=default_provider,
        default_local_base_url=default_local_base_url,
        method=method,
    )


def copy_plugin_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def cli_install_plugin(source: Path) -> None:
    openclaw_bin = (
        shutil.which("openclaw.cmd")
        or shutil.which("openclaw.ps1")
        or shutil.which("openclaw")
        or "openclaw"
    )
    subprocess.run(
        [openclaw_bin, "plugins", "install", str(source)],
        check=True,
        text=True,
        capture_output=True,
    )


def apply_install(plan: InstallPlan) -> dict[str, Any]:
    repo_root = Path(plan.repo_root)
    source = Path(plan.plugin_source)
    destination = Path(plan.extension_dir)
    config_path = Path(plan.config_path)
    backup_path = Path(plan.backup_path)

    if not source.exists():
        raise FileNotFoundError(f"Plugin source does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if plan.method == "copy":
        copy_plugin_tree(source, destination)
    elif plan.method == "cli":
        cli_install_plugin(source)
    else:
        raise ValueError(f"Unsupported install method: {plan.method}")

    current = load_json(config_path)
    if config_path.exists():
        backup_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")

    patched = patch_openclaw_config(
        current,
        repo_root=repo_root,
        install_path=destination,
        python_bin=plan.python_bin,
        timeout_ms=plan.timeout_ms,
        default_provider=plan.default_provider,
        default_local_base_url=plan.default_local_base_url,
    )
    write_json(config_path, patched)

    return {
        "plugin_id": PLUGIN_ID,
        "installed_to": str(destination),
        "config_path": str(config_path),
        "backup_path": str(backup_path) if backup_path.exists() else None,
        "next_steps": [
            "Restart the OpenClaw gateway so the new plugin is discovered.",
            "Run openclaw plugins list to confirm scbe-system-tools is loaded.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the repo-owned SCBE OpenClaw plugin.")
    parser.add_argument("--openclaw-home", default=str(Path.home() / ".openclaw"))
    parser.add_argument("--python-bin", default="python")
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--default-provider", choices=["auto", "local", "hf"], default="hf")
    parser.add_argument("--default-local-base-url", default="http://localhost:1234/v1")
    parser.add_argument("--method", choices=["cli", "copy"], default="copy")
    parser.add_argument("--apply", action="store_true", help="Perform the install. Without this flag the script prints the plan only.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_script()
    plan = build_install_plan(
        repo_root,
        openclaw_home=Path(args.openclaw_home),
        python_bin=args.python_bin,
        timeout_ms=args.timeout_ms,
        default_provider=args.default_provider,
        default_local_base_url=args.default_local_base_url,
        method=args.method,
    )

    if args.apply:
        payload: dict[str, Any] = apply_install(plan)
        payload["plan"] = asdict(plan)
    else:
        payload = {"apply": False, "plan": asdict(plan)}

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
