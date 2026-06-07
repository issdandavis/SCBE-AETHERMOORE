#!/usr/bin/env python3
"""Mission body budget: orbit bill -> propellant bill -> crew-loop bill.

This module intentionally separates load-bearing physics from accounting
assumptions:

* `src.physics_sim.orbital.hohmann_transfer` supplies transfer time and delta-v.
* Tsiolkovsky's rocket equation supplies propellant mass.
* Crew water/food/oxygen rates are explicit knobs, not hidden constants.

The default profile is illustrative. It is a mission-accounting scaffold, not a
NASA design reference.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Sequence

from src.physics_sim.orbital import (
    AU,
    MU_EARTH,
    MU_SUN,
    RADIUS_EARTH,
    circular_velocity,
    hohmann_transfer,
)

G0_M_S2 = 9.80665
MARS_ORBIT_AU = 1.524

# Electrodynamic-tether regime (LEO). The EDT force F = I*L*B is linear in B, so it is
# field-odd: reversing B reverses the thrust. That is the property that makes a tether a
# steerable, propellantless Δv source in a planetary magnetic field.
B_FIELD_LEO_T = 25e-6  # ~Earth field magnitude in LEO (T)
KM_M = 1000.0


@dataclass(frozen=True)
class PropulsionOption:
    name: str
    isp_s: float
    propellant_kind: str
    notes: str


@dataclass(frozen=True)
class PropellantBudget:
    name: str
    isp_s: float
    propellant_kind: str
    delta_v_m_s: float
    dry_mass_kg: float
    mass_ratio: float
    propellant_kg: float
    wet_mass_kg: float
    wet_mass_fraction_propellant: float
    work_water_spent_kg: float
    notes: str


@dataclass(frozen=True)
class CrewLoopAssumptions:
    crew_size: int = 4
    personal_water_kg_per_crew_day: float = 4.0
    personal_water_recovery_fraction: float = 0.93
    oxygen_kg_per_crew_day: float = 0.84
    oxygen_recovery_fraction: float = 0.50
    food_kg_per_crew_day: float = 0.80
    food_closure_fraction: float = 0.0
    life_water_reserve_days: float = 14.0
    work_water_reserve_kg: float = 1000.0


@dataclass(frozen=True)
class CrewLoopBudget:
    crew_size: int
    mission_days: float
    personal_water_use_kg: float
    personal_water_makeup_kg: float
    protected_life_water_reserve_kg: float
    oxygen_use_kg: float
    oxygen_makeup_kg: float
    food_use_kg: float
    food_makeup_kg: float
    work_water_reserve_kg: float
    assumptions: CrewLoopAssumptions


@dataclass(frozen=True)
class MarsMissionBodyBudget:
    schema_version: str
    mission: str
    transfer: dict[str, float]
    dry_mass_kg: float
    crew_loop: CrewLoopBudget
    propulsion_options: list[PropellantBudget]
    interpretation: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_PROPULSION_OPTIONS: tuple[PropulsionOption, ...] = (
    PropulsionOption(
        name="chemical_h2_o2_reference",
        isp_s=450.0,
        propellant_kind="hydrogen_oxygen",
        notes="High-thrust chemical reference; water is reaction product, not preserved inventory.",
    ),
    PropulsionOption(
        name="nuclear_thermal_reference",
        isp_s=900.0,
        propellant_kind="hydrogen",
        notes="Nuclear thermal class reference; hydrogen is the hard currency.",
    ),
    PropulsionOption(
        name="electric_ion_reference",
        isp_s=3000.0,
        propellant_kind="inert_gas_or_other",
        notes="High-Isp electric reference; low thrust, power-limited, not a launch engine.",
    ),
    PropulsionOption(
        name="steam_water_reference",
        isp_s=220.0,
        propellant_kind="work_water",
        notes="Simple water exhaust reference; shows why water should not be the whole transfer propellant.",
    ),
)


def rocket_equation_propellant_kg(dry_mass_kg: float, delta_v_m_s: float, isp_s: float) -> dict[str, float]:
    if dry_mass_kg <= 0:
        raise ValueError("dry_mass_kg must be positive")
    if delta_v_m_s < 0:
        raise ValueError("delta_v_m_s must be non-negative")
    if isp_s <= 0:
        raise ValueError("isp_s must be positive")

    mass_ratio = math.exp(delta_v_m_s / (isp_s * G0_M_S2))
    propellant_kg = dry_mass_kg * (mass_ratio - 1.0)
    wet_mass_kg = dry_mass_kg + propellant_kg
    return {
        "mass_ratio": mass_ratio,
        "propellant_kg": propellant_kg,
        "wet_mass_kg": wet_mass_kg,
        "wet_mass_fraction_propellant": propellant_kg / wet_mass_kg,
    }


def build_propellant_budget(
    *,
    option: PropulsionOption,
    dry_mass_kg: float,
    delta_v_m_s: float,
) -> PropellantBudget:
    rocket = rocket_equation_propellant_kg(dry_mass_kg, delta_v_m_s, option.isp_s)
    work_water_spent_kg = rocket["propellant_kg"] if option.propellant_kind == "work_water" else 0.0
    return PropellantBudget(
        name=option.name,
        isp_s=option.isp_s,
        propellant_kind=option.propellant_kind,
        delta_v_m_s=delta_v_m_s,
        dry_mass_kg=dry_mass_kg,
        mass_ratio=rocket["mass_ratio"],
        propellant_kg=rocket["propellant_kg"],
        wet_mass_kg=rocket["wet_mass_kg"],
        wet_mass_fraction_propellant=rocket["wet_mass_fraction_propellant"],
        work_water_spent_kg=work_water_spent_kg,
        notes=option.notes,
    )


def build_crew_loop_budget(mission_days: float, assumptions: CrewLoopAssumptions) -> CrewLoopBudget:
    if mission_days <= 0:
        raise ValueError("mission_days must be positive")
    if assumptions.crew_size <= 0:
        raise ValueError("crew_size must be positive")
    for field_name in (
        "personal_water_recovery_fraction",
        "oxygen_recovery_fraction",
        "food_closure_fraction",
    ):
        value = float(getattr(assumptions, field_name))
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1")

    crew_days = assumptions.crew_size * mission_days
    personal_water_use = crew_days * assumptions.personal_water_kg_per_crew_day
    oxygen_use = crew_days * assumptions.oxygen_kg_per_crew_day
    food_use = crew_days * assumptions.food_kg_per_crew_day
    return CrewLoopBudget(
        crew_size=assumptions.crew_size,
        mission_days=mission_days,
        personal_water_use_kg=personal_water_use,
        personal_water_makeup_kg=personal_water_use * (1.0 - assumptions.personal_water_recovery_fraction),
        protected_life_water_reserve_kg=(
            assumptions.crew_size * assumptions.life_water_reserve_days * assumptions.personal_water_kg_per_crew_day
        ),
        oxygen_use_kg=oxygen_use,
        oxygen_makeup_kg=oxygen_use * (1.0 - assumptions.oxygen_recovery_fraction),
        food_use_kg=food_use,
        food_makeup_kg=food_use * (1.0 - assumptions.food_closure_fraction),
        work_water_reserve_kg=assumptions.work_water_reserve_kg,
        assumptions=assumptions,
    )


def build_earth_mars_body_budget(
    *,
    dry_mass_kg: float = 20_000.0,
    crew_assumptions: CrewLoopAssumptions | None = None,
    propulsion_options: Sequence[PropulsionOption] = DEFAULT_PROPULSION_OPTIONS,
) -> MarsMissionBodyBudget:
    transfer = hohmann_transfer(1.0 * AU, MARS_ORBIT_AU * AU, MU_SUN)
    crew_budget = build_crew_loop_budget(
        mission_days=transfer["transfer_time_days"],
        assumptions=crew_assumptions or CrewLoopAssumptions(),
    )
    propellant = [
        build_propellant_budget(option=option, dry_mass_kg=dry_mass_kg, delta_v_m_s=transfer["delta_v_total_m_s"])
        for option in propulsion_options
    ]
    return MarsMissionBodyBudget(
        schema_version="mars_mission_body_budget_v1",
        mission="heliocentric_earth_to_mars_hohmann_body_budget",
        transfer=transfer,
        dry_mass_kg=dry_mass_kg,
        crew_loop=crew_budget,
        propulsion_options=propellant,
        interpretation={
            "scope": (
                "Heliocentric transfer leg only. Earth departure, Mars capture, launch, landing, margins, boiloff, "
                "power, and thrust-time constraints are outside this first budget."
            ),
            "water_rule": (
                "Life water is protected inventory. Work water can be spent, but water-exhaust propulsion directly "
                "draws down the work-water account unless local ice or other resupply replaces it."
            ),
            "body_model": (
                "The orbital module tells the trip bill; the body budget tells which substance account pays it."
            ),
        },
    )


# --------------------------------------------------------------------------- #
#  CARGO-ONLY MODE (no crew loop)                                              #
#  A logistics / debris-tug machine: no life support, no food, no human margin.#
#  Accounts are payload masses; the electrodynamic tether is the              #
#  propellantless channel (it trades TIME for propellant MASS, and its force   #
#  F=I*L*B is field-odd -- reversing B reverses the thrust).                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CargoManifest:
    """Payload accounts for a crewless tug. Every kg here is deliverable mass."""

    bus_dry_mass_kg: float = 1_500.0  # the tug itself: structure, avionics, capture arm, tether reel
    metal_feedstock_kg: float = 0.0
    water_ice_kg: float = 0.0
    regolith_kg: float = 0.0
    robotics_spares_kg: float = 0.0
    debris_capture_hardware_kg: float = 0.0

    @property
    def payload_kg(self) -> float:
        return (
            self.metal_feedstock_kg
            + self.water_ice_kg
            + self.regolith_kg
            + self.robotics_spares_kg
            + self.debris_capture_hardware_kg
        )

    @property
    def dry_mass_kg(self) -> float:
        return self.bus_dry_mass_kg + self.payload_kg


@dataclass(frozen=True)
class ElectrodynamicTether:
    """A bare/conductive tether. mode 'deorbit' = passive harvest (drag, free Δv,
    dissipated power is yours to use). mode 'boost' = powered: you drive current
    against the motional EMF and PAY electrical energy (propellantless, not free)."""

    length_m: float = 10_000.0
    current_a: float = 5.0
    b_field_t: float = B_FIELD_LEO_T
    mode: str = "deorbit"


def edt_thrust_n(tether: ElectrodynamicTether) -> float:
    """Lorentz thrust  F = I * L * B  (the field-odd channel; flips sign with B)."""
    return tether.current_a * tether.length_m * tether.b_field_t


def edt_motional_emf_v(tether: ElectrodynamicTether, rel_speed_m_s: float) -> float:
    """Motional EMF  emf = v * B * L  driven by orbital motion across the field."""
    return rel_speed_m_s * tether.b_field_t * tether.length_m


def edt_delta_v_time_s(delta_v_m_s: float, dry_mass_kg: float, thrust_n: float) -> float:
    """How long the (low) tether thrust must run to deliver a given Δv: t = Δv*m / F.
    This is the EDT's real cost -- it pays in TIME what a rocket pays in propellant MASS."""
    if thrust_n <= 0:
        raise ValueError("thrust_n must be positive")
    return delta_v_m_s * dry_mass_kg / thrust_n


