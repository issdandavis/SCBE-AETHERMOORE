"""constellation_band.py -- the RELATIONAL band: a cell's identity from its NEIGHBORHOOD arrangement.

Issac's idea (2026-07-05): identity isn't in the cell's own color/grain -- it's in "the state of its
neighborhood, ring by ring." A point is a circle; its signature is the arrangement of the cells touching
it, and the cells touching those. Two identical-looking clones sit in DIFFERENT neighborhoods, so the
constellation distinguishes them where appearance can't; and as the crowd drifts, the constellation
deforms slowly + coherently (the "oscillation"), so it matches frame to frame.

This is a 3D log-distance x angular shape-context histogram of the relative positions of neighbors --
translation-invariant (relative coords), robust (binned), matchable (histogram similarity). It's the 4th
band on the trichromatic identity: IR (world-line) / Visible (grain) / UV (dynamics) / Relational (this).
"""
from __future__ import annotations
import numpy as np


def constellation_signature(center, neighbors, scale, rings=(4.0, 9.0, 16.0, 28.0), n_az=8, n_el=3):
    """Relative-position histogram of neighbors around a cell: rings x azimuth x elevation. L2-normalized.
    rings = distance-band edges in microns (physical); neighbors excludes the cell itself."""
    center = np.asarray(center, float)
    scale = np.asarray(scale, float)
    nb = np.asarray(neighbors, float)
    if nb.size == 0:
        return np.zeros(len(rings) * n_az * n_el)
    rel = (nb - center) * scale                                       # physical relative positions
    d = np.linalg.norm(rel, axis=1)
    sig = np.zeros((len(rings), n_az, n_el))
    for v, dist in zip(rel, d):
        if dist < 1e-6:
            continue
        ring = int(np.searchsorted(rings, dist))
        if ring >= len(rings):
            continue                                                  # beyond outer ring -> ignored
        az = np.arctan2(v[1], v[2])                                   # azimuth in the y-x plane
        el = np.arctan2(v[0], np.linalg.norm(v[1:]) + 1e-9)           # elevation: z vs xy
        ai = int((az + np.pi) / (2 * np.pi + 1e-9) * n_az) % n_az
        ei = min(int((el + np.pi / 2) / (np.pi + 1e-9) * n_el), n_el - 1)
        sig[ring, ai, ei] += 1.0
    v = sig.ravel()
    return v / (np.linalg.norm(v) + 1e-6)


def constellation_similarity(a, b):
    n = min(len(a), len(b))
    return float(np.dot(a[:n], b[:n]))


def _pca_frame(rel):
    """Local orientation frame from the neighbor cloud (PCA) -> the '6D': position + orientation.
    Sign-disambiguated by third-moment (skew) so a rotated neighborhood maps to the SAME frame."""
    cov = rel.T @ rel
    _, V = np.linalg.eigh(cov)                                        # columns = principal axes
    aligned = rel @ V
    for k in range(aligned.shape[1]):                                # fix axis signs by skew convention
        if (aligned[:, k] ** 3).sum() < 0:
            aligned[:, k] *= -1
    return aligned


def _hist_from_aligned(aligned, rings, n_az, n_el):
    d = np.linalg.norm(aligned, axis=1)
    sig = np.zeros((len(rings), n_az, n_el))
    for v, dist in zip(aligned, d):
        if dist < 1e-6:
            continue
        ring = int(np.searchsorted(rings, dist))
        if ring >= len(rings):
            continue
        az = np.arctan2(v[1], v[2]); el = np.arctan2(v[0], np.linalg.norm(v[1:]) + 1e-9)
        ai = int((az + np.pi) / (2 * np.pi + 1e-9) * n_az) % n_az
        ei = min(int((el + np.pi / 2) / (np.pi + 1e-9) * n_el), n_el - 1)
        sig[ring, ai, ei] += 1.0
    v = sig.ravel()
    return v / (np.linalg.norm(v) + 1e-6)


def grid_frame(all_points, scale):
    """Issac's 'fill the grid, use it to re-orient': ONE coherent orientation read from the WHOLE cell
    arrangement (global PCA + skew-consistent signs). Works even when individual nuclei are featureless
    -- the grid has structure the cells don't. Rotates with the crowd, so it cancels a swirl consistently."""
    p = (np.asarray(all_points, float) - np.asarray(all_points, float).mean(0)) * np.asarray(scale)
    _, V = np.linalg.eigh(p.T @ p)
    a = p @ V
    for k in range(3):                                               # global skew sign -> one consistent choice
        if (a[:, k] ** 3).sum() < 0:
            V[:, k] *= -1.0
    return V


def constellation_signature_gridframe(center, neighbors, gframe, scale, rings=(4.0, 9.0, 16.0, 28.0),
                                       n_az=8, n_el=3):
    """Constellation re-oriented by the GRID's global frame (same gframe for every cell in the frame)."""
    center = np.asarray(center, float); scale = np.asarray(scale, float)
    nb = np.asarray(neighbors, float)
    if nb.size == 0:
        return np.zeros(len(rings) * n_az * n_el)
    aligned = ((nb - center) * scale) @ np.asarray(gframe, float)
    return _hist_from_aligned(aligned, rings, n_az, n_el)


