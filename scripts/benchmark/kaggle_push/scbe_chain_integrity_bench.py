#!/usr/bin/env python3
"""
SCBE Aethermoore -- Chain Integrity Benchmark (Kaggle Edition)
==============================================================
Self-contained. All code inlined from src/longform/context_bridge.py.
Stdlib only -- no external packages required.

Covers:
  Hash-chain structural integrity (A1-A8)  -- 8 attack classes
  Semantic anchor layer (S1-S3)            -- closes A7/A8 gap
  Cold-start resume fidelity (R1)          -- cross-load durability
  Performance table (P0)                   -- O(n) scaling to 1000 events
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =============================================================================
# CORE: context_bridge inlined
# =============================================================================

@dataclass
class PrincipleSet:
    mission: str
    invariants: List[str] = field(default_factory=list)
    claim_boundaries: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    next_footholds: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(
            mission=d["mission"],
            invariants=d.get("invariants", []),
            claim_boundaries=d.get("claim_boundaries", []),
            open_questions=d.get("open_questions", []),
            next_footholds=d.get("next_footholds", []),
        )


@dataclass
class LedgerEvent:
    event_id: str
    kind: str
    ts: str
    sequence: int
    previous_hash: Optional[str]
    parent_hashes: List[str]
    payload: Dict[str, Any]
    event_hash: str = ""

    def canonical_json(self) -> str:
        d = asdict(self)
        d["event_hash"] = ""
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ContextLanding:
    landing_id: str
    ts: str
    landing_hash: str
    brick_count: int
    last_sequence: int
    principles_validated: bool
    principles: PrincipleSet
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["principles"] = PrincipleSet.from_dict(d["principles"])
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})

    def verify(self) -> bool:
        content = json.dumps(
            {k: v for k, v in self.to_dict().items() if k != "landing_hash"},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(content.encode()).hexdigest() == self.landing_hash

    def verify_semantic(self, ledger) -> tuple:
        """Verify semantic anchor against current ledger.

        Detects A7 (full recompute) and A8 (tail truncation) which both
        pass verify_chain() alone. Uses last_sequence as the scope boundary
        so the landing event appended after anchor computation is excluded.
        """
        anchor = self.metadata.get("semantic_anchor", "")
        if not anchor:
            return (True, "no anchor (pre-semantic landing)")
        scoped = [e for e in ledger.read_all() if e.sequence <= self.last_sequence]
        expected_count = self.metadata.get("event_count")
        if expected_count is not None and len(scoped) != expected_count:
            return (False, f"event count: expected {expected_count}, got {len(scoped)}")
        if _compute_semantic_anchor(scoped) != anchor:
            return (False, "semantic anchor mismatch: payload corpus changed")
        return (True, "ok")


@dataclass
class ResumePack:
    pack_id: str
    ts: str
    landing: ContextLanding
    recent_brick_count: int
    open_questions: List[str]
    next_footholds: List[str]
    session_hint: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["landing"] = ContextLanding.from_dict(d["landing"])
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


def _compute_semantic_anchor(events: List[LedgerEvent]) -> str:
    """SHA-256 of ordered payload corpus (NUL-delimited JSON).

    Detects A7 (full hash recompute after mutation) and A8 (tail truncation):
    both attacks pass verify_chain() but produce a different payload fingerprint.
    Committed inside landing_hash so the anchor itself is cryptographically sealed.
    """
    parts = [
        json.dumps(ev.payload, sort_keys=True, separators=(",", ":"))
        for ev in events
    ]
    return hashlib.sha256(("\x00".join(parts)).encode()).hexdigest()


class JsonlWorkflowLedger:
    LEDGER_FILE = "ledger.jsonl"
    LANDINGS_DIR = "landings"
    RESUME_DIR = "resume"
    PRINCIPLES_FILE = "principles.json"

    def __init__(self, workspace_dir: str):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self._ledger_path = os.path.join(self.workspace_dir, self.LEDGER_FILE)
        self._landings_dir = os.path.join(self.workspace_dir, self.LANDINGS_DIR)
        self._resume_dir = os.path.join(self.workspace_dir, self.RESUME_DIR)
        self._principles_path = os.path.join(self.workspace_dir, self.PRINCIPLES_FILE)

    def _ensure_dirs(self):
        for d in (self._landings_dir, self._resume_dir):
            os.makedirs(d, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _read_last_event(self) -> Optional[LedgerEvent]:
        if not os.path.exists(self._ledger_path):
            return None
        last = None
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    last = LedgerEvent.from_dict(json.loads(s))
        return last

    def append(self, kind: str, payload: Dict[str, Any], parent_hashes=None) -> LedgerEvent:
        self._ensure_dirs()
        last = self._read_last_event()
        ev = LedgerEvent(
            event_id=str(uuid.uuid4()), kind=kind, ts=self._now(),
            sequence=(last.sequence + 1) if last else 1,
            previous_hash=last.event_hash if last else None,
            parent_hashes=parent_hashes or [], payload=payload, event_hash="",
        )
        ev.event_hash = ev.compute_hash()
        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev.to_dict()) + "\n")
        return ev

    def read_all(self) -> List[LedgerEvent]:
        if not os.path.exists(self._ledger_path):
            return []
        out = []
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    out.append(LedgerEvent.from_dict(json.loads(s)))
        return out

    def verify_chain(self) -> bool:
        prev = None
        for ev in self.read_all():
            if ev.previous_hash != prev or ev.compute_hash() != ev.event_hash:
                return False
            prev = ev.event_hash
        return True

    def brick_count(self) -> int:
        return sum(1 for e in self.read_all() if e.kind == "brick")

    def save_principles(self, p: PrincipleSet):
        self._ensure_dirs()
        with open(self._principles_path, "w", encoding="utf-8") as f:
            json.dump(p.to_dict(), f, indent=2)

    def load_principles(self) -> Optional[PrincipleSet]:
        if not os.path.exists(self._principles_path):
            return None
        with open(self._principles_path, encoding="utf-8") as f:
            return PrincipleSet.from_dict(json.load(f))

    def last_landing(self) -> Optional[ContextLanding]:
        if not os.path.exists(self._landings_dir):
            return None
        out = []
        for fn in os.listdir(self._landings_dir):
            if fn.endswith(".json"):
                with open(os.path.join(self._landings_dir, fn), encoding="utf-8") as f:
                    out.append(ContextLanding.from_dict(json.load(f)))
        return max(out, key=lambda lnd: lnd.ts) if out else None

    def save_resume_pack(self, pack: ResumePack) -> str:
        self._ensure_dirs()
        path = os.path.join(self._resume_dir, "resume_pack.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pack.to_dict(), f, indent=2)
        return path

    def load_resume_pack(self) -> Optional[ResumePack]:
        path = os.path.join(self._resume_dir, "resume_pack.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return ResumePack.from_dict(json.load(f))


def _lf(ws: str) -> str:
    return os.path.join(ws, ".scbe-longform")


def new_ledger(ws: str, mission: str, invariants=None, claim_boundaries=None):
    lf = _lf(ws)
    os.makedirs(lf, exist_ok=True)
    ledger = JsonlWorkflowLedger(lf)
    p = PrincipleSet(
        mission=mission,
        invariants=invariants or [],
        claim_boundaries=claim_boundaries or [],
    )
    ledger.save_principles(p)
    ledger.append("brick", {
        "mission": mission, "invariants": p.invariants,
        "claim_boundaries": p.claim_boundaries, "open_questions": [],
        "next_footholds": [], "metadata": {"event": "workspace_init"},
    })
    return ledger


def load_ledger(ws: str):
    lf = _lf(ws)
    if not os.path.exists(lf):
        raise FileNotFoundError(f"No .scbe-longform at {ws}")
    return JsonlWorkflowLedger(lf)


def create_landing(ledger, principles=None, metadata=None):
    if principles is None:
        principles = ledger.load_principles() or PrincipleSet(mission="(unknown)")
    all_events = ledger.read_all()
    bc = sum(1 for e in all_events if e.kind == "brick")
    last_seq = all_events[-1].sequence if all_events else 0
    meta = dict(metadata or {})
    meta["event_count"] = len(all_events)
    meta["semantic_anchor"] = _compute_semantic_anchor(all_events)
    lid = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ld = {
        "landing_id": lid, "ts": ts, "landing_hash": "",
        "brick_count": bc, "last_sequence": last_seq,
        "principles_validated": True, "principles": principles.to_dict(), "metadata": meta,
    }
    content = json.dumps(
        {k: v for k, v in ld.items() if k != "landing_hash"},
        sort_keys=True, separators=(",", ":"),
    )
    ld["landing_hash"] = hashlib.sha256(content.encode()).hexdigest()
    landing = ContextLanding.from_dict(ld)
    ldir = os.path.join(ledger.workspace_dir, ledger.LANDINGS_DIR)
    os.makedirs(ldir, exist_ok=True)
    fname = f"landing_{ts[:19].replace(':', '-')}_{ld['landing_hash'][:8]}.json"
    with open(os.path.join(ldir, fname), "w", encoding="utf-8") as f:
        json.dump(landing.to_dict(), f, indent=2)
    ledger.append("landing", {
        "landing_id": lid, "landing_hash": ld["landing_hash"],
        "brick_count": bc, "last_sequence": last_seq, "principles_validated": True,
    })
    return landing


def build_resume_pack(ledger, session_hint=""):
    landing = ledger.last_landing()
    if landing is None:
        raise ValueError("No landings.")
    pack = ResumePack(
        pack_id=str(uuid.uuid4()),
        ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        landing=landing, recent_brick_count=ledger.brick_count(),
        open_questions=landing.principles.open_questions,
        next_footholds=landing.principles.next_footholds,
        session_hint=session_hint or f"Resume from {landing.landing_hash[:12]}",
    )
    ledger.save_resume_pack(pack)
    return pack


# =============================================================================
# BENCHMARK HELPERS
# =============================================================================

CHAIN_DEPTH = 20


def build_chain(n=CHAIN_DEPTH):
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    lg = new_ledger(ws, "Chain integrity bench", invariants=["append-only", "no deletions"])
    for i in range(n - 1):
        lg.append("brick", {"seq": i, "data": f"payload-{i}"})
    return tmp, lg


def rlines(lg):
    return open(lg._ledger_path, encoding="utf-8").read().splitlines()


def wlines(lg, lines):
    open(lg._ledger_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def flip(s, pos=7):
    c = list(s)
    i = pos % len(c)
    c[i] = {"0": "1", "1": "2", "9": "8", "a": "b", "b": "c", "f": "e"}.get(c[i], "x")
    return "".join(c)


# =============================================================================
# ATTACK FUNCTIONS  (A1-A6: detect; A7-A8: chain fools, anchor catches)
# =============================================================================

def attack_a1():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        ev = json.loads(lines[4])
        ev.setdefault("payload", {})["data"] = "MUTATED"
        lines[4] = json.dumps(ev)
        wlines(lg, lines)
        det = not lg.verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a2():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        ev = json.loads(lines[2])
        ev["event_hash"] = flip(ev["event_hash"])
        lines[2] = json.dumps(ev)
        wlines(lg, lines)
        det = not JsonlWorkflowLedger(lg.workspace_dir).verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a3():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        prev = json.loads(lines[3])
        fake = {
            "event_id": "00000000-0000-0000-0000-000000000000", "kind": "brick",
            "ts": "2020-01-01T00:00:00Z", "sequence": prev["sequence"] + 1,
            "previous_hash": prev["event_hash"], "parent_hashes": [],
            "payload": {"injected": True}, "event_hash": "aaaa" * 16,
        }
        lines.insert(4, json.dumps(fake))
        wlines(lg, lines)
        det = not JsonlWorkflowLedger(lg.workspace_dir).verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a4():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        del lines[4]
        wlines(lg, lines)
        det = not JsonlWorkflowLedger(lg.workspace_dir).verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a5():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        lines[3], lines[4] = lines[4], lines[3]
        wlines(lg, lines)
        det = not JsonlWorkflowLedger(lg.workspace_dir).verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a6():
    tmp, lg = build_chain()
    try:
        lines = rlines(lg)
        ev4, ev8 = json.loads(lines[3]), json.loads(lines[7])
        ev4["event_hash"] = ev8["event_hash"]
        lines[3] = json.dumps(ev4)
        wlines(lg, lines)
        det = not JsonlWorkflowLedger(lg.workspace_dir).verify_chain()
        return det, "detected" if det else "MISS"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a7():
    """Full recompute: chain passes, semantic anchor must catch it."""
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    lg = new_ledger(ws, "A7 full recompute", invariants=["integrity"])
    try:
        for i in range(14):
            lg.append("brick", {"i": i, "data": f"d-{i}"})
        landing = create_landing(lg)
        events = [LedgerEvent.from_dict(json.loads(l)) for l in rlines(lg)]
        events[4].payload["data"] = "RECOMPUTED_ATTACK"
        for i in range(4, len(events)):
            if i > 0:
                events[i].previous_hash = events[i - 1].event_hash
            events[i].event_hash = events[i].compute_hash()
        wlines(lg, [json.dumps(e.to_dict()) for e in events])
        fresh = JsonlWorkflowLedger(lg.workspace_dir)
        chain_ok = fresh.verify_chain()
        sem_ok, reason = landing.verify_semantic(fresh)
        passed = chain_ok and not sem_ok
        return passed, f"chain={chain_ok} sem=({sem_ok}, '{reason}')"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def attack_a8():
    """Tail truncation: chain passes, semantic anchor must catch it."""
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    lg = new_ledger(ws, "A8 tail truncation", invariants=["integrity"])
    try:
        for i in range(14):
            lg.append("brick", {"i": i})
        landing = create_landing(lg)
        lines = rlines(lg)
        wlines(lg, lines[:-3])
        fresh = JsonlWorkflowLedger(lg.workspace_dir)
        chain_ok = fresh.verify_chain()
        sem_ok, reason = landing.verify_semantic(fresh)
        passed = chain_ok and not sem_ok
        return passed, f"chain={chain_ok} sem=({sem_ok}, '{reason}')"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# SEMANTIC ANCHOR TESTS
# =============================================================================

def semantic_s1():
    """Intact chain: verify_semantic must return (True, 'ok')."""
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    try:
        lg = new_ledger(ws, "S1 baseline", invariants=["integrity"])
        for i in range(12):
            lg.append("brick", {"i": i})
        landing = create_landing(lg)
        ok, reason = landing.verify_semantic(JsonlWorkflowLedger(lg.workspace_dir))
        return ok, reason
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def semantic_s2():
    """After A7 mutation, verify_semantic detects while verify_chain passes."""
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    try:
        lg = new_ledger(ws, "S2", invariants=["integrity"])
        for i in range(12):
            lg.append("brick", {"i": i, "data": f"d-{i}"})
        landing = create_landing(lg)
        events = [LedgerEvent.from_dict(json.loads(l)) for l in rlines(lg)]
        events[4].payload["data"] = "RECOMPUTED"
        for i in range(4, len(events)):
            if i > 0:
                events[i].previous_hash = events[i - 1].event_hash
            events[i].event_hash = events[i].compute_hash()
        wlines(lg, [json.dumps(e.to_dict()) for e in events])
        fresh = JsonlWorkflowLedger(lg.workspace_dir)
        chain_ok = fresh.verify_chain()
        sem_ok, reason = landing.verify_semantic(fresh)
        caught = chain_ok and not sem_ok
        return caught, f"chain={chain_ok} sem=({sem_ok}, '{reason}')"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def semantic_s3():
    """After A8 truncation, verify_semantic detects while verify_chain passes."""
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    try:
        lg = new_ledger(ws, "S3", invariants=["integrity"])
        for i in range(12):
            lg.append("brick", {"i": i})
        landing = create_landing(lg)
        lines = rlines(lg)
        wlines(lg, lines[:-3])
        fresh = JsonlWorkflowLedger(lg.workspace_dir)
        chain_ok = fresh.verify_chain()
        sem_ok, reason = landing.verify_semantic(fresh)
        caught = chain_ok and not sem_ok
        return caught, f"chain={chain_ok} sem=({sem_ok}, '{reason}')"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# RESUME FIDELITY
# =============================================================================

def test_r1():
    tmp = tempfile.mkdtemp(prefix="scbe-")
    ws = os.path.join(tmp, "ws")
    os.makedirs(ws)
    try:
        lg = new_ledger(ws, "R1 cold-start", invariants=["chain valid on reload"])
        for i in range(14):
            lg.append("brick", {"step": i})
        create_landing(lg)
        build_resume_pack(lg, session_hint="cold-start")
        lg2 = load_ledger(ws)
        if not lg2.verify_chain():
            return False, "chain invalid on reload"
        pack = lg2.load_resume_pack()
        if pack is None:
            return False, "no resume pack"
        if not pack.landing.verify():
            return False, "landing integrity failed"
        sem_ok, sem_reason = pack.landing.verify_semantic(lg2)
        if not sem_ok:
            return False, f"semantic check failed: {sem_reason}"
        return True, "chain valid, landing verified, semantic anchor ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# PERFORMANCE TABLE
# =============================================================================

def perf_table(depths=(50, 100, 250, 500, 1000)):
    rows = []
    for n in depths:
        tmp, lg = build_chain(n)
        try:
            events = lg.read_all()
            t0 = time.perf_counter()
            ok = lg.verify_chain()
            ms = (time.perf_counter() - t0) * 1000
            rows.append({
                "depth": len(events),
                "ms": round(ms, 3),
                "us_per_event": round(ms * 1000 / max(len(events), 1), 2),
                "ok": ok,
            })
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return rows


# =============================================================================
# RUN
# =============================================================================

ATTACKS = [
    ("A1", "payload byte-flip                  -> detect",       15, attack_a1),
    ("A2", "event_hash field flip              -> detect",       15, attack_a2),
    ("A3", "event insertion (no recompute)     -> detect",       15, attack_a3),
    ("A4", "event deletion                    -> detect",       15, attack_a4),
    ("A5", "adjacent swap                     -> detect",       10, attack_a5),
    ("A6", "hash-field substitution           -> detect",       10, attack_a6),
    ("A7", "full recompute (chain/anchor)     -> two-phase",    10, attack_a7),
    ("A8", "tail truncation (chain/anchor)    -> two-phase",     5, attack_a8),
]
SEMANTIC = [
    ("S1", "baseline verify_semantic passes",                   10, semantic_s1),
    ("S2", "A7 mutation caught by anchor",                      10, semantic_s2),
    ("S3", "A8 truncation caught by anchor",                    10, semantic_s3),
]
RESUME = [
    ("R1", "cold-start resume (fresh load + semantic check)",   10, test_r1),
]

print("=" * 72)
print("SCBE Aethermoore -- Chain Integrity Benchmark")
print(f"Generated : {datetime.now(timezone.utc).isoformat()}")
print(f"Python    : {sys.version.split()[0]}")
print(f"Chain depth per attack: {CHAIN_DEPTH} events")
print("=" * 72)

earned = 0
total = 0
all_results = []

for suite, label in [
    (ATTACKS,  "Hash-Chain Structural Integrity"),
    (SEMANTIC, "Semantic Anchor Layer"),
    (RESUME,   "Resume Fidelity"),
]:
    print(f"\n  {label}")
    print(f"  {'ID':<4} {'Label':<50} {'':>4} {'Pts':>5}  Note")
    print("  " + "-" * 70)
    for tid, desc, pts, fn in suite:
        passed, note = fn()
        got = pts if passed else 0
        earned += got
        total += pts
        tick = "PASS" if passed else "FAIL"
        all_results.append({"id": tid, "passed": passed, "pts": got, "max": pts})
        print(f"  {tid:<4} {desc:<50} {tick:>4} {got:>2}/{pts:<2}  {note[:55]}")

print()
print("=" * 72)
print(f"TOTAL : {earned}/{total}  ({round(earned / total * 100, 1)}%)")
print(f"PASS  : {sum(1 for r in all_results if r['passed'])}/{len(all_results)} tests")

print()
print("  Design notes:")
print("  A7/A8 are two-phase: verify_chain() is fooled (known structural gap),")
print("  verify_semantic() catches it (semantic anchor committed in landing_hash).")
print("  The anchor is SHA-256 of the ordered payload corpus, scoped to")
print("  last_sequence so the landing event itself is excluded from the check.")

print()
print("  Performance Table -- verify_chain() O(n) scaling")
print(f"  {'Events':>8}  {'ms':>8}  {'us/event':>10}  {'OK':>4}")
print("  " + "-" * 38)
for row in perf_table():
    print(f"  {row['depth']:>8}  {row['ms']:>8.3f}  {row['us_per_event']:>10.2f}  {str(row['ok']):>4}")

print()
result = {
    "schema_version": "scbe.chain_integrity_bench.kaggle.v1",
    "score": f"{earned}/{total}",
    "pct": round(earned / total * 100, 1),
    "all_passed": all(r["passed"] for r in all_results),
    "results": all_results,
}
print("JSON:", json.dumps(result))
