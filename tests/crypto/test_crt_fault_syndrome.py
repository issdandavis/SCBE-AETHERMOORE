"""Deterministic tests for the toy CRT-RSA hexaphase fault harness."""

from __future__ import annotations

import copy
from itertools import product

import pytest

from src.crypto.crt_fault_syndrome import (
    EISENSTEIN_POWERS,
    SLOT_LABELS,
    TONGUE_ANGLES_DEGREES,
    TONGUE_CODES,
    TONGUE_PHI_WEIGHTS,
    bellcore_factor_for_toy,
    build_crt_batch,
    build_ross_lattice,
    build_syndrome_receipt,
    canonical_receipt_bytes,
    crt_certificate_matches,
    crt_private_operation,
    exact_hexaphase_spectrum,
    fold_integer,
    locate_single_fault,
    make_toy_rsa_key,
    public_verification,
    receipt_hashes,
    seal_syndrome_receipt,
    unfold_integer,
    unseal_syndrome_receipt,
    zero_syndrome,
)
from src.crypto.geo_fenced_seal import GeoFenceViolation
from src.crypto.sacred_eggs import SacredEgg
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

PORT_ANGELES = {"lat": 48.1181, "lon": -123.4307}
SEQUIM = {"lat": 48.0792, "lon": -123.1027}
TOY_CIPHERTEXTS = (2, 42, 999_983)


def test_crt_matches_direct_private_operation_over_deterministic_sweep() -> None:
    key = make_toy_rsa_key()
    samples = list(range(0, key.n, 4093))
    samples.extend([key.n - 1, key.n, key.n + 1, 10**30])
    for ciphertext in samples:
        result = crt_private_operation(ciphertext, key)
        assert result.value == pow(ciphertext, key.d, key.n)
        assert public_verification(ciphertext, result.value, key)


def test_clean_batch_is_six_zeros_and_release_allowed() -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key)
    assert batch.residuals == (0, 0, 0, 0, 0, 0)
    assert batch.public_verification == (True, True, True)
    assert zero_syndrome(batch.residuals)
    assert locate_single_fault(batch.residuals) is None
    assert all(bin_value == (0, 0) for bin_value in exact_hexaphase_spectrum(batch.residuals))


@pytest.mark.parametrize("fault_slot", range(6), ids=SLOT_LABELS)
@pytest.mark.parametrize("fault_delta", (-3, -1, 1, 3))
def test_every_single_branch_fault_is_located_and_rejected(fault_slot: int, fault_delta: int) -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key, fault_slot=fault_slot, fault_delta=fault_delta)

    non_zero = [index for index, residual in enumerate(batch.residuals) if residual]
    assert non_zero == [fault_slot]
    location = locate_single_fault(batch.residuals)
    assert location is not None
    assert location.index == fault_slot
    assert location.label == SLOT_LABELS[fault_slot]
    assert not zero_syndrome(batch.residuals)

    affected_operation = fault_slot // 2
    assert batch.public_verification[affected_operation] is False
    assert sum(not passed for passed in batch.public_verification) == 1


@pytest.mark.parametrize("fault_slot", range(6), ids=SLOT_LABELS)
def test_bellcore_toy_fault_leaks_the_untouched_prime(fault_slot: int) -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key, fault_slot=fault_slot, fault_delta=1)
    operation_index, branch_index = divmod(fault_slot, 2)
    factor = bellcore_factor_for_toy(
        batch.ciphertexts[operation_index],
        batch.results[operation_index].value,
        key,
    )
    assert factor == (key.q if branch_index == 0 else key.p)


def test_bin_one_antipodal_blind_spot_is_closed_by_bin_zero() -> None:
    for index in range(3):
        values = [0] * 6
        values[index] = 7
        values[index + 3] = 7
        spectrum = exact_hexaphase_spectrum(values)
        assert spectrum[1] == (0, 0)
        assert spectrum[0] == (14, 0)
        assert not zero_syndrome(values)


def test_bins_zero_and_one_detect_all_bounded_distinct_two_slot_errors() -> None:
    deltas = (-3, -2, -1, 1, 2, 3)
    tested = 0
    for left in range(6):
        for right in range(left + 1, 6):
            for left_delta in deltas:
                for right_delta in deltas:
                    values = [0] * 6
                    values[left] = left_delta
                    values[right] = right_delta
                    assert not zero_syndrome(values)
                    tested += 1
    assert tested == 540


def test_single_fault_syndrome_formula_matches_each_exact_root() -> None:
    for index, root in enumerate(EISENSTEIN_POWERS):
        values = [0] * 6
        values[index] = 11
        spectrum = exact_hexaphase_spectrum(values)
        assert spectrum[0] == (11, 0)
        assert spectrum[1] == (11 * root[0], 11 * root[1])


def test_exhaustive_zero_zone_kernel_sizes_match_loom_measurement() -> None:
    bin_one_kernel = 0
    bins_zero_one_kernel = 0
    states = 0
    for values in product(range(-3, 4), repeat=6):
        spectrum = exact_hexaphase_spectrum(values)
        bin_one_kernel += spectrum[1] == (0, 0)
        bins_zero_one_kernel += spectrum[0] == (0, 0) and spectrum[1] == (0, 0)
        states += 1
    assert states == 117_649
    assert bin_one_kernel == 1225
    assert bins_zero_one_kernel == 91


