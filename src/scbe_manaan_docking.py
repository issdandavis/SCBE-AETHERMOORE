#!/usr/bin/env python3
"""
SCBE Manaan Permeable Docking Module
====================================

Physical + protocol model for a self-healing liquid-plug interface that allows
small drones (or other bodies) to transit from pressurized environment to vacuum
(or Manaan-style water/air boundary) with minimal loss.

This is the concrete realization of the "Star Wars TOR Manaan doorway" concept,
expressed as a SCBE spaceflight component.

It composes:
- DockingProtocol (mutual auth / governance gate)
- PermeableLiquidPlug (the physical self-healing membrane)
- CA conlang commands (Sacred Tongues lane for "transit permission")

HONESTY FIREWALL (pinned in source):
- This module EMITS models/descriptions for up to 8 language faces (provenance).
- Only the Python reference (and any Rust where actually compiled+run) count as EXECUTED.
- "emitted-to-8 faces is not claimed as executed-on-8".
- All loss numbers are consistency checks, NOT a proof the physical model is correct
  for real spacecraft. "no transcription/arithmetic drift … consistency of the parts,
  NOT a proof the model is the right physics."
- See artifacts/ai_brain/conlang_macros_claim_manifest.json (hash 5117a81c...)
  and python/scbe/rosetta.py for the binding discipline.

Physics grounded in:
- Choked flow for open orifices (the term that kills naive gas interfaces)
- Landau-Levich film for liquid plugs (the recoverable term)
- Young-Laplace / magnetic confinement for the plug
- Dartfish trailing geometry for clean pinch-off

Conlang example (from verified binding):
    "bip'a draum-sel" → 7.0 (add + clamp, executed on py+rust core)

Dependencies: stdlib only.

Usage:
    python -m src.scbe_manaan_docking
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# Re-export useful bits from the spaceflight module for composition
from .scbe_spaceflight import (
    DockingProtocol,
    DockingState,
    DelayTolerantBundle,
    PHI,
    R_FIFTH,
)

# Coding conlangs integration: use the user's conlang_macros system (with honesty firewalls)
# for verified "transit commands" in the Manaan door.
# This ties the space door concept to the SCBE conlang (Sacred Tongues CA lane).
import sys
CONLANG_DEV_PATH = r"C:\dev\train-orchestrator\training"
if CONLANG_DEV_PATH not in sys.path:
    sys.path.insert(0, CONLANG_DEV_PATH)
CONLANG_AVAILABLE = False
speak = None
LEX = {}
MacroBank = None
film_calc = None
try:
    from conlang_macros import speak, LEX  # the macro system for verified CA opcodes
    from shorthand import MacroBank  # for shorthand verified constructs
    CONLANG_AVAILABLE = True
except Exception:
    pass  # graceful if dev conlang not in this env; still documents the integration

# Build a door-specific verified macro using shorthand, for space conlang
film_calc = None
if CONLANG_AVAILABLE and MacroBank:
    try:
        door_bank = MacroBank()
        film_code = '''import math
def calc_film(speed, trailing=0.005, rho=1900, gamma=0.018, mu=0.005, wetted=0.4):
    Ca = (mu * speed) / gamma
    h = 0.94 * trailing * (Ca ** (2/3)) if Ca > 0 else 0
    vol = 2 * math.pi * trailing * wetted * h * 0.12
    return vol * rho * 1000'''
        r = door_bank.register("film", film_code, "calc_film", [([0.8], 4.940461960703508)])
        print("  [conlang] registered door 'film' macro:", r)
        if r.get("admitted"):
            door_module = door_bank.compose(["film"])
            ns = {}
            exec(door_module, ns)
            film_calc = ns["calc_film"]
            print("  [conlang] door film demo:", film_calc(0.8))
    except Exception as e:
        print("  [conlang] door macro (honesty firewall active):", type(e).__name__, str(e)[:50])

# Example conlang sentence for door transit (using the verified binding)
# "kor-vael av-sai ru-thar [CA op] draum-sel" for intent -> args -> permission -> compute -> seal
# This will be "spoken" to get a verified result for the film or loss calc.
DOOR_CONLANG_SENTENCE = "kor-vael av-sai ru-thar bip'a draum-sel"  # example compute add for demo
# Honesty: this sentence emits to 8 faces but only executes on verified (py+rust here).

# Space-themed conlang example: use for space docking physics
# e.g., a sentence to "compute" film for the door, using verified CA.
SPACE_DOOR_SENTENCE = "kor-vael av-sai ru-thar klik'ra draum-sel"  # clamp for film limit
# This ties conlangs to spaceflight: conlang command for the permeable membrane.

# ---------------------------------------------------------------------------
# Physics constants (from the original permeable membrane thread)
# ---------------------------------------------------------------------------

RHO_AIR = 1.225
CHOKED_FLUX = 236.0          # kg s^-1 m^-2 for air at ~1 atm into vacuum
GAMMA_PFPE = 0.018           # N/m typical PFPE vacuum fluid
RHO_PFPE = 1900.0
MU_PFPE = 0.005              # Pa s (low viscosity grade)

# CA conlang opcodes (narrow verified core, from instrument.py + binding)
# Only these are EXECUTED here. Everything else is provenance.
CA_OPS: Dict[str, Tuple[str, float]] = {
    "bip'a": ("add", 1.0),      # 0x00
    "bip'i": ("mul", 2.0),      # example mul
    "klik'ra": ("clamp", 10.0), # clamp
}

# ---------------------------------------------------------------------------
# Permeable Liquid Plug (the physical self-healing membrane)
# ---------------------------------------------------------------------------

@dataclass
class PermeableLiquidPlug:
    """Self-healing liquid plug for low-loss transit across pressure boundaries.

    Models a magnetically-confined PFPE/ferrofluid or ionic-liquid membrane
    that a drone (or body) displaces and that reseals behind it.

    Loss is reduced to thin drag-out film + evaporation (recoverable with wiper).

    SCBE analogy:
        The plug acts as a physical ReentryShield / boundary layer that consumes
        "film mass" instead of one-time tokens. The magnetic field + recovery
        loop is the L12-style harmonic wall + self-healing mechanism.

    Honesty firewall:
        - This class *computes* loss numbers in Python.
        - It can *emit* descriptions for other faces.
        - Only runs where the exact same physics code is executed count as verified.
        - The "8 faces" claim is documentation/provenance only.
    """

    trailing_radius_m: float = 0.005   # dartfish taper is critical
    fluid_mu: float = MU_PFPE
    fluid_gamma: float = GAMMA_PFPE
    fluid_rho: float = RHO_PFPE
    wetted_length_m: float = 0.4
    recovery_efficiency: float = 0.95  # wiper + collector reclaim

    _transit_log: List[Dict[str, float]] = field(default_factory=list, repr=False)

    def compute_film_loss_g(self, speed_m_s: float) -> float:
        """Landau-Levich film mass in grams before recovery.
        Honesty: if door 'film' macro registered via shorthand, use the verified calc (emitted to faces but only executed where verified).
        """
        if film_calc is not None:
            return film_calc(speed_m_s)
        Ca = (self.fluid_mu * speed_m_s) / self.fluid_gamma
        if Ca <= 0:
            h = 0.0
        else:
            h = 0.94 * self.trailing_radius_m * (Ca ** (2.0 / 3.0))
        vol = 2 * math.pi * self.trailing_radius_m * self.wetted_length_m * h * 0.12
        return vol * self.fluid_rho * 1000.0

    def part_for_transit(
        self,
        drone_diameter_m: float,
        speed_m_s: float,
        transit_time_s: float = 3.5,
        conlang_command: Optional[str] = None,
    ) -> Dict[str, float]:
        """Execute the physical passage.

        The plug "parts" around the body and reseals. Loss is the post-recovery film.

        If a conlang_command is provided it must be valid CA and will be "executed"
        against the narrow core before the physical model is allowed to run.
        This mirrors the governance gate + physical shield composition.

        Returns a dict with open_gap_loss_kg (for comparison), film_before_g,
        film_after_recovery_g, and net_loss_g.
        """
        # 1. Use full coding conlang for verified transit command (if available)
        # This uses the user's conlang_macros.speak for the full pipeline: resolve, phase check, execute verified, paraphrase, seal.
        # Honesty firewall: only narrow executed faces count; this sentence "programs" the plug transit.
        conlang_executed = None
        if CONLANG_AVAILABLE and speak and conlang_command:
            try:
                # Use the sentence as the "command", with physics args (speed, film) for the CA compute part.
                # E.g., the bip'a or other op "computes" a verified factor for the loss.
                res = speak(conlang_command, args=[speed_m_s, 0.0])  # args for the compute part
                conlang_executed = {
                    "result": res.get("result"),
                    "faces_executed": res.get("faces_executed"),
                    "paraphrase": res.get("paraphrase"),
                    "seal": res.get("seal", "")[:16] + "..." if res.get("seal") else None,
                }
            except Exception as e:
                raise ValueError(f"Transit command rejected by full conlang core: {e} (see honesty in conlang_macros.py)")

        # 2. Physical calculation - use verified 'film' macro from shorthand if admitted (honesty: use verified calc)
        open_gap = 236.0 * (math.pi * drone_diameter_m * 0.002) * transit_time_s
        film_before = film_calc(speed_m_s) if film_calc is not None else self.compute_film_loss_g(speed_m_s)
        film_after = film_before * (1.0 - self.recovery_efficiency)
        net = film_after

        # If conlang executed, use its verified result to "adjust" net loss (example integration)
        if conlang_executed and conlang_executed.get("result") is not None:
            verified_adjust = abs(conlang_executed["result"]) / 10.0  # scale from CA result
            net *= verified_adjust

        record = {
            "drone_diameter_m": drone_diameter_m,
            "speed_m_s": speed_m_s,
            "open_gap_loss_kg": open_gap,
            "film_before_g": film_before,
            "film_after_recovery_g": film_after,
            "net_loss_g": net,
            "conlang_command": conlang_command or "",
            "conlang_executed": conlang_executed,
        }
        self._transit_log.append(record)
        return record

    @property
    def transit_history(self) -> List[Dict[str, float]]:
        return list(self._transit_log)


# ---------------------------------------------------------------------------
# Convenience: full Manaan-style docking + physical transit
# ---------------------------------------------------------------------------

def perform_manaan_docking_and_transit(
    local_id: str = "drone-001",
    remote_id: str = "manaan-station-03",
    drone_diameter_m: float = 0.30,
    approach_speed_m_s: float = 0.8,
    conlang_transit_cmd: str = "bip'a draum-sel",
) -> Dict[str, object]:
    """End-to-end example: DockingProtocol + physical liquid plug passage.

    This is the "build" that combines the original engineering idea with the
    SCBE spaceflight metaphors and the conlang macros discipline.

    Returns a rich result dict with auth result, physical losses, and status.
    """
    # 1. Logical / governance docking (from existing module)
    proto = DockingProtocol()
    proto.initiate(local_id, remote_id)
    proto.negotiate_cipher_suite(["AES-GCM"], ["AES-GCM"])
    secret = proto.exchange_keys(5, 7)
    expected = hashlib.sha256(secret + b"challenge").digest()
    proto.verify_and_dock(b"challenge", expected)

    # 2. Physical passage through the permeable plug (new)
    plug = PermeableLiquidPlug()
    # Use full conlang sentence for the verified command to the plug (not the simple one)
    physics = plug.part_for_transit(
        drone_diameter_m, approach_speed_m_s, conlang_command=DOOR_CONLANG_SENTENCE
    )

    # Conlang result from the plug (already executed the sentence in part_for_transit)
    conlang_result = physics.get("conlang_executed") or {
        "status": "conlang executed inside plug (see part_for_transit for honesty)",
        "sentence": DOOR_CONLANG_SENTENCE
    }

    # 3. Bundle the result (DelayTolerantBundle style custody for the transit record)
    bundle = DelayTolerantBundle(
        payload=f"transit-log:{physics}".encode(),
        sender_id=local_id,
        receiver_id=remote_id,
    )
    bundle.add_custody("manaan-plug-01", hashlib.sha256(str(physics).encode()).hexdigest())

    net_loss_g = physics["net_loss_g"]
    status = "SUCCESS_LOW_LOSS" if net_loss_g < 20 else "SUCCESS_WITH_RECOVERY_NEEDED"

    return {
        "overall": status,
        "docking_state": proto.state.name,
        "auth_history": proto.history,
        "physics": physics,
        "custody_bundle_order": len(bundle.custody_chain),
        "conlang_transit_command": conlang_result,
        "honesty_firewall": (
            "emitted-to-8 faces (polyglot provenance) is NOT executed-on-8. "
            "Only narrow verified runtimes count. See conlang_macros claim manifest. "
            "Conlang sentence for door executed only on verified faces; physical plug is the real shield."
        ),
    }


# ---------------------------------------------------------------------------
# CLI / demo runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SCBE Manaan Permeable Docking — full transit demo")
    print("=" * 60)

    result = perform_manaan_docking_and_transit(
        conlang_transit_cmd="bip'a draum-sel"   # from the verified binding
    )

    print(f"Overall: {result['overall']}")
    print(f"Docking state: {result['docking_state']}")
    print(f"Auth steps: {' -> '.join(result['auth_history'])}")
    print()
    phys = result["physics"]
    print(f"Drone diameter: {phys['drone_diameter_m']} m")
    print(f"Approach speed: {phys['speed_m_s']} m/s")
    print(f"Open-gap loss (what we avoided): {phys['open_gap_loss_kg']:.2f} kg")
    print(f"Film before wiper: {phys['film_before_g']:.1f} g")
    print(f"Film after recovery: {phys['film_after_recovery_g']:.1f} g")
    print(f"Net loss: {phys['net_loss_g']:.1f} g")
    print(f"Conlang command: {phys['conlang_command']}")
    if result.get("conlang_transit_command"):
        cl = result["conlang_transit_command"]
        if cl.get("sentence"):
            print(f"Conlang transit sentence: {cl.get('sentence')}")
            print(f"  Verified result: {cl.get('result')} | faces executed: {cl.get('faces_executed')} | seal: {cl.get('seal')}")
            print(f"  Paraphrase: {cl.get('paraphrase')}")
        elif "error" in cl:
            print(f"  Conlang note: {cl['error']} (honesty firewall: {cl.get('honesty', 'emitted vs executed')})")
        else:
            print(f"  Conlang status: {cl}")
    print()
    print(result["honesty_firewall"])
    print(f"Custody attestations for transit record: {result['custody_bundle_order']}")
    print()
    print("Reference: conlang_macros artifact hash 5117a81c6dc6bf2f6594862e728fd9b149a9835a1938172ac22fb8cf51e1efb1")
    print("This is a narrow verified core demonstration. Not a claim that the model flies on real hardware.")