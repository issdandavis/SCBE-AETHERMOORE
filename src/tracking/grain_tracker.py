"""grain_tracker.py -- track near-identical objects by their fine-grained texture fingerprint.

Issac's idea (2026-07): when objects are identical at the blob level (a crowd of clones), the
MICRO-PERTURBATION on the image grain -- the high-frequency speckle *inside* each object -- is a unique
fingerprint. The key is the SPATIAL PATTERN of the grain (its arrangement), not its distribution: two
different random speckles have nearly identical histograms but very different patterns. So we correlate
the aligned grain PATCHES. Multiple views of the same patch (grain / gradient) enrich the signature.
This is the "different views of one substrate, minor differences" principle applied to object association.

  grain_signature(image, center) -> normalized spatial grain vector
  grain_similarity(a, b)          -> correlation in [-1, 1]  (high = same object across a small move)
  grain_link(...)                 -> geometry + grain fused assignment (clone tie-breaker)

Pure numpy/scipy; works on 2D or 3D patches. (First attempt used histograms and FAILED its own self-test
-- clones matched *better* -- because histograms discard the spatial arrangement. Fixed to patterns.)
"""
from __future__ import annotations
import numpy as np


def _patch(image, center, r):
    center = [int(round(c)) for c in center]
    slices = tuple(slice(max(0, c - r), c + r + 1) for c in center)
    return np.asarray(image[slices], dtype=np.float32)


def grain_signature(image, center, r=6, blur_sigma=1.5):
    """The SPATIAL high-frequency residual around a detection, flattened + L2-normalized = the fingerprint."""
    from scipy import ndimage as ndi
    p = _patch(image, center, r).astype(np.float32)
    p = (p - p.mean()) / (p.std() + 1e-6)                          # contrast-normalize so identical blobs align
    grain = p - ndi.gaussian_filter(p, blur_sigma)                # the grain: keep the PATTERN, not a histogram
    v = grain.ravel()
    return v / (np.linalg.norm(v) + 1e-6)


def grain_similarity(a, b):
    """Correlation of two grain signatures (already L2-normalized -> dot product). High = same speckle."""
    n = min(len(a), len(b))
    return float(np.dot(a[:n], b[:n]))


def grain_field(image, center, r=6, blur_sigma=1.5):
    """Same grain, kept as its SPATIAL field (not flattened) so partial/occluded views can be matched."""
    from scipy import ndimage as ndi
    p = _patch(image, center, r).astype(np.float32)
    p = (p - p.mean()) / (p.std() + 1e-6)
    return p - ndi.gaussian_filter(p, blur_sigma)


def grain_similarity_partial(field_a, field_b, mask=None):
    """HALF-MOON / FULL-MOON: correlate two grain fields over only the VISIBLE region (mask=True).
    Recognizes a cell from a fragment (frame edge / occlusion) by matching the part that IS there."""
    a, b = np.asarray(field_a, np.float32), np.asarray(field_b, np.float32)
    if a.shape != b.shape:
        s = tuple(min(x, y) for x, y in zip(a.shape, b.shape))
        a, b = a[tuple(slice(0, k) for k in s)], b[tuple(slice(0, k) for k in s)]
    if mask is None:
        mask = np.ones(a.shape, bool)
    else:
        mask = np.asarray(mask, bool)
        if mask.shape != a.shape:
            mask = mask[tuple(slice(0, k) for k in a.shape)]
    av, bv = a[mask], b[mask]                                       # only the visible portion
    if av.size < 4:
        return 0.0
    av = (av - av.mean()) / (av.std() + 1e-6)
    bv = (bv - bv.mean()) / (bv.std() + 1e-6)
    return float((av * bv).mean())                                 # normalized correlation over the crescent


def trajectory_continuity(history, candidate, scale, soft_um=6.0):
    """WORLD-LINE identity (the Weasley principle): identity is a property of TIME, not appearance.
    Score how well a candidate next-position continues a cell's established world-line. Uses the recent
    trajectory to predict where the cell *should* be (constant velocity, extended by curvature if enough
    history), and scores the candidate by how little it deviates from that. High = 'this is the same cell.'"""
    h = np.asarray(history, dtype=np.float64)
    if len(h) < 2:
        return 0.5                                                 # no world-line yet -> neutral
    vel = h[-1] - h[-2]
    predicted = h[-1] + vel                                        # constant-velocity extrapolation
    if len(h) >= 3:
        predicted = predicted + 0.5 * ((h[-1] - h[-2]) - (h[-2] - h[-3]))   # + curvature (accel) term
    dev = np.sqrt((((np.asarray(candidate, float) - predicted) * np.asarray(scale)) ** 2).sum())
    return float(np.exp(-(dev / soft_um) ** 2))                    # 1 at perfect continuation, ->0 as it diverges


def identity_score(history, candidate, sig_prev, sig_cand, scale, w_grain=0.25):
    """Full identity = world-line continuity FIRST, grain as the tie-breaker only when trajectories are close."""
    traj = trajectory_continuity(history, candidate, scale)
    grain = 0.5 * (grain_similarity(sig_prev, sig_cand) + 1.0)     # map [-1,1] -> [0,1]
    return (1 - w_grain) * traj + w_grain * grain


