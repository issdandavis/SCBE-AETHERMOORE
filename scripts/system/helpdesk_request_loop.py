#!/usr/bin/env python3
"""Local help-desk queue for tester requests and fix plans.

The loop is intentionally conservative: it records requests, evaluates them,
and emits scoped fix-plan commands. It does not modify source files directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "artifacts" / "helpdesk"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _slug(text: str, fallback: str = "ticket") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value[:72] or fallback


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            + "\n"
        )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _ticket_id(kind: str, title: str, body: str) -> str:
    return f"{kind}-{_sha256_text(title + chr(0) + body)[:16]}"


def submit_ticket(
    *,
    title: str,
    body: str,
    kind: str,
    requester: str = "tester",
    root: Path = DEFAULT_ROOT,
) -> dict[str, Any]:
    ticket = {
        "schema_version": "scbe-helpdesk-ticket-v1",
        "ticket_id": _ticket_id(kind, title, body),
        "created_at_utc": _utc_now(),
        "kind": kind,
        "requester": requester,
        "title": title,
        "body_sha256": _sha256_text(body),
        "body_chars": len(body),
        "status": "new",
    }
    _append_jsonl(root / "tickets.jsonl", ticket)
    return ticket


def _classify_paths(title: str, body: str) -> list[str]:
    text = f"{title} {body}".lower()
    paths = []
    if "agentbus" in text or "agent bus" in text or "pipe" in text:
        paths.extend(["scripts/scbe-system-cli.py", "scripts/system/agentbus_pipe.mjs"])
    if "watch" in text or "state" in text or "mirror" in text:
        paths.append("scripts/system/observable_state_watcher.py")
    if "track" in text or "file" in text:
        paths.append("scripts/system/auto_file_tracker.py")
    if "token" in text or "topolog" in text or "tree" in text:
        paths.append("src/tokenizer/topological_operator_tree.py")
    return sorted(set(paths or ["scripts/scbe-system-cli.py"]))


def evaluate_ticket(
    ticket: dict[str, Any], *, root: Path = DEFAULT_ROOT
) -> dict[str, Any]:
    title = str(ticket.get("title", ""))
    kind = str(ticket.get("kind", "feature"))
    severity = "high" if kind == "bug" else "medium"
    impacted_paths = _classify_paths(title, title)
    evaluation = {
        "schema_version": "scbe-helpdesk-evaluation-v1",
        "ticket_id": ticket["ticket_id"],
        "evaluated_at_utc": _utc_now(),
        "severity": severity,
        "route": {
            "primary": "agentbus",
            "state_space": "local_control_plane",
            "operation": "evaluate_then_plan",
        },
        "decision": "PLAN_FIX",
        "impacted_paths": impacted_paths,
        "required_checks": [
            "python -m pytest tests/test_agentbus_user_e2e.py -q",
            "python -m pytest tests/test_mirror_room_agent_bus.py tests/test_observable_state_watcher.py -q",
        ],
    }
    _append_jsonl(root / "evaluations.jsonl", evaluation)
    return evaluation


def build_fix_plan(
    ticket: dict[str, Any], evaluation: dict[str, Any], *, root: Path = DEFAULT_ROOT
) -> dict[str, Any]:
    plan = {
        "schema_version": "scbe-helpdesk-fix-plan-v1",
        "ticket_id": ticket["ticket_id"],
        "created_at_utc": _utc_now(),
        "title": ticket["title"],
        "decision": evaluation["decision"],
        "impacted_paths": evaluation["impacted_paths"],
        "steps": [
            "Reproduce through public CLI or Node pipe.",
            "Patch only impacted paths.",
            "Run required checks.",
            "Emit a new agentbus run summary and watcher artifact.",
        ],
        "commands": evaluation["required_checks"],
        "execution_policy": "plan_only_no_source_edits",
    }
    out_path = (
        root / "fix_plans" / f"{ticket['ticket_id']}-{_slug(str(ticket['title']))}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=True), encoding="utf-8")
    return {**plan, "path": str(out_path)}


def seed_demo(root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    seeded = []
    requests = [
        (
            "feature",
            "Expose agentbus as one user endpoint",
            "Tester wants one command that shapes, routes, dispatches, tracks, and watches a task.",
        ),
        (
            "feature",
            "Add Node JSON pipe for fleet automation",
            "Tester wants Zapier/Grok-style JSON events to flow through the agent bus.",
        ),
        (
            "bug",
            "Watcher can miss a just-written mirror round",
            "Tester saw watcher run before latest_round.json was visible and wants sequencing checks.",
        ),
    ]
    for kind, title, body in requests:
        ticket = submit_ticket(
            title=title, body=body, kind=kind, requester="system-helpdesk", root=root
        )
        evaluation = evaluate_ticket(ticket, root=root)
        plan = build_fix_plan(ticket, evaluation, root=root)
        seeded.append(
            {"ticket": ticket, "evaluation": evaluation, "plan_path": plan["path"]}
        )
    return {
        "schema_version": "scbe-helpdesk-seed-result-v1",
        "root": str(root),
        "count": len(seeded),
        "items": seeded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SCBE local help-desk request and fix-plan loop"
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    sub = parser.add_subparsers(dest="cmd", required=True)

    submit = sub.add_parser("submit")
    submit.add_argument("--kind", choices=["bug", "feature"], default="feature")
    submit.add_argument("--title", required=True)
    submit.add_argument("--body", required=True)
    submit.add_argument("--requester", default="tester")

    sub.add_parser("seed-demo")
    sub.add_parser("evaluate-open")

    args = parser.parse_args()
    root = Path(args.root)
    if args.cmd == "submit":
        ticket = submit_ticket(
            title=args.title,
            body=args.body,
            kind=args.kind,
            requester=args.requester,
            root=root,
        )
        evaluation = evaluate_ticket(ticket, root=root)
        plan = build_fix_plan(ticket, evaluation, root=root)
        print(
            json.dumps(
                {"ticket": ticket, "evaluation": evaluation, "plan": plan},
                indent=2,
                ensure_ascii=True,
            )
        )
        return 0
    if args.cmd == "seed-demo":
        print(json.dumps(seed_demo(root), indent=2, ensure_ascii=True))
        return 0
    if args.cmd == "evaluate-open":
        tickets = _load_jsonl(root / "tickets.jsonl")
        evaluations = []
        for ticket in tickets:
            evaluations.append(evaluate_ticket(ticket, root=root))
        print(
            json.dumps(
                {
                    "schema_version": "scbe-helpdesk-evaluate-open-v1",
                    "count": len(evaluations),
                },
                indent=2,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
