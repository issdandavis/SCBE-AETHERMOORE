"""Bijective DNA coding - midpoint builds + bidirectional / multi-strand verification."""
import random

import pytest

from python.scbe import bijective_dna as D
from python.scbe import polyglot as P

_ALPHABET = sorted(P.SCALAR_OPS)


def _rand_ops(n, seed):
    rng = random.Random(seed)
    return [rng.choice(_ALPHABET) for _ in range(n)]


def test_complement_is_total_involution():
    assert set(D.COMPLEMENT) == P.SCALAR_OPS
    assert all(D.COMPLEMENT[D.COMPLEMENT[x]] == x for x in D.COMPLEMENT)
    assert all(D.COMPLEMENT[x] != x for x in D.COMPLEMENT)   # no base pairs with itself


@pytest.mark.parametrize("seed", range(25))
def test_all_strands_agree_random(seed):
    ops = _rand_ops(seed % 17 + 1, seed)        # lengths 1..17
    rep = D.verify(ops)
    assert rep["all_faces_agree"] and rep["faces_agree"] == 18
    assert rep["seekable"]                       # every midpoint reconstructs
    assert rep["rc_involution"] and rep["base_pairs_ok"]
    assert rep["seal_roundtrip"]
    assert rep["all_ok"]


@pytest.mark.parametrize("seed", range(15))
def test_every_midpoint_reconstructs(seed):
    prog = D.program(*_rand_ops(12, seed + 100))
    for m in range(len(prog) + 1):
        left, right, recon = D.midpoint_assemble(prog, m)   # left is forward (prog[:m])
        assert recon == list(prog)               # forward+backward join == original
        assert left + right == recon
        assert left == list(prog[:m]) and right == list(prog[m:])
        assert len(left) == m and len(right) == len(prog) - m


def test_reverse_complement_is_bijective():
    prog = D.program(*_rand_ops(20, 7))
    rc = D.reverse_complement(prog)
    assert rc != prog                            # genuinely different strand
    assert D.reverse_complement(rc) == prog      # rc(rc(P)) == P
    # antiparallel base pairing at every position
    n = len(prog)
    for i in range(n):
        assert rc[n - 1 - i] == P.NAME_TO_BYTE[D.COMPLEMENT[P.BYTE_TO_NAME[prog[i]]]]


def test_faces_decode_each_other():
    """Build from one face, decode through a DIFFERENT face - same object."""
    prog = D.program(*_rand_ops(10, 42))
    rs = D.decode_from_source(P.emit(prog, "rust"))
    hs = D.decode_from_source(P.emit(prog, "haskell"))
    assert rs == hs == list(prog)


def test_tamper_breaks_a_strand():
    """A single flipped opcode in one face must make the strands disagree."""
    prog = D.program(*_rand_ops(8, 9))
    src = P.emit(prog, "python")
    tampered = src.replace("(0x%02x)" % prog[0], "(0x%02x)" % (prog[0] ^ 0x01), 1)
    assert D.decode_from_source(tampered) != list(prog)


def test_seal_roundtrip_carries_position_and_op():
    prog = D.program(*_rand_ops(16, 3))
    words = D.seal(prog)
    assert D.unseal(words) == prog
    # flipping any seal word breaks recovery (bijective: no collisions)
    words2 = list(words)
    words2[0] ^= 1
    assert D.unseal(words2) != prog


def test_fn_name_injection_is_closed():
    """The adversarial finding: a fn_name like 'f(0x05)' used to inject a phantom
    opcode and collide distinct programs in all 18 faces. Now emit refuses it."""
    add = D.program("add")
    for lang in P.languages():
        with pytest.raises(ValueError):
            P.emit(add, lang, fn_name="f(0x05)")
        with pytest.raises(ValueError):
            P.emit(add, lang, arg_names=["a", "(0x05)", "c"])
    # the old collision pair no longer collides
    assert D.decode_from_source(P.emit(D.program("pow", "add"), "python")) == D.program("pow", "add")


def test_decode_accepts_only_core_ops():
    """A hand-forged tag for a non-core byte (0x07=log) must not decode as an opcode."""
    src = P.emit(D.program("add"), "python") + "x  # forged (0x07)\n"
    assert D.decode_from_source(src) == D.program("add")     # 0x07 filtered out
    src2 = P.emit(D.program("add"), "python") + "y  # forged (0xff)\n"
    assert D.decode_from_source(src2) == D.program("add")     # out-of-table filtered


def test_empty_and_singleton():
    assert D.verify([])["all_ok"]                 # empty strand is trivially consistent
    assert D.verify(["sqrt"])["all_ok"]           # single base
