#!/usr/bin/env python3
"""Enrollment/verification protocol for Sacred Egg CRP-PUF measurements.

This module is the operational successor to ``sacred_egg_crp_puf_analysis``.
The older harness compares every row with every other row and is useful for
exploration, but it learns quantization thresholds from the same rows it scores.
That makes it unsuitable as an authentication measurement.

V2 enforces a temporal boundary:

* ``enroll`` rows alone create thresholds, stable-bit masks, templates, and
  error radii;
* ``verify`` rows are never consulted while the enrollment model is built;
* genuine, wrong-device, and wrong-challenge attempts are scored separately;
* a domain-separated SHA-256 selector maps a seed and fresh nonce to one
  registered challenge without modulo bias;
* reports contain source/config/template digests, not raw sensor responses.

This code evaluates measurements.  It is not a fuzzy extractor, a replacement
for a standard authenticator, or evidence that any unmeasured physical device
is unclonable.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

SCHEMA_VERSION = "sacred_egg_crp_puf_protocol_v2"
ARCHITECTURE_STATUS = "MEASUREMENT_PROTOCOL_IMPLEMENTED_PHYSICAL_SECURITY_UNMEASURED"
SELECTOR_DOMAIN = b"SCBE-SACRED-EGG-CRP-SELECTOR-v1\x00"
MODEL_DOMAIN = b"SCBE-SACRED-EGG-CRP-MODEL-v2\x00"
VALID_SPLITS = frozenset({"enroll", "verify"})


class CrpProtocolError(ValueError):
    """Raised when a measurement set cannot support a sealed CRP evaluation."""


@dataclass(frozen=True)
class CrpSample:
    device_id: str
    challenge_id: str
    split: str
    read_id: str
    values: tuple[float, ...]
    environment_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("device_id", self.device_id),
            ("challenge_id", self.challenge_id),
            ("read_id", self.read_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise CrpProtocolError(f"{name} must be a non-empty string")
        if self.split not in VALID_SPLITS:
            raise CrpProtocolError(f"split must be one of {sorted(VALID_SPLITS)}")
        if not self.values:
            raise CrpProtocolError("a response must contain at least one feature")
        if any(not math.isfinite(value) for value in self.values):
            raise CrpProtocolError("response features must be finite")


@dataclass(frozen=True)
class ChallengeReceipt:
    schema_version: str
    challenge_id: str
    challenge_count: int
    nonce_sha256: str
    selector_seed_sha256: str
    selection_digest: str
    rejection_counter: int


@dataclass(frozen=True)
class ResponseTemplate:
    device_id: str
    challenge_id: str
    stable_indices: tuple[int, ...]
    stable_bits: tuple[int, ...]
    enrollment_reads: int
    max_enrollment_error_bits: int
    acceptance_radius_bits: int
    template_sha256: str

    @property
    def stable_bit_count(self) -> int:
        return len(self.stable_indices)


@dataclass(frozen=True)
class EnrollmentModel:
    schema_version: str
    feature_names: tuple[str, ...]
    thresholds: tuple[float, ...]
    reliability_floor: float
    error_margin_bits: int
    templates: tuple[ResponseTemplate, ...]
    model_sha256: str

    def template_map(self) -> dict[tuple[str, str], ResponseTemplate]:
        return {(template.device_id, template.challenge_id): template for template in self.templates}


@dataclass(frozen=True)
class VerificationAttempt:
    claimed_device_id: str
    selected_challenge_id: str
    source_device_id: str
    source_challenge_id: str
    accepted: bool
    reason: str
    error_bits: int | None
    compared_bits: int


@dataclass(frozen=True)
class ProtocolMetrics:
    schema_version: str
    architecture_status: str
    enrollment_count: int
    verification_count: int
    device_count: int
    challenge_count: int
    feature_count: int
    template_count: int
    minimum_stable_bits: int
    mean_stable_bits: float
    maximum_acceptance_radius_bits: int
    enrollment_code_margin_bits: int | None
    genuine_attempts: int
    genuine_rejects: int
    false_reject_rate: float
    impostor_attempts: int
    impostor_accepts: int
    false_accept_rate: float
    wrong_challenge_attempts: int
    wrong_challenge_accepts: int
    wrong_challenge_accept_rate: float
    distinct_response_patterns: int
    empirical_response_pattern_min_entropy_bits: float
    marginal_bit_entropy_sum: float
    meets_mechanical_gate: bool


def _median(values: Sequence[float]) -> float:
    if not values:
        raise CrpProtocolError("median requires at least one value")
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_measurements(path: Path) -> tuple[list[CrpSample], list[str]]:
    """Load explicit enrollment and verification rows from a wide CSV."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CrpProtocolError("CSV has no header")
        required = {"device_id", "challenge_id", "split", "read_id"}
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise CrpProtocolError(f"CSV missing required columns: {missing}")
        metadata = required.union({"environment_id"})
        feature_names = [name for name in reader.fieldnames if name not in metadata]
        if not feature_names:
            raise CrpProtocolError("CSV must include at least one numeric response column")

        rows: list[CrpSample] = []
        identities: set[tuple[str, str, str, str]] = set()
        for line_number, row in enumerate(reader, start=2):
            device_id = str(row.get("device_id") or "").strip()
            challenge_id = str(row.get("challenge_id") or "").strip()
            split = str(row.get("split") or "").strip().lower()
            read_id = str(row.get("read_id") or "").strip()
            environment_id = str(row.get("environment_id") or "").strip() or None
            identity = (device_id, challenge_id, split, read_id)
            if identity in identities:
                raise CrpProtocolError(f"line {line_number}: duplicate measurement identity {identity!r}")
            identities.add(identity)
            try:
                values = tuple(float(row[name]) for name in feature_names)
            except (TypeError, ValueError) as exc:
                raise CrpProtocolError(f"line {line_number}: non-numeric response value") from exc
            try:
                rows.append(
                    CrpSample(
                        device_id=device_id,
                        challenge_id=challenge_id,
                        split=split,
                        read_id=read_id,
                        values=values,
                        environment_id=environment_id,
                    )
                )
            except CrpProtocolError as exc:
                raise CrpProtocolError(f"line {line_number}: {exc}") from exc
    return rows, feature_names


