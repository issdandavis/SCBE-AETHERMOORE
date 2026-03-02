#!/usr/bin/env python3
"""
Browser-as-a-Service smoke client for SCBE AetherBrowse.

This helper hits the BaaS endpoints with a minimal flow:
  1) create session
  2) health / usage checks
  3) navigate to a URL
  4) screenshot + snapshot/perception

Use this to validate a fresh BaaS deployment quickly without manual UI work.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _api_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def _parse_session_id(payload: object) -> str | None:
    if isinstance(payload, dict):
        if isinstance(payload.get("session_id"), str):
            return payload["session_id"]
        if isinstance(payload.get("sessionId"), str):
            return payload["sessionId"]
        if isinstance(payload.get("id"), str):
            return payload["id"]
        data = payload.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("session_id"), str):
                return data["session_id"]
            if isinstance(data.get("sessionId"), str):
                return data["sessionId"]
            if isinstance(data.get("id"), str):
                return data["id"]
    return None


def request(
    base_url: str,
    method: str,
    path: str,
    api_key: str,
    payload: dict | None = None,
    timeout: float = 8.0,
) -> tuple[int, object]:
    body = None
    headers: dict[str, str] = {"X-API-Key": api_key, "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        _api_url(base_url, path),
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read() or b"{}"
            text = raw.decode("utf-8", errors="ignore")
            try:
                return resp.status, json.loads(text)
            except json.JSONDecodeError:
                return resp.status, {"raw": text}
    except urllib.error.HTTPError as exc:
        err_text = ""
        try:
            err_text = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        return exc.code, {"error": err_text or str(exc)}
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc)}


def _assert_ok(method: str, path: str, status: int, payload: object, body: object | None) -> None:
    if status < 200 or status >= 300:
        print(f"[{method}] {path} -> HTTP {status}")
        print(json.dumps({"payload": payload, "response": body}, indent=2))
        raise RuntimeError(f"Request failed: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test SCBE Browser-as-a-Service")
    parser.add_argument("--base-url", default="http://127.0.0.1:8600")
    parser.add_argument("--api-key", default=os.environ.get("SCBE_API_KEY", "demo_key_12345"))
    parser.add_argument("--url", default="https://example.com")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    if not args.api_key:
        print("Missing API key. Set --api-key or SCBE_API_KEY.", file=sys.stderr)
        return 2

    print("[1/6] Health check")
    health_status, health = request(args.base_url, "GET", "/health", args.api_key, timeout=args.timeout)
    _assert_ok("GET", "/health", health_status, None, health)
    print("    health:", json.dumps(health, indent=2))

    print("[2/6] Create browser session")
    create_status, create_body = request(
        args.base_url,
        "POST",
        "/v1/sessions",
        args.api_key,
        payload={"profile": "smoke", "headless": True},
        timeout=args.timeout,
    )
    _assert_ok("POST", "/v1/sessions", create_status, {"profile": "smoke", "headless": True}, create_body)
    session_id = _parse_session_id(create_body)
    if not session_id:
        print("Session response:", json.dumps(create_body, indent=2), file=sys.stderr)
        print("Session ID not returned by /v1/sessions", file=sys.stderr)
        return 2
    print(f"    session_id={session_id}")

    print("[3/6] Navigate to demo URL")
    nav_status, nav_body = request(
        args.base_url,
        "POST",
        f"/v1/sessions/{urllib.parse.quote(session_id)}/navigate",
        args.api_key,
        payload={"url": args.url},
        timeout=args.timeout,
    )
    _assert_ok("POST", "/v1/sessions/{id}/navigate", nav_status, {"url": args.url}, nav_body)
    print("    navigate:", json.dumps(nav_body, indent=2))

    print("[4/6] Session snapshot")
    snap_status, snap_body = request(
        args.base_url,
        "POST",
        f"/v1/sessions/{urllib.parse.quote(session_id)}/snapshot",
        args.api_key,
        timeout=args.timeout,
    )
    _assert_ok("POST", "/v1/sessions/{id}/snapshot", snap_status, None, snap_body)
    print("    snapshot:", json.dumps(snap_body, indent=2)[:2000])

    print("[5/6] Screenshot capture")
    shot_status, shot_body = request(
        args.base_url,
        "POST",
        f"/v1/sessions/{urllib.parse.quote(session_id)}/screenshot",
        args.api_key,
        timeout=args.timeout + 5,
    )
    _assert_ok("POST", "/v1/sessions/{id}/screenshot", shot_status, None, shot_body)
    if isinstance(shot_body, dict) and shot_body.get("screenshot"):
        print(f"    screenshot: base64 len={len(shot_body['screenshot'])}")
    else:
        print("    screenshot: response returned")

    print("[6/6] Usage summary")
    usage_status, usage_body = request(args.base_url, "GET", "/v1/usage", args.api_key, timeout=args.timeout)
    _assert_ok("GET", "/v1/usage", usage_status, None, usage_body)
    print("    usage:", json.dumps(usage_body, indent=2))

    # keep session briefly to support manual follow-up before auto-cleanup
    time.sleep(0.2)
    del_status, del_body = request(
        args.base_url,
        "DELETE",
        f"/v1/sessions/{urllib.parse.quote(session_id)}",
        args.api_key,
        timeout=args.timeout,
    )
    print("[cleanup] delete session ->", del_status, json.dumps(del_body))

    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
