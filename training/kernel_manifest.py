"""Load and validate the canonical SCBE kernel manifest.

The heavy training tree moved to scbe-training-lab, but CI still needs a small
main-repo manifest for kernel-focused tests and SFT export tooling.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fallback is for minimal environments.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path(__file__).with_name("kernel_manifest.yaml")


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    current_list: list[str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            payload[key] = int(value) if value.isdigit() else value
            current_list = None
        else:
            current_list = []
            payload[key] = current_list
    return payload


def load_manifest(path: str | Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    text = manifest_path.read_text(encoding="utf-8")
    if yaml is not None:
        payload = yaml.safe_load(text)
    else:
        payload = _minimal_yaml_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"kernel manifest must be a mapping: {manifest_path}")
    return payload


def validate_manifest_entries(manifest: dict[str, Any], repo_root: str | Path = REPO_ROOT) -> list[str]:
    root = Path(repo_root)
    missing: list[str] = []
    for rel_path in manifest.get("kernel", []):
        if not isinstance(rel_path, str):
            missing.append(str(rel_path))
            continue
        if not (root / rel_path).exists():
            missing.append(rel_path)
    return missing


def to_summary(manifest: dict[str, Any], path: str | Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    kernel = manifest.get("kernel", [])
    return {
        "version": manifest.get("version"),
        "kernel_file_count": len(kernel) if isinstance(kernel, list) else 0,
        "kernel_manifest_sha": digest,
    }
