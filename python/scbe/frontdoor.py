"""
Front door — type tokens, hit Enter, see the perfect code.
==========================================================

The keyboard layer. You type a token stream (symbols, op names, hex, or Sacred
Tongue tokens); `tokens_to_program` turns it into the one CA-opcode object; the
coding harness emits it to every language face; and it renders in clean panels
with live verification badges (faces agree / seekable / DNA-sealed).

    python -m python.scbe.frontdoor "+ sqrt * inc /"        # one shot
    python -m python.scbe.frontdoor --repl                  # hit-Enter loop
    python -m python.scbe.frontdoor "+ * sqrt" --all        # every face

Easy on purpose: `+ - * /` map to add/sub/mul/div, `√ ^ %` to sqrt/pow/mod, and
plain words (`sqrt`, `inc`, `max`) and hex (`0x06`) all work. Unknown tokens get a
"did you mean" hint instead of a stack trace.
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import sys
from typing import List, Sequence, Tuple

from . import bijective_dna as DNA
from . import board as _BOARD
from . import polyglot as P
from . import torus as _TOR

# --- the friendly keyboard: any of these -> a core opcode name ------------------
_SYMBOLS = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "%": "mod",
    "^": "pow",
    "**": "pow",
    "√": "sqrt",
    "<": "lt",
    ">": "gt",
    "<=": "lte",
    ">=": "gte",
    "==": "eq",
    "!=": "neq",
    "++": "inc",
    "--": "dec",
    "|": "abs",
    "~": "neg",
}
_ALIASES = {
    "power": "pow",
    "modulo": "mod",
    "minimum": "min",
    "maximum": "max",
    "negate": "neg",
    "absolute": "abs",
    "increment": "inc",
    "decrement": "dec",
    "root": "sqrt",
}

# --- the Sacred Tongue keyboard: type prefix'suffix tokens straight in ----------
try:  # canonical 6-tongue byte<->token table
    from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER as _STT

    _TONGUE_ORDER = ("ko", "av", "ru", "ca", "um", "dr")
    _HAVE_TONGUES = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_TONGUES = False
    _TONGUE_ORDER = ()


def _decode_tongue_token(tok: str, tongue: str | None = None):
    """A Sacred Tongue token (prefix'suffix) -> (opcode byte, tongue code), or (None, None)."""
    if not _HAVE_TONGUES:
        return None, None
    for c in ((tongue,) if tongue else _TONGUE_ORDER):
        b = _STT.token_to_byte.get(c, {}).get(tok)
        if b is not None:
            return b, c
    return None, None


def tongue_spell(prog: Sequence[int], tongue: str = "ko") -> str:
    """The opcode strand spelled in Sacred Tongue tokens — the keyboard made visible."""
    if not _HAVE_TONGUES or tongue not in _TONGUE_ORDER:
        return ""
    table = _STT.byte_to_token[tongue]
    return " ".join(table[b] for b in prog)


def tokens_to_program(text: str, tongue: str | None = None) -> Tuple[List[str], List[int]]:
    """THE FRONT DOOR: a typed token stream -> (op names, opcode bytes).

    Accepts core op names, friendly symbols/aliases, 0xNN hex bytes, and Sacred
    Tongue tokens (prefix'suffix). With `tongue`, tongue tokens are read in that
    tongue; otherwise all six are searched. Raises ValueError with a hint on misses."""
    names: List[str] = []
    for raw in text.replace(",", " ").split():
        tok = raw.strip()
        if not tok:
            continue
        if tok in _SYMBOLS:
            name = _SYMBOLS[tok]
        elif tok.lower() in _ALIASES:
            name = _ALIASES[tok.lower()]
        elif re.fullmatch(r"0x[0-9a-fA-F]{1,2}", tok):
            b = int(tok, 16)
            if b not in P.BYTE_TO_NAME or P.BYTE_TO_NAME[b] not in P.SCALAR_OPS:
                raise ValueError("0x%02x is not a v1 core opcode" % b)
            name = P.BYTE_TO_NAME[b]
        elif tok.lower() in P.SCALAR_OPS:
            name = tok.lower()
        elif "'" in tok and _HAVE_TONGUES:  # a Sacred Tongue keystroke
            b, _c = _decode_tongue_token(tok, tongue)
            if b is None:
                raise ValueError("%r is not a Sacred Tongue token%s" % (tok, (" in %s" % tongue) if tongue else ""))
            nm = P.BYTE_TO_NAME.get(b)
            if nm not in P.SCALAR_OPS:
                raise ValueError("%s = byte 0x%02x%s, not a core opcode" % (tok, b, " (%s)" % nm if nm else ""))
            name = nm
        else:
            hint = difflib.get_close_matches(tok.lower(), sorted(P.SCALAR_OPS), n=3)
            tip = ("  did you mean: %s ?" % ", ".join(hint)) if hint else ""
            raise ValueError("don't know token %r.%s" % (tok, tip))
        names.append(name)
    return names, P.program_bytes(*names)


# --- terminal styling (dependency-free; degrades when not a tty) ----------------
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _style_enabled(flag: bool) -> bool:
    return flag and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _unicode_enabled() -> bool:
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in enc


class _S:
    def __init__(self, on: bool):
        self.on = on
        self.uni = _unicode_enabled()

    def _w(self, s, code):
        return ("\x1b[%sm%s\x1b[0m" % (code, s)) if self.on else s

    def bold(self, s):
        return self._w(s, "1")

    def dim(self, s):
        return self._w(s, "2")

    def cyan(self, s):
        return self._w(s, "36")

    def green(self, s):
        return self._w(s, "32")

    def red(self, s):
        return self._w(s, "31")

    def yellow(self, s):
        return self._w(s, "33")

    def mag(self, s):
        return self._w(s, "35")

    def rgb(self, s, r, g, b):
        """24-bit truecolor (trichromatic stones/notes); plain when styling is off."""
        return ("\x1b[38;2;%d;%d;%dm%s\x1b[0m" % (r, g, b, s)) if self.on else s


def _tongue_freq(tongue: str) -> float:
    if _HAVE_TONGUES and tongue in _STT.tongues:
        return float(_STT.tongues[tongue].harmonic_frequency)
    return 440.0  # A4 default


def _vis(s: str) -> int:
    return len(_ANSI.sub("", s))


def _clip(s: str, w: int, st: _S) -> str:
    if _vis(s) <= w:
        return s
    ellipsis = "…" if st.uni else "..."
    return st.dim(_ANSI.sub("", s)[: max(0, w - len(ellipsis))] + ellipsis)


def _panel(title: str, lines: Sequence[str], st: _S, inner: int, accent=None) -> str:
    """Render a titled box at a FIXED inner width so stacked panels line up."""
    accent = accent or st.cyan
    if _vis(title) > inner - 4:
        ellipsis = "…" if st.uni else "..."
        title = _ANSI.sub("", title)[: inner - 4 - len(ellipsis)] + ellipsis
    if st.uni:
        tl, tr, bl, br, h, v = "╭", "╮", "╰", "╯", "─", "│"
    else:
        tl, tr, bl, br, h, v = "+", "+", "+", "+", "-", "|"
    top = accent(tl + h + " ") + st.bold(title) + " " + accent(h * (inner - _vis(title) - 3) + tr)
    out = [top]
    for ln in lines:
        ln = _clip(ln, inner - 2, st)
        out.append(accent(v + " ") + ln + " " * (inner - _vis(ln) - 2) + accent(" " + v))
    out.append(accent(bl + h * inner + br))
    return "\n".join(out)


def _badge(ok: bool, label: str, st: _S) -> str:
    if st.uni:
        mark = st.green("✓ ") if ok else st.red("✗ ")
    else:
        mark = st.green("OK ") if ok else st.red("ERR ")
    return mark + (label if ok else st.red(label))


def _fmt(v) -> str:
    if isinstance(v, float):
        return "%.1f" % v if v == int(v) else "%.6g" % v
    return str(v)


def _run(prog: Sequence[int], st: _S) -> str:
    """Run the Python face on the default args and show the result. If the raw run
    hits an undefined zone (÷0, √-), fall back to the roundabout and say so."""

    def call(safe):
        ns: dict = {}
        exec(compile(P.emit(prog, "python", safe=safe), "<face>", "exec"), ns)  # noqa: S102
        return ns["tongue_fn"](2.0, 3.0, 4.0)

    try:
        ok = st.green("✓ ") if st.uni else st.green("OK ")
        arrow = "→" if st.uni else "->"
        return ok + "tongue_fn(2,3,4) " + arrow + " " + st.bold(_fmt(call(False)))
    except (ZeroDivisionError, ValueError, OverflowError) as e:
        try:  # undefined zone -> roundabout
            warn = st.yellow("⚠ ") if st.uni else st.yellow("WARN ")
            arrow = "→" if st.uni else "->"
            return warn + "undefined (%s) %s roundabout %s" % (type(e).__name__, arrow, st.bold(_fmt(call(True))))
        except Exception as e2:  # pragma: no cover - defensive
            err = st.red("✗ ") if st.uni else st.red("ERR ")
            return err + "error: %s" % type(e2).__name__
    except IndexError:  # not enough values on the stack
        dot = "·" if st.uni else "*"
        return st.dim(dot + " incomplete strand (needs more operands)")
    except Exception as e:  # pragma: no cover - defensive
        dot = "·" if st.uni else "*"
        return st.dim(dot + " did not run (%s)" % type(e).__name__)


def board_lines(prog: Sequence[int], tongue: str, st: _S) -> List[str]:
    """The strand as trichromatic stones on the token board: hi nibble = row, lo
    nibble = col, MID nibble = the seam/depth strip, RGB = the cube axes, and a
    musical melody rooted at the tongue's note."""
    root = _tongue_freq(tongue)
    pts: dict = {}
    seam: dict = {}
    for i, b in enumerate(prog, 1):
        pts[_BOARD.to_point(b)] = (i, b)  # last move wins on a replayed point
        seam[_BOARD.mid_nibble(b)] = (i, b)
    dot = "·" if st.uni else "."

    def stone(key, tbl):
        if key in tbl:
            i, b = tbl[key]
            return st.rgb("%3d" % i, *_BOARD.rgb(b))
        return "  " + st.dim(dot)

    lines = [st.dim("    " + "".join("%3s" % ("%x" % c) for c in range(_BOARD.EDGE)))]
    for r in range(len(_BOARD.BANDS)):  # rows 0-3: the four opcode bands
        row = "".join(stone((r, c), pts) for c in range(_BOARD.EDGE))
        lines.append(st.dim(" %x  " % r) + row + st.dim("  " + _BOARD.BANDS[r]))
    seam_row = "".join(stone(c, seam) for c in range(_BOARD.EDGE))
    lines += ["", st.dim(" mid") + " " + seam_row + st.dim("  seam nibble (depth axis)")]

    notes = [st.rgb(_BOARD.opcode_note(b, root)[1], *_BOARD.rgb(b)) for b in prog]
    melody = " ".join(notes) if notes else st.dim("(silent)")
    lines += ["", st.dim(" notes ") + melody + st.dim("   key %s @ %gHz (%s)" % (_BOARD.note_name(root), root, tongue))]
    ok = _BOARD.is_reversible(prog)
    mark = (st.green("✓ ") if st.uni else st.green("OK ")) if ok else (st.red("✗ ") if st.uni else st.red("ERR "))
    lines.append(st.dim(" addr  ") + mark + st.dim("board ⇄ program reversible · stone hue = rgb(band,mid,col)"))
    hops = sum(1 for x, y in zip(prog, prog[1:]) if _TOR.hamming(x, y) == 1)
    arrow = "↻" if st.uni else "(wrap)"
    lines.append(
        st.dim(" torus ")
        + st.cyan("16-periodic %s" % arrow)
        + st.dim(" edges wrap = wormholes · Q6 cube: %d/%d moves are 1-bit hops" % (hops, max(len(prog) - 1, 0)))
    )
    return lines


def render(
    text: str,
    langs: Sequence[str] = ("python",),
    color: bool = True,
    width: int = 58,
    tongue: str = "ko",
    board: bool = False,
) -> str:
    st = _S(_style_enabled(color))
    names, prog = tokens_to_program(text, tongue)
    rep = DNA.verify(names)
    seal = DNA.seal(prog) if DNA._HAVE_SEAL else []
    acc = 0
    for w in seal:
        acc ^= w  # XOR-fold the sealed strand into one fingerprint
    sig = "%016x" % acc if seal else "-"
    dot = "·" if st.uni else "*"

    head = [st.dim("tokens  ") + (" ".join(names) if names else st.dim("(empty)"))]
    spell = tongue_spell(prog, tongue)
    if spell:  # the same program on the Sacred Tongue keyboard
        head.append(st.dim("tongue  ") + st.cyan(spell) + st.dim("  (%s)" % tongue))
    head += [
        st.dim("strand  ")
        + (" ".join("%02x" % b for b in prog) or st.dim(dot))
        + st.dim("   (%d op%s %s 1 object)" % (len(prog), "" if len(prog) == 1 else "s", dot)),
        st.dim("verify  ")
        + "  ".join(
            [
                _badge(rep["all_faces_agree"], "%d/%d faces" % (rep["faces_agree"], rep["faces_total"]), st),
                _badge(rep["seekable"], "seekable", st),
                _badge(bool(rep.get("seal_roundtrip", True)), "sealed", st),
            ]
        ),
        st.dim("runs    ") + _run(prog, st),
        st.dim("geoseal ") + st.mag(sig),
    ]
    blocks = [("SCBE %s cube code" % dot, head, st.cyan)]
    if board:
        blocks.append(("go-board %s cube (%s)" % (dot, tongue), board_lines(prog, tongue, st), st.mag))
    for lang in langs:
        src = P.emit(prog, lang, runnable=True)
        code = []
        for line in src.rstrip("\n").split("\n"):
            m = re.search(r"(" + re.escape(P.REGISTRY[lang].comment) + r".*)$", line)
            if m and m.group(1):
                code.append(line[: m.start(1)] + st.dim(m.group(1)))
            else:
                code.append(line)
        blocks.append((lang, code, st.yellow))

    # one shared inner width so every panel lines up; clamp to the terminal
    term = shutil.get_terminal_size((100, 24)).columns
    content = max(_vis(x) for _, lines, _ in blocks for x in lines)
    inner = min(max(width, content), max(width, term - 2))
    return "\n".join(_panel(title, lines, st, inner, accent) for title, lines, accent in blocks)


def _repl(langs, color, tongue="ko", board=False):
    st = _S(_style_enabled(color))
    dash = "—" if st.uni else "-"
    prompt = "› " if st.uni else "> "
    print(
        st.bold(st.cyan("SCBE cube code"))
        + st.dim(
            "  %s  type tokens (ops, symbols, or %s tongue), Enter to compile."
            "  ':q' quits, ':lang rust', ':tongue av', ':board'." % (dash, tongue)
        )
    )
    cur, tng, brd = list(langs), tongue, board
    while True:
        try:
            line = input(st.cyan(prompt))
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        line = line.strip()
        if line in (":q", ":quit", "exit"):
            return 0
        if line.startswith(":lang"):
            cur = line.split()[1:] or ["python"]
            continue
        if line.startswith(":tongue"):
            tng = (line.split()[1:] or ["ko"])[0]
            continue
        if line == ":board":
            brd = not brd
            continue
        if line == ":all":
            cur = P.languages()
            continue
        if not line:
            continue
        try:
            print(render(line, cur, color, tongue=tng, board=brd))
        except ValueError as e:
            print(st.red("  " + str(e)))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-code", description="type tokens, see the perfect code")
    ap.add_argument("tokens", nargs="*", help="token stream, e.g. + sqrt * inc /  or  sil'a sil'ei")
    ap.add_argument("--lang", action="append", help="language face (repeatable); default python")
    ap.add_argument("--all", action="store_true", help="every language face")
    ap.add_argument("--tongue", default="ko", help="Sacred Tongue for input/spelling (ko av ru ca um dr)")
    ap.add_argument("--board", action="store_true", help="show the go-board / cube embedding")
    ap.add_argument("--repl", action="store_true", help="interactive hit-Enter loop")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)
    color = not a.no_color
    langs = P.languages() if a.all else (a.lang or ["python"])
    if a.repl or not a.tokens:
        return _repl(langs, color, a.tongue, a.board)
    try:
        print(render(" ".join(a.tokens), langs, color, tongue=a.tongue, board=a.board))
        return 0
    except ValueError as e:
        print(_S(_style_enabled(color)).red(str(e)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
