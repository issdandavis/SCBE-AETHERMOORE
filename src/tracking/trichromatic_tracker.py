"""trichromatic_tracker.py -- object identity as a TRICHROMATIC (IR / Visible / UV) signature.

Applies Issac's trichromatic forgery-resistance system (articles/12_trichromatic_forgery_resistance.md,
src/governance/trichromatic_governance.py) to tracking. The insight transfers exactly:

  VISIBLE band  = appearance (grain)          -- observable; CLONES MATCH IT (the "attacker sees this")
  INFRARED band = slow accumulated world-line  -- the trajectory history ("you'd need to have lived its life")
  ULTRAVIOLET   = fast emergent dynamics        -- acceleration / direction-change spikes

A WRONG link is a FORGERY: it matches the visible band (a look-alike clone) but fails IR + UV. Just like
the governance system caught 5/5 forgeries that perfectly matched all visible signals, the hidden bands
catch the clone the appearance can't. Identity is transferred across frames by matching ALL THREE bands,
hidden-band-dominant.
"""
from __future__ import annotations
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from grain_tracker import grain_signature, grain_similarity   # noqa: E402


def _predict(history, span):
    """Predict the next position from the last `span` points (linear fit) -> time-scale band."""
    h = np.asarray(history, dtype=np.float64)
    if len(h) < 2:
        return None
    seg = h[-span:] if len(h) >= span else h
    t = np.arange(len(seg))
    pred = np.array([np.polyval(np.polyfit(t, seg[:, k], 1), len(seg)) for k in range(seg.shape[1])])
    return pred


def infrared_continuity(history, candidate, scale, soft_um=6.0):
    """SLOW band: does the candidate continue the cell's LONG accumulated world-line? (whole history)"""
    pred = _predict(history, span=99)
    if pred is None:
        return 0.5
    dev = np.sqrt((((np.asarray(candidate, float) - pred) * np.asarray(scale)) ** 2).sum())
    return float(np.exp(-(dev / soft_um) ** 2))


def ultraviolet_continuity(history, candidate, scale, soft_um=6.0):
    """FAST band: does the candidate match the cell's IMMEDIATE dynamics (last 3 pts: velocity+accel)?"""
    h = np.asarray(history, dtype=np.float64)
    if len(h) < 3:
        return 0.5
    vel = h[-1] - h[-2]
    accel = (h[-1] - h[-2]) - (h[-2] - h[-3])
    pred = h[-1] + vel + 0.5 * accel                                  # fast emergent extrapolation
    dev = np.sqrt((((np.asarray(candidate, float) - pred) * np.asarray(scale)) ** 2).sum())
    return float(np.exp(-(dev / soft_um) ** 2))


def trichromatic_score(history, candidate, cell_grain, cand_grain, scale, w=(0.4, 0.2, 0.4)):
    """Fuse the three bands. w = (IR, Visible, UV). Hidden bands (IR+UV) dominate so a look-alike clone
    that only matches the visible band is caught -- the tracking analogue of the 5/5 forgery test."""
    ir = infrared_continuity(history, candidate, scale)
    uv = ultraviolet_continuity(history, candidate, scale)
    vis = 0.5 * (grain_similarity(cell_grain, cand_grain) + 1.0)      # [-1,1] -> [0,1]
    return w[0] * ir + w[1] * vis + w[2] * uv, dict(ir=ir, visible=vis, uv=uv)


def band_confidence(grain_sig=None, frame_eigs=None, neighbor_rel=None):
    """How DEFINABLE is each spatial band for this cell (0 = null, 1 = strong)? Issac's negative-space:
    absence is itself a signal. Undefinable bands get down-weighted so identity reconstructs from the
    bands that ARE defined (world-line always on) -- MRI-style filling of the null space from priors."""
    conf = {}
    conf["grain"] = 0.0 if grain_sig is None else float(min(1.0, np.std(grain_sig) * np.sqrt(len(grain_sig)) / 1.5))
    if frame_eigs is None:                                            # nucleus orientation definability
        conf["frame"] = 0.0
    else:
        e = np.sort(np.abs(frame_eigs))[::-1]
        conf["frame"] = float(min(1.0, (e[0] - e[-1]) / (e[0] + 1e-9)))   # elongation -> orientable
    if neighbor_rel is None or len(neighbor_rel) < 3:
        conf["const"] = 0.0
    else:
        c = np.linalg.eigvalsh(np.asarray(neighbor_rel).T @ np.asarray(neighbor_rel))
        conf["const"] = float(min(1.0, (c.max() - c.min()) / (c.max() + 1e-9)))   # anisotropy -> distinctive
    return conf


