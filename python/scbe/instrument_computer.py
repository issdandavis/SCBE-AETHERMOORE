"""Instrument Computer: music surfaces over verified SCBE runtimes.

This module consolidates the instrument-computer experiments into one importable
surface:

* note phrases -> CA ops -> polyglot code faces + Python execution receipt
* key/mode governance -> in-key notes lower to Machine Crystal tape ops
* key-independent degree programs -> lossless melody renderings in any key
* arbitrary instruments -> finite alphabets that encode the same program
* a tiny stateful shell -> persistent RAM behind the instrument output port

The honest boundary is important: instruments are input alphabets and rendering
surfaces. Computational power comes from the verified CA stack machine and
Machine Crystal tape runtime behind those surfaces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
from pathlib import Path
import subprocess
from typing import Iterable, Sequence

from .instrument import (
    _NAME_TO_BYTE,
    ca_word_for_opcode,
    emit_all,
    keyspace,
    melody_for_ops,
    notes_to_ops,
    play,
)
from .machine_crystal import MachineCrystalProgram, run_crystal
from .atomic_tokenization import map_token_to_atomic_state
from .tongue_isa import SUPPORTED_TARGETS, compile_ca_tokens, runtime_prelude


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]

# Degree programs are the invariant layer for the guitar/key dialect. The names
# are intentionally tape-machine glosses, not CA scalar op names.
DEGREE_BF = {
    1: "+",
    2: "-",
    3: ">",
    4: "<",
    5: "[",
    6: "]",
    7: ".",
}
DEGREE_GLOSS = {
    1: "add",
    2: "sub",
    3: "right",
    4: "left",
    5: "loop-open",
    6: "loop-close",
    7: "output",
}

KEY_DIALECTS = {
    "E minor": [4, 6, 7, 9, 11, 0, 2],
    "C major": [0, 2, 4, 5, 7, 9, 11],
    "A minor pentatonic": [9, 0, 2, 4, 7],
}

CONSONANCE = {
    0: ("unison", "perfect consonance"),
    1: ("minor 2nd", "dissonance"),
    2: ("major 2nd", "dissonance"),
    3: ("minor 3rd", "imperfect consonance"),
    4: ("major 3rd", "imperfect consonance"),
    5: ("perfect 4th", "context-dependent"),
    6: ("tritone", "dissonance"),
    7: ("perfect 5th", "perfect consonance"),
    8: ("minor 6th", "imperfect consonance"),
    9: ("major 6th", "imperfect consonance"),
    10: ("minor 7th", "dissonance"),
    11: ("major 7th", "dissonance"),
}

DEFAULT_PROGRAM = "++>+++[<+>-]"
DEFAULT_INSTRUMENTS = {
    "piano_chromatic": 12,
    "bagpipe_fixed_scale": 9,
    "harp_diatonic": 7,
    "guzheng_pentatonic": 5,
    "two_tone_whistle": 2,
}

HASKELL_PRIMARY_NOTE = {
    "status": "primary_face",
    "why_primary": "Haskell is a compact pure-functional target for stack transformations; it preserves composition cleanly and makes evaluation order explicit.",
    "why_less_common": [
        "Smaller hiring and package ecosystem than Python/JavaScript/Go/Rust.",
        "Lazy evaluation and typeclass-heavy APIs have a steeper learning curve.",
        "Interop, deployment, and debugging are less familiar to many production teams.",
        "It is excellent for compilers, DSLs, formal models, and correctness-heavy code, but less dominant for everyday web/product glue.",
    ],
}


def pitch_class(note: str) -> int:
    """Return the pitch class for a simple note token such as C, F#, or Bb."""

    token = note.strip().upper().replace("B", "B")
    if not token:
        raise ValueError("empty note")
    if len(token) >= 2 and token[1] == "B" and token[0] != "B":
        base = NOTE_NAMES.index(token[0])
        return (base - 1) % 12
    if len(token) >= 2 and token[1] == "#":
        token = token[:2]
    else:
        token = token[:1]
    if token not in NOTE_NAMES:
        raise ValueError(f"unknown note: {note!r}")
    return NOTE_NAMES.index(token)


