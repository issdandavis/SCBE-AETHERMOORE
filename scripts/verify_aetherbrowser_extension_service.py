#!/usr/bin/env python3
"""Verify a running AetherBrowser backend + Chrome extension service stack."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.aetherbrowser_live_smoke import run_ws_smoke


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fetch_health(host: str, port: int, timeout: float = 5.0) -> dict[str, Any]:
    response = httpx.get(f"http://{host}:{port}/health", timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_cdp_targets(port: int, timeout: float = 5.0) -> list[dict[str, Any]]:
    response = httpx.get(f"http://127.0.0.1:{port}/json/list", timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("CDP target list is not a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def classify_cdp_targets(targets: list[dict[str, Any]]) -> dict[str, Any]:
    pages = [target for target in targets if target.get("type") == "page"]
    workers = [target for target in targets if target.get("type") == "service_worker"]
    extension_workers = [
        target for target in workers if str(target.get("url", "")).startswith("chrome-extension://")
    ]
    extension_ids = sorted(
        {
            str(target.get("url", "")).split("/")[2]
            for target in extension_workers
            if str(target.get("url", "")).startswith("chrome-extension://")
        }
    )
    return {
        "page_count": len(pages),
        "service_worker_count": len(workers),
        "extension_worker_count": len(extension_workers),
        "extension_ids": extension_ids,
        "pages": [
            {
                "title": page.get("title", ""),
                "url": page.get("url", ""),
                "id": page.get("id", ""),
            }
            for page in pages
        ],
        "extension_workers": [
            {
                "title": worker.get("title", ""),
                "url": worker.get("url", ""),
                "id": worker.get("id", ""),
            }
            for worker in extension_workers
        ],
    }


def build_service_report(
    health: dict[str, Any],
    cdp: dict[str, Any],
    backend_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executor = health.get("executor", {}) if isinstance(health, dict) else {}
    ready_providers = sorted(
        provider
        for provider, meta in executor.items()
        if isinstance(meta, dict) and meta.get("available") is True
    )
    blocked_providers = sorted(
        provider
        for provider, meta in executor.items()
        if isinstance(meta, dict) and meta.get("available") is False
    )
    return {
        "status": health.get("status"),
        "backend_version": health.get("version"),
        "ready_providers": ready_providers,
        "blocked_providers": blocked_providers,
        "agent_count": len(health.get("agents", {})) if isinstance(health.get("agents"), dict) else 0,
        "cdp": cdp,
        "backend_smoke": backend_smoke or {},
        "extension_loaded": cdp.get("extension_worker_count", 0) > 0,
    }


def write_report(report: dict[str, Any]) -> Path:
    output_dir = PROJECT_ROOT / "artifacts" / "smokes" / f"aetherbrowser-service-verify-{utc_stamp()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "service_verify_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a running AetherBrowser service stack.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--chrome-port", type=int, default=9222)
    parser.add_argument("--run-backend-smoke", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    health = fetch_health(args.host, args.port)
    targets = fetch_cdp_targets(args.chrome_port)
    cdp = classify_cdp_targets(targets)
    backend_smoke = asyncio.run(run_ws_smoke(args.host, args.port)) if args.run_backend_smoke else None
    report = build_service_report(health, cdp, backend_smoke)
    report_path = write_report(report)
    payload = {"report_path": str(report_path), **report}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"AetherBrowser service verify complete: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