def grain_link(prev_pts, prev_ids, cur_pts, cur_ids, prev_img, cur_img, scale, gate_um, w_grain=0.5, r=6):
    """Fuse geometry + grain into a clone-aware assignment. cost = (1-w)*dist/gate + w*(1 - grain_sim).
    The grain breaks the ties that distance alone cannot (a cell surrounded by look-alike clones)."""
    from scipy.optimize import linear_sum_assignment
    if len(prev_pts) == 0 or len(cur_pts) == 0:
        return []
    pp, cp = np.asarray(prev_pts) * scale, np.asarray(cur_pts) * scale
    d = np.sqrt(((pp[:, None, :] - cp[None, :, :]) ** 2).sum(axis=2))
    sp = [grain_signature(prev_img, c, r) for c in prev_pts]
    sc = [grain_signature(cur_img, c, r) for c in cur_pts]
    big = 5.0
    cost = np.full(d.shape, big)
    for i in range(len(prev_pts)):
        for j in range(len(cur_pts)):
            if d[i, j] <= gate_um:
                cost[i, j] = (1 - w_grain) * (d[i, j] / gate_um) + w_grain * (1.0 - grain_similarity(sp[i], sc[j]))
    ri, ci = linear_sum_assignment(cost)
    return [(int(prev_ids[r_]), int(cur_ids[c_])) for r_, c_ in zip(ri, ci)
            if cost[r_, c_] < big and d[r_, c_] <= gate_um]


if __name__ == "__main__":
    # SELF-TEST: two IDENTICAL-shape blobs (clones) with DIFFERENT grain that TRAVELS WITH the cell.
    # Claim: grain fingerprint links each cell to itself across a small move better than to its clone.
    def cell(grain_seed, shift=(0, 0)):
        yy, xx = np.mgrid[-14:15, -14:15].astype(np.float32)
        base = np.exp(-((yy ** 2 + xx ** 2) / 20.0))                       # identical shape, centered
        g = np.random.RandomState(grain_seed).randn(29, 29).astype(np.float32) * 0.20  # unique grain
        obj = base + g * base                                              # grain lives ON the object
        return np.roll(np.roll(obj, shift[0], axis=0), shift[1], axis=1)   # move the whole object (grain rides along)

    A0, A1 = cell(11), cell(11, shift=(1, -1))     # cell A, two frames (its grain moves with it)
    B1 = cell(22, shift=(1, 1))                    # cell B: a clone (identical shape, DIFFERENT grain)
    fpA0 = grain_signature(A0, (14, 14))
    fpA1 = grain_signature(A1, (15, 13))           # A re-centered at its moved position
    fpB1 = grain_signature(B1, (15, 15))
    same = grain_similarity(fpA0, fpA1)            # correct link A->A
    clone = grain_similarity(fpA0, fpB1)           # wrong link A->clone
    print(f"A0~A1 (same cell):    {same:.3f}")
    print(f"A0~B1 (clone, wrong): {clone:.3f}")
    print(f"=> grain distinguishes clones: {same > clone}  (margin {same - clone:+.3f})")

    # HALF-MOON: A is only HALF visible (occluded / at the frame edge). Does its crescent still ID it?
    fA0, fA1, fB1 = grain_field(A0, (14, 14)), grain_field(A1, (15, 13)), grain_field(B1, (15, 15))
    halfmask = np.zeros(fA0.shape, bool); halfmask[:, :fA0.shape[1] // 2] = True     # only left half visible
    hm_same = grain_similarity_partial(fA0, fA1, halfmask)
    hm_clone = grain_similarity_partial(fA0, fB1, halfmask)
    print("\nHALF-MOON (only left half of the cell visible):")
    print(f"  crescent-A ~ full-A (same cell): {hm_same:.3f}")
    print(f"  crescent-A ~ clone (wrong):      {hm_clone:.3f}")
    print(f"  => fragment still IDs the cell: {hm_same > hm_clone}  (margin {hm_same - hm_clone:+.3f})")

    # WEASLEY TWINS: two cells with IDENTICAL grain (true twins) -- appearance CANNOT separate them.
    # Their world-lines differ, so "characteristic over time" tells them apart.
    sc = np.array([1.0, 1.0, 1.0])
    histFred = [(0, 10, 0), (0, 10, 5), (0, 10, 10)]           # Fred: moving +x along row 10
    histGeorge = [(0, 0, 12), (0, 5, 11), (0, 10, 11)]         # George: moving +y, crosses near Fred
    detA = (0, 10, 15)                                         # continues Fred's +x world-line
    detB = (0, 15, 11)                                         # continues George's +y world-line
    fA, fB = trajectory_continuity(histFred, detA, sc), trajectory_continuity(histFred, detB, sc)
    gA, gB = trajectory_continuity(histGeorge, detA, sc), trajectory_continuity(histGeorge, detB, sc)
    print("\nWEASLEY TWINS (identical grain, different world-lines):")
    print(f"  Fred   -> detA {fA:.2f} / detB {fB:.2f}  => {'detA (correct)' if fA > fB else 'WRONG'}")
    print(f"  George -> detA {gA:.2f} / detB {gB:.2f}  => {'detB (correct)' if gB > gA else 'WRONG'}")
    print(f"  => world-line separates the twins: {fA > fB and gB > gA}")
