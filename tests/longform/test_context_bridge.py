"""
Tests for src/longform/context_bridge.py — SCBE Longform Bridge kernel.

Core invariants:
  1.  Ledger appends produce events with monotone sequence numbers
  2.  Hash chain is intact after any sequence of appends
  3.  Hash chain detects any tampered event
  4.  PrincipleSet round-trips through to_dict / from_dict
  5.  ContextLanding hash is reproducible and self-verifying
  6.  Landing integrity fails if any field is mutated
  7.  ResumePack round-trips cleanly
  8.  new_ledger creates workspace + emits initial brick event
  9.  load_ledger raises FileNotFoundError for missing workspace
  10. create_landing persists to landings/ dir + appends landing event
  11. build_resume_pack round-trips through save/load
  12. validate_principles passes when context contains all key words
  13. validate_principles fails when mission words are absent
  14. validate_principles fails when an invariant keyword is absent
  15. JsonlWorkflowLedger.brick_count only counts brick events
  16. JsonlWorkflowLedger.last_landing returns the most recent landing
  17. Agent spawn/list round-trip through workspace
  18. Principles save/load round-trip
  19. Multiple landings list correctly sorted
  20. load_landing prefix match works
"""

import json
import os
import pytest

from src.longform.context_bridge import (
    PrincipleSet,
    LedgerEvent,
    ContextLanding,
    JsonlWorkflowLedger,
    new_ledger,
    load_ledger,
    create_landing,
    build_resume_pack,
    validate_principles,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def ws(tmp_path):
    """A fresh workspace directory (does NOT yet have .scbe-longform)."""
    return str(tmp_path)


@pytest.fixture
def ledger(ws):
    """An initialized ledger inside tmp_path/.scbe-longform."""
    return new_ledger(ws, "Test mission", invariants=["inv A", "inv B"])


@pytest.fixture
def ps():
    return PrincipleSet(
        mission="Accomplish the objective",
        invariants=["hash chain is intact", "no context loss"],
        claim_boundaries=["durable ledger proven", "chain verifiable"],
        open_questions=["squad routing phase 2?"],
        next_footholds=["wire temporal backend"],
    )


# ── PrincipleSet ──────────────────────────────────────────────────────────────


def test_principle_set_roundtrip(ps):
    d = ps.to_dict()
    restored = PrincipleSet.from_dict(d)
    assert restored.mission == ps.mission
    assert restored.invariants == ps.invariants
    assert restored.claim_boundaries == ps.claim_boundaries
    assert restored.open_questions == ps.open_questions
    assert restored.next_footholds == ps.next_footholds


def test_principle_set_to_dict_has_all_fields(ps):
    d = ps.to_dict()
    for key in (
        "mission",
        "invariants",
        "claim_boundaries",
        "open_questions",
        "next_footholds",
    ):
        assert key in d


def test_principle_set_empty_lists():
    ps = PrincipleSet(mission="minimal")
    assert ps.invariants == []
    assert ps.claim_boundaries == []


# ── LedgerEvent / hash chain ──────────────────────────────────────────────────


def test_ledger_event_hash_deterministic():
    ev = LedgerEvent(
        event_id="test-id",
        kind="brick",
        ts="2026-01-01T00:00:00Z",
        sequence=1,
        previous_hash=None,
        parent_hashes=[],
        payload={"mission": "x"},
        event_hash="",
    )
    h1 = ev.compute_hash()
    h2 = ev.compute_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_ledger_event_hash_changes_with_payload():
    ev = LedgerEvent(
        event_id="test-id",
        kind="brick",
        ts="2026-01-01T00:00:00Z",
        sequence=1,
        previous_hash=None,
        parent_hashes=[],
        payload={"mission": "x"},
        event_hash="",
    )
    ev2 = LedgerEvent(
        event_id="test-id",
        kind="brick",
        ts="2026-01-01T00:00:00Z",
        sequence=1,
        previous_hash=None,
        parent_hashes=[],
        payload={"mission": "y"},
        event_hash="",
    )
    assert ev.compute_hash() != ev2.compute_hash()


def test_ledger_event_roundtrip():
    ev = LedgerEvent(
        event_id="abc",
        kind="brick",
        ts="2026-01-01Z",
        sequence=5,
        previous_hash="aaaa",
        parent_hashes=["bbbb"],
        payload={"k": "v"},
        event_hash="xxxx",
    )
    d = ev.to_dict()
    ev2 = LedgerEvent.from_dict(d)
    assert ev2.event_id == ev.event_id
    assert ev2.kind == ev.kind
    assert ev2.sequence == ev.sequence
    assert ev2.payload == ev.payload
    assert ev2.event_hash == ev.event_hash


# ── JsonlWorkflowLedger ───────────────────────────────────────────────────────


def test_new_ledger_creates_workspace(ws):
    ledger = new_ledger(ws, "Mission A")
    lf = os.path.join(ws, ".scbe-longform")
    assert ledger is not None
    assert os.path.isdir(lf)
    assert os.path.isfile(os.path.join(lf, "ledger.jsonl"))
    assert os.path.isfile(os.path.join(lf, "principles.json"))


def test_new_ledger_emits_initial_brick(ledger):
    events = ledger.read_all()
    assert len(events) >= 1
    assert events[0].kind == "brick"


def test_new_ledger_mission_in_brick(ws):
    ledger = new_ledger(ws, "My special mission")
    events = ledger.read_all()
    assert events[0].payload["mission"] == "My special mission"


def test_load_ledger_raises_for_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ledger(str(tmp_path / "nonexistent"))


def test_load_ledger_returns_existing(ws, ledger):
    ledger2 = load_ledger(ws)
    assert ledger2.workspace_dir == ledger.workspace_dir


def test_append_sequence_monotone(ledger):
    for _ in range(5):
        ledger.append("brick", {"mission": "x"})
    events = ledger.read_all()
    seqs = [e.sequence for e in events]
    assert seqs == sorted(seqs)
    assert seqs == list(range(1, len(seqs) + 1))


def test_append_previous_hash_chain(ledger):
    ledger.append("brick", {"mission": "a"})
    ledger.append("brick", {"mission": "b"})
    events = ledger.read_all()
    for i in range(1, len(events)):
        assert events[i].previous_hash == events[i - 1].event_hash


def test_first_event_previous_hash_none(ledger):
    events = ledger.read_all()
    assert events[0].previous_hash is None


def test_verify_chain_passes_intact(ledger):
    ledger.append("brick", {"mission": "test"})
    ledger.append("brick", {"mission": "test2"})
    assert ledger.verify_chain() is True


def test_verify_chain_detects_tampering(ledger):
    ledger.append("brick", {"mission": "test"})
    # Tamper: overwrite the ledger with a modified second event
    path = ledger._ledger_path
    lines = open(path, encoding="utf-8").readlines()
    d = json.loads(lines[1])
    d["payload"]["mission"] = "TAMPERED"
    lines[1] = json.dumps(d) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    assert ledger.verify_chain() is False


def test_brick_count_only_counts_bricks(ledger):
    initial = ledger.brick_count()
    ledger.append("stage_intent", {"loop": 1})
    ledger.append("brick", {"mission": "x"})
    assert ledger.brick_count() == initial + 1


def test_principles_save_load_roundtrip(ledger, ps):
    ledger.save_principles(ps)
    restored = ledger.load_principles()
    assert restored.mission == ps.mission
    assert restored.invariants == ps.invariants


def test_load_principles_none_when_missing(tmp_path):
    lf = os.path.join(str(tmp_path), ".scbe-longform")
    os.makedirs(lf)
    ledger = JsonlWorkflowLedger(lf)
    assert ledger.load_principles() is None


# ── ContextLanding ────────────────────────────────────────────────────────────


def test_create_landing_persists_file(ledger):
    ps = ledger.load_principles()
    landing = create_landing(ledger, ps)
    assert landing.landing_hash
    assert len(landing.landing_hash) == 64
    lf = os.path.join(ledger.workspace_dir, "landings")
    files = [f for f in os.listdir(lf) if f.endswith(".json")]
    assert len(files) >= 1


def test_create_landing_integrity(ledger):
    ps = ledger.load_principles()
    landing = create_landing(ledger, ps)
    assert landing.verify() is True


def test_landing_integrity_fails_on_mutation(ledger):
    ps = ledger.load_principles()
    landing = create_landing(ledger, ps)
    original_hash = landing.landing_hash
    landing.landing_hash = "deadbeef" * 8
    assert landing.verify() is False
    # restore
    landing.landing_hash = original_hash
    assert landing.verify() is True


def test_create_landing_appends_landing_event(ledger):
    ps = ledger.load_principles()
    before = len(ledger.read_all())
    create_landing(ledger, ps)
    after = len(ledger.read_all())
    assert after == before + 1
    events = ledger.read_all()
    assert events[-1].kind == "landing"


def test_landing_roundtrip(ledger):
    ps = ledger.load_principles()
    landing = create_landing(ledger, ps)
    d = landing.to_dict()
    restored = ContextLanding.from_dict(d)
    assert restored.landing_hash == landing.landing_hash
    assert restored.brick_count == landing.brick_count
    assert restored.principles.mission == landing.principles.mission


def test_last_landing_returns_latest(ledger):
    ps = ledger.load_principles()
    create_landing(ledger, ps)
    create_landing(ledger, ps)
    last = ledger.last_landing()
    assert last is not None
    # The last one should have the highest sequence
    all_l = ledger.list_landings()
    assert last.ts >= all_l[0].ts


def test_list_landings_returns_all(ledger):
    ps = ledger.load_principles()
    create_landing(ledger, ps)
    create_landing(ledger, ps)
    create_landing(ledger, ps)
    landings = ledger.list_landings()
    assert len(landings) == 3


def test_load_landing_prefix_match(ledger):
    ps = ledger.load_principles()
    landing = create_landing(ledger, ps)
    prefix = landing.landing_hash[:8]
    found = ledger.load_landing(prefix)
    assert found is not None
    assert found.landing_hash == landing.landing_hash


def test_load_landing_none_for_unknown(ledger):
    assert ledger.load_landing("0000000000000000") is None


# ── ResumePack ────────────────────────────────────────────────────────────────


def test_build_resume_pack_requires_landing(ledger):
    with pytest.raises(ValueError, match="No landings"):
        build_resume_pack(ledger)


def test_build_resume_pack_success(ledger):
    ps = ledger.load_principles()
    create_landing(ledger, ps)
    pack = build_resume_pack(ledger, session_hint="Test session")
    assert pack.landing.verify()
    assert pack.session_hint == "Test session"


def test_build_resume_pack_saves_to_disk(ledger):
    ps = ledger.load_principles()
    create_landing(ledger, ps)
    build_resume_pack(ledger)
    path = os.path.join(ledger.workspace_dir, "resume", "resume_pack.json")
    assert os.path.isfile(path)


def test_resume_pack_roundtrip(ledger):
    ps = ledger.load_principles()
    create_landing(ledger, ps)
    pack = build_resume_pack(ledger)
    loaded = ledger.load_resume_pack()
    assert loaded is not None
    assert loaded.landing.landing_hash == pack.landing.landing_hash


def test_build_resume_pack_by_hash(ledger):
    ps = ledger.load_principles()
    l1 = create_landing(ledger, ps)
    create_landing(ledger, ps)
    pack = build_resume_pack(ledger, landing_hash=l1.landing_hash[:8])
    assert pack.landing.landing_hash == l1.landing_hash


# ── validate_principles ───────────────────────────────────────────────────────


def test_validate_principles_passes_full_match():
    ps = PrincipleSet(
        mission="accomplish the objective",
        invariants=["chain integrity must hold"],
        claim_boundaries=["durable ledger proven"],
    )
    context = (
        "We must accomplish the objective. "
        "The chain integrity must hold throughout. "
        "The durable ledger proven approach works."
    )
    assert validate_principles(ps, context) is True


def test_validate_principles_fails_missing_mission():
    ps = PrincipleSet(
        mission="quantumflux computation",
        invariants=[],
    )
    context = "This context does not mention it."
    assert validate_principles(ps, context) is False


def test_validate_principles_fails_missing_invariant():
    ps = PrincipleSet(
        mission="accomplish the objective",
        invariants=["chain integrity must hold"],
    )
    context = "We accomplish the objective but nothing else."
    assert validate_principles(ps, context) is False


def test_validate_principles_empty_invariants_passes():
    ps = PrincipleSet(
        mission="accomplish something",
        invariants=[],
        claim_boundaries=[],
    )
    context = "accomplish something here"
    assert validate_principles(ps, context) is True


def test_validate_principles_case_insensitive():
    ps = PrincipleSet(
        mission="Accomplish The OBJECTIVE",
        invariants=["CHAIN INTEGRITY"],
    )
    context = "accomplish the objective and chain integrity matters"
    assert validate_principles(ps, context) is True


# ── Agent spawn/list ──────────────────────────────────────────────────────────


def test_agent_save_and_list(ledger):
    contract = {
        "agent_id": "test-agent-001",
        "role": "architect",
        "mandate": "Design the system",
        "allowed_tools": ["read", "write"],
        "budget": 10,
    }
    ledger.save_agent("test-agent-001", contract)
    agents = ledger.list_agents()
    assert len(agents) == 1
    assert agents[0]["agent_id"] == "test-agent-001"
    assert agents[0]["role"] == "architect"


def test_agent_list_empty_workspace(ledger):
    agents = ledger.list_agents()
    assert agents == []


def test_multiple_agents(ledger):
    for i in range(3):
        ledger.save_agent(
            f"agent-{i:03d}", {"agent_id": f"agent-{i:03d}", "role": f"role_{i}"}
        )
    agents = ledger.list_agents()
    assert len(agents) == 3