def select_challenge(
    challenge_ids: Sequence[str],
    *,
    selector_seed: bytes,
    nonce: bytes,
) -> ChallengeReceipt:
    """Select a registered challenge with domain separation and no modulo bias.

    The selector seed may be public.  This function provides deterministic,
    auditable challenge choice; it does not authenticate the response.  Nonce
    freshness must be enforced by the verifier.
    """

    registered = tuple(sorted(set(challenge_ids)))
    if not registered or any(not isinstance(item, str) or not item for item in registered):
        raise CrpProtocolError("challenge_ids must contain non-empty strings")
    if not selector_seed:
        raise CrpProtocolError("selector_seed must not be empty")
    if not nonce:
        raise CrpProtocolError("nonce must not be empty")

    modulus = len(registered)
    sample_space = 1 << 256
    acceptance_limit = sample_space - (sample_space % modulus)
    counter = 0
    while True:
        digest = hashlib.sha256(
            SELECTOR_DOMAIN
            + len(selector_seed).to_bytes(4, "big")
            + selector_seed
            + len(nonce).to_bytes(4, "big")
            + nonce
            + counter.to_bytes(8, "big")
        ).digest()
        candidate = int.from_bytes(digest, "big")
        if candidate < acceptance_limit:
            return ChallengeReceipt(
                schema_version="sacred_egg_challenge_receipt_v1",
                challenge_id=registered[candidate % modulus],
                challenge_count=modulus,
                nonce_sha256=_sha256_bytes(nonce),
                selector_seed_sha256=_sha256_bytes(selector_seed),
                selection_digest=digest.hex(),
                rejection_counter=counter,
            )
        counter += 1


