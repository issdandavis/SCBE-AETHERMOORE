from python.scbe.toroidal_braid import (
    Crossing,
    apply_word,
    braid_relation_holds,
    cyclic_loop,
    demo_receipt,
    inverse_word,
    prove_bijective,
)


def test_random_toroidal_braids_round_trip_bijectively() -> None:
    receipt = prove_bijective(samples=2000, strands=8, word_len=60, seed=11)

    assert receipt["bijective"] is True
    assert receipt["passed"] == 2000


def test_cyclic_loop_wraps_torus_and_inverse_restores_identity() -> None:
    strands = list(range(8))
    initial = list(strands)
    loop = cyclic_loop(8)

    writhe = apply_word(strands, loop)

    assert strands == [0, 2, 3, 4, 5, 6, 7, 1]
    assert writhe == 8
    apply_word(strands, inverse_word(loop))
    assert strands == initial


def test_over_and_under_have_same_permutation_but_distinct_writhe() -> None:
    over = list(range(8))
    under = list(range(8))

    over_writhe = apply_word(over, [Crossing(2, True)])
    under_writhe = apply_word(under, [Crossing(2, False)])

    assert over == under
    assert over_writhe == 1
    assert under_writhe == -1


def test_braid_relation_holds_on_toroidal_ring() -> None:
    assert braid_relation_holds(index=2, strands=8)


def test_demo_receipt_reports_world_map_proofs() -> None:
    receipt = demo_receipt()

    assert receipt["proof"]["bijective"] is True
    assert receipt["cyclic_loop"]["inverse_restores"] is True
    assert receipt["over_under"]["distinct_braids"] is True
    assert receipt["braid_relation"] is True