# the 4 proper-rotation (det=+1) sign frames -- the "semi-similar projections" of the aligned cloud
_PROPER_SIGNS = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)


def constellation_frames_sym(center, neighbors, scale, rings=(4.0, 9.0, 16.0, 28.0), n_az=8, n_el=3):
    """Return the constellation over ALL 4 semi-similar (proper-rotation) sign frames, resolving the PCA
    sign ambiguity that a single canonical frame leaves (the antipodal/spinor-like degeneracy)."""
    center = np.asarray(center, float); scale = np.asarray(scale, float)
    nb = np.asarray(neighbors, float)
    if len(nb) < 3:
        return [constellation_signature(center, neighbors, scale, rings, n_az, n_el)]
    rel = (nb - center) * scale
    cov = rel.T @ rel
    _, V = np.linalg.eigh(cov)
    base = rel @ V
    return [_hist_from_aligned(base * s, rings, n_az, n_el) for s in _PROPER_SIGNS]


def constellation_similarity_sym(frames_a, sig_b):
    """Match to the BEST semi-similar projection (max over the 4 proper-rotation sign frames)."""
    return max(constellation_similarity(fa, sig_b) for fa in frames_a)


def constellation_signature_cellframe(center, neighbors, cell_frame, scale, rings=(4.0, 9.0, 16.0, 28.0),
                                       n_az=8, n_el=3):
    """Constellation in the cell's OWN nucleus-frame (Issac: skew/vector of the wall->nucleus axis as the
    canonical reference). cell_frame = 3x3 orthonormal (the nucleus principal axes / polarity, cols=axes).
    A crowd swirl rotates the cell's frame WITH it, so the signature is EXACTLY invariant -- no PCA sign
    degeneracy, because the reference is physical/intrinsic, not a fragile statistic of the neighborhood."""
    center = np.asarray(center, float); scale = np.asarray(scale, float)
    nb = np.asarray(neighbors, float)
    if nb.size == 0:
        return np.zeros(len(rings) * n_az * n_el)
    rel = (nb - center) * scale
    aligned = rel @ np.asarray(cell_frame, float)                    # express neighbors in the cell's own frame
    return _hist_from_aligned(aligned, rings, n_az, n_el)


def constellation_signature_rotinv(center, neighbors, scale, rings=(4.0, 9.0, 16.0, 28.0), n_az=8, n_el=3):
    """ROTATION-INVARIANT constellation: align the neighbor cloud to its own principal axes first, so a
    swirling / rotating crowd still yields the same signature. Inner->outer rings preserved (multi-depth)."""
    center = np.asarray(center, float); scale = np.asarray(scale, float)
    nb = np.asarray(neighbors, float)
    if len(nb) < 3:
        return constellation_signature(center, neighbors, scale, rings, n_az, n_el)
    rel = (nb - center) * scale
    aligned = _pca_frame(rel)                                        # cancel the rotation
    d = np.linalg.norm(aligned, axis=1)
    sig = np.zeros((len(rings), n_az, n_el))
    for v, dist in zip(aligned, d):
        if dist < 1e-6:
            continue
        ring = int(np.searchsorted(rings, dist))
        if ring >= len(rings):
            continue
        az = np.arctan2(v[1], v[2]); el = np.arctan2(v[0], np.linalg.norm(v[1:]) + 1e-9)
        ai = int((az + np.pi) / (2 * np.pi + 1e-9) * n_az) % n_az
        ei = min(int((el + np.pi / 2) / (np.pi + 1e-9) * n_el), n_el - 1)
        sig[ring, ai, ei] += 1.0
    v = sig.ravel()
    return v / (np.linalg.norm(v) + 1e-6)


def constellation_signatures_for_frame(points, scale, gate_um=28.0, **kw):
    """Signature for every point in a frame (neighbors = the other points)."""
    pts = np.asarray(points, float)
    return [constellation_signature(pts[i], np.delete(pts, i, axis=0), scale, **kw) for i in range(len(pts))]


