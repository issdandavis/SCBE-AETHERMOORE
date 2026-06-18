"""The Instrument -- play a token-song; it manifests verified code in any language face.

A SONG is a sequence of NOTES. A MODE maps notes -> CA opcodes (a domain: "coding"
ships now; chemistry / movement / flight plug in the same way -- same keys, different
meaning, like major vs Mixolydian). The chain:

    notes --(mode/scale)--> op names --(CA table)--> opcode bytes
          --(tongue_isa.compile_ca_tokens)--> source in any FACE (python/rust/haskell/...)

Bijective: ``tongue_isa.disassemble`` reads the op-trace back out of the emitted source,
so we recover the SONG from the code (the scale runs both ways). The python face is also
executed, so the manifested value is VERIFIED by running, not claimed.

This is the Holophonor: you play the keys, it projects a working program.
"""

from __future__ import annotations

import os
from typing import Dict, List, Sequence

from .ca_opcode_table import OP_TABLE
from .tongue_isa import compile_ca_tokens, disassemble, runtime_prelude

# op name -> opcode byte (reverse of the CA table)
_NAME_TO_BYTE: Dict[str, int] = {entry.name: op_id for op_id, entry in OP_TABLE.items()}

# A MODE is a scale: note -> op name. Same keys, different domain meaning.
# "coding" is the first mode; add a dict here to add a mode (chemistry, movement, ...).
MODES: Dict[str, Dict[str, str]] = {
    "coding": {
        # diatonic: the everyday arithmetic ops
        "C": "add",
        "D": "sub",
        "E": "mul",
        "F": "div",
        "G": "inc",
        "A": "dec",
        "B": "neg",
        # chromatic: the rest of the playable op-set
        "C#": "mod",
        "D#": "abs",
        "F#": "eq",
        "G#": "lt",
        "A#": "gt",
    },
}


def modes() -> List[str]:
    return sorted(MODES)


def scale(mode: str = "coding") -> Dict[str, str]:
    return dict(MODES[mode])


def _op_to_note(mode: str) -> Dict[str, str]:
    return {op: note for note, op in MODES[mode].items()}


def notes_to_ops(song: str, mode: str = "coding") -> List[str]:
    sc = MODES[mode]
    ops: List[str] = []
    for tok in song.replace(",", " ").split():
        if tok not in sc:
            raise ValueError(f"note {tok!r} not in {mode} scale {sorted(sc)}")
        ops.append(sc[tok])
    return ops


def _assemble(prog, face: str) -> str:
    """Wrap the compiled body into a runnable/readable module for the face."""
    if face == "python":
        header = f"def {prog.fn_name}({', '.join(prog.arg_names)}):"
        body = "\n".join("    " + line for line in prog.body_lines)
        return runtime_prelude("python") + "\n\n" + header + "\n" + body + "\n"
    # non-python faces: emit prelude + body as a readable module (not executed here)
    return runtime_prelude(face) + "\n\n" + "\n".join(prog.body_lines) + "\n"


def _run_python(code: str, args: Sequence[float]):
    ns: Dict[str, object] = {}
    exec(code, ns)  # noqa: S102 - executing OUR OWN emitted code to verify it runs
    return ns["play"](*args)


def play(song: str, mode: str = "coding", face: str = "python", args: Sequence[float] = ()) -> dict:
    """Play a song in a mode; manifest it in a language face.

    Returns the manifested value (verified by running the python face), the emitted
    code, and the song read back out of that code (the bijection)."""
    ops = notes_to_ops(song, mode)
    tokens = [_NAME_TO_BYTE[op] for op in ops]
    arg_names = [f"x{i}" for i in range(len(args))]
    prog = compile_ca_tokens(tokens, target=face, fn_name="play", arg_names=arg_names)
    code = _assemble(prog, face)

    value = _run_python(code, args) if face == "python" else None

    o2n = _op_to_note(mode)
    song_back = " ".join(o2n.get(name, f"?{name}") for _, name in disassemble(code))
    normalized = " ".join(song.replace(",", " ").split())

    return {
        "song": song,
        "mode": mode,
        "face": face,
        "ops": ops,
        "value": value,
        "code": code,
        "song_back": song_back,
        "bijective": song_back == normalized,
    }


# --- conlang keys (sixtongues) + the melody view --------------------------------

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _sixtongues():
    """Lazy-load the sixtongues conlang codec (lives in packages/, not the scbe pkg)."""
    import importlib
    import sys

    p = os.path.join(_REPO, "packages", "sixtongues")
    if p not in sys.path:
        sys.path.insert(0, p)
    return importlib.import_module("sixtongues")


_INSTRUMENTS = ["piano", "strings", "brass", "woodwinds", "mallets", "synth"]


