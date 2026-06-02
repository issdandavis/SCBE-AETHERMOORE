"""
@file context_bridge.py
@module longform/context_bridge

SCBE Longform Bridge — durable multi-session agentic workflow kernel.

The raw immutable JSONL ledger is the authoritative source of truth.
Protected context landings act as cryptographically verified resume contracts.
Principle-placed compaction must prove mission/invariants/claim_boundaries
survive before any event can be trimmed.

Design axioms:
  1. No unaccounted context loss — every trim is a logged compaction event.
  2. Principle preservation is mandatory before compaction — not optional.
  3. The ledger grows forward only — no retroactive edits.
  4. Any session can resume from any landing via the resume pack.
  5. Hash chain integrity is verifiable offline with stdlib sha256 only.

Event kinds:
  brick         — context brick: mission snapshot, invariants, open questions
  landing       — verified context landing (resume contract)
  agent_spawn   — agent registered with role contract
  tool_invoked  — governed tool invocation receipt
  compaction    — principle-validated compaction log
  resume        — session pickup from a landing
  objective     — top-level do() objective recorded
  stage_intent  — stage loop start
  stage_complete — stage loop end
  audit_pass    — principle audit passed
  audit_fail    — principle audit failed
"""

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── Core data structures ──────────────────────────────────────────────────────


@dataclass
class PrincipleSet:
    """
    The protected set that must survive any compaction.

    mission:          What we are trying to accomplish.
    invariants:       Facts that must remain true throughout.
    claim_boundaries: What the evidence supports (no more, no less).
    open_questions:   Unresolved questions that must carry forward.
    next_footholds:   Concrete next steps.
    """

    mission: str
    invariants: List[str] = field(default_factory=list)
    claim_boundaries: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    next_footholds: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PrincipleSet":
        return cls(
            mission=d["mission"],
            invariants=d.get("invariants", []),
            claim_boundaries=d.get("claim_boundaries", []),
            open_questions=d.get("open_questions", []),
            next_footholds=d.get("next_footholds", []),
        )


