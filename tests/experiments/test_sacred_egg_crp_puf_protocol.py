import csv
import json
import math

import pytest

from scripts.experiments.sacred_egg_crp_puf_protocol import (
    CrpProtocolError,
    CrpSample,
    NonceReplayGuard,
    build_enrollment_model,
    build_report,
    evaluate_protocol,
    load_measurements,
    select_challenge,
    verify_values,
)

WIDTH = 96
FEATURE_NAMES = tuple(f"r_{index}" for index in range(WIDTH))


def _bits_to_values(bits: tuple[int, ...], jitter: float = 0.0) -> tuple[float, ...]:
    return tuple((-1.0 if bit == 0 else 1.0) + jitter for bit in bits)


def _patterns(width: int = WIDTH) -> dict[tuple[str, str], tuple[int, ...]]:
    a_c0 = tuple(index % 2 for index in range(width))
    a_c1 = tuple((index // 2) % 2 for index in range(width))
    return {
        ("unit-a", "challenge-0"): a_c0,
        ("unit-b", "challenge-0"): tuple(1 - bit for bit in a_c0),
        ("unit-a", "challenge-1"): a_c1,
        ("unit-b", "challenge-1"): tuple(1 - bit for bit in a_c1),
    }


def separated_rows(width: int = WIDTH) -> list[CrpSample]:
    rows: list[CrpSample] = []
    for (device_id, challenge_id), bits in _patterns(width).items():
        for read_index, jitter in enumerate((-0.04, 0.0, 0.04)):
            rows.append(
                CrpSample(
                    device_id,
                    challenge_id,
                    "enroll",
                    f"enroll-{read_index}",
                    _bits_to_values(bits, jitter),
                )
            )
        for read_index, jitter in enumerate((-0.02, 0.02)):
            rows.append(
                CrpSample(
                    device_id,
                    challenge_id,
                    "verify",
                    f"verify-{read_index}",
                    _bits_to_values(bits, jitter),
                )
            )
    return rows


def test_held_out_protocol_rejects_device_and_challenge_replays() -> None:
    rows = separated_rows()
    model = build_enrollment_model(rows, FEATURE_NAMES)
    metrics = evaluate_protocol(rows, model)

    assert metrics.enrollment_count == 12
    assert metrics.verification_count == 8
    assert metrics.minimum_stable_bits == WIDTH
    assert metrics.enrollment_code_margin_bits == WIDTH
    assert metrics.false_reject_rate == 0.0
    assert metrics.false_accept_rate == 0.0
    assert metrics.wrong_challenge_accept_rate == 0.0
    assert metrics.distinct_response_patterns == 4
    assert metrics.empirical_response_pattern_min_entropy_bits == 2.0
    assert metrics.meets_mechanical_gate is True


def test_verification_rows_cannot_change_enrollment_model() -> None:
    rows = separated_rows()
    baseline = build_enrollment_model(rows, FEATURE_NAMES)
    mutated = [
        CrpSample(
            row.device_id,
            row.challenge_id,
            row.split,
            row.read_id,
            tuple(10_000.0 - index for index in range(WIDTH)) if row.split == "verify" else row.values,
        )
        for row in rows
    ]
    after_verify_mutation = build_enrollment_model(mutated, FEATURE_NAMES)

    assert after_verify_mutation.model_sha256 == baseline.model_sha256
    assert after_verify_mutation.thresholds == baseline.thresholds
    assert after_verify_mutation.templates == baseline.templates
    assert evaluate_protocol(mutated, after_verify_mutation).meets_mechanical_gate is False


def test_direct_verifier_preserves_source_challenge_and_fails_closed() -> None:
    rows = separated_rows()
    model = build_enrollment_model(rows, FEATURE_NAMES)
    source_bits = _patterns()[("unit-a", "challenge-0")]

    mismatch = verify_values(
        _bits_to_values(source_bits),
        source_device_id="unit-a",
        source_challenge_id="challenge-0",
        claimed_device_id="unit-a",
        selected_challenge_id="challenge-1",
        model=model,
    )
    replay = verify_values(
        _bits_to_values(source_bits),
        source_device_id="unit-a",
        source_challenge_id="challenge-0",
        claimed_device_id="unit-a",
        selected_challenge_id="challenge-1",
        model=model,
        enforce_source_challenge=False,
    )

    assert mismatch.reason == "challenge_mismatch"
    assert mismatch.source_challenge_id == "challenge-0"
    assert replay.accepted is False
    assert replay.source_challenge_id == "challenge-0"
    with pytest.raises(CrpProtocolError, match="finite"):
        verify_values(
            (math.nan,) + _bits_to_values(source_bits)[1:],
            source_device_id="unit-a",
            source_challenge_id="challenge-0",
            claimed_device_id="unit-a",
            selected_challenge_id="challenge-0",
            model=model,
        )


def test_identity_labels_do_not_manufacture_response_entropy() -> None:
    width = 8
    features = tuple(f"r_{index}" for index in range(width))
    rows: list[CrpSample] = []
    identical = (1.0,) * width
    for device_id in ("unit-a", "unit-b"):
        for challenge_id in ("challenge-0", "challenge-1"):
            rows.extend(
                [
                    CrpSample(device_id, challenge_id, "enroll", "e0", identical),
                    CrpSample(device_id, challenge_id, "enroll", "e1", identical),
                    CrpSample(device_id, challenge_id, "verify", "v0", identical),
                ]
            )

    model = build_enrollment_model(rows, features)
    metrics = evaluate_protocol(rows, model, min_stable_bits=width)

    assert len({template.template_sha256 for template in model.templates}) == 4
    assert metrics.distinct_response_patterns == 1
    assert metrics.empirical_response_pattern_min_entropy_bits == 0.0
    assert metrics.meets_mechanical_gate is False


def test_challenge_selector_and_nonce_guard_are_deterministic_and_auditable() -> None:
    challenges = ["challenge-2", "challenge-0", "challenge-1"]
    first = select_challenge(challenges, selector_seed=b"public-seed", nonce=b"nonce-1")
    repeated = select_challenge(list(reversed(challenges)), selector_seed=b"public-seed", nonce=b"nonce-1")
    next_nonce = select_challenge(challenges, selector_seed=b"public-seed", nonce=b"nonce-2")

    assert first == repeated
    assert first.challenge_id in challenges
    assert first.selection_digest != next_nonce.selection_digest
    assert first.nonce_sha256 != next_nonce.nonce_sha256

    guard = NonceReplayGuard()
    assert guard.admit("verifier-a", b"nonce-1") is True
    assert guard.admit("verifier-a", b"nonce-1") is False
    assert guard.admit("verifier-b", b"nonce-1") is True


def test_csv_requires_explicit_split_and_rejects_duplicate_or_nonfinite_rows(tmp_path) -> None:
    missing_split = tmp_path / "missing_split.csv"
    missing_split.write_text(
        "device_id,challenge_id,read_id,r0\nunit-a,c0,e0,0.1\n",
        encoding="utf-8",
    )
    with pytest.raises(CrpProtocolError, match="split"):
        load_measurements(missing_split)

    bad_rows = tmp_path / "bad_rows.csv"
    with bad_rows.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["device_id", "challenge_id", "split", "read_id", "r0"])
        writer.writerow(["unit-a", "c0", "enroll", "e0", "nan"])
    with pytest.raises(CrpProtocolError, match="finite"):
        load_measurements(bad_rows)

    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text(
        "device_id,challenge_id,split,read_id,r0\n" "unit-a,c0,enroll,e0,0.1\n" "unit-a,c0,enroll,e0,0.2\n",
        encoding="utf-8",
    )
    with pytest.raises(CrpProtocolError, match="duplicate"):
        load_measurements(duplicate)


def test_report_contains_receipts_and_no_raw_response_or_threshold_vector() -> None:
    rows = separated_rows()
    model = build_enrollment_model(rows, FEATURE_NAMES)
    metrics = evaluate_protocol(rows, model)
    report = build_report(
        metrics,
        model,
        input_sha256="a" * 64,
        min_stable_bits=64,
        maximum_false_reject_rate=0.05,
    )
    encoded = json.dumps(report, sort_keys=True)

    assert report["verdict"] == "measurement_protocol_candidate"
    assert report["model_sha256"] == model.model_sha256
    assert len(report["template_receipts"]) == 4
    assert len(report["report_sha256"]) == 64
    assert "thresholds" not in report
    assert '"stable_bits":' not in encoded
    assert "-1.0" not in encoded