def _nm_to_hex(nm: float) -> str:
    """Approximate a visible wavelength (380-750 nm) as an RGB hex color."""
    if nm < 380 or nm > 750:
        r = g = b = 0.0
    elif nm < 440:
        r, g, b = -(nm - 440) / 60, 0.0, 1.0
    elif nm < 490:
        r, g, b = 0.0, (nm - 440) / 50, 1.0
    elif nm < 510:
        r, g, b = 0.0, 1.0, -(nm - 510) / 20
    elif nm < 580:
        r, g, b = (nm - 510) / 70, 1.0, 0.0
    elif nm < 645:
        r, g, b = 1.0, -(nm - 645) / 65, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    return "#" + "".join(f"{int(max(0.0, min(1.0, c)) * 255):02X}" for c in (r, g, b))


def keyspace(op_id: int) -> dict:
    """The full multi-sensory key for an op -- built in wavelengths. When the 12 notes
    run out, the instrument (op//12 band) and the color (light wavelength) keep all 64
    ops distinguishable: a key is a CHORD of pitch + timbre + color, not one note."""
    op_id = int(op_id) % 64
    midi = 48 + op_id
    hz = 440.0 * 2 ** ((midi - 69) / 12)
    nm = round(380 + op_id / 63 * 370, 1)
    return {
        "op_id": op_id,
        "note": _NOTE_NAMES[midi % 12] + str(midi // 12 - 1),
        "hz": round(hz, 2),
        "sound_wavelength_cm": round(34300.0 / hz, 2),  # 343 m/s in air
        "instrument": _INSTRUMENTS[(op_id // 12) % len(_INSTRUMENTS)],
        "light_nm": nm,  # visible wavelength
        "color": _nm_to_hex(nm),
    }


def pitch(op_id: int) -> dict:
    k = keyspace(op_id)
    return {"note": k["note"], "midi": 48 + (int(op_id) % 64), "hz": k["hz"]}


def melody(ops_bytes: Sequence[int]) -> List[dict]:
    return [keyspace(b) for b in ops_bytes]


def play_tongue(song_tokens: str, tongue: str = "ko", face: str = "python", args: Sequence[float] = ()) -> dict:
    """Play a song written in the CONLANG. sixtongues tokens decode to bytes, and the
    bytes ARE the op ids -- so the conlang is literally the keyboard. Bijective both
    ways: encode_bytes reads the song back out of the ops."""
    st = _sixtongues()
    ops_bytes = list(st.decode_tokens(song_tokens, tongue))
    arg_names = [f"x{i}" for i in range(len(args))]
    prog = compile_ca_tokens(ops_bytes, target=face, fn_name="play", arg_names=arg_names)
    code = _assemble(prog, face)
    value = _run_python(code, args) if face == "python" else None
    song_back = st.encode_bytes(bytes(ops_bytes), tongue)
    return {
        "song": song_tokens,
        "tongue": tongue,
        "face": face,
        "ops": [name for _, name in prog.op_trace],
        "op_bytes": ops_bytes,
        "value": value,
        "code": code,
        "song_back": song_back,
        "bijective": song_back.split() == song_tokens.split(),
        "melody": melody(ops_bytes),
    }


def faces() -> List[str]:
    """Every language face the instrument can emit to (polyglot + tongue_isa)."""
    langs = set()
    try:
        from .polyglot import languages as _pl

        langs.update(_pl())
    except Exception:
        pass
    try:
        from .tongue_isa import SUPPORTED_TARGETS

        langs.update(SUPPORTED_TARGETS)
    except Exception:
        pass
    return sorted(langs)


def emit_all(song: str, mode: str = "coding", args: Sequence[float] = ()) -> Dict[str, str]:
    """Play one song into EVERY available language. Best-effort + honest: each value is
    the emitted source, or 'ERROR: ...' if that face can't carry the song's ops."""
    ops = notes_to_ops(song, mode)
    tokens = [_NAME_TO_BYTE[op] for op in ops]
    argn = [f"x{i}" for i in range(len(args))]
    from .tongue_isa import SUPPORTED_TARGETS

    try:
        from . import polyglot as _pg
    except Exception:
        _pg = None

    out: Dict[str, str] = {}
    for face in faces():
        try:
            if face in SUPPORTED_TARGETS:
                prog = compile_ca_tokens(tokens, target=face, fn_name="play", arg_names=argn)
                out[face] = "\n".join(prog.body_lines)
            elif _pg is not None:
                out[face] = _pg.emit(tokens, face, fn_name="play", arg_names=argn)
            else:
                out[face] = "ERROR: no emitter for this face"
        except Exception as exc:
            out[face] = f"ERROR: {type(exc).__name__}: {exc}"
    return out


if __name__ == "__main__":
    r = play("C E", face="python", args=(10, 3, 2))
    print(f"play('C E') ops={r['ops']} value={r['value']} song_back={r['song_back']!r} bijective={r['bijective']}")
