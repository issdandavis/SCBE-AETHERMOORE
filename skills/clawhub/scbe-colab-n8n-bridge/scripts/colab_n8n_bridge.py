#!/usr/bin/env python3
"""Colab local-connection bridge with SCBE Sacred Tongue secret storage."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import sys


REPO_ROOT = Path(__file__).resolve().parent
for _ in range(6):
    if (REPO_ROOT / "pyproject.toml").exists():
        break
    REPO_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.security.secret_store import get_secret, set_secret  # noqa: E402
except Exception as exc:
    raise SystemExit(f"failed to import src.security.secret_store: {exc}")


CONFIG_PATH = Path.home() / ".scbe" / "colab_n8n_bridge.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_backend(url: str, token_override: str = "") -> Tuple[str, str]:
    if not url:
        raise ValueError("backend URL required")
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        raise ValueError("Backend URL must include scheme and host: e.g. http://127.0.0.1:8888/?token=...")
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path or "", "", ""))
    cleaned = cleaned.rstrip("/")

    token = (token_override or "").strip()
    if not token:
        query = parse_qs(parts.query)
        token = "".join(query.get("token", [""])).strip()
    if not token:
        raise ValueError("token required (use ?token= in backend URL or --token)")

    return cleaned, token


def build_api_url(base: str, token: str, path: str = "/api") -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}?token={token}"


def probe_backend(base: str, token: str) -> Dict:
    url = build_api_url(base, token, "/api")
    req = Request(url)
    try:
        with urlopen(req, timeout=8) as response:
            status = getattr(response, "status", response.getcode())
            preview = response.read(128).decode("utf-8", errors="ignore")
            return {"ok": True, "status": status, "url": url, "preview": preview[:120]}
    except HTTPError as err:
        return {"ok": False, "status": err.code, "error": str(err), "url": url}
    except URLError as err:
        return {"ok": False, "status": 0, "error": str(err), "url": url}


def load_store() -> Dict:
    if not CONFIG_PATH.exists():
        return {"profiles": {}}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or "profiles" not in payload:
        return {"profiles": {}}
    return payload


def save_store(payload: Dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def _sanitize_profile_name(name: str) -> str:
    safe = "".join(ch for ch in name.strip().lower().replace(" ", "_") if ch.isalnum() or ch in "-_")
    if not safe:
        safe = "default"
    return safe


def _secret_names(profile: str) -> Tuple[str, str]:
    tag = profile.upper().replace("-", "_")
    return f"SCBE_COLAB_BACKEND_URL_{tag}", f"SCBE_COLAB_TOKEN_{tag}"


def cmd_set(args: argparse.Namespace) -> int:
    profile = _sanitize_profile_name(args.name)
    backend_url, token = parse_backend(args.backend_url, args.token)
    if args.check:
        check = probe_backend(backend_url, token)
        if not check["ok"]:
            print(json.dumps({"error": "probe_failed", "details": check}, indent=2))
            return 2

    backend_secret_name, token_secret_name = _secret_names(profile)
    set_secret(backend_secret_name, backend_url, tongue="ko")
    set_secret(token_secret_name, token, tongue="ko")

    store = load_store()
    profiles = store.setdefault("profiles", {})
    prior = profiles.get(profile, {})
    record = {
        "backend_url": backend_url,
        "backend_secret_name": backend_secret_name,
        "token_secret_name": token_secret_name,
        "n8n_webhook": args.n8n_webhook or prior.get("n8n_webhook", ""),
        "updated_at": now_iso(),
        "created_at": prior.get("created_at", now_iso()),
    }
    if prior and not args.n8n_webhook:
        record["n8n_webhook"] = prior.get("n8n_webhook", "")
    profiles[profile] = record
    save_store(store)

    print(
        json.dumps(
            {
                "status": "saved",
                "name": profile,
                "backend_url": backend_url,
                "token_hint": mask(token),
            },
            indent=2,
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    profile = _sanitize_profile_name(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(json.dumps({"error": "profile_not_found", "name": profile}, indent=2))
        return 1

    backend = get_secret(str(record.get("backend_secret_name", "")), "")
    token = get_secret(str(record.get("token_secret_name", "")), "")
    print(
        json.dumps(
            {
                "name": profile,
                "backend_url": backend or record.get("backend_url"),
                "backend_secret_name": record.get("backend_secret_name"),
                "token_hint": mask(token),
                "n8n_webhook": record.get("n8n_webhook"),
                "config_path": str(CONFIG_PATH),
            },
            indent=2,
        )
    )
    return 0


def cmd_env(args: argparse.Namespace) -> int:
    profile = _sanitize_profile_name(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(f"# profile_not_found: {profile}")
        return 1

    backend = get_secret(str(record.get("backend_secret_name", "")), "")
    token = get_secret(str(record.get("token_secret_name", "")), "")
    if not backend or not token:
        print(f"# missing_secret_for_profile: {profile}")
        return 1

    shell = args.shell.lower()
    if shell == "bash":
        print(f'export SCBE_COLAB_BACKEND_URL="{backend}"')
        print(f'export SCBE_COLAB_TOKEN="{token}"')
        if record.get("n8n_webhook"):
            print(f'export N8N_WEBHOOK_URL="{record.get("n8n_webhook")}"')
    elif shell == "json":
        print(
            json.dumps(
                {
                    "SCBE_COLAB_BACKEND_URL": backend,
                    "SCBE_COLAB_TOKEN": token,
                    "N8N_WEBHOOK_URL": record.get("n8n_webhook") or "",
                },
                indent=2,
            )
        )
    else:
        # default powershell
        print(f'$env:SCBE_COLAB_BACKEND_URL = "{backend}"')
        print(f'$env:SCBE_COLAB_TOKEN = "{token}"')
        if record.get("n8n_webhook"):
            print(f'$env:N8N_WEBHOOK_URL = "{record.get("n8n_webhook")}"')
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    profile = _sanitize_profile_name(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(json.dumps({"error": "profile_not_found", "name": profile}, indent=2))
        return 1

    backend = get_secret(str(record.get("backend_secret_name", "")), "")
    token = get_secret(str(record.get("token_secret_name", "")), "")
    if not backend or not token:
        print(json.dumps({"error": "secrets_missing", "name": profile}, indent=2))
        return 1

    result = probe_backend(backend, token)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


def cmd_workflow(args: argparse.Namespace) -> int:
    profile = _sanitize_profile_name(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(json.dumps({"error": "profile_not_found", "name": profile}, indent=2))
        return 1

    backend = get_secret(str(record.get("backend_secret_name", "")), "")
    token = get_secret(str(record.get("token_secret_name", "")), "")
    payload = {
        "profile": profile,
        "backend_url": backend,
        "n8n_webhook": record.get("n8n_webhook", ""),
        "timestamp": now_iso(),
    }
    if args.reveal_token:
        payload["token"] = token
    else:
        payload["token_hint"] = mask(token)
    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return 0
    print(payload)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Colab local connection profiles for n8n workflows")
    parser.add_argument("--name", default="default", help="Profile name")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--set", action="store_true", help="Create or update a profile")
    actions.add_argument("--status", action="store_true", help="Show profile status")
    actions.add_argument("--env", action="store_true", help="Print shell exports from secrets")
    actions.add_argument("--probe", action="store_true", help="Probe /api for profile")
    actions.add_argument("--workflow", action="store_true", help="Emit n8n payload")

    parser.add_argument("--backend-url", default="", help="Colab local backend URL")
    parser.add_argument("--token", default="", help="Colab token (optional if provided in --backend-url)")
    parser.add_argument("--n8n-webhook", default="", help="n8n webhook URL")
    parser.add_argument("--check", action="store_true", help="Probe backend API when set")
    parser.add_argument("--shell", default="pwsh", choices=["pwsh", "bash", "json"], help="env output format")
    parser.add_argument("--format", default="json", choices=["json", "text"], help="workflow output format")
    parser.add_argument("--reveal-token", action="store_true", help="Include full token in workflow output")

    args = parser.parse_args()

    if args.set and not args.backend_url:
        parser.error("--backend-url required for --set")

    if args.set:
        return cmd_set(args)
    if args.status:
        return cmd_status(args)
    if args.env:
        return cmd_env(args)
    if args.probe:
        return cmd_probe(args)
    if args.workflow:
        return cmd_workflow(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
