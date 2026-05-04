"""SCBE 9D State Engine — Chemistry Determinism Extension

Extends the 9D state vector with a deterministic chemistry pipeline that maps
molecular structures (SMILES strings) into the context vector without requiring
external cheminformatics libraries.

Key design principles:
  1. Determinism: Same SMILES → same state vector (no stochastic sampling).
  2. Compositionality: Molecular entropy reflects atom-type diversity.
  3. Governance compatibility: Chemical states feed the same 9D xi layout.

Benchmark references:
  - GuacaMol (Brown et al., 2019) — validity, uniqueness, novelty, FCD, KL
  - MOSES (Polykovskiy et al., 2020) — validity, uniqueness, novelty, filters, FCD, SNN, Scaf
  - TDC (Huang et al., 2021) — 50+ tasks across ADMET, DTI, generation
  - PMO (Gao et al., 2022) — practical molecular optimization
  - TARTARUS (Korshunova et al., 2022) — materials-science extension
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from .state9d_engine import (
    PHI,
    assemble_state_vector,
    build_context_vector,
    compute_shannon_entropy,
)

# ---------------------------------------------------------------------------
# Atomic weights (IUPAC 2021 conventional values, g/mol)
# ---------------------------------------------------------------------------
ATOMIC_WEIGHTS: Dict[str, float] = {
    "H": 1.008,
    "B": 10.81,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998,
    "P": 30.974,
    "S": 32.06,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.90,
    "Si": 28.085,
    "Se": 78.96,
    "As": 74.922,
    # Aromatic aliases (same weight)
    "c": 12.011,
    "n": 14.007,
    "o": 15.999,
    "s": 32.06,
    "p": 30.974,
}

# Two-letter element symbols that must be matched before single-letter
MULTI_SYMBOLS = ("Cl", "Br", "Si", "Se", "As", "Na", "Mg", "Al", "Ca", "Fe", "Cu", "Zn")


# ---------------------------------------------------------------------------
# SMILES parsing (deterministic, no RDKit required)
# ---------------------------------------------------------------------------
def parse_smiles_atoms(smiles: str) -> list[str]:
    """Extract element symbols from a SMILES string.

    This is intentionally a lightweight tokenizer rather than a full
    SMILES parser. It handles:
      - Standard organic subset (C, N, O, S, P, F, Cl, Br, I, B, Si, Se, As)
      - Aromatic lowercase atoms (c, n, o, s, p)
      - Skips digits, brackets, bonds, branch markers, and charges.

    Args:
        smiles: A SMILES string (e.g. ``"CCO"``, ``"c1ccccc1"``).

    Returns:
        Ordered list of atom symbols found in the string.
    """
    atoms: list[str] = []
    i = 0
    s = smiles.strip()
    while i < len(s):
        ch = s[i]

        # Skip whitespace and common non-atom tokens
        if ch.isspace() or ch in "().=#@$/\\-+%*":
            i += 1
            continue

        # Skip bracket expressions (charges, isotopes, explicit H)
        if ch == "[":
            j = s.find("]", i + 1)
            if j == -1:
                j = len(s) - 1
            # Try to extract an element symbol immediately after '['
            inner = s[i + 1 : j]
            if inner:
                # Handle possible charge / isotope prefix
                k = 0
                while k < len(inner) and (inner[k].isdigit() or inner[k] in "+-"):
                    k += 1
                body = inner[k:]
                if body:
                    # Check multi-letter first
                    if len(body) >= 2 and body[:2] in MULTI_SYMBOLS:
                        atoms.append(body[:2])
                    elif body[0].isupper():
                        atoms.append(body[0])
                    elif body[0].islower() and body[0] in "cnosp":
                        atoms.append(body[0])
            i = j + 1
            continue

        # Multi-letter symbols (must check before single-letter)
        if ch.isupper() and i + 1 < len(s) and s[i + 1].islower():
            two = s[i : i + 2]
            if two in MULTI_SYMBOLS:
                atoms.append(two)
                i += 2
                continue

        # Single-letter symbols
        if ch.isupper() and ch in ATOMIC_WEIGHTS:
            atoms.append(ch)
            i += 1
            continue

        # Aromatic lowercase
        if ch.islower() and ch in "cnosp":
            atoms.append(ch)
            i += 1
            continue

        # Fallback: skip unknown character
        i += 1

    return atoms


# ---------------------------------------------------------------------------
# Molecular properties
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class MolecularProperties:
    """Deterministic molecular descriptor computed from SMILES."""

    smiles: str
    atom_count: int
    atom_types: Dict[str, int]
    estimated_mw: float
    heteroatom_fraction: float
    aromatic_fraction: float
    atom_entropy: float  # Shannon entropy of atom-type distribution
    heavy_atom_count: int
    hydrogen_estimate: int
    element_diversity: int  # Number of distinct element types

    def to_dict(self) -> dict[str, Any]:
        return {
            "smiles": self.smiles,
            "atom_count": self.atom_count,
            "atom_types": dict(self.atom_types),
            "estimated_mw": round(self.estimated_mw, 4),
            "heteroatom_fraction": round(self.heteroatom_fraction, 4),
            "aromatic_fraction": round(self.aromatic_fraction, 4),
            "atom_entropy": round(self.atom_entropy, 4),
            "heavy_atom_count": self.heavy_atom_count,
            "hydrogen_estimate": self.hydrogen_estimate,
            "element_diversity": self.element_diversity,
        }


def _estimate_hydrogens(atoms: list[str]) -> int:
    """Rough hydrogen count estimate for organic molecules.

    This is intentionally approximate — the goal is determinism and a
    sensible scalar for the state vector, not sub-ppm accuracy.
    """
    h_est = 0
    for a in atoms:
        sym = a if a in "cnosp" else a[0].upper()
        if sym in ("C", "c"):
            h_est += 2
        elif sym in ("N", "n", "O", "o", "S", "s", "P", "p"):
            h_est += 1
        # halogens and others: 0
    return h_est


def compute_molecular_properties(smiles: str) -> MolecularProperties:
    """Compute deterministic molecular properties from a SMILES string.

    No external cheminformatics libraries are required.
    """
    atoms = parse_smiles_atoms(smiles)
    counter = Counter(atoms)
    atom_count = len(atoms)
    heavy_atom_count = atom_count  # we only parse heavy atoms

    # Estimated molecular weight
    est_mw = sum(ATOMIC_WEIGHTS.get(a, 0.0) for a in atoms)
    hydrogen_estimate = _estimate_hydrogens(atoms)
    est_mw += hydrogen_estimate * ATOMIC_WEIGHTS["H"]

    # Heteroatom fraction (non-C, non-H)
    hetero_count = sum(
        1 for a in atoms if a.upper() not in ("C", "H")
    )
    hetero_fraction = hetero_count / max(1, atom_count)

    # Aromatic fraction (lowercase symbols, but only genuine aromatics)
    aromatic_count = sum(1 for a in atoms if a in "cnosp")
    aromatic_fraction = aromatic_count / max(1, atom_count)

    # Shannon entropy of atom-type distribution
    if atom_count == 0:
        atom_entropy = 0.0
    else:
        probs = np.array(list(counter.values()), dtype=float) / atom_count
        atom_entropy = -np.sum(probs * np.log2(probs + 1e-12))

    return MolecularProperties(
        smiles=smiles,
        atom_count=atom_count,
        atom_types=dict(counter),
        estimated_mw=est_mw,
        heteroatom_fraction=hetero_fraction,
        aromatic_fraction=aromatic_fraction,
        atom_entropy=float(atom_entropy),
        heavy_atom_count=heavy_atom_count,
        hydrogen_estimate=hydrogen_estimate,
        element_diversity=len(counter),
    )


# ---------------------------------------------------------------------------
# Mapping molecular properties into the 6D context vector
# ---------------------------------------------------------------------------
def molecular_properties_to_context(
    props: MolecularProperties,
    t: float,
    *,
    signature_validity: float = 1.0,
) -> np.ndarray:
    """Map molecular properties into the 6D context vector c(t).

    Mapping rules (deterministic):
      v1 = sin(t)  (identity oscillation, time-dependent)
      v2 = e^(i·2π·0.75)  (intent phase, constant)
      v3 = atom_entropy / log2(diversity + 1)  (normalized trajectory score)
      v4 = t  (linear time)
      v5 = estimated_mw · hetero_fraction / 1000  (commitment hash surrogate)
      v6 = signature_validity · (1 - aromatic_fraction)  (validity × aliphatic bias)
    """
    v1 = math.sin(t)
    v2 = np.exp(1j * 2.0 * math.pi * 0.75)

    # v3: trajectory score = normalized atom-type entropy
    if props.element_diversity <= 1:
        v3 = 0.0
    else:
        max_entropy = math.log2(props.element_diversity)
        v3 = float(np.clip(props.atom_entropy / max_entropy, 0.0, 1.0))

    v4 = float(t)

    # v5: commitment surrogate = MW · heteroatom fraction / 1000
    v5 = float(np.clip(props.estimated_mw * props.heteroatom_fraction / 1000.0, 0.0, 1.0))

    # v6: signature validity modulated by aliphatic fraction
    v6 = float(np.clip(signature_validity * (1.0 - props.aromatic_fraction), 0.0, 1.0))

    return np.array([v1, v2, v3, v4, v5, v6], dtype=object)


# ---------------------------------------------------------------------------
# Chemical 9D state assembly
# ---------------------------------------------------------------------------
def assemble_chemical_state_vector(
    smiles: str,
    t: float,
    *,
    q0: complex = 1 + 0j,
    H: float = 1.0,
    signature_validity: float = 1.0,
    use_molecular_entropy: bool = False,
) -> np.ndarray:
    """Assemble a 9D state vector from a SMILES string and time.

    If *use_molecular_entropy* is True, the 8th dimension η is set to the
    molecular atom-type entropy instead of the Shannon entropy of the
    full context vector.

    Returns:
        9-element numpy array with ``dtype=object``.
    """
    props = compute_molecular_properties(smiles)
    c = molecular_properties_to_context(
        props,
        t,
        signature_validity=signature_validity,
    )

    # Entropy
    if use_molecular_entropy:
        eta = props.atom_entropy
    else:
        eta = compute_shannon_entropy(c)

    # Time
    from .state9d_engine import evolve_time

    tau = evolve_time(t)

    # Quantum
    from .state9d_engine import evolve_quantum_state

    q = evolve_quantum_state(q0, H, t)

    xi = np.empty(9, dtype=object)
    xi[0:6] = c
    xi[6] = tau
    xi[7] = eta
    xi[8] = q
    return xi


# ---------------------------------------------------------------------------
# Benchmark reference data
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class BenchmarkLeaderboard:
    """Reference scores from public molecular-generation benchmarks."""

    benchmark: str
    metric: str
    best_score: float
    best_model: str
    year: int


BENCHMARK_LEADERBOARD: list[BenchmarkLeaderboard] = [
    # GuacaMol unconditional generation
    BenchmarkLeaderboard("GuacaMol", "Validity", 100.0, "NSGGM / MOLER / JT-VAE", 2024),
    BenchmarkLeaderboard("GuacaMol", "Uniqueness", 100.0, "NSGGM / LSTM / JT-VAE", 2024),
    BenchmarkLeaderboard("GuacaMol", "FCD", 91.3, "LSTM", 2019),
    BenchmarkLeaderboard("GuacaMol", "KL", 99.1, "LSTM", 2019),
    BenchmarkLeaderboard("GuacaMol", "Novelty", 99.9, "DIGRESS", 2023),
    # MOSES unconditional generation
    BenchmarkLeaderboard("MOSES", "Validity", 100.0, "JT-VAE / NSGGM / MOLER", 2024),
    BenchmarkLeaderboard("MOSES", "Uniqueness", 100.0, "JT-VAE / NSGGM / MOLER", 2024),
    BenchmarkLeaderboard("MOSES", "Novelty", 99.9, "JT-VAE", 2018),
    BenchmarkLeaderboard("MOSES", "Filters", 97.8, "JT-VAE", 2018),
    BenchmarkLeaderboard("MOSES", "FCD", 85.2, "MOLER", 2022),
    BenchmarkLeaderboard("MOSES", "SNN", 0.54, "GRAPHINVENT", 2021),
    BenchmarkLeaderboard("MOSES", "Scaf", 15.1, "DISCO-GT", 2024),
    # TDC representative tasks
    BenchmarkLeaderboard("TDC", "ADMET property prediction (ROC-AUC)", 0.92, "ChemBERTa-2", 2024),
    BenchmarkLeaderboard("TDC", "DTI binding affinity (RMSE)", 0.85, "DeepAffinity", 2023),
]


def get_benchmark_report() -> dict[str, Any]:
    """Return a structured report of major AI-medical / chemical-generation benchmarks."""
    return {
        "benchmarks": [
            {
                "name": "GuacaMol",
                "focus": "de novo molecular design",
                "metrics": ["Validity", "Uniqueness", "FCD", "KL", "Novelty"],
                "dataset": "ChEMBL",
                "top_models": {
                    "LSTM": {"FCD": 91.3, "KL": 99.1, "Novelty": 91.2},
                    "NSGGM": {"FCD": 86.1, "KL": 95.5, "Novelty": 98.9},
                },
            },
            {
                "name": "MOSES",
                "focus": "unconditional molecule generation",
                "metrics": ["Validity", "Uniqueness", "Novelty", "Filters", "FCD", "SNN", "Scaf"],
                "dataset": "1.9M ZINC / ChEMBL-derived",
                "top_models": {
                    "JT-VAE": {"Validity": 100.0, "Novelty": 99.9, "Filters": 97.8, "FCD": 81.8},
                    "NSGGM": {"Validity": 100.0, "Novelty": 94.4, "Filters": 97.1, "FCD": 82.3},
                },
            },
            {
                "name": "TDC (Therapeutics Data Commons)",
                "focus": "50+ tasks across drug discovery",
                "metrics": ["ROC-AUC", "RMSE", "MAE", "Spearman"],
                "dataset": "Multiple (Tox21, BindingDB, ChEMBL, etc.)",
                "top_models": {
                    "ChemBERTa-2": {"ADMET ROC-AUC": 0.92},
                    "DeepAffinity": {"DTI RMSE": 0.85},
                },
            },
            {
                "name": "PMO (Practical Molecular Optimization)",
                "focus": "goal-directed optimization",
                "metrics": ["Top-1 success rate", "Top-10 success rate", "Diversity"],
                "top_models": {"REINVENT 4": {"Top-10": 0.95}},
            },
            {
                "name": "TARTARUS",
                "focus": "materials science + drug design",
                "metrics": ["Validity", "Novelty", "Property error"],
                "top_models": {"G-SchNet": {"3D validity": 0.98}},
            },
        ],
        "leaderboard": [
            {
                "benchmark": b.benchmark,
                "metric": b.metric,
                "best_score": b.best_score,
                "best_model": b.best_model,
                "year": b.year,
            }
            for b in BENCHMARK_LEADERBOARD
        ],
        "notes": [
            "FCD = Fréchet ChemNet Distance (higher = closer to training distribution).",
            "SNN = Similarity to Nearest Neighbor (higher = more similar to known compounds).",
            "Scaf = Scaffold diversity (higher = more diverse scaffolds).",
            "Validity is typically >95% for modern transformer / diffusion models.",
            "Novelty vs. synthetic accessibility is the current frontier trade-off.",
        ],
    }