@dataclass(frozen=True)
class CargoTugBudget:
    schema_version: str
    mission: str
    transfer: dict[str, float]
    manifest: CargoManifest
    tether_length_m: float
    tether_current_a: float
    tether_mode: str
    motional_emf_v: float
    tether_thrust_n: float
    edt_only_thrust_days: float
    edt_electrical_power_w: float
    edt_energy_kwh: float
    propellant_options: list[PropellantBudget]
    interpretation: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_cargo_tug_budget(
    *,
    alt_start_km: float = 800.0,
    alt_end_km: float = 300.0,
    manifest: CargoManifest | None = None,
    tether: ElectrodynamicTether | None = None,
    propulsion_options: Sequence[PropulsionOption] = DEFAULT_PROPULSION_OPTIONS,
) -> CargoTugBudget:
    """Earth-centric orbit change for a crewless tug. The Hohmann Δv sets the bill;
    the rocket equation prices it in propellant; the tether prices it in TIME (and,
    for boost, in electrical energy) at zero propellant."""
    manifest = manifest or CargoManifest()
    tether = tether or ElectrodynamicTether()

    r1 = RADIUS_EARTH + alt_start_km * KM_M
    r2 = RADIUS_EARTH + alt_end_km * KM_M
    transfer = hohmann_transfer(r1, r2, MU_EARTH)
    delta_v = transfer["delta_v_total_m_s"]

    dry_mass = manifest.dry_mass_kg
    rel_speed = circular_velocity(r1, MU_EARTH)
    emf = edt_motional_emf_v(tether, rel_speed)
    thrust = edt_thrust_n(tether)
    edt_seconds = edt_delta_v_time_s(delta_v, dry_mass, thrust)

    # Power: deorbit DISSIPATES emf*I (a harvest you can use); boost SPENDS emf*I.
    electrical_power_w = emf * tether.current_a
    energy_kwh = electrical_power_w * edt_seconds / 3.6e6

    propellant = [
        build_propellant_budget(option=option, dry_mass_kg=dry_mass, delta_v_m_s=delta_v)
        for option in propulsion_options
    ]

    sign = "harvested (yours to use)" if tether.mode == "deorbit" else "spent (you pay)"
    return CargoTugBudget(
        schema_version="cargo_tug_body_budget_v1",
        mission=f"leo_{alt_start_km:.0f}km_to_{alt_end_km:.0f}km_crewless_tug",
        transfer=transfer,
        manifest=manifest,
        tether_length_m=tether.length_m,
        tether_current_a=tether.current_a,
        tether_mode=tether.mode,
        motional_emf_v=emf,
        tether_thrust_n=thrust,
        edt_only_thrust_days=edt_seconds / 86400.0,
        edt_electrical_power_w=electrical_power_w,
        edt_energy_kwh=energy_kwh,
        propellant_options=propellant,
        interpretation={
            "scope": (
                "Single Earth-centric orbit change for a crewless tug. Rendezvous, attitude, plasma "
                "contactor losses, tether libration/survivability, and J2 are outside this first budget."
            ),
            "edt_rule": (
                "The tether is a field-odd harvest/drive: F=I*L*B reverses with B. "
                "It delivers the SAME Δv as the rocket at ZERO propellant, paid for in thrust TIME "
                f"(~{edt_seconds / 86400.0:.1f} days here). Electrical power {electrical_power_w / 1000:.1f} kW "
                f"is {sign} in '{tether.mode}' mode."
            ),
            "why_cargo_first": (
                "No crew = no life-support loop, no food, no human safety margin. The whole budget reduces "
                "to payload mass, Δv, tether force, and orbital mechanics -- the practical first target."
            ),
        },
    )