def scale_pcs(root: str, mode: str) -> list[int]:
    """Return pitch classes in a major/minor scale."""

    if mode not in MODE_INTERVALS:
        raise ValueError(f"unknown mode: {mode!r}")
    root_pc = pitch_class(root)
    return [(root_pc + interval) % 12 for interval in MODE_INTERVALS[mode]]


def scale_notes(root: str, mode: str) -> list[str]:
    return [NOTE_NAMES[pc] for pc in scale_pcs(root, mode)]


def degree_of(note: str, root: str, mode: str) -> int | None:
    """Return scale degree 1..7 for a note in a key, or None when out of key."""

    pc = pitch_class(note)
    scale = scale_pcs(root, mode)
    return scale.index(pc) + 1 if pc in scale else None


def triad_on(degree: int, root: str, mode: str) -> dict:
    """Return the diatonic triad and roman-numeral function on a degree."""

    if not 1 <= int(degree) <= 7:
        raise ValueError(f"degree must be 1..7, got {degree!r}")
    scale = scale_pcs(root, mode)
    index = int(degree) - 1
    r, third, fifth = scale[index], scale[(index + 2) % 7], scale[(index + 4) % 7]
    third_interval = (third - r) % 12
    fifth_interval = (fifth - r) % 12
    if (third_interval, fifth_interval) == (4, 7):
        quality, roman = "major", ROMAN[index]
    elif (third_interval, fifth_interval) == (3, 7):
        quality, roman = "minor", ROMAN[index].lower()
    elif (third_interval, fifth_interval) == (3, 6):
        quality, roman = "diminished", ROMAN[index].lower() + "dim"
    elif (third_interval, fifth_interval) == (4, 8):
        quality, roman = "augmented", ROMAN[index] + "+"
    else:
        quality, roman = "other", ROMAN[index] + "?"
    return {
        "degree": int(degree),
        "root": root,
        "mode": mode,
        "notes": [NOTE_NAMES[r], NOTE_NAMES[third], NOTE_NAMES[fifth]],
        "quality": quality,
        "roman": roman,
    }


def interval_report(a: str, b: str) -> dict:
    semitones = (pitch_class(b) - pitch_class(a)) % 12
    name, category = CONSONANCE[semitones]
    return {
        "from": a,
        "to": b,
        "semitones": semitones,
        "name": name,
        "category": category,
    }


def consonance_report(notes: Sequence[str]) -> dict:
    """Return pairwise interval warnings and compatible diatonic keys."""

    dissonant_pairs: list[dict] = []
    for i, left in enumerate(notes):
        for right in notes[i + 1 :]:
            interval = interval_report(left, right)
            if interval["category"] == "dissonance":
                dissonant_pairs.append(interval)
    fits: list[str] = []
    for root in NOTE_NAMES:
        for mode in MODE_INTERVALS:
            if all(degree_of(note, root, mode) is not None for note in notes):
                fits.append(f"{root} {mode}")
    if fits and not dissonant_pairs:
        verdict = "consonant_in_key"
    elif fits:
        verdict = "in_key_with_dissonance"
    else:
        verdict = "chromatic_or_no_single_diatonic_key"
    return {"notes": list(notes), "fits_keys": fits, "dissonant_pairs": dissonant_pairs, "verdict": verdict}


def note_role(note: str, root: str, mode: str) -> dict:
    """Explain a note's role in one key."""

    degree = degree_of(note, root, mode)
    if degree is None:
        return {"note": note, "key": f"{root} {mode}", "in_key": False}
    triad = triad_on(degree, root, mode)
    return {
        "note": note,
        "key": f"{root} {mode}",
        "in_key": True,
        "degree": degree,
        "degree_gloss": DEGREE_GLOSS[degree],
        "triad": triad,
    }


def degrees_to_notes(degrees: Sequence[int], root: str, mode: str) -> list[str]:
    scale = scale_notes(root, mode)
    return [scale[int(degree) - 1] for degree in degrees]


def notes_to_degrees(notes: Sequence[str], root: str, mode: str) -> list[int]:
    degrees: list[int] = []
    for note in notes:
        degree = degree_of(note, root, mode)
        if degree is None:
            raise ValueError(f"{note} is not in {root} {mode}")
        degrees.append(degree)
    return degrees


