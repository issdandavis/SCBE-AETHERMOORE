"""Illuminate — agentic mass-generation curated by the bicameral gap (MAP-Elites)."""

import random

from python.scbe import bicameral as B
from python.scbe import illuminate as IL
from python.scbe import polyglot as P


def test_random_program_is_mostly_stack_valid():
    rng = random.Random(1)
    incomplete = 0
    for _ in range(300):
        ops = IL.random_program(rng.randint(2, 8), rng)
        if B.think(P.program_bytes(*ops))["relation"] == "incomplete":
            incomplete += 1
    assert incomplete < 60  # the shape-aware generator rarely underflows


def test_archive_is_nonempty_and_curated():
    arch = IL.illuminate(generations=3, batch=120, seed=3)
    assert arch
    for (sig, rel), elite in arch.items():
        # every archived elite is real: re-running think reproduces its niche + it's not incomplete
        t = B.think(P.program_bytes(*elite["ops"]))
        assert t["relation"] == rel and rel != "incomplete"
        assert tuple(t["nonlinear_ops"]) == sig


def test_illuminate_is_deterministic():
    a = IL.illuminate(generations=2, batch=80, seed=11)
    b = IL.illuminate(generations=2, batch=80, seed=11)
    assert {k: v["ops"] for k, v in a.items()} == {k: v["ops"] for k, v in b.items()}


def test_archive_has_intuitive_and_usually_divergent_niches():
    arch = IL.illuminate(generations=4, batch=200, seed=5)
    relations = {rel for (_sig, rel) in arch}
    assert "exact match" in relations  # linear programs are intuitive
    # nonlinear ops should produce at least one divergent niche
    assert any(rel in ("close", "diverged", "sign flip") for (_sig, rel) in arch)


def test_render_archive_has_header_and_counts():
    out = IL.render_archive(IL.illuminate(generations=2, batch=80, seed=2))
    assert "MAP-Elites archive" in out and "ship-ready" in out