def test_crt_certificate_is_bounded_by_error_not_absolute_value() -> None:
    moduli = (99, 91)
    product = 9009
    for reference in (10**2, 10**6, 10**30):
        for error in range(-(product - 1), product):
            if error:
                assert not crt_certificate_matches(reference, reference + error, moduli)
        assert crt_certificate_matches(reference, reference + product, moduli)
        assert crt_certificate_matches(reference, reference - product, moduli)


@pytest.mark.parametrize(
    ("value", "expected_folds"),
    ((30, 1), (90_000, 2), (10**12, 4), (10**20, 6), (-(10**20), 6)),
)
def test_rebase_cycles_grow_logarithmically(value: int, expected_folds: int) -> None:
    folded = fold_integer(value, 9009)
    assert folded.folds == expected_folds
    assert unfold_integer(folded) == value
    assert all(0 <= digit < 9009 for digit in folded.digits)


def test_syndrome_receipt_contains_no_rsa_private_key_material() -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key, fault_slot=4, fault_delta=1)
    receipt = build_syndrome_receipt(batch)
    payload = canonical_receipt_bytes(receipt)

    assert receipt["single_fault_location"]["label"] == "op2:p"
    assert receipt["release_allowed"] is False
    assert all(field not in receipt for field in ("p", "q", "d", "d_p", "d_q", "q_inv"))
    hashes = receipt_hashes(payload)
    assert set(hashes) == {"sha256", "sha3_256", "blake2b_256"}
    assert all(len(digest) == 64 for digest in hashes.values())
    assert len(set(hashes.values())) == 3


def test_ross_lattice_covers_256_nodes_at_six_weighted_angles() -> None:
    payload = b"six tongues see the same receipt"
    lattice = build_ross_lattice(payload)

    assert lattice["shape"] == [6, 256]
    assert lattice["node_count"] == 1536
    assert [axis["tongue"] for axis in lattice["axes"]] == list(TONGUE_CODES)
    assert [axis["angle_degrees"] for axis in lattice["axes"]] == list(TONGUE_ANGLES_DEGREES)
    assert [(axis["phi_weight"]["a"], axis["phi_weight"]["b"]) for axis in lattice["axes"]] == list(TONGUE_PHI_WEIGHTS)
    assert all(axis["node_count"] == 256 for axis in lattice["axes"])
    assert len({axis["codebook_sha3_256"] for axis in lattice["axes"]}) == 6
    assert len({axis["projection_blake2b_256"] for axis in lattice["axes"]}) == 6

    for code in TONGUE_CODES:
        codebook = SACRED_TONGUE_TOKENIZER.byte_to_token[code]
        assert len(codebook) == len(set(codebook)) == 256
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(code, payload)
        assert SACRED_TONGUE_TOKENIZER.decode_tokens(code, tokens) == payload


def test_ross_lattice_root_changes_with_payload() -> None:
    left = build_ross_lattice(b"receipt A")
    right = build_ross_lattice(b"receipt B")
    assert left["root_sha256"] != right["root_sha256"]
    assert [axis["codebook_sha3_256"] for axis in left["axes"]] == [axis["codebook_sha3_256"] for axis in right["axes"]]
    assert [axis["projection_blake2b_256"] for axis in left["axes"]] != [
        axis["projection_blake2b_256"] for axis in right["axes"]
    ]


def test_sacred_egg_multi_hash_geoseal_roundtrip_and_policy() -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key, fault_slot=3, fault_delta=2)
    receipt = build_syndrome_receipt(batch)
    egg = SacredEgg.create(context="crt-fault-receipt", yolk=b"e" * 32)
    secret = b"s" * 32
    packet = seal_syndrome_receipt(
        secret,
        egg,
        receipt,
        geo_fence={**PORT_ANGELES, "radius_m": 5_000},
    )

    opened = unseal_syndrome_receipt(secret, egg, packet, current_location=PORT_ANGELES)
    assert opened["receipt"] == receipt
    assert opened["egg_id"] == egg.egg_id
    assert opened["geo_fence_check"]["passed"] is True
    assert opened["receipt_hashes"] == packet["metadata"]["receipt_hashes"]
    assert opened["ross_lattice"] == packet["metadata"]["ross_lattice"]
    assert opened["ross_lattice"]["node_count"] == 1536

    with pytest.raises(GeoFenceViolation):
        unseal_syndrome_receipt(secret, egg, packet, current_location=SEQUIM)


def test_syndrome_receipt_rejects_wrong_egg_and_tampered_hash_metadata() -> None:
    key = make_toy_rsa_key()
    batch = build_crt_batch(TOY_CIPHERTEXTS, key)
    receipt = build_syndrome_receipt(batch)
    egg = SacredEgg.create(context="crt-fault-receipt", yolk=b"e" * 32)
    wrong_egg = SacredEgg.create(context="crt-fault-receipt", yolk=b"w" * 32)
    secret = b"s" * 32
    packet = seal_syndrome_receipt(
        secret,
        egg,
        receipt,
        geo_fence={**PORT_ANGELES, "radius_m": 5_000},
    )

    with pytest.raises(ValueError, match="syndrome receipt verification failed"):
        unseal_syndrome_receipt(secret, wrong_egg, packet, current_location=PORT_ANGELES)

    tampered = copy.deepcopy(packet)
    tampered["metadata"]["receipt_hashes"]["sha3_256"] = "0" * 64
    with pytest.raises(Exception):
        unseal_syndrome_receipt(secret, egg, tampered, current_location=PORT_ANGELES)
