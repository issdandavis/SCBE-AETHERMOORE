"""Auditable mechanics for Condensed Boundary Density (CBD).

This module is a bounded research prototype. It treats cells of every dimension
as nodes in a barycentric incidence network, supports complex-valued transport,
coarsens coherent cell groups into meta-nodes, and emits exact additive traces
for its linear transport core. It does not claim a neural-network improvement.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

TOLERANCE = 1e-10


def _finite(value: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


@dataclass(frozen=True)
class BoundaryCell:
    """One typed boundary cell lifted into the common incidence network."""

    cell_id: str
    dimension: int
    layer: str
    seed_id: str
    mass: float = 1.0
    amplitude: float = 1.0
    phase: float = 0.0
    frequency: float = 0.0
    trits: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.cell_id or not self.layer or not self.seed_id:
            raise ValueError("cell_id, layer, and seed_id are required")
        if type(self.dimension) is not int or self.dimension < 0:
            raise ValueError("dimension must be a nonnegative integer")
        if not _finite(self.mass) or self.mass <= 0:
            raise ValueError("mass must be finite and positive")
        if not _finite(self.amplitude) or self.amplitude < 0:
            raise ValueError("amplitude must be finite and nonnegative")
        if not _finite(self.phase) or not _finite(self.frequency):
            raise ValueError("phase and frequency must be finite")
        if any(
            type(value) is not int or value not in (-1, 0, 1) for value in self.trits
        ):
            raise ValueError("trits must contain only -1, 0, or +1")

    @property
    def state(self) -> complex:
        return self.amplitude * np.exp(1j * self.phase)


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


@dataclass(frozen=True)
class RepeatedCellContract:
    """Auditable interface for one leaf cell or recursively condensed meta-cell.

    A hardware-like neural fabric needs a repeated interface before it needs a
    chip analogy. Every contract uses the same base update-rule digest and tensor
    widths. A sector may add a separately identified residual. Meta-cells retain
    their child identities instead of erasing the fine-grained provenance.
    """

    cell_id: str
    address: tuple[int, ...]
    sector_id: str
    base_rule_sha256: str
    state_width: int
    message_width: int
    generation: int = 0
    child_ids: tuple[str, ...] = ()
    residual_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.cell_id or not self.address or not self.sector_id:
            raise ValueError("cell ID, address, and sector are required")
        if any(type(value) is not int or value < 0 for value in self.address):
            raise ValueError("addresses must contain nonnegative integers")
        if not _is_sha256(self.base_rule_sha256):
            raise ValueError("base rule must have a lowercase SHA256 digest")
        if self.residual_sha256 is not None and not _is_sha256(self.residual_sha256):
            raise ValueError("sector residual must have a lowercase SHA256 digest")
        if type(self.state_width) is not int or self.state_width < 1:
            raise ValueError("state width must be a positive integer")
        if type(self.message_width) is not int or self.message_width < 1:
            raise ValueError("message width must be a positive integer")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("generation must be a nonnegative integer")
        if self.generation == 0 and self.child_ids:
            raise ValueError("leaf cells cannot claim children")
        if self.generation > 0 and len(self.child_ids) < 2:
            raise ValueError("a meta-cell must condense at least two child cells")
        if len(set(self.child_ids)) != len(self.child_ids):
            raise ValueError("meta-cell child IDs must be unique")


def validate_repeated_fabric(
    contracts: Sequence[RepeatedCellContract],
) -> dict[str, object]:
    """Verify a shared-rule recursive cell fabric and return its canonical hash.

    This validates an architecture manifest. It does not show that the cells
    learn, self-reproduce, or execute faster than an ordinary neural layer.
    """

    if not contracts:
        raise ValueError("a repeated fabric needs at least one cell")
    by_id = {contract.cell_id: contract for contract in contracts}
    if len(by_id) != len(contracts):
        raise ValueError("fabric cell IDs must be unique")
    addresses = {(contract.generation, contract.address) for contract in contracts}
    if len(addresses) != len(contracts):
        raise ValueError("fabric addresses must be unique within each generation")
    interfaces = {
        (
            contract.base_rule_sha256,
            contract.state_width,
            contract.message_width,
        )
        for contract in contracts
    }
    if len(interfaces) != 1:
        raise ValueError("fabric cells drifted from the shared base rule/interface")
    parent_of: dict[str, str] = {}
    for contract in contracts:
        for child_id in contract.child_ids:
            if child_id not in by_id:
                raise ValueError("meta-cell refers to an unknown child")
            child = by_id[child_id]
            if child.generation >= contract.generation:
                raise ValueError("meta-cell children must come from lower generations")
            if child_id in parent_of:
                raise ValueError("a child cannot belong to two condensed parents")
            parent_of[child_id] = contract.cell_id
    rows = [
        {
            "address": list(contract.address),
            "base_rule_sha256": contract.base_rule_sha256,
            "cell_id": contract.cell_id,
            "child_ids": list(contract.child_ids),
            "generation": contract.generation,
            "message_width": contract.message_width,
            "residual_sha256": contract.residual_sha256,
            "sector_id": contract.sector_id,
            "state_width": contract.state_width,
        }
        for contract in sorted(contracts, key=lambda value: value.cell_id)
    ]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    base_rule, state_width, message_width = next(iter(interfaces))
    return {
        "cell_count": len(contracts),
        "leaf_count": sum(contract.generation == 0 for contract in contracts),
        "meta_cell_count": sum(contract.generation > 0 for contract in contracts),
        "max_generation": max(contract.generation for contract in contracts),
        "sector_count": len({contract.sector_id for contract in contracts}),
        "residual_variant_count": len(
            {
                contract.residual_sha256
                for contract in contracts
                if contract.residual_sha256 is not None
            }
        ),
        "base_rule_sha256": base_rule,
        "state_width": state_width,
        "message_width": message_width,
        "manifest_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "canonical_manifest": rows,
    }


@dataclass(frozen=True)
class TransportLink:
    """Typed transport from source to target.

    ``phase`` is the connection angle. Sibling links are valid only when their
    endpoints carry the same stable concept seed.
    """

    source: str
    target: str
    weight: float = 1.0
    phase: float = 0.0
    kind: str = "boundary"

    def __post_init__(self) -> None:
        if not self.source or not self.target or self.source == self.target:
            raise ValueError("a link needs two different endpoint IDs")
        if not _finite(self.weight) or self.weight <= 0:
            raise ValueError("link weight must be finite and positive")
        if not _finite(self.phase) or not self.kind:
            raise ValueError("link phase must be finite and kind must be present")

    @property
    def transport(self) -> complex:
        return np.exp(1j * self.phase)


def index_cells(cells: Sequence[BoundaryCell]) -> dict[str, int]:
    index = {cell.cell_id: position for position, cell in enumerate(cells)}
    if len(index) != len(cells):
        raise ValueError("cell IDs must be unique")
    return index


def validate_boundary_chain(
    boundaries: Mapping[int, np.ndarray], tolerance: float = TOLERANCE
) -> None:
    """Validate B_k B_(k+1) = 0 for boundary maps B_k: C_k -> C_(k-1)."""

    for dimension, matrix in boundaries.items():
        if type(dimension) is not int or dimension < 1:
            raise ValueError("boundary keys must be positive dimensions")
        value = np.asarray(matrix, dtype=float)
        if value.ndim != 2 or not np.isfinite(value).all():
            raise ValueError("boundary maps must be finite matrices")
    for dimension in sorted(boundaries):
        above = boundaries.get(dimension + 1)
        if above is None:
            continue
        lower = np.asarray(boundaries[dimension], dtype=float)
        upper = np.asarray(above, dtype=float)
        if lower.shape[1] != upper.shape[0]:
            raise ValueError("adjacent boundary maps have incompatible shapes")
        if np.max(np.abs(lower @ upper), initial=0.0) > tolerance:
            raise ValueError("boundary of a boundary is nonzero")


def hodge_laplacian(boundaries: Mapping[int, np.ndarray], dimension: int) -> np.ndarray:
    """Return L_k = B_k* B_k + B_(k+1) B_(k+1)* on k-cells."""

    validate_boundary_chain(boundaries)
    if type(dimension) is not int or dimension < 0:
        raise ValueError("dimension must be nonnegative")
    if dimension == 0:
        above = boundaries.get(1)
        count = 0 if above is None else np.asarray(above).shape[0]
    else:
        current = boundaries.get(dimension)
        above = boundaries.get(dimension + 1)
        count = (
            np.asarray(current).shape[1]
            if current is not None
            else (0 if above is None else np.asarray(above).shape[0])
        )
    laplacian = np.zeros((count, count), dtype=float)
    current = boundaries.get(dimension)
    if current is not None:
        matrix = np.asarray(current, dtype=float)
        laplacian += matrix.T @ matrix
    above = boundaries.get(dimension + 1)
    if above is not None:
        matrix = np.asarray(above, dtype=float)
        laplacian += matrix @ matrix.T
    return laplacian


def barycentric_links(
    boundaries: Mapping[int, np.ndarray],
    ids_by_dimension: Mapping[int, Sequence[str]],
) -> list[TransportLink]:
    """Lift every nonzero boundary incidence into a cell-to-cell connection.

    Negative incidence orientation is carried as a pi phase rather than being
    discarded. This is the precise cell-as-node conversion used by CBD.
    """

    validate_boundary_chain(boundaries)
    links: list[TransportLink] = []
    for dimension, raw in sorted(boundaries.items()):
        matrix = np.asarray(raw, dtype=float)
        lower = ids_by_dimension.get(dimension - 1, ())
        upper = ids_by_dimension.get(dimension, ())
        if len(lower) != matrix.shape[0] or len(upper) != matrix.shape[1]:
            raise ValueError("cell IDs do not match boundary-map shapes")
        for row, column in zip(*np.nonzero(matrix), strict=True):
            coefficient = float(matrix[row, column])
            links.append(
                TransportLink(
                    source=lower[row],
                    target=upper[column],
                    weight=abs(coefficient),
                    phase=0.0 if coefficient > 0 else math.pi,
                    kind="boundary",
                )
            )
    return links


def connection_laplacian(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    *,
    enforce_seed_binding: bool = True,
) -> np.ndarray:
    """Hermitian connection Laplacian with energy sum w|z_j - T_ij z_i|^2."""

    index = index_cells(cells)
    laplacian = np.zeros((len(cells), len(cells)), dtype=complex)
    by_id = {cell.cell_id: cell for cell in cells}
    for link in links:
        if link.source not in index or link.target not in index:
            raise ValueError("link endpoint is absent from the cell set")
        if (
            enforce_seed_binding
            and link.kind == "sibling"
            and by_id[link.source].seed_id != by_id[link.target].seed_id
        ):
            raise ValueError("sibling link crossed stable concept seeds")
        source, target = index[link.source], index[link.target]
        transport = link.transport
        laplacian[source, source] += link.weight
        laplacian[target, target] += link.weight
        laplacian[source, target] -= link.weight * np.conj(transport)
        laplacian[target, source] -= link.weight * transport
    if not np.allclose(laplacian, laplacian.conj().T, atol=TOLERANCE):
        raise AssertionError("connection Laplacian lost Hermitian symmetry")
    return laplacian


def sheaf_consistency(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    members: Iterable[str] | None = None,
) -> dict[str, float | int]:
    """Measure cross-layer sibling agreement and explicit binding violations."""

    by_id = {cell.cell_id: cell for cell in cells}
    allowed = set(by_id) if members is None else set(members)
    numerator = 0.0
    denominator = 0.0
    violations = 0
    count = 0
    for link in links:
        if (
            link.kind != "sibling"
            or link.source not in allowed
            or link.target not in allowed
        ):
            continue
        left, right = by_id[link.source], by_id[link.target]
        count += 1
        scale = link.weight * (abs(left.state) ** 2 + abs(right.state) ** 2)
        denominator += scale
        numerator += link.weight * abs(right.state - link.transport * left.state) ** 2
        if left.seed_id != right.seed_id:
            violations += 1
            numerator += scale
    residual = numerator / denominator if denominator else 0.0
    valid_fraction = 1.0 - violations / count if count else 1.0
    return {
        "sibling_links": count,
        "binding_violations": violations,
        "residual": float(residual),
        "consistency": float(math.exp(-residual) * valid_fraction),
    }


def cluster_metrics(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    members: Iterable[str],
) -> dict[str, float | int]:
    """Return auditable mass, coherence, boundary, and condensation diagnostics.

    The condensation index is a preregisterable diagnostic, not a theorem:

        coherence * boundary_retention * poly_nodal_factor * sheaf_consistency

    The poly-nodal factor is zero for a singleton, preventing one large node
    from being mislabeled as an emergent cluster.
    """

    member_ids = set(members)
    by_id = {cell.cell_id: cell for cell in cells}
    if not member_ids or not member_ids.issubset(by_id):
        raise ValueError("cluster members must be a nonempty subset of cells")
    chosen = [cell for cell in cells if cell.cell_id in member_ids]
    masses = np.asarray([cell.mass for cell in chosen], dtype=float)
    total_mass = float(masses.sum())
    effective_nodes = float(total_mass**2 / np.square(masses).sum())
    weighted_states = np.asarray(
        [cell.mass * cell.state for cell in chosen], dtype=complex
    )
    coherence_denominator = sum(cell.mass * abs(cell.state) for cell in chosen)
    coherence = (
        abs(weighted_states.sum()) / coherence_denominator
        if coherence_denominator
        else 0.0
    )
    internal_weight = 0.0
    cut_weight = 0.0
    for link in links:
        source_inside = link.source in member_ids
        target_inside = link.target in member_ids
        if source_inside and target_inside:
            internal_weight += link.weight
        elif source_inside != target_inside:
            cut_weight += link.weight
    boundary_retention = (
        internal_weight / (internal_weight + cut_weight)
        if internal_weight + cut_weight
        else 0.0
    )
    poly_nodal_factor = max(0.0, 1.0 - 1.0 / effective_nodes)
    consistency = sheaf_consistency(cells, links, member_ids)
    condensed = (
        coherence
        * boundary_retention
        * poly_nodal_factor
        * float(consistency["consistency"])
    )
    return {
        "members": len(chosen),
        "dimensions": len({cell.dimension for cell in chosen}),
        "layers": len({cell.layer for cell in chosen}),
        "total_mass": total_mass,
        "effective_nodes": effective_nodes,
        "coherence": float(coherence),
        "internal_weight": float(internal_weight),
        "cut_weight": float(cut_weight),
        "boundary_retention": float(boundary_retention),
        "poly_nodal_factor": float(poly_nodal_factor),
        "sheaf_residual": float(consistency["residual"]),
        "binding_violations": int(consistency["binding_violations"]),
        "condensation_index": float(condensed),
    }


def normal_modes(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    *,
    enforce_seed_binding: bool = True,
) -> dict[str, np.ndarray]:
    """Solve L u = omega^2 M u for the cluster's mass-weighted modes."""

    laplacian = connection_laplacian(
        cells, links, enforce_seed_binding=enforce_seed_binding
    )
    masses = np.asarray([cell.mass for cell in cells], dtype=float)
    inverse_root = np.diag(1.0 / np.sqrt(masses))
    normalized = inverse_root @ laplacian @ inverse_root
    eigenvalues, eigenvectors = np.linalg.eigh(normalized)
    if eigenvalues.min(initial=0.0) < -1e-8:
        raise ValueError("connection energy is not positive semidefinite")
    eigenvalues = np.maximum(eigenvalues.real, 0.0)
    modes = inverse_root @ eigenvectors
    return {
        "eigenvalues": eigenvalues,
        "frequencies": np.sqrt(eigenvalues),
        "modes": modes,
    }


