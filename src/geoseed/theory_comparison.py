"""
@file theory_comparison.py
@module geoseed/theory_comparison
@component ElectronTheoryComparison

Models the Compton oscillation as the orbital frequency and compares
the resulting energy/frequency predictions against five other theoretical
framings across the 6 GeoSeed shell positions.

Theories implemented:
  1. compton_orbital  — Zitterbewegung freq IS orbital freq (Hestenes)
  2. bohr             — Hydrogen Bohr model (1/n²), n = shell+1
  3. de_broglie       — Standing wave: n wavelengths in circumference
  4. geoseed_lb       — Laplace-Beltrami eigenvalue ladder -(l+1)²
  5. harmonic         — QM harmonic oscillator (ℏω per shell step)
  6. pilot_wave       — Bohm quantum potential energy on GeoSeed shells

Each theory returns a TheoryResult: energy (eV) and frequency (Hz)
per shell, plus a residual vs measured hydrogen levels.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict

# ── Physical constants ────────────────────────────────────────────────────────

PHI         = (1.0 + math.sqrt(5.0)) / 2.0
HBAR        = 1.054571817e-34   # J·s
H_PLANCK    = 6.62607015e-34    # J·s
M_ELECTRON  = 9.1093837015e-31  # kg
C_LIGHT     = 2.99792458e8      # m/s
EV          = 1.602176634e-19   # J per eV
RYDBERG_EV  = 13.605693122994   # eV  (hydrogen ground state binding energy)
ALPHA       = 7.2973525693e-3   # fine-structure constant
A0          = 5.29177210903e-11 # Bohr radius (m)

# Derived
COMPTON_WAVELENGTH  = H_PLANCK / (M_ELECTRON * C_LIGHT)   # ≈ 2.426e-12 m
COMPTON_FREQUENCY   = M_ELECTRON * C_LIGHT**2 / H_PLANCK  # ≈ 1.236e20 Hz
COMPTON_ENERGY_EV   = M_ELECTRON * C_LIGHT**2 / EV        # ≈ 511 keV

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Measured hydrogen binding energies (eV) for n = 1..6
# (positive = energy to remove electron)
HYDROGEN_MEASURED_EV = [
    RYDBERG_EV / (n**2)
    for n in range(1, 7)
]


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ShellPrediction:
    shell_index: int
    tongue: str
    energy_ev: float        # binding energy magnitude (eV)
    frequency_hz: float     # characteristic frequency (Hz)
    orbital_radius_m: float # implied orbital radius (m)


@dataclass
class TheoryResult:
    name: str
    description: str
    shells: List[ShellPrediction]
    residuals_ev: List[float]       # theory - hydrogen_measured (eV per shell)
    rms_residual_ev: float          # root-mean-square residual
    note: str = ""

    def energies_ev(self) -> List[float]:
        return [s.energy_ev for s in self.shells]

    def frequencies_hz(self) -> List[float]:
        return [s.frequency_hz for s in self.shells]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "rms_residual_ev": round(self.rms_residual_ev, 6),
            "note": self.note,
            "shells": [
                {
                    "tongue": s.tongue,
                    "shell": s.shell_index,
                    "energy_ev": round(s.energy_ev, 6),
                    "frequency_hz": s.frequency_hz,
                    "orbital_radius_m": s.orbital_radius_m,
                    "residual_ev": round(self.residuals_ev[s.shell_index], 6),
                    "hydrogen_measured_ev": round(HYDROGEN_MEASURED_EV[s.shell_index], 6),
                }
                for s in self.shells
            ],
        }


# ── Theory implementations ────────────────────────────────────────────────────

def _make_result(name: str, description: str,
                 energies_ev: List[float],
                 frequencies_hz: List[float],
                 radii_m: List[float],
                 note: str = "") -> TheoryResult:
    shells = [
        ShellPrediction(
            shell_index=i,
            tongue=TONGUE_ORDER[i],
            energy_ev=energies_ev[i],
            frequency_hz=frequencies_hz[i],
            orbital_radius_m=radii_m[i],
        )
        for i in range(6)
    ]
    residuals = [energies_ev[i] - HYDROGEN_MEASURED_EV[i] for i in range(6)]
    rms = math.sqrt(sum(r**2 for r in residuals) / 6)
    return TheoryResult(name=name, description=description,
                        shells=shells, residuals_ev=residuals,
                        rms_residual_ev=rms, note=note)


def theory_compton_orbital() -> TheoryResult:
    """
    Zitterbewegung / Hestenes: Compton oscillation IS the orbital frequency.

    Hypothesis: the electron's internal trembling at f_C sets the base
    orbital frequency.  Each GeoSeed shell is a phi-scaled subharmonic:
      f_n = f_C / φⁿ
      E_n = h · f_n = E_C / φⁿ   (in eV)

    Then normalise to the Rydberg scale so the ground shell matches
    hydrogen n=1 (the GeoSeed geometry sets the SHAPE; we anchor the
    energy scale at the measured ground-state value to compare slopes).
    """
    scale = RYDBERG_EV  # anchor KO (n=0) to hydrogen n=1
    energies, freqs, radii = [], [], []
    for n in range(6):
        e_ev = scale / (PHI**n)
        f_hz = COMPTON_FREQUENCY / (PHI**n)
        # r = c / (2π f)  — wavelength/2π of the oscillation
        r_m = C_LIGHT / (2 * math.pi * f_hz)
        energies.append(e_ev)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "compton_orbital",
        "Compton oscillation as orbital frequency (phi-scaled subharmonics)",
        energies, freqs, radii,
        note=(
            f"Base: f_C={COMPTON_FREQUENCY:.4e} Hz, E_C={COMPTON_ENERGY_EV:.1f} keV. "
            "Energy normalised to Rydberg at KO shell."
        ),
    )


def theory_bohr() -> TheoryResult:
    """
    Bohr model: E_n = -13.6 eV / n²,  n = shell_index + 1.
    The reference model — measured hydrogen levels.
    """
    energies, freqs, radii = [], [], []
    for n in range(1, 7):
        e_ev = RYDBERG_EV / (n**2)
        # Orbital frequency: f = v / (2π r),  v = α·c/n,  r = a₀·n²
        v = ALPHA * C_LIGHT / n
        r_m = A0 * n**2
        f_hz = v / (2 * math.pi * r_m)
        energies.append(e_ev)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "bohr",
        "Bohr hydrogen model: E = 13.6/n²  (n = shell+1)",
        energies, freqs, radii,
        note="Residual is zero by definition — this is the reference.",
    )


def theory_de_broglie() -> TheoryResult:
    """
    de Broglie standing wave: n full wavelengths fit in the orbital circumference.
      λ_n = 2π r_n / n   →   p = h/λ   →   E = p²/2m
    Radius r_n taken from GeoSeed Poincaré positions scaled to Bohr units.
    """
    # Scale: set n=0 shell to Bohr radius a₀
    poincare_rs = [math.tanh(n * math.log(PHI) / 2) for n in range(6)]
    # Rescale so that n=1 shell matches a₀
    scale = A0 / poincare_rs[1] if poincare_rs[1] > 0 else A0
    energies, freqs, radii = [], [], []
    for n in range(6):
        r_m = poincare_rs[n] * scale if n > 0 else A0 * 0.01
        shell_n = n + 1
        wavelength = 2 * math.pi * r_m / shell_n
        p = H_PLANCK / wavelength
        e_j = p**2 / (2 * M_ELECTRON)
        e_ev = e_j / EV
        f_hz = e_j / H_PLANCK
        energies.append(e_ev)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "de_broglie",
        "de Broglie standing wave on GeoSeed phi-radii (n wavelengths/orbit)",
        energies, freqs, radii,
        note="GeoSeed Poincaré radii rescaled to physical units at Bohr radius.",
    )


def theory_geoseed_lb() -> TheoryResult:
    """
    GeoSeed Laplace-Beltrami ladder: |λ_l| = (l+1)² = 1,4,9,16,25,36.
    Normalise so shell 0 (KO, l=0) = Rydberg energy.
    """
    lam = [(l + 1)**2 for l in range(6)]
    scale = RYDBERG_EV / lam[0]
    energies, freqs, radii = [], [], []
    for l in range(6):
        e_ev = scale * lam[l]
        f_hz = e_ev * EV / H_PLANCK
        r_m = HBAR / math.sqrt(2 * M_ELECTRON * e_ev * EV) if e_ev > 0 else 0.0
        energies.append(e_ev)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "geoseed_lb",
        "GeoSeed Laplace-Beltrami eigenvalues: E ∝ (l+1)²",
        energies, freqs, radii,
        note="LB ladder grows as perfect squares — steeper than Bohr (1/n²).",
    )


def theory_harmonic() -> TheoryResult:
    """
    Quantum harmonic oscillator: E_n = (n + ½)·ℏω_C.
    Each GeoSeed shell is one rung of the Compton-frequency ladder.
    """
    omega_c = 2 * math.pi * COMPTON_FREQUENCY
    energies, freqs, radii = [], [], []
    for n in range(6):
        e_j = (n + 0.5) * HBAR * omega_c
        e_ev = e_j / EV
        # Normalise to Rydberg scale
        e_ev_norm = e_ev * (RYDBERG_EV / ((0.5) * HBAR * omega_c / EV))
        f_hz = COMPTON_FREQUENCY * (n + 0.5)
        r_m = math.sqrt(HBAR * (n + 0.5) / (M_ELECTRON * omega_c))
        energies.append(e_ev_norm)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "harmonic",
        "QM harmonic oscillator rungs at Compton frequency (normalised)",
        energies, freqs, radii,
        note="Linear energy ladder — flattest possible slope on the comparison chart.",
    )


def theory_pilot_wave() -> TheoryResult:
    """
    Bohm pilot wave: the quantum potential Q adds to classical energy.
    On GeoSeed shells, Q_n ∝ -ℏ²/(2m) · ∇²|ψ|/|ψ| where |ψ|² follows
    the hyperbolic volume-weighted density sinh²(ρ_n).

    Approximation: E_n ≈ ℏ²/(2m r_n²) with r_n = Bohr-scaled GeoSeed radius.
    This is the de Broglie-Bohm kinetic energy from quantum potential alone.
    """
    poincare_rs = [math.tanh(n * math.log(PHI) / 2) for n in range(6)]
    scale = A0 / poincare_rs[1] if poincare_rs[1] > 0 else A0
    energies, freqs, radii = [], [], []
    for n in range(6):
        r_m = poincare_rs[n] * scale if n > 0 else A0 * 0.05
        # Quantum potential kinetic energy: E = ℏ²/(2m r²)
        e_j = HBAR**2 / (2 * M_ELECTRON * r_m**2)
        e_ev = e_j / EV
        f_hz = e_j / H_PLANCK
        energies.append(e_ev)
        freqs.append(f_hz)
        radii.append(r_m)
    return _make_result(
        "pilot_wave",
        "Bohm quantum potential: E ≈ ℏ²/(2m·r²) on GeoSeed phi-radii",
        energies, freqs, radii,
        note="Quantum potential dominates at small r — peaks at inner shells.",
    )


# ── Comparison table ──────────────────────────────────────────────────────────

ALL_THEORIES = [
    theory_compton_orbital,
    theory_bohr,
    theory_de_broglie,
    theory_geoseed_lb,
    theory_harmonic,
    theory_pilot_wave,
]


def run_all() -> Dict[str, TheoryResult]:
    return {fn().name: fn() for fn in ALL_THEORIES}


def comparison_table(results: Dict[str, TheoryResult]) -> str:
    """ASCII table: energy (eV) per shell per theory + RMS residual."""
    theories = list(results.values())
    col_w = 14
    lines = []
    lines.append("Theory Comparison: Binding Energy (eV) per GeoSeed Shell")
    lines.append("  vs hydrogen measured: " +
                 "  ".join(f"{e:.4f}" for e in HYDROGEN_MEASURED_EV))
    lines.append("")
    header = f"{'Theory':<22}" + "".join(
        f"{t:>{col_w}}" for t in TONGUE_ORDER
    ) + f"{'RMS Δ(eV)':>{col_w}}"
    lines.append(header)
    lines.append("-" * len(header))
    for t in theories:
        row = f"{t.name:<22}" + "".join(
            f"{e:>{col_w}.4f}" for e in t.energies_ev()
        ) + f"{t.rms_residual_ev:>{col_w}.4f}"
        lines.append(row)
    lines.append("-" * len(header))
    lines.append("")
    lines.append("Frequency (Hz, log10) per shell:")
    freq_header = f"{'Theory':<22}" + "".join(f"{t:>{col_w}}" for t in TONGUE_ORDER)
    lines.append(freq_header)
    lines.append("-" * (len(freq_header)))
    for t in theories:
        row = f"{t.name:<22}" + "".join(
            f"{math.log10(f):>{col_w}.2f}" for f in t.frequencies_hz()
        )
        lines.append(row)
    return "\n".join(lines)


def main():
    import json
    results = run_all()
    print(comparison_table(results))
    print()
    # JSON summary
    summary = {
        "schema_version": "geoseed_theory_comparison_v1",
        "hydrogen_measured_ev": HYDROGEN_MEASURED_EV,
        "compton_frequency_hz": COMPTON_FREQUENCY,
        "compton_energy_kev": COMPTON_ENERGY_EV / 1000,
        "theories": {k: v.to_dict() for k, v in results.items()},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