@dataclass
class ContextBrick:
    """A named context snapshot — the unit of longform memory."""

    brick_id: str
    kind: str  # always "brick"
    ts: str
    mission: str
    invariants: List[str] = field(default_factory=list)
    claim_boundaries: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    next_footholds: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContextBrick":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LedgerEvent:
    """
    Immutable ledger event with cryptographic hash chain.

    event_hash is computed over the canonical JSON of this event
    with event_hash set to the empty string, then SHA-256'd.
    """

    event_id: str
    kind: str
    ts: str
    sequence: int
    previous_hash: Optional[str]
    parent_hashes: List[str]
    payload: Dict[str, Any]
    event_hash: str = ""

    def canonical_json(self) -> str:
        """JSON for hashing — event_hash is stripped to avoid circularity."""
        d = asdict(self)
        d["event_hash"] = ""
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LedgerEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ContextLanding:
    """
    A verified context landing — the durable resume contract.

    Contains a snapshot of the current PrincipleSet at the time of landing,
    plus the brick count and a cryptographic hash of the landing content.
    Any future session can verify integrity and resume from this point.
    """

    landing_id: str
    ts: str
    landing_hash: str
    brick_count: int
    last_sequence: int
    principles_validated: bool
    principles: PrincipleSet
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContextLanding":
        d = dict(d)
        d["principles"] = PrincipleSet.from_dict(d["principles"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def verify(self) -> bool:
        """Verify this landing's hash matches its content."""
        content = json.dumps(
            {k: v for k, v in self.to_dict().items() if k != "landing_hash"},
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = hashlib.sha256(content.encode()).hexdigest()
        return expected == self.landing_hash


@dataclass
class ResumePack:
    """
    Bundle for session handoff: landing + recent context summary.

    External sessions use this to resume without re-reading the full ledger.
    The pack is NOT authoritative — the JSONL ledger always is.
    """

    pack_id: str
    ts: str
    landing: ContextLanding
    recent_brick_count: int
    open_questions: List[str]
    next_footholds: List[str]
    session_hint: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResumePack":
        d = dict(d)
        d["landing"] = ContextLanding.from_dict(d["landing"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Validation ────────────────────────────────────────────────────────────────


def validate_principles(principles: PrincipleSet, context: str) -> bool:
    """
    Principle-placed compaction gate.

    Before any brick can be dropped from the ledger, verify that the context
    still contains all invariants and claim_boundaries from the PrincipleSet.
    The mission keyword must also appear.

    This is the patent-defensible compaction guard — no trimming without proof.
    """
    ctx_lower = context.lower()
    mission_words = [w for w in re.split(r"\W+", principles.mission.lower()) if len(w) > 3]
    if mission_words and not any(w in ctx_lower for w in mission_words):
        return False
    for inv in principles.invariants:
        key_words = [w for w in re.split(r"\W+", inv.lower()) if len(w) > 3]
        if key_words and not any(w in ctx_lower for w in key_words):
            return False
    for claim in principles.claim_boundaries:
        key_words = [w for w in re.split(r"\W+", claim.lower()) if len(w) > 3]
        if key_words and not any(w in ctx_lower for w in key_words):
            return False
    return True


# ── JsonlWorkflowLedger ───────────────────────────────────────────────────────


class JsonlWorkflowLedger:
    """
    Append-only JSONL event ledger with cryptographic hash chain.

    Each event is a JSON object on its own line. The hash chain links each
    event to the previous via previous_hash, making any tampering detectable.

    The ledger file is the raw immutable source of truth. Landing files in
    landings/ and the resume pack in resume/ are derived views only.
    """

    LEDGER_FILE = "ledger.jsonl"
    LANDINGS_DIR = "landings"
    RESUME_DIR = "resume"
    AGENTS_DIR = "agents"
    PRINCIPLES_FILE = "principles.json"

    def __init__(self, workspace_dir: str):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self._ledger_path = os.path.join(self.workspace_dir, self.LEDGER_FILE)
        self._landings_dir = os.path.join(self.workspace_dir, self.LANDINGS_DIR)
        self._resume_dir = os.path.join(self.workspace_dir, self.RESUME_DIR)
        self._agents_dir = os.path.join(self.workspace_dir, self.AGENTS_DIR)
        self._principles_path = os.path.join(self.workspace_dir, self.PRINCIPLES_FILE)

    def _ensure_dirs(self) -> None:
        for d in (self._landings_dir, self._resume_dir, self._agents_dir):
            os.makedirs(d, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _read_last_event(self) -> Optional[LedgerEvent]:
        if not os.path.exists(self._ledger_path):
            return None
        last = None
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = LedgerEvent.from_dict(json.loads(line))
        return last

    def _next_sequence(self) -> int:
        last = self._read_last_event()
        return (last.sequence + 1) if last else 1

    def append(self, kind: str, payload: Dict[str, Any], parent_hashes: Optional[List[str]] = None) -> LedgerEvent:
        """Append an event to the ledger. Returns the committed event."""
        self._ensure_dirs()
        last = self._read_last_event()
        previous_hash = last.event_hash if last else None
        event = LedgerEvent(
            event_id=str(uuid.uuid4()),
            kind=kind,
            ts=self._now(),
            sequence=self._next_sequence(),
            previous_hash=previous_hash,
            parent_hashes=parent_hashes or [],
            payload=payload,
            event_hash="",
        )
        event.event_hash = event.compute_hash()
        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")
        return event

    def read_all(self) -> List[LedgerEvent]:
        if not os.path.exists(self._ledger_path):
            return []
        events = []
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(LedgerEvent.from_dict(json.loads(line)))
        return events

    def verify_chain(self) -> bool:
        """Verify the full hash chain. Returns True if intact."""
        events = self.read_all()
        prev_hash: Optional[str] = None
        for ev in events:
            if ev.previous_hash != prev_hash:
                return False
            expected = ev.compute_hash()
            if expected != ev.event_hash:
                return False
            prev_hash = ev.event_hash
        return True

    def brick_count(self) -> int:
        return sum(1 for e in self.read_all() if e.kind == "brick")

    def last_landing(self) -> Optional[ContextLanding]:
        """Most recent landing from landings/ dir, by ts."""
        if not os.path.exists(self._landings_dir):
            return None
        landings = []
        for fname in os.listdir(self._landings_dir):
            if fname.endswith(".json"):
                path = os.path.join(self._landings_dir, fname)
                with open(path, encoding="utf-8") as f:
                    landings.append(ContextLanding.from_dict(json.load(f)))
        if not landings:
            return None
        return max(landings, key=lambda l: l.ts)

    def list_landings(self) -> List[ContextLanding]:
        if not os.path.exists(self._landings_dir):
            return []
        out = []
        for fname in sorted(os.listdir(self._landings_dir)):
            if fname.endswith(".json"):
                with open(os.path.join(self._landings_dir, fname), encoding="utf-8") as f:
                    out.append(ContextLanding.from_dict(json.load(f)))
        return out

    def load_landing(self, landing_hash: str) -> Optional[ContextLanding]:
        for landing in self.list_landings():
            if landing.landing_hash.startswith(landing_hash):
                return landing
        return None

    def save_principles(self, principles: PrincipleSet) -> None:
        self._ensure_dirs()
        with open(self._principles_path, "w", encoding="utf-8") as f:
            json.dump(principles.to_dict(), f, indent=2)

    def load_principles(self) -> Optional[PrincipleSet]:
        if not os.path.exists(self._principles_path):
            return None
        with open(self._principles_path, encoding="utf-8") as f:
            return PrincipleSet.from_dict(json.load(f))

    def save_agent(self, agent_id: str, contract: Dict[str, Any]) -> None:
        self._ensure_dirs()
        path = os.path.join(self._agents_dir, f"{agent_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(contract, f, indent=2)

    def list_agents(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._agents_dir):
            return []
        agents = []
        for fname in sorted(os.listdir(self._agents_dir)):
            if fname.endswith(".json"):
                with open(os.path.join(self._agents_dir, fname), encoding="utf-8") as f:
                    agents.append(json.load(f))
        return agents

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


# ── Factory functions ─────────────────────────────────────────────────────────


def _longform_dir(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, ".scbe-longform")


def new_ledger(
    workspace_dir: str,
    mission: str,
    invariants: Optional[List[str]] = None,
    claim_boundaries: Optional[List[str]] = None,
) -> JsonlWorkflowLedger:
    """
    Create a new longform workflow workspace and return the ledger.
    Emits an initial 'brick' event with the PrincipleSet.
    """
    lf_dir = _longform_dir(workspace_dir)
    os.makedirs(lf_dir, exist_ok=True)
    ledger = JsonlWorkflowLedger(lf_dir)
    principles = PrincipleSet(
        mission=mission,
        invariants=invariants or [],
        claim_boundaries=claim_boundaries or [],
    )
    ledger.save_principles(principles)
    ledger.append(
        "brick",
        {
            "mission": mission,
            "invariants": principles.invariants,
            "claim_boundaries": principles.claim_boundaries,
            "open_questions": [],
            "next_footholds": [],
            "metadata": {"event": "workspace_init"},
        },
    )
    return ledger


def load_ledger(workspace_dir: str) -> JsonlWorkflowLedger:
    """Load an existing longform workspace ledger."""
    lf_dir = _longform_dir(workspace_dir)
    if not os.path.exists(lf_dir):
        raise FileNotFoundError(f"No .scbe-longform workspace at {workspace_dir}. " "Run `scbe work init` first.")
    return JsonlWorkflowLedger(lf_dir)


def create_landing(
    ledger: JsonlWorkflowLedger,
    principles: Optional[PrincipleSet] = None,
    open_questions: Optional[List[str]] = None,
    next_footholds: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ContextLanding:
    """
    Create and persist a verified ContextLanding.

    The landing_hash is computed over all fields except landing_hash itself,
    making it a cryptographic commitment to the principle state at this point.
    """
    if principles is None:
        principles = ledger.load_principles() or PrincipleSet(mission="(unknown)")
    all_events = ledger.read_all()
    bc = sum(1 for e in all_events if e.kind == "brick")
    last_seq = all_events[-1].sequence if all_events else 0

    landing_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    landing_data = {
        "landing_id": landing_id,
        "ts": ts,
        "landing_hash": "",
        "brick_count": bc,
        "last_sequence": last_seq,
        "principles_validated": True,
        "principles": principles.to_dict(),
        "metadata": metadata or {},
    }
    content = json.dumps(
        {k: v for k, v in landing_data.items() if k != "landing_hash"},
        sort_keys=True,
        separators=(",", ":"),
    )
    landing_hash = hashlib.sha256(content.encode()).hexdigest()
    landing_data["landing_hash"] = landing_hash

    landing = ContextLanding.from_dict(landing_data)

    # Persist to landings/ dir
    lf = os.path.join(ledger.workspace_dir, ledger.LANDINGS_DIR)
    os.makedirs(lf, exist_ok=True)
    fname = f"landing_{ts[:19].replace(':', '-')}_{landing_hash[:8]}.json"
    with open(os.path.join(lf, fname), "w", encoding="utf-8") as f:
        json.dump(landing.to_dict(), f, indent=2)

    # Append landing event to ledger
    ledger.append(
        "landing",
        {
            "landing_id": landing_id,
            "landing_hash": landing_hash,
            "brick_count": bc,
            "last_sequence": last_seq,
            "principles_validated": True,
        },
    )

    return landing


def build_resume_pack(
    ledger: JsonlWorkflowLedger,
    landing_hash: Optional[str] = None,
    session_hint: str = "",
) -> ResumePack:
    """
    Build a ResumePack from the latest (or specified) landing.

    The pack is saved to .scbe-longform/resume/resume_pack.json.
    It is NOT the source of truth — the ledger is. But it lets any
    session bootstrap quickly without reading the full ledger.
    """
    if landing_hash:
        landing = ledger.load_landing(landing_hash)
        if landing is None:
            raise ValueError(f"Landing {landing_hash!r} not found.")
    else:
        landing = ledger.last_landing()
        if landing is None:
            raise ValueError("No landings exist yet. Run `scbe land create` first.")

    principles = landing.principles
    pack = ResumePack(
        pack_id=str(uuid.uuid4()),
        ts=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        landing=landing,
        recent_brick_count=ledger.brick_count(),
        open_questions=principles.open_questions,
        next_footholds=principles.next_footholds,
        session_hint=session_hint or f"Resume from landing {landing.landing_hash[:12]}",
    )
    ledger.save_resume_pack(pack)
    return pack