def coarsen_partition(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    clusters: Sequence[Sequence[str]],
    *,
    enforce_seed_binding: bool = True,
) -> dict[str, np.ndarray]:
    """Galerkin coarsening: poly-nodal clumps become mass-bearing meta-nodes."""

    index = index_cells(cells)
    seen: set[str] = set()
    lift = np.zeros((len(cells), len(clusters)), dtype=complex)
    for cluster_index, cluster in enumerate(clusters):
        if not cluster:
            raise ValueError("clusters cannot be empty")
        for cell_id in cluster:
            if cell_id not in index or cell_id in seen:
                raise ValueError("clusters must partition known cells exactly once")
            seen.add(cell_id)
            lift[index[cell_id], cluster_index] = 1.0
    if seen != set(index):
        raise ValueError("clusters must cover every cell")
    fine_laplacian = connection_laplacian(
        cells, links, enforce_seed_binding=enforce_seed_binding
    )
    fine_mass = np.diag([cell.mass for cell in cells]).astype(complex)
    coarse_laplacian = lift.conj().T @ fine_laplacian @ lift
    coarse_mass = lift.conj().T @ fine_mass @ lift
    return {
        "lift": lift,
        "fine_laplacian": fine_laplacian,
        "fine_mass": fine_mass,
        "coarse_laplacian": coarse_laplacian,
        "coarse_mass": coarse_mass,
    }


