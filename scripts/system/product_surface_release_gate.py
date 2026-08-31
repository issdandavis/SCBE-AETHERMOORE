#!/usr/bin/env python3
"""Run the AetherBrowser + AetherDesk product release gate.

The gate starts both local product surfaces, verifies their health, executes one
bounded AetherDesk action, confirms receipts exist, and always writes a
consolidated JSON receipt before shutting down processes it started.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DESK_URL = "http://127.0.0.1:5717"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object from {url}")
    return value


def wait_for_json(url: str, timeout: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return request_json(url)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def run_npm(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [npm_command(), "run", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=True,
    )


def newest_browser_receipt() -> Path:
    candidates = list((ARTIFACTS / "smokes").glob("aetherbrowser-service-verify-*/service_verify_report.json"))
    if not candidates:
        raise RuntimeError("AetherBrowser verification did not emit service_verify_report.json")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def validate_browser_receipt(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") not in {"ok", "healthy"}:
        raise RuntimeError(f"AetherBrowser backend is not healthy: {report.get('status')!r}")
    if not report.get("extension_loaded"):
        raise RuntimeError("AetherBrowser Chrome extension worker was not detected")
    smoke = report.get("backend_smoke")
    if isinstance(smoke, dict) and smoke and smoke.get("ok") is False:
        raise RuntimeError("AetherBrowser backend smoke failed")
    return report


def write_gate_receipt(receipt: dict[str, Any]) -> Path:
    output = ARTIFACTS / "product_surface"
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = output / f"product_surface_release_gate_{stamp}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-running", action="store_true", help="Leave successfully started services running.")
    args = parser.parse_args(argv)

    started_at = utc_now()
    desk_process: subprocess.Popen[str] | None = None
    passed = False
    evidence: dict[str, Any] = {}
    error: str | None = None

    try:
        start = run_npm("aetherbrowser:service:start")
        evidence["aetherbrowser_start"] = {"ok": True, "stdout_tail": start.stdout[-2000:]}

        verify = run_npm("aetherbrowser:service:verify")
        browser_receipt_path = newest_browser_receipt()
        browser_report = validate_browser_receipt(browser_receipt_path)
        evidence["aetherbrowser_verify"] = {
            "ok": True,
            "receipt": str(browser_receipt_path.relative_to(ROOT)),
            "status": browser_report.get("status"),
            "extension_loaded": browser_report.get("extension_loaded"),
            "stdout_tail": verify.stdout[-2000:],
        }

        desk_process = subprocess.Popen(
            ["node", "aetherdesk/server.js"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        desk_health = wait_for_json(f"{DESK_URL}/api/health")
        if desk_health.get("ok") is not True:
            raise RuntimeError("AetherDesk health endpoint did not return ok=true")

        bounded_run = request_json(f"{DESK_URL}/api/run/token_lookup", method="POST", payload={})
        if bounded_run.get("ok") is not True:
            raise RuntimeError("AetherDesk bounded token lookup failed")
        receipt_list = request_json(f"{DESK_URL}/api/receipts?limit=5")
        receipts = receipt_list.get("receipts", [])
        if not receipts:
            raise RuntimeError("AetherDesk action completed without an audit receipt")
        evidence["aetherdesk"] = {
            "ok": True,
            "health_schema": desk_health.get("schema"),
            "bounded_action": "token_lookup",
            "receipt_count": len(receipts),
            "latest_receipt": receipts[0],
        }
        passed = True
    except Exception as exc:  # The receipt must describe failures too.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if not (passed and args.keep_running):
            if desk_process is not None and desk_process.poll() is None:
                desk_process.terminate()
                try:
                    desk_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    desk_process.kill()
            try:
                run_npm("aetherbrowser:service:stop")
            except Exception as stop_exc:
                evidence["shutdown_warning"] = f"{type(stop_exc).__name__}: {stop_exc}"

        receipt = {
            "schema": "scbe_product_surface_release_gate_v1",
            "started_at": started_at,
            "finished_at": utc_now(),
            "decision": "PASS" if passed else "FAIL",
            "error": error,
            "evidence": evidence,
        }
        receipt_path = write_gate_receipt(receipt)
        print(json.dumps({**receipt, "receipt_path": str(receipt_path)}, indent=2))

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
