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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CROSSTALK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
ACK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk_acks.jsonl"
LEGACY_OBSIDIAN_WORKSPACE = REPO_ROOT / "notes"
PACKET_CLASS_VALUES = {"internal", "external", "evidence", "governance"}
RAIL_KEYS = ("P+", "P-", "D+", "D-")


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


def _default_env(var_name: str, fallback: str) -> str:
    """Resolve a non-empty default value from env var or fallback."""
    raw = os.environ.get(var_name, "")
    value = str(raw).strip()
    return value or fallback


def _coalesce_cli_value(value: Optional[str], env_var: str, fallback: str) -> str:
    """Prefer explicit CLI value, then env var, then fallback."""
    if value is not None:
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return _default_env(env_var, fallback)


def _parse_json_arg(raw: str, field_name: str) -> Dict[str, Any]:
    cleaned = str(raw).strip()
    if not cleaned:
        return {}
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must decode to an object")
    return value


def _normalize_packet_class(packet_class: str) -> str:
    cleaned = str(packet_class or "internal").strip().lower()
    if cleaned not in PACKET_CLASS_VALUES:
        allowed = ", ".join(sorted(PACKET_CLASS_VALUES))
        raise ValueError(f"packet_class must be one of: {allowed}")
    return cleaned


def _normalize_rail_entries(entries: Any) -> List[Dict[str, Any]]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError("rail entries must be arrays")
    normalized: List[Dict[str, Any]] = []
    for idx, entry in enumerate(entries, start=1):
        if isinstance(entry, dict):
            normalized.append(dict(entry))
        elif isinstance(entry, str):
            normalized.append({"type": "note", "message": entry})
        else:
            raise ValueError(f"rail entry {idx} must be object or string")
    return normalized