def coarsen_operator_hierarchy(
    fine_laplacian: np.ndarray,
    fine_mass: np.ndarray,
    lifts: Sequence[np.ndarray],
) -> dict[str, object]:
    """Compose cell-to-cluster lifts while preserving the exact quadratic energy.

    Each binary lift maps a coarser state to exactly one parent for every node at
    the preceding level. Repeating the operation makes cell -> cluster ->
    meta-cell recursion concrete without pretending that the coarse state is an
    independent observation.
    """

    laplacian = np.asarray(fine_laplacian, dtype=complex)
    mass = np.asarray(fine_mass, dtype=complex)
    if (
        laplacian.ndim != 2
        or laplacian.shape[0] != laplacian.shape[1]
        or mass.shape != laplacian.shape
    ):
        raise ValueError("fine Laplacian and mass must be equally sized squares")
    if not np.isfinite(laplacian).all() or not np.isfinite(mass).all():
        raise ValueError("fine operators must be finite")
    if not np.allclose(laplacian, laplacian.conj().T, atol=TOLERANCE):
        raise ValueError("fine Laplacian must be Hermitian")
    if not np.allclose(mass, mass.conj().T, atol=TOLERANCE):
        raise ValueError("fine mass must be Hermitian")
    if float(np.linalg.eigvalsh(mass).min()) <= 0:
        raise ValueError("fine mass must be positive definite")
    if not lifts:
        raise ValueError("at least one hierarchy lift is required")
    total_lift = np.eye(laplacian.shape[0], dtype=complex)
    levels: list[dict[str, np.ndarray]] = []
    for raw_lift in lifts:
        lift = np.asarray(raw_lift, dtype=complex)
        if lift.ndim != 2 or lift.shape[0] != laplacian.shape[0]:
            raise ValueError("hierarchy lift shape does not match its input level")
        if not np.isfinite(lift).all() or not np.all(
            np.isclose(lift, 0.0) | np.isclose(lift, 1.0)
        ):
            raise ValueError("hierarchy lifts must be finite binary membership maps")
        if not np.allclose(lift.sum(axis=1), 1.0) or np.any(
            np.isclose(lift.sum(axis=0), 0.0)
        ):
            raise ValueError("every node needs exactly one nonempty parent cluster")
        laplacian = lift.conj().T @ laplacian @ lift
        mass = lift.conj().T @ mass @ lift
        total_lift = total_lift @ lift
        levels.append({"lift": lift, "laplacian": laplacian, "mass": mass})
    return {
        "total_lift": total_lift,
        "coarse_laplacian": laplacian,
        "coarse_mass": mass,
        "levels": levels,
    }


