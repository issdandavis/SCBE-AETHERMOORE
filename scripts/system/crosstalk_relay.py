#!/usr/bin/env python3
"""
Cross-Talk Relay — Reliable multi-lane AI-to-AI packet delivery.

Guarantees:
  1. Atomic emission: packet lands on ALL lanes or reports partial failure
  2. Delivery verification: check that a packet exists on each lane
  3. Consumption ACK: receiving agent marks packets as consumed
  4. Health report: shows lane status, pending packets, stale deliveries

Usage:
  # Emit a packet (from any agent)
  python scripts/system/crosstalk_relay.py emit \
    --sender agent.claude --recipient agent.codex \
    --intent sync --task-id MY-TASK --summary "Working on X"

  # Verify a packet landed on all lanes
  python scripts/system/crosstalk_relay.py verify --packet-id <id>

  # Mark a packet as consumed (ACK receipt)
  python scripts/system/crosstalk_relay.py ack --packet-id <id> --agent agent.claude

  # Health report
  python scripts/system/crosstalk_relay.py health

  # List pending (unconsumed) packets for an agent
  python scripts/system/crosstalk_relay.py pending --agent agent.claude
"""

import argparse
import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CROSSTALK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
ACK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk_acks.jsonl"
OBSIDIAN_WORKSPACE = Path(
    os.environ.get(
        "OBSIDIAN_WORKSPACE",
        r"C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace",
    )
)
OBSIDIAN_CROSSTALK = OBSIDIAN_WORKSPACE / "Cross Talk.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _safe_token(value: str, fallback: str = "unknown") -> str:
    import re
    token = re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")
    return token or fallback


def _packet_hash(packet: Dict[str, Any]) -> str:
    """Deterministic hash of packet content for integrity checks."""
    canonical = json.dumps(packet, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ── Emission ─────────────────────────────────────────────────────────

def emit_packet(
    sender: str,
    recipient: str,
    intent: str,
    task_id: str,
    summary: str,
    status: str = "in_progress",
    proof: Optional[List[str]] = None,
    next_action: str = "",
    risk: str = "low",
    branch: str = "clean-sync",
    session_id: str = "",
    codename: str = "",
    where: str = "",
    why: str = "",
    how: str = "",
) -> Dict[str, Any]:
    """Emit a cross-talk packet to ALL lanes atomically. Returns delivery report."""

    created_at = _utc_now()
    stamp = _utc_stamp()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_task = _safe_token(task_id, "general")
    safe_sender = _safe_token(sender, "agent")
    packet_id = f"cross-talk-{safe_sender}-{safe_task}-{stamp}"

    packet = {
        "packet_id": packet_id,
        "created_at": created_at,
        "session_id": session_id or f"sess-{day}",
        "codename": codename or safe_sender,
        "sender": sender,
        "recipient": recipient,
        "intent": intent,
        "status": status,
        "repo": "SCBE-AETHERMOORE",
        "branch": branch,
        "task_id": task_id,
        "summary": summary,
        "proof": proof or [],
        "next_action": next_action,
        "risk": risk,
        "where": where,
        "why": why,
        "how": how,
        "gates": {"governance_packet": True, "tests_requested": []},
    }

    integrity_hash = _packet_hash(packet)
    packet["_integrity"] = integrity_hash

    delivery = {"packet_id": packet_id, "lanes": {}}

    # Lane 1: Dated JSON file
    try:
        out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
        out_dir.mkdir(parents=True, exist_ok=True)
        packet_path = out_dir / f"{packet_id}.json"
        packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        delivery["lanes"]["dated_json"] = {"ok": True, "path": str(packet_path)}
    except Exception as e:
        delivery["lanes"]["dated_json"] = {"ok": False, "error": str(e)}

    # Lane 2: JSONL bus
    try:
        CROSSTALK_LANE.parent.mkdir(parents=True, exist_ok=True)
        with CROSSTALK_LANE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(packet) + "\n")
        delivery["lanes"]["jsonl_bus"] = {"ok": True, "path": str(CROSSTALK_LANE)}
    except Exception as e:
        delivery["lanes"]["jsonl_bus"] = {"ok": False, "error": str(e)}

    # Lane 3: Obsidian Cross Talk.md
    try:
        if OBSIDIAN_CROSSTALK.parent.exists():
            agent_short = sender.replace("agent.", "").capitalize()
            obsidian_entry = (
                f"\n## {created_at} | {agent_short} | {task_id}\n\n"
                f"**Status**: {status}\n"
                f"**Intent**: {intent}\n"
                f"**Summary**: {summary}\n"
                f"**Proof**: {', '.join(proof or ['none'])}\n"
                f"**Next**: {next_action or 'none'}\n"
                f"**Integrity**: {integrity_hash}\n"
            )
            with OBSIDIAN_CROSSTALK.open("a", encoding="utf-8") as f:
                f.write(obsidian_entry)
            delivery["lanes"]["obsidian"] = {"ok": True, "path": str(OBSIDIAN_CROSSTALK)}
        else:
            delivery["lanes"]["obsidian"] = {"ok": False, "error": "Obsidian workspace not found"}
    except Exception as e:
        delivery["lanes"]["obsidian"] = {"ok": False, "error": str(e)}

    # Delivery summary
    ok_count = sum(1 for lane in delivery["lanes"].values() if lane.get("ok"))
    total_lanes = len(delivery["lanes"])
    delivery["delivered"] = ok_count
    delivery["total_lanes"] = total_lanes
    delivery["all_delivered"] = ok_count == total_lanes
    delivery["integrity"] = integrity_hash

    return delivery


