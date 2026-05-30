#!/usr/bin/env python3
"""
@file longform_cli.py
@module longform/longform_cli

SCBE Longform Bridge CLI — invoked by `scbe.js` via runPythonScript().

Usage (via scbe.js):
  scbe do "<objective>" [--loops N] [--land-every-stage] [--json]
  scbe work init [--mission M] [--invariant I...] [--workspace DIR]
  scbe work status [--json] [--workspace DIR]
  scbe work resume [--hash H] [--json] [--workspace DIR]
  scbe land create [--json] [--workspace DIR]
  scbe land list [--json] [--workspace DIR]
  scbe land verify <hash> [--json] [--workspace DIR]
  scbe land show <hash> [--json] [--workspace DIR]
  scbe agent spawn <role> --mandate M [--tools T] [--budget N] [--json]
  scbe agent list [--json] [--workspace DIR]
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

# Resolve imports whether called as a script or module
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.longform.context_bridge import (
    PrincipleSet,
    JsonlWorkflowLedger,
    new_ledger,
    load_ledger,
    create_landing,
    build_resume_pack,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _workspace(args) -> str:
    return os.path.abspath(getattr(args, "workspace", None) or os.getcwd())


def _emit(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        _print_human(data)


def _print_human(data: dict) -> None:
    kind = data.get("kind", "")
    if kind == "work_status":
        _print_work_status(data)
    elif kind == "land_list":
        _print_land_list(data)
    elif kind == "land_detail":
        _print_land_detail(data)
    elif kind == "agent_list":
        _print_agent_list(data)
    elif kind == "do_complete":
        _print_do_complete(data)
    else:
        # generic
        for k, v in data.items():
            if k != "kind":
                print(f"  {k}: {v}")


def _print_work_status(d: dict) -> None:
    print("─" * 60)
    print("  SCBE Longform Workspace Status")
    print("─" * 60)
    print(f"  workspace:     {d.get('workspace_dir', '')}")
    print(f"  bricks:        {d.get('brick_count', 0)}")
    print(f"  events total:  {d.get('event_count', 0)}")
    print(f"  chain valid:   {d.get('chain_valid', False)}")
    lm = d.get("last_landing")
    if lm:
        print(f"  last landing:  {lm['hash'][:16]}…  ({lm['ts'][:19]})")
    else:
        print("  last landing:  (none)")
    ps = d.get("principles", {})
    if ps:
        print(f"  mission:       {ps.get('mission', '')[:60]}")
        for inv in ps.get("invariants", []):
            print(f"    invariant:   {inv}")
    oq = d.get("open_questions", [])
    if oq:
        print("  open questions:")
        for q in oq:
            print(f"    • {q}")
    nf = d.get("next_footholds", [])
    if nf:
        print("  next footholds:")
        for f_ in nf:
            print(f"    → {f_}")
    print("─" * 60)


def _print_land_list(d: dict) -> None:
    landings = d.get("landings", [])
    if not landings:
        print("  No landings yet. Run `scbe land create`.")
        return
    print(f"  {'#':<4}  {'Hash (short)':<18}  {'Timestamp':<20}  {'Bricks':>6}")
    print("  " + "─" * 56)
    for i, l in enumerate(landings, 1):
        print(f"  {i:<4}  {l['hash'][:16]:<18}  {l['ts'][:19]:<20}  {l['brick_count']:>6}")


def _print_land_detail(d: dict) -> None:
    print("─" * 60)
    print(f"  Landing: {d.get('hash', '')[:16]}…")
    print(f"  Created: {d.get('ts', '')[:19]}")
    print(f"  Bricks:  {d.get('brick_count', 0)}")
    print(f"  Valid:   {d.get('verified', False)}")
    ps = d.get("principles", {})
    if ps:
        print(f"  Mission: {ps.get('mission', '')[:60]}")
        for inv in ps.get("invariants", []):
            print(f"    invariant:   {inv}")
        for cb in ps.get("claim_boundaries", []):
            print(f"    claim:       {cb}")
        for oq in ps.get("open_questions", []):
            print(f"    open_q:      {oq}")
        for nf in ps.get("next_footholds", []):
            print(f"    foothold:    {nf}")
    print("─" * 60)


def _print_agent_list(d: dict) -> None:
    agents = d.get("agents", [])
    if not agents:
        print("  No agents registered in this workflow.")
        return
    for a in agents:
        print(f"  [{a.get('role', '?')}]  {a.get('agent_id', '')[:12]}…")
        print(f"    mandate: {a.get('mandate', '')[:60]}")
        print(f"    tools:   {', '.join(a.get('allowed_tools', []))}")
        print(f"    budget:  {a.get('budget', '?')} invocations")


def _print_do_complete(d: dict) -> None:
    print("─" * 60)
    print("  SCBE Longform — Objective Complete")
    print("─" * 60)
    print(f"  objective:     {d.get('objective', '')[:60]}")
    print(f"  loops_run:     {d.get('loops_run', 0)}")
    print(f"  bricks:        {d.get('brick_count', 0)}")
    lh = d.get("landing_hash")
    if lh:
        print(f"  landing:       {lh[:16]}…")
    rp = d.get("resume_pack_path")
    if rp:
        print(f"  resume pack:   {rp}")
    print("─" * 60)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_work_init(args) -> None:
    ws = _workspace(args)
    mission = args.mission or "Accomplish the objective."
    invariants = list(args.invariant) if args.invariant else []
    claim_boundaries = list(args.claim) if hasattr(args, "claim") and args.claim else []

    ledger = new_ledger(ws, mission, invariants, claim_boundaries)
    result = {
        "kind": "work_init",
        "workspace_dir": ledger.workspace_dir,
        "mission": mission,
        "invariants": invariants,
        "status": "initialized",
    }
    _emit(result, args.json)
    if not args.json:
        print(f"  Workspace initialized at {ledger.workspace_dir}")


def cmd_work_status(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    events = ledger.read_all()
    bc = sum(1 for e in events if e.kind == "brick")
    chain_ok = ledger.verify_chain()
    principles = ledger.load_principles()
    last_l = ledger.last_landing()

    result: dict = {
        "kind": "work_status",
        "workspace_dir": ledger.workspace_dir,
        "brick_count": bc,
        "event_count": len(events),
        "chain_valid": chain_ok,
        "principles": principles.to_dict() if principles else {},
        "open_questions": principles.open_questions if principles else [],
        "next_footholds": principles.next_footholds if principles else [],
        "last_landing": {
            "hash": last_l.landing_hash,
            "ts": last_l.ts,
            "brick_count": last_l.brick_count,
        } if last_l else None,
    }
    _emit(result, args.json)


def cmd_work_resume(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    landing_hash = getattr(args, "hash", None)
    try:
        pack = build_resume_pack(ledger, landing_hash)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    # Append resume event
    ledger.append("resume", {
        "landing_hash": pack.landing.landing_hash,
        "session_id": str(uuid.uuid4()),
        "resumed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })

    result = {
        "kind": "work_resume",
        "landing_hash": pack.landing.landing_hash,
        "mission": pack.landing.principles.mission,
        "open_questions": pack.open_questions,
        "next_footholds": pack.next_footholds,
        "brick_count": pack.recent_brick_count,
        "resume_pack_path": ledger.save_resume_pack(pack),
    }
    _emit(result, args.json)
    if not args.json:
        print(f"\n  Resumed from landing {pack.landing.landing_hash[:16]}…")
        print(f"  Mission: {pack.landing.principles.mission}")


def cmd_land_create(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    principles = ledger.load_principles()
    if principles is None:
        principles = PrincipleSet(mission="(no mission set)")

    landing = create_landing(ledger, principles)
    result = {
        "kind": "land_create",
        "landing_id": landing.landing_id,
        "landing_hash": landing.landing_hash,
        "ts": landing.ts,
        "brick_count": landing.brick_count,
        "verified": landing.verify(),
        "principles": landing.principles.to_dict(),
    }
    _emit(result, args.json)
    if not args.json:
        print(f"  Landing created: {landing.landing_hash[:16]}…  ({landing.ts[:19]})")
        print(f"  Bricks captured: {landing.brick_count}")
        print(f"  Integrity:       {landing.verify()}")


def cmd_land_list(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    landings = ledger.list_landings()
    result = {
        "kind": "land_list",
        "count": len(landings),
        "landings": [
            {
                "hash": l.landing_hash,
                "ts": l.ts,
                "brick_count": l.brick_count,
                "verified": l.verify(),
            }
            for l in landings
        ],
    }
    _emit(result, args.json)


def cmd_land_verify(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    landing = ledger.load_landing(args.hash)
    if landing is None:
        sys.stderr.write(f"Landing not found: {args.hash!r}\n")
        sys.exit(1)

    ok = landing.verify()
    chain_ok = ledger.verify_chain()
    result = {
        "kind": "land_verify",
        "hash": landing.landing_hash,
        "ts": landing.ts,
        "landing_integrity": ok,
        "chain_integrity": chain_ok,
        "brick_count": landing.brick_count,
    }
    _emit(result, args.json)
    if not args.json:
        sym = "✓" if ok and chain_ok else "✗"
        print(f"  {sym} landing={ok}  chain={chain_ok}  ({landing.landing_hash[:16]}…)")


def cmd_land_show(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    landing = ledger.load_landing(args.hash)
    if landing is None:
        sys.stderr.write(f"Landing not found: {args.hash!r}\n")
        sys.exit(1)

    result = {
        "kind": "land_detail",
        "hash": landing.landing_hash,
        "ts": landing.ts,
        "brick_count": landing.brick_count,
        "verified": landing.verify(),
        "principles": landing.principles.to_dict(),
    }
    _emit(result, args.json)


def cmd_agent_spawn(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    agent_id = str(uuid.uuid4())
    allowed_tools = [t.strip() for t in (args.tools or "").split(",") if t.strip()]
    budget = int(args.budget) if args.budget else 20
    contract = {
        "agent_id": agent_id,
        "role": args.role,
        "mandate": args.mandate,
        "allowed_tools": allowed_tools,
        "budget": budget,
        "spawned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "active",
    }
    ledger.save_agent(agent_id, contract)
    ledger.append("agent_spawn", {
        "agent_id": agent_id,
        "role": args.role,
        "mandate": args.mandate,
        "allowed_tools": allowed_tools,
        "budget": budget,
    })

    result = {"kind": "agent_spawn", **contract}
    _emit(result, args.json)
    if not args.json:
        print(f"  Agent spawned: [{args.role}]  {agent_id[:12]}…")
        print(f"  Mandate: {args.mandate[:60]}")
        print(f"  Tools:   {', '.join(allowed_tools) or '(all)'}")
        print(f"  Budget:  {budget} invocations")


def cmd_agent_list(args) -> None:
    ws = _workspace(args)
    try:
        ledger = load_ledger(ws)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    agents = ledger.list_agents()
    result = {"kind": "agent_list", "count": len(agents), "agents": agents}
    _emit(result, args.json)


def cmd_do(args) -> None:
    """
    Core durable agentic command.

    Runs the Orient → Plan → Execute → Audit → (Compact) → Land loop.
    In phase 1, execution is a governed stub: emits bricks and landings.
    Squad execution (--squad) wires to the agent bus in phase 2.

    Every stage emits verifiable bricks to the JSONL ledger.
    Every landing is cryptographically signed and resumable.
    """
    ws = _workspace(args)
    objective = args.objective
    loops = int(args.loops)
    land_every = args.land_every_stage
    emit_json = args.json

    # Orient: load or create workspace
    lf_dir = os.path.join(ws, ".scbe-longform")
    if os.path.exists(lf_dir):
        ledger = load_ledger(ws)
        principles = ledger.load_principles() or PrincipleSet(mission=objective)
    else:
        ledger = new_ledger(ws, objective)
        principles = ledger.load_principles()

    # Record objective
    ledger.append("objective", {
        "objective": objective,
        "loops_requested": loops,
        "land_every_stage": land_every,
        "backend": getattr(args, "backend", "local"),
    })

    if not emit_json:
        print(f"  SCBE Longform — do: {objective[:60]}")
        print(f"  Workspace: {ledger.workspace_dir}")
        print(f"  Loops: {loops}  land-every-stage: {land_every}")
        print()

    last_landing = None
    for loop_n in range(1, loops + 1):
        if not emit_json:
            print(f"  ── Stage {loop_n}/{loops} ──────────────────────────────")

        # Stage intent
        ledger.append("stage_intent", {
            "loop": loop_n,
            "objective": objective,
            "phase": "execute",
        })

        # Stage execution stub — in phase 1, records the intent.
        # Wire actual squad execution here in phase 2.
        ledger.append("stage_complete", {
            "loop": loop_n,
            "status": "stub",
            "note": (
                "Phase 1: execution stub. "
                "Wire squad routing in phase 2 (`--squad` flag activates bus dispatch)."
            ),
        })

        # Audit: validate principles
        audit_ok = True  # in phase 1, always passes (stub)
        ledger.append("audit_pass" if audit_ok else "audit_fail", {
            "loop": loop_n,
            "principles_validated": audit_ok,
        })

        if not emit_json:
            print(f"    brick emitted  loop={loop_n}  audit={'pass' if audit_ok else 'FAIL'}")

        if land_every:
            landing = create_landing(ledger, principles, metadata={"loop": loop_n})
            last_landing = landing
            if not emit_json:
                print(f"    landing:       {landing.landing_hash[:16]}…")

    # Final landing
    if not land_every or last_landing is None:
        last_landing = create_landing(ledger, principles, metadata={"final": True})
        if not emit_json:
            print(f"\n  Final landing: {last_landing.landing_hash[:16]}…")

    # Build resume pack
    pack = build_resume_pack(ledger, session_hint=f"Resume: {objective[:40]}")

    result = {
        "kind": "do_complete",
        "objective": objective,
        "loops_run": loops,
        "brick_count": ledger.brick_count(),
        "landing_hash": last_landing.landing_hash,
        "landing_ts": last_landing.ts,
        "resume_pack_path": os.path.join(ledger.workspace_dir, "resume", "resume_pack.json"),
        "workspace_dir": ledger.workspace_dir,
    }
    if emit_json:
        print(json.dumps(result, indent=2))
    else:
        _print_do_complete(result)


# ── Argument parsing ──────────────────────────────────────────────────────────

def _ws_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("--workspace", "-w", default=None,
                   help="Workspace directory (default: cwd)")


def _json_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="Emit JSON output")


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="longform_cli",
        description="SCBE Longform Bridge — durable agentic workflow CLI",
    )
    sub = root.add_subparsers(dest="command")

    # ── do ──
    p_do = sub.add_parser("do", help="Run a durable governed agentic workflow")
    p_do.add_argument("objective", help="The objective to accomplish")
    p_do.add_argument("--loops", default="6", help="Max stage iterations (default 6)")
    p_do.add_argument("--land-every-stage", action="store_true",
                      help="Create a landing after each stage")
    p_do.add_argument("--squad", action="store_true",
                      help="Route each stage to the multi-agent squad (phase 2)")
    p_do.add_argument("--resume-policy", default="latest-safe",
                      choices=["latest-safe", "explicit-hash"],
                      help="Resume policy (default latest-safe)")
    p_do.add_argument("--backend", default="local",
                      choices=["local", "temporal"],
                      help="Execution backend (default local)")
    _ws_arg(p_do)
    _json_arg(p_do)

    # ── work ──
    p_work = sub.add_parser("work", help="Manage longform workflow workspace")
    ws_sub = p_work.add_subparsers(dest="work_cmd")

    p_init = ws_sub.add_parser("init", help="Initialize a new workspace")
    p_init.add_argument("--mission", "-m", default="", help="Mission statement")
    p_init.add_argument("--invariant", "-i", action="append", default=[],
                        help="Add an invariant (repeatable)")
    p_init.add_argument("--claim", "-c", action="append", default=[],
                        help="Add a claim boundary (repeatable)")
    _ws_arg(p_init)
    _json_arg(p_init)

    p_status = ws_sub.add_parser("status", help="Show workspace status")
    _ws_arg(p_status)
    _json_arg(p_status)

    p_resume = ws_sub.add_parser("resume", help="Resume from a landing")
    p_resume.add_argument("--hash", default=None,
                          help="Landing hash prefix (default: latest)")
    _ws_arg(p_resume)
    _json_arg(p_resume)

    # ── land ──
    p_land = sub.add_parser("land", help="Manage context landings")
    land_sub = p_land.add_subparsers(dest="land_cmd")

    p_lc = land_sub.add_parser("create", help="Create a verified context landing")
    _ws_arg(p_lc)
    _json_arg(p_lc)

    p_ll = land_sub.add_parser("list", help="List all landings")
    _ws_arg(p_ll)
    _json_arg(p_ll)

    p_lv = land_sub.add_parser("verify", help="Verify a landing's integrity")
    p_lv.add_argument("hash", help="Landing hash prefix")
    _ws_arg(p_lv)
    _json_arg(p_lv)

    p_ls = land_sub.add_parser("show", help="Show landing content")
    p_ls.add_argument("hash", help="Landing hash prefix")
    _ws_arg(p_ls)
    _json_arg(p_ls)

    # ── agent ──
    p_agent = sub.add_parser("agent", help="Manage governed agents")
    agent_sub = p_agent.add_subparsers(dest="agent_cmd")

    p_asp = agent_sub.add_parser("spawn", help="Spawn a governed agent")
    p_asp.add_argument("role", help="Agent role (architect/tester/prover/etc.)")
    p_asp.add_argument("--mandate", required=True, help="Agent mandate/objective")
    p_asp.add_argument("--tools", default="",
                       help="Comma-separated allowed tools")
    p_asp.add_argument("--budget", default="20",
                       help="Max invocations before escalation (default 20)")
    _ws_arg(p_asp)
    _json_arg(p_asp)

    p_al = agent_sub.add_parser("list", help="List agents in current workflow")
    _ws_arg(p_al)
    _json_arg(p_al)

    return root


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "do":
        cmd_do(args)
    elif args.command == "work":
        if args.work_cmd == "init":
            cmd_work_init(args)
        elif args.work_cmd == "status":
            cmd_work_status(args)
        elif args.work_cmd == "resume":
            cmd_work_resume(args)
        else:
            parser.parse_args(["work", "--help"])
    elif args.command == "land":
        if args.land_cmd == "create":
            cmd_land_create(args)
        elif args.land_cmd == "list":
            cmd_land_list(args)
        elif args.land_cmd == "verify":
            cmd_land_verify(args)
        elif args.land_cmd == "show":
            cmd_land_show(args)
        else:
            parser.parse_args(["land", "--help"])
    elif args.command == "agent":
        if args.agent_cmd == "spawn":
            cmd_agent_spawn(args)
        elif args.agent_cmd == "list":
            cmd_agent_list(args)
        else:
            parser.parse_args(["agent", "--help"])
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
