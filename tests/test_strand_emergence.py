"""Tier 1: organic dominance emergence in the strand extruder.

No routing rules — every op's winning tongue must fall out of
phi-weighted co-activation alone.
"""

from __future__ import annotations

import pytest

from src.symphonic.multipath.group_alignment import (
    extrude_strand,
    PROMOTION_ORDER,
    CANONICAL_ORDER,
)
from src.symphonic.multipath import (
    KO_TABLE, AV_TABLE, RU_TABLE, UM_TABLE, DR_TABLE,
)
from src.symphonic.multipath import trit_table_CA as _ca_module


# Semantic-home expectations per op. Each key is an op name drawn
# from ONE tongue's vocabulary; the value is the tongue we expect
# the strand extruder to pick organically.
EXPECTED_DOMINANT = {
    # CA — arithmetic / raw-compute home
    "add": "CA",
    # KO — control flow
    "if_": "KO",
    # RU — ownership
    "own": "RU",
    # AV — async/promise
    "promise": "AV",
    # UM — scientific / matrix
    "matrix": "UM",
    # DR — monadic bind
    "bind_d": "DR",
}


def test_strand_emergence_on_demo():
    demo_ops = ["add", "if_", "own", "promise", "matrix", "bind_d", "unknown_op"]
    strand = extrude_strand(demo_ops)
    assert strand.dominant_sequence() == ["CA", "KO", "RU", "AV", "UM", "DR", "CA"]
    assert strand.phi_total() > 130.0
    reshaped = strand.reshape(PROMOTION_ORDER)
    # Same dough, different die — ordering-sensitive phi_total.
    assert reshaped.phi_total() != strand.phi_total()


@pytest.mark.parametrize("op,expected", list(EXPECTED_DOMINANT.items()))
def test_organic_dominance_per_op(op, expected):
    strand = extrude_strand([op])
    assert strand.beads[0].dominant == expected, (
        f"{op} resolved to {strand.beads[0].dominant}, expected {expected}"
    )


def test_full_vocab_coverage():
    """Every op from every tongue's vocabulary must produce a non-silent bead."""
    all_ops = []
    for table in (KO_TABLE, AV_TABLE, RU_TABLE, UM_TABLE, DR_TABLE):
        all_ops.extend(table.ops)
    all_ops.extend(_ca_module.OP_ID.keys())

    strand = extrude_strand(all_ops)
    assert len(strand.beads) == len(all_ops)
    non_silent = sum(1 for b in strand.beads if b.phi_cost > 0)
    # Cross-tongue lookup is sparse but every op is native to at least
    # one table, so every bead must light up.
    assert non_silent == len(all_ops), (
        f"{len(all_ops) - non_silent} silent beads among native ops"
    )