# ── Verification ─────────────────────────────────────────────────────

def verify_packet(packet_id: str) -> Dict[str, Any]:
    """Verify that a packet exists on all lanes."""
    result: Dict[str, Any] = {"packet_id": packet_id, "lanes": {}}

    # Check dated JSON
    found_json = False
    for day_dir in sorted((REPO_ROOT / "artifacts" / "agent_comm").iterdir(), reverse=True):
        if not day_dir.is_dir() or day_dir.name == "github_lanes":
            continue
        candidate = day_dir / f"{packet_id}.json"
        if candidate.exists():
            found_json = True
            result["lanes"]["dated_json"] = {"ok": True, "path": str(candidate)}
            break
    if not found_json:
        result["lanes"]["dated_json"] = {"ok": False, "error": "Not found"}

    # Check JSONL bus
    found_jsonl = False
    if CROSSTALK_LANE.exists():
        with CROSSTALK_LANE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if row.get("packet_id") == packet_id:
                        found_jsonl = True
                        break
                except json.JSONDecodeError:
                    pass
    result["lanes"]["jsonl_bus"] = {"ok": found_jsonl, "error": "" if found_jsonl else "Not found in bus"}

    # Check Obsidian — look for integrity hash or packet_id
    found_obsidian = False
    if OBSIDIAN_CROSSTALK.exists():
        content = OBSIDIAN_CROSSTALK.read_text(encoding="utf-8")
        # First try packet_id, then try integrity hash from the dated JSON
        if packet_id in content:
            found_obsidian = True
        elif result["lanes"]["dated_json"].get("ok") and result["lanes"]["dated_json"].get("path"):
            try:
                pkt = json.loads(Path(result["lanes"]["dated_json"]["path"]).read_text(encoding="utf-8"))
                integrity = pkt.get("_integrity", "")
                if integrity and integrity in content:
                    found_obsidian = True
            except Exception:
                pass
    result["lanes"]["obsidian"] = {
        "ok": found_obsidian,
        "error": "" if found_obsidian else "Not found in Cross Talk.md",
    }

    ok_count = sum(1 for lane in result["lanes"].values() if lane.get("ok"))
    result["verified_lanes"] = ok_count
    result["total_lanes"] = len(result["lanes"])
    result["fully_verified"] = ok_count == len(result["lanes"])

    return result


# ── Consumption ACK ──────────────────────────────────────────────────

def ack_packet(packet_id: str, agent: str, notes: str = "") -> Dict[str, Any]:
    """Mark a packet as consumed by an agent. Appends to ACK lane."""
    ack_record = {
        "packet_id": packet_id,
        "consumed_by": agent,
        "consumed_at": _utc_now(),
        "notes": notes,
    }

    ACK_LANE.parent.mkdir(parents=True, exist_ok=True)
    with ACK_LANE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ack_record) + "\n")

    return {"ok": True, "ack": ack_record}


