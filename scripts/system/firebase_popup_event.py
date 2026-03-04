#!/usr/bin/env python3
"""Push a quick popup/event into Firebase collections.

Examples:
  python scripts/system/firebase_popup_event.py --type post --content "M4 route online"
  python scripts/system/firebase_popup_event.py --type task --title "Review model routing"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            os.environ.setdefault(key, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Push popup-style events to Firebase.")
    parser.add_argument("--type", choices=("post", "task"), default="post")
    parser.add_argument("--content", default="SCBE popup event")
    parser.add_argument("--title", default="SCBE Event")
    parser.add_argument("--channel", default="ops")
    parser.add_argument("--tongue", default="KO")
    parser.add_argument("--task-status", default="available")
    args = parser.parse_args()

    _load_env()

    from src.fleet.firebase_connector import FirebaseSync

    fb = FirebaseSync()
    if not fb.initialize():
        print(json.dumps({"ok": False, "error": "firebase_init_failed", "project_id": fb.project_id}))
        return 1

    stamp = int(time.time())
    if args.type == "post":
        record_id = f"popup-{stamp}"
        payload = {
            "post_id": record_id,
            "content": args.content,
            "channel": args.channel,
            "tongue": args.tongue,
            "source": "firebase_popup_event",
            "created_at": stamp,
        }
        ok = fb.save_post(payload)
    else:
        record_id = f"task-{stamp}"
        payload = {
            "task_id": record_id,
            "title": args.title,
            "description": args.content,
            "status": args.task_status,
            "channel": args.channel,
            "source": "firebase_popup_event",
            "created_at": stamp,
        }
        ok = fb.save_task(payload)

    print(
        json.dumps(
            {
                "ok": bool(ok),
                "type": args.type,
                "id": record_id,
                "project_id": fb.project_id,
                "collection": "aethernet_posts" if args.type == "post" else "aethernet_tasks",
            }
        )
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
