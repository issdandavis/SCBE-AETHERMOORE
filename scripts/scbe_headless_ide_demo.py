#!/usr/bin/env python3
"""
SCBE Headless IDE Demo
======================

Creates a local-first HYDRA switchboard coding workflow:
- planner -> coder -> reviewer -> memory
- optional local worker execution
- visual exports (Mermaid + HTML dashboard)
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hydra.switchboard import Switchboard


def _to_rel(path: Path, workspace: Path) -> str:
    try:
        rel = path.resolve().relative_to(workspace.resolve())
        return str(rel).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _seed_demo_tasks(board: Switchboard, workspace: Path, out_dir: Path) -> List[Dict[str, Any]]:
    output_dir = out_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_path = _to_rel(output_dir / "plan.md", workspace)
    code_path = _to_rel(output_dir / "claybot_demo.py", workspace)
    memory_path = _to_rel(output_dir / "memory.log", workspace)

    tasks = [
        {
            "role": "planner",
            "priority": 10,
            "dedupe": "headless-ide-plan",
            "task": {
                "action": "plan_doc",
                "target": plan_path,
                "params": {
                    "title": "ClayBot Headless IDE Plan",
                    "prompt": "Build local-first ClayBot/PollyBot headless coding workflow with switchboard lanes.",
                },
            },
        },
        {
            "role": "coder",
            "priority": 20,
            "dedupe": "headless-ide-code",
            "task": {
                "action": "write_file",
                "target": code_path,
                "params": {
                    "content": (
                        "def claybot_status():\n"
                        "    return {\n"
                        "        'system': 'SCBE-HYDRA',\n"
                        "        'mode': 'headless-ide',\n"
                        "        'state': 'ready'\n"
                        "    }\n\n"
                        "if __name__ == '__main__':\n"
                        "    print(claybot_status())\n"
                    )
                },
            },
        },
        {
            "role": "reviewer",
            "priority": 30,
            "dedupe": "headless-ide-review",
            "task": {
                "action": "run_cmd",
                "target": f"python -m py_compile {code_path}",
                "params": {"timeout_sec": 45},
            },
        },
        {
            "role": "memory",
            "priority": 40,
            "dedupe": "headless-ide-memory",
            "task": {
                "action": "append_file",
                "target": memory_path,
                "params": {
                    "content": (
                        "Headless IDE session stored.\n"
                        "- Roles executed: planner,coder,reviewer,memory\n"
                        "- Output artifact: claybot_demo.py\n"
                    )
                },
            },
        },
    ]

    queued: List[Dict[str, Any]] = []
    for item in tasks:
        queued.append(
            board.enqueue_task(
                role=item["role"],
                payload=item["task"],
                dedupe_key=item["dedupe"],
                priority=int(item["priority"]),
            )
        )
    return queued


def _run_workers(db_path: Path, workspace: Path) -> None:
    roles = ["planner", "coder", "reviewer", "memory"]
    for role in roles:
        cmd = [
            sys.executable,
            "-m",
            "hydra.remote_coding_worker",
            "--db",
            str(db_path),
            "--roles",
            role,
            "--workspace",
            str(workspace),
            "--domain",
            "fleet",
            "--once",
            "--max-tasks",
            "5",
            "--allowed-cmd-prefixes",
            "python,pytest",
        ]
        subprocess.run(cmd, cwd=str(ROOT), check=True)


def _read_rows(db_path: Path, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append({k: row[k] for k in row.keys()})
    return out


def _parse_json(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _render_mermaid(tasks: List[Dict[str, Any]]) -> str:
    lines = ["flowchart LR"]
    role_order = ["planner", "coder", "reviewer", "memory"]

    by_role: Dict[str, List[Dict[str, Any]]] = {r: [] for r in role_order}
    for task in tasks:
        role = str(task.get("role", "")).lower()
        by_role.setdefault(role, []).append(task)

    def node_id(task_id: str) -> str:
        return f"n_{task_id.replace('-', '_')}"

    for role in role_order:
        role_tasks = by_role.get(role, [])
        if not role_tasks:
            continue
        lines.append(f"  subgraph {role.upper()}")
        for t in role_tasks:
            tid = str(t.get("task_id"))
            payload = t.get("payload_json", {})
            if isinstance(payload, str):
                payload = _parse_json(payload)
            action = payload.get("action", "task") if isinstance(payload, dict) else "task"
            status = str(t.get("status", "queued"))
            lines.append(f'    {node_id(tid)}["{role}:{action} ({status})"]')
        lines.append("  end")

    ordered = sorted(tasks, key=lambda x: int(x.get("created_at", 0)))
    for idx in range(len(ordered) - 1):
        a = node_id(str(ordered[idx].get("task_id")))
        b = node_id(str(ordered[idx + 1].get("task_id")))
        lines.append(f"  {a} --> {b}")

    return "\n".join(lines) + "\n"


def _render_html(tasks: List[Dict[str, Any]], messages: List[Dict[str, Any]], stats: Dict[str, Any], mermaid_text: str) -> str:
    status_counts = Counter(str(t.get("status", "unknown")) for t in tasks)
    roles = ["planner", "coder", "reviewer", "memory"]

    lane_html_parts: List[str] = []
    for role in roles:
        lane_tasks = [t for t in tasks if str(t.get("role", "")).lower() == role]
        cards: List[str] = []
        for t in lane_tasks:
            payload = _parse_json(t.get("payload_json"))
            action = payload.get("action", "task") if isinstance(payload, dict) else "task"
            status = str(t.get("status", "queued"))
            cards.append(
                f"""
                <div class="card status-{status}">
                  <div class="task-id">{t.get('task_id')}</div>
                  <div><b>{action}</b></div>
                  <div>status: {status}</div>
                </div>
                """
            )
        lane_html_parts.append(
            f"""
            <section class="lane">
              <h3>{role.upper()}</h3>
              {''.join(cards) if cards else '<div class="empty">No tasks</div>'}
            </section>
            """
        )

    message_rows: List[str] = []
    for m in messages[-20:]:
        message_rows.append(
            f"<tr><td>{m.get('id')}</td><td>{m.get('channel')}</td><td>{m.get('sender')}</td><td><pre>{json.dumps(_parse_json(m.get('message_json')), indent=2)}</pre></td></tr>"
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SCBE Headless IDE Dashboard</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 16px; background: #0d1117; color: #e6edf3; }}
    .stats {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
    .pill {{ border: 1px solid #30363d; padding: 8px 12px; border-radius: 8px; background: #161b22; }}
    .lanes {{ display: grid; grid-template-columns: repeat(4, minmax(220px, 1fr)); gap: 12px; }}
    .lane {{ border: 1px solid #30363d; border-radius: 8px; padding: 10px; background: #161b22; min-height: 180px; }}
    .card {{ border: 1px solid #30363d; border-radius: 6px; padding: 8px; margin-bottom: 8px; background: #0f172a; }}
    .task-id {{ font-size: 12px; opacity: 0.75; margin-bottom: 4px; }}
    .status-done {{ border-color: #1f6feb; }}
    .status-failed {{ border-color: #f85149; }}
    .status-queued {{ border-color: #d29922; }}
    .empty {{ opacity: 0.7; font-style: italic; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; vertical-align: top; }}
    pre {{ white-space: pre-wrap; margin: 0; font-size: 12px; }}
    textarea {{ width: 100%; min-height: 220px; background: #0f172a; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }}
  </style>
</head>
<body>
  <h1>SCBE Headless IDE Dashboard</h1>
  <div class="stats">
    <div class="pill">tasks: {len(tasks)}</div>
    <div class="pill">done: {status_counts.get('done', 0)}</div>
    <div class="pill">failed: {status_counts.get('failed', 0)}</div>
    <div class="pill">queued: {status_counts.get('queued', 0)}</div>
    <div class="pill">messages: {len(messages)}</div>
  </div>
  <div class="lanes">
    {''.join(lane_html_parts)}
  </div>
  <h2>Mermaid Flow</h2>
  <textarea readonly>{mermaid_text}</textarea>
  <h2>Role Messages (Last 20)</h2>
  <table>
    <thead><tr><th>id</th><th>channel</th><th>sender</th><th>message</th></tr></thead>
    <tbody>
      {''.join(message_rows)}
    </tbody>
  </table>
  <h2>Raw Stats</h2>
  <pre>{json.dumps(stats, indent=2)}</pre>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SCBE headless IDE demo")
    parser.add_argument("--db", default="artifacts/hydra/headless_ide/switchboard.db")
    parser.add_argument("--out-dir", default="artifacts/hydra/headless_ide")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--no-run-workers", action="store_true")
    args = parser.parse_args()

    db_path = (ROOT / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db).resolve()
    out_dir = (ROOT / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir).resolve()
    workspace = (ROOT / args.workspace).resolve() if not Path(args.workspace).is_absolute() else Path(args.workspace).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    board = Switchboard(str(db_path))
    queued = _seed_demo_tasks(board, workspace=workspace, out_dir=out_dir)

    if not args.no_run_workers:
        _run_workers(db_path=db_path, workspace=workspace)

    tasks = _read_rows(
        db_path,
        """
        SELECT task_id, role, payload_json, status, priority, attempts, result_json, error_text, created_at, updated_at
        FROM tasks
        ORDER BY created_at ASC
        """,
    )
    messages = _read_rows(
        db_path,
        """
        SELECT id, channel, sender, message_json, created_at
        FROM role_messages
        ORDER BY id ASC
        """,
    )
    stats = board.stats()
    mermaid_text = _render_mermaid(tasks)

    mermaid_path = out_dir / "headless_ide_flow.mmd"
    html_path = out_dir / "headless_ide_dashboard.html"
    summary_path = out_dir / "headless_ide_summary.json"

    mermaid_path.write_text(mermaid_text, encoding="utf-8")
    html_path.write_text(_render_html(tasks, messages, stats, mermaid_text), encoding="utf-8")

    summary = {
        "db_path": str(db_path),
        "queued": queued,
        "stats": stats,
        "artifacts": {
            "dashboard_html": str(html_path),
            "flow_mermaid": str(mermaid_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
