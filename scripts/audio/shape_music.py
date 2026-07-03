"""shape_music.py -- shapes as chords, from a center-point system (Issac, 2026-06-27).

THE PLAIN IDEA: put a shape's corners as DIRECTIONS pointing out from one center. The ANGLE
between two corners is a musical INTERVAL. A shape's whole set of corner-relations = a CHORD.
"Negative" is not a minus sign here -- it is the OPPOSITE direction (an angle of 180 deg, the
antipode). Every real number (frequency in Hz, interval in cents) stays positive; only the
POSITION carries the sign. Going around the full circle (360 deg) = going up one octave.

WHAT IS COMPUTED (not recalled): each shape is defined by its corner COORDINATES; everything
else -- the angles between corners, the cents, the notes -- is computed from those coordinates,
so it checks itself. Works the same in 2D, 3D, and 4D (higher dimensions) because an angle
between two direction-vectors is defined in any dimension.

FIREWALL (honest): the rule "360 deg = one octave, angle -> cents -> nearest note" is a CHOSEN
instrument (a designed mapping), not a law of nature. The ANGLES are real geometry. The fact
that a regular polygon = an equal division of the octave = a known symmetric chord (triangle ->
augmented, square -> diminished-7th, hexagon -> whole-tone) is REAL music theory (Messiaen's
modes of limited transposition / equal temperament). Precedent for "shapes as music": Pythagoras
(ratios), Kepler, Harmonices Mundi (1619). We are picking an instrument, not discovering physics.
"""
from __future__ import annotations
import math

PHI = (1 + 5 ** 0.5) / 2
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# named symmetric chords (the famous polygon correspondences), keyed by the pitch-class set
NAMED = {
    frozenset([0, 6]): "tritone",
    frozenset([0, 4, 8]): "augmented triad",
    frozenset([0, 3, 6, 9]): "diminished 7th",
    frozenset([0, 2, 4, 6, 8, 10]): "whole-tone scale",
    frozenset(range(12)): "chromatic (all 12)",
    frozenset([0, 3, 6]): "diminished triad",
}


def angle_between(u, v):
    """Angle between two direction vectors, in degrees (works in any dimension)."""
    du = math.sqrt(sum(x * x for x in u))
    dv = math.sqrt(sum(x * x for x in v))
    if du == 0 or dv == 0:
        return 0.0
    c = sum(a * b for a, b in zip(u, v)) / (du * dv)
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def cents(angle_deg):
    """360 deg around the center = one octave (1200 cents)."""
    return angle_deg * (1200.0 / 360.0)


def pc_of(angle_deg):
    return round(cents(angle_deg) / 100.0) % 12


def name_chord(pcs):
    fs = frozenset(pcs)
    return NAMED.get(fs, f"{len(fs)}-note set")


# ---------- shape corner-coordinates ----------
def polygon(n):
    return [(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)]


def signs(vals):
    out = [[]]
    for v in vals:
        nxt = []
        for pre in out:
            if v == 0:
                nxt.append(pre + [0])
            else:
                nxt.append(pre + [v]); nxt.append(pre + [-v])
        out = nxt
    return [tuple(p) for p in out]


PLATONIC = {
    "tetrahedron": [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)],
    "octahedron (our crystal)": [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)],
    "cube": signs([1, 1, 1]),
    "icosahedron": ([(0, s1, s2 * PHI) for s1 in (1, -1) for s2 in (1, -1)]
                    + [(s1, s2 * PHI, 0) for s1 in (1, -1) for s2 in (1, -1)]
                    + [(s1 * PHI, 0, s2) for s1 in (1, -1) for s2 in (1, -1)]),
    "dodecahedron": (signs([1, 1, 1])
                     + [(0, s1 / PHI, s2 * PHI) for s1 in (1, -1) for s2 in (1, -1)]
                     + [(s1 / PHI, s2 * PHI, 0) for s1 in (1, -1) for s2 in (1, -1)]
                     + [(s1 * PHI, 0, s2 / PHI) for s1 in (1, -1) for s2 in (1, -1)]),
}

FOUR_D = {
    "16-cell (4D)": [tuple(1 if j == i else 0 for j in range(4)) for i in range(4)]
                    + [tuple(-1 if j == i else 0 for j in range(4)) for i in range(4)],
    "tesseract (4D cube)": signs([1, 1, 1, 1]),
    "24-cell (4D)": [p for p in signs([1, 1, 0, 0])
                     if sum(1 for x in p if x != 0) == 2 and p.index(next(x for x in p if x != 0)) >= 0],
}
# 24-cell = all permutations of (+-1,+-1,0,0); build cleanly:
def _24cell():
    pts = set()
    for i in range(4):
        for j in range(4):
            if i < j:
                for si in (1, -1):
                    for sj in (1, -1):
                        p = [0, 0, 0, 0]; p[i] = si; p[j] = sj
                        pts.add(tuple(p))
    return [list(p) for p in pts]
FOUR_D["24-cell (4D)"] = _24cell()


