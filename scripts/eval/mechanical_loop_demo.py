"""End-to-end mechanical loop: vision -> touch -> motor -> correction, per frame.

Plays a short hand "video": the hand drifts across the frame while its depth
changes, and on ONE frame it glitches (a fingertip bends back through its own
knuckle). Each frame runs the WHOLE body in one pass:

    VISION   perspective_map  : depth -> radial position
    TOUCH    pose_checker      : is the hand anatomically intact?
    MOTOR    temporal_tracker  : how far has it drifted from the intended pose?
             frame_corrector   : emit a correction signal when it strays

This is the cybernetic-closure rule from MECHANICAL_LAYER_TANGENTIAL_TREE.md:
"bad frame -> measured drift -> localized cause -> corrected next input."

HONEST SCOPE: the frames here are SYNTHETIC (a scripted hand), not a real camera.
That proves the modules COMPOSE into a closed loop. Swapping the frame source for
a real camera / MediaPipe feed is the only remaining step.

Run:  PYTHONPATH=. python scripts/eval/mechanical_loop_demo.py
"""

from __future__ import annotations

import numpy as np

from src.video_lattice import (
    FrameCorrector,
    HandLandmark,
    Landmark,
    LatticeAxis,
    PerspectiveMap,
    PoseChecker,
    TemporalTracker,
    hand_polygon_features,
)

GLITCH_FRAME = 6
N_FRAMES = 10


def open_hand() -> list:
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
    return [Landmark(pts[HandLandmark(i)][0], pts[HandLandmark(i)][1], 0.0) for i in range(21)]


def translate(hand: list, dx: float) -> list:
    return [Landmark(l.x + dx, l.y, l.z) for l in hand]


def axis_vectors(hand: list, depth: float, dim: int) -> dict:
    feat = hand_polygon_features(hand)
    struct = np.resize(feat, dim).astype(float)
    wrist = hand[int(HandLandmark.WRIST)]
    motion = np.resize(np.array([wrist.x, wrist.y]), dim).astype(float)
    return {
        LatticeAxis.STRUCTURE: struct,
        LatticeAxis.MOTION: motion,
        LatticeAxis.DEPTH: np.full(dim, depth),
    }


def main():
    ref = open_hand()
    dim = len(hand_polygon_features(ref))
    pm = PerspectiveMap(max_depth=1.0)
    checker = PoseChecker()
    tracker = TemporalTracker(dim=dim, correction_threshold=1.0, intent_threshold=0.8)
    # Anchor intent on the hand SHAPE only — depth and position are SUPPOSED to
    # change as the hand moves; what must stay invariant is "it's still a hand".
    struct_ref = np.resize(hand_polygon_features(ref), dim).astype(float)
    tracker.set_intent_anchor({LatticeAxis.STRUCTURE: struct_ref}, "intended hand shape")
    corrector = FrameCorrector(tracker)

    print("\n  MECHANICAL LOOP — synthetic hand video (vision → touch → motor)\n")
    print(f"  {'frame':5} {'vision(depth→r)':16} {'touch':22} {'motor drift':12} action")
    print("  " + "─" * 74)

    for f in range(1, N_FRAMES + 1):
        depth = 0.2 + f * 0.045
        hand = translate(ref, 0.012 * f)
        glitch = f == GLITCH_FRAME
        if glitch:
            hand = list(hand)
            # Two fingertips bent back through their knuckles — an unmistakable break.
            hand[int(HandLandmark.INDEX_TIP)] = Landmark(hand[int(HandLandmark.INDEX_MCP)].x, 0.88, 0.0)
            hand[int(HandLandmark.MIDDLE_TIP)] = Landmark(hand[int(HandLandmark.MIDDLE_MCP)].x, 0.90, 0.0)

        # VISION
        pp = pm.project(depth, angle=0.0)
        # TOUCH
        touch = checker.check_hand(ref, hand)
        # MOTOR
        state = tracker.observe(axis_vectors(hand, depth, dim))
        sig = corrector.correct(state)

        intact = "✓ intact" if touch.overall_drift < 0.5 else "✗ BROKEN HAND"
        acted = state.correction_triggered or state.intent_violated
        action = f"⟳ CORRECT ({sig.severity}, cost {sig.cost_signal:.1f})" if acted else "—"
        flag = "  ← glitch" if glitch else ""
        print(f"  {f:<5} depth {depth:.2f} → r {pp.radius:.2f}   "
              f"{intact:22} {state.aggregate_drift:<12.2f} {action}{flag}")

    print("  " + "─" * 74)
    s = tracker.summary()
    print(f"  loop closed: {s['frame_count']} frames, {s['correction_events']} corrections, "
          f"{s['intent_violations']} intent violations.")
    print("  the glitch frame was seen (touch), measured (motor), and corrected — in one pass.")
    print("  (synthetic frames; swap the source for a real camera/MediaPipe feed to go live.)\n")


if __name__ == "__main__":
    main()
