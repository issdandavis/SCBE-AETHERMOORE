#!/usr/bin/env python3
"""Utility for managing Colab local backend details for SCBE n8n bridge workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit, urlunsplit
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent
for _ in range(6):
    if (REPO_ROOT / "pyproject.toml").exists():
        break
    REPO_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.security.secret_store import get_secret, has_secret, set_secret  # noqa: E402
except Exception as exc:
    raise SystemExit(f"failed to import src.security.secret_store: {exc}")


CONFIG_PATH = Path.home() / ".scbe" / "colab_n8n_bridge.json"


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
        token = "".join(parse_qs(parts.query).get("token", [""])).strip()
    if not token:
        raise ValueError("token required (use ?token= in backend URL or --token)")
    return cleaned, token


def build_api_url(base: str, token: str) -> str:
    return f"{base.rstrip('/')}/api?token={token}"


def probe_backend(base: str, token: str) -> Dict:
    req = Request(build_api_url(base, token))
    try:
        with urlopen(req, timeout=8) as response:
            status = getattr(response, "status", response.getcode())
            _ = response.read(160)
            return {"ok": True, "status": status, "api_root": f"{base.rstrip('/')}/api"}
    except HTTPError as err:
        return {"ok": False, "status": err.code, "error": "backend_http_error"}
    except URLError:
        return {"ok": False, "status": 0, "error": "backend_network_error"}


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


def sanitize_profile(name: str) -> str:
    safe = "".join(ch for ch in name.strip().lower().replace(" ", "_") if ch.isalnum() or ch in "-_")
    if not safe:
        safe = "default"
    return safe


def secret_names(profile: str) -> Tuple[str, str]:
    tag = profile.upper().replace("-", "_")
    return f"SCBE_COLAB_BACKEND_URL_{tag}", f"SCBE_COLAB_TOKEN_{tag}"


def _python_secret_resolver(secret_name: str) -> str:
    repo_root = str(REPO_ROOT)
    return (
        "& python -c 'import sys; "
        f'sys.path.insert(0, r\"{repo_root}\"); '
        "from src.security.secret_store import get_secret; "
        f'print(get_secret(\"{secret_name}\", \"\"))' + "'"
    )


def _public_probe_result(result: Dict) -> Dict:
    payload = {
        "ok": bool(result.get("ok")),
        "status": int(result.get("status", 0) or 0),
    }
    if result.get("api_root"):
        payload["api_root"] = str(result["api_root"])
    if result.get("error"):
        payload["error"] = str(result["error"])
    return payload


def set_profile(args: argparse.Namespace) -> int:
    profile = sanitize_profile(args.name)
    token_override = args.token or os.environ.get(args.token_env, "").strip()
    base, token = parse_backend(args.backend_url, token_override)

    if args.probe:
        probe = probe_backend(base, token)
        if not probe.get("ok"):
            print(json.dumps({"error": "probe_failed", "details": probe}, indent=2))
            return 2

    backend_secret, token_secret = secret_names(profile)
    set_secret(backend_secret, base, note=f"colab-bridge:{profile}", tongue="KO")
    set_secret(token_secret, token, note=f"colab-bridge:{profile}", tongue="KO")

    store = load_store()
    profiles = store.setdefault("profiles", {})
    prior = profiles.get(profile, {})
    profiles[profile] = {
        "backend_url": base,
        "backend_secret_name": backend_secret,
        "token_secret_name": token_secret,
        "n8n_webhook": args.n8n_webhook or prior.get("n8n_webhook", ""),
    }
    save_store(store)
    print(
        json.dumps(
            {
                "status": "saved",
                "name": profile,
                "backend_url": base,
                "token_hint": mask(token),
            },
            indent=2,
        )
    )
    return 0


def status_profile(args: argparse.Namespace) -> int:
    profile = sanitize_profile(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(json.dumps({"error": "profile_not_found", "name": profile}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "name": profile,
                "backend_secret_name": record.get("backend_secret_name"),
                "backend_configured": has_secret(str(record.get("backend_secret_name", ""))),
                "token_secret_name": record.get("token_secret_name"),
                "token_configured": has_secret(str(record.get("token_secret_name", ""))),
                "n8n_webhook": record.get("n8n_webhook"),
                "config_path": str(CONFIG_PATH),
            },
            indent=2,
        )
    )
    return 0


def env_profile(args: argparse.Namespace) -> int:
    profile = sanitize_profile(args.name)
    store = load_store()
    record = store.get("profiles", {}).get(profile)
    if not record:
        print(f"# profile_not_found: {profile}")
        return 1

    backend_secret_name = str(record.get("backend_secret_name", ""))
    token_secret_name = str(record.get("token_secret_name", ""))
    if not backend_secret_name or not token_secret_name:
        print(f"# missing_secret_for_profile: {profile}")
        return 1
    if not has_secret(backend_secret_name) or not has_secret(token_secret_name):
        print(f"# missing_secret_for_profile: {profile}")
        return 1

    payload = {
        "name": profile,
        "backend_secret_name": backend_secret_name,
        "token_secret_name": token_secret_name,
        "n8n_webhook": record.get("n8n_webhook"),
        "resolution": "Resolve secrets locally via src.security.secret_store.get_secret before exporting env.",
    }
    print(json.dumps(payload, indent=2))
    return 0


def probe_profile(args: argparse.Namespace) -> int:
    profile = sanitize_profile(args.name)
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
    print(json.dumps(_public_probe_result(result), indent=2))
    return 0 if result.get("ok") else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Store and validate Colab local connection for n8n bridge use")
    parser.add_argument("--name", default="default", help="Profile name")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--set", action="store_true", help="Create/update profile")
    actions.add_argument("--status", action="store_true", help="Print profile status")
    actions.add_argument("--env", action="store_true", help="Emit shell env exports")
    actions.add_argument("--probe", action="store_true", help="Probe backend API endpoint")

    parser.add_argument("--backend-url", help="Colab local backend URL including token")
    parser.add_argument("--token", default="", help="Colab token (alternative to ?token= in backend URL)")
    parser.add_argument("--token-env", default="", help="Environment variable containing the Colab token")
    parser.add_argument("--n8n-webhook", default="", help="Optional n8n webhook URL")
    parser.add_argument("--check", action="store_true", help="Alias for --probe with --set")

    args = parser.parse_args()
    if args.set and not (args.backend_url or args.token or args.token_env):
        parser.error("--backend-url plus ?token=..., --token, or --token-env is required for --set")

    if args.check:
        args.probe = True

    if args.set:
        return set_profile(args)
    if args.status:
        return status_profile(args)
    if args.env:
        return env_profile(args)
    if args.probe:
        return probe_profile(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
