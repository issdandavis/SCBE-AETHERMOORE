"""The Instrument: play a token-song; it manifests verified code in any language face.

A song is a sequence of keys. A mode maps keys to CA opcodes: "coding" ships with
Western note names, and "ca" ships with the canonical Cassisivadan byte words from
the root ``scbe.py`` encoder. Chemistry, movement, or flight can plug in later as
different scales over the same opcode body. The chain is:

    notes -> mode/scale -> op names -> CA opcode bytes -> target-language source

The emitted source carries opcode trace comments, so ``tongue_isa.disassemble`` can
read the song back out of the code. The Python face is also executed, so that face is
verified by running rather than just emitted.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from .ca_opcode_table import OP_TABLE
from .tongue_isa import compile_ca_tokens, disassemble, runtime_prelude

_NAME_TO_BYTE: Dict[str, int] = {entry.name: op_id for op_id, entry in OP_TABLE.items()}

# Canonical CA byte words. Keep this table aligned with root scbe.py's
# _CANONICAL_TONGUES["ca"] encoder so the instrument's native keys are the real
# Cassisivadan spellings, not local placeholders.
_CA_PREFIXES = [
    "bip",
    "bop",
    "klik",
    "loopa",
    "ifta",
    "thena",
    "elsa",
    "spira",
    "rythm",
    "quirk",
    "fizz",
    "gear",
    "pop",
    "zip",
    "mix",
    "chass",
]
_CA_SUFFIXES = [
    "a",
    "e",
    "i",
    "o",
    "u",
    "y",
    "ta",
    "na",
    "sa",
    "ra",
    "lo",
    "mi",
    "ki",
    "zi",
    "qwa",
    "sh",
]

_CODING_SCALE: Dict[str, str] = {
    "C": "add",
    "D": "sub",
    "E": "mul",
    "F": "div",
    "G": "inc",
    "A": "dec",
    "B": "neg",
    "C#": "mod",
    "D#": "abs",
    "F#": "eq",
    "G#": "lt",
    "A#": "gt",
}


def ca_word_for_opcode(op_id: int) -> str:
    """Return the canonical Cassisivadan word for a CA opcode byte."""

    return f"{_CA_PREFIXES[(op_id >> 4) & 0xF]}'{_CA_SUFFIXES[op_id & 0xF]}"


def _ca_scale_for_ops(op_names: Sequence[str]) -> Dict[str, str]:
    return {ca_word_for_opcode(_NAME_TO_BYTE[op]): op for op in op_names}


MODES: Dict[str, Dict[str, str]] = {
    "ca": _ca_scale_for_ops(_CODING_SCALE.values()),
    "coding": _CODING_SCALE,
}


def modes() -> List[str]:
    """Return available instrument modes."""

    return sorted(MODES)


def scale(mode: str = "coding") -> Dict[str, str]:
    """Return the note-to-op scale for a mode."""

    return dict(MODES[mode])


def _op_to_note(mode: str) -> Dict[str, str]:
    return {op: note for note, op in MODES[mode].items()}


def notes_to_ops(song: str, mode: str = "coding") -> List[str]:
    """Map a note song like ``"C E"`` to CA op names like ``["add", "mul"]``."""

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
    return runtime_prelude(face) + "\n\n" + "\n".join(prog.body_lines) + "\n"


def _run_python(code: str, args: Sequence[float]):
    ns: Dict[str, object] = {}
    exec(
        code, ns
    )  # noqa: S102 - executing emitted code from this module to verify it runs.
    return ns["play"](*args)


def play(
    song: str, mode: str = "coding", face: str = "python", args: Sequence[float] = ()
) -> dict:
    """Play a song in a mode and manifest it in a language face."""

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


def main() -> int:
    r = play("C E", face="python", args=(10, 3, 2))
    print(
        f"play('C E') ops={r['ops']} value={r['value']} song_back={r['song_back']!r} bijective={r['bijective']}"
    )
    ca = play("bip'a bip'i", mode="ca", face="python", args=(10, 3, 2))
    print(
        f"play(\"bip'a bip'i\", mode='ca') ops={ca['ops']} value={ca['value']} "
        f"song_back={ca['song_back']!r} bijective={ca['bijective']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
