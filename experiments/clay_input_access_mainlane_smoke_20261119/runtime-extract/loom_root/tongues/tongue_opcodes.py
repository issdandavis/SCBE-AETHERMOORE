"""tongue_opcodes.py — render ANY opcode in EACH of the six tongues, so they LOOK and READ
differently (Issac, 2026-06-27: "why are they all the same language ... they should look and
read different as opcodes AND any codes").

THE BUG this fixes: ca_word_for_opcode() returns CASSISIVADAN words (bip'a/klik'ra/...) because
CA is the system's compute tongue. Binding all six tongues to those words made six languages
read as one. Here each tongue gets its OWN phonology, so the same byte renders distinctly.

DESIGN: every byte b -> onset[b>>4] + joiner + coda[b & 0xF]. Distinct onset/coda palettes +
distinct joiners give each tongue an unmistakable look. The map is BIJECTIVE (render<->parse
round-trips), so each tongue is a real reversible language skin over the one instruction set,
not decoration. "Any code" generalizes: this works for every byte, not just the 6 signatures.

FIREWALL (designed != pre-existing): CA is the EXISTING authentic system language (we defer to
scbe.ca_word_for_opcode). KO/AV/RU/UM/DR are phonologies I CONSTRUCTED here from each tongue's
lore sound-palette (the signature songs: Kor'aelin/Sil'thara, Avela toma, Ru'vaneth tal,
Umbra kael, Draum keth tharn). They are real in that they round-trip and are deterministic;
they are NEW (built today), not recovered from a prior lexicon. Distinct look is the whole point.
"""
from __future__ import annotations
import sys
from pathlib import Path

_SCBE_PYTHON_CANDIDATES = (
    Path(r"C:\Users\issda\SCBE-AETHERMOORE\python"),
    Path(r"C:\dev\.repos_clone\SCBE-AETHERMOORE\python"),
    Path(r"C:\Users\issda\instrument-wt\python"),
)

# 16 onsets (high nibble) + 16 codas (low nibble) + a joiner, per constructed tongue.
# Palettes are deliberately disjoint so each tongue reads unmistakably different.
PHON = {
    "KO": {  # Kor'aelin -- liquid, warm; apostrophe joiner (canonical Kor'aelin/Sil'thara look)
        "join": "'",
        "onset": ["kor","sil","ael","nav","lae","mer","vel","nia","mor","lir","ven","sae","rol","nim","vae","lor"],
        "coda":  ["a","el","in","or","ae","il","en","ar","oth","aen","een","ira","oan","ull","eir","aon"],
    },
    "AV": {  # Avali -- open, flowing; space joiner (Avela toma reads as separated open syllables)
        "join": " ",
        "onset": ["ava","ela","toma","lae","vea","nima","oli","ame","veli","tao","mira","aelo","nuvi","ova","lema","tuva"],
        "coda":  ["la","ra","no","mi","va","le","tu","na","lor","vee","mae","ria","noa","lia","veo","sai"],
    },
    "RU": {  # Runethic / Ru'khari -- heavy, runic, guttural kh/th; apostrophe joiner
        "join": "'",
        "onset": ["ru","khar","vaneth","thal","dur","khor","vath","rune","dhol","khen","vra","thun","dro","khae","vael","run"],
        "coda":  ["tal","khi","eth","un","ar","oth","em","ash","ull","enth","ord","akh","ein","uth","olm","arn"],
    },
    "UM": {  # Umbroth / Umbriel -- hollow, melancholy; NO joiner (seamless), onsets prefix-free
        "join": "",
        "onset": ["umbra","kael","mor","bel","thren","lun","nael","bro","moir","luth","vael","nim","brae","thol","mell","umbro"],
        "coda":  ["eth","ael","or","un","ill","ohm","are","ull","enn","oth","eir","umn","esh","oll","aer","ynd"],
    },
    "DR": {  # Draumric -- hard, forged d/k/th/g; hyphen joiner (riveted look)
        "join": "-",
        "onset": ["draum","keth","tharn","dor","grak","thol","dru","korr","tav","gron","dreth","kaul","thrau","dag","gorn","drak"],
        "coda":  ["ar","eth","orn","uk","al","ek","un","ath","ohr","ekt","urn","akh","eld","ost","agg","urk"],
    },
}


def _scbe():
    scbe_python = next(
        (path for path in _SCBE_PYTHON_CANDIDATES if (path / "scbe").is_dir()),
        None,
    )
    if scbe_python is None:
        searched = ", ".join(str(path) for path in _SCBE_PYTHON_CANDIDATES)
        raise FileNotFoundError(f"SCBE Python package not found; searched: {searched}")
    scbe_path = str(scbe_python)
    if scbe_path not in sys.path:
        sys.path.insert(0, scbe_path)
    from scbe.instrument import _NAME_TO_BYTE, ca_word_for_opcode
    return _NAME_TO_BYTE, ca_word_for_opcode


def render(code: str, byte: int, ca_word=None) -> str:
    """The word for opcode `byte` in tongue `code`. CA defers to the authentic system word."""
    if code == "CA":
        if ca_word is None:
            _, ca_word = _scbe()
        return ca_word(byte)
    p = PHON[code]
    return p["onset"][byte >> 4] + p["join"] + p["coda"][byte & 0xF]


_CA_INV_CACHE = None


