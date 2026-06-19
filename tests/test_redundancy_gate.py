"""redundancy_gate: the second immune system -- catch conceptually-redundant work before it lands.

Execution + cross-face catch BROKEN code; this catches REDUNDANT code (two sessions building the
same idea in different words). It must flag the #2422/#2423 two-string-designs collision class and
must NOT false-positive on the genuinely-distinct modules already on main.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

import redundancy_gate as rg  # noqa: E402

REGISTRY = ROOT / "scripts" / "ci" / "math_claims.txt"


def test_normalize_drops_stopwords_case_and_plurals():
    toks = rg.normalize("A string is an array of CHAR codes")
    assert "string" in toks and "array" in toks and "char" in toks and "code" in toks
    assert "a" not in toks and "is" not in toks and "of" not in toks  # stopwords gone
    assert "strings" not in toks and "arrays" not in toks  # de-pluralized


def test_overlap_identical_and_disjoint():
    assert rg.overlap("a string is an array of char codes", "a string is an array of char codes") == 1.0
    assert rg.overlap("string array char codes", "geodesic hyperbolic manifold distance") == 0.0


def test_two_string_designs_collide():
    # the #2422 (strlit/chr) vs #2423 (str/char) near-collision: same idea, different words
    a = "loomfn strings: a string is a heap array of char codes"
    b = "add string support to loomfn via arrays of char codes"
    assert rg.overlap(a, b) >= 0.5


def test_unrelated_work_does_not_collide():
    a = "a string is a heap array of char codes"
    b = "bind two instruction streams within epsilon distance with a depth gate"
    assert rg.overlap(a, b) < 0.3


def test_check_against_seeded_registry_flags_a_redundant_string_layer():
    # a realistic restatement of "add strings to loomfn" -- the #2422/#2423 class
    reg = rg.load_registry(REGISTRY)
    hits = rg.check("add strings to loomfn as arrays of char codes", reg, threshold=0.5)
    assert any(mod.endswith("#strings") for mod, _claim, _score in hits)  # surfaces loomfn#strings


def test_a_genuinely_new_claim_is_clear():
    reg = rg.load_registry(REGISTRY)
    hits = rg.check("schedule jobs onto worker threads by priority with backpressure", reg, threshold=0.5)
    assert hits == []  # nothing like it on main -> clear to build


def test_seed_registry_surfaces_only_the_known_kernel_sibling_overlap():
    # curriculum + reasoning_ladder are intentional siblings on ladder.py: the gate SHOULD flag them
    # (same "score a generator on held-out items, graded into tiers" shape), and that overlap is
    # acknowledged -- resolved by the shared kernel, not by hiding it. NOTHING ELSE may overlap.
    reg = rg.load_registry(REGISTRY)
    assert len(reg) >= 10
    pairs = {frozenset((m1, m2)) for m1, m2, _ in rg.audit(reg, threshold=0.5)}
    sibling = frozenset(("python/helm/curriculum.py", "python/helm/reasoning_ladder.py"))
    assert sibling in pairs  # the gate catches the real, intended overlap
    assert all(p == sibling for p in pairs)  # and surfaces no other (unacknowledged) redundancy


def test_cli_claim_and_audit_run():
    assert rg.main(["--claim", "a totally unprecedented widget", "--registry", str(REGISTRY)]) == 0
    assert rg.main(["--audit", "--registry", str(REGISTRY)]) == 0
    # strict mode exits nonzero when an overlap is found
    assert rg.main(["--claim", "a string as a heap array of char codes", "--registry", str(REGISTRY), "--strict"]) == 1


def test_concept_trigger_flags_a_tc_reencoding_that_jaccard_misses():
    # a 'turing rubix' re-encoding shares almost no tokens with 'binary spine' (Jaccard < 0.5),
    # but it IS just Brainfuck again -- the concept trigger must catch it against the registered cores
    reg = rg.load_registry(REGISTRY)
    claim = "turing rubix: cube moves as a brainfuck instruction surface over an unbounded tape, turing complete"
    assert rg.check(claim, reg, 0.5) == []  # the honest limit: Jaccard alone does NOT catch it
    cm = rg.concept_matches(claim, reg)
    phrases = {p for p, _ in cm}
    assert {"brainfuck", "turing complete", "unbounded tape"} & phrases  # the concept trigger DOES
    flagged = {m for _, mods in cm for m in mods}
    assert any("bit_spine" in m for m in flagged)  # flagged against the registered BF/TC core


def test_concept_trigger_is_quiet_on_unrelated_work():
    reg = rg.load_registry(REGISTRY)
    assert rg.concept_matches("a graded reasoning ladder scored by exact match", reg) == []
    # and strict mode now blocks a TC re-encoding even with zero Jaccard overlap
    args = ["--claim", "encode brainfuck as dance moves, turing complete", "--registry", str(REGISTRY), "--strict"]
    assert rg.main(args) == 1
