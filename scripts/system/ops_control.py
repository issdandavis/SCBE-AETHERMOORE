#!/usr/bin/env python3
"""
ops_control.py — Unified cross-talk bus for SCBE multi-agent coordination.

Writes packets to all 4 surfaces atomically:
  1. JSON packet  → artifacts/agent_comm/{date}/
  2. JSONL lane   → artifacts/agent_comm/github_lanes/cross_talk.jsonl
  3. Obsidian     → Cross Talk.md (A follder vault)
  4. Agent log    → agents/{agent}.md

Usage:
  python scripts/system/ops_control.py send --from claude --to codex --intent handoff \\
    --status done --summary "Built Kindle APK" --artifacts "kindle-app/package.json" --next "Test on Kindle"

  python scripts/system/ops_control.py ack --packet-id "claude-handoff-20260304T021000Z-abc123"

  python scripts/system/ops_control.py status

  python scripts/system/ops_control.py verify --packet-id "claude-handoff-20260304T021000Z-abc123"

  python scripts/system/ops_control.py roster

  python scripts/system/ops_control.py health
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_COMM = REPO_ROOT / "artifacts" / "agent_comm"
GITHUB_LANES = AGENT_COMM / "github_lanes"
AGENTS_DIR = REPO_ROOT / "agents"
SCBE_DIR = REPO_ROOT / ".scbe"
OBSIDIAN_VAULT = Path(
    r"C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder\AI Workspace"
)
CROSS_TALK_MD = OBSIDIAN_VAULT / "Cross Talk.md"
SESSION_SIGNONS = AGENT_COMM / "session_signons.jsonl"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_dir() -> Path:
    d = AGENT_COMM / datetime.now(timezone.utc).strftime("%Y%m%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_packet_id(from_agent: str, intent: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = f"{from_agent}-{intent}-{ts}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:6]
    return f"{from_agent}-{intent}-{ts}-{h}"


def build_packet(args) -> dict:
    artifacts = []
    if args.artifacts:
        artifacts = [a.strip() for a in args.artifacts.split(",") if a.strip()]

    return {
        "packet_id": make_packet_id(args.from_agent, args.intent),
        "created_at": now_utc(),
        "from": f"agent.{args.from_agent}",
        "to": f"agent.{args.to}",
        "intent": args.intent,
        "status": args.status,
        "summary": args.summary,
        "artifacts": artifacts,
        "next": args.next_action or "",
        "ack_required": args.intent not in ("ack", "status_update"),
    }


# ---- Surface Writers ----

def write_json_packet(packet: dict) -> tuple[bool, str]:
    """Surface 1: JSON file in artifacts/agent_comm/{date}/"""
    try:
        d = today_dir()
        slug = packet["packet_id"].replace(":", "-")
        path = d / f"cross-talk-{slug}.json"
        path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        return True, str(path.relative_to(REPO_ROOT))
    except Exception as e:
        return False, str(e)


def write_jsonl_lane(packet: dict) -> tuple[bool, str]:
    """Surface 2: Append to cross_talk.jsonl"""
    try:
        GITHUB_LANES.mkdir(parents=True, exist_ok=True)
        path = GITHUB_LANES / "cross_talk.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(packet) + "\n")
        return True, str(path.relative_to(REPO_ROOT))
    except Exception as e:
        return False, str(e)


def write_obsidian(packet: dict) -> tuple[bool, str]:
    """Surface 3: Append markdown block to Obsidian Cross Talk.md"""
    try:
        if not OBSIDIAN_VAULT.exists():
            return False, f"Obsidian vault not found: {OBSIDIAN_VAULT}"

        agent_name = packet["from"].replace("agent.", "").title()
        task_slug = packet["intent"]
        artifacts_md = ""
        if packet.get("artifacts"):
            items = "\n".join(f"  - {a}" for a in packet["artifacts"])
            artifacts_md = f"\n- artifacts:\n{items}"

        block = (
            f"\n## {packet['created_at']} | {agent_name} | {task_slug}\n\n"
            f"- status: {packet['status']}\n"
            f"- summary: {packet['summary']}{artifacts_md}\n"
            f"- next: {packet.get('next', 'none')}\n"
        )

        with open(CROSS_TALK_MD, "a", encoding="utf-8") as f:
            f.write(block)
        return True, str(CROSS_TALK_MD)
    except Exception as e:
        return False, str(e)


def write_agent_log(packet: dict) -> tuple[bool, str]:
    """Surface 4: Append to agents/{from_agent}.md"""
    try:
        AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        agent = packet["from"].replace("agent.", "")
        path = AGENTS_DIR / f"{agent}.md"

        if not path.exists():
            path.write_text(
                f"# Agent: {agent}\n\nPacket log for {agent}.\n\n",
                encoding="utf-8",
            )

        first_artifact = packet["artifacts"][0] if packet.get("artifacts") else "-"
        line = (
            f"- {packet['created_at']} {packet['from']} -> {packet['to']} "
            f"| {packet['intent']} | {packet['status']} "
            f"| {packet['summary'][:80]} ({first_artifact})\n"
        )

        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
        return True, str(path.relative_to(REPO_ROOT))
    except Exception as e:
        return False, str(e)


def deliver_to_all(packet: dict) -> dict:
    """Write packet to all 4 surfaces, return delivery report."""
    results = {}
    for name, writer in [
        ("json_packet", write_json_packet),
        ("jsonl_lane", write_jsonl_lane),
        ("obsidian", write_obsidian),
        ("agent_log", write_agent_log),
    ]:
        ok, detail = writer(packet)
        results[name] = {"ok": ok, "detail": detail}
    return results


# ---- Commands ----

def cmd_send(args):
    packet = build_packet(args)
    delivery = deliver_to_all(packet)

    successes = sum(1 for v in delivery.values() if v["ok"])
    print(f"\n--- SEND: {packet['packet_id']} ---")
    print(f"From: {packet['from']} -> To: {packet['to']}")
    print(f"Intent: {packet['intent']} | Status: {packet['status']}")
    print(f"Summary: {packet['summary']}")
    print(f"\nDelivery: {successes}/4 surfaces")
    for name, result in delivery.items():
        status = "OK" if result["ok"] else "FAIL"
        print(f"  [{status}] {name}: {result['detail']}")

    if successes < 4:
        print("\nWARNING: Not all surfaces received the packet!")
        sys.exit(1)
    else:
        print("\nAll surfaces delivered successfully.")


def cmd_ack(args):
    """ACK a specific packet by ID."""
    # Build an ACK packet
    ack_packet = {
        "packet_id": make_packet_id(args.from_agent, "ack"),
        "created_at": now_utc(),
        "from": f"agent.{args.from_agent}",
        "to": "agent.all",
        "intent": "ack",
        "status": "done",
        "summary": f"ACK {args.packet_id}: Received and acknowledged.",
        "artifacts": [],
        "next": "",
        "ack_required": False,
    }

    delivery = deliver_to_all(ack_packet)
    successes = sum(1 for v in delivery.values() if v["ok"])
    print(f"\n--- ACK: {args.packet_id} ---")
    print(f"Delivery: {successes}/4 surfaces")
    for name, result in delivery.items():
        status = "OK" if result["ok"] else "FAIL"
        print(f"  [{status}] {name}: {result['detail']}")


def cmd_status(args):
    """Show active lanes and pending handoffs."""
    print("\n--- AGENT STATUS ---\n")

    # Recent packets (last 24h)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    packet_dir = AGENT_COMM / today
    packets = []
    if packet_dir.exists():
        for f in sorted(packet_dir.glob("cross-talk-*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                packets.append(data)
            except Exception:
                pass

    print(f"Packets today ({today}): {len(packets)}")
    for p in packets[-10:]:
        ack_tag = " [ACK-NEEDED]" if p.get("ack_required") and p.get("intent") != "ack" else ""
        print(f"  {p.get('created_at','')} {p.get('from','')} -> {p.get('to','')} | {p.get('intent','')} | {p.get('status','')}{ack_tag}")
        print(f"    {p.get('summary','')[:100]}")

    # JSONL lane tail
    lane_file = GITHUB_LANES / "cross_talk.jsonl"
    if lane_file.exists():
        lines = lane_file.read_text(encoding="utf-8").strip().split("\n")
        recent = lines[-5:] if len(lines) >= 5 else lines
        print(f"\nJSONL lane (last {len(recent)}):")
        for line in recent:
            try:
                d = json.loads(line)
                print(f"  {d.get('created_at','')} {d.get('from','')} -> {d.get('to','')} | {d.get('intent', d.get('type',''))}")
            except Exception:
                pass

    # Session signons
    if SESSION_SIGNONS.exists():
        lines = SESSION_SIGNONS.read_text(encoding="utf-8").strip().split("\n")
        recent = lines[-5:] if len(lines) >= 5 else lines
        print(f"\nRecent sessions ({len(recent)}):")
        for line in recent:
            try:
                d = json.loads(line)
                print(f"  {d.get('timestamp_utc','')} {d.get('agent','')} ({d.get('callsign','')}) — {d.get('status','')}")
            except Exception:
                pass

    print()


def cmd_verify(args):
    """Check if a packet exists on all surfaces."""
    pid = args.packet_id
    print(f"\n--- VERIFY: {pid} ---\n")

    found = {}

    # Surface 1: JSON packet
    for date_dir in sorted(AGENT_COMM.iterdir()):
        if date_dir.is_dir() and date_dir.name.isdigit():
            for f in date_dir.glob("cross-talk-*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get("packet_id") == pid:
                        found["json_packet"] = str(f.relative_to(REPO_ROOT))
                except Exception:
                    pass

    # Surface 2: JSONL lane
    lane_file = GITHUB_LANES / "cross_talk.jsonl"
    if lane_file.exists():
        for line in lane_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                d = json.loads(line)
                if d.get("packet_id") == pid:
                    found["jsonl_lane"] = str(lane_file.relative_to(REPO_ROOT))
            except Exception:
                pass

    # Surface 3: Obsidian
    if CROSS_TALK_MD.exists():
        content = CROSS_TALK_MD.read_text(encoding="utf-8")
        # Check for packet ID or matching timestamp
        if pid in content:
            found["obsidian"] = str(CROSS_TALK_MD)

    # Surface 4: Agent log
    for f in AGENTS_DIR.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        if pid in content or (pid.split("-")[0] in content):
            found["agent_log"] = str(f.relative_to(REPO_ROOT))

    for surface in ["json_packet", "jsonl_lane", "obsidian", "agent_log"]:
        if surface in found:
            print(f"  [FOUND] {surface}: {found[surface]}")
        else:
            print(f"  [MISSING] {surface}")

    print(f"\nDelivery: {len(found)}/4 surfaces")


def cmd_roster(args):
    """Show agent registry."""
    print("\n--- AGENT ROSTER ---\n")

    squad_file = SCBE_DIR / "agent_squad.json"
    if squad_file.exists():
        data = json.loads(squad_file.read_text(encoding="utf-8"))
        agents = data.get("agents", {})
        print(f"Registered agents: {len(agents)}")
        for aid, info in agents.items():
            enabled = info.get("enabled", True)
            tag = "ACTIVE" if enabled else "DISABLED"
            print(f"  [{tag}] {aid}: {info.get('display_name',aid)} ({info.get('provider','?')}/{info.get('model','?')})")
    else:
        print("No agent_squad.json found.")

    print()


def cmd_health(args):
    """Run health checks."""
    import subprocess

    print("\n--- HEALTH CHECK ---\n")

    checks = [
        ("GCP VM", "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 https://34.134.99.90:8001/health"),
        ("n8n Bridge", "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1:8001/health"),
        ("AetherNet", "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1:8300/health"),
    ]

    for name, cmd in checks:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            code = result.stdout.strip().replace("'", "")
            if code == "200":
                print(f"  [PASS] {name}: HTTP {code}")
            else:
                print(f"  [FAIL] {name}: HTTP {code}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    # Check connector health script
    health_script = REPO_ROOT / "scripts" / "connector_health_check.py"
    if health_script.exists():
        print(f"\n  Connector health script available: {health_script.relative_to(REPO_ROOT)}")
    else:
        print("\n  No connector_health_check.py found")

    print()


# ---- CLI ----

def main():
    parser = argparse.ArgumentParser(description="SCBE Ops Control — Multi-Agent Bus")
    sub = parser.add_subparsers(dest="command")

    # send
    p_send = sub.add_parser("send", help="Send cross-talk to all surfaces")
    p_send.add_argument("--from", dest="from_agent", required=True)
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--intent", required=True,
                        choices=["handoff", "ack", "sync", "lane_claim",
                                 "status_update", "smoke", "asset_drop"])
    p_send.add_argument("--status", required=True,
                        choices=["done", "in_progress", "pending", "blocked"])
    p_send.add_argument("--summary", required=True)
    p_send.add_argument("--artifacts", default="", help="Comma-separated file paths")
    p_send.add_argument("--next", dest="next_action", default="")

    # ack
    p_ack = sub.add_parser("ack", help="Acknowledge a packet")
    p_ack.add_argument("--packet-id", required=True)
    p_ack.add_argument("--from", dest="from_agent", default="claude")

    # status
    sub.add_parser("status", help="Show active lanes and pending handoffs")

    # verify
    p_verify = sub.add_parser("verify", help="Verify packet delivery")
    p_verify.add_argument("--packet-id", required=True)

    # roster
    sub.add_parser("roster", help="Show agent registry")

    # health
    sub.add_parser("health", help="Run health checks")

    args = parser.parse_args()

    if args.command == "send":
        cmd_send(args)
    elif args.command == "ack":
        cmd_ack(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "roster":
        cmd_roster(args)
    elif args.command == "health":
        cmd_health(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