def transition_operator(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    *,
    dt: float,
    diffusion: float,
    enforce_seed_binding: bool = True,
) -> np.ndarray:
    """One stable, exactly traceable diffusion-plus-rotation step."""

    if not _finite(dt) or dt <= 0 or not _finite(diffusion) or diffusion < 0:
        raise ValueError("dt must be positive and diffusion must be nonnegative")
    laplacian = connection_laplacian(
        cells, links, enforce_seed_binding=enforce_seed_binding
    )
    maximum = float(np.linalg.eigvalsh(laplacian).max(initial=0.0))
    if dt * diffusion * maximum > 1.0 + TOLERANCE:
        raise ValueError("explicit diffusion step is outside its stability interval")
    diffuse = np.eye(len(cells), dtype=complex) - dt * diffusion * laplacian
    rotate = np.diag([np.exp(1j * cell.frequency * dt) for cell in cells])
    return rotate @ diffuse


def step_with_trace(
    cells: Sequence[BoundaryCell],
    links: Sequence[TransportLink],
    readout: Sequence[complex],
    *,
    dt: float = 0.05,
    diffusion: float = 0.1,
    drive: Sequence[complex] | None = None,
    enforce_seed_binding: bool = True,
) -> dict[str, object]:
    """Advance once and reconstruct a real readout from exact source terms."""

    readout_vector = np.asarray(readout, dtype=complex)
    if readout_vector.shape != (len(cells),) or not np.isfinite(readout_vector).all():
        raise ValueError("readout must be one finite coefficient per cell")
    drive_vector = (
        np.zeros(len(cells), dtype=complex)
        if drive is None
        else np.asarray(drive, dtype=complex)
    )
    if drive_vector.shape != (len(cells),) or not np.isfinite(drive_vector).all():
        raise ValueError("drive must be one finite value per cell")
    states = np.asarray([cell.state for cell in cells], dtype=complex)
    operator = transition_operator(
        cells,
        links,
        dt=dt,
        diffusion=diffusion,
        enforce_seed_binding=enforce_seed_binding,
    )
    next_state = operator @ states + drive_vector
    output = float(np.real(np.vdot(readout_vector, next_state)))
    output_terms = []
    reconstructed = 0.0
    for source, cell in enumerate(cells):
        contribution = float(
            np.real(np.vdot(readout_vector, operator[:, source] * states[source]))
        )
        reconstructed += contribution
        output_terms.append(
            {
                "kind": "cell",
                "cell_id": cell.cell_id,
                "seed_id": cell.seed_id,
                "layer": cell.layer,
                "dimension": cell.dimension,
                "contribution": contribution,
            }
        )
    drive_contribution = float(np.real(np.vdot(readout_vector, drive_vector)))
    reconstructed += drive_contribution
    output_terms.append({"kind": "drive", "contribution": drive_contribution})
    state_terms = []
    for target, target_cell in enumerate(cells):
        for source, source_cell in enumerate(cells):
            coefficient = operator[target, source]
            if abs(coefficient) <= TOLERANCE:
                continue
            contribution = coefficient * states[source]
            state_terms.append(
                {
                    "source": source_cell.cell_id,
                    "target": target_cell.cell_id,
                    "coefficient_real": float(coefficient.real),
                    "coefficient_imag": float(coefficient.imag),
                    "contribution_real": float(contribution.real),
                    "contribution_imag": float(contribution.imag),
                }
            )
    residual = output - reconstructed
    if abs(residual) > 1e-9:
        raise AssertionError(
            "output contribution ledger did not reconstruct the output"
        )
    return {
        "output": output,
        "reconstructed_output": reconstructed,
        "trace_residual": residual,
        "next_state": next_state,
        "output_terms": output_terms,
        "state_terms": state_terms,
        "operator": operator,
    }


def oriented_triangle() -> tuple[dict[int, np.ndarray], dict[int, tuple[str, ...]]]:
    """A closed triangle fixture with explicit orientations."""

    boundaries = {
        1: np.asarray([[-1, 0, -1], [1, -1, 0], [0, 1, 1]], dtype=float),
        2: np.asarray([[1], [1], [-1]], dtype=float),
    }
    ids = {0: ("v0", "v1", "v2"), 1: ("e01", "e12", "e02"), 2: ("f012",)}
    validate_boundary_chain(boundaries)
    return boundaries, ids
