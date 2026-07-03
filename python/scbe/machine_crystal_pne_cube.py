"""Proton/neutron/electron cube for chemistry and nuclear process checks.

This is the p/n/e relation surface adjacent to the Machine Crystal geometry:

* chemistry lane: electron axis moves while proton/neutron totals stay frozen
* nuclear lane: proton/neutron composition can change, but nucleon number and
  charge must balance

The module intentionally uses a small explicit isotope table for the validated
examples. It is a conservation gate and receipt generator, not a nuclear
database.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


ELEMENT_Z = {
    "H": 1,
    "He": 2,
    "C": 6,
    "N": 7,
    "Na": 11,
    "Cl": 17,
    "Kr": 36,
    "Ba": 56,
    "Th": 90,
    "U": 92,
}


class PNECubeError(ValueError):
    """Invalid proton/neutron/electron cube state."""


@dataclass(frozen=True, slots=True)
class Species:
    """Particle or isotope state in p/n/e coordinates."""

    name: str
    protons: int
    neutrons: int
    electrons: int = 0
    count: int = 1

    @property
    def nucleons(self) -> int:
        return self.protons + self.neutrons

    @property
    def charge(self) -> int:
        return self.protons - self.electrons

    def scaled(self) -> "Species":
        return Species(
            self.name,
            self.protons * self.count,
            self.neutrons * self.count,
            self.electrons * self.count,
            1,
        )

    def packet(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "protons": self.protons,
            "neutrons": self.neutrons,
            "electrons": self.electrons,
            "nucleons": self.nucleons,
            "charge": self.charge,
        }


def nucleus(symbol: str, mass_number: int, *, count: int = 1) -> Species:
    """Bare nucleus, used for nuclear equations."""

    if symbol not in ELEMENT_Z:
        raise PNECubeError(f"unknown element symbol: {symbol!r}")
    z = ELEMENT_Z[symbol]
    neutrons = int(mass_number) - z
    if neutrons < 0:
        raise PNECubeError(f"mass number too small for {symbol}-{mass_number}")
    return Species(f"{symbol}-{mass_number}", z, neutrons, 0, count)


def atom(symbol: str, mass_number: int, *, charge: int = 0, count: int = 1) -> Species:
    """Atom or ion, used for chemistry equations.

    ``charge`` is conventional ion charge: Na+ has charge=+1, Cl- has charge=-1.
    """

    base = nucleus(symbol, mass_number, count=count)
    electrons = base.protons - int(charge)
    if electrons < 0:
        raise PNECubeError(f"ion charge removes too many electrons: {symbol}-{mass_number}")
    suffix = "" if charge == 0 else ("+" if charge > 0 else "-")
    if abs(charge) > 1:
        suffix = f"{charge:+d}"
    return Species(f"{symbol}-{mass_number}{suffix}", base.protons, base.neutrons, electrons, count)


def electron(*, count: int = 1) -> Species:
    return Species("e-", 0, 0, 1, count)


def neutron(*, count: int = 1) -> Species:
    return Species("n", 0, 1, 0, count)


def alpha(*, count: int = 1) -> Species:
    return Species("alpha", 2, 2, 0, count)


def totals(side: Iterable[Species]) -> dict:
    p = n = e = 0
    names = []
    for species in side:
        scaled = species.scaled()
        p += scaled.protons
        n += scaled.neutrons
        e += scaled.electrons
        names.append(species.packet())
    return {
        "species": names,
        "protons": p,
        "neutrons": n,
        "electrons": e,
        "nucleons": p + n,
        "charge": p - e,
    }


def validate_reaction(
    label: str,
    left: tuple[Species, ...],
    right: tuple[Species, ...],
    *,
    expected_lane: str,
    note: str,
) -> dict:
    """Validate one p/n/e reaction as chemistry, nuclear, or rejected."""

    l = totals(left)
    r = totals(right)
    mass_ok = l["nucleons"] == r["nucleons"]
    charge_ok = l["charge"] == r["charge"]
    p_frozen = l["protons"] == r["protons"]
    n_frozen = l["neutrons"] == r["neutrons"]
    e_balanced = l["electrons"] == r["electrons"]

    if expected_lane == "chemistry":
        accepted = mass_ok and charge_ok and p_frozen and n_frozen and e_balanced
        lane = "chemistry" if accepted else "rejected"
    elif expected_lane == "nuclear":
        accepted = mass_ok and charge_ok
        lane = "nuclear" if accepted else "rejected"
    elif expected_lane == "reject":
        accepted = False
        lane = "rejected"
    else:
        raise PNECubeError(f"unknown expected lane: {expected_lane!r}")

    if expected_lane == "reject":
        correctly_rejected = not (mass_ok and charge_ok)
    else:
        correctly_rejected = False

    reasons = []
    if not mass_ok:
        reasons.append(f"nucleon A {l['nucleons']}->{r['nucleons']}")
    if not charge_ok:
        reasons.append(f"charge {l['charge']}->{r['charge']}")
    if expected_lane == "chemistry" and not p_frozen:
        reasons.append(f"protons moved {l['protons']}->{r['protons']}")
    if expected_lane == "chemistry" and not n_frozen:
        reasons.append(f"neutrons moved {l['neutrons']}->{r['neutrons']}")
    if expected_lane == "chemistry" and not e_balanced:
        reasons.append(f"electrons unbalanced {l['electrons']}->{r['electrons']}")

    return {
        "label": label,
        "expected_lane": expected_lane,
        "lane": lane,
        "accepted": accepted,
        "correctly_rejected": correctly_rejected,
        "note": note,
        "left": l,
        "right": r,
        "checks": {
            "nucleon_A_conserved": mass_ok,
            "charge_conserved": charge_ok,
            "protons_frozen": p_frozen,
            "neutrons_frozen": n_frozen,
            "electrons_balanced": e_balanced,
        },
        "reasons": reasons,
    }


def pne_cube_receipt() -> dict:
    """Run the validated p/n/e chemistry+nuclear cases."""

    cases = [
        validate_reaction(
            "Na-23 -> Na-23+ + e-",
            (atom("Na", 23),),
            (atom("Na", 23, charge=+1), electron()),
            expected_lane="chemistry",
            note="chemistry ionization: electron axis moves, p/n frozen",
        ),
        validate_reaction(
            "Cl-35 + e- -> Cl-35-",
            (atom("Cl", 35), electron()),
            (atom("Cl", 35, charge=-1),),
            expected_lane="chemistry",
            note="chemistry reduction: electron axis moves, p/n frozen",
        ),
        validate_reaction(
            "C-14 -> N-14 + e-",
            (nucleus("C", 14),),
            (nucleus("N", 14), electron()),
            expected_lane="nuclear",
            note="beta-minus: a neutron becomes a proton and emits an electron",
        ),
        validate_reaction(
            "U-238 -> Th-234 + alpha",
            (nucleus("U", 238),),
            (nucleus("Th", 234), alpha()),
            expected_lane="nuclear",
            note="alpha decay",
        ),
        validate_reaction(
            "H-2 + H-3 -> He-4 + n",
            (nucleus("H", 2), nucleus("H", 3)),
            (nucleus("He", 4), neutron()),
            expected_lane="nuclear",
            note="fusion",
        ),
        validate_reaction(
            "U-235 + n -> Ba-141 + Kr-92 + 3n",
            (nucleus("U", 235), neutron()),
            (nucleus("Ba", 141), nucleus("Kr", 92), neutron(count=3)),
            expected_lane="nuclear",
            note="fission",
        ),
        validate_reaction(
            "C-14 -> N-15 + e-",
            (nucleus("C", 14),),
            (nucleus("N", 15), electron()),
            expected_lane="reject",
            note="fake beta-minus: creates one nucleon",
        ),
        validate_reaction(
            "C-14 -> C-14 + n",
            (nucleus("C", 14),),
            (nucleus("C", 14), neutron()),
            expected_lane="reject",
            note="fake emission: neutron from nothing",
        ),
    ]

    chemistry = [case for case in cases if case["expected_lane"] == "chemistry"]
    nuclear = [case for case in cases if case["expected_lane"] == "nuclear"]
    rejected = [case for case in cases if case["expected_lane"] == "reject"]

    beta = next(case for case in cases if case["label"] == "C-14 -> N-14 + e-")
    checks = {
        "chemistry_electron_axis_only": all(
            case["accepted"]
            and case["checks"]["protons_frozen"]
            and case["checks"]["neutrons_frozen"]
            and case["checks"]["electrons_balanced"]
            for case in chemistry
        ),
        "nuclear_processes_balance_A_and_charge": all(
            case["accepted"]
            and case["checks"]["nucleon_A_conserved"]
            and case["checks"]["charge_conserved"]
            for case in nuclear
        ),
        "invalid_cases_rejected": all(
            (not case["accepted"]) and case["correctly_rejected"] for case in rejected
        ),
        "beta_minus_neutron_to_proton": (
            beta["left"]["protons"] == 6
            and beta["left"]["neutrons"] == 8
            and beta["right"]["protons"] == 7
            and beta["right"]["neutrons"] == 7
            and beta["right"]["electrons"] == 1
        ),
        "fission_neutron_count_three": any(
            case["label"] == "U-235 + n -> Ba-141 + Kr-92 + 3n"
            and case["right"]["neutrons"] == 144
            for case in cases
        ),
    }

    return {
        "schema": "scbe_machine_crystal_pne_cube_v1",
        "claim": "Chemistry is an electron-axis lane over frozen p/n totals; nuclear processes use the full p/n/e charge-and-nucleon conservation cube.",
        "cases": cases,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "honest_boundary": "Small conservation-gate example set, not a full chemistry or nuclear database.",
    }


def main() -> int:
    receipt = pne_cube_receipt()
    out_dir = Path("artifacts/machine_crystal")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pne_cube.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


__all__ = [
    "PNECubeError",
    "Species",
    "alpha",
    "atom",
    "electron",
    "neutron",
    "nucleus",
    "pne_cube_receipt",
    "totals",
    "validate_reaction",
]


if __name__ == "__main__":
    raise SystemExit(main())
