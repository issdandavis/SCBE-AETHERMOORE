"""Canonical periodic-table identities for atomic token routing.

The atomic-tokenizer feature table historically covered only a small teaching
subset.  This module provides the complete 118-element identity layer without
pretending that one scalar ``valence`` or electronegativity value is universal.
Only stable identity fields live here: symbol, atomic number, conventional
period/group placement, and orbital block.

Element names, symbols, and atomic numbers follow the IUPAC periodic table.
Groups use IUPAC's 1--18 numbering.  The f-block rows retain ``group=3`` as a
layout/address convention and are distinguished by ``block='f'``; this is not
a claim that IUPAC has resolved every group-3 presentation convention.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

IUPAC_PERIODIC_TABLE_URL: Final = (
    "https://iupac.org/what-we-do/periodic-table-of-elements/"
)


@dataclass(frozen=True, slots=True)
class PeriodicIdentity:
    symbol: str
    atomic_number: int
    period: int
    group: int
    block: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


# Atomic-number order is the primary identity.  Keep this compact and validate
# every derived position below at import time.
SYMBOLS_BY_ATOMIC_NUMBER: Final[tuple[str, ...]] = (
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
    "Md",
    "No",
    "Lr",
    "Rf",
    "Db",
    "Sg",
    "Bh",
    "Hs",
    "Mt",
    "Ds",
    "Rg",
    "Cn",
    "Nh",
    "Fl",
    "Mc",
    "Lv",
    "Ts",
    "Og",
)


_PERIOD_GROUP_ROWS: Final[dict[int, dict[int, str]]] = {
    1: {1: "H", 18: "He"},
    2: {1: "Li", 2: "Be", 13: "B", 14: "C", 15: "N", 16: "O", 17: "F", 18: "Ne"},
    3: {1: "Na", 2: "Mg", 13: "Al", 14: "Si", 15: "P", 16: "S", 17: "Cl", 18: "Ar"},
    4: {
        1: "K",
        2: "Ca",
        3: "Sc",
        4: "Ti",
        5: "V",
        6: "Cr",
        7: "Mn",
        8: "Fe",
        9: "Co",
        10: "Ni",
        11: "Cu",
        12: "Zn",
        13: "Ga",
        14: "Ge",
        15: "As",
        16: "Se",
        17: "Br",
        18: "Kr",
    },
    5: {
        1: "Rb",
        2: "Sr",
        3: "Y",
        4: "Zr",
        5: "Nb",
        6: "Mo",
        7: "Tc",
        8: "Ru",
        9: "Rh",
        10: "Pd",
        11: "Ag",
        12: "Cd",
        13: "In",
        14: "Sn",
        15: "Sb",
        16: "Te",
        17: "I",
        18: "Xe",
    },
    6: {
        1: "Cs",
        2: "Ba",
        3: "La",
        4: "Hf",
        5: "Ta",
        6: "W",
        7: "Re",
        8: "Os",
        9: "Ir",
        10: "Pt",
        11: "Au",
        12: "Hg",
        13: "Tl",
        14: "Pb",
        15: "Bi",
        16: "Po",
        17: "At",
        18: "Rn",
    },
    7: {
        1: "Fr",
        2: "Ra",
        3: "Ac",
        4: "Rf",
        5: "Db",
        6: "Sg",
        7: "Bh",
        8: "Hs",
        9: "Mt",
        10: "Ds",
        11: "Rg",
        12: "Cn",
        13: "Nh",
        14: "Fl",
        15: "Mc",
        16: "Lv",
        17: "Ts",
        18: "Og",
    },
}

_F_BLOCK: Final[dict[int, tuple[str, ...]]] = {
    6: (
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
    ),
    7: (
        "Th",
        "Pa",
        "U",
        "Np",
        "Pu",
        "Am",
        "Cm",
        "Bk",
        "Cf",
        "Es",
        "Fm",
        "Md",
        "No",
        "Lr",
    ),
}


def _positions() -> dict[str, tuple[int, int, str]]:
    positions: dict[str, tuple[int, int, str]] = {}
    for period, row in _PERIOD_GROUP_ROWS.items():
        for group, symbol in row.items():
            if symbol == "He" or group <= 2:
                block = "s"
            elif group <= 12:
                block = "d"
            else:
                block = "p"
            positions[symbol] = (period, group, block)
    for period, symbols in _F_BLOCK.items():
        for symbol in symbols:
            positions[symbol] = (period, 3, "f")
    return positions


_POSITIONS = _positions()

if len(SYMBOLS_BY_ATOMIC_NUMBER) != 118:
    raise RuntimeError("periodic identity table must contain exactly 118 symbols")
if len(set(SYMBOLS_BY_ATOMIC_NUMBER)) != 118:
    raise RuntimeError("periodic identity symbols must be unique")
if set(_POSITIONS) != set(SYMBOLS_BY_ATOMIC_NUMBER):
    missing = sorted(set(SYMBOLS_BY_ATOMIC_NUMBER) - set(_POSITIONS))
    extra = sorted(set(_POSITIONS) - set(SYMBOLS_BY_ATOMIC_NUMBER))
    raise RuntimeError(
        f"periodic positions disagree with identities: missing={missing}, extra={extra}"
    )


PERIODIC_IDENTITIES: Final[dict[str, PeriodicIdentity]] = {
    symbol: PeriodicIdentity(
        symbol=symbol,
        atomic_number=atomic_number,
        period=_POSITIONS[symbol][0],
        group=_POSITIONS[symbol][1],
        block=_POSITIONS[symbol][2],
    )
    for atomic_number, symbol in enumerate(SYMBOLS_BY_ATOMIC_NUMBER, start=1)
}

_SYMBOL_BY_LOWER: Final[dict[str, str]] = {
    symbol.lower(): symbol for symbol in PERIODIC_IDENTITIES
}


def periodic_identity(token: str) -> PeriodicIdentity | None:
    """Resolve an element symbol case-insensitively, or return ``None``."""

    if not token:
        return None
    symbol = _SYMBOL_BY_LOWER.get(token.strip().lower())
    return PERIODIC_IDENTITIES.get(symbol) if symbol else None


def periodic_identity_manifest() -> dict[str, object]:
    """Return a deterministic, JSON-ready 118-row identity manifest."""

    return {
        "schema": "scbe.periodic-identity.v1",
        "source": IUPAC_PERIODIC_TABLE_URL,
        "group_three_boundary": (
            "f-block rows use group=3 only as an address convention; block='f' retains the distinction"
        ),
        "elements": [
            PERIODIC_IDENTITIES[symbol].as_dict() for symbol in SYMBOLS_BY_ATOMIC_NUMBER
        ],
    }


__all__ = [
    "IUPAC_PERIODIC_TABLE_URL",
    "PERIODIC_IDENTITIES",
    "PeriodicIdentity",
    "SYMBOLS_BY_ATOMIC_NUMBER",
    "periodic_identity",
    "periodic_identity_manifest",
]
