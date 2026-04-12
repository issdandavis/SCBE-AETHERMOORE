"""Cross-scale validation of the phi_phase recurrence.

Same recurrence: x_n = phi^cos(theta_n) * x_{n-1} - x_{n-2}
Four different theta drivers, one per scale of physics:

  ATOMIC    - Bohr-like energy spacing, theta ~ sqrt(n)
  MOLECULAR - Boltzmann thermal tail, theta ~ exp decay
  CELLULAR  - 24-step circadian-style clock, theta ~ sawtooth
  MACRO     - Lotka-Volterra slow drift, theta ~ slow sine

If the math is good, all four produce bounded oscillations with periods
determined by the driver -- not by the recurrence. Same engine, four
different rhythms.
"""

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.symphonic.phi_phase import run, PHI


def stats(name, history):
    mn, mx = min(history), max(history)
    span = mx - mn
    mean = statistics.mean(history)
    stdev = statistics.stdev(history)
    # crude period detection: count zero-mean crossings
    centered = [v - mean for v in history]
    crossings = sum(1 for i in range(1, len(centered))
                    if centered[i - 1] * centered[i] < 0)
    period = (2 * len(history) / crossings) if crossings else float("inf")
    bounded = math.isfinite(span) and span < 1e6
    print(f"\n=== {name} ===")
    print(f"  steps        : {len(history)}")
    print(f"  min / max    : {mn:+.4f} / {mx:+.4f}")
    print(f"  amplitude    : {span:.4f}")
    print(f"  mean / stdev : {mean:+.4f} / {stdev:.4f}")
    print(f"  zero-crossings: {crossings}")
    print(f"  est. period  : {period:.2f} steps")
    print(f"  bounded?     : {'YES' if bounded else 'NO -- DIVERGED'}")
    return bounded


N = 200

# --- ATOMIC: Bohr-like spacing, theta scales with sqrt of step index ---
def atomic_theta(i, h):
    return 2 * math.pi * math.sqrt(i) / 8.0

atomic = run(1.0, 0.5, atomic_theta, N)

# --- MOLECULAR: Boltzmann thermal tail, theta decays exponentially ---
def molecular_theta(i, h):
    return 2 * math.pi * math.exp(-i / 40.0)

molecular = run(1.0, 0.5, molecular_theta, N)

# --- CELLULAR: 24-step cell cycle clock (G1 -> S -> G2 -> M) ---
def cellular_theta(i, h):
    return 2 * math.pi * (i % 24) / 24.0

cellular = run(1.0, 0.5, cellular_theta, N)

# --- MACRO: slow sinusoidal drift (Lotka-Volterra-style modulation) ---
def macro_theta(i, h):
    return 2 * math.pi * math.sin(i / 30.0)

macro = run(1.0, 0.5, macro_theta, N)

results = {
    "ATOMIC    (Bohr sqrt-n)"  : stats("ATOMIC    (Bohr sqrt-n)",     atomic),
    "MOLECULAR (Boltzmann exp)": stats("MOLECULAR (Boltzmann exp)",   molecular),
    "CELLULAR  (24-step clock)": stats("CELLULAR  (24-step clock)",   cellular),
    "MACRO     (Lotka slow)"   : stats("MACRO     (Lotka slow)",      macro),
}

print("\n=== SUMMARY ===")
for k, v in results.items():
    print(f"  {k:30s}  bounded: {'YES' if v else 'NO'}")
print(f"\n  passed: {sum(results.values())}/{len(results)}")
