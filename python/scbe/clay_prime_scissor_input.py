"""Causal prime-scissor byte features for Clay's frozen action model.

The canonical byte remains the identity.  A committed ``clay_math`` universal
cycle maps every byte rank through a caller-owned next-prime writable slot and
two crossed prime-lane schedules, verifies the round trip, then exposes only a
spectrally compact feature table.  The learned projection is applied to owned
byte positions before the frozen GRU and only on the action path.

Control tables use the same 206 -> 64 projection. The canonical control matches
the candidate's uniform-token spectrum/Gram, while the random control matches
every candidate token's row norm. The shuffled control is not a fixed token
permutation: train and holdout each receive an independently seeded, sealed,
one-to-one derangement of their own byte occurrences.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch import Tensor, nn

from clay_math.prime_lane_scissors import (
    PrimeLaneFrame,
    ScheduleSpec,
    create_prime_spot_assignment,
    create_scissor_packet,
    select_prime_anchor,
    verify_prime_spot_assignment,
    verify_scissor_packet,
)
from clay_math.universal_cycle_curriculum import (
    ZERO_HASH,
    UniversalCycleShell,
    iter_window_sections,
)
from clay_math.universal_prime_scissors import (
    create_window_prime_scissor,
    verify_window_prime_scissor,
)
from python.scbe.clay_frozen_multiview_adapter import FrozenActionModel
from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    BYTE_TOKEN_BASE,
    decode_byte_token_text,
)

SCHEMA = "clay.prime-scissor-input.v1"
BINDING_SCHEMA = f"{SCHEMA}.occurrence-derangement"
BYTE_COUNT = 256
FEATURE_WIDTH = 206
EMBEDDING_WIDTH = 64
ANCHOR_POLICIES = ("next-cyclic", "previous-cyclic")
LEFT_SPEC = ScheduleSpec(offset=0, reverse=False, shuffle_key="left")
RIGHT_SPEC = ScheduleSpec(
    offset=2,
    reverse=True,
    shuffle_key="right",
)
PIVOT_MODULUS = 1_000_003
ARMS = (
    "prime_scissor_input",
    "canonical_onehot_matched",
    "shuffled_binding_matched",
    "deterministic_random_matched",
    "no_intervention_matched",
)
TABLE_ARM = {
    "prime_scissor_input": "prime_scissor",
    "canonical_onehot_matched": "canonical_onehot_matched",
    "shuffled_binding_matched": "prime_scissor",
    "deterministic_random_matched": "deterministic_random_matched",
    "no_intervention_matched": "no_intervention",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def tensor_sha256(value: Tensor) -> str:
    array = value.detach().cpu().contiguous().numpy()
    header = _canonical_json({"dtype": str(array.dtype), "shape": list(array.shape)})
    return hashlib.sha256(header + b"\n" + array.tobytes(order="C")).hexdigest()


def _raw_prime_scissor_rows(
    policy: str,
) -> tuple[np.ndarray, tuple[str, ...], dict[str, Any]]:
    """Build one audited integer feature block under a committed anchor policy."""

    if policy not in ANCHOR_POLICIES:
        raise ValueError(f"unsupported structural anchor policy: {policy}")

    shell = UniversalCycleShell(
        alphabet_size=16,
        order=2,
        namespace="clay-byte-token-id-v1",
    )
    frame = PrimeLaneFrame(domain_size=BYTE_COUNT)
    section = next(iter_window_sections(shell, partition_size=BYTE_COUNT))
    if section.previous_section_hash != ZERO_HASH or not section.terminal:
        raise RuntimeError(
            "byte universal-cycle section is not the expected single trusted section"
        )
    windows = {window.rank: window for window in section.windows}
    if set(windows) != set(range(BYTE_COUNT)):
        raise RuntimeError(
            "byte universal-cycle section does not cover every canonical byte"
        )
    names: list[str] = []
    rows: list[list[float]] = []
    packet_hashes: list[str] = []
    bundle_hashes: list[str] = []
    anchors: list[int] = []
    for value in range(BYTE_COUNT):
        window = windows[value]
        anchor = select_prime_anchor(frame, value, policy=policy)
        policy_assignment = create_prime_spot_assignment(
            frame,
            value,
            policy=policy,
            assignment_label=f"clay-byte-policy:{policy}:value:{value}",
        )
        verify_prime_spot_assignment(
            frame,
            policy_assignment,
            expected_value=value,
            policy=policy,
            expected_receipt_hash=policy_assignment.receipt_hash,
        )
        packet = create_scissor_packet(
            frame,
            policy_assignment,
            left_spec=LEFT_SPEC,
            right_spec=RIGHT_SPEC,
            include_degree2=True,
        )
        verify_scissor_packet(
            frame,
            packet,
            expected_value=value,
            expected_slots=frame.residues(anchor),
            expected_packet_hash=packet.packet_hash,
        )

        # The universal bridge independently binds the same numeric structure
        # to a caller-owned rank/window and section receipt.
        bundle = create_window_prime_scissor(
            shell,
            frame,
            window,
            source_section_hash=section.receipt_hash,
            anchor_prime=anchor,
            left_spec=LEFT_SPEC,
            right_spec=RIGHT_SPEC,
            include_degree2=True,
        )
        recovered = verify_window_prime_scissor(
            shell,
            frame,
            bundle,
            expected_section_hash=section.receipt_hash,
            expected_window=window,
            expected_receipt_hash=bundle.receipt_hash,
            expected_anchor_prime=anchor,
            expected_left_spec=LEFT_SPEC,
            expected_right_spec=RIGHT_SPEC,
            expected_include_degree2=True,
        )
        if recovered.rank != value:
            raise RuntimeError(
                "verified prime-scissor bundle changed the canonical byte"
            )
        if (
            policy_assignment.canonical_value,
            policy_assignment.canonical_is_prime,
            policy_assignment.canonical_residues,
            policy_assignment.sheared_residues,
            policy_assignment.writable_slots,
            policy_assignment.inverse_residuals,
        ) != (
            bundle.packet.assignment.canonical_value,
            bundle.packet.assignment.canonical_is_prime,
            bundle.packet.assignment.canonical_residues,
            bundle.packet.assignment.sheared_residues,
            bundle.packet.assignment.writable_slots,
            bundle.packet.assignment.inverse_residuals,
        ):
            raise RuntimeError("universal bridge and prime-spot policy disagree")
        if packet.steps != bundle.packet.steps:
            raise RuntimeError("universal bridge and prime-spot scissors disagree")

        assignment = policy_assignment
        row: list[float] = []
        row_names: list[str] = []

        def add(name: str, item: int | bool | None) -> None:
            row_names.append(name)
            row.append(float(0 if item is None else item))

        add("canonical_is_prime", assignment.canonical_is_prime)
        add("anchor", anchor)
        for field_name, field_values in (
            ("canonical_residue", assignment.canonical_residues),
            ("sheared_residue", assignment.sheared_residues),
            ("writable_prime_slot", assignment.writable_slots),
            ("inverse_residual", assignment.inverse_residuals),
        ):
            for lane, item in enumerate(field_values):
                add(f"{field_name}_{lane}", item)

        for step in packet.steps:
            prefix = f"cross_{step.index}"
            for field_name in (
                "left_lane",
                "right_lane",
                "left_modulus",
                "right_modulus",
                "left_slot",
                "right_slot",
                "left_canonical_residue",
                "right_canonical_residue",
                "left_residue_delta",
                "right_residue_delta",
                "cross_slot_difference",
                "cross_residual_difference",
                "slot_product",
            ):
                add(f"{prefix}_{field_name}", getattr(step, field_name))
            for field_name in (
                "bit_deltas_lsb",
                "bit_xor_lsb",
                "canonical_bit_deltas_lsb",
                "canonical_bit_xor_lsb",
                "residual_bit_deltas_lsb",
                "residual_bit_xor_lsb",
                "bit_hadamard_lsb",
            ):
                values = getattr(step, field_name)
                if values is None:
                    raise RuntimeError(
                        f"degree-two field is absent: {prefix}_{field_name}"
                    )
                for bit, item in enumerate(values):
                    add(f"{prefix}_{field_name}_{bit}", item)

        if not names:
            names = row_names
        elif names != row_names:
            raise RuntimeError("prime-scissor feature schema changed between byte rows")
        rows.append(row)
        anchors.append(anchor)
        packet_hashes.append(packet.packet_hash)
        bundle_hashes.append(bundle.receipt_hash)

    matrix = np.asarray(rows, dtype=np.float64)
    receipt = {
        "schema": f"{SCHEMA}.raw-feature-receipt",
        "shell_id": shell.shell_id,
        "section_receipt_hash": section.receipt_hash,
        "frame_id": frame.frame_id,
        "anchor_policy": policy,
        "anchor_sha256": _sha256_json(anchors),
        "left_schedule": list(packet.left_schedule),
        "right_schedule": list(packet.right_schedule),
        "packet_hashes_sha256": _sha256_json(packet_hashes),
        "bundle_hashes_sha256": _sha256_json(bundle_hashes),
        "raw_shape": list(matrix.shape),
        "raw_schema_sha256": _sha256_json(names),
        "raw_values_sha256": hashlib.sha256(
            matrix.astype("<f8", copy=False).tobytes()
        ).hexdigest(),
    }
    return matrix, tuple(names), receipt


def _modular_pivot_columns(matrix: np.ndarray, modulus: int) -> tuple[int, ...]:
    """Return exact left-to-right RREF pivot columns over one prime field."""

    if matrix.ndim != 2 or matrix.shape[0] != BYTE_COUNT - 1:
        raise ValueError("affine-difference matrix must have 255 rows")
    work = np.remainder(np.asarray(matrix, dtype=np.int64), modulus)
    pivot_row = 0
    pivots: list[int] = []
    for column in range(work.shape[1]):
        candidates = np.flatnonzero(work[pivot_row:, column])
        if not candidates.size:
            continue
        source = pivot_row + int(candidates[0])
        if source != pivot_row:
            work[[pivot_row, source]] = work[[source, pivot_row]]
        inverse = pow(int(work[pivot_row, column]), -1, modulus)
        work[pivot_row] = (work[pivot_row] * inverse) % modulus
        factors = work[:, column].copy()
        factors[pivot_row] = 0
        work = (work - factors[:, None] * work[pivot_row][None, :]) % modulus
        pivots.append(column)
        pivot_row += 1
        if pivot_row == work.shape[0]:
            break
    return tuple(pivots)


def _hadamard_basis(rank: int) -> np.ndarray:
    if not 1 <= rank <= BYTE_COUNT - 1:
        raise ValueError("matched control rank must lie in [1, 255]")
    basis = np.empty((BYTE_COUNT, rank), dtype=np.float64)
    scale = math.sqrt(BYTE_COUNT)
    for row in range(BYTE_COUNT):
        for column in range(1, rank + 1):
            basis[row, column - 1] = (
                -1.0 if (row & column).bit_count() & 1 else 1.0
            ) / scale
    if not np.allclose(basis.T @ basis, np.eye(rank), atol=1e-12, rtol=0.0):
        raise RuntimeError("canonical one-hot Hadamard basis is not orthonormal")
    return basis


def _deterministic_random_basis(rank: int, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gaussian = rng.standard_normal((BYTE_COUNT, rank))
    gaussian -= gaussian.mean(axis=0, keepdims=True)
    basis, upper = np.linalg.qr(gaussian, mode="reduced")
    signs = np.where(np.diag(upper) < 0.0, -1.0, 1.0)
    basis *= signs
    if np.linalg.norm(basis.mean(axis=0)) > 1e-12:
        raise RuntimeError("random matched basis escaped the centered byte subspace")
    if not np.allclose(basis.T @ basis, np.eye(rank), atol=1e-12, rtol=0.0):
        raise RuntimeError("random matched basis is not orthonormal")
    return basis


def _row_norm_matched_random(
    target_row_norms: np.ndarray, *, width: int, seed: int
) -> np.ndarray:
    """Alternate exact row-sphere and centered-column projections deterministically."""

    rng = np.random.default_rng(seed)
    value = rng.standard_normal((len(target_row_norms), width))
    for _ in range(10_000):
        value -= value.mean(axis=0, keepdims=True)
        row_norms = np.linalg.norm(value, axis=1)
        if np.any(row_norms <= 0.0):
            raise RuntimeError("random row-norm control produced a zero direction")
        value *= (target_row_norms / row_norms)[:, None]
        if (
            np.linalg.norm(value.mean(axis=0)) <= 1e-12
            and np.max(np.abs(np.linalg.norm(value, axis=1) - target_row_norms))
            <= 1e-12
        ):
            break
    else:
        raise RuntimeError(
            "random row-norm control did not converge to centered row spheres"
        )
    if np.linalg.matrix_rank(value, tol=1e-10) != width:
        raise RuntimeError("random row-norm control lost variable rank")
    return value


@dataclass(frozen=True, slots=True)
class FeatureTables:
    tables: Mapping[str, Tensor]
    receipt: Mapping[str, Any]

    def table_for_arm(self, arm: str) -> Tensor:
        if arm not in TABLE_ARM:
            raise ValueError(f"unknown prime-scissor arm: {arm}")
        return self.tables[TABLE_ARM[arm]]


@lru_cache(maxsize=1)
def build_feature_tables() -> FeatureTables:
    """Create the candidate and complementary capacity/leverage controls."""

    blocks = [_raw_prime_scissor_rows(policy) for policy in ANCHOR_POLICIES]
    if any(block[0].shape != (BYTE_COUNT, 456) for block in blocks):
        raise RuntimeError("audited prime-scissor block width changed")
    combined = np.concatenate([block[0].astype(np.int64) for block in blocks], axis=1)
    combined_names = tuple(
        f"{policy}:{name}"
        for policy, (_matrix, names, _receipt) in zip(
            ANCHOR_POLICIES, blocks, strict=True
        )
        for name in names
    )
    differences = combined[1:] - combined[0:1]
    pivots = _modular_pivot_columns(differences, PIVOT_MODULUS)
    if len(pivots) != FEATURE_WIDTH - 1:
        raise RuntimeError(f"audited dual-policy affine rank changed: {len(pivots)}")
    pivot_names = tuple(combined_names[index] for index in pivots)
    fraw = np.column_stack(
        [
            np.ones(BYTE_COUNT, dtype=np.int64),
            combined[:, np.asarray(pivots, dtype=np.int64)],
        ]
    )
    if _modular_pivot_columns(fraw[1:] - fraw[0:1], PIVOT_MODULUS) != tuple(
        range(1, FEATURE_WIDTH)
    ):
        raise RuntimeError(
            "selected structural pivot table lost exact affine independence"
        )

    variable = fraw[:, 1:].astype(np.float64)
    variable -= variable.mean(axis=0, keepdims=True)
    column_norms = np.linalg.norm(variable, axis=0)
    if np.any(column_norms <= 0.0):
        raise RuntimeError("selected structural pivot contains a constant column")
    variable /= column_norms
    constant = np.full((BYTE_COUNT, 1), 1.0 / math.sqrt(BYTE_COUNT), dtype=np.float64)
    prime = np.concatenate([constant, variable], axis=1)

    _u, singular, right = np.linalg.svd(variable, full_matrices=False)
    if int(np.count_nonzero(singular > singular[0] * 1e-10)) != FEATURE_WIDTH - 1:
        raise RuntimeError("normalized structural pivot table lost affine rank")
    canonical_variable = (_hadamard_basis(FEATURE_WIDTH - 1) * singular) @ right
    random_variable = _row_norm_matched_random(
        np.linalg.norm(variable, axis=1),
        width=FEATURE_WIDTH - 1,
        seed=20261118,
    )
    canonical = np.concatenate([constant, canonical_variable], axis=1)
    random_control = np.concatenate([constant, random_variable], axis=1)
    no_intervention = np.zeros_like(prime)

    float_tables = {
        "prime_scissor": torch.from_numpy(prime.astype(np.float32)),
        "canonical_onehot_matched": torch.from_numpy(canonical.astype(np.float32)),
        "deterministic_random_matched": torch.from_numpy(
            random_control.astype(np.float32)
        ),
        "no_intervention": torch.from_numpy(no_intervention.astype(np.float32)),
    }
    nonzero_names = (
        "prime_scissor",
        "canonical_onehot_matched",
        "deterministic_random_matched",
    )
    spectra = {
        name: torch.linalg.svdvals(float_tables[name].double()).cpu().numpy()
        for name in nonzero_names
    }
    reference = spectra["prime_scissor"]
    if not np.allclose(
        reference, spectra["canonical_onehot_matched"], atol=2e-5, rtol=2e-6
    ):
        raise RuntimeError(
            "canonical control does not preserve the candidate singular spectrum"
        )
    grams = {
        name: float_tables[name].double().T @ float_tables[name].double()
        for name in nonzero_names
    }
    if not torch.allclose(
        grams["prime_scissor"],
        grams["canonical_onehot_matched"],
        atol=2e-5,
        rtol=2e-6,
    ):
        raise RuntimeError(
            "canonical control does not preserve candidate column Gram/norm"
        )
    if not torch.allclose(
        torch.linalg.vector_norm(float_tables["prime_scissor"].double(), dim=1),
        torch.linalg.vector_norm(
            float_tables["deterministic_random_matched"].double(), dim=1
        ),
        atol=2e-6,
        rtol=2e-6,
    ):
        raise RuntimeError(
            "random control does not preserve every candidate token row norm"
        )
    unique_rows = {
        name: int(torch.unique(float_tables[name], dim=0).shape[0])
        for name in nonzero_names
    }
    if any(count != BYTE_COUNT for count in unique_rows.values()):
        raise RuntimeError(
            "candidate or matched control collapsed canonical byte identities"
        )

    receipt = {
        "schema": f"{SCHEMA}.feature-tables",
        "raw": {
            policy: block[2]
            for policy, block in zip(ANCHOR_POLICIES, blocks, strict=True)
        },
        "raw_block_width": 456,
        "combined_raw_width": int(combined.shape[1]),
        "combined_raw_sha256": hashlib.sha256(
            combined.astype("<i8", copy=False).tobytes()
        ).hexdigest(),
        "pivot_modulus": PIVOT_MODULUS,
        "pivot_count": len(pivots),
        "pivot_indices_sha256": _sha256_json(pivots),
        "pivot_descriptors_sha256": _sha256_json(pivot_names),
        "fraw_sha256": hashlib.sha256(
            fraw.astype("<i8", copy=False).tobytes()
        ).hexdigest(),
        "affine_rank": FEATURE_WIDTH - 1,
        "linear_rank_with_constant": FEATURE_WIDTH,
        "feature_width": FEATURE_WIDTH,
        "constant_rail": 1.0 / math.sqrt(BYTE_COUNT),
        "variable_column_l2_norm": 1.0,
        "frobenius_norm": math.sqrt(FEATURE_WIDTH),
        "singular_values_sha256": hashlib.sha256(
            singular.astype("<f8", copy=False).tobytes()
        ).hexdigest(),
        "table_sha256": {
            name: tensor_sha256(table) for name, table in float_tables.items()
        },
        "unique_rows": unique_rows,
        "canonical_control": "205 centered Sylvester-Hadamard axes of canonical one-hot, candidate S/V applied",
        "control_match_classes": {
            "canonical_onehot_matched": "uniform-token global singular spectrum and column Gram",
            "deterministic_random_matched": "seeded centered random directions with exact per-token candidate row norm",
            "shuffled_binding_matched": "candidate table with split-local occurrence-level binding broken",
            "no_intervention_matched": "identical learned topology with a zero table",
        },
        "random_row_norms_sha256": tensor_sha256(
            torch.linalg.vector_norm(
                float_tables["deterministic_random_matched"], dim=1
            )
        ),
        "candidate_row_norms_sha256": tensor_sha256(
            torch.linalg.vector_norm(float_tables["prime_scissor"], dim=1)
        ),
        "random_control": "seeded centered Gaussian directions, exact candidate variable-row norms, full rank",
    }
    return FeatureTables(tables=float_tables, receipt=receipt)


@dataclass(frozen=True, slots=True)
class SealedOccurrenceDerangement:
    """One split-local byte-occurrence permutation with no value fixed points."""

    sample_ids: tuple[str, ...]
    mapped_values: Tensor
    occurrence_width: int
    split_name: str
    seed: int
    pool_sha256: str
    permutation_sha256: str
    mapped_values_sha256: str
    association: Mapping[str, Any]
    seal_sha256: str

    def __post_init__(self) -> None:
        if self.mapped_values.dtype != torch.uint8:
            raise ValueError("deranged occurrence values must be uint8")
        if tuple(self.mapped_values.shape) != (
            len(self.sample_ids),
            self.occurrence_width,
        ):
            raise ValueError(
                "deranged occurrence table shape differs from its sample IDs"
            )
        if len(set(self.sample_ids)) != len(self.sample_ids):
            raise ValueError("derangement sample IDs must be unique")
        if tensor_sha256(self.mapped_values) != self.mapped_values_sha256:
            raise ValueError("deranged occurrence values differ from their receipt")
        if _sha256_json(self.metadata()) != self.seal_sha256:
            raise ValueError("derangement seal differs")

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": BINDING_SCHEMA,
            "sample_ids_sha256": _sha256_json(self.sample_ids),
            "sample_count": len(self.sample_ids),
            "occurrence_width": self.occurrence_width,
            "occurrence_count": len(self.sample_ids) * self.occurrence_width,
            "split_name": self.split_name,
            "seed": self.seed,
            "pool_sha256": self.pool_sha256,
            "permutation_sha256": self.permutation_sha256,
            "mapped_values_sha256": self.mapped_values_sha256,
            "labels_used": False,
            "split_local": True,
            "same_value_fixed_points": 0,
            "one_to_one_source_occurrences": True,
            "association": dict(self.association),
        }

    def row_indices(self) -> dict[str, int]:
        return {sample_id: index for index, sample_id in enumerate(self.sample_ids)}


def _association_receipt(
    targets: np.ndarray,
    sources: np.ndarray,
    *,
    target_rows: np.ndarray,
    source_rows: np.ndarray,
    split_name: str,
) -> dict[str, Any]:
    """Measure whether the sealed mapping behaves like occurrence noise, not a codebook."""

    if targets.shape != sources.shape or targets.ndim != 1:
        raise ValueError(
            "association vectors must be equally sized one-dimensional arrays"
        )
    joint = np.bincount(
        targets.astype(np.int64) * BYTE_COUNT + sources.astype(np.int64),
        minlength=BYTE_COUNT * BYTE_COUNT,
    ).reshape(BYTE_COUNT, BYTE_COUNT)
    target_counts = joint.sum(axis=1)
    source_counts = joint.sum(axis=0)
    eligible = np.flatnonzero(target_counts > 0)
    diversity = (
        np.count_nonzero(joint[eligible], axis=1) if eligible.size else np.asarray([])
    )
    maximum_share = (
        np.max(joint[eligible], axis=1) / target_counts[eligible]
        if eligible.size
        else np.asarray([])
    )
    normalized_entropy: list[float] = []
    for value in eligible:
        probabilities = (
            joint[value, joint[value] > 0].astype(np.float64) / target_counts[value]
        )
        entropy = float(-(probabilities * np.log(probabilities)).sum())
        ceiling = math.log(min(BYTE_COUNT, int(target_counts[value])))
        normalized_entropy.append(entropy / ceiling if ceiling else 1.0)

    total = float(targets.size)
    pxy = joint.astype(np.float64) / total
    px = target_counts.astype(np.float64) / total
    py = source_counts.astype(np.float64) / total
    active_i, active_j = np.nonzero(joint)
    mutual_information = float(
        sum(
            pxy[i, j] * math.log(pxy[i, j] / (px[i] * py[j]))
            for i, j in zip(active_i, active_j, strict=True)
        )
    )
    target_entropy = float(-(px[px > 0] * np.log(px[px > 0])).sum())
    source_entropy = float(-(py[py > 0] * np.log(py[py > 0])).sum())
    normalizer = math.sqrt(target_entropy * source_entropy)
    normalized_mutual_information = (
        mutual_information / normalizer if normalizer else 0.0
    )

    gate_evaluated = targets.size >= 100_000 and split_name in {"train", "holdout"}
    median_diversity = float(np.median(diversity)) if diversity.size else 0.0
    minimum_diversity = float(np.min(diversity)) if diversity.size else 0.0
    median_maximum_share = (
        float(np.median(maximum_share)) if maximum_share.size else 1.0
    )
    maximum_conditional_share = (
        float(np.max(maximum_share)) if maximum_share.size else 1.0
    )
    median_normalized_entropy = (
        float(np.median(normalized_entropy)) if normalized_entropy else 0.0
    )
    same_sample_share = float(np.mean(target_rows == source_rows))
    diversity_minimum = 48 if split_name == "train" else 24
    diversity_median = 80 if split_name == "train" else 48
    clears_gate = not gate_evaluated or (
        minimum_diversity >= diversity_minimum
        and median_diversity >= diversity_median
        and maximum_conditional_share <= 0.72
        and normalized_mutual_information <= 0.115
        and same_sample_share <= 0.001
    )
    receipt = {
        "eligible_target_values": int(eligible.size),
        "minimum_target_count_for_statistics": 1,
        "minimum_target_to_source_diversity": minimum_diversity,
        "median_target_to_source_diversity": median_diversity,
        "median_maximum_conditional_share": median_maximum_share,
        "maximum_conditional_share": maximum_conditional_share,
        "median_normalized_conditional_entropy": median_normalized_entropy,
        "normalized_mutual_information": normalized_mutual_information,
        "same_sample_source_share": same_sample_share,
        "gate_minimum_occurrences": 100_000,
        "gate_thresholds": {
            "minimum_diversity": diversity_minimum,
            "median_diversity": diversity_median,
            "maximum_conditional_share": 0.72,
            "maximum_normalized_mutual_information": 0.115,
            "maximum_same_sample_source_share": 0.001,
        },
        "gate_evaluated": gate_evaluated,
        "clears_randomized_association_gate": clears_gate,
        "joint_histogram_sha256": hashlib.sha256(
            joint.astype("<i8", copy=False).tobytes()
        ).hexdigest(),
    }
    if not clears_gate:
        raise RuntimeError(
            f"occurrence mapping retained a learnable byte codebook: {receipt}"
        )
    return receipt


def build_occurrence_derangement(
    rows: Sequence[ActionTextRow], *, seed: int, split_name: str
) -> SealedOccurrenceDerangement:
    """Seed-shuffle and repair one split-local pool while preserving its histogram."""

    if not rows:
        raise ValueError("occurrence derangement requires at least one row")
    if not split_name or any(character.isspace() for character in split_name):
        raise ValueError("occurrence split name must be one nonempty token")
    sample_ids = tuple(row.sample.sample_id for row in rows)
    if len(set(sample_ids)) != len(sample_ids):
        raise ValueError("occurrence derangement requires unique sample IDs")
    payloads = [decode_byte_token_text(row.prompt[3:-3]) for row in rows]
    widths = {len(payload) for payload in payloads}
    if len(widths) != 1:
        raise ValueError("occurrence derangement requires one fixed byte width")
    width = widths.pop()
    occurrences = [
        (value, sample_ids[row_index], offset, row_index)
        for row_index, payload in enumerate(payloads)
        for offset, value in enumerate(payload)
    ]
    target_values = np.fromiter((item[0] for item in occurrences), dtype=np.uint8)
    counts = np.bincount(target_values.astype(np.int64), minlength=BYTE_COUNT)
    if int(counts.max()) * 2 > len(occurrences):
        raise ValueError("dataset occurrence pool cannot form a byte-value derangement")

    rng = np.random.default_rng(seed)
    source_order = rng.permutation(len(occurrences))
    mapped_flat = target_values[source_order]
    conflicts = np.flatnonzero(mapped_flat == target_values)
    for target_index in conflicts:
        if mapped_flat[target_index] != target_values[target_index]:
            continue
        repaired = False
        for _ in range(10_000):
            candidate = int(rng.integers(0, len(occurrences)))
            if candidate == target_index:
                continue
            if (
                mapped_flat[candidate] != target_values[target_index]
                and mapped_flat[target_index] != target_values[candidate]
            ):
                source_order[target_index], source_order[candidate] = (
                    source_order[candidate],
                    source_order[target_index],
                )
                mapped_flat[target_index], mapped_flat[candidate] = (
                    mapped_flat[candidate],
                    mapped_flat[target_index],
                )
                repaired = True
                break
        if not repaired:
            for candidate in rng.permutation(len(occurrences)):
                if candidate == target_index:
                    continue
                if (
                    mapped_flat[candidate] != target_values[target_index]
                    and mapped_flat[target_index] != target_values[candidate]
                ):
                    source_order[target_index], source_order[candidate] = (
                        source_order[candidate],
                        source_order[target_index],
                    )
                    mapped_flat[target_index], mapped_flat[candidate] = (
                        mapped_flat[candidate],
                        mapped_flat[target_index],
                    )
                    repaired = True
                    break
        if not repaired:
            raise RuntimeError(
                "seeded occurrence shuffle could not repair a fixed byte value"
            )

    if np.any(mapped_flat == target_values):
        raise RuntimeError(
            "seeded occurrence shuffle retained a byte-value fixed point"
        )
    if np.unique(source_order).size != len(occurrences):
        raise RuntimeError("seeded occurrence shuffle reused a source occurrence")
    if not np.array_equal(
        np.bincount(mapped_flat.astype(np.int64), minlength=BYTE_COUNT), counts
    ):
        raise RuntimeError("seeded occurrence shuffle changed the split byte histogram")

    mapped = torch.empty((len(rows), width), dtype=torch.uint8)
    permutation_hash = hashlib.sha256()
    pool_hash = hashlib.sha256()
    for target_index, source_index in enumerate(source_order):
        target_value, target_id, target_offset, target_row = occurrences[target_index]
        source_value, source_id, source_offset, source_row = occurrences[source_index]
        if target_value == source_value:
            raise RuntimeError(
                "dataset occurrence derangement retained a byte-feature fixed point"
            )
        mapped[target_row, target_offset] = source_value
        pool_hash.update(_canonical_json([target_id, target_offset, target_value]))
        pool_hash.update(b"\n")
        permutation_hash.update(
            _canonical_json(
                [
                    target_id,
                    target_offset,
                    source_id,
                    source_offset,
                    source_row,
                    source_value,
                ]
            )
        )
        permutation_hash.update(b"\n")
    target_rows = np.fromiter((item[3] for item in occurrences), dtype=np.int64)
    source_rows = np.fromiter(
        (occurrences[int(source_index)][3] for source_index in source_order),
        dtype=np.int64,
    )
    association = _association_receipt(
        target_values,
        mapped_flat,
        target_rows=target_rows,
        source_rows=source_rows,
        split_name=split_name,
    )
    metadata = {
        "schema": BINDING_SCHEMA,
        "sample_ids_sha256": _sha256_json(sample_ids),
        "sample_count": len(sample_ids),
        "occurrence_width": width,
        "occurrence_count": len(occurrences),
        "split_name": split_name,
        "seed": seed,
        "pool_sha256": pool_hash.hexdigest(),
        "permutation_sha256": permutation_hash.hexdigest(),
        "mapped_values_sha256": tensor_sha256(mapped),
        "labels_used": False,
        "split_local": True,
        "same_value_fixed_points": 0,
        "one_to_one_source_occurrences": True,
        "association": association,
    }
    return SealedOccurrenceDerangement(
        sample_ids=sample_ids,
        mapped_values=mapped,
        occurrence_width=width,
        split_name=split_name,
        seed=seed,
        pool_sha256=metadata["pool_sha256"],
        permutation_sha256=metadata["permutation_sha256"],
        mapped_values_sha256=metadata["mapped_values_sha256"],
        association=association,
        seal_sha256=_sha256_json(metadata),
    )


class ActionGatedPrimeScissorInput(FrozenActionModel):
    """Action-only matched feature projection placed before the frozen GRU."""

    def __init__(
        self, vocab: Sequence[str], *, arm: str, tables: FeatureTables
    ) -> None:
        if arm not in ARMS:
            raise ValueError(f"unknown prime-scissor arm: {arm}")
        super().__init__(len(vocab))
        stoi = {token: index for index, token in enumerate(vocab)}
        byte_ids = []
        for value in range(BYTE_COUNT):
            token = chr(BYTE_TOKEN_BASE + value)
            if token not in stoi:
                raise ValueError(f"vocabulary is missing byte token {value}")
            byte_ids.append(stoi[token])
        ids = torch.tensor(byte_ids, dtype=torch.long)
        lookup = torch.full((len(vocab),), -1, dtype=torch.long)
        lookup[ids] = torch.arange(BYTE_COUNT, dtype=torch.long)
        self.register_buffer("byte_token_ids", ids, persistent=False)
        self.register_buffer("byte_lookup", lookup, persistent=False)
        self.register_buffer(
            "feature_table", tables.table_for_arm(arm).clone(), persistent=False
        )
        self.feature_projection = nn.Linear(FEATURE_WIDTH, EMBEDDING_WIDTH, bias=False)
        nn.init.zeros_(self.feature_projection.weight)
        self.arm = arm
        self.feature_receipt = dict(tables.receipt)
        self._parent_loaded = False

    def load_parent_state(self, state: Mapping[str, Tensor]) -> None:
        result = self.load_state_dict(state, strict=False)
        if result.unexpected_keys or result.missing_keys != [
            "feature_projection.weight"
        ]:
            raise RuntimeError(
                "parent state does not match the prime-scissor input architecture: "
                f"missing={result.missing_keys}, unexpected={result.unexpected_keys}"
            )
        nn.init.zeros_(self.feature_projection.weight)
        self._parent_loaded = True

    def _bound_feature_ids(
        self,
        inputs: Tensor,
        *,
        feature_owner_mask: Tensor,
        sample_ids: Sequence[str] | None,
        binding: SealedOccurrenceDerangement | None,
    ) -> Tensor:
        if (
            feature_owner_mask.dtype != torch.bool
            or feature_owner_mask.shape != inputs.shape
        ):
            raise ValueError(
                "feature owner mask must be boolean with the exact input shape"
            )
        byte_values = self.byte_lookup[inputs]
        if bool(torch.any(feature_owner_mask & (byte_values < 0))):
            raise ValueError("feature owner mask selected a non-byte token")
        owned_values = torch.where(
            feature_owner_mask, byte_values, torch.full_like(byte_values, -1)
        )
        if self.arm != "shuffled_binding_matched":
            if binding is not None or sample_ids is not None:
                raise ValueError("binding metadata is valid only for the shuffled arm")
            return owned_values
        if not bool(feature_owner_mask.any()):
            if binding is not None or sample_ids is not None:
                raise ValueError(
                    "unowned continuation cannot consume shuffled binding metadata"
                )
            return owned_values
        if binding is None or sample_ids is None or len(sample_ids) != inputs.shape[0]:
            raise ValueError(
                "shuffled byte inputs require their sealed occurrence binding and sample IDs"
            )
        row_lookup = binding.row_indices()
        result = owned_values.clone()
        for batch_index, sample_id in enumerate(sample_ids):
            if sample_id not in row_lookup:
                raise ValueError(
                    f"sample is absent from the sealed occurrence pool: {sample_id}"
                )
            positions = torch.nonzero(
                feature_owner_mask[batch_index], as_tuple=False
            ).flatten()
            if positions.numel() != binding.occurrence_width:
                raise ValueError(
                    "owned byte occurrence count differs from the sealed binding"
                )
            mapped = binding.mapped_values[row_lookup[sample_id]].to(
                inputs.device, torch.long
            )
            result[batch_index, positions] = mapped
        active = feature_owner_mask
        if bool(torch.any(result[active] == byte_values[active])):
            raise RuntimeError(
                "shuffled feature binding retained a same-byte fixed point"
            )
        return result

    def _embed(
        self,
        inputs: Tensor,
        head: str,
        *,
        feature_owner_mask: Tensor | None = None,
        sample_ids: Sequence[str] | None = None,
        binding: SealedOccurrenceDerangement | None = None,
    ) -> Tensor:
        embedded = self.e(inputs)
        if head != "action":
            if (
                sample_ids is not None
                or binding is not None
                or feature_owner_mask is not None
            ):
                raise ValueError(
                    "counting inference cannot consume action feature bindings"
                )
            return embedded
        if not self._parent_loaded:
            raise RuntimeError("load_parent_state must run before action inference")
        if feature_owner_mask is None:
            raise ValueError(
                "action inference requires an explicit caller-owned feature mask"
            )
        feature_ids = self._bound_feature_ids(
            inputs,
            feature_owner_mask=feature_owner_mask,
            sample_ids=sample_ids,
            binding=binding,
        )
        active = feature_ids >= 0
        features = self.feature_table[feature_ids.clamp(min=0)]
        projected = self.feature_projection(features)
        return embedded + torch.where(
            active.unsqueeze(-1), projected, torch.zeros_like(projected)
        )

    def forward(
        self,
        inputs: Tensor,
        head: str,
        state: Any = None,
        *,
        feature_owner_mask: Tensor | None = None,
        sample_ids: Sequence[str] | None = None,
        binding: SealedOccurrenceDerangement | None = None,
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        embedded = self._embed(
            inputs,
            head,
            feature_owner_mask=feature_owner_mask,
            sample_ids=sample_ids,
            binding=binding,
        )
        hidden, core_state = self.g(embedded, core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = (
            torch.ones_like(hidden) if self.active_path == "adapter_null" else hidden
        )
        return self.adapter_head(self.adapter(carrier)), (core_state, None)

    def parameters_for(self, stage: str) -> list[nn.Parameter]:
        if stage in ARMS:
            modules: tuple[nn.Module, ...] = (
                self.adapter,
                self.adapter_head,
                self.feature_projection,
            )
            return [
                parameter for module in modules for parameter in module.parameters()
            ]
        return super().parameters_for(stage)

    def input_receipt(self) -> dict[str, Any]:
        return {
            "schema": f"{SCHEMA}.model-input",
            "arm": self.arm,
            "table_kind": TABLE_ARM[self.arm],
            "table_sha256": tensor_sha256(self.feature_table),
            "placement": "owned-byte embedding plus fixed feature projection before frozen GRU",
            "action_only": True,
            "ownership": "explicit caller-owned boolean mask; generated continuations are false",
            "count_path_uses_parent_embedding_only": True,
            "feature_width": FEATURE_WIDTH,
            "embedding_width": EMBEDDING_WIDTH,
            "projection_parameters": self.feature_projection.weight.numel(),
            "projection_nonzero": int(
                torch.count_nonzero(self.feature_projection.weight.detach()).item()
            ),
        }


__all__ = [
    "ANCHOR_POLICIES",
    "ARMS",
    "ActionGatedPrimeScissorInput",
    "BYTE_COUNT",
    "FEATURE_WIDTH",
    "FeatureTables",
    "SCHEMA",
    "SealedOccurrenceDerangement",
    "build_feature_tables",
    "build_occurrence_derangement",
    "tensor_sha256",
]
