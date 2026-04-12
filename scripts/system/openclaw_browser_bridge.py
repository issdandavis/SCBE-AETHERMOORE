from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_GATEWAY_PORT = 18789
DEFAULT_BROWSER_CONTROL_PORT = 18791
DEFAULT_PROFILE = "openclaw"
DEFAULT_TIMEOUT = 20.0


def load_openclaw_config(config_path: str | None = None) -> dict[str, Any]:
    target = Path(config_path) if config_path else Path.home() / ".openclaw" / "openclaw.json"
    return json.loads(target.read_text(encoding="utf-8"))


def resolve_browser_base_url(config: dict[str, Any]) -> str:
    browser = config.get("browser")
    if isinstance(browser, dict):
        base_url = browser.get("controlBaseUrl")
        if isinstance(base_url, str) and base_url.strip():
            return base_url.strip().rstrip("/")

        port = browser.get("controlPort")
        if isinstance(port, int) and port > 0:
            return f"http://127.0.0.1:{port}"

    gateway = config.get("gateway")
    gateway_port = DEFAULT_GATEWAY_PORT
    if isinstance(gateway, dict):
        port = gateway.get("port")
        if isinstance(port, int) and port > 0:
            gateway_port = port

    return f"http://127.0.0.1:{gateway_port + 2}"


def resolve_auth_headers(config: dict[str, Any]) -> dict[str, str]:
    gateway = config.get("gateway")
    auth = gateway.get("auth") if isinstance(gateway, dict) else None
    if not isinstance(auth, dict):
        return {}

    token = auth.get("token")
    if isinstance(token, str) and token.strip():
        return {"Authorization": f"Bearer {token.strip()}"}

    password = auth.get("password")
    if isinstance(password, str) and password.strip():
        return {"x-openclaw-key": password.strip()}

    return {}


def request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    if query:
        items = {key: value for key, value in query.items() if value not in (None, "")}
        if items:
            url = f"{url}?{parse.urlencode(items)}"

    data = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=req_headers, method=method.upper())
    with request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def get_status(
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    profile: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    query = {"profile": profile} if profile else None
    return request_json(base_url, "/", headers=headers, query=query, timeout=timeout)


def start_browser(
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    profile: str = DEFAULT_PROFILE,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    return request_json(
        base_url,
        "/start",
        method="POST",
        headers=headers,
        body={"profile": profile},
        timeout=timeout,
    )


def stop_browser(
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    profile: str = DEFAULT_PROFILE,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    return request_json(
        base_url,
        "/stop",
        method="POST",
        headers=headers,
        body={"profile": profile},
        timeout=timeout,
    )


def ensure_browser_running(
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    profile: str = DEFAULT_PROFILE,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    status = get_status(base_url, headers=headers, profile=profile, timeout=timeout)
    if isinstance(status, dict) and status.get("running") is True:
        return status

    start_browser(base_url, headers=headers, profile=profile, timeout=timeout)
    return get_status(base_url, headers=headers, profile=profile, timeout=timeout)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Direct bridge to the live OpenClaw browser control service.")
    parser.add_argument("action", choices=["status", "profiles", "start", "stop", "tabs", "snapshot", "open"])
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--target-id")
    parser.add_argument("--format", default="ai")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mode")
    parser.add_argument("--url")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--config-path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        config = load_openclaw_config(args.config_path)
        base_url = resolve_browser_base_url(config)
        headers = resolve_auth_headers(config)

        if args.action == "status":
            payload = get_status(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
        elif args.action == "profiles":
            payload = request_json(base_url, "/profiles", headers=headers, timeout=args.timeout)
        elif args.action == "start":
            payload = start_browser(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
        elif args.action == "stop":
            payload = stop_browser(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
        elif args.action == "tabs":
            ensure_browser_running(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
            payload = request_json(
                base_url,
                "/tabs",
                headers=headers,
                query={"profile": args.profile},
                timeout=args.timeout,
            )
        elif args.action == "snapshot":
            ensure_browser_running(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
            payload = request_json(
                base_url,
                "/snapshot",
                headers=headers,
                query={
                    "profile": args.profile,
                    "targetId": args.target_id,
                    "format": args.format,
                    "limit": args.limit,
                    "mode": args.mode,
                },
                timeout=args.timeout,
            )
        else:
            if not args.url:
                raise SystemExit("--url is required for action=open")
            ensure_browser_running(base_url, headers=headers, profile=args.profile, timeout=args.timeout)
            payload = request_json(
                base_url,
                "/tabs/open",
                method="POST",
                headers=headers,
                query={"profile": args.profile},
                body={"url": args.url},
                timeout=args.timeout,
            )

        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    except (FileNotFoundError, json.JSONDecodeError, error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
        message = {"ok": False, "action": args.action, "error": str(exc)}
        json.dump(message, sys.stderr)
        sys.stderr.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
