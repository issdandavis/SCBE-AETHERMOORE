#!/usr/bin/env python3
"""
SCBE Longform Bridge — Chain Integrity Stress Benchmark
========================================================

Tests 8 attack classes against the JSONL hash chain + semantic landing anchor,
plus cold-start resume fidelity and a non-scored depth/time table.

Score breakdown:
  A1  payload byte-flip                   → must detect              [15 pts]
  A2  event_hash field byte-flip          → must detect              [15 pts]
  A3  event insertion (no recompute)      → must detect              [15 pts]
  A4  event deletion (middle of chain)    → must detect              [15 pts]
  A5  event swap (adjacent pair)          → must detect              [10 pts]
  A6  hash-field substitution             → must detect              [10 pts]
  A7  full recompute-from-mutation        → chain passes, anchor detects [10 pts]
  A8  anchored-prefix truncation          → chain passes, anchor detects [ 5 pts]
  R1  cold-start resume via subprocess    → pack loads + verifies    [10 pts]
  ─────────────────────────────────────────────────────────────────────────
  Total                                                              105 pts

Performance (non-scored):
  P0  depth × time table at N = 50, 100, 250, 500 events
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.longform.context_bridge import (
    ContextLanding,
    LedgerEvent,
    JsonlWorkflowLedger,
    PrincipleSet,
    new_ledger,
    create_landing,
    build_resume_pack,
)

CHAIN_DEPTH = 20  # events for each attack scenario


# ── Workspace helpers ────────────────────────────────────────────────────────

def build_chain(n_events: int = CHAIN_DEPTH) -> tuple[str, JsonlWorkflowLedger]:
    """Create a temp workspace with an n_events-long chain. Caller must rmtree."""
    tmp = tempfile.mkdtemp(prefix="scbe-chain-bench-")
    ws = os.path.join(tmp, "workspace")
    os.makedirs(ws)
    ledger = new_ledger(
        ws,
        "Chain integrity stress test",
        invariants=["chain is append-only", "no event deleted"],
    )
    for i in range(n_events - 1):
        ledger.append("brick", {"seq_check": i, "data": f"payload-{i}"})
    return tmp, ledger


def ledger_path(ledger: JsonlWorkflowLedger) -> Path:
    return Path(ledger._ledger_path)


def read_lines(ledger: JsonlWorkflowLedger) -> list[str]:
    return ledger_path(ledger).read_text(encoding="utf-8").splitlines()


def write_lines(ledger: JsonlWorkflowLedger, lines: list[str]) -> None:
    ledger_path(ledger).write_text("\n".join(lines) + "\n", encoding="utf-8")


def recompute_from(events: list[LedgerEvent], start: int = 0) -> None:
    """Recompute previous_hash/event_hash fields from start through chain end."""
    for i in range(start, len(events)):
        events[i].previous_hash = events[i - 1].event_hash if i > 0 else None
        events[i].event_hash = events[i].compute_hash()


def flip_hex_char(s: str, pos: int = 7) -> str:
    """Flip one hex character in a string — used to create a 1-char diff."""
    chars = list(s)
    idx = pos % len(chars)
    rotate = {"0": "1", "1": "2", "9": "8", "a": "b", "b": "c", "f": "e"}
    chars[idx] = rotate.get(chars[idx], "x")
    return "".join(chars)


# ── Attack functions ─────────────────────────────────────────────────────────

def attack_a1_payload_bitflip() -> tuple[bool, str]:
    """Flip one character in the payload dict of event 5.
    Expected: verify_chain() returns False."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        event = json.loads(lines[4])
        event.setdefault("payload", {})["data"] = "MUTATED"
        lines[4] = json.dumps(event)
        write_lines(ledger, lines)
        detected = not ledger.verify_chain()
        return detected, "detected" if detected else "MISS: payload mutation undetected"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a2_event_hash_field_flip() -> tuple[bool, str]:
    """Flip one hex char in the event_hash field of event 3 without changing payload.
    Expected: verify_chain() returns False (stored hash ≠ recomputed hash)."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        event = json.loads(lines[2])
        event["event_hash"] = flip_hex_char(event["event_hash"], pos=7)
        lines[2] = json.dumps(event)
        write_lines(ledger, lines)
        # Verify from scratch (re-read file, don't trust in-memory state)
        detected = not JsonlWorkflowLedger(ledger.workspace_dir).verify_chain()
        return detected, "detected" if detected else "MISS: event_hash field flip undetected"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a3_event_insertion() -> tuple[bool, str]:
    """Insert a plausible-looking forged event between events 4 and 5.
    The forged event cannot have a valid event_hash without controlling compute_hash().
    Expected: verify_chain() returns False (forged hash doesn't match content)."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        prev_event = json.loads(lines[3])
        fake = {
            "event_id": "00000000-0000-0000-0000-000000000000",
            "kind": "brick",
            "ts": "2020-01-01T00:00:00Z",
            "sequence": prev_event["sequence"] + 1,
            "previous_hash": prev_event["event_hash"],
            "parent_hashes": [],
            "payload": {"injected": True, "data": "attacker-controlled"},
            # Attacker guesses an event_hash — cannot compute the real one without
            # knowing the canonical sort order and exact schema structure
            "event_hash": "aaaa" * 16,
        }
        lines.insert(4, json.dumps(fake))
        write_lines(ledger, lines)
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        detected = not fresh.verify_chain()
        return detected, "detected" if detected else "MISS: inserted event accepted"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a4_event_deletion() -> tuple[bool, str]:
    """Delete event 5 (0-indexed 4) from the middle of the chain.
    Expected: verify_chain() returns False (event 6's previous_hash no longer
    matches event 4's event_hash)."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        del lines[4]
        write_lines(ledger, lines)
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        detected = not fresh.verify_chain()
        return detected, "detected" if detected else "MISS: deleted event went unnoticed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a5_event_swap() -> tuple[bool, str]:
    """Swap adjacent events 4 and 5 (0-indexed 3 and 4).
    Expected: verify_chain() returns False (previous_hash links break)."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        if len(lines) < 5:
            return False, "SKIP: chain too short for swap test"
        lines[3], lines[4] = lines[4], lines[3]
        write_lines(ledger, lines)
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        detected = not fresh.verify_chain()
        return detected, "detected" if detected else "MISS: swapped events accepted"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a6_hash_field_substitution() -> tuple[bool, str]:
    """Copy event_hash from event 8 into event 4's event_hash field (payload unchanged).
    Expected: verify_chain() returns False (wrong hash stored, recomputed hash differs)."""
    tmp, ledger = build_chain()
    try:
        lines = read_lines(ledger)
        event4 = json.loads(lines[3])
        event8 = json.loads(lines[7])
        stolen_hash = event8["event_hash"]
        event4["event_hash"] = stolen_hash
        lines[3] = json.dumps(event4)
        write_lines(ledger, lines)
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        detected = not fresh.verify_chain()
        return detected, "detected" if detected else "MISS: substituted hash accepted"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a7_full_recompute() -> tuple[bool, str]:
    """
    Mutate event 5 and recompute all downstream hashes with write access after
    a semantic landing has committed the expected payload corpus.

    Expected: verify_chain() returns True, while verify_semantic() returns
    False because the sealed payload anchor no longer matches.
    """
    tmp, ledger = build_chain()
    try:
        principles = ledger.load_principles() or PrincipleSet("Chain integrity stress test")
        landing = create_landing(ledger, principles)
        events = [
            LedgerEvent.from_dict(json.loads(line))
            for line in read_lines(ledger)
        ]
        # Mutate event 5 (index 4)
        events[4].payload["data"] = "RECOMPUTED_ATTACK"
        recompute_from(events, start=4)
        new_lines = [json.dumps(ev.to_dict()) for ev in events]
        write_lines(ledger, new_lines)
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        chain_ok = fresh.verify_chain()
        semantic_ok, reason = landing.verify_semantic(fresh)
        passed = chain_ok and not semantic_ok
        if passed:
            return True, f"chain passes; semantic anchor detects content drift ({reason})"
        return False, f"chain_ok={chain_ok}; semantic_ok={semantic_ok}; reason={reason}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a8_tail_truncation() -> tuple[bool, str]:
    """
    Delete the last 3 protected events from the anchored corpus, then recompute
    the surviving chain including the landing event.

    Expected: verify_chain() returns True, while verify_semantic() returns
    False because event_count no longer matches the sealed landing metadata.
    """
    tmp, ledger = build_chain()
    try:
        principles = ledger.load_principles() or PrincipleSet("Chain integrity stress test")
        landing = create_landing(ledger, principles)
        lines = read_lines(ledger)
        if len(lines) < 8:
            return False, "SKIP: chain too short for tail-truncation test"
        events = [LedgerEvent.from_dict(json.loads(line)) for line in lines]
        landing_event = events[-1]
        protected_prefix = events[:-1]
        truncated = protected_prefix[:-3] + [landing_event]
        recompute_from(truncated, start=max(0, len(protected_prefix) - 3))
        write_lines(ledger, [json.dumps(ev.to_dict()) for ev in truncated])
        fresh = JsonlWorkflowLedger(ledger.workspace_dir)
        chain_ok = fresh.verify_chain()
        semantic_ok, reason = landing.verify_semantic(fresh)
        passed = chain_ok and not semantic_ok
        if passed:
            return True, f"chain passes; semantic anchor detects truncation ({reason})"
        return False, f"chain_ok={chain_ok}; semantic_ok={semantic_ok}; reason={reason}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Cold-start resume fidelity ───────────────────────────────────────────────

def test_r1_cold_start_resume() -> tuple[bool, str]:
    """
    Create a workspace in-process, then verify the resume pack loads and verifies
    inside a fresh subprocess — proving durability across process boundaries.
    """
    tmp = tempfile.mkdtemp(prefix="scbe-chain-bench-")
    ws = os.path.join(tmp, "workspace")
    os.makedirs(ws)
    ledger = new_ledger(
        ws,
        "Cold-start resume test",
        invariants=["chain valid on reload", "resume pack intact"],
    )
    try:
        for i in range(14):
            ledger.append("brick", {"step": i})
        ps = ledger.load_principles()
        create_landing(ledger, ps)
        build_resume_pack(ledger, session_hint="cold-start test")

        # Pass paths as JSON-encoded strings so backslashes survive subprocess launch.
        # The child process deliberately does not import SCBE modules. It verifies
        # the raw JSONL chain and resume pack by schema/hash rules only, which
        # makes the benchmark Kaggle-safe and proves cold-start portability.
        ws_j = json.dumps(ws)

        script = (
            "import hashlib, json, os\n"
            f"ws = {ws_j}\n"
            "lf = os.path.join(ws, '.scbe-longform')\n"
            "ledger_path = os.path.join(lf, 'ledger.jsonl')\n"
            "events = [json.loads(line) for line in open(ledger_path, encoding='utf-8') if line.strip()]\n"
            "prev = None\n"
            "for ev in events:\n"
            "    assert ev.get('previous_hash') == prev, 'previous_hash mismatch'\n"
            "    d = dict(ev); d['event_hash'] = ''\n"
            "    canon = json.dumps(d, sort_keys=True, separators=(',', ':'))\n"
            "    expected = hashlib.sha256(canon.encode()).hexdigest()\n"
            "    assert ev.get('event_hash') == expected, 'event_hash mismatch'\n"
            "    prev = ev.get('event_hash')\n"
            "pack_path = os.path.join(lf, 'resume', 'resume_pack.json')\n"
            "pack = json.load(open(pack_path, encoding='utf-8'))\n"
            "landing = pack['landing']\n"
            "d = dict(landing); d.pop('landing_hash', None)\n"
            "canon = json.dumps(d, sort_keys=True, separators=(',', ':'))\n"
            "assert landing['landing_hash'] == hashlib.sha256(canon.encode()).hexdigest(), 'landing integrity failed'\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip() == "ok":
            return True, "subprocess resumed, chain valid, landing verified"
        return False, f"subprocess failed: {result.stderr.strip()[:300]}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Performance table (non-scored) ───────────────────────────────────────────

def perf_depth_table(depths: list[int] | None = None) -> list[dict[str, Any]]:
    if depths is None:
        depths = [50, 100, 250, 500]
    rows = []
    for n in depths:
        tmp, ledger = build_chain(n_events=n)
        try:
            events = ledger.read_all()
            actual_depth = len(events)
            t0 = time.perf_counter()
            valid = ledger.verify_chain()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            rows.append({
                "requested_depth": n,
                "actual_events": actual_depth,
                "verify_chain_ok": valid,
                "verify_chain_ms": round(elapsed_ms, 3),
            })
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return rows


# ── Scoring ──────────────────────────────────────────────────────────────────

ATTACKS: list[tuple[str, str, int, Any]] = [
    # (id, label, points, fn)
    ("A1", "payload byte-flip → detect",          15, attack_a1_payload_bitflip),
    ("A2", "event_hash field flip → detect",       15, attack_a2_event_hash_field_flip),
    ("A3", "event insertion (no recompute) → detect", 15, attack_a3_event_insertion),
    ("A4", "event deletion → detect",              15, attack_a4_event_deletion),
    ("A5", "event swap → detect",                  10, attack_a5_event_swap),
    ("A6", "hash-field substitution → detect",     10, attack_a6_hash_field_substitution),
    ("A7", "full recompute → chain passes, semantic detects", 10, attack_a7_full_recompute),
    ("A8", "anchored truncation → chain passes, semantic detects", 5, attack_a8_tail_truncation),
]


def run_benchmark(skip_perf: bool = False) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    earned = 0
    max_score = sum(pts for _, _, pts, _ in ATTACKS) + 10  # + R1

    for attack_id, label, points, fn in ATTACKS:
        t0 = time.perf_counter()
        passed, note = fn()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        got = points if passed else 0
        earned += got
        results.append({
            "id": attack_id,
            "label": label,
            "passed": passed,
            "points_earned": got,
            "points_max": points,
            "note": note,
            "elapsed_ms": round(elapsed_ms, 3),
        })

    # Cold-start resume
    t0 = time.perf_counter()
    r1_ok, r1_note = test_r1_cold_start_resume()
    r1_ms = (time.perf_counter() - t0) * 1000
    r1_pts = 10 if r1_ok else 0
    earned += r1_pts
    r1_result = {
        "id": "R1",
        "label": "cold-start resume (subprocess)",
        "passed": r1_ok,
        "points_earned": r1_pts,
        "points_max": 10,
        "note": r1_note,
        "elapsed_ms": round(r1_ms, 3),
    }

    perf_rows: list[dict[str, Any]] = []
    if not skip_perf:
        perf_rows = perf_depth_table()

    report = {
        "schema_version": "scbe.longform_chain_integrity.v3",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "chain_depth_per_attack": CHAIN_DEPTH,
        "attacks": results,
        "resume": r1_result,
        "score": {
            "earned": earned,
            "max": max_score,
            "percent": round((earned / max_score) * 100, 2),
        },
        "semantic_anchor_note": {
            "A7": (
                "Recompute-from-mutation is intentionally still accepted by verify_chain(), "
                "but rejected by ContextLanding.verify_semantic() because the landing seals "
                "the ordered payload corpus."
            ),
            "A8": (
                "Anchored-prefix truncation is intentionally still accepted by verify_chain() "
                "after recomputation, but rejected by ContextLanding.verify_semantic() because "
                "the landing seals event_count and semantic_anchor."
            ),
        },
        "perf_table": perf_rows,
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCBE Chain Integrity Benchmark",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Score: **{report['score']['percent']}%** ({report['score']['earned']}/{report['score']['max']} pts)  ",
        f"Chain depth per attack: {report['chain_depth_per_attack']} events",
        "",
        "## Attack Results",
        "",
        "| ID | Label | Pass | Pts | Note |",
        "|---|---|---:|---:|---|",
    ]
    for a in report["attacks"] + [report["resume"]]:
        tick = "✓" if a["passed"] else "✗"
        lines.append(
            f"| {a['id']} | {a['label']} | {tick} "
            f"| {a['points_earned']}/{a['points_max']} "
            f"| {a['note'][:80]} |"
        )

    lines += ["", "## Semantic Anchor Layer", ""]
    for aid, text in report["semantic_anchor_note"].items():
        lines.append(f"**{aid}**: {text}")
        lines.append("")

    if report["perf_table"]:
        lines += [
            "## Performance Table (non-scored)",
            "",
            "| Events | verify_chain() ms |",
            "|---:|---:|",
        ]
        for row in report["perf_table"]:
            lines.append(f"| {row['actual_events']} | {row['verify_chain_ms']} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "benchmarks"))
    parser.add_argument("--skip-perf", action="store_true",
                        help="Skip the depth/time table (saves ~10 s)")
    parser.add_argument("--json-only", action="store_true",
                        help="Print JSON result to stdout, do not write files")
    args = parser.parse_args()

    report = run_benchmark(skip_perf=args.skip_perf)

    if args.json_only:
        print(json.dumps(report, indent=2))
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"longform_chain_integrity_{stamp}.json"
    md_path = out_dir / f"longform_chain_integrity_{stamp}.md"
    latest_json = out_dir / "longform_chain_integrity_latest.json"
    latest_md = out_dir / "longform_chain_integrity_latest.md"

    json_text = json.dumps(report, indent=2)
    md_text = render_markdown(report)
    for p in (json_path, latest_json):
        p.write_text(json_text + "\n", encoding="utf-8")
    for p in (md_path, latest_md):
        p.write_text(md_text + "\n", encoding="utf-8")

    summary = {
        "score_percent": report["score"]["percent"],
        "earned": report["score"]["earned"],
        "max": report["score"]["max"],
        "all_passed": all(a["passed"] for a in report["attacks"] + [report["resume"]]),
        "a7_semantic_detected": report["attacks"][6]["passed"],
        "a8_semantic_detected": report["attacks"][7]["passed"],
        "json": str(json_path),
        "markdown": str(md_path),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