class NonceReplayGuard:
    """Small verifier-owned replay guard for one process/session boundary."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def admit(self, verifier_id: str, nonce: bytes) -> bool:
        if not verifier_id or not nonce:
            raise CrpProtocolError("verifier_id and nonce are required")
        key = (verifier_id, _sha256_bytes(nonce))
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def quantize(values: Sequence[float], thresholds: Sequence[float]) -> tuple[int, ...]:
    if len(values) != len(thresholds):
        raise CrpProtocolError("values and thresholds length mismatch")
    return tuple(int(value >= threshold) for value, threshold in zip(values, thresholds))


def _group_rows(rows: Iterable[CrpSample]) -> dict[tuple[str, str], list[CrpSample]]:
    groups: dict[tuple[str, str], list[CrpSample]] = {}
    for row in rows:
        groups.setdefault((row.device_id, row.challenge_id), []).append(row)
    return groups


def _template_digest(
    device_id: str,
    challenge_id: str,
    stable_indices: Sequence[int],
    stable_bits: Sequence[int],
) -> str:
    packet = {
        "device_id": device_id,
        "challenge_id": challenge_id,
        "stable_indices": list(stable_indices),
        "stable_bits": list(stable_bits),
    }
    return _sha256_bytes(MODEL_DOMAIN + _canonical_json(packet))


def build_enrollment_model(
    rows: Sequence[CrpSample],
    feature_names: Sequence[str],
    *,
    reliability_floor: float = 0.90,
    error_margin_bits: int = 0,
) -> EnrollmentModel:
    """Build a response model using enrollment rows and enrollment rows only."""

    if not 0.5 < reliability_floor <= 1.0:
        raise CrpProtocolError("reliability_floor must be in (0.5, 1.0]")
    if type(error_margin_bits) is not int or error_margin_bits < 0:
        raise CrpProtocolError("error_margin_bits must be a non-negative integer")
    enroll = [row for row in rows if row.split == "enroll"]
    if not enroll:
        raise CrpProtocolError("at least one enrollment row is required")
    width = len(feature_names)
    if width == 0 or any(len(row.values) != width for row in rows):
        raise CrpProtocolError("feature_names and response widths must agree")

    groups = _group_rows(enroll)
    sparse = [key for key, group in groups.items() if len(group) < 2]
    if sparse:
        raise CrpProtocolError(f"each device/challenge needs at least two enrollment reads: {sparse!r}")

    # One median response per device/challenge prevents heavily sampled devices
    # from moving global thresholds toward themselves.
    group_centers = [
        tuple(_median([row.values[index] for row in group]) for index in range(width)) for group in groups.values()
    ]
    thresholds = tuple(_median([center[index] for center in group_centers]) for index in range(width))

    templates: list[ResponseTemplate] = []
    for (device_id, challenge_id), group in sorted(groups.items()):
        bit_rows = [quantize(row.values, thresholds) for row in group]
        stable_indices: list[int] = []
        stable_bits: list[int] = []
        for index in range(width):
            ones = sum(bits[index] for bits in bit_rows)
            majority = int(ones * 2 >= len(bit_rows))
            agreement = max(ones, len(bit_rows) - ones) / len(bit_rows)
            if agreement >= reliability_floor:
                stable_indices.append(index)
                stable_bits.append(majority)
        if not stable_indices:
            raise CrpProtocolError(f"no stable response bits for {(device_id, challenge_id)!r}")
        errors = [
            sum(bits[index] != expected for index, expected in zip(stable_indices, stable_bits)) for bits in bit_rows
        ]
        radius = max(errors) + error_margin_bits
        if radius >= len(stable_indices):
            raise CrpProtocolError(f"acceptance radius consumes every stable bit for {(device_id, challenge_id)!r}")
        templates.append(
            ResponseTemplate(
                device_id=device_id,
                challenge_id=challenge_id,
                stable_indices=tuple(stable_indices),
                stable_bits=tuple(stable_bits),
                enrollment_reads=len(group),
                max_enrollment_error_bits=max(errors),
                acceptance_radius_bits=radius,
                template_sha256=_template_digest(device_id, challenge_id, stable_indices, stable_bits),
            )
        )

    model_record = {
        "schema_version": SCHEMA_VERSION,
        "feature_names": list(feature_names),
        "thresholds": list(thresholds),
        "reliability_floor": reliability_floor,
        "error_margin_bits": error_margin_bits,
        "templates": [asdict(template) for template in templates],
    }
    model_sha256 = _sha256_bytes(MODEL_DOMAIN + _canonical_json(model_record))
    return EnrollmentModel(
        schema_version=SCHEMA_VERSION,
        feature_names=tuple(feature_names),
        thresholds=thresholds,
        reliability_floor=reliability_floor,
        error_margin_bits=error_margin_bits,
        templates=tuple(templates),
        model_sha256=model_sha256,
    )


def verify_values(
    values: Sequence[float],
    *,
    source_device_id: str,
    source_challenge_id: str,
    claimed_device_id: str,
    selected_challenge_id: str,
    model: EnrollmentModel,
    enforce_source_challenge: bool = True,
) -> VerificationAttempt:
    """Compare one measured response with a selected enrolled template."""

    if len(values) != len(model.thresholds):
        raise CrpProtocolError("response width does not match the enrollment model")
    if any(not math.isfinite(value) for value in values):
        raise CrpProtocolError("response features must be finite")
    if enforce_source_challenge and source_challenge_id != selected_challenge_id:
        return VerificationAttempt(
            claimed_device_id=claimed_device_id,
            selected_challenge_id=selected_challenge_id,
            source_device_id=source_device_id,
            source_challenge_id=source_challenge_id,
            accepted=False,
            reason="challenge_mismatch",
            error_bits=None,
            compared_bits=0,
        )
    template = model.template_map().get((claimed_device_id, selected_challenge_id))
    if template is None:
        return VerificationAttempt(
            claimed_device_id=claimed_device_id,
            selected_challenge_id=selected_challenge_id,
            source_device_id=source_device_id,
            source_challenge_id=source_challenge_id,
            accepted=False,
            reason="template_missing",
            error_bits=None,
            compared_bits=0,
        )
    bits = quantize(values, model.thresholds)
    errors = sum(bits[index] != expected for index, expected in zip(template.stable_indices, template.stable_bits))
    accepted = errors <= template.acceptance_radius_bits
    return VerificationAttempt(
        claimed_device_id=claimed_device_id,
        selected_challenge_id=selected_challenge_id,
        source_device_id=source_device_id,
        source_challenge_id=source_challenge_id,
        accepted=accepted,
        reason="within_enrollment_radius" if accepted else "outside_enrollment_radius",
        error_bits=errors,
        compared_bits=template.stable_bit_count,
    )


def _template_distance_bits(left: ResponseTemplate, right: ResponseTemplate) -> int | None:
    left_map = dict(zip(left.stable_indices, left.stable_bits))
    right_map = dict(zip(right.stable_indices, right.stable_bits))
    common = sorted(left_map.keys() & right_map.keys())
    if not common:
        return None
    return sum(left_map[index] != right_map[index] for index in common)


def _enrollment_code_margin(model: EnrollmentModel) -> int | None:
    margins: list[int] = []
    for index, left in enumerate(model.templates):
        for right in model.templates[index + 1 :]:
            if left.challenge_id != right.challenge_id or left.device_id == right.device_id:
                continue
            distance = _template_distance_bits(left, right)
            if distance is not None:
                margins.append(distance - left.acceptance_radius_bits - right.acceptance_radius_bits)
    return min(margins) if margins else None


def _entropy_summaries(model: EnrollmentModel) -> tuple[int, float, float]:
    # Identity-bound template receipts are intentionally all different because
    # they include device_id and challenge_id.  Counting those receipts would
    # manufacture entropy from labels.  Measure only the quantized response
    # pattern and its stable-index mask here.
    digests = [
        _sha256_bytes(
            _canonical_json(
                {
                    "stable_indices": list(template.stable_indices),
                    "stable_bits": list(template.stable_bits),
                }
            )
        )
        for template in model.templates
    ]
    counts: dict[str, int] = {}
    for digest in digests:
        counts[digest] = counts.get(digest, 0) + 1
    distinct = len(counts)
    empirical_min_entropy = -math.log2(max(counts.values()) / len(digests)) if digests else 0.0

    # This is deliberately labelled a marginal sum.  Correlated bits can make
    # it much larger than true joint min-entropy, so it never gates a security
    # claim in this harness.
    union_indices = sorted({index for template in model.templates for index in template.stable_indices})
    marginal_sum = 0.0
    for index in union_indices:
        values = [
            dict(zip(template.stable_indices, template.stable_bits))[index]
            for template in model.templates
            if index in template.stable_indices
        ]
        if len(values) < 2:
            continue
        probability_one = sum(values) / len(values)
        marginal_sum += -math.log2(max(probability_one, 1.0 - probability_one))
    return distinct, empirical_min_entropy, marginal_sum


def evaluate_protocol(
    rows: Sequence[CrpSample],
    model: EnrollmentModel,
    *,
    min_stable_bits: int = 64,
    maximum_false_reject_rate: float = 0.05,
) -> ProtocolMetrics:
    """Evaluate held-out reads without changing the enrollment model."""

    if min_stable_bits <= 0:
        raise CrpProtocolError("min_stable_bits must be positive")
    if not 0.0 <= maximum_false_reject_rate <= 1.0:
        raise CrpProtocolError("maximum_false_reject_rate must be in [0, 1]")
    verify_rows = [row for row in rows if row.split == "verify"]
    if not verify_rows:
        raise CrpProtocolError("at least one verification row is required")
    templates = model.template_map()
    missing = sorted(
        {(row.device_id, row.challenge_id) for row in verify_rows if (row.device_id, row.challenge_id) not in templates}
    )
    if missing:
        raise CrpProtocolError(f"verification rows lack enrollment templates: {missing!r}")

    genuine: list[VerificationAttempt] = []
    impostor: list[VerificationAttempt] = []
    wrong_challenge: list[VerificationAttempt] = []
    for row in verify_rows:
        genuine.append(
            verify_values(
                row.values,
                source_device_id=row.device_id,
                source_challenge_id=row.challenge_id,
                claimed_device_id=row.device_id,
                selected_challenge_id=row.challenge_id,
                model=model,
            )
        )
        for candidate in model.templates:
            if candidate.challenge_id == row.challenge_id and candidate.device_id != row.device_id:
                impostor.append(
                    verify_values(
                        row.values,
                        source_device_id=row.device_id,
                        source_challenge_id=row.challenge_id,
                        claimed_device_id=candidate.device_id,
                        selected_challenge_id=candidate.challenge_id,
                        model=model,
                    )
                )
            if candidate.device_id == row.device_id and candidate.challenge_id != row.challenge_id:
                # Relabel the captured response as though it answered another
                # challenge.  This is stricter than the structural mismatch
                # check and measures response cross-talk/replay acceptance.
                wrong_challenge.append(
                    verify_values(
                        row.values,
                        source_device_id=row.device_id,
                        source_challenge_id=row.challenge_id,
                        claimed_device_id=row.device_id,
                        selected_challenge_id=candidate.challenge_id,
                        model=model,
                        enforce_source_challenge=False,
                    )
                )

    genuine_rejects = sum(not attempt.accepted for attempt in genuine)
    impostor_accepts = sum(attempt.accepted for attempt in impostor)
    wrong_accepts = sum(attempt.accepted for attempt in wrong_challenge)
    false_reject_rate = genuine_rejects / len(genuine)
    false_accept_rate = impostor_accepts / len(impostor) if impostor else 1.0
    wrong_accept_rate = wrong_accepts / len(wrong_challenge) if wrong_challenge else 1.0
    stable_counts = [template.stable_bit_count for template in model.templates]
    code_margin = _enrollment_code_margin(model)
    distinct, empirical_entropy, marginal_sum = _entropy_summaries(model)
    meets_gate = bool(
        min(stable_counts) >= min_stable_bits
        and code_margin is not None
        and code_margin > 0
        and false_reject_rate <= maximum_false_reject_rate
        and impostor
        and impostor_accepts == 0
        and wrong_challenge
        and wrong_accepts == 0
    )
    return ProtocolMetrics(
        schema_version=SCHEMA_VERSION,
        architecture_status=ARCHITECTURE_STATUS,
        enrollment_count=sum(row.split == "enroll" for row in rows),
        verification_count=len(verify_rows),
        device_count=len({row.device_id for row in rows}),
        challenge_count=len({row.challenge_id for row in rows}),
        feature_count=len(model.feature_names),
        template_count=len(model.templates),
        minimum_stable_bits=min(stable_counts),
        mean_stable_bits=float(mean(stable_counts)),
        maximum_acceptance_radius_bits=max(template.acceptance_radius_bits for template in model.templates),
        enrollment_code_margin_bits=code_margin,
        genuine_attempts=len(genuine),
        genuine_rejects=genuine_rejects,
        false_reject_rate=false_reject_rate,
        impostor_attempts=len(impostor),
        impostor_accepts=impostor_accepts,
        false_accept_rate=false_accept_rate,
        wrong_challenge_attempts=len(wrong_challenge),
        wrong_challenge_accepts=wrong_accepts,
        wrong_challenge_accept_rate=wrong_accept_rate,
        distinct_response_patterns=distinct,
        empirical_response_pattern_min_entropy_bits=empirical_entropy,
        marginal_bit_entropy_sum=marginal_sum,
        meets_mechanical_gate=meets_gate,
    )


def build_report(
    metrics: ProtocolMetrics,
    model: EnrollmentModel,
    *,
    input_sha256: str,
    min_stable_bits: int,
    maximum_false_reject_rate: float,
) -> dict[str, object]:
    """Build a reviewable report that excludes raw physical responses."""

    report: dict[str, object] = asdict(metrics)
    report.update(
        {
            "input_sha256": input_sha256,
            "model_sha256": model.model_sha256,
            "feature_names": list(model.feature_names),
            "reliability_floor": model.reliability_floor,
            "error_margin_bits": model.error_margin_bits,
            "min_stable_bits_gate": min_stable_bits,
            "maximum_false_reject_rate_gate": maximum_false_reject_rate,
            "template_receipts": [
                {
                    "device_id": template.device_id,
                    "challenge_id": template.challenge_id,
                    "stable_bit_count": template.stable_bit_count,
                    "enrollment_reads": template.enrollment_reads,
                    "max_enrollment_error_bits": template.max_enrollment_error_bits,
                    "acceptance_radius_bits": template.acceptance_radius_bits,
                    "template_sha256": template.template_sha256,
                }
                for template in model.templates
            ],
            "verdict": "measurement_protocol_candidate" if metrics.meets_mechanical_gate else "reject_or_collect_more",
            "security_boundary": (
                "A pass proves held-out separation for this capture only. It does not establish joint min-entropy, "
                "modeling-attack resistance, unclonability, a fuzzy extractor, or authorization. Bind a fresh "
                "challenge receipt and the accepted measurement to a standard cryptographic authenticator."
            ),
            "entropy_boundary": (
                "empirical_response_pattern_min_entropy_bits is capped by sample count; "
                "marginal_bit_entropy_sum assumes "
                "away correlations and is descriptive only. Neither is a production key-entropy claim."
            ),
        }
    )
    report_sha256 = _sha256_bytes(_canonical_json(report))
    report["report_sha256"] = report_sha256
    return report


def write_report(report: Mapping[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate explicit enrollment/verification CRP-PUF captures without split leakage."
    )
    parser.add_argument("csv", type=Path, help="CSV with device_id, challenge_id, split, read_id, response columns")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/aetherfab/sacred_egg_crp_puf_protocol_v2.json"),
    )
    parser.add_argument("--reliability-floor", type=float, default=0.90)
    parser.add_argument("--error-margin-bits", type=int, default=0)
    parser.add_argument("--min-stable-bits", type=int, default=64)
    parser.add_argument("--maximum-frr", type=float, default=0.05)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows, feature_names = load_measurements(args.csv)
    model = build_enrollment_model(
        rows,
        feature_names,
        reliability_floor=args.reliability_floor,
        error_margin_bits=args.error_margin_bits,
    )
    metrics = evaluate_protocol(
        rows,
        model,
        min_stable_bits=args.min_stable_bits,
        maximum_false_reject_rate=args.maximum_frr,
    )
    report = build_report(
        metrics,
        model,
        input_sha256=sha256_file(args.csv),
        min_stable_bits=args.min_stable_bits,
        maximum_false_reject_rate=args.maximum_frr,
    )
    write_report(report, args.report)
    print(
        "Sacred Egg CRP-PUF protocol v2: "
        f"FRR={metrics.false_reject_rate:.6f} "
        f"FAR={metrics.false_accept_rate:.6f} "
        f"wrong_challenge={metrics.wrong_challenge_accept_rate:.6f} "
        f"stable_bits_min={metrics.minimum_stable_bits} "
        f"code_margin={metrics.enrollment_code_margin_bits} "
        f"verdict={report['verdict']}"
    )
    print(f"report={args.report}")
    return 0 if metrics.meets_mechanical_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
