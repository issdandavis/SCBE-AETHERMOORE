#!/usr/bin/env python3
"""SCBE full-system smoke test for bridge + browser + n8n workflows.

This script validates the runnable stack expected by SCBE workflow automation:
1) bridge health
2) browser service health
3) n8n health
4) bridge integrations status
5) governance scan endpoint
6) buffer post endpoint
7) n8n browse proxy path (optionally real browser execution)
8) agent task submit + completion poll
9) optional webhook route probe
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WEBHOOK_PATH = "scbe-notion-github-swarm"
DEFAULT_API_ENV_KEYS = (
    "SCBE_API_KEY",
    "N8N_API_KEY",
    "SCBE_BROWSER_API_KEY",
    "BROWSER_AGENT_API_KEY",
)


@dataclass
class CheckResult:
    name: str
    ok: bool
    required: bool
    status_code: int | None = None
    elapsed_ms: float = 0.0
    detail: str = ""
    response: Any = None


def _pick_api_key(explicit_value: str) -> str:
    if explicit_value.strip():
        return explicit_value.strip()
    for key in DEFAULT_API_ENV_KEYS:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return "test-key"


def _trim_response(value: Any, max_chars: int = 1200) -> Any:
    if isinstance(value, (dict, list)):
        encoded = json.dumps(value, ensure_ascii=True)
        if len(encoded) <= max_chars:
            return value
        return encoded[:max_chars] + "...<truncated>"
    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + "...<truncated>"
    return value


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 15.0,
) -> tuple[int | None, Any, str]:
    body_bytes: bytes | None = None
    req_headers = dict(headers or {})
    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(
        url=url,
        method=method.upper(),
        data=body_bytes,
        headers=req_headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if raw:
                try:
                    return int(resp.status), json.loads(raw), ""
                except json.JSONDecodeError:
                    return int(resp.status), raw, ""
            return int(resp.status), {}, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: Any = raw
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
        return int(exc.code), parsed, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        return None, {"error": reason}, "url_error"
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}, "exception"


def _wait_for_health(
    name: str,
    url: str,
    *,
    timeout_sec: float,
    request_timeout_sec: float,
) -> tuple[bool, str]:
    if timeout_sec <= 0:
        return True, "startup_wait_disabled"

    deadline = time.time() + timeout_sec
    last_detail = "not_started"
    while time.time() < deadline:
        status, _, error = _request_json(
            "GET",
            url,
            timeout_sec=request_timeout_sec,
        )
        if status == 200:
            return True, "ready"
        if status is None:
            last_detail = error or "unreachable"
        else:
            last_detail = f"status_{status}"
        time.sleep(1.0)
    return False, f"timeout_waiting_for_{name}:{last_detail}"


def _record_check(
    checks: list[CheckResult],
    *,
    name: str,
    required: bool,
    request_call,
    validate_call,
) -> None:
    started = time.time()
    status_code, payload, error = request_call()
    elapsed_ms = (time.time() - started) * 1000.0
    ok, detail = validate_call(status_code, payload, error)
    checks.append(
        CheckResult(
            name=name,
            ok=ok,
            required=required,
            status_code=status_code,
            elapsed_ms=round(elapsed_ms, 2),
            detail=detail,
            response=_trim_response(payload),
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE full-system smoke checks.")
    parser.add_argument("--bridge-url", default="http://127.0.0.1:8001", help="Bridge base URL.")
    parser.add_argument("--browser-url", default="http://127.0.0.1:8011", help="Browser service base URL.")
    parser.add_argument("--n8n-url", default="http://127.0.0.1:5678", help="n8n base URL.")
    parser.add_argument("--api-key", default="", help="API key for bridge/browser calls.")
    parser.add_argument("--timeout-sec", type=float, default=20.0, help="Per-request timeout.")
    parser.add_argument(
        "--startup-wait-sec",
        type=float,
        default=0.0,
        help="Wait for health endpoints before running checks (seconds).",
    )
    parser.add_argument("--poll-seconds", type=float, default=15.0, help="Task completion poll timeout.")
    parser.add_argument("--poll-interval-sec", type=float, default=1.0, help="Task completion poll interval.")
    parser.add_argument("--webhook-path", default=DEFAULT_WEBHOOK_PATH, help="n8n webhook path to probe.")
    parser.add_argument("--require-webhook", action="store_true", help="Fail if webhook route is not present.")
    parser.add_argument("--probe-webhook", action="store_true", help="Probe n8n webhook route.")
    parser.add_argument("--browse-real", action="store_true", help="Run real browser action instead of dry-run.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip browser health + browse proxy checks.")
    parser.add_argument("--skip-n8n", action="store_true", help="Skip n8n health + webhook checks.")
    parser.add_argument("--skip-governance", action="store_true", help="Skip governance scan endpoint check.")
    parser.add_argument("--skip-buffer", action="store_true", help="Skip buffer post endpoint check.")
    parser.add_argument("--skip-browse", action="store_true", help="Skip n8n browse proxy endpoint check.")
    parser.add_argument("--skip-agent-task", action="store_true", help="Skip agent task submit/poll check.")
    parser.add_argument(
        "--output",
        default="artifacts/system_smoke/full_system_smoke_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument("--print-json", action="store_true", help="Print JSON report to stdout.")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    api_key = _pick_api_key(args.api_key)
    headers = {"X-API-Key": api_key}
    checks: list[CheckResult] = []
    startup_messages: list[str] = []

    bridge_url = args.bridge_url.rstrip("/")
    browser_url = args.browser_url.rstrip("/")
    n8n_url = args.n8n_url.rstrip("/")

    wait_targets: list[tuple[str, str]] = [("bridge", f"{bridge_url}/health")]
    if not args.skip_browser:
        wait_targets.append(("browser", f"{browser_url}/health"))
    if not args.skip_n8n:
        wait_targets.append(("n8n", f"{n8n_url}/healthz"))

    for name, url in wait_targets:
        ok, msg = _wait_for_health(
            name,
            url,
            timeout_sec=args.startup_wait_sec,
            request_timeout_sec=max(1.0, min(args.timeout_sec, 5.0)),
        )
        startup_messages.append(f"{name}:{msg}")
        if not ok:
            checks.append(
                CheckResult(
                    name=f"startup_wait_{name}",
                    ok=False,
                    required=True,
                    detail=msg,
                )
            )

    if any(not c.ok and c.required for c in checks):
        report = _build_report(args, api_key, checks, startup_messages)
        _write_report(report, args.output, args.print_json)
        return 1

    _record_check(
        checks,
        name="bridge_health",
        required=True,
        request_call=lambda: _request_json("GET", f"{bridge_url}/health", timeout_sec=args.timeout_sec),
        validate_call=lambda status, payload, error: (
            status == 200 and isinstance(payload, dict),
            "ok" if status == 200 else f"{error or 'unexpected_status'}",
        ),
    )

    if not args.skip_browser:
        _record_check(
            checks,
            name="browser_health",
            required=True,
            request_call=lambda: _request_json("GET", f"{browser_url}/health", timeout_sec=args.timeout_sec),
            validate_call=lambda status, payload, error: (
                status == 200 and isinstance(payload, dict),
                "ok" if status == 200 else f"{error or 'unexpected_status'}",
            ),
        )

    if not args.skip_n8n:
        def _n8n_health_request() -> tuple[int | None, Any, str]:
            status, payload, error = _request_json(
                "GET",
                f"{n8n_url}/healthz",
                timeout_sec=args.timeout_sec,
            )
            if status == 200:
                return status, payload, error
            return _request_json("GET", n8n_url, timeout_sec=args.timeout_sec)

        _record_check(
            checks,
            name="n8n_health",
            required=True,
            request_call=_n8n_health_request,
            validate_call=lambda status, payload, error: (
                status == 200,
                "ok" if status == 200 else f"{error or 'unexpected_status'}",
            ),
        )

    _record_check(
        checks,
        name="bridge_integrations_status",
        required=True,
        request_call=lambda: _request_json(
            "GET",
            f"{bridge_url}/v1/integrations/status",
            headers=headers,
            timeout_sec=args.timeout_sec,
        ),
        validate_call=lambda status, payload, error: (
            status == 200 and isinstance(payload, dict) and "bridge" in payload,
            "ok" if status == 200 else f"{error or 'unexpected_status'}",
        ),
    )

    if not args.skip_governance:
        _record_check(
            checks,
            name="governance_scan",
            required=True,
            request_call=lambda: _request_json(
                "POST",
                f"{bridge_url}/v1/governance/scan",
                headers=headers,
                payload={
                    "content": "SCBE full-system smoke test governance payload.",
                    "scan_mode": "full",
                    "platforms": ["github", "notion", "n8n"],
                },
                timeout_sec=args.timeout_sec,
            ),
            validate_call=lambda status, payload, error: (
                status == 200 and isinstance(payload, dict),
                "ok" if status == 200 else f"{error or 'unexpected_status'}",
            ),
        )

    if not args.skip_buffer:
        _record_check(
            checks,
            name="buffer_post",
            required=True,
            request_call=lambda: _request_json(
                "POST",
                f"{bridge_url}/v1/buffer/post",
                headers=headers,
                payload={
                    "text": "SCBE smoke test post payload.",
                    "platforms": ["twitter"],
                    "tags": ["smoke", "scbe"],
                },
                timeout_sec=args.timeout_sec,
            ),
            validate_call=lambda status, payload, error: (
                status == 200 and isinstance(payload, dict),
                "ok" if status == 200 else f"{error or 'unexpected_status'}",
            ),
        )

    if not args.skip_browse and not args.skip_browser:
        browse_actions = (
            [
                {"action": "navigate", "target": "https://example.com", "timeout_ms": 15000},
                {"action": "extract", "target": "h1", "timeout_ms": 15000},
            ]
            if args.browse_real
            else [
                {"action": "navigate", "target": "https://example.com", "timeout_ms": 15000},
            ]
        )
        _record_check(
            checks,
            name="browse_proxy",
            required=True,
            request_call=lambda: _request_json(
                "POST",
                f"{bridge_url}/v1/integrations/n8n/browse",
                headers=headers,
                payload={
                    "actions": browse_actions,
                    "session_id": "scbe-full-smoke",
                    "dry_run": not args.browse_real,
                    "workflow_id": "full-system-smoke",
                    "run_id": f"smoke-{int(time.time())}",
                    "source": "n8n",
                },
                timeout_sec=max(args.timeout_sec, 45.0),
            ),
            validate_call=lambda status, payload, error: (
                status == 200 and isinstance(payload, dict),
                "ok" if status == 200 else f"{error or 'unexpected_status'}",
            ),
        )

    if not args.skip_agent_task:
        submit_status, submit_payload, submit_error = _request_json(
            "POST",
            f"{bridge_url}/v1/agent/task",
            headers=headers,
            payload={
                "task_type": "post_content",
                "goal": "smoke task completion validation",
                "text": "SCBE smoke task post payload",
                "platforms": ["twitter"],
            },
            timeout_sec=args.timeout_sec,
        )

        if submit_status != 200 or not isinstance(submit_payload, dict) or "task_id" not in submit_payload:
            checks.append(
                CheckResult(
                    name="agent_task_submit",
                    ok=False,
                    required=True,
                    status_code=submit_status,
                    detail=f"{submit_error or 'submit_failed'}",
                    response=_trim_response(submit_payload),
                )
            )
        else:
            task_id = str(submit_payload.get("task_id", "")).strip()
            deadline = time.time() + max(1.0, args.poll_seconds)
            final_status = "unknown"
            last_payload: Any = {}
            last_code: int | None = None
            while time.time() < deadline:
                last_code, last_payload, _ = _request_json(
                    "GET",
                    f"{bridge_url}/v1/agent/task/{task_id}/status",
                    headers=headers,
                    timeout_sec=args.timeout_sec,
                )
                if last_code == 200 and isinstance(last_payload, dict):
                    final_status = str(last_payload.get("status", "unknown")).lower()
                    if final_status in {"completed", "failed", "timeout", "cancelled"}:
                        break
                time.sleep(max(0.2, args.poll_interval_sec))

            checks.append(
                CheckResult(
                    name="agent_task_completion",
                    ok=final_status == "completed",
                    required=True,
                    status_code=last_code,
                    detail=f"final_status={final_status}",
                    response=_trim_response(last_payload),
                )
            )

    if args.probe_webhook and not args.skip_n8n:
        webhook_candidates = [
            f"{n8n_url}/webhook/{args.webhook_path}",
            f"{n8n_url}/webhook-test/{args.webhook_path}",
        ]
        probe_results: list[tuple[str, int | None, Any, str]] = []
        for url in webhook_candidates:
            code, payload, error = _request_json(
                "GET",
                url,
                timeout_sec=args.timeout_sec,
            )
            probe_results.append((url, code, payload, error))

        existing_codes = {200, 400, 401, 403, 405, 409, 422}
        seen_codes = {item[1] for item in probe_results if item[1] is not None}
        has_existing_route = any(code in existing_codes for code in seen_codes)
        has_server_error = any(code is not None and code >= 500 for code in seen_codes)

        if has_existing_route:
            webhook_ok = True
            detail = "route_detected"
        elif has_server_error:
            webhook_ok = False
            detail = "route_error"
        else:
            webhook_ok = not args.require_webhook
            detail = "route_missing"

        checks.append(
            CheckResult(
                name="n8n_webhook_probe",
                ok=webhook_ok,
                required=args.require_webhook,
                detail=detail,
                response=_trim_response(
                    [
                        {
                            "url": url,
                            "status_code": code,
                            "error": error,
                            "payload": payload,
                        }
                        for url, code, payload, error in probe_results
                    ]
                ),
            )
        )

    report = _build_report(args, api_key, checks, startup_messages)
    _write_report(report, args.output, args.print_json)

    required_failures = [
        c for c in checks if c.required and not c.ok
    ]
    return 1 if required_failures else 0


def _build_report(
    args: argparse.Namespace,
    api_key: str,
    checks: list[CheckResult],
    startup_messages: list[str],
) -> dict[str, Any]:
    required_failures = [c for c in checks if c.required and not c.ok]
    optional_failures = [c for c in checks if not c.required and not c.ok]
    ok_count = sum(1 for c in checks if c.ok)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "bridge_url": args.bridge_url,
            "browser_url": args.browser_url,
            "n8n_url": args.n8n_url,
            "api_key_source": "explicit_or_env_or_default",
            "api_key_preview": f"{api_key[:4]}***" if api_key else "",
            "startup_wait_sec": args.startup_wait_sec,
            "poll_seconds": args.poll_seconds,
            "probe_webhook": args.probe_webhook,
            "require_webhook": args.require_webhook,
            "browse_real": args.browse_real,
        },
        "startup_wait": startup_messages,
        "counts": {
            "total_checks": len(checks),
            "ok": ok_count,
            "required_failures": len(required_failures),
            "optional_failures": len(optional_failures),
        },
        "checks": [asdict(check) for check in checks],
    }
    return summary


def _write_report(report: dict[str, Any], output_path: str, print_json: bool) -> None:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, indent=2)
    out_path.write_text(encoded, encoding="utf-8")
    if print_json:
        print(encoded)
    else:
        counts = report.get("counts", {})
        print(
            "[SCBE] Full-system smoke summary: "
            f"{counts.get('ok', 0)}/{counts.get('total_checks', 0)} checks passed; "
            f"required_failures={counts.get('required_failures', 0)} "
            f"optional_failures={counts.get('optional_failures', 0)}"
        )
        print(f"[SCBE] Report written: {out_path}")


if __name__ == "__main__":
    raise SystemExit(run())
