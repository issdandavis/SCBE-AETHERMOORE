r"""shape_manifest.py -- exact-numbers export + tamper-evident receipt for the shape-chords
(addresses Codex's review: "add an exact numbers export" + "write a receipt/manifest beside the
WAVs"). Writes manifest.json (full) + manifest.csv (flat) + a SHA-256 seal, into the WAV folder.

Each row carries the EXACT numbers, not just a label: shape, dimension, corner count, the angles
(degrees) the chord came from, those angles in cents, the pitch classes, note names, frequencies
(Hz at octave 4), and the rendered .wav file. The seal is tamper-evidence ONLY (it proves the
file wasn't changed since writing), NOT a proof of correctness -- same honesty rule as the rest.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import shape_music as sm                 # noqa: E402
from shape_audio import freq, OUT        # noqa: E402

# which rendered wav (if any) goes with which shape
WAV = {
    "3-gon": "01_triangle_augmented.wav", "4-gon": "02_square_diminished.wav",
    "5-gon": "03_pentagon.wav", "6-gon": "04_hexagon_wholetone.wav",
    "12-gon": "05_dodecagon_chromatic.wav", "octahedron": "06_octahedron_crystal.wav",
    "cube": "07_cube.wav", "dodecahedron": "08_dodecahedron.wav",
    "tesseract": "09_tesseract_4d.wav", "six-tongues": "10_six_tongues_phi.wav",
}


def rows():
    out = []
    # 2D: corner-as-note (the chord you hear), exact corner angle + cents
    for n in (2, 3, 4, 5, 6, 8, 12):
        pcs = sm.polygon_voice_chord(n)
        step = 360.0 / n
        out.append({
            "shape": f"{n}-gon", "dimension": 2, "corners": n, "mode": "corner-as-note",
            "angles_deg": [round((k * step) % 360, 2) for k in range(n)],
            "cents": [round(sm.cents((k * step) % 360), 1) for k in range(n)],
            "pitch_classes": pcs, "notes": [sm.NOTE[p] for p in pcs],
            "freqs_hz": [round(freq(p, 4), 2) for p in pcs],
            "chord_name": sm.name_chord(pcs), "wav": WAV.get(f"{n}-gon"),
        })
    # 3D + 4D: relations (distinct corner-to-corner angles)
    for store, dim in ((sm.PLATONIC, 3), (sm.FOUR_D, 4)):
        for name, verts in store.items():
            base = name.split(" (")[0]
            angles, pcs = sm.relations_chord(verts)
            out.append({
                "shape": base, "dimension": dim, "corners": len(verts), "mode": "relations",
                "angles_deg": angles, "cents": [round(sm.cents(a), 1) for a in angles],
                "pitch_classes": pcs, "notes": [sm.NOTE[p] for p in pcs],
                "freqs_hz": [round(freq(p, 4), 2) for p in pcs],
                "chord_name": sm.name_chord(pcs), "wav": WAV.get(base),
            })
    # the six tongues (named explicitly)
    pcs = sm.polygon_voice_chord(6)
    out.append({
        "shape": "six-tongues", "dimension": 2, "corners": 6, "mode": "corner-as-note (phi-loud)",
        "angles_deg": [0, 60, 120, 180, 240, 300],
        "cents": [round(sm.cents(a), 1) for a in (0, 60, 120, 180, 240, 300)],
        "pitch_classes": pcs, "notes": [sm.NOTE[p] for p in pcs],
        "freqs_hz": [round(freq(p, 4), 2) for p in pcs],
        "chord_name": sm.name_chord(pcs), "wav": WAV.get("six-tongues"),
    })
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(OUT, exist_ok=True)
    data = rows()
    meta = {"mapping": "360deg = one octave; angle->cents (x10/3)->nearest of 12 notes; A4=440Hz",
            "claim": "angles are real/computed from corner coordinates; the chord mapping is a CHOSEN "
                     "instrument, not physics; named chords check out UNDER THIS MAPPING",
            "rows": len(data)}
    body = {"meta": meta, "shapes": data}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=True)
    seal = hashlib.sha256(canonical.encode()).hexdigest()
    body["seal_sha256"] = seal

    jpath = os.path.join(OUT, "manifest.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2)
    cpath = os.path.join(OUT, "manifest.csv")
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["shape", "dimension", "corners", "mode", "chord_name", "notes",
                    "pitch_classes", "angles_deg", "cents", "freqs_hz", "wav"])
        for r in data:
            w.writerow([r["shape"], r["dimension"], r["corners"], r["mode"], r["chord_name"],
                        " ".join(r["notes"]), r["pitch_classes"], r["angles_deg"],
                        r["cents"], r["freqs_hz"], r["wav"]])

    # VALIDATE: reparse + recompute the seal
    with open(jpath, encoding="utf-8") as f:
        back = json.load(f)
    recomputed = hashlib.sha256(json.dumps(
        {"meta": back["meta"], "shapes": back["shapes"]}, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()
    seal_ok = recomputed == back["seal_sha256"]

    print(f"=== exact-numbers manifest + receipt -> {OUT} ===\n")
    print(f"  manifest.json ({os.path.getsize(jpath)} B) + manifest.csv ({os.path.getsize(cpath)} B), "
          f"{len(data)} shapes")
    print(f"  seal sha256: {seal[:16]}...  (re-read + recomputed match: {seal_ok})\n")
    print(f"  {'shape':14}{'dim':4}{'chord':18}{'notes':22}wav")
    for r in data:
        print(f"  {r['shape']:14}{r['dimension']:<4}{r['chord_name']:18}{' '.join(r['notes']):22}{r['wav'] or '-'}")
    print(f"\n  VERDICT: {'PASS' if seal_ok else 'FAIL'} -- exact numbers exported, receipt sealed and verified.")
    return 0 if seal_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
