"""
Dual Combat System — Cl(4,0) Bivector Type Advantage (Python reference).

Mirrors src/game/combat.ts.
Type advantage computed from Clifford algebra, NOT a lookup table.

A4: Symmetry — [F_A, F_B] = -[F_B, F_A].
"""

from __future__ import annotations

import math
from typing import List

from .types import TongueCode, TongueVector, TONGUE_CODES

# ---------------------------------------------------------------------------
#  4×4 matrix helpers
# ---------------------------------------------------------------------------

Matrix4 = List[List[float]]


def _zeros4() -> Matrix4:
    return [[0.0] * 4 for _ in range(4)]


def _basis_bivector(i: int, j: int) -> Matrix4:
    m = _zeros4()
    m[i][j] = 1.0
    m[j][i] = -1.0
    return m


# 6 basis bivectors mapped to tongue codes
_BIVECTOR_BASIS: dict[TongueCode, Matrix4] = {
    "KO": _basis_bivector(0, 1),  # e₁₂
    "AV": _basis_bivector(0, 2),  # e₁₃
    "RU": _basis_bivector(0, 3),  # e₁₄
    "CA": _basis_bivector(1, 2),  # e₂₃
    "UM": _basis_bivector(1, 3),  # e₂₄
    "DR": _basis_bivector(2, 3),  # e₃₄
}


def _mat_sub(a: Matrix4, b: Matrix4) -> Matrix4:
    return [[a[i][j] - b[i][j] for j in range(4)] for i in range(4)]


def _mat_mul(a: Matrix4, b: Matrix4) -> Matrix4:
    c = _zeros4()
    for i in range(4):
        for j in range(4):
            for k in range(4):
                c[i][j] += a[i][k] * b[k][j]
    return c


def _mat_norm(m: Matrix4) -> float:
    return math.sqrt(sum(m[i][j] ** 2 for i in range(4) for j in range(4)))


def _mat_inner(a: Matrix4, b: Matrix4) -> float:
    return sum(a[i][j] * b[i][j] for i in range(4) for j in range(4))


def _commutator(a: Matrix4, b: Matrix4) -> Matrix4:
    return _mat_sub(_mat_mul(a, b), _mat_mul(b, a))


# ---------------------------------------------------------------------------
#  Tongue → Bivector
# ---------------------------------------------------------------------------


def tongue_to_bivector(v: TongueVector) -> Matrix4:
    """Convert a TongueVector to a bivector (linear combination of basis)."""
    result = _zeros4()
    for idx, code in enumerate(TONGUE_CODES):
        basis = _BIVECTOR_BASIS[code]
        for i in range(4):
            for j in range(4):
                result[i][j] += v[idx] * basis[i][j]
    return result


# ---------------------------------------------------------------------------
#  Type Advantage
# ---------------------------------------------------------------------------


def compute_type_advantage(a: TongueVector, b: TongueVector) -> float:
    """
    Compute type advantage via Cl(4,0) commutator.

    Δ = ⟨[F_A, F_B], F_A − F_B⟩ / (‖[F_A,F_B]‖ · ‖F_A − F_B‖)

    Returns Δ ∈ [-1, 1]. Δ > 0 → A wins.
    Antisymmetric: advantage(A,B) = -advantage(B,A).
    """
    f_a = tongue_to_bivector(a)
    f_b = tongue_to_bivector(b)

    comm = _commutator(f_a, f_b)
    diff = _mat_sub(f_a, f_b)

    comm_norm = _mat_norm(comm)
    diff_norm = _mat_norm(diff)

    if comm_norm < 1e-12 or diff_norm < 1e-12:
        return 0.0

    delta = _mat_inner(comm, diff) / (comm_norm * diff_norm)
    return max(-1.0, min(1.0, delta))


# ---------------------------------------------------------------------------
#  Damage Calculation
# ---------------------------------------------------------------------------


def calculate_damage(
    base_damage: float,
    type_advantage: float,
    proof_power: float,
    resilience: float,
) -> int:
    """
    Calculate final damage.

    Args:
        base_damage: Raw damage value.
        type_advantage: Δ from compute_type_advantage.
        proof_power: Attacker's proof power (0-100).
        resilience: Defender's resilience (0-100).

    Returns:
        Final damage (always >= 1).
    """
    type_mul = 1.0 + type_advantage * 0.5
    proof_mul = 0.8 + (proof_power / 100) * 0.7
    res_reduce = 1.0 - (resilience / 100) * 0.4
    final = base_damage * type_mul * proof_mul * res_reduce
    return max(1, round(final))
