#!/usr/bin/env python3
"""Targeted smoke checks for AetherCode gateway UX and install surfaces."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    required: bool
    status_code: int | None
    elapsed_ms: float
    detail: str
    response_preview: Any


def _request(
    url: str,
    timeout_sec: float,
    *,
    method: str = "GET",
    json_body: Any | None = None,
) -> tuple[int | None, str, str]:
    headers = {}
    data = None
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), text, ""
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), text, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        return None, "", f"url_error_{getattr(exc, 'reason', exc)}"
    except Exception as exc:  # noqa: BLE001
        return None, "", f"exception_{exc}"


def _preview(text: str, limit: int = 200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


def _json_ok(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def _json_field_matches(text: str, expected: dict[str, Any]) -> bool:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    for key, value in expected.items():
        if payload.get(key) != value:
            return False
    return True


def _run_check(
    *,
    checks: list[CheckResult],
    base_url: str,
    path: str,
    name: str,
    required: bool,
    validator,
    timeout_sec: float,
    method: str = "GET",
    json_body: Any | None = None,
) -> None:
    url = f"{base_url}{path}"
    started = time.time()
    code, body, err = _request(
        url,
        timeout_sec=timeout_sec,
        method=method,
        json_body=json_body,
    )
    elapsed_ms = round((time.time() - started) * 1000.0, 2)
    ok, detail = validator(code, body, err)
    checks.append(
        CheckResult(
            name=name,
            ok=ok,
            required=required,
            status_code=code,
            elapsed_ms=elapsed_ms,
            detail=detail,
            response_preview=_preview(body),
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke check AetherCode gateway surfaces.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8500", help="Gateway base URL.")
    parser.add_argument("--timeout-sec", type=float, default=5.0, help="Per-request timeout seconds.")
    parser.add_argument(
        "--output",
        default="artifacts/system_smoke/aethercode_gateway_smoke.json",
        help="Output report path.",
    )
    parser.add_argument("--print-json", action="store_true", help="Print full JSON report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    checks: list[CheckResult] = []

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/health",
        name="health",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and _json_ok(body),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/api/status",
        name="api_status",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and _json_ok(body),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/ops/crosstalk",
        name="ops_crosstalk",
        required=True,
        timeout_sec=args.timeout_sec,
        method="POST",
        json_body={"summary": "smoke-check crosstalk route"},
        validator=lambda code, body, err: (
            code == 200 and _json_field_matches(body, {"ok": True, "action": "crosstalk"}),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/ops/publish",
        name="ops_publish",
        required=True,
        timeout_sec=args.timeout_sec,
        method="POST",
        json_body={},
        validator=lambda code, body, err: (
            code == 200 and _json_field_matches(body, {"ok": True, "action": "publish"}),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/",
        name="root_ui",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and "<html" in body.lower(),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/arena",
        name="arena_ui",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and "<html" in body.lower(),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/home",
        name="home_ui",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and "<html" in body.lower(),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/manifest.json",
        name="manifest",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and _json_ok(body),
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    _run_check(
        checks=checks,
        base_url=base_url,
        path="/sw.js",
        name="service_worker",
        required=True,
        timeout_sec=args.timeout_sec,
        validator=lambda code, body, err: (
            code == 200 and "addEventListener" in body,
            "ok" if code == 200 else (err or f"status_{code}"),
        ),
    )

    required_failures = [check for check in checks if check.required and not check.ok]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "counts": {
            "total": len(checks),
            "passed": sum(1 for check in checks if check.ok),
            "required_failures": len(required_failures),
        },
        "checks": [asdict(check) for check in checks],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.print_json:
        print(json.dumps(report, indent=2))
    else:
        counts = report["counts"]
        print(
            "[AetherCode] Smoke summary: "
            f"{counts['passed']}/{counts['total']} passed; "
            f"required_failures={counts['required_failures']}"
        )
        print(f"[AetherCode] Report written: {out_path}")

    return 1 if required_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