def identity_null_aware(ir, uv, visible, const, conf):
    """Fuse bands weighted by definability. World-line (ir+uv) is the always-defined prior that fills the
    null space of the undefinable spatial bands (visible/const). The absence pattern is encoded in the weights."""
    wv, wc = conf.get("grain", 0.0), conf.get("const", 0.0)
    w_time = 1.0                                                      # world-line is always defined
    tot = w_time + wv + wc + 1e-9
    time_band = 0.5 * (ir + uv)
    return (w_time * time_band + wv * visible + wc * const) / tot


if __name__ == "__main__":
    # FORGERY TEST (tracking analogue of the governance 5/5): a clone perfectly matches the VISIBLE band
    # (same grain) but sits on the wrong world-line. Does the trichromatic identity catch the forgery?
    rng = np.random.RandomState(7)
    scale = np.array([1.0, 1.0, 1.0])

    def grain_img(seed, shift=(0, 0)):
        yy, xx = np.mgrid[-14:15, -14:15].astype(np.float32)
        base = np.exp(-((yy ** 2 + xx ** 2) / 20.0))
        g = np.random.RandomState(seed).randn(29, 29).astype(np.float32) * 0.20
        obj = base + g * base
        return np.roll(np.roll(obj, shift[0], axis=0), shift[1], axis=1)

    # Fred: history moving +x; his grain = seed 11.
    histFred = [(0, 10, 0), (0, 10, 5), (0, 10, 10)]
    fred_grain = grain_signature(grain_img(11, (0, 10)), (14, 24 - 10))     # Fred's appearance signature
    detReal = (0, 10, 15)                                                   # real Fred: continues +x
    detForge = (0, 16, 11)                                                  # forgery: elsewhere, WRONG world-line
    # the forgery is a CLONE that copied Fred's grain perfectly (visible band matched):
    forge_grain = fred_grain.copy()
    real_grain = fred_grain.copy()                                          # real Fred also has Fred's grain

    s_real, b_real = trichromatic_score(histFred, detReal, fred_grain, real_grain, scale)
    s_forge, b_forge = trichromatic_score(histFred, detForge, fred_grain, forge_grain, scale)
    print("FORGERY TEST (clone matches VISIBLE band perfectly, wrong world-line):")
    print(f"  real   detReal : score {s_real:.3f}  bands IR={b_real['ir']:.2f} Vis={b_real['visible']:.2f} UV={b_real['uv']:.2f}")
    print(f"  forgery detForge: score {s_forge:.3f}  bands IR={b_forge['ir']:.2f} Vis={b_forge['visible']:.2f} UV={b_forge['uv']:.2f}")
    print(f"  => hidden bands catch the forgery: {s_real > s_forge}  "
          f"(visible matched: {abs(b_real['visible'] - b_forge['visible']) < 1e-6})")

    # NULL-SPACE demo (Issac's negative-space + MRI-light): a smooth nucleus -> the GRAIN band is NULL.
    # World-lines are close, so the (meaningless) grain band tips naive fusion to a distractor that forged
    # it. Encoding the ABSENCE (grain confidence ~0) drops that band and reconstructs identity from time.
    conf_null = band_confidence(grain_sig=np.zeros(48), frame_eigs=None, neighbor_rel=None)   # grain conf -> 0
    real = dict(ir=0.70, uv=0.65, visible=0.30, const=0.0)          # right cell; grain uninformative (low match)
    dist = dict(ir=0.68, uv=0.60, visible=0.95, const=0.0)          # distractor: slightly worse world-line, forged grain
    naive = lambda b: (b["ir"] + b["uv"] + b["visible"]) / 3.0
    na_r = identity_null_aware(real["ir"], real["uv"], real["visible"], real["const"], conf_null)
    na_d = identity_null_aware(dist["ir"], dist["uv"], dist["visible"], dist["const"], conf_null)
    print("\nNULL-SPACE demo (grain band NULL for a smooth nucleus, close world-lines):")
    print(f"  naive equal-weight:  real {naive(real):.2f} vs distractor {naive(dist):.2f}  "
          f"=> {'real' if naive(real) > naive(dist) else 'WRONG (fooled by the null band)'}")
    print(f"  null-aware (conf-wt): real {na_r:.2f} vs distractor {na_d:.2f}  "
          f"=> {'real (world-line fills the null)' if na_r > na_d else 'wrong'}")
    print(f"  (grain confidence when null: {conf_null['grain']:.2f})")