def _format_kg(value: float) -> str:
    return f"{value:,.1f}"


def _print_summary(budget: MarsMissionBodyBudget) -> None:
    transfer = budget.transfer
    print("Mars mission body budget v1")
    print(f"transfer_days={transfer['transfer_time_days']:.2f}")
    print(f"heliocentric_delta_v_m_s={transfer['delta_v_total_m_s']:.2f}")
    print(f"dry_mass_kg={_format_kg(budget.dry_mass_kg)}")
    crew = budget.crew_loop
    print(
        "crew_loop "
        f"crew={crew.crew_size} "
        f"life_water_use_kg={_format_kg(crew.personal_water_use_kg)} "
        f"life_water_makeup_kg={_format_kg(crew.personal_water_makeup_kg)} "
        f"food_makeup_kg={_format_kg(crew.food_makeup_kg)} "
        f"oxygen_makeup_kg={_format_kg(crew.oxygen_makeup_kg)}"
    )
    print("propulsion_options")
    for option in budget.propulsion_options:
        print(
            f"  {option.name:<28} "
            f"isp={option.isp_s:>6.1f}s "
            f"prop_kg={_format_kg(option.propellant_kg):>12} "
            f"prop_frac={option.wet_mass_fraction_propellant:>6.1%} "
            f"work_water_spent_kg={_format_kg(option.work_water_spent_kg)}"
        )