def _normalize_rails(rails: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    raw = rails or {}
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for key in RAIL_KEYS:
        normalized[key] = _normalize_rail_entries(raw.get(key, []))
    extra_keys = sorted(k for k in raw.keys() if k not in RAIL_KEYS)
    if extra_keys:
        normalized["_extra"] = [{"type": "ignored_keys", "keys": extra_keys}]
    return normalized


def _normalize_lease(lease: Optional[Dict[str, Any]], worker_id: str, created_at: str) -> Optional[Dict[str, Any]]:
    if not lease:
        return None
    owner = str(lease.get("owner", "")).strip() or worker_id
    provider = str(lease.get("provider", "")).strip() or "local"
    resource_class = str(lease.get("resource_class", "")).strip() or "browser"
    lease_id = str(lease.get("lease_id", "")).strip() or f"lease-{_safe_token(owner)}-{_safe_token(provider)}"
    lease_seconds = int(lease.get("lease_seconds", 0) or 0)
    claimed_at_utc = str(lease.get("claimed_at_utc", "")).strip() or created_at
    expires_at_utc = str(lease.get("expires_at_utc", "")).strip()
    if not expires_at_utc and lease_seconds > 0:
        claimed_dt = datetime.strptime(claimed_at_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        expires_at_utc = (claimed_dt + timedelta(seconds=lease_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "lease_id": lease_id,
        "owner": owner,
        "provider": provider,
        "resource_class": resource_class,
        "lease_seconds": lease_seconds,
        "claimed_at_utc": claimed_at_utc,
        "expires_at_utc": expires_at_utc or None,
    }


def _normalize_layer14(layer14: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    raw = dict(layer14 or {})
    numeric_fields = (
        "energy",
        "centroid",
        "flux",
        "hf_ratio",
        "stability",
        "verification_score",
        "anomaly_ratio",
    )
    normalized: Dict[str, Any] = {}
    for field in numeric_fields:
        if field in raw and raw[field] is not None:
            normalized[field] = float(raw[field])
    for field in ("signal_class", "channel", "summary"):
        if field in raw and raw[field] is not None:
            normalized[field] = str(raw[field])
    return normalized


def _normalize_ledger(ledger: Optional[Dict[str, Any]], packet_class: str) -> Dict[str, Any]:
    raw = dict(ledger or {})
    lane_targets = raw.get("lane_targets")
    if not isinstance(lane_targets, list) or not lane_targets:
        lane_targets = ["dated_json", "jsonl_bus", "obsidian"]
    return {
        "packet_class": packet_class,
        "delivery_mode": str(raw.get("delivery_mode", "all_lanes")),
        "lane_targets": [str(item) for item in lane_targets],
        "channel": str(raw.get("channel", "cross_talk")),
    }


def _obsidian_config_path() -> Path:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "Obsidian" / "obsidian.json"
    return Path.home() / "AppData" / "Roaming" / "Obsidian" / "obsidian.json"


def _load_obsidian_vaults(config_path: Path) -> List[Path]:
    if not config_path.exists():
        return []
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    vaults_obj = payload.get("vaults", {})
    vault_paths: List[Path] = []
    if isinstance(vaults_obj, dict):
        for meta in vaults_obj.values():
            if not isinstance(meta, dict):
                continue
            raw_path = str(meta.get("path", "")).strip()
            if raw_path:
                vault_paths.append(Path(raw_path))
    return vault_paths


def _resolve_obsidian_workspace() -> Path:
    env_workspace = str(os.environ.get("OBSIDIAN_WORKSPACE", "")).strip()
    if env_workspace:
        env_path = Path(env_workspace)
        if env_path.exists():
            return env_path

    for vault_path in _load_obsidian_vaults(_obsidian_config_path()):
        if vault_path.exists():
            return vault_path

    return LEGACY_OBSIDIAN_WORKSPACE


def _resolve_obsidian_crosstalk() -> Path:
    return _resolve_obsidian_workspace() / "Cross Talk.md"


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
    packet_class: str = "internal",
    mission_id: str = "",
    worker_id: str = "",
    lease: Optional[Dict[str, Any]] = None,
    rails: Optional[Dict[str, Any]] = None,
    layer14: Optional[Dict[str, Any]] = None,
    ledger: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Emit a cross-talk packet to ALL lanes atomically. Returns delivery report."""

    created_at = _utc_now()
    stamp = _utc_stamp()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_task = _safe_token(task_id, "general")
    safe_sender = _safe_token(sender, "agent")
    packet_id = f"cross-talk-{safe_sender}-{safe_task}-{stamp}"
    normalized_packet_class = _normalize_packet_class(packet_class)
    normalized_worker_id = str(worker_id).strip() or (codename or safe_sender)
    normalized_rails = _normalize_rails(rails)
    normalized_lease = _normalize_lease(lease, normalized_worker_id, created_at)
    normalized_layer14 = _normalize_layer14(layer14)
    normalized_ledger = _normalize_ledger(ledger, normalized_packet_class)

    packet = {
        "packet_id": packet_id,
        "created_at": created_at,
        "session_id": session_id or f"sess-{day}",
        "mission_id": mission_id or task_id,
        "worker_id": normalized_worker_id,
        "codename": codename or safe_sender,
        "sender": sender,
        "recipient": recipient,
        "intent": intent,
        "status": status,
        "packet_class": normalized_packet_class,
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
        "lease": normalized_lease,
        "rails": normalized_rails,
        "layer14": normalized_layer14,
        "ledger": normalized_ledger,
        "gates": {"governance_packet": True, "tests_requested": []},
    }

    integrity_hash = _packet_hash(packet)
    packet["_integrity"] = integrity_hash
    packet["ledger"]["integrity_hint"] = integrity_hash

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
        obsidian_crosstalk = _resolve_obsidian_crosstalk()
        if obsidian_crosstalk.parent.exists():
            agent_short = sender.replace("agent.", "").capitalize()
            obsidian_entry = (
                f"\n## {created_at} | {agent_short} | {task_id}\n\n"
                f"**Status**: {status}\n"
                f"**Packet Class**: {normalized_packet_class}\n"
                f"**Intent**: {intent}\n"
                f"**Mission**: {packet['mission_id']}\n"
                f"**Worker**: {normalized_worker_id}\n"
                f"**Summary**: {summary}\n"
                f"**Proof**: {', '.join(proof or ['none'])}\n"
                f"**Next**: {next_action or 'none'}\n"
                f"**Packet ID**: {packet_id}\n"
                f"**Integrity**: {integrity_hash}\n"
            )
            if not obsidian_crosstalk.exists():
                obsidian_crosstalk.write_text("# Cross Talk\n", encoding="utf-8")
            with obsidian_crosstalk.open("a", encoding="utf-8") as f:
                f.write(obsidian_entry)
            delivery["lanes"]["obsidian"] = {"ok": True, "path": str(obsidian_crosstalk)}
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
    delivery["packet_class"] = normalized_packet_class
    delivery["mission_id"] = packet["mission_id"]
    delivery["worker_id"] = normalized_worker_id

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
    obsidian_crosstalk = _resolve_obsidian_crosstalk()
    if obsidian_crosstalk.exists():
        content = obsidian_crosstalk.read_text(encoding="utf-8")
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
    packet_classes: Dict[str, int] = {}
    mission_counts: Dict[str, int] = {}
    if CROSSTALK_LANE.exists():
        with CROSSTALK_LANE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                bus_lines += 1
                try:
                    latest_packet = json.loads(line)
                    packet_class = str(latest_packet.get("packet_class", "internal"))
                    mission = str(latest_packet.get("mission_id", "")).strip()
                    packet_classes[packet_class] = packet_classes.get(packet_class, 0) + 1
                    if mission:
                        mission_counts[mission] = mission_counts.get(mission, 0) + 1
                except json.JSONDecodeError:
                    pass
    report["lanes"]["jsonl_bus"] = {
        "exists": CROSSTALK_LANE.exists(),
        "total_packets": bus_lines,
        "latest_at": latest_packet.get("created_at", "") if latest_packet else "",
        "latest_task": latest_packet.get("task_id", "") if latest_packet else "",
        "packet_classes": packet_classes,
        "recent_missions": dict(sorted(mission_counts.items(), key=lambda item: item[1], reverse=True)[:10]),
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
    obsidian_crosstalk = _resolve_obsidian_crosstalk()
    report["lanes"]["obsidian"] = {
        "workspace": str(obsidian_crosstalk.parent),
        "path": str(obsidian_crosstalk),
        "exists": obsidian_crosstalk.exists(),
        "size_bytes": obsidian_crosstalk.stat().st_size if obsidian_crosstalk.exists() else 0,
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
    emit_p.add_argument("--sender", default="")
    emit_p.add_argument("--recipient", default="")
    emit_p.add_argument("--intent", default="sync")
    emit_p.add_argument("--task-id", default="")
    emit_p.add_argument("--summary", default="")
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
    emit_p.add_argument("--packet-class", default="internal")
    emit_p.add_argument("--mission-id", default="")
    emit_p.add_argument("--worker-id", default="")
    emit_p.add_argument("--lease-json", default="")
    emit_p.add_argument("--rails-json", default="")
    emit_p.add_argument("--layer14-json", default="")
    emit_p.add_argument("--ledger-json", default="")

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
        sender = _coalesce_cli_value(args.sender, "SCBE_CROSSTALK_SENDER", "agent.codex")
        recipient = _coalesce_cli_value(args.recipient, "SCBE_CROSSTALK_RECIPIENT", "agent.claude")
        task_id = _coalesce_cli_value(args.task_id, "SCBE_CROSSTALK_TASK_ID", "NOTE")
        summary = _coalesce_cli_value(args.summary, "SCBE_CROSSTALK_SUMMARY", "Cross-talk note.")
        lease = _parse_json_arg(args.lease_json, "lease_json")
        rails = _parse_json_arg(args.rails_json, "rails_json")
        layer14 = _parse_json_arg(args.layer14_json, "layer14_json")
        ledger = _parse_json_arg(args.ledger_json, "ledger_json")
        result = emit_packet(
            sender=sender,
            recipient=recipient,
            intent=args.intent,
            task_id=task_id,
            summary=summary,
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
            packet_class=args.packet_class,
            mission_id=args.mission_id,
            worker_id=args.worker_id,
            lease=lease or None,
            rails=rails or None,
            layer14=layer14 or None,
            ledger=ledger or None,
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
