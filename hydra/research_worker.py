"""HYDRA cloud research worker.

Extends the remote worker pattern with a multi-step `research_fetch` action:
1) navigate
2) extract page HTML
3) return cleaned text content
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import time
from typing import Any, Dict, List

from agents.browser.playwright_wrapper import BrowserConfig, PlaywrightWrapper

from .limbs import BrowserLimb
from .research import html_to_text
from .switchboard import Switchboard


def _worker_id(cli_worker_id: str | None) -> str:
    if cli_worker_id and cli_worker_id.strip():
        return cli_worker_id.strip()
    return f"{socket.gethostname()}-{int(time.time())}"


async def _handle_research_fetch(
    browser: PlaywrightWrapper,
    *,
    url: str,
    max_chars: int,
    timeout_ms: int,
) -> Dict[str, Any]:
    """Execute research fetch pipeline for one URL."""
    final_url = await browser.navigate(url, timeout_ms=timeout_ms)
    html = await browser.get_page_content()
    text = html_to_text(html, max_chars=max_chars)
    return {
        "success": True,
        "url": final_url,
        "text": text,
        "chars": len(text),
    }


async def run_worker(args: argparse.Namespace) -> int:
    roles: List[str] = [r.strip().lower() for r in args.roles.split(",") if r.strip()]
    if not roles:
        raise ValueError("At least one role is required")

    worker_id = _worker_id(args.worker_id)
    board = Switchboard(args.db)

    # Fallback limb for non-research tasks.
    limb = BrowserLimb(backend_type=args.backend, scbe_url=args.scbe_url)
    await limb.activate()

    browser = PlaywrightWrapper(
        BrowserConfig(
            headless=True,
            default_timeout_ms=args.timeout_ms,
            navigation_timeout_ms=args.timeout_ms,
        )
    )
    await browser.initialize()

    processed = 0
    print(
        json.dumps(
            {
                "event": "research_worker_start",
                "worker_id": worker_id,
                "roles": roles,
                "db": args.db,
                "backend": args.backend,
            }
        )
    )

    try:
        while True:
            task = board.claim_task(worker_id, roles, lease_seconds=args.lease_sec)
            if not task:
                if args.once:
                    break
                await asyncio.sleep(args.poll_sec)
                continue

            task_id = task["task_id"]
            payload = task.get("payload", {})
            action = str(payload.get("action", "")).strip()
            target = str(payload.get("target", "")).strip()
            params = payload.get("params", {}) if isinstance(payload.get("params", {}), dict) else {}

            t0 = time.time()
            try:
                if action == "research_fetch":
                    if not target:
                        raise ValueError("research_fetch requires target URL")
                    max_chars = int(params.get("max_chars", args.max_chars))
                    result = await _handle_research_fetch(
                        browser,
                        url=target,
                        max_chars=max_chars,
                        timeout_ms=args.timeout_ms,
                    )
                else:
                    if not action or not target:
                        raise ValueError("payload requires action and target")
                    result = await limb.execute(action, target, params)

                elapsed_ms = round((time.time() - t0) * 1000.0, 2)
                result["elapsed_ms"] = elapsed_ms
                result["worker_id"] = worker_id
                result["task_role"] = task.get("role")

                if result.get("success"):
                    board.complete_task(task_id, worker_id, result)
                    status = "done"
                else:
                    err = str(result.get("error") or result.get("reason") or "execution failed")
                    board.fail_task(task_id, worker_id, err, result=result)
                    status = "failed"
            except Exception as exc:  # noqa: BLE001
                board.fail_task(task_id, worker_id, str(exc), result={"worker_id": worker_id})
                status = "failed"
                result = {"error": str(exc)}

            processed += 1
            print(
                json.dumps(
                    {
                        "event": "task_processed",
                        "worker_id": worker_id,
                        "task_id": task_id,
                        "role": task.get("role"),
                        "status": status,
                        "result_preview": str(result)[:300],
                    }
                )
            )

            if args.max_tasks > 0 and processed >= args.max_tasks:
                break
    finally:
        await browser.close()
        await limb.deactivate()

    print(json.dumps({"event": "research_worker_stop", "worker_id": worker_id, "processed": processed}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HYDRA cloud research worker")
    parser.add_argument("--db", default="artifacts/hydra/switchboard.db")
    parser.add_argument("--roles", default="researcher")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--backend", default="playwright")
    parser.add_argument("--scbe-url", default="http://127.0.0.1:8080")
    parser.add_argument("--poll-sec", type=float, default=1.0)
    parser.add_argument("--lease-sec", type=int, default=60)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_worker(args))


if __name__ == "__main__":
    main()
