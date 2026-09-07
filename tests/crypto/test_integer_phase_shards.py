"""Tests for the exact-integer phase-shard research scaffold."""

from __future__ import annotations

import ast
from dataclasses import replace
from itertools import product
from pathlib import Path
import random

import pytest

from src.crypto import integer_phase_shards as S

SOURCE_IDS = ("os", "hardware", "owner", "ceremony")
SAMPLES = tuple(bytes([index]) * S.SOURCE_BYTES for index in range(1, 5))
CONTEXT = b'{"who":"owner","what":"create-root","when":1,"where":"device","why":"test","how":"local"}'
NONCE = bytes.fromhex("00112233445566778899aabbccddeeff")


def test_11_over_4_carry_is_exhaustively_bijective_on_small_vectors() -> None:
    encoded = set()
    for values in product(range(8), repeat=4):
        carried = S.carry_scale(values)
        decoded, initial = S.carry_unscale(carried)
        assert decoded == values
        assert initial == 0
        encoded.add((carried.values, carried.terminal_remainder))
    assert len(encoded) == 8**4


def test_11_over_4_carry_roundtrips_random_256_bit_values() -> None:
    rng = random.Random(20260906)
    for _ in range(1_000):
        values = tuple(rng.randrange(1 << 256) for _ in range(4))
        assert S.carry_unscale(S.carry_scale(values))[0] == values


def test_invalid_carry_stream_is_rejected() -> None:
    with pytest.raises(ValueError, match="valid carried"):
        S.carry_unscale(S.CarryEncoding((1,), 0))


def test_integer_phase_is_exactly_periodic_and_reversible() -> None:
    rng = random.Random(12030)
    for _ in range(1_000):
        state = tuple(rng.randrange(-(1 << 128), 1 << 128) for _ in range(4))
        assert S.rotate_phase30(state, 12) == state
        assert S.rotate_phase30(S.rotate_phase30(state), 11) == state
        assert S.rotate_phase30(state, -1) == S.rotate_phase30(state, 11)


@pytest.mark.parametrize(
    "anchor,observed,corrections",
    [
        (17, 17, ()),
        (10, -75, (-30, 5)),
        (-(10**250), 10**300, (10**125, -(10**75))),
    ],
)
def test_primed_anchor_reconstructs_any_integer_exactly(anchor, observed, corrections) -> None:
    key = bytes.fromhex("a5" * S.KEY_BYTES)
    witness = S.create_primed_anchor_witness(
        key,
        anchor=anchor,
        observed_value=observed,
        corrections=corrections,
        context=CONTEXT,
    )
    assert S.verify_primed_anchor_witness(key, witness, context=CONTEXT, expected_value=observed) == observed


@pytest.mark.parametrize("field", ["anchor", "correction", "residual", "direction", "tag", "context"])
def test_primed_anchor_rejects_changed_calibration_or_witness(field: str) -> None:
    key = bytes.fromhex("3c" * S.KEY_BYTES)
    context = CONTEXT
    witness = S.create_primed_anchor_witness(
        key,
        anchor=1_000,
        observed_value=1_127,
        corrections=(20, -3),
        context=context,
    )
    if field == "anchor":
        witness = replace(witness, anchor=witness.anchor + 1)
    elif field == "correction":
        witness = replace(witness, corrections=(21, -3))
    elif field == "residual":
        changed = replace(witness.scaled_residual, values=(witness.scaled_residual.values[0] + 1,))
        witness = replace(witness, scaled_residual=changed)
    elif field == "direction":
        witness = replace(witness, residual_sign=-witness.residual_sign)
    elif field == "tag":
        witness = replace(witness, tag="0" * 64)
    else:
        context += b"!"
    with pytest.raises(ValueError):
        S.verify_primed_anchor_witness(key, witness, context=context)


def test_primed_anchor_requires_the_declared_target() -> None:
    key = bytes.fromhex("7d" * S.KEY_BYTES)
    witness = S.create_primed_anchor_witness(
        key,
        anchor=123_456_789_012,
        observed_value=123_456_789_016,
        corrections=(7, -3),
        context=CONTEXT,
    )
    with pytest.raises(ValueError, match="required target"):
        S.verify_primed_anchor_witness(key, witness, context=CONTEXT, expected_value=123_456_789_017)


def test_primed_anchor_rejects_wrong_key_and_malformed_fields() -> None:
    key = bytes.fromhex("18" * S.KEY_BYTES)
    witness = S.create_primed_anchor_witness(
        key,
        anchor=42,
        observed_value=-9,
        corrections=(-2, 7),
        context=CONTEXT,
    )
    with pytest.raises(ValueError, match="authentication"):
        S.verify_primed_anchor_witness(bytes.fromhex("19" * S.KEY_BYTES), witness, context=CONTEXT)
    with pytest.raises(ValueError, match="malformed"):
        S.verify_primed_anchor_witness(key, replace(witness, tag="not-hex"), context=CONTEXT)
    with pytest.raises(ValueError, match="direction"):
        S.verify_primed_anchor_witness(key, replace(witness, residual_sign=True), context=CONTEXT)


