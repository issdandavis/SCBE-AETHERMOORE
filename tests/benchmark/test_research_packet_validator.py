"""research_packet_validator: the Research Packet Standard as a CI-checkable gate.

These pin the load-bearing checks (not a judgment of the science): a note must carry the minimum sections
for its claimed grade AND a CLAIM BOUNDARY at every grade (the anti-overclaim spine) -- so nothing gets
sold as more than it is. Also runs against a real research note in the repo.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "eval" / "research_packet_validator.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_rpv_test", MODULE_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


_COMPLIANT_BRIEF = """# Foo: a bounded thing
## Abstract
What it is.
## Research Question
Is X true under Y?
## Background
Prior work.
## Sources
- a primary paper
## Claim Boundary
We claim only Z; we do NOT claim more.
"""

_NO_CLAIM_BOUNDARY = """# Foo
## Abstract
A.
## Research Question
Q?
## Sources
- a paper
"""


def test_compliant_brief_passes():
    m = _mod()
    r = m.validate(_COMPLIANT_BRIEF, "research_brief")
    assert r["ok"] is True and r["meets_grade"] is True
    assert r["has_claim_boundary"] is True and r["has_source_ledger"] is True


def test_missing_claim_boundary_fails_at_every_grade():
    m = _mod()
    for g in ("idea_seed", "research_brief", "research_packet"):
        r = m.validate(_NO_CLAIM_BOUNDARY, g)
        assert r["ok"] is False, g  # the claim boundary is the anti-overclaim spine; required everywhere
        assert r["has_claim_boundary"] is False


def test_brief_does_not_meet_the_full_research_packet_grade():
    # a brief is missing most of the 13 sections -> it must NOT pass as a full research_packet
    m = _mod()
    r = m.validate(_COMPLIANT_BRIEF, "research_packet")
    assert r["meets_grade"] is False and len(r["sections_missing_for_grade"]) > 0


def test_invalid_grade_is_flagged():
    m = _mod()
    r = m.validate(_COMPLIANT_BRIEF, "totally_made_up_grade")
    assert r["valid_grade"] is False and r["ok"] is False


def test_runs_against_a_real_repo_note_with_a_claim_boundary():
    # the dice research note explicitly carries a claim boundary + sources -> qualifies at brief grade
    m = _mod()
    note = (ROOT / "docs" / "research" / "dice_input_coding_systems_2026-05-31.md").read_text(encoding="utf-8")
    r = m.validate(note, "research_brief")
    assert r["has_claim_boundary"] is True and r["has_source_ledger"] is True
    assert r["ok"] is True