def _ca_inverse():
    """CA word -> byte, DERIVED from the forward function rather than imported.

    BUG THIS FIXES, measured 2026-08-04. Callers reached for `_scbe()[0]` as the CA inverse,
    but that is `_NAME_TO_BYTE` -- the opcode MNEMONIC map, 64 entries keyed 'add', 'sub',
    'mul', 'div'. It is not Cassisivadan words at all: overlap with what ca_word_for_opcode
    actually emits is ZERO, so parse("CA", w, _NAME_TO_BYTE) raised KeyError for every byte,
    and clay_crosslingual_demo.py:117 calls parse(code, word) with no ca_inv at all, which
    made it TypeError on None.

    CA itself was never broken: 256 bytes -> 256 distinct words, no collisions, and the
    inverse derived here round-trips 256/256. Deriving it removes the chance of the two maps
    drifting apart again, which is how this broke in the first place.
    """
    global _CA_INV_CACHE
    if _CA_INV_CACHE is None:
        _, ca_word = _scbe()
        _CA_INV_CACHE = {ca_word(b): b for b in range(256)}
    return _CA_INV_CACHE


def parse(code: str, word: str, ca_inv=None) -> int:
    """Inverse of render. CA uses ca_inv if given, else the derived inverse (see _ca_inverse)."""
    if code == "CA":
        return (ca_inv or _ca_inverse())[word]
    p = PHON[code]
    j = p["join"]
    if j:
        on, co = word.split(j, 1)
    else:  # seamless tongue: match the longest onset prefix
        on = max((o for o in p["onset"] if word.startswith(o)), key=len)
        co = word[len(on):]
    return (p["onset"].index(on) << 4) | p["coda"].index(co)


# the 6 signature opcodes from tongues_canon, each shown in ITS OWN tongue
SIGNATURE = {"KO": ("add", 0x00), "AV": ("cmp", 0x26), "RU": ("within", 0x2A),
             "CA": ("mul", 0x02), "UM": ("sub", 0x01), "DR": ("clamp", 0x29)}
ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
NAMES = {"KO": "Kor'aelin", "AV": "Avali", "RU": "Runethic",
         "CA": "Cassisivadan", "UM": "Umbroth", "DR": "Draumric"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    failures = []

    name_to_byte, ca_word = _scbe()
    ca_inv = {ca_word(b): b for b in name_to_byte.values()}
    real_bytes = sorted(set(name_to_byte.values()))
    byte_to_op = {b: n for n, b in name_to_byte.items()}

    print("=== one instruction set, six tongues -- each reads differently ===\n")

    # 1. each tongue's SIGNATURE opcode, in its native tongue
    print("  signature opcode, in its OWN tongue:")
    print(f"    {'tongue':14} {'op':7} {'byte':5} word")
    for code in ORDER:
        op, b = SIGNATURE[code]
        w = render(code, b, ca_word)
        tag = "  (authentic system word)" if code == "CA" else ""
        print(f"    {NAMES[code]:14} {op:7} 0x{b:02X}  {w}{tag}")

    # 2. the SAME opcode across all six tongues -> six different looks
    print("\n  the SAME code (mul, 0x02) spoken in all six tongues:")
    forms = [render(c, 0x02, ca_word) for c in ORDER]
    print("    " + "   ".join(f"{c}:{f}" for c, f in zip(ORDER, forms)))
    if len(set(forms)) != len(forms):
        failures.append("mul renders identically in two tongues (not distinct)")

    # 3. a handful of real opcodes x six tongues (proves it generalizes to ANY code)
    sample = [b for b in (0x00, 0x01, 0x02, 0x26, 0x29, 0x2A) if b in byte_to_op]
    print("\n  any code, six tongues:")
    print(f"    {'op':8} {'byte':5} " + " ".join(f"{c:>12}" for c in ORDER))
    for b in sample:
        row = [render(c, b, ca_word) for c in ORDER]
        print(f"    {byte_to_op[b]:8} 0x{b:02X}  " + " ".join(f"{w:>12}" for w in row))

    # 4. VERIFY bijective round-trip for every real opcode in every tongue
    rt_fail = 0
    for code in ORDER:
        for b in real_bytes:
            w = render(code, b, ca_word)
            back = parse(code, w, ca_inv)
            if back != b:
                rt_fail += 1
                if rt_fail <= 5:
                    failures.append(f"{code} round-trip 0x{b:02X} -> {w!r} -> 0x{back:02X}")
    # 5. VERIFY cross-tongue distinctness for every real opcode
    dist_fail = 0
    for b in real_bytes:
        forms = [render(c, b, ca_word) for c in ORDER]
        if len(set(forms)) != len(forms):
            dist_fail += 1
    print(f"\n  round-trip: {len(real_bytes)} opcodes x {len(ORDER)} tongues, "
          f"{'all reversible' if rt_fail == 0 else str(rt_fail)+' FAILED'}")
    print(f"  distinctness: {len(real_bytes)} opcodes, "
          f"{'all six forms differ' if dist_fail == 0 else str(dist_fail)+' had a collision'}")
    if dist_fail:
        failures.append(f"{dist_fail} opcodes had identical forms across tongues")

    print()
    if failures:
        print("  SELF-TEST: FAIL")
        for f in failures[:8]:
            print("   -", f)
        return 1
    print("  SELF-TEST: PASS (six distinct languages; every code reversible in each; CA authentic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
