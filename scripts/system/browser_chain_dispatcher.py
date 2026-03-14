#!/usr/bin/env python3
"""Simple browser lane dispatcher for SCBE browser skills.

Provides a lightweight registry that maps domains/tasks to browser tentacles.
This module intentionally stays dependency-light so automation can run even
without Playwriter/Playwright extension connectivity.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BrowserTentacle:
    tentacle_id: str
    domain_patterns: List[str]
    default_task: str = "navigate"
    execution_engine: str = "playwriter"
    tags: List[str] = field(default_factory=list)

    def matches(self, domain: str) -> bool:
        check = domain.strip().lower()
        return any(check == pat or check.endswith(f".{pat}") for pat in self.domain_patterns)


class BrowserChainDispatcher:
    def __init__(self) -> None:
        self._tentacles: List[BrowserTentacle] = []

    def register_tentacle(self, tentacle: BrowserTentacle) -> None:
        self._tentacles.append(tentacle)

    def assign_task(self, domain: str, task_type: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = payload or {}
        engine = str(payload.get("engine", "playwriter")).strip().lower() or "playwriter"
        domain_norm = domain.strip().lower()
        task_norm = task_type.strip().lower() or "navigate"

        selected = next((t for t in self._tentacles if t.matches(domain_norm)), None)
        if selected is None:
            selected = BrowserTentacle(
                tentacle_id="tentacle-generic",
                domain_patterns=[domain_norm],
                default_task="navigate",
                execution_engine=engine,
                tags=["generic"],
            )

        return {
            "ok": True,
            "assigned_at": _utc_iso(),
            "domain": domain_norm,
            "task_type": task_norm,
            "tentacle_id": selected.tentacle_id,
            "execution_engine": engine or selected.execution_engine,
            "tentacle": asdict(selected),
            "payload": payload,
        }


def build_default_fleet() -> List[BrowserTentacle]:
    return [
        BrowserTentacle(
            tentacle_id="tentacle-arxiv-um",
            domain_patterns=["arxiv.org"],
            default_task="research",
            execution_engine="playwriter",
            tags=["research", "metadata", "evidence"],
        ),
        BrowserTentacle(
            tentacle_id="tentacle-github-ko",
            domain_patterns=["github.com"],
            default_task="navigate",
            execution_engine="playwriter",
            tags=["repo", "pr", "issues"],
        ),
        BrowserTentacle(
            tentacle_id="tentacle-notion-av",
            domain_patterns=["notion.so", "www.notion.so"],
            default_task="navigate",
            execution_engine="playwriter",
            tags=["workspace", "knowledge"],
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch browser tasks to SCBE tentacles.")
    parser.add_argument("--domain", required=True, help="Target domain, e.g. arxiv.org")
    parser.add_argument("--task", default="navigate", help="Task type, e.g. research/navigate")
    parser.add_argument("--engine", default="playwriter", help="Execution engine (playwriter/playwright)")
    parser.add_argument("--payload-json", default="", help="Optional JSON payload for assignment context")
    args = parser.parse_args()

    payload: Dict[str, Any] = {"engine": args.engine}
    if args.payload_json.strip():
        try:
            extra = json.loads(args.payload_json)
            if isinstance(extra, dict):
                payload.update(extra)
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"invalid payload JSON: {exc}"}))
            return 1

    dispatcher = BrowserChainDispatcher()
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    result = dispatcher.assign_task(domain=args.domain, task_type=args.task, payload=payload)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
