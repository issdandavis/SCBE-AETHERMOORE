"""SCBE 9D State Engine — Chemistry via Atomic Tokenization + Fusion

Maps molecules into the 9D state vector using the existing SCBE pipeline:

  1. Tokenize molecular fragments → AtomicTokenState (periodic table)
  2. Fuse atomic states → FusionResult (trit votes, edge tension, valence pressure)
  3. Map fusion output → 6D context vector (multiview decomposition)
  4. Assemble full 9D xi = [c(t), tau(t), eta(t), q(t)]

This is deterministic, uses the Sacred Tongues trit lattice, and respects
the periodic-table valence/electronegativity model already in atomic_tokenization.py.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np

from .atomic_tokenization import (
    AtomicTokenState,
    TONGUES,
    map_token_to_atomic_state,
)
from .chemical_fusion import (
    FusionParams,
    fuse_atomic_states,
)
from .state9d_engine import (
    assemble_state_vector,
    build_context_vector,
    compute_shannon_entropy,
    evolve_quantum_state,
    evolve_time,
)


def _tokens_from_molecule(smiles: str) -> List[str]:
    """Split a SMILES into coarse tokens for atomic tokenization.

    We treat each atom symbol and key structural motif as a token.
    This is intentionally approximate — the tokenizer's semantic
    classifier handles the mapping into periodic-table elements.
    """
    # Aromatic mappings
    AROMATIC = {"c": "carbon_aromatic", "n": "nitrogen_aromatic",
                "o": "oxygen_aromatic", "s": "sulfur_aromatic",
                "p": "phosphorus_aromatic"}

    tokens = []
    i = 0
    while i < len(smiles):
        ch = smiles[i]

        # Aromatic atoms
        if ch in AROMATIC:
            tokens.append(AROMATIC[ch])
            i += 1
            continue

        # Aliphatic multi-letter symbols
        if ch.isupper() and i + 1 < len(smiles) and smiles[i + 1].islower():
            two = smiles[i : i + 2]
            if two in ("Cl", "Br", "Si", "Se", "As", "Na"):
                tokens.append(two)
                i += 2
                continue

        # Single-letter aliphatic atoms
        if ch.isupper():
            tokens.append(ch)
            i += 1
            continue

        # Structural motifs
        if ch == "=":
            tokens.append("double_bond")
        elif ch == "#":
            tokens.append("triple_bond")
        elif ch == "(":
            tokens.append("branch_open")
        elif ch == ")":
            tokens.append("branch_close")
        elif ch.isdigit():
            tokens.append(f"ring_{ch}")

        i += 1

    return [t for t in tokens if t]


def tokenize_molecule(smiles: str) -> List[AtomicTokenState]:
    """Map a SMILES string into a sequence of AtomicTokenState objects.

    Each token is classified through phi: V x L x C -> P and projected
    into the Six Sacred Tongue trit lattice.
    """
    tokens = _tokens_from_molecule(smiles)
    states = []
    for token in tokens:
        state = map_token_to_atomic_state(
            token,
            language="chemistry",
            context_class="molecular",
        )
        states.append(state)
    return states


def fuse_molecule(states: List[AtomicTokenState]) -> Dict[str, Any]:
    """Fuse atomic states into a molecular coherence descriptor.

    Uses the existing SCBE fusion algebra:
      R_k = sum_i w_i * tau_{i,k}
            + sum_(i,j) lambda * (chi_i - chi_j)
            - sum_(i,j) gamma * lambda * |chi_i - chi_j|
            + sum_i rho_i * v_i
    """
    if not states:
        return {
            "tau_hat": {t: 0 for t in TONGUES},
            "votes": {t: 0.0 for t in TONGUES},
            "signed_edge_tension": 0.0,
            "coherence_penalty": 0.0,
            "valence_pressure": 0.0,
            "elements": [],
        }

    result = fuse_atomic_states(
        states,
        params=FusionParams(),
    )

    return {
        "tau_hat": dict(result.tau_hat),
        "votes": dict(result.reconstruction_votes),
        "signed_edge_tension": result.signed_edge_tension,
        "coherence_penalty": result.coherence_penalty,
        "valence_pressure": result.valence_pressure,
        "elements": [e.symbol for e in result.elements],
    }


def fusion_to_context(
    fusion: Dict[str, Any],
    t: float,
    smiles: str,
    signature_validity: float = 1.0,
) -> np.ndarray:
    """Map fusion output into the 6D context vector.

    Multiview decomposition:
      v1 = sin(t)  — identity oscillation (universal)
      v2 = e^(i·2π·0.75)  — intent phase (constant)
      v3 = normalized trust baseline from fusion coherence
      v4 = t  — linear time
      v5 = molecular hash (commitment surrogate)
      v6 = signature validity × (1 - coherence_penalty / max_pressure)
    """
    v1 = math.sin(t)
    v2 = np.exp(1j * 2.0 * math.pi * 0.75)

    # v3: trajectory score = normalized molecular coherence
    votes = fusion["votes"]
    vote_sum = sum(abs(v) for v in votes.values())
    vote_max = max(abs(v) for v in votes.values()) if votes else 1.0
    coherence = 1.0 - (fusion["coherence_penalty"] / max(1.0, vote_max))
    v3 = float(np.clip(coherence, 0.0, 1.0))

    v4 = float(t)

    # v5: commitment hash = SHA-256 of SMILES normalized
    import hashlib
    digest = hashlib.sha256(smiles.encode("utf-8")).digest()
    v5 = int.from_bytes(digest, "big") / (2**256)

    # v6: signature validity modulated by valence pressure
    pressure = fusion["valence_pressure"]
    max_pressure = max(1.0, abs(pressure) + 1.0)
    pressure_factor = 1.0 - min(1.0, abs(pressure) / max_pressure)
    v6 = float(np.clip(signature_validity * pressure_factor, 0.0, 1.0))

    return np.array([v1, v2, v3, v4, v5, v6], dtype=object)


def assemble_fusion_state_vector(
    smiles: str,
    t: float,
    *,
    q0: complex = 1 + 0j,
    H: float = 1.0,
    signature_validity: float = 1.0,
) -> np.ndarray:
    """Assemble a 9D state vector from a molecule using SCBE fusion.

    Pipeline:
      SMILES → tokens → AtomicTokenState → fusion → 6D context → 9D xi
    """
    states = tokenize_molecule(smiles)
    fusion = fuse_molecule(states)
    c = fusion_to_context(fusion, t, smiles, signature_validity)

    eta = compute_shannon_entropy(c)
    tau = evolve_time(t)
    q = evolve_quantum_state(q0, H, t)

    xi = np.empty(9, dtype=object)
    xi[0:6] = c
    xi[6] = tau
    xi[7] = eta
    xi[8] = q
    return xi


def molecule_governance_summary(smiles: str, t: float = 0.0) -> Dict[str, Any]:
    """Full governance-ready summary of a molecule in SCBE terms."""
    states = tokenize_molecule(smiles)
    fusion = fuse_molecule(states)
    xi = assemble_fusion_state_vector(smiles, t)

    return {
        "smiles": smiles,
        "tokens": [s.token for s in states],
        "elements": fusion["elements"],
        "tau_hat": fusion["tau_hat"],
        "votes": {k: round(v, 4) for k, v in fusion["votes"].items()},
        "signed_edge_tension": round(fusion["signed_edge_tension"], 4),
        "coherence_penalty": round(fusion["coherence_penalty"], 4),
        "valence_pressure": round(fusion["valence_pressure"], 4),
        "state_vector": {
            "context": [float(xi[i]) if not isinstance(xi[i], (complex, np.complexfloating)) else {"real": xi[i].real, "imag": xi[i].imag} for i in range(6)],
            "tau": float(xi[6]),
            "eta": float(xi[7]),
            "q": {"real": complex(xi[8]).real, "imag": complex(xi[8]).imag, "norm": abs(complex(xi[8]))},
        },
    }
