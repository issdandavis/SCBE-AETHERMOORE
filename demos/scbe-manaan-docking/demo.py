#!/usr/bin/env python3
"""
SCBE Manaan Permeable Docking Demo (Python reference)

Mirrors the interactive HTML demo.
Implements the liquid plug physics + CA conlang command execution
with explicit honesty firewalls (emitted vs executed).

Run:
    python instrument-wt/demos/scbe-manaan-docking/demo.py

Ties the original space door concept to SCBE spaceflight + conlang macros.
"""

import math
from dataclasses import dataclass

RHO_AIR = 1.225
GAMMA_PFPE = 0.018
RHO_PFPE = 1900
MU_PFPE = 0.005

CA_OPS = {
    "bip'a": {"op": "add", "val": 1.0},
    "bip'i": {"op": "mul", "val": 2.0},
    "klik'ra": {"op": "clamp", "val": 10.0},
}

def choked_flux() -> float:
    return 236.0

def open_gap_loss(diameter_m: float, clearance_m: float = 0.002, transit_s: float = 3.5) -> float:
    perimeter = math.pi * diameter_m
    gap_area = perimeter * clearance_m
    return choked_flux() * gap_area * transit_s

def film_loss_g(trailing_r_m: float, speed_m_s: float) -> float:
    Ca = (MU_PFPE * speed_m_s) / GAMMA_PFPE
    h = 0.94 * trailing_r_m * (Ca ** (2/3))
    vol = 2 * math.pi * trailing_r_m * 0.4 * h * 0.12
    return vol * RHO_PFPE * 1000

def execute_conlang(cmd: str) -> dict:
    tokens = cmd.strip().lower().split()
    result = 0.0
    details = []
    status = "EXECUTED"

    for t in tokens:
        if t in CA_OPS:
            op = CA_OPS[t]
            if op["op"] == "add":
                result += op["val"]
            elif op["op"] == "mul":
                result = (result or 1.0) * op["val"]
            elif op["op"] == "clamp":
                result = min(result, op["val"])
            details.append(f"{t}→{op['op']}")
        else:
            status = "CLARIFY (unknown)"
            details.append(f"{t}→UNKNOWN")

    # Minimal phase grammar check (CA core token required)
    has_ca = any(t.startswith(("bip'", "klik'")) for t in tokens)
    if not has_ca and status == "EXECUTED":
        status = "REJECTED (no CA core)"

    return {
        "result": round(result, 2),
        "status": status,
        "paraphrase": " | ".join(details),
    }

def scbe_gate(film_g: float, open_kg: float, conlang: dict) -> dict:
    if "REJECTED" in conlang["status"] or "CLARIFY" in conlang["status"]:
        return {"decision": "QUARANTINE", "reason": "Conlang phase failure"}
    if open_kg > 0.5:
        return {"decision": "QUARANTINE", "reason": "Open gap loss too high"}
    if film_g > 50:
        return {"decision": "ALLOW (recover film)", "reason": "Recoverable"}
    return {"decision": "ALLOW", "reason": "Clean verified transit"}

def run_demo():
    print("SCBE Manaan Permeable Docking — Python reference")
    print("=" * 55)

    diam = 0.30
    speed = 0.8
    trail = 0.005
    time = 3.5

    open_kg = open_gap_loss(diam, transit_s=time)
    film_g = film_loss_g(trail, speed)
    cmd = "bip'a draum-sel"
    conlang = execute_conlang(cmd)
    gate = scbe_gate(film_g, open_kg, conlang)

    print(f"Drone diameter: {diam} m")
    print(f"Speed: {speed} m/s")
    print(f"Trailing radius: {trail*1000} mm")
    print()
    print(f"Open gas gap loss: {open_kg:.2f} kg")
    print(f"Liquid plug film (recoverable): {film_g:.1f} g")
    print(f"Conlang cmd '{cmd}' → {conlang['status']} ({conlang['result']})")
    print(f"SCBE Gate: {gate['decision']} — {gate['reason']}")
    print()
    print("HONESTY FIREWALL (in source):")
    print("  This emits to 8 faces (polyglot provenance).")
    print("  Only Python + Rust count as executed here.")
    print("  See conlang_macros_claim_manifest.json + scbe_spaceflight.py")
    print("  Emitted-to-8 ≠ executed-on-8")

if __name__ == "__main__":
    run_demo()