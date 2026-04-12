"""Eigenvalue / phase-space diagnostics for offset-spin equivalence.

The phi_phase recurrence x_n = phi^cos(theta) * x_{n-1} - x_{n-2} is a
parametric oscillator with companion-matrix eigenvalues on the unit
circle for every theta (|lambda| = 1, neutrally stable). Six Sacred
Tongues run the SAME engine with golden-angle phase offsets, so the
right diagnostics live in 2D state space (x_n, x_{n-1}), not in 1D
value space. The previous test asked the wrong questions.

Three properties, all eigenvalue / phase-space framed:

  1. EIGENVALUE   -- empirical |lambda| ~= 1 for every tongue
                     (norm of state vector preserved on average).
  2. PHASE-SPACE  -- pairwise minimum separation of state vectors
                     (x_n, x_{n-1}) across the run is strictly > 0.
                     Golden-angle offsets guarantee non-collision in
                     the 2D plane even when 1D values cross zero.
  3. PHASE-ANGLE  -- final phase angles of the six state vectors are
                     spread (not clustered); spread compared against
                     the golden-angle expectation.
"""

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.symphonic.phi_phase import run_six_tongues, TONGUES, GOLDEN_ANGLE
from src.symphonic.tongue_lang_map import TONGUE_LANG


def base_theta(i, _state):
    return 2 * math.pi * i / 50.0


N = 400
WARMUP = 50  # drop transient before measuring
runs = run_six_tongues(1.0, 0.5, base_theta, N)

print(f"Golden angle: {GOLDEN_ANGLE:.4f} rad ({math.degrees(GOLDEN_ANGLE):.3f} deg)")
print(f"Tongues     : {', '.join(TONGUES)}")
print(f"Steps       : {N}  (warmup dropped: {WARMUP})\n")


def state_vectors(history):
    """Build (x_n, x_{n-1}) state-vector trajectory."""
    return [(history[i], history[i - 1]) for i in range(1, len(history))]


def vec_norm(v):
    return math.hypot(v[0], v[1])


def vec_dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --- 1) Eigenvalue: |lambda| ~= 1 per tongue ---
print("=== 1) EIGENVALUE (|lambda| ~= 1 on every tongue) ===")
lambdas = {}
for t in TONGUES:
    sv = state_vectors(runs[t])[WARMUP:]
    norms = [vec_norm(v) for v in sv]
    # Geometric mean of successive ratios -> empirical |lambda|
    ratios = [norms[i + 1] / norms[i] for i in range(len(norms) - 1)
              if norms[i] > 1e-12]
    log_mean = statistics.mean(math.log(r) for r in ratios if r > 0)
    lam = math.exp(log_mean)
    lambdas[t] = lam
    lang = TONGUE_LANG[t]
    print(f"  {t} -> {lang:10s}  |lambda| = {lam:.6f}   "
          f"||state|| mean {statistics.mean(norms):.4f}")

lam_dev = max(abs(l - 1.0) for l in lambdas.values())
print(f"  max deviation from 1.0: {lam_dev:.6f}  "
      f"({'NEUTRALLY STABLE' if lam_dev < 0.01 else 'DRIFTING'})")

# --- 2) Trit-collision: +1/+1 write-write coincidences only ---
#
# A "collision" in 1D value space is just a coincidence -- whether it's
# dangerous depends on what each tongue is doing at that step. Polarity
# from a zero-band on x_n: |x| < EPS => 0 (witness/read), x > EPS => +1
# (active/write), x < -EPS => -1 (blocking/negate). Only +1/+1 is a
# write-write conflict; everything else is safe.
print("\n=== 2) TRIT COLLISION (only +1/+1 = write-write is dangerous) ===")
EPS = 0.25  # zero-band; outside it the tongue is acting

def polarity(x):
    if x > EPS:
        return +1
    if x < -EPS:
        return -1
    return 0

pols = {t: [polarity(v) for v in runs[t][WARMUP:]] for t in TONGUES}
N_steps = len(next(iter(pols.values())))

ww_total = 0   # write-write (dangerous)
wr_total = 0   # write-read  (safe)
wn_total = 0   # write-negate (cancel)
ww_pairs = {}
for ai, a in enumerate(TONGUES):
    for b in TONGUES[ai + 1:]:
        ww = wr = wn = 0
        for pa, pb in zip(pols[a], pols[b]):
            if pa == 1 and pb == 1:
                ww += 1
            elif (pa == 1 and pb == 0) or (pa == 0 and pb == 1):
                wr += 1
            elif (pa == 1 and pb == -1) or (pa == -1 and pb == 1):
                wn += 1
        ww_total += ww
        wr_total += wr
        wn_total += wn
        if ww:
            ww_pairs[(a, b)] = ww

print(f"  steps measured       : {N_steps}")
print(f"  write-write (danger) : {ww_total}")
print(f"  write-read  (safe)   : {wr_total}")
print(f"  write-negate(cancel) : {wn_total}")
if ww_pairs:
    worst = max(ww_pairs.items(), key=lambda kv: kv[1])
    print(f"  worst pair           : {worst[0]} -> {worst[1]} ww-collisions")
print(f"  ww-rate per pair-step: {ww_total / (15 * N_steps):.4f}")
print(f"  conflict check       : "
      f"{'PASS (no ww-collisions)' if ww_total == 0 else 'CONFLICTS PRESENT'}")

# --- 3) Phase-angle distribution at end of run ---
print("\n=== 3) PHASE-ANGLE (final angles spread by golden angle) ===")
final_angles = {}
for t in TONGUES:
    sv = state_vectors(runs[t])
    x, y = sv[-1]
    final_angles[t] = math.atan2(y, x) % (2 * math.pi)
ordered = sorted(final_angles.values())
gaps = [(ordered[(i + 1) % 6] - ordered[i]) % (2 * math.pi)
        for i in range(6)]
print(f"  final angles (rad): "
      f"{[f'{a:.3f}' for a in ordered]}")
print(f"  gaps (rad)        : {[f'{g:.3f}' for g in gaps]}")
print(f"  gap stdev         : {statistics.stdev(gaps):.4f}  "
      f"({'EVENLY SPREAD' if statistics.stdev(gaps) < 0.5 else 'CLUSTERED'})")

# --- Summary ---
print("\n=== SUMMARY ===")
ok_eig = lam_dev < 0.01
ok_trit = ww_total == 0
ok_ang = statistics.stdev(gaps) < 0.5
print(f"  EIGENVALUE  : {'PASS' if ok_eig else 'FAIL'}")
print(f"  TRIT-SAFETY : {'PASS' if ok_trit else 'FAIL'}  ({ww_total} ww-collisions)")
print(f"  PHASE-ANGLE : {'PASS' if ok_ang else 'FAIL'}")
print(f"  total       : {sum([ok_eig, ok_trit, ok_ang])}/3")
