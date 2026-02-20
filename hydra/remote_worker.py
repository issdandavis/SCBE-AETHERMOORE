"""
HYDRA Remote Browser Worker
===========================

Polls switchboard tasks by role, executes browser actions, and writes results.
Designed to run on remote/virtual compute to reduce local workstation load.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import time
from typing import Any, Dict, List

from .limbs import BrowserLimb
from .switchboard import Switchboard


def _worker_id(cli_worker_id: str | None) -> str:
    if cli_worker_id and cli_worker_id.strip():
        return cli_worker_id.strip()
    return f"{socket.gethostname()}-{int(time.time())}"


async def run_worker(args: argparse.Namespace) -> int:
    roles: List[str] = [r.strip().lower() for r in args.roles.split(",") if r.strip()]
    if not roles:
        raise ValueError("At least one role is required")

    worker_id = _worker_id(args.worker_id)
    board = Switchboard(args.db)
    limb = BrowserLimb(backend_type=args.backend, scbe_url=args.scbe_url)
    await limb.activate()

    processed = 0
    print(
        json.dumps(
            {
                "event": "worker_start",
                "worker_id": worker_id,
                "roles": roles,
                "db": args.db,
                "backend": args.backend,
            }
        )
    )

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

    print(json.dumps({"event": "worker_stop", "worker_id": worker_id, "processed": processed}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HYDRA remote browser worker")
    parser.add_argument("--db", default="artifacts/hydra/switchboard.db")
    parser.add_argument("--roles", default="pilot")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--backend", default="playwright")
    parser.add_argument("--scbe-url", default="http://127.0.0.1:8080")
    parser.add_argument("--poll-sec", type=float, default=1.0)
    parser.add_argument("--lease-sec", type=int, default=60)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_worker(args))


if __name__ == "__main__":
    main()

