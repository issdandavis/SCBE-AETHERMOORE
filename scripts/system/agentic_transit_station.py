#!/usr/bin/env python3
"""Agentic Transit Station packets for SCBE operational work.

This is the human-facing wrapper around the older agent-bus/mirror-room pieces.
It keeps the transport metaphor explicit: platforms, tickets, dispatch lanes,
receipts, and proof artifacts. The packets are still regular AgentPacketV1
objects underneath so existing AI-to-AI tooling can consume them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent_comms import AgentPacketV1, Budget, ContextRef, Route, enforce_budget, hash_state, packet_input_tokens

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agentic_transit_station"
AWS_DEMO_SCRIPT = REPO_ROOT / "scripts" / "system" / "aws_free_tier_demo_stack.py"
AWS_DEMO_GUIDE = REPO_ROOT / "docs" / "customer-guides" / "SCBE_FREE_TIER_DEMO_USER_GUIDE.md"
AWS_DEMO_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "aws_free_tier_demo" / "scbe-free-tier-demo"


@dataclass(frozen=True)
class StationPlatform:
    platform_id: str
    full_name: str
    tongue: str
    role: str
    allowed_action: str
    blocked_action: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def latest_aws_demo_packet() -> Path | None:
    if not AWS_DEMO_ARTIFACT_ROOT.exists():
        return None
    packets = sorted(AWS_DEMO_ARTIFACT_ROOT.glob("*/demo_stack_packet.json"), key=lambda p: p.stat().st_mtime)
    return packets[-1] if packets else None


def station_platforms() -> list[StationPlatform]:
    return [
        StationPlatform(
            "ticketing",
            "Intent Ticketing Platform",
            "KO",
            "Convert user intent into a bounded work ticket.",
            "write a compact AgentPacketV1 with refs",
            "paste raw secrets or full repo context into a model prompt",
        ),
        StationPlatform(
            "security_gate",
            "Security And Cost Gate Platform",
            "RU",
            "Check permissions, billing risk, and deployment boundaries.",
            "verify profile, table capacity, and email-send gates",
            "grant broad EC2/IAM/admin permissions",
        ),
        StationPlatform(
            "operator_track",
            "AWS Demo Operator Track",
            "CA",
            "Run or dry-run the AWS free-tier demo stack.",
            "call scripts/system/aws_free_tier_demo_stack.py",
            "create public endpoints without an explicit promotion gate",
        ),
        StationPlatform(
            "guide_counter",
            "Buyer Guide Counter",
            "UM",
            "Convert working prototype proof into a buyer-safe guide.",
            "review docs/customer-guides/SCBE_FREE_TIER_DEMO_USER_GUIDE.md",
            "claim email delivery works before SES identity verification",
        ),
        StationPlatform(
            "telemetry_archive",
            "Telemetry Archive Platform",
            "DR",
            "Preserve proof receipts and next-action packets.",
            "record artifact paths, hashes, and test commands",
            "store raw credentials or unverifiable claims",
        ),
    ]


def build_aws_demo_agent_packet(*, ticket_id: str, execute_demo: bool, latest_packet: Path | None) -> AgentPacketV1:
    refs = [
        ContextRef(kind="path", value=_rel(AWS_DEMO_SCRIPT), bytes=AWS_DEMO_SCRIPT.stat().st_size),
        ContextRef(kind="path", value=_rel(AWS_DEMO_GUIDE), bytes=AWS_DEMO_GUIDE.stat().st_size if AWS_DEMO_GUIDE.exists() else 0),
    ]
    if latest_packet:
        refs.append(ContextRef(kind="path", value=_rel(latest_packet), bytes=latest_packet.stat().st_size))
        refs.append(ContextRef(kind="sha256", value=_sha256_file(latest_packet), bytes=32))
    request = (
        "Verify the AWS free-tier demo stack ticket. Return a compact verdict with "
        "resource status, cost guardrails, and next promotion blocker."
    )
    packet = AgentPacketV1(
        task_id=ticket_id,
        phase="verify" if latest_packet else "plan",
        route=Route(tongue="RU", domain="aws-free-tier-demo", permission="read"),
        context_refs=refs,
        state_hash=hash_state(ticket_id, str(execute_demo), refs[0].value),
        budget=Budget(max_input_tokens=768, max_output_tokens=256),
        request=request,
        expected_output="verdict",
    )
    enforce_budget(packet)
    return packet


def run_aws_demo(*, execute_demo: bool, json_output: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(AWS_DEMO_SCRIPT)]
    if execute_demo:
        cmd.append("--execute")
    if json_output:
        cmd.append("--json")
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    payload: dict[str, Any] = {"returncode": proc.returncode, "ok": proc.returncode == 0}
    if proc.stdout.strip():
        try:
            payload["packet"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload["stdout_tail"] = proc.stdout[-2000:]
    if proc.stderr.strip():
        payload["stderr_tail"] = proc.stderr[-2000:]
    return payload


def build_station_manifest(args: argparse.Namespace) -> dict[str, Any]:
    latest_packet = latest_aws_demo_packet()
    ticket_id = args.ticket_id or f"ats-aws-demo-{_sha256_text(_utc_now())[:12]}"
    packet = build_aws_demo_agent_packet(ticket_id=ticket_id, execute_demo=bool(args.execute_demo), latest_packet=latest_packet)
    manifest: dict[str, Any] = {
        "schema_version": "scbe_agentic_transit_station_v1",
        "generated_at": _utc_now(),
        "station_name": "SCBE Agentic Transit Station Operational Complex",
        "legacy_bridge": "agentbus/mirror_room compatibility remains available behind this station surface",
        "ticket_id": ticket_id,
        "operation": "aws-free-tier-demo",
        "privacy": "local_only" if not args.remote_ok else "remote_ok",
        "platforms": [asdict(platform) for platform in station_platforms()],
        "agent_packet": packet.to_dict(),
        "packet_input_tokens": packet_input_tokens(packet),
        "context_policy": {
            "small_context_packet": True,
            "raw_secret_forwarding": False,
            "remote_provider_allowed": bool(args.remote_ok),
            "public_endpoint_created": False,
        },
        "proof_refs": {
            "demo_script": _rel(AWS_DEMO_SCRIPT),
            "customer_guide": _rel(AWS_DEMO_GUIDE),
            "latest_demo_packet": _rel(latest_packet) if latest_packet else "",
        },
        "recommended_commands": [
            "python scripts/system/agentic_transit_station.py aws-demo --json",
            "python scripts/system/aws_free_tier_demo_stack.py --json",
            "python scripts/system/aws_free_tier_demo_stack.py --execute --json",
        ],
    }
    if args.run_demo:
        manifest["aws_demo_run"] = run_aws_demo(execute_demo=bool(args.execute_demo), json_output=True)
    return manifest


def write_manifest(manifest: dict[str, Any], output_root: Path) -> Path:
    ticket_id = str(manifest["ticket_id"])
    out_dir = output_root / ticket_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "station_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    latest = output_root / "latest_station_manifest.json"
    latest.write_text(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    return path


def cmd_aws_demo(args: argparse.Namespace) -> int:
    manifest = build_station_manifest(args)
    path = write_manifest(manifest, Path(args.output_root))
    manifest["artifact"] = _rel(path)
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True))
    else:
        print("SCBE Agentic Transit Station Operational Complex")
        print(f"ticket={manifest['ticket_id']}")
        print(f"operation={manifest['operation']}")
        print(f"packet_tokens={manifest['packet_input_tokens']}")
        print(f"artifact={manifest['artifact']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCBE agentic transit station operational complex")
    sub = parser.add_subparsers(dest="command", required=True)
    aws = sub.add_parser("aws-demo", help="Create an agentic transit ticket for the AWS free-tier demo stack")
    aws.add_argument("--ticket-id", default="")
    aws.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    aws.add_argument("--remote-ok", action="store_true", help="Mark the packet as eligible for remote helper review")
    aws.add_argument("--run-demo", action="store_true", help="Run the AWS demo stack script from the station")
    aws.add_argument("--execute-demo", action="store_true", help="Mutate AWS demo resources when --run-demo is used")
    aws.add_argument("--json", action="store_true")
    aws.set_defaults(func=cmd_aws_demo)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