def _print_cargo_summary(budget: CargoTugBudget) -> None:
    transfer = budget.transfer
    m = budget.manifest
    print("Cargo tug body budget v1 (crewless)")
    print(f"mission={budget.mission}")
    print(
        f"transfer_days={transfer['transfer_time_days']:.3f}  hohmann_delta_v_m_s={transfer['delta_v_total_m_s']:.2f}"
    )
    print(
        "manifest "
        f"bus_kg={_format_kg(m.bus_dry_mass_kg)} "
        f"payload_kg={_format_kg(m.payload_kg)} "
        f"dry_mass_kg={_format_kg(m.dry_mass_kg)}"
    )
    print(
        "  payload  "
        f"metal={_format_kg(m.metal_feedstock_kg)} "
        f"water_ice={_format_kg(m.water_ice_kg)} "
        f"regolith={_format_kg(m.regolith_kg)} "
        f"robotics_spares={_format_kg(m.robotics_spares_kg)} "
        f"capture_hw={_format_kg(m.debris_capture_hardware_kg)}"
    )
    print(
        "electrodynamic_tether "
        f"mode={budget.tether_mode} L={budget.tether_length_m:.0f}m I={budget.tether_current_a:.1f}A "
        f"emf={budget.motional_emf_v:.1f}V thrust_N={budget.tether_thrust_n:.3f}"
    )
    verb = "harvested" if budget.tether_mode == "deorbit" else "spent"
    print(
        "  edt_only "
        f"thrust_days={budget.edt_only_thrust_days:.2f} "
        f"propellant_kg=0.0 "
        f"power_kW={budget.edt_electrical_power_w / 1000:.2f}({verb}) "
        f"energy_kWh={budget.edt_energy_kwh:.0f}"
    )
    print("propellant_options (same Δv, priced in MASS instead of TIME)")
    for option in budget.propellant_options:
        print(
            f"  {option.name:<28} "
            f"isp={option.isp_s:>6.1f}s "
            f"prop_kg={_format_kg(option.propellant_kg):>12} "
            f"prop_frac={option.wet_mass_fraction_propellant:>6.1%}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("crew", "cargo"), default="crew")
    # crew mode
    parser.add_argument("--dry-mass-kg", type=float, default=20_000.0)
    parser.add_argument("--crew-size", type=int, default=4)
    parser.add_argument("--water-recovery", type=float, default=0.93)
    parser.add_argument("--oxygen-recovery", type=float, default=0.50)
    parser.add_argument("--food-closure", type=float, default=0.0)
    # cargo mode
    parser.add_argument("--alt-start-km", type=float, default=800.0)
    parser.add_argument("--alt-end-km", type=float, default=300.0)
    parser.add_argument("--bus-kg", type=float, default=1_500.0)
    parser.add_argument("--metal-kg", type=float, default=0.0)
    parser.add_argument("--water-ice-kg", type=float, default=0.0)
    parser.add_argument("--regolith-kg", type=float, default=0.0)
    parser.add_argument("--robotics-spares-kg", type=float, default=0.0)
    parser.add_argument("--debris-capture-kg", type=float, default=0.0)
    parser.add_argument("--tether-length-m", type=float, default=10_000.0)
    parser.add_argument("--tether-current-a", type=float, default=5.0)
    parser.add_argument("--tether-mode", choices=("deorbit", "boost"), default="deorbit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.mode == "cargo":
        manifest = CargoManifest(
            bus_dry_mass_kg=args.bus_kg,
            metal_feedstock_kg=args.metal_kg,
            water_ice_kg=args.water_ice_kg,
            regolith_kg=args.regolith_kg,
            robotics_spares_kg=args.robotics_spares_kg,
            debris_capture_hardware_kg=args.debris_capture_kg,
        )
        tether = ElectrodynamicTether(
            length_m=args.tether_length_m,
            current_a=args.tether_current_a,
            mode=args.tether_mode,
        )
        cargo = build_cargo_tug_budget(
            alt_start_km=args.alt_start_km,
            alt_end_km=args.alt_end_km,
            manifest=manifest,
            tether=tether,
        )
        if args.json:
            print(json.dumps(cargo.to_dict(), indent=2, sort_keys=True))
        else:
            _print_cargo_summary(cargo)
        return 0

    assumptions = CrewLoopAssumptions(
        crew_size=args.crew_size,
        personal_water_recovery_fraction=args.water_recovery,
        oxygen_recovery_fraction=args.oxygen_recovery,
        food_closure_fraction=args.food_closure,
    )
    budget = build_earth_mars_body_budget(dry_mass_kg=args.dry_mass_kg, crew_assumptions=assumptions)
    if args.json:
        print(json.dumps(budget.to_dict(), indent=2, sort_keys=True))
    else:
        _print_summary(budget)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
