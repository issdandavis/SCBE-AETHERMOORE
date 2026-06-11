"""Test the mechanical tree (vision / touch / motor) — each by its own job.

These layers are NOT threat detectors. They are the system's body:

    VISION  (perspective_map)   -> does depth read true? (radius rises with depth,
                                   stays inside the ball)
    TOUCH   (pose_checker)      -> does it FEEL a broken hand? (drift rises when a
                                   pose is corrupted, graded not binary)
    MOTOR   (temporal_tracker +  -> does it TRACK motion away from intent, and does
             frame_corrector)      the correction PUSH BACK proportionally?

All runs hit the real src/video_lattice/ code. Run:
    PYTHONPATH=. python scripts/eval/mechanical_role_bench.py
"""

from __future__ import annotations

import numpy as np

from src.video_lattice import (
    FrameCorrector,
    FrameState,
    HandLandmark,
    Landmark,
    LatticeAxis,
    PerspectiveMap,
    PoseChecker,
    TemporalTracker,
)

rng = np.random.default_rng(11)


def spearman(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def line(name, role, test, value, verdict):
    print(f"  {name:11} {role:7} {test:30} {value:>11}   {verdict}")


def open_hand() -> list:
    """A plausible MediaPipe open right hand as an index-ordered list of 21
    landmarks (pose_checker enumerates the sequence, so order 0..20 matters)."""
    pts = {
        HandLandmark.WRIST: (0.50, 0.95),
        HandLandmark.THUMB_CMC: (0.44, 0.90), HandLandmark.THUMB_MCP: (0.39, 0.83),
        HandLandmark.THUMB_IP: (0.35, 0.77), HandLandmark.THUMB_TIP: (0.32, 0.72),
    }
    cols = {"INDEX": 0.46, "MIDDLE": 0.51, "RING": 0.56, "PINKY": 0.605}
    rows = {"MCP": 0.70, "PIP": 0.55, "DIP": 0.44, "TIP": 0.34}
    for f, x in cols.items():
        for r, y in rows.items():
            pts[HandLandmark[f + "_" + r]] = (x, y)
    return [Landmark(x=pts[HandLandmark(i)][0], y=pts[HandLandmark(i)][1], z=0.0) for i in range(21)]


def main():
    print("\n  layer       role    test                                 value   verdict")
    print("  " + "─" * 74)

    # ---- VISION: does depth read true? ----------------------------------- #
    pm = PerspectiveMap(max_depth=1.0)
    depths = np.linspace(0.0, 1.0, 40)
    radii = [pm.radius_for_depth(float(d)) for d in depths]
    s_depth = spearman(depths, radii)
    line("perspective", "VISION", "radius rises with depth", f"{s_depth:+.2f}",
         "DEPTH READS TRUE" if abs(s_depth) > 0.95 else "flat")
    line("perspective", "VISION", "stays in ball (r<1)", f"{max(radii):.4f}",
         "IN BALL" if max(radii) < 1.0 else "ESCAPES")

    # ---- TOUCH: does it feel a broken hand? ------------------------------ #
    checker = PoseChecker()
    ref = open_hand()
    TIP = int(HandLandmark.INDEX_TIP)  # landmark index 8
    good = [Landmark(l.x + 0.004 * rng.standard_normal(), l.y + 0.004 * rng.standard_normal()) for l in ref]
    bad = list(ref)
    bad[TIP] = Landmark(0.46, 0.86)  # fingertip bent back below its own knuckle
    d_good = checker.check_hand(ref, good).overall_drift
    bad_res = checker.check_hand(ref, bad)
    d_bad = bad_res.overall_drift
    line("pose_checker", "TOUCH", "good vs broken hand drift", f"{d_good:.2f}/{d_bad:.2f}",
         "FEELS THE BREAK" if d_bad > d_good * 3 else "numb")
    # graded: walk the fingertip out, drift must rise monotonically
    disp = np.linspace(0.0, 0.3, 25)
    drifts = []
    for dx in disp:
        g = list(ref)
        g[TIP] = Landmark(ref[TIP].x + float(dx), ref[TIP].y)
        drifts.append(checker.check_hand(ref, g).overall_drift)
    s_touch = spearman(disp, drifts)
    line("pose_checker", "TOUCH", "drift graded with damage", f"{s_touch:+.2f}",
         f"GRADED SENSE ({bad_res.verdict.value})" if s_touch > 0.95 else "binary/flat")

    # ---- MOTOR: track motion from intent + push back proportionally ------ #
    axes = list(LatticeAxis)
    base = {ax: rng.standard_normal(16) for ax in axes}
    tracker = TemporalTracker(dim=16, correction_threshold=2.0, intent_threshold=1.0)
    tracker.set_intent_anchor(base, "neutral pose")
    drift_in, intent_out = [], []
    for k in range(1, 26):
        mag = k * 0.15
        frame = {ax: base[ax] + mag * np.ones(16) for ax in axes}  # walk away from intent
        st = tracker.observe(frame)
        if st.intent_drift_by_axis:
            drift_in.append(mag)
            intent_out.append(max(st.intent_drift_by_axis.values()))
    s_motor = spearman(drift_in, intent_out)
    violations = len(tracker.intent_violations())
    line("temporal_trk", "MOTOR", "tracks motion from target", f"{s_motor:+.2f}",
         f"TRACKS ({violations} violations flagged)" if s_motor > 0.95 else "loses target")

    # corrector: cost + restoring signal must scale with drift (proportional control)
    corrector = FrameCorrector(tracker)
    dd = np.linspace(0.1, 3.0, 25)
    costs, pushes = [], []
    for d in dd:
        state = FrameState(frame_index=0, aggregate_drift=float(d), correction_triggered=d > 2.0,
                           max_drift_axis=LatticeAxis.MOTION, drift_by_axis={LatticeAxis.MOTION: float(d)})
        sig = corrector.correct(state)
        costs.append(sig.cost_signal)
        pushes.append(abs(sig.axis_corrections.get("motion", 0.0)))
    s_cost = spearman(dd, costs)
    s_push = spearman(dd, pushes)
    line("frame_corr", "MOTOR", "push-back grows with error", f"{s_push:+.2f}",
         "PROPORTIONAL CONTROL" if s_cost > 0.95 and s_push > 0.95 else "weak")

    print("  " + "─" * 74)
    print("  vision reads depth, touch feels a broken pose (graded), motor tracks")
    print("  drift from intent and pushes back harder the further it strays.\n")


if __name__ == "__main__":
    main()
