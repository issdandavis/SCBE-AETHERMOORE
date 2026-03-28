from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _now_stamp() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat().replace(":", "").replace("-", "") + "Z"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def build_packets(goal: str) -> dict[str, str]:
    # Keep these packets provider-agnostic: feed them to any model lane.
    return {
        "spec_kit_king": (
            "You are the Spec Kit (King) layer.\n"
            f"Goal: {goal}\n\n"
            "Output:\n"
            "- Constitution (governing principles)\n"
            "- Requirements (what must be true)\n"
            "- Constraints + invariants (what must not break)\n"
            "- Acceptance tests (how we know it is done)\n\n"
            "Rules:\n"
            "- Be explicit and testable.\n"
            "- Prefer fewer, stronger constraints over vague prose.\n"
        ),
        "bmad_queen_ko_orchestrator": (
            "You are BMAD (Queen) role: KO Orchestrator / Intent.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Identify the top 3 intent risks (scope creep, wrong goal, unsafe automation).\n"
            "- Propose a 5-step plan with clear exit conditions.\n"
        ),
        "bmad_queen_ru_policy_witness": (
            "You are BMAD (Queen) role: RU Policy / Witness.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- List claims that require proof.\n"
            "- Define what evidence is acceptable (tests, logs, screenshots, reproducible runs).\n"
            "- Flag any language that overstates what is implemented.\n"
        ),
        "bmad_queen_ca_compute_impl": (
            "You are BMAD (Queen) role: CA Compute / Implementation.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Propose the smallest implementation slice that proves the architecture.\n"
            "- Identify performance constraints and failure cases.\n"
        ),
        "bmad_queen_av_interfaces_io": (
            "You are BMAD (Queen) role: AV Interfaces / External IO.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Identify required connectors/surfaces (email, YouTube, vault, web, APIs).\n"
            "- Define inputs/outputs for each (schemas, contracts).\n"
        ),
        "bmad_queen_um_security_privacy": (
            "You are BMAD (Queen) role: UM Security / Privacy.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Threat model: how can this be abused.\n"
            "- Secrets handling requirements.\n"
            "- Safe-by-default execution rules.\n"
        ),
        "bmad_queen_dr_verification_judge": (
            "You are BMAD (Queen) role: DR Verification / Judge.\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Define deterministic checks (unit tests, integration tests, invariants).\n"
            "- Define what 'done' means in verifiable terms.\n"
        ),
        "gsd_rook_state_lane": (
            "You are GSD (Rook) continuity layer.\n"
            f"Goal: {goal}\n\n"
            "Output:\n"
            "- STATE: current position, decisions, blockers, next actions.\n"
            "- LEDGER: what ran, what changed, where artifacts are stored.\n"
            "- THREADS: open loops to revisit (backlog items).\n"
        ),
        "superpowers_bishop_gate": (
            "You are Superpowers (Bishop) implementation discipline layer.\n"
            f"Goal: {goal}\n\n"
            "Rules:\n"
            "- Do not jump to broad refactors.\n"
            "- Implement in small steps.\n"
            "- Tie each change to a verification step.\n"
            "- Produce evidence, not vibes.\n"
        ),
        "pawns_tasks_to_promotions": (
            "You are the Pawn layer (tasks).\n"
            f"Goal: {goal}\n\n"
            "Task:\n"
            "- Break work into 5-15 minute tasks.\n"
            "- Identify which tasks can 'promote' into reusable scripts, skills, or templates.\n"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an agentic-dev chessboard packet (Spec Kit + BMAD + GSD + Superpowers).")
    parser.add_argument("--goal", default="Improve SCBE long-running agentic workflows with governed momentum trains.", help="Goal for the run.")
    parser.add_argument("--output-dir", default="", help="Output directory relative to repo root (default: artifacts/chessboard/<timestamp>).")
    args = parser.parse_args()

    stamp = _now_stamp()
    out_dir = ROOT / (args.output_dir or f"artifacts/chessboard/{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    packets = build_packets(str(args.goal).strip())
    meta = {
        "schema_version": "scbe_chessboard_packets_v1",
        "generated_at_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "goal": str(args.goal).strip(),
        "packet_count": len(packets),
        "spec_doc": "docs/specs/AGENTIC_DEV_CHESSBOARD_STACK.md",
    }

    _write_json(out_dir / "meta.json", meta)
    _write_json(out_dir / "packets.json", packets)

    print(json.dumps({"ok": True, "output_dir": str(out_dir.relative_to(ROOT)), "packet_count": len(packets)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

