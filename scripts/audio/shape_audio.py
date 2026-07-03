"""shape_audio.py -- HEAR the shape-chords. Synthesizes a .wav per shape from its chord
(Issac, 2026-06-27, "hear it"). Pure Python stdlib (wave + math) -> 16-bit PCM WAV, $0/local.

Each chord = a set of pitch classes (from shape_music). We turn pitch class -> real frequency
(A4 = 440 Hz), sum gentle sine waves with a soft attack/release envelope so it doesn't click,
normalize, and write a .wav you can double-click. The six tongues use their phi-weights as the
LOUDNESS of each note, so the heavier tongues literally ring louder.

VALIDATION: after writing, every file is reopened and checked (valid WAV header, non-zero
frames, expected duration) -- per the always-validate rule.
"""
from __future__ import annotations
import math
import os
from pathlib import Path
import sys
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import shape_music as sm  # noqa: E402

SR = 44100
OUT = os.environ.get(
    "SCBE_SHAPE_CHORD_WAV_DIR",
    str(ROOT / "artifacts" / "shape_chords" / "wav"),
)


def freq(pc: int, octave: int = 4) -> float:
    # A4 = 440 Hz sits at pitch class 9, octave 4
    return 440.0 * 2 ** ((pc - 9) / 12.0 + (octave - 4))


def synth(pcs, dur=2.6, octave=4, amps=None):
    """Sum sine waves for the chord's pitch classes, with a soft envelope; return int16 samples."""
    pcs = list(pcs)
    amps = list(amps) if amps else [1.0] * len(pcs)
    aw = sum(amps) or 1.0
    n = int(SR * dur)
    atk, rel = int(0.04 * SR), int(0.25 * SR)
    out = bytearray()
    peak = 0.0
    raw = [0.0] * n
    for i in range(n):
        t = i / SR
        s = sum(a * math.sin(2 * math.pi * freq(pc, octave) * t) for pc, a in zip(pcs, amps)) / aw
        # envelope
        env = 1.0
        if i < atk:
            env = i / atk
        elif i > n - rel:
            env = max(0.0, (n - i) / rel)
        raw[i] = s * env
        peak = max(peak, abs(raw[i]))
    scale = (0.85 * 32767) / (peak or 1.0)
    for v in raw:
        iv = int(v * scale)
        iv = max(-32768, min(32767, iv))
        out += iv.to_bytes(2, "little", signed=True)
    return bytes(out), n


def write_wav(path, frames):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(OUT, exist_ok=True)

    # build the playlist: (filename, label, pitch-classes, amps)
    jobs = []
    jobs.append(("01_triangle_augmented.wav", "triangle = augmented (floaty)", sm.polygon_voice_chord(3), None))
    jobs.append(("02_square_diminished.wav", "square = diminished-7th (tense)", sm.polygon_voice_chord(4), None))
    jobs.append(("03_pentagon.wav", "pentagon = 5-note set", sm.polygon_voice_chord(5), None))
    jobs.append(("04_hexagon_wholetone.wav", "hexagon = whole-tone (dreamy)", sm.polygon_voice_chord(6), None))
    jobs.append(("05_dodecagon_chromatic.wav", "12-gon = all 12 notes (chromatic cluster)", sm.polygon_voice_chord(12), None))
    jobs.append(("06_octahedron_crystal.wav", "octahedron = the Machine Crystal", sm.relations_chord(sm.PLATONIC["octahedron (our crystal)"])[1], None))
    jobs.append(("07_cube.wav", "cube", sm.relations_chord(sm.PLATONIC["cube"])[1], None))
    jobs.append(("08_dodecahedron.wav", "dodecahedron", sm.relations_chord(sm.PLATONIC["dodecahedron"])[1], None))
    jobs.append(("09_tesseract_4d.wav", "tesseract (4D)", sm.relations_chord(sm.FOUR_D["tesseract (4D cube)"])[1], None))
    # the six tongues: whole-tone chord, phi-weights = loudness per note
    phi_amps = [1.0, 1.618, 2.618, 4.236, 6.854, 11.09]
    jobs.append(("10_six_tongues_phi.wav", "the six tongues (phi-weighted loudness)", sm.polygon_voice_chord(6), phi_amps))

    print(f"=== hearing the shapes -> {OUT} ===\n")
    print(f"  {'file':32} {'notes':20} chord")
    rows = []
    for fname, label, pcs, amps in jobs:
        frames, n = synth(pcs, amps=amps)
        path = os.path.join(OUT, fname)
        write_wav(path, frames)
        notes = " ".join(sm.NOTE[p] for p in pcs)
        print(f"  {fname:32} {notes:20} {label}")
        rows.append((path, n))

    # VALIDATE: reopen each file, confirm it's a real WAV with the right length
    print("\n  validating written files:")
    ok = True
    for path, n_expected in rows:
        with wave.open(path, "rb") as w:
            nf, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
        good = (nf == n_expected and sr == SR and ch == 1 and sw == 2 and os.path.getsize(path) > 1000)
        ok &= good
        print(f"    {os.path.basename(path):32} {nf/sr:4.1f}s  {sr}Hz  {os.path.getsize(path)//1024} KB  "
              f"{'OK' if good else 'BAD'}")

    print("\n  VERDICT:", "PASS -- 10 playable .wav files written and validated." if ok else "FAIL")
    print(f"  HOW TO HEAR: open the folder {OUT} and double-click any file.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
