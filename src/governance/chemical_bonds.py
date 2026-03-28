"""Chemical bond analysis of tongue interactions.

Treats the 6 Sacred Tongues as a molecular system where perpendicular
pairs form chemical bonds. Complex numbers encode both activation
strength (real) and phase relationship (imaginary).

Bond types:
  KO-RU = sigma bond (intent constrained by policy)
  CA-UM = pi bond (compute constrained by security)
  AV-DR = delta bond (transport constrained by structure)

Usage:
    from src.governance.chemical_bonds import TongueMolecule
    mol = TongueMolecule([0.9, 0.1, 0.7, 0.4, 0.9, 0.2])
    print(mol.stability)        # 0.0-1.0
    print(mol.broken_bonds)     # which bonds snapped
    print(mol.fuzzy_hostile)    # fuzzy membership in hostile set
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
BOND_PAIRS = [("KO", "RU"), ("CA", "UM"), ("AV", "DR")]
BOND_NAMES = ["sigma_KO_RU", "pi_CA_UM", "delta_AV_DR"]


@dataclass
class BondState:
    name: str
    z: complex
    energy: float
    angle_deg: float
    dissociation: float
    broken: bool


@dataclass
class MoleculeReport:
    bonds: List[BondState]
    total_energy: float
    stability: float
    fuzzy_safe: float
    fuzzy_cautious: float
    fuzzy_suspicious: float
    fuzzy_hostile: float
    broken_count: int
    dominant_class: str


class TongueMolecule:
    """Molecular analysis of a 6D tongue coordinate vector."""

    def __init__(self, coords: List[float], reference: List[float] = None):
        if len(coords) != 6:
            raise ValueError(f"Expected 6 coords, got {len(coords)}")
        self.coords = list(coords)
        self.reference = reference or [0.5] * 6
        self._bonds = None
        self._report = None

    def _get_bond(self, t1: str, t2: str, name: str) -> BondState:
        i1 = TONGUES.index(t1)
        i2 = TONGUES.index(t2)
        real_part = (self.coords[i1] + self.coords[i2]) / 2.0
        imag_part = self.coords[i1] - self.coords[i2]
        z = complex(real_part, imag_part)
        energy = abs(z) ** 2
        angle = math.degrees(math.atan2(z.imag, z.real))
        dissociation = abs(z.real) * (1.0 + abs(z.imag))

        # Check if bond is broken compared to reference
        ri1 = TONGUES.index(t1)
        ri2 = TONGUES.index(t2)
        ref_real = (self.reference[ri1] + self.reference[ri2]) / 2.0
        ref_imag = self.reference[ri1] - self.reference[ri2]
        ref_z = complex(ref_real, ref_imag)
        shift = abs(z - ref_z)
        broken = shift > 0.3

        return BondState(
            name=name,
            z=z,
            energy=energy,
            angle_deg=angle,
            dissociation=dissociation,
            broken=broken,
        )

    @property
    def bonds(self) -> List[BondState]:
        if self._bonds is None:
            self._bonds = [self._get_bond(t1, t2, name) for (t1, t2), name in zip(BOND_PAIRS, BOND_NAMES)]
        return self._bonds

    @property
    def total_energy(self) -> float:
        return sum(b.energy for b in self.bonds)

    @property
    def stability(self) -> float:
        angles = [math.radians(b.angle_deg) for b in self.bonds]
        variance = float(np.var(angles))
        return 1.0 / (1.0 + variance * 10.0)

    @property
    def broken_count(self) -> int:
        return sum(1 for b in self.bonds if b.broken)

    @property
    def broken_bonds(self) -> List[str]:
        return [b.name for b in self.bonds if b.broken]

    @staticmethod
    def _fuzzy(value: float, center: float, width: float) -> float:
        return math.exp(-((value - center) ** 2) / (2 * width**2))

    @property
    def fuzzy_safe(self) -> float:
        return self._fuzzy(self.total_energy, 0.3, 0.15)

    @property
    def fuzzy_cautious(self) -> float:
        return self._fuzzy(self.total_energy, 0.6, 0.15)

    @property
    def fuzzy_suspicious(self) -> float:
        return self._fuzzy(self.total_energy, 0.9, 0.15)

    @property
    def fuzzy_hostile(self) -> float:
        return self._fuzzy(self.total_energy, 1.3, 0.20)

    @property
    def dominant_class(self) -> str:
        scores = {
            "SAFE": self.fuzzy_safe,
            "CAUTIOUS": self.fuzzy_cautious,
            "SUSPICIOUS": self.fuzzy_suspicious,
            "HOSTILE": self.fuzzy_hostile,
        }
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        return max(scores, key=scores.get)

    def report(self) -> MoleculeReport:
        if self._report is None:
            scores = {
                "SAFE": self.fuzzy_safe,
                "CAUTIOUS": self.fuzzy_cautious,
                "SUSPICIOUS": self.fuzzy_suspicious,
                "HOSTILE": self.fuzzy_hostile,
            }
            total = sum(scores.values())
            if total > 0:
                scores = {k: v / total for k, v in scores.items()}
            self._report = MoleculeReport(
                bonds=self.bonds,
                total_energy=self.total_energy,
                stability=self.stability,
                fuzzy_safe=scores["SAFE"],
                fuzzy_cautious=scores["CAUTIOUS"],
                fuzzy_suspicious=scores["SUSPICIOUS"],
                fuzzy_hostile=scores["HOSTILE"],
                broken_count=self.broken_count,
                dominant_class=self.dominant_class,
            )
        return self._report


def batch_analyze(
    coords_list: List[List[float]],
    reference: List[float] = None,
) -> List[MoleculeReport]:
    return [TongueMolecule(c, reference).report() for c in coords_list]
