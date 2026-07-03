r"""shape_dataset.py -- turn the shape-chord generator into a LABELED AI dataset (Issac, 2026-06-27).

HONEST FRAMING (this is the real "use it for AI" path, and what it is NOT):
  * NOT for Suno: Suno is closed; you cannot train/fine-tune it on your data.
  * NOT enough/right to train a GENERATIVE music model (those need huge real-recording corpora;
    these are clean synthetic sine-chords with no timbre/rhythm).
  * IT IS a procedural generator of GROUND-TRUTH-LABELED audio: every clip ships with the exact
    shape, chord (pitch classes), note names, and frequencies that produced it. That makes a
    VERIFIABLE task: a model guesses the shape/chord from the sound, and you can PROVE it right
    or wrong because the label is the truth. Good for training/eval of a SMALL classifier, an
    auto-graded curriculum, or pitch/chord-detection -- not for a Suno-style generator.

Output: artifacts/shape_chords/dataset/audio/*.wav  +  labels.jsonl (one JSON label per clip).
Light augmentation (octave shift, gain, a little noise) so a classifier must generalize, not memorize.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import random
import sys
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import shape_music as sm           # noqa: E402
from shape_audio import freq, SR, write_wav  # noqa: E402

OUT = os.environ.get(
    "SCBE_SHAPE_DATASET_DIR",
    str(ROOT / "artifacts" / "shape_chords" / "dataset"),
)
N_CLIPS = int(os.environ.get("SCBE_SHAPE_DATASET_CLIPS", "36"))
random.seed(7)                      # reproducible


def make_clip(pcs, octave, gain, noise, dur=2.0):
    """Sines for the chord + envelope + light noise; return (int16 bytes, n_frames)."""
    n = int(SR * dur)
    atk, rel = int(0.03 * SR), int(0.2 * SR)
    raw = [0.0] * n
    peak = 0.0
    for i in range(n):
        t = i / SR
        s = sum(math.sin(2 * math.pi * freq(pc, octave) * t) for pc in pcs) / max(1, len(pcs))
        s += noise * (random.random() * 2 - 1)
        env = 1.0
        if i < atk:
            env = i / atk
        elif i > n - rel:
            env = max(0.0, (n - i) / rel)
        raw[i] = s * env * gain
        peak = max(peak, abs(raw[i]))
    scale = (0.85 * 32767) / (peak or 1.0)
    out = bytearray()
    for v in raw:
        iv = max(-32768, min(32767, int(v * scale)))
        out += iv.to_bytes(2, "little", signed=True)
    return bytes(out), n


def shape_catalog():
    """(shape name, dimension, pitch-class chord) for every shape we have."""
    cat = []
    for n in (3, 4, 5, 6, 8, 12):
        cat.append((f"{n}-gon", 2, sm.polygon_voice_chord(n)))
    for name, verts in sm.PLATONIC.items():
        cat.append((name.split(" (")[0], 3, sm.relations_chord(verts)[1]))
    for name, verts in sm.FOUR_D.items():
        cat.append((name.split(" (")[0], 4, sm.relations_chord(verts)[1]))
    return cat


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(os.path.join(OUT, "audio"), exist_ok=True)
    cat = shape_catalog()

    labels = []
    for i in range(N_CLIPS):
        name, dim, pcs = cat[i % len(cat)]
        octave = random.choice([3, 4, 5])
        gain = random.choice([0.7, 0.85, 1.0])
        noise = random.choice([0.0, 0.01, 0.03])
        frames, n = make_clip(pcs, octave, gain, noise)
        fname = f"clip_{i:03d}.wav"
        write_wav(os.path.join(OUT, "audio", fname), frames)
        labels.append({
            "file": f"audio/{fname}",
            "shape": name, "dimension": dim,
            "pitch_classes": pcs,
            "notes": [sm.NOTE[p] for p in pcs],
            "freqs_hz": [round(freq(p, octave), 2) for p in pcs],
            "n_notes": len(pcs), "octave": octave,
            "augment": {"gain": gain, "noise": noise},
        })

    with open(os.path.join(OUT, "labels.jsonl"), "w", encoding="utf-8") as f:
        for row in labels:
            f.write(json.dumps(row) + "\n")

    # VALIDATE: files exist, are real WAVs, and every label matches a file
    print(f"=== labeled shape-audio dataset -> {OUT} ===\n")
    print(f"  shapes covered: {len(cat)}   clips written: {len(labels)}")
    shapes_seen = sorted({r['shape'] for r in labels})
    print(f"  distinct labels: {shapes_seen}\n")
    ok = True
    checked = 0
    for row in labels:
        path = os.path.join(OUT, row["file"])
        if not os.path.exists(path):
            ok = False; print("   MISSING", path); continue
        with wave.open(path, "rb") as w:
            if w.getframerate() != SR or w.getnframes() < SR or w.getnchannels() != 1:
                ok = False; print("   BAD WAV", path)
        checked += 1
    print(f"  validated {checked}/{len(labels)} clips are real WAVs; labels.jsonl written "
          f"({os.path.getsize(os.path.join(OUT,'labels.jsonl'))} bytes)")

    print("\n  THE VERIFIABLE TASK this enables:")
    print("    input  = a .wav clip")
    print("    model guesses = the shape (and/or the chord/pitch-classes)")
    print("    grader = compare to labels.jsonl  ->  PROVABLY right or wrong (the label is ground truth)")
    print("\n  VERDICT:", "PASS -- a ground-truth-labeled audio dataset, ready for a small classifier."
          if ok else "FAIL")
    print("  HONEST: this trains/tests a CLASSIFIER on a defined task; it canNOT train Suno and is not a")
    print("          generative-music corpus. Scale N_CLIPS up for more data; it is unlimited and free.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