if __name__ == "__main__":
    # SELF-TEST: a crowd of identical cells. Does each cell's NEIGHBORHOOD constellation ID it across a
    # frame where the whole crowd drifts + jitters, better than it matches a *different* cell?
    rng = np.random.RandomState(3)
    scale = np.array([1.625, 0.40625, 0.40625])                       # real anisotropic voxel scale
    N = 40
    frame0 = rng.uniform(0, 60, size=(N, 3))                          # crowd of N cells (voxel coords)
    drift = np.array([0.0, 1.5, -1.0])                                # whole crowd drifts
    jitter = rng.normal(0, 0.6, size=(N, 3))                          # per-cell wobble
    frame1 = frame0 + drift + jitter                                  # next frame (same cells, moved)

    sig0 = constellation_signatures_for_frame(frame0, scale)
    sig1 = constellation_signatures_for_frame(frame1, scale)

    # For each cell: does its own constellation (t -> t+1) beat its similarity to OTHER cells?
    correct = 0
    self_sims, best_other = [], []
    for i in range(N):
        sims = np.array([constellation_similarity(sig0[i], sig1[j]) for j in range(N)])
        self_sims.append(sims[i])
        other = np.delete(sims, i)
        best_other.append(other.max())
        if sims.argmax() == i:                                        # nearest-constellation is itself
            correct += 1
    print(f"crowd N={N}: constellation nearest-neighbor self-ID = {correct}/{N} = {correct/N:.2f}")
    print(f"  mean self-sim (same cell across drift): {np.mean(self_sims):.3f}")
    print(f"  mean best-other-sim (nearest wrong cell): {np.mean(best_other):.3f}")
    print(f"  => neighborhood IDs the cell across drift: {np.mean(self_sims) > np.mean(best_other)}  "
          f"(margin {np.mean(self_sims) - np.mean(best_other):+.3f})")

    # ROTATION TEST: the crowd SWIRLS between frames (morphogenetic rotation), in the isotropic y-x plane.
    # Absolute-angle constellation should break; the PCA-aligned (rotation-invariant) one should hold.
    th = 0.6                                                          # ~34 deg swirl
    R = np.array([[1, 0, 0], [0, np.cos(th), -np.sin(th)], [0, np.sin(th), np.cos(th)]])
    ctr = frame0.mean(0)
    frame1r = (frame0 - ctr) @ R.T + ctr + drift + jitter            # whole crowd rotates + drifts + jitters

    def self_id(sig_fn):
        s0 = [sig_fn(frame0[i], np.delete(frame0, i, 0), scale) for i in range(N)]
        s1 = [sig_fn(frame1r[i], np.delete(frame1r, i, 0), scale) for i in range(N)]
        return sum(np.array([constellation_similarity(s0[i], s1[j]) for j in range(N)]).argmax() == i for i in range(N))

    orig = self_id(constellation_signature)
    rinv = self_id(constellation_signature_rotinv)
    print(f"\nROTATION TEST (crowd swirls {np.degrees(th):.0f} deg between frames):")
    print(f"  absolute-angle constellation self-ID: {orig}/{N}")
    print(f"  rotation-invariant self-ID:           {rinv}/{N}")
    print(f"  => invariance survives the swirl: {rinv > orig}  (+{rinv - orig} recovered)")

    # SYMMETRY-MATCHED: resolve the residual PCA sign degeneracy by matching up to the 4 semi-similar
    # (proper-rotation) projections -- the antipodal/spinor-like ambiguity your physics musing points at.
    f0 = [constellation_frames_sym(frame0[i], np.delete(frame0, i, 0), scale) for i in range(N)]
    s1r = [constellation_signature_rotinv(frame1r[i], np.delete(frame1r, i, 0), scale) for i in range(N)]
    sym = sum(np.array([constellation_similarity_sym(f0[i], s1r[j]) for j in range(N)]).argmax() == i for i in range(N))
    print(f"  symmetry-matched (up to the semi-similar projections): {sym}/{N}  (+{sym - rinv} over single-frame)")

    # CELL-FRAME (Issac's wall->nucleus polarity as the canonical reference): each cell carries its OWN
    # orientation that swirls WITH it -> cancels the rotation exactly, no fragile neighbor-cloud skew.
    def rand_rot(rs):
        Q, _ = np.linalg.qr(rs.randn(3, 3))
        if np.linalg.det(Q) < 0:
            Q[:, 0] *= -1
        return Q
    rs = np.random.RandomState(99)
    frames = [rand_rot(rs) for _ in range(N)]                        # each cell's nucleus orientation
    frames_rot = [R @ Q for Q in frames]                            # orientations swirl with the crowd
    cf0 = [constellation_signature_cellframe(frame0[i], np.delete(frame0, i, 0), frames[i], scale) for i in range(N)]
    cf1 = [constellation_signature_cellframe(frame1r[i], np.delete(frame1r, i, 0), frames_rot[i], scale) for i in range(N)]
    cf = sum(np.array([constellation_similarity(cf0[i], cf1[j]) for j in range(N)]).argmax() == i for i in range(N))
    print(f"  cell-frame (nucleus-orientation anchored): {cf}/{N}  (+{cf - rinv} over PCA-skew)")

    # GRID-FRAME (Issac: fill the grid, read ONE coherent orientation from the whole arrangement, re-orient
    # every cell by it). No per-nucleus orientation needed -- works when cells are featureless.
    gf0, gf1 = grid_frame(frame0, scale), grid_frame(frame1r, scale)
    gr0 = [constellation_signature_gridframe(frame0[i], np.delete(frame0, i, 0), gf0, scale) for i in range(N)]
    gr1 = [constellation_signature_gridframe(frame1r[i], np.delete(frame1r, i, 0), gf1, scale) for i in range(N)]
    gfr = sum(np.array([constellation_similarity(gr0[i], gr1[j]) for j in range(N)]).argmax() == i for i in range(N))
    print(f"  grid-frame (whole-grid re-orient, no nucleus needed): {gfr}/{N}  (+{gfr - rinv} over PCA-skew)")