def test_module_contains_no_floating_point_constants() -> None:
    source = Path(S.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    floats = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, float)]
    assert floats == []


def test_four_source_conditioning_has_a_fixed_vector() -> None:
    root, receipt = S.condition_four_sources(
        SAMPLES,
        source_ids=SOURCE_IDS,
        context=CONTEXT,
        ceremony_nonce=NONCE,
    )
    assert root.hex() == "b8a73b8e75226467806766e1a55ef375a33227d6bdee9075fac6f90fe042fa9d"
    assert receipt.transform_commitment == "5e69699cf0601fc1ad30f3d3b2933e39904aa9f88ebd51fdac88b8d8921337c1"
    assert receipt.source_ids == SOURCE_IDS
    assert len(set(receipt.source_commitments)) == 4
    assert receipt.scale_numerator == 11 and receipt.scale_denominator == 4
    assert receipt.phase_step == 1 and receipt.phase_order == 12


@pytest.mark.parametrize("field", ["source", "order", "context", "nonce", "phase"])
def test_every_ceremony_dimension_is_bound(field: str) -> None:
    samples = list(SAMPLES)
    ids = list(SOURCE_IDS)
    context = CONTEXT
    nonce = NONCE
    phase = 1
    baseline, _ = S.condition_four_sources(samples, source_ids=ids, context=context, ceremony_nonce=nonce)

    if field == "source":
        samples[0] = bytes([samples[0][0] ^ 1]) + samples[0][1:]
    elif field == "order":
        ids[0], ids[1] = ids[1], ids[0]
        samples[0], samples[1] = samples[1], samples[0]
    elif field == "context":
        context += b"!"
    elif field == "nonce":
        nonce = bytes([nonce[0] ^ 1]) + nonce[1:]
    else:
        phase = 2

    changed, _ = S.condition_four_sources(
        samples,
        source_ids=ids,
        context=context,
        ceremony_nonce=nonce,
        phase_step=phase,
    )
    assert changed != baseline


def test_source_validation_refuses_ambiguous_ceremonies() -> None:
    with pytest.raises(ValueError, match="exactly"):
        S.condition_four_sources(SAMPLES[:3], source_ids=SOURCE_IDS[:3], context=CONTEXT, ceremony_nonce=NONCE)
    with pytest.raises(ValueError, match="unique"):
        S.condition_four_sources(SAMPLES, source_ids=("same",) * 4, context=CONTEXT, ceremony_nonce=NONCE)
    with pytest.raises(ValueError, match="32 bytes"):
        S.condition_four_sources((*SAMPLES[:3], b"short"), source_ids=SOURCE_IDS, context=CONTEXT, ceremony_nonce=NONCE)


def test_two_of_two_split_reconstructs_and_each_piece_differs_from_root() -> None:
    root, _ = S.condition_four_sources(SAMPLES, source_ids=SOURCE_IDS, context=CONTEXT, ceremony_nonce=NONCE)
    owner_random = bytes.fromhex("f0" * S.KEY_BYTES)
    owner, service = S.split_two_of_two(root, owner_random)
    assert owner != root and service != root and owner != service
    assert S.join_two_of_two(owner, service) == root


def test_tree_nodes_bind_path_epoch_context_and_fresh_entropy() -> None:
    root, _ = S.condition_four_sources(SAMPLES, source_ids=SOURCE_IDS, context=CONTEXT, ceremony_nonce=NONCE)
    baseline = S.derive_node_key(root, path=(0, 1), epoch=7, context=CONTEXT)
    repeated = S.derive_node_key(root, path=(0, 1), epoch=7, context=CONTEXT)
    assert baseline == repeated
    assert not baseline.fresh_entropy_mixed

    variants = (
        S.derive_node_key(root, path=(1, 0), epoch=7, context=CONTEXT),
        S.derive_node_key(root, path=(0, 1), epoch=8, context=CONTEXT),
        S.derive_node_key(root, path=(0, 1), epoch=7, context=CONTEXT + b"!"),
        S.derive_node_key(root, path=(0, 1), epoch=7, context=CONTEXT, fresh_entropy=b"z" * 32),
    )
    assert all(node.key != baseline.key for node in variants)
    assert variants[-1].fresh_entropy_mixed
    assert all(0 <= node.phase_step < 12 for node in (baseline, *variants))


def test_rfc5869_sha256_case_one() -> None:
    ikm = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    pseudorandom_key = S._hkdf_extract(salt, ikm)
    output = S._hkdf_expand(pseudorandom_key, info, 42)
    assert pseudorandom_key.hex() == "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
    assert output.hex() == (
        "3cb25f25faacd57a90434f64d0362f2a" "2d2d0a90cf1a5a4c5db02d56ecc4c5bf" "34007208d5b887185865"
    )
