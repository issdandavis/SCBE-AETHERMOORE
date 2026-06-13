"""The auto-adversary auditor must have teeth AND vindicate the real packs.

Mason's verifier is only as sound as each slot's acceptance check. This locks
two things: (1) the auditor actually CATCHES weak checks — an assertion that
verifies nothing, a check that only pins a constant, and a check that only
memorises a fixed accumulation trace — and does NOT false-positive a genuinely
behavioural check; (2) every registered schematic's acceptance checks are sound
against the full hollow-twin arsenal. (2) is the executable form of the
"adversarial audit" that previously found packs gameable — now a passing gate.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


A = _load("mason_verifier_audit", "scripts/eval/mason_verifier_audit.py")
import mason  # noqa: E402  (on sys.path via the audit module)


def _audit_one(template: str, acceptance: str) -> dict:
    piece = mason.Piece(name="probe", shape="test", template=template)
    slot = mason.Slot(name="probe", piece="probe", acceptance=acceptance)
    return A.audit_slot(slot, piece, [], acceptance)


def test_auditor_catches_an_empty_assertion() -> None:
    """A request that asserts nothing real is gamed by the omni-constant twin."""
    r = _audit_one("class Thing:\n    def get(self):\n        return 42", "t = Thing()\nassert True")
    assert r["real_stone_passes"] is True
    assert r["sound"] is False
    assert r["gamed_by"] is not None


def test_auditor_catches_a_constant_pinning_check() -> None:
    """A request that only checks a fixed value is gamed by a constant-return stone."""
    template = (
        "class Thing:\n    def __init__(self):\n        self.value = 7\n    def get(self):\n        return self.value"
    )
    r = _audit_one(template, "t = Thing()\nassert t.value == 7\nassert t.get() == 7")
    assert r["sound"] is False
    assert r["gamed_by"] == "const:7"


def test_auditor_catches_a_fixed_trace_accumulation_check() -> None:
    """A request that only memorises a fixed call sequence is gamed by a bare counter."""
    template = (
        "class Scorer:\n"
        "    def __init__(self):\n"
        "        self.score = 0\n"
        "    def hit(self):\n"
        "        self.score += 1\n"
        "        return self.score"
    )
    r = _audit_one(template, "s = Scorer()\nassert s.hit() == 1\nassert s.hit() == 2\nassert s.hit() == 3")
    assert r["sound"] is False
    assert r["gamed_by"] == "counter"


def test_auditor_catches_a_fixed_sequence_trace_via_replay() -> None:
    """A single-instance check that pins a FIXED ordered run of distinct return
    values (no varied input) is a memorisable trace, not a behaviour: a stone that
    just replays [5, 11, 0] in order passes it. This is the trace-replay class the
    const and counter twins miss; the scripted-sequence replay twin catches it."""
    template = "class Adder:\n    def add(self, a, b):\n        return a + b"
    acceptance = "x = Adder()\nassert x.add(2, 3) == 5\nassert x.add(10, 1) == 11\nassert x.add(0, 0) == 0"
    r = _audit_one(template, acceptance)
    assert r["real_stone_passes"] is True
    assert r["sound"] is False
    assert r["gamed_by"] in ("replay-attr", "replay-method")


def test_auditor_does_not_false_positive_a_random_property_probe() -> None:
    """A check that probes VARIED random inputs (a property probe, not a fixed
    sequence) is genuinely sound: no constant, counter, or scripted-sequence replay
    can satisfy add(a, b) == a + b for inputs it never saw."""
    template = "class Adder:\n    def add(self, a, b):\n        return a + b"
    acceptance = (
        "import random\n"
        "x = Adder()\n"
        "for _ in range(8):\n"
        "    a, b = random.randint(0, 50), random.randint(0, 50)\n"
        "    assert x.add(a, b) == a + b"
    )
    r = _audit_one(template, acceptance)
    assert r["real_stone_passes"] is True
    assert r["sound"] is True
    assert r["gamed_by"] is None


def test_auditor_replay_does_not_false_positive_independent_instances() -> None:
    """Two independent instances asserting DIFFERENT values defeat per-instance
    replay: each new instance resets its sequence index, so no scripted run can
    match both. This is why the pacman 'player' slot (p and q, distinct positions)
    stays sound even though each instance is read once."""
    template = (
        "class Doubler:\n    def __init__(self, base):\n        self.base = base\n"
        "    def value(self):\n        return self.base * 2"
    )
    acceptance = "a = Doubler(3)\nassert a.value() == 6\nb = Doubler(5)\nassert b.value() == 10"
    r = _audit_one(template, acceptance)
    assert r["real_stone_passes"] is True
    assert r["sound"] is True


def test_every_registered_schematic_is_sound_against_the_auto_adversary() -> None:
    """The real gate: no hollow twin survives any slot's acceptance, in any pack."""
    for name in sorted(mason.REGISTRY):
        schematic, pieces, _ = mason.REGISTRY[name]
        result = A.audit_schematic(schematic, pieces)
        assert result["all_sound"] is True, (name, result["weak_slots"], result["log"])
        # and every real stone passes its own request (no broken fixtures)
        assert all(row["real_stone_passes"] for row in result["log"]), name
