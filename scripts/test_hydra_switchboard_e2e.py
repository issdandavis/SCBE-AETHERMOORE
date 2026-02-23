#!/usr/bin/env python3
"""E2E smoke test for HYDRA switchboard + remote workers."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hydra.spine import HydraSpine
from hydra.switchboard import Switchboard


async def seed_tasks(db_path: str) -> None:
    spine = HydraSpine(
        use_dual_lattice=False,
        use_switchboard=True,
        switchboard_db=db_path,
    )
    await spine.execute(
        {
            "action": "switchboard_enqueue",
            "role": "pilot",
            "task": {"action": "navigate", "target": "https://example.com", "params": {}},
            "dedupe_key": "pilot-nav-example",
        }
    )
    await spine.execute(
        {
            "action": "switchboard_enqueue",
            "role": "copilot",
            "task": {"action": "screenshot", "target": "full_page", "params": {}},
            "dedupe_key": "copilot-shot-example",
        }
    )
    await spine.execute(
        {
            "action": "switchboard_enqueue",
            "role": "judge",
            "task": {"action": "get_content", "target": "body", "params": {}},
            "dedupe_key": "judge-content-example",
        }
    )


def run_worker(role: str, db_path: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "hydra.remote_worker",
        "--db",
        db_path,
        "--roles",
        role,
        "--once",
        "--max-tasks",
        "1",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> int:
    td = tempfile.mkdtemp(prefix="hydra-switchboard-")
    db_path = str(Path(td) / "switchboard.db")
    asyncio.run(seed_tasks(db_path))
    run_worker("pilot", db_path)
    run_worker("copilot", db_path)
    run_worker("judge", db_path)

    board = Switchboard(db_path)
    stats = board.stats()
    done = int(stats.get("by_status", {}).get("done", 0))
    failed = int(stats.get("by_status", {}).get("failed", 0))
    assert done >= 3, f"expected >=3 done tasks, got {done}; stats={json.dumps(stats)}"
    assert failed == 0, f"expected 0 failed tasks, got {failed}; stats={json.dumps(stats)}"
    print(json.dumps({"ok": True, "done": done, "failed": failed, "db": db_path}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
