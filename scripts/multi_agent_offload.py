#!/usr/bin/env python3
"""Deterministic multi-lane file triage, training capture, and verified cloud offload."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = "scripts/multi_agent_offload.json"
DEFAULT_STATE_PATH = "training/ingest/multi_agent_offload_state.json"
DEFAULT_RUN_ROOT = "training/runs/multi_agent_offload"
DEFAULT_LATEST_POINTER = "training/ingest/latest_multi_agent_offload.txt"

DEFAULT_EXCLUDES = [
    ".git/**",
    ".venv/**",
    "node_modules/**",
    "**/__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".ruff_cache/**",
    ".idea/**",
    ".vscode/**",
    "dist/**",
    "build/**",
    "training/runs/**",
    "*.zip",
]

PROVIDER_ENV_KEYS = {
    "openai": ["OPENAI_API_KEY", "OPENAI_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "google": ["GOOGLE_API_KEY", "GOOGLE_AI_API_KEY", "GEMINI_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process files through deterministic AI lanes and ship verified bundles to cloud targets."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config file path (default: {DEFAULT_CONFIG})")
    parser.add_argument(
        "--state-path",
        default=DEFAULT_STATE_PATH,
        help=f"State file path (default: {DEFAULT_STATE_PATH})",
    )
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT, help=f"Run root (default: {DEFAULT_RUN_ROOT})")
    parser.add_argument(
        "--latest-pointer",
        default=DEFAULT_LATEST_POINTER,
        help=f"Latest pointer path (default: {DEFAULT_LATEST_POINTER})",
    )
    parser.add_argument("--source-root", action="append", default=[], help="Override configured source roots.")
    parser.add_argument("--targets", default="", help="Override shipping order as CSV target names.")
    parser.add_argument("--batch-size", type=int, default=0, help="Override configured batch size.")
    parser.add_argument(
        "--batch-delay-seconds",
        type=float,
        default=0.0,
        help="Override pause between batches in seconds.",
    )
    parser.add_argument("--max-files", type=int, default=0, help="Limit the number of files processed.")
    parser.add_argument("--dry-run", action="store_true", help="Do not upload or delete anything.")
    parser.add_argument("--no-process", action="store_true", help="Skip model processing and route only.")
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete sources only after verified delete-safe upload success.",
    )
    parser.add_argument("--reprocess", action="store_true", help="Reprocess files already marked successful.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def parse_csv(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def ensure_list(value: Any, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return list(default)
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned or list(default)


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def md5_file(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def safe_slug(text: str, limit: int = 80) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.replace("\\", "/")).strip("-._")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    if len(cleaned) <= limit:
        return cleaned or "item"
    digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned[: limit - 9]}-{digest}"


def matches_any(path_text: str, patterns: list[str]) -> bool:
    candidate = path_text.replace("\\", "/")
    for pattern in patterns:
        rule = pattern.replace("\\", "/").strip()
        if not rule:
            continue
        if fnmatch.fnmatch(candidate, rule):
            return True
        if rule.startswith("**/") and fnmatch.fnmatch(candidate, rule[3:]):
            return True
        prefix = rule.rstrip("*").rstrip("/")
        if prefix and candidate.startswith(prefix + "/"):
            return True
    return False


def pick_api_key(provider: str, lane: dict[str, Any]) -> tuple[str, str]:
    explicit = lane.get("env_keys", [])
    keys = [str(item).strip() for item in explicit if str(item).strip()] if isinstance(explicit, list) else []
    keys.extend(PROVIDER_ENV_KEYS.get(provider, []))
    seen: set[str] = set()
    for key_name in keys:
        if key_name in seen:
            continue
        seen.add(key_name)
        value = os.getenv(key_name, "").strip()
        if value:
            return key_name, value
    return "", ""


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout or ""


def collect_candidates(
    config: dict[str, Any],
    args: argparse.Namespace,
    state: dict[str, Any],
    routing_signature: str,
) -> list[dict[str, Any]]:
    selection = dict(config.get("selection", {}))
    include_globs = ensure_list(selection.get("include_globs"), ["**/*"])
    exclude_globs = ensure_list(selection.get("exclude_globs"), list(DEFAULT_EXCLUDES))
    max_file_bytes = int(selection.get("max_file_bytes", 512 * 1024 * 1024))
    configured_roots = config.get("source_roots", [])
    root_specs = [{"path": entry} for entry in args.source_root] if args.source_root else configured_roots

    prior_files = state.get("files", {}) if isinstance(state.get("files"), dict) else {}
    candidates: list[dict[str, Any]] = []

    for raw in root_specs:
        path_text = str(raw.get("path", "") if isinstance(raw, dict) else raw).strip()
        if not path_text:
            continue
        root = Path(path_text).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        root_excludes = ensure_list(raw.get("exclude", []), []) if isinstance(raw, dict) else []
        root_includes = ensure_list(raw.get("include", []), ["**/*"]) if isinstance(raw, dict) else ["**/*"]

        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file() or file_path.is_symlink():
                continue
            rel = str(file_path.relative_to(root)).replace("\\", "/")
            if not matches_any(rel, include_globs) or not matches_any(rel, root_includes):
                continue
            if matches_any(rel, exclude_globs) or matches_any(rel, root_excludes):
                continue

            stat = file_path.stat()
            if max_file_bytes > 0 and int(stat.st_size) > max_file_bytes:
                continue

            key = str(file_path.resolve())
            prior = prior_files.get(key, {})
            if (
                not args.reprocess
                and prior.get("status") == "success"
                and prior.get("routing_signature") == routing_signature
                and int(prior.get("size", -1)) == int(stat.st_size)
                and int(prior.get("mtime_ns", -1)) == int(stat.st_mtime_ns)
            ):
                continue

            candidates.append(
                {
                    "source_path": file_path.resolve(),
                    "source_root": root.resolve(),
                    "relative_path": rel,
                    "size": int(stat.st_size),
                    "mtime_ns": int(stat.st_mtime_ns),
                }
            )

    candidates.sort(key=lambda row: (str(row["source_root"]), str(row["relative_path"])))
    if args.max_files > 0:
        candidates = candidates[: args.max_files]
    return candidates


def build_routing_signature(lanes: list[dict[str, Any]]) -> str:
    payload = []
    for lane in lanes:
        payload.append(
            {
                "name": str(lane.get("name", "")),
                "provider": str(lane.get("provider", "")),
                "model": str(lane.get("model", "")),
                "weight": lane.get("weight", 1),
            }
        )
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def choose_lane(file_row: dict[str, Any], lanes: list[dict[str, Any]], salt: str) -> dict[str, Any]:
    weighted: list[tuple[int, dict[str, Any]]] = []
    total_weight = 0
    for lane in lanes:
        if not bool(lane.get("enabled", True)):
            continue
        lane_copy = dict(lane)
        lane_copy["name"] = str(lane_copy.get("name", "")).strip() or str(lane_copy.get("provider", "lane"))
        weight = max(1, int(float(lane_copy.get("weight", 1))))
        weighted.append((weight, lane_copy))
        total_weight += weight
    if not weighted:
        raise RuntimeError("No enabled lanes configured.")

    key = (
        f"{salt}|{file_row['source_root']}|{file_row['relative_path']}|"
        f"{file_row['size']}|{file_row['mtime_ns']}"
    )
    bucket = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16) % total_weight
    cursor = bucket
    for weight, lane in weighted:
        if cursor < weight:
            return lane
        cursor -= weight
    return weighted[-1][1]


def read_snippet(path: Path, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""


def build_processing_prompt(file_row: dict[str, Any], snippet: str) -> str:
    return (
        "You are sorting a file for long-term cloud archival.\n"
        "Return compact JSON with keys: category, summary, cloud_priority, sensitivity, keep_local, notes.\n"
        "Use short strings and booleans only.\n\n"
        f"source_root: {file_row['source_root']}\n"
        f"relative_path: {file_row['relative_path']}\n"
        f"size_bytes: {file_row['size']}\n\n"
        "content_snippet:\n"
        f"{snippet}"
    )


def request_json(
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    data = None
    request_headers = dict(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url=url, headers=request_headers, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def call_openai_like(provider: str, lane: dict[str, Any], prompt: str, api_key: str) -> dict[str, Any]:
    endpoint = str(
        lane.get(
            "endpoint",
            "https://api.x.ai/v1/chat/completions" if provider == "xai" else "https://api.openai.com/v1/chat/completions",
        )
    ).strip()
    payload = {
        "model": str(lane.get("model", "")).strip(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(lane.get("temperature", 0.2)),
        "max_tokens": int(lane.get("max_tokens", 320)),
    }
    response = request_json(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        body=payload,
        timeout=int(lane.get("timeout_sec", 45)),
    )
    text = ""
    choices = response.get("choices", [])
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        text = str(message.get("content", "")).strip()
    return {"text": text, "raw": response}


def call_anthropic(lane: dict[str, Any], prompt: str, api_key: str) -> dict[str, Any]:
    endpoint = str(lane.get("endpoint", "https://api.anthropic.com/v1/messages")).strip()
    payload = {
        "model": str(lane.get("model", "")).strip(),
        "system": "You sort files for safe archival and deletion gating.",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(lane.get("temperature", 0.2)),
        "max_tokens": int(lane.get("max_tokens", 320)),
    }
    response = request_json(
        endpoint,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        body=payload,
        timeout=int(lane.get("timeout_sec", 45)),
    )
    text_parts: list[str] = []
    content = response.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                part = item.get("text")
                if isinstance(part, str) and part.strip():
                    text_parts.append(part.strip())
    return {"text": "\n".join(text_parts).strip(), "raw": response}


def call_google(lane: dict[str, Any], prompt: str, api_key: str) -> dict[str, Any]:
    model = str(lane.get("model", "gemini-2.5-flash")).strip()
    endpoint = (
        str(lane.get("endpoint", "")).strip()
        or f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": float(lane.get("temperature", 0.2)),
            "maxOutputTokens": int(lane.get("max_tokens", 320)),
        },
    }
    response = request_json(endpoint, headers={}, body=payload, timeout=int(lane.get("timeout_sec", 45)))
    text = ""
    candidates = response.get("candidates", [])
    if isinstance(candidates, list) and candidates:
        content = candidates[0].get("content", {}) if isinstance(candidates[0], dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = "\n".join(
            str(part.get("text", "")).strip() for part in parts if isinstance(part, dict) and str(part.get("text", "")).strip()
        ).strip()
    return {"text": text, "raw": response}


def call_huggingface(lane: dict[str, Any], prompt: str, api_key: str) -> dict[str, Any]:
    try:
        from huggingface_hub import InferenceClient
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc
    client = InferenceClient(model=str(lane.get("model", "")).strip(), token=api_key or None)
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=int(lane.get("max_tokens", 320)),
            temperature=float(lane.get("temperature", 0.2)),
        )
        text = ""
        if getattr(response, "choices", None):
            choice = response.choices[0]
            text = str(choice.message.content or "").strip()
        return {"text": text, "raw": {"provider": "huggingface", "mode": "chat_completion"}}
    except Exception:
        text = client.text_generation(prompt=prompt, max_new_tokens=int(lane.get("max_tokens", 320)))
        return {"text": str(text).strip(), "raw": {"provider": "huggingface", "mode": "text_generation"}}


def parse_model_output(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text


def run_lane(lane: dict[str, Any], prompt: str, no_process: bool) -> dict[str, Any]:
    if no_process:
        return {"status": "skipped", "provider": lane.get("provider"), "model": lane.get("model"), "text": ""}

    provider = str(lane.get("provider", "")).strip().lower()
    key_name, api_key = pick_api_key(provider, lane)
    if not api_key:
        return {
            "status": "failed",
            "provider": provider,
            "model": str(lane.get("model", "")),
            "reason": "missing_api_key",
        }

    try:
        if provider in {"openai", "xai"}:
            result = call_openai_like(provider, lane, prompt, api_key)
        elif provider == "anthropic":
            result = call_anthropic(lane, prompt, api_key)
        elif provider == "google":
            result = call_google(lane, prompt, api_key)
        elif provider == "huggingface":
            result = call_huggingface(lane, prompt, api_key)
        else:
            return {"status": "failed", "provider": provider, "reason": "unsupported_provider"}
    except Exception as exc:
        return {
            "status": "failed",
            "provider": provider,
            "model": str(lane.get("model", "")),
            "reason": "provider_error",
            "error": str(exc),
        }

    text = str(result.get("text", "") or "").strip()
    return {
        "status": "ok" if text else "empty_response",
        "provider": provider,
        "model": str(lane.get("model", "")),
        "key_name": key_name,
        "text": text,
        "parsed": parse_model_output(text) if text else "",
        "raw": result.get("raw", {}),
    }


def run_lane_with_fallback(primary_lane: dict[str, Any], all_lanes: list[dict[str, Any]], prompt: str, no_process: bool) -> dict[str, Any]:
    ordered: list[dict[str, Any]] = [dict(primary_lane)]
    primary_name = str(primary_lane.get("name", "")).strip()
    for lane in all_lanes:
        if not isinstance(lane, dict):
            continue
        lane_name = str(lane.get("name", "")).strip() or str(lane.get("provider", "lane"))
        if lane_name == primary_name:
            continue
        ordered.append(dict(lane, name=lane_name))

    attempts: list[dict[str, Any]] = []
    for lane in ordered:
        result = run_lane(lane, prompt, no_process)
        attempts.append(
            {
                "lane": lane.get("name"),
                "provider": result.get("provider", lane.get("provider")),
                "model": result.get("model", lane.get("model")),
                "status": result.get("status"),
                "reason": result.get("reason", ""),
                "error": result.get("error", ""),
            }
        )
        if result.get("status") == "ok" or result.get("status") == "skipped":
            result["attempts"] = attempts
            result["selected_lane"] = lane.get("name")
            return result

    final = attempts[-1] if attempts else {}
    return {
        "status": "failed",
        "provider": final.get("provider", primary_lane.get("provider")),
        "model": final.get("model", primary_lane.get("model")),
        "reason": final.get("reason", "all_lanes_failed"),
        "error": final.get("error", ""),
        "attempts": attempts,
        "selected_lane": primary_name,
    }


def auto_detect_sync_dir(provider: str, explicit: str = "") -> Path | None:
    if explicit.strip():
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return candidate

    env_map = {
        "dropbox": "DROPBOX_SYNC_DIR",
        "gdrive": "GOOGLE_DRIVE_SYNC_DIR",
        "adobe": "ADOBE_CLOUD_SYNC_DIR",
        "proton": "PROTON_DRIVE_SYNC_DIR",
    }
    env_name = env_map.get(provider, "")
    if env_name:
        from_env = os.getenv(env_name, "").strip()
        if from_env:
            candidate = Path(from_env).expanduser()
            if candidate.exists():
                return candidate

    home = Path.home()
    patterns = {
        "dropbox": ["Dropbox", "Dropbox (Personal)", "Dropbox (Business)", "Dropbox*"],
        "gdrive": ["Google Drive", "My Drive", "Drive", "Google Drive*", "My Drive*", "Drive*"],
        "adobe": ["Creative Cloud Files", "Adobe Creative Cloud Files", "Creative Cloud Files*"],
        "proton": ["Proton Drive", "ProtonDrive", "Proton Drive*"],
    }
    for pattern in patterns.get(provider, []):
        for path in home.glob(pattern):
            if path.is_dir():
                return path
    return None


def zip_bundle(bundle_dir: Path, bundle_zip: Path) -> None:
    if bundle_zip.exists():
        bundle_zip.unlink()
    with zipfile.ZipFile(bundle_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(bundle_dir.rglob("*")):
            if file_path.is_file() and file_path != bundle_zip:
                zf.write(file_path, arcname=str(file_path.relative_to(bundle_dir)).replace("\\", "/"))


def verify_local_copy(src: Path, dest: Path) -> bool:
    return src.exists() and dest.exists() and sha256_file(src) == sha256_file(dest)


def rclone_remote_md5(remote_path: str) -> str:
    code, output = run_command(["rclone", "md5sum", remote_path])
    if code != 0:
        raise RuntimeError(output.strip() or f"rclone md5sum failed for {remote_path}")
    for line in output.splitlines():
        parts = line.strip().split()
        if parts and re.fullmatch(r"[0-9a-fA-F]{32}", parts[0]):
            return parts[0].lower()
    raise RuntimeError(f"Could not parse rclone md5sum output for {remote_path}")


def ship_with_rclone(bundle_zip: Path, target_cfg: dict[str, Any], run_id: str, lane_name: str) -> dict[str, Any]:
    remote = str(target_cfg.get("remote", "")).strip().rstrip(":")
    if not remote:
        raise RuntimeError("rclone target missing remote")
    path_prefix = str(target_cfg.get("path_prefix", "SCBE/multi-agent-offload")).strip().strip("/")
    remote_path = f"{remote}:{path_prefix}/{run_id}/{lane_name}/{bundle_zip.name}"
    code, output = run_command(["rclone", "copyto", str(bundle_zip), remote_path])
    if code != 0:
        raise RuntimeError(output.strip() or f"rclone copyto failed for {remote_path}")

    local_md5 = md5_file(bundle_zip)
    remote_md5 = rclone_remote_md5(remote_path)
    verified = bool(local_md5 == remote_md5)
    return {
        "status": "ok" if verified else "failed",
        "target_type": "rclone",
        "remote_path": remote_path,
        "verified": verified,
        "verification": "remote_md5",
        "safe_to_delete": verified,
    }


def ship_with_local_copy(bundle_zip: Path, target_cfg: dict[str, Any], run_id: str, lane_name: str) -> dict[str, Any]:
    provider = str(target_cfg.get("provider", "")).strip().lower()
    base_dir = str(target_cfg.get("base_dir", "")).strip()
    resolved = auto_detect_sync_dir(provider, base_dir) if provider else (Path(base_dir).expanduser() if base_dir else None)
    if resolved is None or not resolved.exists():
        raise RuntimeError(f"Local target directory not found for provider={provider or 'custom'}")

    path_prefix = str(target_cfg.get("path_prefix", "SCBE/multi-agent-offload")).strip().strip("/")
    dest = resolved / path_prefix / run_id / lane_name / bundle_zip.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    shutil.copy2(bundle_zip, dest)
    verified = verify_local_copy(bundle_zip, dest)
    safe_to_delete = bool(target_cfg.get("safe_to_delete", False)) and verified
    return {
        "status": "ok" if verified else "failed",
        "target_type": "local_copy",
        "destination": str(dest),
        "verified": verified,
        "verification": "local_sha256",
        "safe_to_delete": safe_to_delete,
    }


def ship_with_hf(bundle_zip: Path, target_cfg: dict[str, Any], run_id: str, lane_name: str) -> dict[str, Any]:
    repo_id = str(target_cfg.get("repo_id", "")).strip()
    if not repo_id:
        raise RuntimeError("HF target missing repo_id")
    token = (
        os.getenv("HF_TOKEN", "").strip()
        or os.getenv("HUGGINGFACE_TOKEN", "").strip()
        or os.getenv("HUGGING_FACE_HUB_TOKEN", "").strip()
    )
    if not token:
        raise RuntimeError("HF token not found")
    try:
        from huggingface_hub import HfApi
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    prefix = str(target_cfg.get("path_prefix", "multi-agent-offload")).strip().strip("/")
    path_in_repo = f"{prefix}/{run_id}/{lane_name}/{bundle_zip.name}"
    api.upload_file(
        repo_id=repo_id,
        repo_type="dataset",
        path_or_fileobj=str(bundle_zip),
        path_in_repo=path_in_repo,
        token=token,
    )
    return {
        "status": "ok",
        "target_type": "hf",
        "repo_id": repo_id,
        "path_in_repo": path_in_repo,
        "verified": True,
        "verification": "api_ack",
        "safe_to_delete": False,
    }


def publish_run_artifacts_to_hf(run_id: str, run_dir: Path, target_cfg: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    repo_id = str(target_cfg.get("repo_id", "")).strip()
    if not repo_id:
        raise RuntimeError("HF target missing repo_id")
    token = (
        os.getenv("HF_TOKEN", "").strip()
        or os.getenv("HUGGINGFACE_TOKEN", "").strip()
        or os.getenv("HUGGING_FACE_HUB_TOKEN", "").strip()
    )
    if not token:
        raise RuntimeError("HF token not found")
    try:
        from huggingface_hub import HfApi
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    prefix = str(target_cfg.get("path_prefix", "multi-agent-offload")).strip().strip("/")
    uploaded: list[str] = []
    for file_path in files:
        rel = str(file_path.relative_to(run_dir)).replace("\\", "/")
        path_in_repo = f"{prefix}/runs/{run_id}/{rel}"
        api.upload_file(
            repo_id=repo_id,
            repo_type="dataset",
            path_or_fileobj=str(file_path),
            path_in_repo=path_in_repo,
            token=token,
        )
        uploaded.append(path_in_repo)
    return {"status": "ok", "repo_id": repo_id, "uploaded": uploaded}


def detect_github_repo() -> str:
    code, output = run_command(["git", "config", "--get", "remote.origin.url"])
    if code != 0:
        return ""
    raw = output.strip()
    if not raw:
        return ""
    if raw.startswith("git@github.com:"):
        repo = raw.split(":", 1)[1]
    else:
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", raw)
        repo = match.group(1) if match else ""
    return repo[:-4] if repo.endswith(".git") else repo


def gh_command(cmd: list[str], env: dict[str, str]) -> None:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or f"gh command failed: {' '.join(cmd)}")


def ship_with_github(bundle_zip: Path, target_cfg: dict[str, Any], run_id: str) -> dict[str, Any]:
    repo = str(target_cfg.get("repo", "")).strip() or detect_github_repo()
    if not repo:
        raise RuntimeError("GitHub repo not configured and origin remote not detected")
    token = (
        os.getenv("GH_TOKEN", "").strip()
        or os.getenv("GITHUB_TOKEN", "").strip()
        or os.getenv("GITHUB_PAT", "").strip()
    )
    if not token:
        raise RuntimeError("GitHub token not found")

    env = dict(os.environ)
    env["GH_TOKEN"] = token
    tag = f"{str(target_cfg.get('release_prefix', 'multi-agent-offload')).strip()}-{run_id}"
    view = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if view.returncode != 0:
        gh_command(
            ["gh", "release", "create", tag, "--repo", repo, "--title", f"Multi Agent Offload {run_id}", "--notes", "Automated file offload bundle."],
            env,
        )
    gh_command(["gh", "release", "upload", tag, "--repo", repo, "--clobber", str(bundle_zip)], env)
    return {
        "status": "ok",
        "target_type": "github",
        "repo": repo,
        "tag": tag,
        "verified": True,
        "verification": "api_ack",
        "safe_to_delete": False,
    }


def ship_bundle(bundle_zip: Path, shipping_cfg: dict[str, Any], target_name: str, run_id: str, lane_name: str) -> dict[str, Any]:
    targets = shipping_cfg.get("targets", {})
    target_cfg = dict(targets.get(target_name, {})) if isinstance(targets, dict) else {}
    if not target_cfg or not bool(target_cfg.get("enabled", True)):
        return {"status": "skipped", "target": target_name, "reason": "target_disabled"}

    target_type = str(target_cfg.get("type", "")).strip().lower()
    try:
        if target_type == "rclone":
            result = ship_with_rclone(bundle_zip, target_cfg, run_id, lane_name)
        elif target_type == "local_copy":
            result = ship_with_local_copy(bundle_zip, target_cfg, run_id, lane_name)
        elif target_type == "hf":
            result = ship_with_hf(bundle_zip, target_cfg, run_id, lane_name)
        elif target_type == "github":
            result = ship_with_github(bundle_zip, target_cfg, run_id)
        else:
            return {"status": "failed", "target": target_name, "reason": f"unsupported_target_type:{target_type}"}
    except Exception as exc:
        return {"status": "failed", "target": target_name, "reason": str(exc)}

    result["target"] = target_name
    return result


def main() -> int:
    args = parse_args()
    load_env_file(REPO_ROOT / ".env")

    config_path = REPO_ROOT / args.config
    state_path = REPO_ROOT / args.state_path
    run_root = REPO_ROOT / args.run_root
    latest_pointer = REPO_ROOT / args.latest_pointer

    config = read_json(config_path, default={})
    if not isinstance(config, dict):
        raise SystemExit(f"Invalid config: {config_path}")
    lanes = config.get("lanes", [])
    if not isinstance(lanes, list) or not lanes:
        raise SystemExit("No lanes configured.")

    routing_signature = build_routing_signature([lane for lane in lanes if isinstance(lane, dict)])
    state = read_json(state_path, default={})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("files", {})

    candidates = collect_candidates(config, args, state, routing_signature)
    if not candidates:
        print(json.dumps({"status": "no_files", "timestamp_utc": utc_now()}, ensure_ascii=True))
        return 0

    batch_size = int(args.batch_size or config.get("batch_size", 3) or 3)
    batch_delay = float(args.batch_delay_seconds or config.get("batch_delay_seconds", 5.0) or 5.0)
    processing_cfg = dict(config.get("processing", {}))
    snippet_chars = int(processing_cfg.get("snippet_chars", 12000))
    shipping_cfg = dict(config.get("shipping", {}))
    target_order = parse_csv(args.targets) if args.targets else ensure_list(shipping_cfg.get("order"), ["gdrive_rclone"])
    keep_runs = int(dict(config.get("retention", {})).get("keep_runs", 25))

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    bundles_root = run_dir / "bundles"
    bundles_root.mkdir(parents=True, exist_ok=True)
    training_jsonl = run_dir / "training_rows.jsonl"

    lane_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        lane = choose_lane(row, [x for x in lanes if isinstance(x, dict)], routing_signature)
        row["lane"] = lane
        lane_groups[str(lane["name"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    method_counts: dict[str, int] = defaultdict(int)
    required_verified_targets = int(shipping_cfg.get("required_verified_targets", 1))

    for lane_name in sorted(lane_groups.keys()):
        group = lane_groups[lane_name]
        for batch_start in range(0, len(group), batch_size):
            batch = group[batch_start : batch_start + batch_size]
            for file_row in batch:
                source_path = Path(file_row["source_path"])
                rel_slug = safe_slug(file_row["relative_path"])
                lane = dict(file_row["lane"])
                bundle_slug = safe_slug(f"{source_path.name}-{rel_slug}-{file_row['mtime_ns']}")
                bundle_dir = bundles_root / bundle_slug
                bundle_dir.mkdir(parents=True, exist_ok=True)

                payload_dir = bundle_dir / "payload"
                payload_dir.mkdir(parents=True, exist_ok=True)
                payload_copy = payload_dir / source_path.name
                shutil.copy2(source_path, payload_copy)

                source_sha256 = sha256_file(source_path)
                payload_sha256 = sha256_file(payload_copy)
                if source_sha256 != payload_sha256:
                    raise RuntimeError(f"Staging copy integrity mismatch for {source_path}")

                snippet = read_snippet(source_path, snippet_chars)
                prompt = build_processing_prompt(file_row, snippet)
                lane_result = run_lane_with_fallback(lane, [x for x in lanes if isinstance(x, dict)], prompt, args.no_process)

                bundle_meta = {
                    "run_id": run_id,
                    "timestamp_utc": utc_now(),
                    "source_path": str(source_path),
                    "source_root": str(file_row["source_root"]),
                    "relative_path": file_row["relative_path"],
                    "size": int(file_row["size"]),
                    "mtime_ns": int(file_row["mtime_ns"]),
                    "source_sha256": source_sha256,
                    "lane": {
                        "name": lane.get("name"),
                        "provider": lane.get("provider"),
                        "model": lane.get("model"),
                    },
                    "lane_attempts": lane_result.get("attempts", []),
                    "lane_result": {
                        "status": lane_result.get("status"),
                        "selected_lane": lane_result.get("selected_lane", lane.get("name")),
                        "parsed": lane_result.get("parsed", ""),
                        "text": lane_result.get("text", ""),
                    },
                }
                write_json(bundle_dir / "metadata.json", bundle_meta)
                write_json(bundle_dir / "lane_result.json", lane_result)

                training_row = {
                    "instruction": "Classify a file for safe cloud archival and deletion gating.",
                    "input": {
                        "relative_path": file_row["relative_path"],
                        "size": int(file_row["size"]),
                        "snippet": snippet,
                        "assigned_lane": lane.get("name"),
                        "assigned_provider": lane.get("provider"),
                        "assigned_model": lane.get("model"),
                        "selected_lane": lane_result.get("selected_lane", lane.get("name")),
                    },
                    "output": lane_result.get("parsed", lane_result.get("text", "")),
                    "metadata": {
                        "run_id": run_id,
                        "source_sha256": source_sha256,
                        "timestamp_utc": utc_now(),
                    },
                }
                append_jsonl(training_jsonl, training_row)
                write_json(bundle_dir / "training_record.json", training_row)

                bundle_zip = bundle_dir / f"{bundle_slug}.zip"
                zip_bundle(bundle_dir, bundle_zip)
                bundle_sha256 = sha256_file(bundle_zip)
                effective_lane_name = str(lane_result.get("selected_lane", lane_name))

                shipping_results: list[dict[str, Any]] = []
                verified_targets = 0
                shipped = False

                for target_name in target_order:
                    if args.dry_run:
                        result = {
                            "status": "dry_run",
                            "target": target_name,
                            "verified": False,
                            "safe_to_delete": False,
                        }
                    else:
                        result = ship_bundle(bundle_zip, shipping_cfg, target_name, run_id, effective_lane_name)
                    shipping_results.append(result)
                    method_counts[f"lane:{lane_name}"] += 1
                    method_counts[f"target:{target_name}:{result.get('status')}"] += 1
                    if result.get("status") == "ok":
                        shipped = True
                    if result.get("status") == "ok" and result.get("verified") and result.get("safe_to_delete"):
                        verified_targets += 1

                deleted = False
                if args.delete_source and not args.dry_run and verified_targets >= required_verified_targets:
                    source_path.unlink()
                    deleted = True

                row_summary = {
                    "source_path": str(source_path),
                    "relative_path": file_row["relative_path"],
                    "lane": lane_name,
                    "provider": lane.get("provider"),
                    "model": lane.get("model"),
                    "bundle_zip": str(bundle_zip),
                    "bundle_sha256": bundle_sha256,
                    "lane_status": lane_result.get("status"),
                    "selected_lane": lane_result.get("selected_lane", lane.get("name")),
                    "lane_attempts": lane_result.get("attempts", []),
                    "shipping": shipping_results,
                    "verified_target_count": verified_targets,
                    "required_verified_targets": required_verified_targets,
                    "status": "success" if shipped else ("dry_run" if args.dry_run else "failed"),
                    "deleted": deleted,
                }
                summary_rows.append(row_summary)

                state["files"][str(source_path)] = {
                    "status": row_summary["status"],
                    "deleted": deleted,
                    "size": int(file_row["size"]),
                    "mtime_ns": int(file_row["mtime_ns"]),
                    "routing_signature": routing_signature,
                    "lane": lane_name,
                    "provider": lane.get("provider"),
                    "model": lane.get("model"),
                    "bundle_sha256": bundle_sha256,
                    "run_id": run_id,
                    "updated_at_utc": utc_now(),
                }

            if batch_delay > 0 and batch_start + batch_size < len(group):
                time.sleep(batch_delay)

    write_json(run_dir / "file_results.json", {"results": summary_rows})
    write_json(
        run_dir / "method_registry.json",
        {
            "run_id": run_id,
            "timestamp_utc": utc_now(),
            "required_verified_targets": required_verified_targets,
            "working_methods": {key: value for key, value in sorted(method_counts.items()) if value > 0},
        },
    )

    success_count = sum(1 for row in summary_rows if row["status"] == "success")
    failed_count = sum(1 for row in summary_rows if row["status"] == "failed")
    deleted_count = sum(1 for row in summary_rows if row["deleted"])
    summary = {
        "run_id": run_id,
        "timestamp_utc": utc_now(),
        "routing_signature": routing_signature,
        "file_count": len(summary_rows),
        "success_count": success_count,
        "failed_count": failed_count,
        "deleted_count": deleted_count,
        "dry_run": bool(args.dry_run),
        "no_process": bool(args.no_process),
        "required_verified_targets": required_verified_targets,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "training_rows": str(training_jsonl.relative_to(REPO_ROOT)).replace("\\", "/"),
        "targets": target_order,
    }
    write_json(run_dir / "run_summary.json", summary)

    hf_publish_result: dict[str, Any] | None = None
    hf_target_cfg = dict(shipping_cfg.get("targets", {}).get("hf_dataset", {})) if isinstance(shipping_cfg.get("targets"), dict) else {}
    if hf_target_cfg and bool(hf_target_cfg.get("enabled")) and not args.dry_run:
        try:
            hf_publish_result = publish_run_artifacts_to_hf(
                run_id,
                run_dir,
                hf_target_cfg,
                [
                    training_jsonl,
                    run_dir / "file_results.json",
                    run_dir / "method_registry.json",
                    run_dir / "run_summary.json",
                ],
            )
        except Exception as exc:
            hf_publish_result = {"status": "failed", "reason": str(exc)}
        summary["hf_run_artifacts"] = hf_publish_result
        write_json(run_dir / "run_summary.json", summary)

    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(str(run_dir.resolve()) + "\n", encoding="utf-8")
    write_json(state_path, state)

    if keep_runs > 0:
        runs = sorted([p for p in run_root.iterdir() if p.is_dir()], key=lambda p: p.name)
        stale = runs[: max(0, len(runs) - keep_runs)]
        for old in stale:
            shutil.rmtree(old, ignore_errors=True)

    print(json.dumps(summary, ensure_ascii=True))
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
