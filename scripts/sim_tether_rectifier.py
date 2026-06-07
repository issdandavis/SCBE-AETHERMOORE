#!/usr/bin/env python3
"""1D tether rectifier desk simulation — finger-trap tension, eddy brake proxy, Strandbeest torque.

Outputs telemetry suitable for src/harmonic/tetherTelemetry.ts ingestion.

Usage:
    python scripts/sim_tether_rectifier.py --steps 500
    python scripts/sim_tether_rectifier.py --stream --interval-ms 100
    python scripts/sim_tether_rectifier.py --stream --serve 8765
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.physics_sim.orbital import (
    MU_EARTH,
    RADIUS_EARTH,
    circular_velocity,
)  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "research" / "tether_sim"


def nonreciprocal_grip_lift_torque(
    y: list[float],
    v: list[float],
    *,
    dx: float,
    gain: float,
    orientation_sign: float = 1.0,
    grip_gain: float = 6.0,
) -> float:
    """Continuous directional rectifier proxy with no velocity sign bias.

    The model is intentionally small:
    - curvature magnitude opens the "grip" gate,
    - slope * lateral velocity is the signed lift/shear flux,
    - linkage orientation flips the output direction.

    It is a reduced bench mechanism, not a Jansen linkage solver. It is not
    magnetic-field odd; B-linear force belongs to the electrodynamic tether
    terms, not this mechanical proxy.
    """
    if len(y) != len(v):
        raise ValueError("y and v must have the same length")
    if len(y) < 3:
        return 0.0
    if dx <= 0:
        raise ValueError("dx must be positive")
    if orientation_sign == 0.0:
        return 0.0

    direction = math.copysign(1.0, orientation_sign)
    rectified = 0.0
    for i in range(1, len(y) - 1):
        slope = (y[i + 1] - y[i - 1]) / (2.0 * dx)
        curvature = (y[i + 1] - 2.0 * y[i] + y[i - 1]) / (dx * dx)
        grip = math.tanh(grip_gain * abs(curvature) * dx)
        rectified += grip * slope * v[i]
    return gain * direction * rectified / max(len(y) - 2, 1)


def electrodynamic_tether_terms(
    *,
    orbital_speed_m_s: float,
    b_field_t: float,
    tether_length_m: float,
    current_a: float,
    tether_mass_kg: float,
) -> dict[str, float]:
    """Signed and magnitude EDT terms for the simplified perpendicular case."""
    if tether_length_m <= 0:
        raise ValueError("tether_length_m must be positive")
    if tether_mass_kg <= 0:
        raise ValueError("tether_mass_kg must be positive")

    motional_emf_signed_v = orbital_speed_m_s * b_field_t * tether_length_m
    lorentz_force_signed_n = current_a * tether_length_m * b_field_t
    return {
        "motional_emf_signed_v": motional_emf_signed_v,
        "lorentz_force_signed_n": lorentz_force_signed_n,
        "specific_lorentz_force_signed_m_s2": lorentz_force_signed_n / tether_mass_kg,
        "motional_emf_v": abs(motional_emf_signed_v),
        "lorentz_force_n": abs(lorentz_force_signed_n),
        "specific_lorentz_force_m_s2": abs(lorentz_force_signed_n) / tether_mass_kg,
    }


@dataclass
class SimParams:
    n_nodes: int = 64
    length_m: float = 1.0
    dt: float = 0.00025
    tension_n: float = 40.0
    linear_density: float = 0.5
    finger_trap_gain: float = 8.0
    eddy_gain: float = 4.0
    strandbeest_gain: float = 0.35
    b_field_t: float = 25e-6
    orbital_speed: float = 7800.0
    current_a: float = 0.0
    orbit_altitude_m: float | None = None
    # Hybrid ferro-fluid harmonic drive (phenomenological)
    harmonic_enabled: bool = False
    harmonic_freq_hz: tuple[float, ...] = (12.0, 48.0, 120.0)
    harmonic_amp_t: tuple[float, ...] = (8e-6, 3e-6, 1e-6)
    ferro_viscosity_gain: float = 5.0e9  # desk scale: eta ~ 1..6 at ~10–30 uT RMS


class TetherRectifierSim:
    """Semi-implicit 1D wave with phenomenological tether sub-models."""

    def __init__(self, p: SimParams | None = None) -> None:
        self.p = p or SimParams()
        self.dx = self.p.length_m / max(self.p.n_nodes - 1, 1)
        self.y = [0.0] * self.p.n_nodes
        self.v = [0.0] * self.p.n_nodes
        self._inner_v = [0.0] * self.p.n_nodes
        self._flux_drift = 0.0
        self._torque_accum = 0.0
        self.t = 0.0
        self._step = 0

    def _axial_strain(self) -> float:
        s = 0.0
        for i in range(1, self.p.n_nodes):
            s += abs(self.y[i] - self.y[i - 1]) / self.dx
        return s / max(self.p.n_nodes - 1, 1)

    def _finger_trap_damping(self, strain: float) -> float:
        """Radial grip proxy: higher strain -> higher effective damping."""
        return 1.0 + self.p.finger_trap_gain * math.tanh(strain * 12.0)

    def _eddy_force(self, i: int) -> float:
        """Lenz-style coupling between outer (v) and inner sheath (inner_v)."""
        rel = self.v[i] - self._inner_v[i]
        return -self.p.eddy_gain * rel

    def _strandbeest_torque(self) -> float:
        """Rectify coherent lateral shear into a signed torque proxy."""
        t_spin = nonreciprocal_grip_lift_torque(
            self.y,
            self.v,
            dx=self.dx,
            gain=self.p.strandbeest_gain,
            orientation_sign=1.0,
        )
        self._torque_accum = 0.95 * self._torque_accum + 0.05 * t_spin
        return self._torque_accum

    def _harmonic_b_total(self) -> tuple[float, float]:
        """Return (B_total, B_rms) in tesla for current time."""
        if not self.p.harmonic_enabled:
            return self.p.b_field_t, self.p.b_field_t
        b = self.p.b_field_t
        sq = self.p.b_field_t**2
        n = max(len(self.p.harmonic_freq_hz), 1)
        for f_k, a_k in zip(
            self.p.harmonic_freq_hz, self.p.harmonic_amp_t, strict=False
        ):
            b += a_k * math.sin(2.0 * math.pi * f_k * self.t)
            sq += 0.5 * (a_k**2)
        rms = math.sqrt(sq / n)
        return b, rms

    def _ferro_viscosity_proxy(self, b_rms: float) -> float:
        """eta_eff / eta_0 ~ 1 + gain * |B|^2 (scaled for desk units)."""
        return 1.0 + self.p.ferro_viscosity_gain * (b_rms**2)

    def _magnetic_flux_drift(self, strain: float, b_total: float) -> float:
        """Crude motional-flux drift: B * v_orbit * strain coupling."""
        emf = b_total * self.p.orbital_speed * strain * self.dx
        self._flux_drift = 0.98 * self._flux_drift + 0.02 * emf
        return self._flux_drift

    def _orbit_aware_telemetry(self, b_total: float) -> dict[str, Any]:
        """Order-of-magnitude electrodynamic tether terms.

        Assumptions are deliberately visible:
        - circular Earth orbit,
        - uniform magnetic field over the tether,
        - tether, orbital velocity, and B-field are mutually perpendicular.

        These are real equations (`emf = vBL`, `F = ILB`) but not a full
        ionospheric plasma/current-collection model.
        """
        if self.p.orbit_altitude_m is None:
            return {}

        length_m = self.p.length_m
        tether_mass_kg = self.p.linear_density * length_m
        terms = electrodynamic_tether_terms(
            orbital_speed_m_s=self.p.orbital_speed,
            b_field_t=b_total,
            tether_length_m=length_m,
            current_a=self.p.current_a,
            tether_mass_kg=tether_mass_kg,
        )
        return {
            "orbit_model": "leo_uniform_perpendicular_field_order_of_magnitude",
            "orbit_altitude_m": round(self.p.orbit_altitude_m, 3),
            "orbital_speed_m_s": round(self.p.orbital_speed, 6),
            "tether_length_m": round(length_m, 6),
            "tether_mass_kg": round(tether_mass_kg, 6),
            "current_a": round(self.p.current_a, 6),
            "motional_emf_v": round(terms["motional_emf_v"], 8),
            "motional_emf_signed_v": round(terms["motional_emf_signed_v"], 8),
            "lorentz_force_n": round(terms["lorentz_force_n"], 8),
            "lorentz_force_signed_n": round(terms["lorentz_force_signed_n"], 8),
            "specific_lorentz_force_m_s2": round(
                terms["specific_lorentz_force_m_s2"], 12
            ),
            "specific_lorentz_force_signed_m_s2": round(
                terms["specific_lorentz_force_signed_m_s2"], 12
            ),
        }

    def excite(self, amp: float = 0.002, freq_hz: float = 3.0) -> None:
        mid = self.p.n_nodes // 2
        self.v[mid] += amp * math.cos(2.0 * math.pi * freq_hz * self.t)

    def step_once(self, *, impulse: bool = False) -> dict[str, Any]:
        if impulse and self._step % 80 == 0:
            self.excite(amp=0.008, freq_hz=2.0 + 0.05 * (self._step % 20))

        strain = self._axial_strain()
        b_total, b_rms = self._harmonic_b_total()
        ferro_eta = self._ferro_viscosity_proxy(b_rms)
        c_eff = self._finger_trap_damping(strain) * min(ferro_eta, 6.0)
        flux = self._magnetic_flux_drift(strain, b_total)

        c_wave = self.p.tension_n / max(self.p.linear_density, 1e-9)
        c2 = min(c_wave / (self.dx * self.dx), 2.5e4)

        y_new = list(self.y)
        v_new = list(self.v)

        for i in range(1, self.p.n_nodes - 1):
            lap = self.y[i + 1] - 2.0 * self.y[i] + self.y[i - 1]
            f_eddy = self._eddy_force(i)
            a = c2 * lap - (c_eff * 2.0) * self.v[i] + f_eddy
            v_new[i] = self.v[i] + self.p.dt * a
            y_new[i] = self.y[i] + self.p.dt * v_new[i]
            self._inner_v[i] += 0.15 * (self.v[i] - self._inner_v[i])

        y_new[0] = y_new[-1] = 0.0
        v_new[0] = v_new[-1] = 0.0
        cap = 0.05
        for i in range(self.p.n_nodes):
            y_new[i] = max(-cap, min(cap, y_new[i]))
            v_new[i] = max(-cap, min(cap, v_new[i]))
        self.y = y_new
        self.v = v_new
        self.t += self.p.dt
        self._step += 1

        vib = max(abs(v) for v in self.y)
        torque = self._strandbeest_torque()

        frame: dict[str, Any] = {
            "ts_ms": int(time.time() * 1000),
            "sim_time_s": round(self.t, 6),
            "step": self._step,
            "vibration_amplitude": round(vib, 8),
            "tension_strain": round(strain, 8),
            "magnetic_flux_drift": round(flux, 8),
            "rectified_torque": round(torque, 8),
        }
        frame.update(self._orbit_aware_telemetry(b_total))
        if self.p.harmonic_enabled:
            frame["harmonic_field_rms"] = round(b_rms, 10)
            frame["ferro_viscosity_proxy"] = round(ferro_eta, 4)
            frame["ferro_damping_factor"] = round(min(ferro_eta, 6.0), 4)
        return frame

    def run(self, steps: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for _ in range(steps):
            out.append(self.step_once(impulse=True))
        return out


def write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def stream_loop(
    sim: TetherRectifierSim,
    *,
    interval_s: float,
    jsonl_path: Path | None,
    snapshot_path: Path,
    max_steps: int | None,
) -> None:
    steps = 0
    while max_steps is None or steps < max_steps:
        frame = sim.step_once(impulse=True)
        write_snapshot(snapshot_path, frame)
        if jsonl_path:
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(frame) + "\n")
        print(json.dumps(frame), flush=True)
        steps += 1
        time.sleep(interval_s)


def make_handler(snapshot_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/latest", "/latest.json"):
                self.send_response(404)
                self.end_headers()
                return
            body = (
                snapshot_path.read_text(encoding="utf-8")
                if snapshot_path.is_file()
                else "{}"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--steps", type=int, default=500, help="Batch steps (non-stream mode)"
    )
    parser.add_argument(
        "--stream", action="store_true", help="Emit JSON every interval"
    )
    parser.add_argument("--interval-ms", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=None, help="Cap stream steps")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--serve", type=int, default=0, help="HTTP port for latest.json (with --stream)"
    )
    parser.add_argument(
        "--orbit-aware",
        action="store_true",
        help="Emit vBL and ILB order-of-magnitude terms",
    )
    parser.add_argument(
        "--orbit-altitude-m",
        type=float,
        default=400_000.0,
        help="Circular Earth orbit altitude",
    )
    parser.add_argument(
        "--tether-length-m",
        type=float,
        default=None,
        help="Override SimParams.length_m",
    )
    parser.add_argument(
        "--line-density-kg-m",
        type=float,
        default=None,
        help="Override SimParams.linear_density",
    )
    parser.add_argument(
        "--current-a",
        type=float,
        default=0.0,
        help="Current through tether for ILB force",
    )
    parser.add_argument(
        "--b-field-t", type=float, default=None, help="Uniform B-field magnitude"
    )
    parser.add_argument(
        "--harmonic",
        action="store_true",
        help="Superpose multi-frequency B(t); emit harmonic_field_rms and ferro_viscosity_proxy",
    )
    args = parser.parse_args()

    snapshot = args.out_dir / "latest.json"
    jsonl = args.out_dir / "stream.jsonl"
    altitude = args.orbit_altitude_m if args.orbit_aware else None
    orbital_speed = (
        circular_velocity(RADIUS_EARTH + args.orbit_altitude_m, MU_EARTH)
        if args.orbit_aware
        else SimParams.orbital_speed
    )
    params = SimParams(
        length_m=(
            args.tether_length_m
            if args.tether_length_m is not None
            else SimParams.length_m
        ),
        linear_density=(
            args.line_density_kg_m
            if args.line_density_kg_m is not None
            else SimParams.linear_density
        ),
        b_field_t=args.b_field_t if args.b_field_t is not None else SimParams.b_field_t,
        orbital_speed=orbital_speed,
        current_a=args.current_a,
        orbit_altitude_m=altitude,
        harmonic_enabled=args.harmonic,
    )
    sim = TetherRectifierSim(params)

    if args.stream:
        if args.serve:
            import threading

            def run_sim() -> None:
                stream_loop(
                    sim,
                    interval_s=args.interval_ms / 1000.0,
                    jsonl_path=jsonl,
                    snapshot_path=snapshot,
                    max_steps=args.max_steps,
                )

            threading.Thread(target=run_sim, daemon=True).start()
            print(
                f"Serving {snapshot} on http://127.0.0.1:{args.serve}/latest.json",
                flush=True,
            )
            HTTPServer(
                ("127.0.0.1", args.serve), make_handler(snapshot)
            ).serve_forever()
        stream_loop(
            sim,
            interval_s=args.interval_ms / 1000.0,
            jsonl_path=jsonl,
            snapshot_path=snapshot,
            max_steps=args.max_steps,
        )
        return 0

    frames = sim.run(args.steps)
    write_snapshot(snapshot, frames[-1])
    summary = args.out_dir / "batch_summary.json"
    summary.write_text(
        json.dumps({"frames": len(frames), "last": frames[-1]}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(frames[-1], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
