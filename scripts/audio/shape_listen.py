r"""shape_listen.py -- the scaled COMPARISON: an AI 'listener' guesses each clip's chord from the
raw audio, graded against the ground-truth labels (Issac, 2026-06-27, "scale a comparison at that
style and level").

This is the honest "use it for AI" demonstration: the generator makes ground-truth-labeled audio,
a listener must RECOVER the chord from sound alone, and we MEASURE it against a dumb baseline.

LISTENER (pure Python, no ML libs, $0): for each clip, use the Goertzel algorithm to measure
energy at the 12 pitch-class frequencies (summed across octaves 3-5, so it does NOT need to know
the octave), threshold relative to the loudest, and emit the detected set of pitch classes.

GRADER: compare the detected pitch-class SET to the label's pitch_classes -> exact match or not,
plus per-note precision/recall. BASELINE: always guess the single most-common chord (the floor).

HONEST: this measures a CHORD-RECOGNITION task (well-posed: the chord is literally in the audio).
SHAPE recognition is only recoverable up to chord-equivalence -- some different shapes share a
chord (octahedron and 16-cell both = {D#,F#}); we report that ambiguity rather than hide it. This
trains/evaluates a small classifier; it does not train Suno and is not a generative-music corpus.
"""
from __future__ import annotations
import array
import math
import os
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import shape_music as sm                       # noqa: E402
from shape_audio import freq, SR               # noqa: E402
from shape_dataset import make_clip, shape_catalog  # noqa: E402

random.seed(11)
N_CLIPS = int(os.environ.get("SCBE_SHAPE_LISTEN_CLIPS", "120"))
DS = 4                       # downsample factor for analysis
WIN = 0.6                    # seconds analyzed


def goertzel_power(samples, sr, f):
    w = 2 * math.pi * f / sr
    coeff = 2 * math.cos(w)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2 = s1; s1 = s0
    return s1 * s1 + s2 * s2 - coeff * s1 * s2


def listen(frames_bytes):
    """Hear a clip -> the set of pitch classes present (the chord), octave-independent."""
    pcm = array.array("h"); pcm.frombytes(frames_bytes)
    samples = [pcm[i] / 32768.0 for i in range(0, min(len(pcm), int(SR * WIN)), DS)]
    sr = SR / DS
    energy = []
    for pc in range(12):
        e = sum(goertzel_power(samples, sr, freq(pc, octv)) for octv in (3, 4, 5))
        energy.append(e)
    peak = max(energy) or 1.0
    return sorted(pc for pc in range(12) if energy[pc] > 0.30 * peak)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    cat = shape_catalog()

    # build the scaled, labeled set in memory (the generator is unlimited + free)
    clips = []
    for i in range(N_CLIPS):
        name, dim, pcs = cat[i % len(cat)]
        octave = random.choice([3, 4, 5])
        gain = random.choice([0.7, 0.85, 1.0])
        noise = random.choice([0.0, 0.01, 0.03])
        frames, _ = make_clip(pcs, octave, gain, noise, dur=WIN + 0.1)
        clips.append({"shape": name, "true": pcs, "frames": frames})

    print(f"=== scaled comparison: AI listener vs ground truth ({N_CLIPS} clips, {len(cat)} shapes) ===\n")

    # the listener guesses every clip; grade vs the label
    exact = tp = fp = fn = 0
    for c in clips:
        guess = listen(c["frames"])
        c["guess"] = guess
        if guess == c["true"]:
            exact += 1
        gt, gs = set(c["true"]), set(guess)
        tp += len(gt & gs); fp += len(gs - gt); fn += len(gt - gs)
    acc = exact / len(clips)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0

    # dumb baseline: always guess the most-common chord
    from collections import Counter
    common = Counter(tuple(c["true"]) for c in clips).most_common(1)[0][0]
    base = sum(1 for c in clips if tuple(c["true"]) == common) / len(clips)

    print(f"  LISTENER  exact-chord accuracy : {acc:5.1%}   ({exact}/{len(clips)})")
    print(f"            per-note precision    : {prec:5.1%}")
    print(f"            per-note recall       : {rec:5.1%}")
    print(f"  BASELINE  (always guess the most-common chord): {base:5.1%}  <- the floor to beat\n")

    # honesty: shape ambiguity -- which shapes are indistinguishable by chord alone
    by_chord = {}
    for name, dim, pcs in cat:
        by_chord.setdefault(tuple(pcs), []).append(name)
    collisions = {c: names for c, names in by_chord.items() if len(names) > 1}
    print("  HONEST -- shapes that share a chord (so chord alone can't tell them apart):")
    for c, names in collisions.items():
        print(f"    {' = '.join(names)}  ->  {' '.join(sm.NOTE[p] for p in c)}")
    if not collisions:
        print("    (none)")

    # a few example rows
    print("\n  examples (true -> heard):")
    for c in clips[:6]:
        t = " ".join(sm.NOTE[p] for p in c["true"])
        g = " ".join(sm.NOTE[p] for p in c["guess"])
        print(f"    {c['shape']:14} {t:20} -> {g:20} {'OK' if c['guess']==c['true'] else 'x'}")

    beat = acc > base
    print(f"\n  VERDICT: {'PASS' if beat else 'CHECK'} -- the listener {'beats' if beat else 'does NOT beat'} "
          f"the floor ({acc:.0%} vs {base:.0%}), graded against ground truth.")
    print("  This is what 'use it for AI' really means: a measured, checkable task. NOT Suno training,")
    print("  NOT a generative-music corpus -- a verifiable classifier benchmark the generator feeds for free.")
    return 0 if beat else 1


if __name__ == "__main__":
    raise SystemExit(main())
