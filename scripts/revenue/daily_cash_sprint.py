#!/usr/bin/env python3
"""Generate a 20-minute daily cash sprint packet for SCBE.

This is deliberately local-only: it does not send outreach, charge cards, or
publish products. It turns current repo proof into a small daily execution
packet that can be reviewed, sent manually, or handed to connector automation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "artifacts" / "revenue" / "cash_sprint"
StateName = Literal["PENDING", "RUNNING", "DONE", "BLOCKED"]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class Offer:
    offer_id: str
    title: str
    buyer: str
    price_floor_usd: int
    price_anchor_usd: int
    promise: str
    deliverables: list[str]
    proof_paths: list[str]
    call_to_action: str


DEFAULT_OFFERS = [
    Offer(
        offer_id="local_ai_command_center_setup",
        title="GeoSeal CLI Agent Bus Setup",
        buyer="solo founders, indie devs, and small teams trying to make local AI coding agents cooperate",
        price_floor_usd=150,
        price_anchor_usd=500,
        promise="Install or package GeoSeal CLI and prove a real task crosses the local agent bus with an audit event.",
        deliverables=[
            "Install or verify the GeoSeal CLI entrypoint from npm/PyPI/local checkout.",
            "Run a real publish-readiness or coding-task prompt through the free/local agent bus.",
            "Deliver the command log, bus event hash, and exact next command for the buyer.",
        ],
        proof_paths=[
            "bin/geoseal.cjs",
            "src/geoseal_cli.py",
            "src/api/geoseal_service.py",
            "src/api/free_llm_routes.py",
            "tests/smoke/test_geoseal_service.py",
            "tests/smoke/test_npm_geoseal_bin.py",
            "tests/api/test_free_llm_routes.py",
        ],
        call_to_action="Reply with your OS and the AI coding tools you already use; I will quote the CLI plus agent-bus setup.",
    ),
    Offer(
        offer_id="ai_workflow_audit_sprint",
        title="AI Workflow Audit Sprint",
        buyer="people paying for multiple AI tools but lacking a reliable daily workflow",
        price_floor_usd=100,
        price_anchor_usd=300,
        promise="Find waste, fragile steps, and missing handoffs in an AI tool stack, then produce a usable repair plan.",
        deliverables=[
            "Inventory current tools, scripts, datasets, and failure points.",
            "Flag what should be automated, deleted, preserved, or moved.",
            "Deliver a prioritized 7-day repair checklist.",
        ],
        proof_paths=[
            "scripts/revenue/daily_autopilot.py",
            "scripts/system/sell_from_terminal.py",
            "scripts/system/monetization_swarm_status.py",
            "docs/business/GTM_PLAYBOOK.md",
        ],
        call_to_action="Send me the tools you use and one repeated workflow that keeps breaking.",
    ),
    Offer(
        offer_id="research_packet_cleanup",
        title="Research and Patent Packet Cleanup",
        buyer="builders with messy AI/research/provisional notes who need a clean private packet",
        price_floor_usd=200,
        price_anchor_usd=750,
        promise="Turn scattered notes and artifacts into a private, dated, source-linked evidence packet.",
        deliverables=[
            "Separate private material from open-source repo paths.",
            "Create a dated tracker and source map.",
            "Write next-deadline and missing-piece checklist.",
        ],
        proof_paths=[
            "docs/legal/patent_63_961_403_nonprovisional",
            "docs/specs/PATENT_63_961_403_SUPPORT_MATRIX.md",
            "docs/specs/PATENT_63_961_403_FILING_PREP.md",
        ],
        call_to_action="Send the folder names and deadline; I will produce the first cleanup map.",
    ),
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _path_status(paths: Iterable[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for raw in paths:
        path = REPO_ROOT / raw
        rows.append(
            {
                "path": raw,
                "exists": path.exists(),
                "kind": "dir" if path.is_dir() else "file" if path.is_file() else "missing",
            }
        )
    return rows


def _run_quick(cmd: list[str], timeout: int = 12) -> dict[str, object]:
    resolved_cmd = list(cmd)
    if resolved_cmd:
        exe = shutil.which(resolved_cmd[0])
        if exe:
            resolved_cmd[0] = exe
    try:
        proc = subprocess.run(
            resolved_cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - exact OS failures vary
        return {"command": cmd, "resolved_command": resolved_cmd, "returncode": -1, "error": str(exc)}
    return {
        "command": cmd,
        "resolved_command": resolved_cmd,
        "returncode": proc.returncode,
        "stdout_excerpt": (proc.stdout or "").strip()[:500],
        "stderr_excerpt": (proc.stderr or "").strip()[:500],
    }


def _proof_snapshot() -> dict[str, object]:
    checks = [
        ["python", "-m", "py_compile", "scripts/revenue/daily_cash_sprint.py"],
    ]
    if (REPO_ROOT / "bin" / "geoseal.cjs").exists():
        checks.append(["node", "-c", "bin/geoseal.cjs"])
    return {"checks": [_run_quick(cmd) for cmd in checks]}


def _dispatch_bus_task(prompt: str, *, task_id: str, dry_run: bool = False) -> dict[str, object]:
    """Route one real task through the local HYDRA free-LLM bus."""

    try:
        raw_keys = os.getenv("SCBE_API_KEYS", "").strip()
        if raw_keys:
            try:
                json.loads(raw_keys)
            except json.JSONDecodeError:
                os.environ.pop("SCBE_API_KEYS", None)
        os.environ.setdefault("SCBE_ALLOW_DEMO_KEYS", "1")
        os.environ.setdefault("SCBE_ENV", "test")

        from src.api import free_llm_routes

        response = free_llm_routes.dispatch_free_llm_request(
            free_llm_routes.FreeLLMDispatchRequest(
                provider="offline",
                prompt=prompt,
                dry_run=dry_run,
                metadata={"task_id": task_id, "lane": "daily_cash_sprint"},
            ),
            user="cash-sprint",
            origin="inside",
        )
        data = response["data"]
        event = data["bus_event"]
        return {
            "status": "ok",
            "route": data.get("route", {}),
            "event_id": event.get("event_id"),
            "prompt_sha256": event.get("prompt", {}).get("sha256"),
            "result_sha256": event.get("result", {}).get("text_sha256"),
            "finish_reason": (data.get("result") or {}).get("finish_reason"),
        }
    except Exception as exc:  # pragma: no cover - exact local provider failures vary
        return {"status": "error", "error": str(exc)[:500]}


def _select_offer(offer_id: str) -> Offer:
    if offer_id == "rotate":
        day_index = datetime.now().timetuple().tm_yday % len(DEFAULT_OFFERS)
        return DEFAULT_OFFERS[day_index]
    for offer in DEFAULT_OFFERS:
        if offer.offer_id == offer_id:
            return offer
    valid = ", ".join(offer.offer_id for offer in DEFAULT_OFFERS)
    raise SystemExit(f"unknown offer_id={offer_id!r}; valid: rotate, {valid}")


def _build_outreach(offer: Offer) -> list[dict[str, str]]:
    base = (
        f"I am offering a small {offer.title} sprint (${offer.price_floor_usd}-${offer.price_anchor_usd}). "
        f"{offer.promise} {offer.call_to_action}"
    )
    return [
        {
            "channel": "dm_short",
            "text": base,
        },
        {
            "channel": "email",
            "subject": f"{offer.title} - small fixed-scope setup",
            "text": (
                f"Hi,\n\n"
                f"I am running a fixed-scope {offer.title} sprint for {offer.buyer}.\n\n"
                f"Result: {offer.promise}\n\n"
                f"Includes:\n"
                + "\n".join(f"- {item}" for item in offer.deliverables)
                + f"\n\nPrice: ${offer.price_floor_usd}-${offer.price_anchor_usd}, depending on scope.\n"
                f"{offer.call_to_action}\n\n"
                f"- Issac"
            ),
        },
        {
            "channel": "post",
            "text": (
                f"I am opening a few fixed-scope {offer.title} slots this week. "
                f"Built for {offer.buyer}. {offer.promise} "
                f"Starting at ${offer.price_floor_usd}. {offer.call_to_action}"
            ),
        },
    ]


def _markdown(report: dict[str, object]) -> str:
    offer = report["offer"]
    assert isinstance(offer, dict)
    lines = [
        f"# SCBE Daily Cash Sprint - {report['date']}",
        "",
        f"Budget: {report['minutes']} minutes.",
        "",
        "## Offer",
        f"- ID: `{offer['offer_id']}`",
        f"- Title: {offer['title']}",
        f"- Buyer: {offer['buyer']}",
        f"- Price: ${offer['price_floor_usd']}-${offer['price_anchor_usd']}",
        f"- Promise: {offer['promise']}",
        "",
        "## 20-Minute Loop",
        "- 0-3 min: read this packet and pick one channel.",
        "- 3-8 min: send the short DM to 5 people or communities.",
        "- 8-14 min: send the email version to 2 higher-fit leads.",
        "- 14-18 min: post the public version once.",
        "- 18-20 min: log replies, blockers, and tomorrow's adjustment.",
        "",
        "## Proof Paths",
    ]
    for row in report["proof_paths"]:
        assert isinstance(row, dict)
        marker = "ok" if row["exists"] else "missing"
        lines.append(f"- [{marker}] `{row['path']}` ({row['kind']})")
    lines.extend(["", "## Outreach Drafts"])
    for draft in report["outreach_drafts"]:
        assert isinstance(draft, dict)
        lines.extend(["", f"### {draft['channel']}", "```text", draft["text"], "```"])
    lines.extend(["", "## Verification"])
    snapshot = report["proof_snapshot"]
    assert isinstance(snapshot, dict)
    for check in snapshot["checks"]:
        assert isinstance(check, dict)
        lines.append(f"- `{ ' '.join(check['command']) }` -> {check['returncode']}")
    return "\n".join(lines) + "\n"


def generate_packet(*, offer_id: str, minutes: int, out_root: Path = OUT_ROOT) -> dict[str, Path]:
    offer = _select_offer(offer_id)
    date = datetime.now().strftime("%Y-%m-%d")
    out_dir = out_root / date
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "generated_at_utc": _now_utc(),
        "date": date,
        "minutes": minutes,
        "offer": asdict(offer),
        "proof_paths": _path_status(offer.proof_paths),
        "proof_snapshot": _proof_snapshot(),
        "outreach_drafts": _build_outreach(offer),
        "send_goal": {"dm": 5, "email": 2, "public_post": 1},
        "success_metric": "one reply, one scheduled call, or one paid setup request",
    }

    json_path = out_dir / "daily_cash_sprint.json"
    md_path = out_dir / "daily_cash_sprint.md"
    queue_path = out_dir / "outreach_queue.jsonl"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    queue_path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in report["outreach_drafts"]),
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": md_path, "queue": queue_path}


def _task(task_id: str, kind: str, label: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "task_id": task_id,
        "kind": kind,
        "label": label,
        "state": "PENDING",
        "attempts": 0,
        "payload": payload,
        "history": [],
    }


def _initial_state(*, offer_id: str, minutes: int, out_root: Path) -> dict[str, object]:
    return {
        "version": "scbe-daily-cash-continuous-state-v1",
        "created_at_utc": _now_utc(),
        "updated_at_utc": _now_utc(),
        "offer_id": offer_id,
        "minutes": minutes,
        "out_root": str(out_root),
        "cycle_index": 0,
        "cycle_history": [],
        "cursor": 0,
        "completed_count": 0,
        "blocked_count": 0,
        "tasks": [
            _task(
                "generate_packet",
                "packet",
                "Generate today's GeoSeal CLI agent-bus cash packet.",
                {"offer_id": offer_id, "minutes": minutes},
            ),
            _task(
                "bus_publish_readiness",
                "bus_dispatch",
                "Route GeoSeal publish-readiness through the agent bus.",
                {
                    "prompt": (
                        "Inspect GeoSeal CLI publish readiness: verify bin/geoseal.cjs, "
                        "src/geoseal_cli.py, package.json bin mapping, npm pack guard, "
                        "free/local agent bus smoke tests, and the generated cash sprint packet. "
                        "Return blockers only."
                    )
                },
            ),
            _task(
                "publish_guard",
                "command",
                "Run npm package guard for GeoSeal CLI publish readiness.",
                {"command": ["npm", "run", "publish:check:strict"], "timeout": 300},
            ),
            _task(
                "bus_dm_short",
                "queue_bus_dispatch",
                "Route the short outreach item through the bus.",
                {"channel": "dm_short"},
            ),
            _task(
                "bus_email",
                "queue_bus_dispatch",
                "Route the email outreach item through the bus.",
                {"channel": "email"},
            ),
            _task(
                "bus_post",
                "queue_bus_dispatch",
                "Route the public post item through the bus.",
                {"channel": "post"},
            ),
        ],
    }


def _load_or_create_state(
    *, state_path: Path, offer_id: str, minutes: int, out_root: Path, reset: bool
) -> dict[str, object]:
    if state_path.exists() and not reset:
        return json.loads(state_path.read_text(encoding="utf-8"))
    state = _initial_state(offer_id=offer_id, minutes=minutes, out_root=out_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def _write_state(state_path: Path, state: dict[str, object]) -> None:
    state["updated_at_utc"] = _now_utc()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _cycle_state(state: dict[str, object], *, offer_id: str, minutes: int, out_root: Path) -> dict[str, object]:
    tasks = state.get("tasks", [])
    assert isinstance(tasks, list)
    cycle_history = state.setdefault("cycle_history", [])
    assert isinstance(cycle_history, list)
    cycle_history.append(
        {
            "cycle_index": int(state.get("cycle_index", 0)),
            "closed_at_utc": _now_utc(),
            "completed_count": sum(1 for task in tasks if task.get("state") == "DONE"),
            "blocked_count": sum(1 for task in tasks if task.get("state") == "BLOCKED"),
        }
    )
    next_state = _initial_state(offer_id=offer_id, minutes=minutes, out_root=out_root)
    next_state["cycle_index"] = int(state.get("cycle_index", 0)) + 1
    next_state["cycle_history"] = cycle_history[-25:]
    return next_state


def _record(task: dict[str, object], state: StateName, result: dict[str, object]) -> None:
    task["state"] = state
    task["attempts"] = int(task.get("attempts", 0)) + 1
    history = task.setdefault("history", [])
    assert isinstance(history, list)
    history.append({"at_utc": _now_utc(), "state": state, "result": result})


def _read_queue_item(paths: dict[str, Path], channel: str) -> dict[str, object]:
    if not paths["queue"].exists():
        raise RuntimeError("outreach queue missing; run generate_packet first")
    for line in paths["queue"].read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("channel") == channel:
            return row
    raise RuntimeError(f"queue channel not found: {channel}")


def _latest_packet_paths(out_root: Path) -> dict[str, Path]:
    date = datetime.now().strftime("%Y-%m-%d")
    out_dir = out_root / date
    return {
        "json": out_dir / "daily_cash_sprint.json",
        "markdown": out_dir / "daily_cash_sprint.md",
        "queue": out_dir / "outreach_queue.jsonl",
    }


def _run_task(task: dict[str, object], *, offer_id: str, minutes: int, out_root: Path) -> tuple[StateName, dict[str, object]]:
    kind = str(task["kind"])
    payload = task.get("payload", {})
    assert isinstance(payload, dict)
    if kind == "packet":
        paths = generate_packet(offer_id=offer_id, minutes=minutes, out_root=out_root)
        return "DONE", {name: _safe_rel(path) for name, path in paths.items()}
    if kind == "bus_dispatch":
        result = _dispatch_bus_task(str(payload["prompt"]), task_id=str(task["task_id"]))
        return ("DONE" if result.get("status") == "ok" else "BLOCKED"), result
    if kind == "command":
        result = _run_quick(list(payload["command"]), timeout=int(payload.get("timeout", 120)))
        return ("DONE" if result.get("returncode") == 0 else "BLOCKED"), result
    if kind == "queue_bus_dispatch":
        paths = _latest_packet_paths(out_root)
        row = _read_queue_item(paths, str(payload["channel"]))
        prompt = (
            f"Prepare this {row['channel']} item for a GeoSeal CLI Agent Bus Setup action. "
            f"Do not send it. Return one improvement or 'ready'.\n\n{row['text']}"
        )
        result = _dispatch_bus_task(prompt, task_id=str(task["task_id"]))
        return ("DONE" if result.get("status") == "ok" else "BLOCKED"), result
    return "BLOCKED", {"error": f"unknown task kind: {kind}"}


def run_continuous(
    *,
    offer_id: str,
    minutes: int,
    out_root: Path,
    state_path: Path,
    max_steps: int,
    reset: bool = False,
    cycle_when_complete: bool = False,
) -> dict[str, object]:
    state = _load_or_create_state(
        state_path=state_path,
        offer_id=offer_id,
        minutes=minutes,
        out_root=out_root,
        reset=reset,
    )
    tasks = state["tasks"]
    assert isinstance(tasks, list)
    steps: list[dict[str, object]] = []
    for _ in range(max_steps):
        next_task = next((task for task in tasks if task.get("state") == "PENDING"), None)
        if not next_task:
            if cycle_when_complete and not any(task.get("state") == "BLOCKED" for task in tasks):
                state = _cycle_state(state, offer_id=offer_id, minutes=minutes, out_root=out_root)
                tasks = state["tasks"]
                assert isinstance(tasks, list)
                _write_state(state_path, state)
                next_task = next((task for task in tasks if task.get("state") == "PENDING"), None)
            if not next_task:
                break
        next_task["state"] = "RUNNING"
        _write_state(state_path, state)
        final_state, result = _run_task(next_task, offer_id=offer_id, minutes=minutes, out_root=out_root)
        _record(next_task, final_state, result)
        steps.append({"task_id": next_task["task_id"], "state": final_state, "result": result})
        if final_state == "BLOCKED":
            break
        _write_state(state_path, state)

    state["completed_count"] = sum(1 for task in tasks if task.get("state") == "DONE")
    state["blocked_count"] = sum(1 for task in tasks if task.get("state") == "BLOCKED")
    state["cursor"] = state["completed_count"]
    _write_state(state_path, state)
    return {
        "state_path": _safe_rel(state_path),
        "cycle_index": state.get("cycle_index", 0),
        "completed_count": state["completed_count"],
        "blocked_count": state["blocked_count"],
        "remaining_count": sum(1 for task in tasks if task.get("state") == "PENDING"),
        "steps": steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the daily 20-minute SCBE cash sprint packet.")
    parser.add_argument("--offer", default="rotate", help="Offer ID to use, or 'rotate'.")
    parser.add_argument("--minutes", type=int, default=20, help="Execution budget in minutes.")
    parser.add_argument("--out-root", default=str(OUT_ROOT), help="Output directory root.")
    parser.add_argument("--continuous", action="store_true", help="Run the next stateful task instead of stopping at packet generation.")
    parser.add_argument("--max-steps", type=int, default=1, help="Maximum continuous tasks to advance this invocation.")
    parser.add_argument("--reset-state", action="store_true", help="Start the continuous state machine over.")
    parser.add_argument(
        "--cycle-when-complete",
        action="store_true",
        help="When all tasks are done, start the next cycle instead of stopping.",
    )
    parser.add_argument(
        "--state-path",
        default=str(OUT_ROOT / "continuous_state.json"),
        help="Persistent continuous state file.",
    )
    args = parser.parse_args()
    out_root = Path(args.out_root)
    if args.continuous:
        result = run_continuous(
            offer_id=args.offer,
            minutes=args.minutes,
            out_root=out_root,
            state_path=Path(args.state_path),
            max_steps=args.max_steps,
            reset=args.reset_state,
            cycle_when_complete=args.cycle_when_complete,
        )
        print(json.dumps(result, indent=2))
        return 1 if int(result["blocked_count"]) else 0
    paths = generate_packet(offer_id=args.offer, minutes=args.minutes, out_root=out_root)
    for name, path in paths.items():
        print(f"{name}={_safe_rel(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