def get_acks(packet_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all ACKs, optionally filtered by packet_id."""
    if not ACK_LANE.exists():
        return []
    acks = []
    with ACK_LANE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if packet_id is None or row.get("packet_id") == packet_id:
                    acks.append(row)
            except json.JSONDecodeError:
                pass
    return acks


# ── Pending Packets ──────────────────────────────────────────────────

def pending_for_agent(agent: str, limit: int = 50) -> List[Dict[str, Any]]:
    """List packets addressed to an agent that haven't been ACK'd."""
    if not CROSSTALK_LANE.exists():
        return []

    # Load all ACKs by this agent
    acked_ids = set()
    for ack in get_acks():
        if ack.get("consumed_by") == agent:
            acked_ids.add(ack.get("packet_id"))

    # Find packets addressed to this agent
    pending = []
    with CROSSTALK_LANE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                recipient = row.get("recipient", "")
                pid = row.get("packet_id", "")
                # Check if agent is in recipient list
                if agent in recipient and pid not in acked_ids:
                    pending.append(row)
            except json.JSONDecodeError:
                pass

    # Return latest first, limited
    return list(reversed(pending[-limit:]))


# ── Health Report ────────────────────────────────────────────────────

def health_report() -> Dict[str, Any]:
    """Cross-talk system health report."""
    report: Dict[str, Any] = {"timestamp": _utc_now(), "lanes": {}}

    # JSONL bus stats
    bus_lines = 0
    latest_packet = None
    if CROSSTALK_LANE.exists():
        with CROSSTALK_LANE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                bus_lines += 1
                try:
                    latest_packet = json.loads(line)
                except json.JSONDecodeError:
                    pass
    report["lanes"]["jsonl_bus"] = {
        "exists": CROSSTALK_LANE.exists(),
        "total_packets": bus_lines,
        "latest_at": latest_packet.get("created_at", "") if latest_packet else "",
        "latest_task": latest_packet.get("task_id", "") if latest_packet else "",
    }

    # Dated JSON dirs
    agent_comm = REPO_ROOT / "artifacts" / "agent_comm"
    day_dirs = []
    total_json_packets = 0
    if agent_comm.exists():
        for d in sorted(agent_comm.iterdir(), reverse=True):
            if d.is_dir() and d.name not in ("github_lanes", "aetherbrowse", "biomorphic", "ide_mesh"):
                count = len(list(d.glob("cross-talk-*.json")))
                total_json_packets += count
                day_dirs.append({"date": d.name, "packets": count})
    report["lanes"]["dated_json"] = {
        "total_packets": total_json_packets,
        "recent_days": day_dirs[:7],
    }

    # Obsidian
    report["lanes"]["obsidian"] = {
        "exists": OBSIDIAN_CROSSTALK.exists(),
        "size_bytes": OBSIDIAN_CROSSTALK.stat().st_size if OBSIDIAN_CROSSTALK.exists() else 0,
    }

    # ACK stats
    total_acks = 0
    ack_agents: Dict[str, int] = {}
    if ACK_LANE.exists():
        with ACK_LANE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    total_acks += 1
                    a = row.get("consumed_by", "unknown")
                    ack_agents[a] = ack_agents.get(a, 0) + 1
                except json.JSONDecodeError:
                    pass
    report["acks"] = {
        "total": total_acks,
        "by_agent": ack_agents,
    }

    # Pending per known agent
    known_agents = ["agent.claude", "agent.codex", "agent.gemini", "agent.grok"]
    pending_counts: Dict[str, int] = {}
    for a in known_agents:
        pending_counts[a] = len(pending_for_agent(a))
    report["pending"] = pending_counts

    return report


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cross-Talk Relay — reliable multi-lane AI comms")
    sub = parser.add_subparsers(dest="command")

    # emit
    emit_p = sub.add_parser("emit", help="Emit a cross-talk packet to all lanes")
    emit_p.add_argument("--sender", required=True)
    emit_p.add_argument("--recipient", required=True)
    emit_p.add_argument("--intent", default="sync")
    emit_p.add_argument("--task-id", required=True)
    emit_p.add_argument("--summary", required=True)
    emit_p.add_argument("--status", default="in_progress")
    emit_p.add_argument("--proof", nargs="*", default=[])
    emit_p.add_argument("--next-action", default="")
    emit_p.add_argument("--risk", default="low")
    emit_p.add_argument("--branch", default="clean-sync")
    emit_p.add_argument("--session-id", default="")
    emit_p.add_argument("--codename", default="")
    emit_p.add_argument("--where", default="")
    emit_p.add_argument("--why", default="")
    emit_p.add_argument("--how", default="")

    # verify
    verify_p = sub.add_parser("verify", help="Verify packet on all lanes")
    verify_p.add_argument("--packet-id", required=True)

    # ack
    ack_p = sub.add_parser("ack", help="ACK a packet as consumed")
    ack_p.add_argument("--packet-id", required=True)
    ack_p.add_argument("--agent", required=True)
    ack_p.add_argument("--notes", default="")

    # pending
    pending_p = sub.add_parser("pending", help="List pending packets for an agent")
    pending_p.add_argument("--agent", required=True)
    pending_p.add_argument("--limit", type=int, default=50)

    # health
    sub.add_parser("health", help="Cross-talk system health report")

    args = parser.parse_args()

    if args.command == "emit":
        result = emit_packet(
            sender=args.sender,
            recipient=args.recipient,
            intent=args.intent,
            task_id=args.task_id,
            summary=args.summary,
            status=args.status,
            proof=args.proof,
            next_action=args.next_action,
            risk=args.risk,
            branch=args.branch,
            session_id=args.session_id,
            codename=args.codename,
            where=args.where,
            why=args.why,
            how=args.how,
        )
        print(json.dumps(result, indent=2, default=str))
        if not result["all_delivered"]:
            sys.exit(1)

    elif args.command == "verify":
        result = verify_packet(args.packet_id)
        print(json.dumps(result, indent=2))
        if not result["fully_verified"]:
            sys.exit(1)

    elif args.command == "ack":
        result = ack_packet(args.packet_id, args.agent, args.notes)
        print(json.dumps(result, indent=2))

    elif args.command == "pending":
        items = pending_for_agent(args.agent, args.limit)
        print(json.dumps({"agent": args.agent, "count": len(items), "items": items}, indent=2))

    elif args.command == "health":
        result = health_report()
        print(json.dumps(result, indent=2, default=str))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