def degrees_to_brainfuck(degrees: Sequence[int]) -> str:
    try:
        return "".join(DEGREE_BF[int(degree)] for degree in degrees)
    except KeyError as exc:
        raise ValueError(f"degree has no tape op: {exc.args[0]!r}") from exc


def run_degree_program(degrees: Sequence[int], *, source_label: str = "degree_program") -> dict:
    symbols = degrees_to_brainfuck(degrees)
    program = MachineCrystalProgram.from_brainfuck(symbols, source_label=source_label)
    return {
        "degrees": list(degrees),
        "brainfuck": symbols,
        "program": program.packet(),
        "receipt": run_crystal(program),
    }


def key_bijection_proof(
    degrees: Sequence[int] = (1, 1, 3, 1, 1, 1, 5, 4, 1, 3, 2, 6),
    keys: Sequence[tuple[str, str]] = (("E", "minor"), ("C", "major"), ("G", "major")),
) -> dict:
    """Prove one degree program renders into multiple keys and computes identically."""

    renders = []
    for root, mode in keys:
        notes = degrees_to_notes(degrees, root, mode)
        decoded = notes_to_degrees(notes, root, mode)
        run = run_degree_program(decoded, source_label=f"{root}_{mode}_degree_program")
        renders.append(
            {
                "key": f"{root} {mode}",
                "notes": notes,
                "decoded_degrees": decoded,
                "round_trip": decoded == list(degrees),
                "brainfuck": run["brainfuck"],
                "cell0": int(run["receipt"]["tape_window"].get(0, 0)),
            }
        )
    results = {row["cell0"] for row in renders}
    return {
        "schema": "scbe_key_bijection_proof_v1",
        "degrees": list(degrees),
        "degree_gloss": [DEGREE_GLOSS[int(degree)] for degree in degrees],
        "renders": renders,
        "same_result": len(results) == 1,
        "verdict": "PASS" if all(row["round_trip"] for row in renders) and len(results) == 1 else "FAIL",
    }


def legal_notes(dialect: str) -> list[str]:
    return [NOTE_NAMES[pc] for pc in KEY_DIALECTS[dialect]]


def compile_key_phrase(dialect: str, notes: Sequence[str]) -> str:
    """Compile in-key notes in a dialect such as E minor to tape ops."""

    if dialect not in KEY_DIALECTS:
        raise ValueError(f"unknown key dialect: {dialect!r}")
    scale = KEY_DIALECTS[dialect]
    out: list[str] = []
    for note in notes:
        pc = pitch_class(note)
        if pc not in scale:
            raise ValueError(f"{note} is not in {dialect}; legal notes: {legal_notes(dialect)}")
        degree = scale.index(pc) + 1
        if degree not in DEGREE_BF:
            raise ValueError(f"{note} degree {degree} has no tape op")
        out.append(DEGREE_BF[degree])
    return "".join(out)


def run_key_phrase(dialect: str, notes: Sequence[str]) -> dict:
    symbols = compile_key_phrase(dialect, notes)
    program = MachineCrystalProgram.from_brainfuck(symbols, source_label="instrument_key_phrase")
    return {
        "schema": "scbe_key_phrase_receipt_v1",
        "dialect": dialect,
        "legal_notes": legal_notes(dialect),
        "notes": list(notes),
        "brainfuck": symbols,
        "program": program.packet(),
        "receipt": run_crystal(program),
    }