def relations_chord(verts):
    """The shape's chord = the set of DISTINCT angles between its corners (from the center)."""
    angles = set()
    for i in range(len(verts)):
        for j in range(i + 1, len(verts)):
            a = round(angle_between(verts[i], verts[j]), 1)
            if a > 0.01:
                angles.add(a)
    angles = sorted(angles)
    pcs = sorted({pc_of(a) for a in angles})
    return angles, pcs


def polygon_voice_chord(n):
    """The famous reading: each corner direction IS a note (360 deg = octave)."""
    return sorted({round(k * 12 / n) % 12 for k in range(n)})


ROT_ORDER = {3: 3, 4: 4, 5: 5, 6: 6, 8: 8, 12: 12,
             "tetrahedron": 12, "octahedron (our crystal)": 24, "cube": 24,
             "icosahedron": 60, "dodecahedron": 60}


def main() -> int:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    fails = []
    print("=== SHAPES AS CHORDS (center-point system; 'negative' = opposite direction, 360deg = octave) ===\n")

    print("  2D shapes -- each corner is a note (the famous one):")
    for n in (2, 3, 4, 5, 6, 8, 12):
        pcs = polygon_voice_chord(n)
        notes = " ".join(NOTE[p] for p in pcs)
        print(f"    {n}-gon: corners {360//n if 360%n==0 else round(360/n,1)} deg apart -> {notes:22} = {name_chord(pcs)}  (spins onto itself {ROT_ORDER.get(n,n)} ways)")
    # verify the famous correspondences
    for n, want in [(3, [0, 4, 8]), (4, [0, 3, 6, 9]), (6, [0, 2, 4, 6, 8, 10]), (12, list(range(12)))]:
        if polygon_voice_chord(n) != want:
            fails.append(f"polygon {n} chord {polygon_voice_chord(n)} != {want}")

    print("\n  3D shapes -- chord = the set of corner-to-corner angles (their 'relations'):")
    for name, verts in PLATONIC.items():
        angles, pcs = relations_chord(verts)
        notes = " ".join(NOTE[p] for p in pcs)
        ang_s = ", ".join(f"{a:g}" for a in angles[:6]) + ("..." if len(angles) > 6 else "")
        print(f"    {name:26} {len(verts):2} corners | angles [{ang_s}] deg -> {notes}")
    # verify a couple of known central angles
    oa = relations_chord(PLATONIC["octahedron (our crystal)"])[0]
    if 90.0 not in oa or 180.0 not in oa:
        fails.append(f"octahedron angles wrong: {oa}")
    ca = relations_chord(PLATONIC["cube"])[0]
    if not any(abs(a - 70.5) < 0.2 for a in ca):  # cube edge central angle = arccos(1/3)
        fails.append(f"cube angles wrong: {ca}")

    print("\n  4D shapes -- higher dimensions, same rule (angle between corners works in any D):")
    for name, verts in FOUR_D.items():
        angles, pcs = relations_chord(verts)
        notes = " ".join(NOTE[p] for p in pcs)
        ang_s = ", ".join(f"{a:g}" for a in angles[:6]) + ("..." if len(angles) > 6 else "")
        print(f"    {name:22} {len(verts):2} corners | angles [{ang_s}] deg -> {notes}")

    print("\n  OUR SHAPES:")
    hexc = polygon_voice_chord(6)
    print(f"    the six tongues = a HEXAGON (KO/AV/RU/CA/UM/DR at 0/60/120/180/240/300 deg)")
    print(f"      -> {' '.join(NOTE[p] for p in hexc)} = {name_chord(hexc)}; phi-weights (1,1.618,2.618,4.236,6.854,11.09) = how LOUD each note")
    print(f"    the Machine Crystal = the OCTAHEDRON above (its corner-angles are its chord)")

    print("\n  COMBINATIONS (superimpose = stack two shapes' corners -> a bigger chord):")
    for a, b in [("cube", "octahedron (our crystal)")]:
        verts = PLATONIC[a] + PLATONIC[b]
        angles, pcs = relations_chord(verts)
        print(f"    {a} + {b} (they are opposites/duals) -> {' '.join(NOTE[p] for p in pcs)}  "
              f"({len(angles)} distinct angles)")
    tri_sq = sorted(set(polygon_voice_chord(3)) | set(polygon_voice_chord(4)))
    print(f"    triangle + square stacked -> {' '.join(NOTE[p] for p in tri_sq)} = {name_chord(tri_sq)}")

    print("\n  ROTATIONS: spinning a shape onto itself does NOT change its chord (that IS its symmetry);")
    print("             spinning it part-way moves the whole chord up/down (a transpose).")

    print("\n  VERIFY:", "PASS -- chords computed from corner coordinates; the famous cases check"
          " out UNDER THIS MAPPING (360deg=octave)" if not fails else "FAIL")
    for f in fails:
        print("   -", f)
    print("  HONEST: the angle->note rule is a chosen instrument (360deg=octave); the ANGLES are real,")
    print("          computed from the corners. Polygon=symmetric-chord is real music theory; 'shapes as")
    print("          music' precedent = Pythagoras, Kepler's Harmonices Mundi (1619). Not a claim of physics.")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
