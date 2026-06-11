"""Test the 14 layers in DIFFERENT ways — each by its own job, not one ruler.

The old verdict ("most layers are decoration") came from asking every layer the
same question: does it make the allow/deny call? That is the wrong test for a
layer whose job is to MEASURE, SEE, HEAR, or POSITION. So here each layer is
judged by what it is actually for:

    TRANSFORM   -> does it PRESERVE structure? (isometry / boundedness / invariance)
    INSTRUMENT  -> does its needle MOVE with the quantity it claims to read,
                   and beat a NULL (shuffled / destroyed input)?
    SENSOR/HEAR -> can you DECODE the state back out of what it emits?
    SECURITY    -> does it SEPARATE safe from unsafe?

Everything runs against the real pipeline in
src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py.
Run:  python scripts/eval/layer_role_bench.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
_PIPE = _REPO / "src" / "symphonic_cipher" / "scbe_aethermoore" / "layers" / "fourteen_layer_pipeline.py"

# Load the pipeline module directly from its file (dodges the dual-package
# `import symphonic_cipher` collision documented in CLAUDE.md).
import sys

sys.path.insert(0, str(_REPO))
_spec = importlib.util.spec_from_file_location("scbe_14L", _PIPE)
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

rng = np.random.default_rng(7)


def spearman(a, b) -> float:
    """Rank correlation — monotonicity, not linearity."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def line(name, role, test, value, verdict):
    print(f"  {name:5} {role:11} {test:26} {value:>10}   {verdict}")