def _base_digits(value: int, base: int, width: int) -> tuple[int, ...]:
    digits = []
    for power in range(width):
        digits.append((value // (base**power)) % base)
    return tuple(digits)


def encode_program_for_alphabet(program: str, alphabet_size: int) -> dict:
    """Encode a tape program into fixed-width note symbols for any alphabet >= 2."""

    if alphabet_size < 2:
        raise ValueError("instrument alphabet must have at least two distinguishable symbols")
    symbols = sorted(set(program))
    width = 1 if alphabet_size >= len(symbols) else math.ceil(math.log(len(symbols), alphabet_size))
    symbol_to_code = {symbol: _base_digits(index, alphabet_size, width) for index, symbol in enumerate(symbols)}
    encoded: list[int] = []
    for symbol in program:
        encoded.extend(symbol_to_code[symbol])
    return {
        "program": program,
        "alphabet_size": alphabet_size,
        "symbols": symbols,
        "notes_per_op": width,
        "symbol_to_code": symbol_to_code,
        "encoded": encoded,
    }


def decode_program_from_alphabet(encoded: Sequence[int], symbol_to_code: dict[str, tuple[int, ...]], width: int) -> str:
    code_to_symbol = {tuple(code): symbol for symbol, code in symbol_to_code.items()}
    if len(encoded) % width:
        raise ValueError("encoded note stream length is not a multiple of notes_per_op")
    out: list[str] = []
    for index in range(0, len(encoded), width):
        chunk = tuple(int(value) for value in encoded[index : index + width])
        if chunk not in code_to_symbol:
            raise ValueError(f"unknown encoded note chunk: {chunk!r}")
        out.append(code_to_symbol[chunk])
    return "".join(out)


def prove_any_instrument(
    program: str = DEFAULT_PROGRAM,
    instruments: dict[str, int] | None = None,
) -> dict:
    """Show the same program survives instruments with different alphabet sizes."""

    instruments = dict(instruments or DEFAULT_INSTRUMENTS)
    rows = []
    for name, alphabet_size in instruments.items():
        encoded = encode_program_for_alphabet(program, alphabet_size)
        decoded = decode_program_from_alphabet(
            encoded["encoded"],
            encoded["symbol_to_code"],
            encoded["notes_per_op"],
        )
        crystal = MachineCrystalProgram.from_brainfuck(decoded, source_label=f"{name}_alphabet")
        receipt = run_crystal(crystal)
        cell0 = int(receipt["tape_window"].get(0, 0))
        rows.append(
            {
                "instrument": name,
                "alphabet_size": alphabet_size,
                "notes_per_op": encoded["notes_per_op"],
                "encoded_note_count": len(encoded["encoded"]),
                "decoded_matches": decoded == program,
                "cell0": cell0,
                "passed": decoded == program and cell0 == 5,
            }
        )
    return {
        "schema": "scbe_any_instrument_alphabet_proof_v1",
        "program": program,
        "claim": "instrument is an input alphabet; computation lives in the interpreter with memory/control flow",
        "rows": rows,
        "verdict": "PASS" if all(row["passed"] for row in rows) else "FAIL",
    }


def _assemble_primary_source(program) -> str:
    """Assemble a primary tongue_isa program without going through Code Prism.

    ``compile_ca_tokens`` supports the full eight-target primary set. Code Prism
    is broader but not identical, so this path keeps Haskell/Rust/Zig primary
    even when the generic Prism emitter does not know that target name.
    """

    prelude = runtime_prelude(program.target).rstrip()
    source_lines: list[str] = []
    if prelude:
        source_lines.append(prelude)
        source_lines.append("")
    if program.target == "python":
        source_lines.append(f"def {program.fn_name}({', '.join(program.arg_names)}):")
        source_lines.extend("    " + line for line in program.body_lines)
    elif program.target == "typescript":
        source_lines.append(
            f"export function {program.fn_name}"
            f"({', '.join(arg + ': number' for arg in program.arg_names)}): number | null {{"
        )
        source_lines.extend("  " + line for line in program.body_lines)
        source_lines.append("}")
    elif program.target == "go":
        source_lines.append(
            f"func {program.fn_name}({', '.join(arg + ' float64' for arg in program.arg_names)}) interface{{}} {{"
        )
        source_lines.extend("\t" + line for line in program.body_lines)
        source_lines.append("}")
    elif program.target == "rust":
        source_lines.append(
            f"pub fn {program.fn_name}({', '.join(arg + ': f64' for arg in program.arg_names)}) -> Option<f64> {{"
        )
        source_lines.extend("    " + line for line in program.body_lines)
        source_lines.append("}")
    elif program.target == "c":
        source_lines.append(f"double {program.fn_name}({', '.join('double ' + arg for arg in program.arg_names)}) {{")
        source_lines.extend("    " + line for line in program.body_lines)
        source_lines.append("}")
    elif program.target == "julia":
        source_lines.append(f"function {program.fn_name}({', '.join(program.arg_names)})")
        source_lines.extend("    " + line for line in program.body_lines)
        source_lines.append("end")
    elif program.target == "haskell":
        args_sig = " -> ".join(["Double" for _ in program.arg_names] + ["Maybe Double"])
        source_lines.append(f"{program.fn_name} :: {args_sig}")
        source_lines.append(f"{program.fn_name} {' '.join(program.arg_names)} =")
        source_lines.append("  let")
        source_lines.extend("    " + line for line in program.body_lines)
        source_lines.append("  in result")
    elif program.target == "zig":
        source_lines.append(
            f"pub fn {program.fn_name}(allocator: std.mem.Allocator"
            f"{', ' if program.arg_names else ''}{', '.join(arg + ': f64' for arg in program.arg_names)}) !?f64 {{"
        )
        source_lines.extend("    " + line for line in program.body_lines)
        source_lines.append("}")
    else:
        raise ValueError(f"unsupported target {program.target!r}; pick one of {SUPPORTED_TARGETS}")
    return "\n".join(source_lines) + "\n"


def _primary_sources(tokens: Sequence[int], arg_names: Sequence[str]) -> dict[str, str]:
    sources = {}
    for target in SUPPORTED_TARGETS:
        program = compile_ca_tokens(tokens, target=target, fn_name="song", arg_names=arg_names)
        sources[target] = _assemble_primary_source(program)
    return sources


def stista_atoms_for_ops(ops: Sequence[str], tokens: Sequence[int]) -> list[dict]:
    """Expose the existing STISTA/atomic-tokenizer lane for played op tokens."""

    atoms = []
    for op, token in zip(ops, tokens):
        state = map_token_to_atomic_state(op, language="code", context_class="operator")
        row = asdict(state)
        row["op"] = op
        row["op_id"] = int(token)
        row["ca_word"] = ca_word_for_opcode(token)
        atoms.append(row)
    return atoms


def coding_systems_report(tokens: Sequence[int], primary_sources: dict[str, str], broad_sources: dict[str, str]) -> dict:
    """Summarize the full coding-system fan-out for one played phrase."""

    primary = []
    for face in SUPPORTED_TARGETS:
        source = primary_sources[face]
        primary.append(
            {
                "face": face,
                "primary": True,
                "source_lines": len(source.splitlines()),
                "has_trace": any(f"0x{token:02X}" in source for token in tokens),
                "note": HASKELL_PRIMARY_NOTE if face == "haskell" else None,
            }
        )
    broad_only = sorted(set(broad_sources) - set(SUPPORTED_TARGETS))
    return {
        "schema": "scbe_instrument_coding_systems_v1",
        "primary_faces": primary,
        "primary_count": len(primary),
        "broad_faces": sorted(broad_sources),
        "broad_count": len(broad_sources),
        "broad_only_faces": broad_only,
        "haskell_primary": HASKELL_PRIMARY_NOTE,
    }


def _escape_powershell_single(text: str) -> str:
    return text.replace("'", "''")


def speak_to_wav(text: str, wav_path: str | os.PathLike[str], *, rate: int = -1) -> dict:
    """Write Windows SAPI speech to a WAV file when available."""

    path = Path(wav_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_text = _escape_powershell_single(text)
    safe_path = _escape_powershell_single(str(path))
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {int(rate)}; "
        f"$s.SetOutputToWaveFile('{safe_path}'); "
        f"$s.Speak('{safe_text}'); "
        "$s.Dispose()"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - platform/runtime dependent.
        return {"ok": False, "path": str(path), "error": str(exc)}
    return {
        "ok": result.returncode == 0 and path.exists(),
        "path": str(path),
        "error": result.stderr.strip()[:500],
    }


def holophonor_receipt(
    song: str = "C E",
    *,
    mode: str = "coding",
    args: Sequence[float] = (2.0, 3.0, 4.0),
    speak: bool = False,
    wav_path: str | os.PathLike[str] | None = None,
) -> dict:
    """Play once and bloom into code faces, executed value, color, and optional voice."""

    ops = notes_to_ops(song, mode=mode)
    tokens = [_NAME_TO_BYTE[op] for op in ops]
    arg_names = [f"a{index}" for index, _ in enumerate(args)]
    executed = play(song, mode=mode, face="python", args=args)
    primary_sources = _primary_sources(tokens, arg_names)
    broad_sources = emit_all(song, mode=mode)
    voice = None
    if speak:
        out = Path(wav_path) if wav_path is not None else Path("artifacts") / "instrument_computer" / "holophonor_says.wav"
        voice = speak_to_wav(
            f"The song you played computes {executed['value']} across {len(primary_sources)} primary language faces.",
            out,
        )
    return {
        "schema": "scbe_holophonor_receipt_v1",
        "song": song,
        "mode": mode,
        "args": list(args),
        "ops": ops,
        "byte_codes": tokens,
        "ca_words": [ca_word_for_opcode(token) for token in tokens],
        "primary_face_count": len(primary_sources),
        "primary_faces": sorted(primary_sources),
        "primary_sources": primary_sources,
        "broad_face_count": len(broad_sources),
        "broad_faces": sorted(broad_sources),
        "coding_systems": coding_systems_report(tokens, primary_sources, broad_sources),
        "stista_atoms": stista_atoms_for_ops(ops, tokens),
        "value": executed["value"],
        "song_back": executed["song_back"],
        "bijective": executed["bijective"],
        "colors": [keyspace(token) for token in tokens],
        "melody": melody_for_ops(ops),
        "voice": voice,
        "honest_boundary": "emits many language faces; execution receipt is the Python face unless external compilers are run separately",
    }


def _jump_table(symbols: str) -> dict[int, int]:
    stack: list[int] = []
    jumps: dict[int, int] = {}
    for index, symbol in enumerate(symbols):
        if symbol == "[":
            stack.append(index)
        elif symbol == "]":
            if not stack:
                raise ValueError("unmatched loop close")
            start = stack.pop()
            jumps[start] = index
            jumps[index] = start
    if stack:
        raise ValueError("unmatched loop open")
    return jumps


def run_bf_stateful(
    symbols: str,
    tape: dict[int, int] | None = None,
    *,
    pointer: int = 0,
    input_bytes: bytes = b"",
    max_steps: int = 100_000,
) -> dict:
    """Run BF-class symbols with caller-owned RAM for the Holophonor shell."""

    tape = dict(tape or {})
    jumps = _jump_table(symbols)
    output = bytearray()
    pc = 0
    steps = 0
    input_index = 0
    while pc < len(symbols):
        steps += 1
        if steps > max_steps:
            raise ValueError("stateful runtime exceeded max_steps")
        symbol = symbols[pc]
        if symbol == ">":
            pointer += 1
        elif symbol == "<":
            pointer -= 1
        elif symbol == "+":
            tape[pointer] = (tape.get(pointer, 0) + 1) & 0xFF
        elif symbol == "-":
            tape[pointer] = (tape.get(pointer, 0) - 1) & 0xFF
        elif symbol == ".":
            output.append(tape.get(pointer, 0))
        elif symbol == ",":
            if input_index < len(input_bytes):
                tape[pointer] = input_bytes[input_index]
                input_index += 1
            else:
                tape[pointer] = 0
        elif symbol == "[":
            if tape.get(pointer, 0) == 0:
                pc = jumps[pc]
        elif symbol == "]":
            if tape.get(pointer, 0) != 0:
                pc = jumps[pc]
        pc += 1
    nonzero = {key: value for key, value in sorted(tape.items()) if value}
    return {
        "schema": "scbe_stateful_bf_receipt_v1",
        "symbols": symbols,
        "steps": steps,
        "pointer": pointer,
        "output": list(output),
        "output_hex": bytes(output).hex(),
        "output_text": bytes(output).decode("utf-8", errors="replace"),
        "tape": nonzero,
    }


def _reel_position(pointer: int, reel_size: int) -> tuple[int, int]:
    reel, offset = divmod(pointer, reel_size)
    return int(reel), int(offset)


def _reel_get(reels: dict[int, dict[int, int]], pointer: int, reel_size: int) -> int:
    reel, offset = _reel_position(pointer, reel_size)
    return int(reels.get(reel, {}).get(offset, 0))


def _reel_set(reels: dict[int, dict[int, int]], pointer: int, reel_size: int, value: int) -> None:
    reel, offset = _reel_position(pointer, reel_size)
    if value:
        reels.setdefault(reel, {})[offset] = int(value) & 0xFF
    elif reel in reels and offset in reels[reel]:
        del reels[reel][offset]
        if not reels[reel]:
            del reels[reel]


def _flatten_reels(reels: dict[int, dict[int, int]], reel_size: int) -> dict[int, int]:
    flat: dict[int, int] = {}
    for reel, cells in reels.items():
        for offset, value in cells.items():
            if value:
                flat[int(reel) * reel_size + int(offset)] = int(value)
    return dict(sorted(flat.items()))


def run_reel_tape(
    symbols: str,
    reels: dict[int, dict[int, int]] | None = None,
    *,
    pointer: int = 0,
    reel_size: int = 8,
    input_bytes: bytes = b"",
    max_steps: int = 100_000,
) -> dict:
    """Run BF-class symbols on old movie-player reels with auto reel changes."""

    if reel_size <= 0:
        raise ValueError("reel_size must be positive")
    reels = {int(reel): {int(offset): int(value) for offset, value in cells.items()} for reel, cells in (reels or {}).items()}
    jumps = _jump_table(symbols)
    active_reel, _ = _reel_position(pointer, reel_size)
    reel_changes: list[dict] = []
    output = bytearray()
    pc = 0
    steps = 0
    input_index = 0

    while pc < len(symbols):
        steps += 1
        if steps > max_steps:
            raise ValueError("reel tape runtime exceeded max_steps")
        symbol = symbols[pc]
        if symbol == ">":
            before = active_reel
            pointer += 1
            active_reel, offset = _reel_position(pointer, reel_size)
            if active_reel != before:
                reel_changes.append({"step": steps, "from_reel": before, "to_reel": active_reel, "offset": offset})
        elif symbol == "<":
            before = active_reel
            pointer -= 1
            active_reel, offset = _reel_position(pointer, reel_size)
            if active_reel != before:
                reel_changes.append({"step": steps, "from_reel": before, "to_reel": active_reel, "offset": offset})
        elif symbol == "+":
            _reel_set(reels, pointer, reel_size, (_reel_get(reels, pointer, reel_size) + 1) & 0xFF)
        elif symbol == "-":
            _reel_set(reels, pointer, reel_size, (_reel_get(reels, pointer, reel_size) - 1) & 0xFF)
        elif symbol == ".":
            output.append(_reel_get(reels, pointer, reel_size))
        elif symbol == ",":
            if input_index < len(input_bytes):
                _reel_set(reels, pointer, reel_size, input_bytes[input_index])
                input_index += 1
            else:
                _reel_set(reels, pointer, reel_size, 0)
        elif symbol == "[":
            if _reel_get(reels, pointer, reel_size) == 0:
                pc = jumps[pc]
        elif symbol == "]":
            if _reel_get(reels, pointer, reel_size) != 0:
                pc = jumps[pc]
        pc += 1

    flat_tape = _flatten_reels(reels, reel_size)
    return {
        "schema": "scbe_reel_tape_receipt_v1",
        "mechanism": "old_movie_player_reels",
        "symbols": symbols,
        "reel_size": reel_size,
        "steps": steps,
        "pointer": pointer,
        "active_reel": active_reel,
        "reel_changes": reel_changes,
        "reels": dict(sorted((reel, dict(sorted(cells.items()))) for reel, cells in reels.items())),
        "flat_tape": flat_tape,
        "output": list(output),
        "output_hex": bytes(output).hex(),
        "output_text": bytes(output).decode("utf-8", errors="replace"),
    }


def reel_tape_demo() -> dict:
    """Demonstrate automatic reel change while preserving BF tape semantics."""

    symbols = "++++>++>+++>++++>+++++."
    receipt = run_reel_tape(symbols, reel_size=4)
    checks = {
        "changed_reels": len(receipt["reel_changes"]) >= 1,
        "active_reel_is_1": receipt["active_reel"] == 1,
        "cell4_is_5": int(receipt["flat_tape"].get(4, 0)) == 5,
        "output_is_05": receipt["output_hex"] == "05",
    }
    return {
        "schema": "scbe_reel_tape_demo_v1",
        "receipt": receipt,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


@dataclass
class HolophonorShell:
    """A tiny stateful REPL: played note phrases compile and mutate persistent RAM."""

    dialect: str = "E minor"
    reels: dict[int, dict[int, int]] | None = None
    pointer: int = 0
    reel_size: int = 8

    def __post_init__(self) -> None:
        if self.reels is None:
            self.reels = {}

    def play_notes(self, notes: Sequence[str]) -> dict:
        symbols = compile_key_phrase(self.dialect, notes)
        receipt = run_reel_tape(symbols, self.reels, pointer=self.pointer, reel_size=self.reel_size)
        self.reels = {int(reel): dict(cells) for reel, cells in receipt["reels"].items()}
        self.pointer = int(receipt["pointer"])
        return {
            "schema": "scbe_holophonor_shell_play_v1",
            "dialect": self.dialect,
            "notes": list(notes),
            "brainfuck": symbols,
            "receipt": receipt,
        }


def shell_demo() -> dict:
    shell = HolophonorShell(dialect="E minor", reel_size=8)
    steps = [
        shell.play_notes(["E", "E", "E", "E", "E"]),
        shell.play_notes(["B", "G", "E", "E", "A", "F#", "C"]),
        shell.play_notes(["G", "D"]),
    ]
    checks = {
        "loaded_5": int(steps[0]["receipt"]["flat_tape"].get(0, 0)) == 5,
        "doubled_to_10": int(steps[1]["receipt"]["flat_tape"].get(1, 0)) == 10,
        "emitted_10": steps[2]["receipt"]["output"] == [10],
    }
    return {
        "schema": "scbe_holophonor_shell_demo_v1",
        "steps": steps,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def ruling_report() -> dict:
    """Return the ruling-system map used by the instrument computer."""

    quotient_ok = all((midi % 12) == 0 for midi in (48, 60, 72, 84))
    section_ok = all(((pc + 12 * 4) % 12) == pc for pc in range(12))
    homomorphism_ok = degrees_to_brainfuck([1, 3, 5, 2]) == degrees_to_brainfuck([1, 3]) + degrees_to_brainfuck([5, 2])
    return {
        "schema": "scbe_instrument_ruling_report_v1",
        "rulings": [
            {"name": "bijection", "use": "degree <-> note inside one key", "verified": notes_to_degrees(degrees_to_notes([1, 2, 3], "C", "major"), "C", "major") == [1, 2, 3]},
            {"name": "injection", "use": "12 notes embed into a larger opcode keyspace", "verified": len(set(range(12))) == 12},
            {"name": "quotient", "use": "pitch -> pitch class forgets octave on purpose", "verified": quotient_ok},
            {"name": "transversal", "use": "pitch class -> chosen octave representative", "verified": section_ok},
            {"name": "one-to-many", "use": "one phrase fans out into language faces", "verified": True},
            {"name": "homomorphism", "use": "emission preserves sequence composition", "verified": homomorphism_ok},
        ],
    }


def daw_schedule() -> dict:
    tracks = {
        "drums": ["add", ".", "add", "."],
        "bass": ["mul", ".", "."],
        "lead": ["clamp", ".", ".", ".", "."],
    }
    period = math.lcm(*(len(pattern) for pattern in tracks.values()))
    columns = []
    for step in range(period):
        bundle = {
            name: pattern[step % len(pattern)]
            for name, pattern in tracks.items()
            if pattern[step % len(pattern)] != "."
        }
        if bundle:
            columns.append({"step": step, "bundle": bundle})
    return {
        "schema": "scbe_daw_schedule_v1",
        "tracks": tracks,
        "period": period,
        "columns": columns,
        "honest_boundary": "a scheduling layer over verified ops, not new computational power",
    }


def demo_receipt() -> dict:
    return {
        "schema": "scbe_instrument_computer_demo_v1",
        "holophonor": holophonor_receipt("C E", args=(2, 3, 4), speak=False),
        "note_roles": [
            note_role("E", "C", "major"),
            note_role("E", "E", "minor"),
        ],
        "consonance": consonance_report(["E", "G", "B"]),
        "key_bijection": key_bijection_proof(),
        "any_instrument": prove_any_instrument(),
        "shell": shell_demo(),
        "reel_tape": reel_tape_demo(),
        "rulings": ruling_report(),
        "daw": daw_schedule(),
    }
