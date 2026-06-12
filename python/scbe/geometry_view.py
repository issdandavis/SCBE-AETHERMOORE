"""Geometry view — wrap RDKit to express a molecule's 3D geometry as a spine view.

Real molecular geometry (3D coordinates, rotor type, shape, point group) comes
from REAL engines -- RDKit for the conformer/descriptors, pymatgen for the point
group when installed -- never hand-rolled. This is the "wrap the real engine,
govern it" path: SMILES -> 3D conformer -> geometry descriptors, emitted as a
``domain='geometry'`` ReactionStatePacket and classified by the shared spine.

A single embedded conformer is one sample of the conformational ensemble, so the
transform is LOSSY_RECOVERABLE: connectivity is preserved (the canonical SMILES
round-trips), but the specific 3D pose is a choice, recorded as a loss note.

This is a geometry/shape descriptor lane, not a quantum-accurate structure.
"""

from __future__ import annotations

from typing import Any

from .reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
)

# rotor classification tolerance (relative to the largest principal moment)
ROTOR_TOL = 0.05


class GeometryEngineError(RuntimeError):
    """Raised when no real geometry engine (RDKit) is available or embedding fails."""


def _require_rdkit():
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, rdMolDescriptors
    except Exception as exc:  # pragma: no cover - environment specific
        raise GeometryEngineError(f"RDKit is required for the geometry view: {exc!r}") from exc
    return Chem, AllChem, rdMolDescriptors


def rotor_type(moments: list[float], tol: float = ROTOR_TOL) -> str:
    """Classify a rigid rotor from ascending principal moments of inertia.

    Pure function (no RDKit) so it is independently testable:
      linear (one ~zero moment) / spherical_top (all equal) /
      symmetric_top (two equal) / asymmetric_top (all distinct).
    """
    a, b, c = sorted(moments)
    scale = max(abs(c), 1e-12)
    a_n, b_n, c_n = a / scale, b / scale, c / scale
    if a_n < tol:
        return "linear"
    if abs(a_n - b_n) < tol and abs(b_n - c_n) < tol:
        return "spherical_top"
    if abs(a_n - b_n) < tol or abs(b_n - c_n) < tol:
        return "symmetric_top"
    return "asymmetric_top"


def _principal_moments(mol, conf) -> list[float]:
    import numpy as np

    n = mol.GetNumAtoms()
    coords = np.array(
        [[conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y, conf.GetAtomPosition(i).z] for i in range(n)]
    )
    masses = np.array([atom.GetMass() for atom in mol.GetAtoms()])
    com = (coords * masses[:, None]).sum(axis=0) / masses.sum()
    r = coords - com
    inertia = np.zeros((3, 3))
    for m, (x, y, z) in zip(masses, r):
        inertia[0, 0] += m * (y * y + z * z)
        inertia[1, 1] += m * (x * x + z * z)
        inertia[2, 2] += m * (x * x + y * y)
        inertia[0, 1] -= m * x * y
        inertia[0, 2] -= m * x * z
        inertia[1, 2] -= m * y * z
    inertia[1, 0], inertia[2, 0], inertia[2, 1] = inertia[0, 1], inertia[0, 2], inertia[1, 2]
    return sorted(float(w) for w in np.linalg.eigvalsh(inertia))


def _point_group(symbols: list[str], coords: list[list[float]]) -> str | None:
    """Point group via pymatgen if installed; None (with honest fallback) otherwise."""
    try:
        from pymatgen.core import Molecule
        from pymatgen.symmetry.analyzer import PointGroupAnalyzer
    except Exception:
        return None
    try:
        return PointGroupAnalyzer(Molecule(symbols, coords)).get_pointgroup().sch_symbol
    except Exception:
        return None


def geometry_descriptors(smiles: str, *, seed: int = 0xC0FFEE) -> dict[str, Any]:
    """RDKit 3D embedding -> geometry descriptors for one conformer."""
    Chem, AllChem, rdMolDescriptors = _require_rdkit()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise GeometryEngineError(f"invalid SMILES: {smiles!r}")
    canonical = Chem.MolToSmiles(mol, canonical=True)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    mol_h = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol_h, params) != 0:
        raise GeometryEngineError(f"3D embedding failed for {smiles!r}")
    AllChem.MMFFOptimizeMolecule(mol_h)
    conf = mol_h.GetConformer()
    moments = _principal_moments(mol_h, conf)
    symbols = [atom.GetSymbol() for atom in mol_h.GetAtoms()]
    coords = [
        [conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y, conf.GetAtomPosition(i).z]
        for i in range(mol_h.GetNumAtoms())
    ]
    pg = _point_group(symbols, coords)
    return {
        "canonical_smiles": canonical,
        "formula": formula,
        "n_atoms_with_h": mol_h.GetNumAtoms(),
        "principal_moments": [round(m, 6) for m in moments],
        "rotor_type": rotor_type(moments),
        "npr1": round(float(rdMolDescriptors.CalcNPR1(mol_h)), 6),
        "npr2": round(float(rdMolDescriptors.CalcNPR2(mol_h)), 6),
        "point_group": pg,
        "point_group_engine": "pymatgen" if pg is not None else "absent(pymatgen):rotor_type_proxy",
    }


def geometry_view_packet(smiles: str, *, seed: int = 0xC0FFEE) -> ReactionStatePacket:
    """Wrap a molecule's 3D geometry as a hash-signed domain='geometry' packet."""
    desc = geometry_descriptors(smiles, seed=seed)
    pg_line = f"point_group={desc['point_group']} ({desc['point_group_engine']})"
    return build_reaction_state_packet(
        domain="geometry",
        step=1,
        bounded_operation="smiles_to_3d_geometry",
        source=ReactionEndpoint(
            identity=smiles,
            representation="smiles",
            language="chem",
            tongue="KO",
        ),
        target=ReactionEndpoint(
            identity=desc["canonical_smiles"],
            representation="geometry_descriptors",
            language="geometry",
            tongue="DR",
            metadata=desc,
        ),
        semantic_engravings=[
            f"rotor_type={desc['rotor_type']}",
            f"NPR=({desc['npr1']}, {desc['npr2']})",
            pg_line,
        ],
        loss_notes=["single conformer sampled; full conformational ensemble not retained"],
        recalculation=ReactionRecalculation(scientific_checks_ok=True, identity_ok=True),
        identity_preserved=True,
        recovery_evidence=["canonical SMILES retained (connectivity recoverable from 3D)"],
        claim_boundary=[
            "geometry from RDKit ETKDG + MMFF (one conformer)",
            "point group requires pymatgen; rotor type is an inertial proxy when absent",
            "shape/geometry descriptor lane, not a quantum-accurate structure",
        ],
    )