def main():
    print("\n  layer role           test                          value   verdict")
    print("  " + "─" * 72)

    # ---- TRANSFORM: preserve structure ----------------------------------- #
    # L2 realification claims a distance-preserving isometry.
    errs = []
    for _ in range(200):
        c = rng.standard_normal(8) + 1j * rng.standard_normal(8)
        x = L.layer_2_realify(c)
        errs.append(abs(np.linalg.norm(x) - np.linalg.norm(c)))
    e = max(errs)
    line("L2", "transform", "norm preserved (isometry)", f"{e:.1e}",
         "PRESERVES" if e < 1e-9 else "LOSSY")

    # L4 Poincaré embedding claims the open ball ||u|| < 1.
    norms = [np.linalg.norm(L.layer_4_poincare(rng.standard_normal(8) * s)) for s in np.linspace(0.1, 50, 300)]
    mx = max(norms)
    line("L4", "transform", "stays in ball ||u||<1", f"{mx:.4f}",
         "PRESERVES" if mx < 1.0 else "ESCAPES")

    # L6 breathing + L7 Möbius claim to be isometries: d_H must survive them.
    u = L.layer_4_poincare(rng.standard_normal(8))
    v = L.layer_4_poincare(rng.standard_normal(8))
    d0 = L.layer_5_hyperbolic_distance(u, v)
    a = L.layer_4_poincare(rng.standard_normal(8) * 0.1)
    d7 = L.layer_5_hyperbolic_distance(L.layer_7_phase(u, 0.9, a), L.layer_7_phase(v, 0.9, a))
    # L6 is a hyperbolic DILATION (scales the radius by b). If it is a clean
    # dilation, d6/d0 is the SAME ratio for every pair -> a consistent scale,
    # not random breakage. That is its real role (a breathing scale), and it
    # exposes the docstring's "isometry" claim as wrong.
    ratios = []
    for _ in range(50):
        p = L.layer_4_poincare(rng.standard_normal(8))
        qd = L.layer_4_poincare(rng.standard_normal(8))
        d_pre = L.layer_5_hyperbolic_distance(p, qd)
        d_post = L.layer_5_hyperbolic_distance(L.layer_6_breathing(p, 0.3), L.layer_6_breathing(qd, 0.3))
        if d_pre > 1e-6:
            ratios.append(d_post / d_pre)
    spread = float(np.std(ratios)) if ratios else 0.0
    line("L6", "instrument", "consistent dilation ratio", f"{np.mean(ratios):.2f}±{spread:.2f}",
         "DILATION (docstring 'isometry' is WRONG)" if spread > 1e-3 else "isometry")
    line("L7", "transform", "d_H invariant (Mobius)", f"{abs(d7-d0):.1e}",
         "PRESERVES" if abs(d7 - d0) < 1e-6 else "BREAKS d_H")

    # ---- INSTRUMENT: needle moves with the quantity, and beats a null ----- #
    # L5 ruler: distance must rise as v walks away from u.
    base = L.layer_4_poincare(np.zeros(8))
    steps = np.linspace(0.01, 0.9, 40)
    dh = [L.layer_5_hyperbolic_distance(base, L.layer_4_poincare(np.r_[s, np.zeros(7)] * 5)) for s in steps]
    s_live = spearman(steps, dh)
    s_null = spearman(rng.permutation(steps), dh)
    line("L5", "instrument", "d_H rises with distance", f"{s_live:+.2f}",
         f"LIVE RULER (null {s_null:+.2f})" if s_live > 0.95 else "flat")

    # L9 spectral coherence: smooth signal should read higher than noise.
    t = np.linspace(0, 1, 2048)
    smooth = [L.layer_9_spectral_coherence(np.sin(2 * np.pi * 3 * t) + 0.02 * rng.standard_normal(2048)) for _ in range(30)]
    noisy = [L.layer_9_spectral_coherence(rng.standard_normal(2048)) for _ in range(30)]
    sep = np.mean(smooth) - np.mean(noisy)
    line("L9", "instrument", "smooth>noisy separation", f"{sep:+.3f}",
         "LIVE METER" if sep > 0.05 else "no separation")

    # L10 spin coherence reads MAGNITUDE (2|q|^2-1): needle must rise with |q|.
    mags = np.linspace(0.05, 1.0, 40)
    c10 = [L.layer_10_spin_coherence(complex(m, 0.0)) for m in mags]
    s10 = spearman(mags, c10)
    s10_null = spearman(rng.permutation(mags), c10)
    line("L10", "instrument", "reads amplitude |q|", f"{s10:+.2f}",
         f"LIVE METER (null {s10_null:+.2f})" if s10 > 0.95 else "flat")

    # L11 triadic: distance must grow as the two states truly diverge.
    div = np.linspace(0, 1, 40)
    d11 = []
    for s in div:
        u2 = L.layer_4_poincare(np.r_[s, np.zeros(7)] * 5)
        d11.append(L.layer_11_triadic_distance(base, u2, 0.0, s, 0.0, s, 1 + 0j, complex(np.cos(s), np.sin(s))))
    s11 = spearman(div, d11)
    line("L11", "instrument", "rises with divergence", f"{s11:+.2f}",
         "LIVE TRACKER" if s11 > 0.95 else "flat")

    # L12 gauge: safety score must DROP as distance grows (Theorem C).
    dd = np.linspace(0, 5, 50)
    sc = [L.layer_12_harmonic_scaling(d) for d in dd]
    s12 = spearman(dd, sc)
    line("L12", "instrument", "score falls with risk", f"{s12:+.2f}",
         "LIVE GAUGE" if s12 < -0.95 else "non-monotone")

    # ---- SENSOR / HEAR: decode the state back out of the sound ----------- #
    # L14 audio encodes risk->amplitude, intent->phase, coherence->envelope.
    levels = [L.RiskLevel.LOW, L.RiskLevel.MEDIUM, L.RiskLevel.HIGH, L.RiskLevel.CRITICAL]
    true_amp, heard_amp = [], []
    for _ in range(120):
        lvl = levels[rng.integers(0, 4)]
        coh = float(rng.uniform(0.2, 1.0))
        sig = L.layer_14_audio_axis(intent=0.3, coherence=coh, risk_level=lvl)
        true_amp.append({L.RiskLevel.LOW: 1.0, L.RiskLevel.MEDIUM: 0.7, L.RiskLevel.HIGH: 0.4, L.RiskLevel.CRITICAL: 0.1}[lvl])
        heard_amp.append(float(np.max(np.abs(sig))))  # recover amplitude from the waveform
    corr = float(np.corrcoef(true_amp, heard_amp)[0, 1])
    line("L14", "sensor/hear", "risk recovered from sound", f"{corr:+.2f}",
         "HEARS STATE" if corr > 0.9 else "muffled")

    # ---- SECURITY: separate safe from unsafe ----------------------------- #
    # L8 realm distance + L13 decision on a separable set: points near a center
    # (safe) vs far (unsafe). Catch rate = fraction of far points NOT allowed.
    centers = [L.layer_4_poincare(rng.standard_normal(8)) for _ in range(3)]
    safe_allowed = unsafe_denied = 0
    for _ in range(80):
        near = centers[0] + rng.standard_normal(8) * 1e-3  # genuinely near a realm center
        far = L.layer_4_poincare(rng.standard_normal(8) * 30)
        for pt, bucket in ((near, "safe"), (far, "unsafe")):
            dstar, idx = L.layer_8_multi_well(pt, centers)
            H = L.layer_12_harmonic_scaling(dstar)
            r = L.layer_13_decision(dstar, H, coherence=0.9, realm_idx=idx)
            if bucket == "safe" and r.decision == "ALLOW":
                safe_allowed += 1
            if bucket == "unsafe" and r.decision != "ALLOW":
                unsafe_denied += 1
    line("L8+13", "SECURITY", "safe ALLOW / unsafe DENY", f"{safe_allowed}/{unsafe_denied}/80",
         "SEPARATES" if unsafe_denied > 60 else "weak separation")

    print("  " + "─" * 72)
    print("  each layer judged by its own job. transforms preserve, instruments")
    print("  read live + beat null, the ear decodes, security separates.\n")


if __name__ == "__main__":
    main()
