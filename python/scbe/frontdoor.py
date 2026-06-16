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
from . import polyglot as P

# --- the friendly keyboard: any of these -> a core opcode name ------------------
_SYMBOLS = {
    "+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod",
    "^": "pow", "**": "pow", "√": "sqrt", "<": "lt", ">": "gt",
    "<=": "lte", ">=": "gte", "==": "eq", "!=": "neq", "++": "inc", "--": "dec",
    "|": "abs", "~": "neg",
}
_ALIASES = {"power": "pow", "modulo": "mod", "minimum": "min", "maximum": "max",
            "negate": "neg", "absolute": "abs", "increment": "inc", "decrement": "dec",
            "root": "sqrt"}


def tokens_to_program(text: str) -> Tuple[List[str], List[int]]:
    """THE FRONT DOOR: a typed token stream -> (op names, opcode bytes).

    Accepts core op names, friendly symbols/aliases, and 0xNN hex bytes. Raises a
    ValueError with a 'did you mean' hint on anything it can't place."""
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

    def bold(self, s):  return self._w(s, "1")
    def dim(self, s):   return self._w(s, "2")
    def cyan(self, s):  return self._w(s, "36")
    def green(self, s): return self._w(s, "32")
    def red(self, s):   return self._w(s, "31")
    def yellow(self, s): return self._w(s, "33")
    def mag(self, s):   return self._w(s, "35")


def _vis(s: str) -> int:
    return len(_ANSI.sub("", s))


def _clip(s: str, w: int, st: _S) -> str:
    if _vis(s) <= w:
        return s
    ellipsis = "…" if st.uni else "..."
    return st.dim(_ANSI.sub("", s)[:max(0, w - len(ellipsis))] + ellipsis)


def _panel(title: str, lines: Sequence[str], st: _S, inner: int, accent=None) -> str:
    """Render a titled box at a FIXED inner width so stacked panels line up."""
    accent = accent or st.cyan
    if _vis(title) > inner - 4:
        ellipsis = "…" if st.uni else "..."
        title = _ANSI.sub("", title)[:inner - 4 - len(ellipsis)] + ellipsis
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
        try:                                                 # undefined zone -> roundabout
            warn = st.yellow("⚠ ") if st.uni else st.yellow("WARN ")
            arrow = "→" if st.uni else "->"
            return warn + "undefined (%s) %s roundabout %s" % (
                type(e).__name__, arrow, st.bold(_fmt(call(True))))
        except Exception as e2:                              # pragma: no cover - defensive
            err = st.red("✗ ") if st.uni else st.red("ERR ")
            return err + "error: %s" % type(e2).__name__
    except IndexError:                                       # not enough values on the stack
        dot = "·" if st.uni else "*"
        return st.dim(dot + " incomplete strand (needs more operands)")
    except Exception as e:                                   # pragma: no cover - defensive
        dot = "·" if st.uni else "*"
        return st.dim(dot + " did not run (%s)" % type(e).__name__)


def render(text: str, langs: Sequence[str] = ("python",), color: bool = True,
           width: int = 58) -> str:
    st = _S(_style_enabled(color))
    names, prog = tokens_to_program(text)
    rep = DNA.verify(names)
    seal = DNA.seal(prog) if DNA._HAVE_SEAL else []
    acc = 0
    for w in seal:
        acc ^= w                                  # XOR-fold the sealed strand into one fingerprint
    sig = "%016x" % acc if seal else "-"
    dot = "·" if st.uni else "*"

    head = [
        st.dim("tokens  ") + (" ".join(names) if names else st.dim("(empty)")),
        st.dim("strand  ") + (" ".join("%02x" % b for b in prog) or st.dim(dot)) +
        st.dim("   (%d op%s %s 1 object)" % (len(prog), "" if len(prog) == 1 else "s", dot)),
        st.dim("verify  ") + "  ".join([
            _badge(rep["all_faces_agree"], "%d/%d faces" % (rep["faces_agree"], rep["faces_total"]), st),
            _badge(rep["seekable"], "seekable", st),
            _badge(bool(rep.get("seal_roundtrip", True)), "sealed", st),
        ]),
        st.dim("runs    ") + _run(prog, st),
        st.dim("geoseal ") + st.mag(sig),
    ]
    blocks = [("SCBE %s cube code" % dot, head, st.cyan)]
    for lang in langs:
        src = P.emit(prog, lang, runnable=True)
        code = []
        for line in src.rstrip("\n").split("\n"):
            m = re.search(r"(" + re.escape(P.REGISTRY[lang].comment) + r".*)$", line)
            if m and m.group(1):
                code.append(line[:m.start(1)] + st.dim(m.group(1)))
            else:
                code.append(line)
        blocks.append((lang, code, st.yellow))

    # one shared inner width so every panel lines up; clamp to the terminal
    term = shutil.get_terminal_size((100, 24)).columns
    content = max(_vis(x) for _, lines, _ in blocks for x in lines)
    inner = min(max(width, content), max(width, term - 2))
    return "\n".join(_panel(title, lines, st, inner, accent) for title, lines, accent in blocks)


def _repl(langs, color):
    st = _S(_style_enabled(color))
    dash = "—" if st.uni else "-"
    prompt = "› " if st.uni else "> "
    print(st.bold(st.cyan("SCBE cube code")) + st.dim("  %s  type tokens, Enter to compile.  ':q' quits, ':lang rust' switches." % dash))
    cur = list(langs)
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
        if line == ":all":
            cur = P.languages()
            continue
        if not line:
            continue
        try:
            print(render(line, cur, color))
        except ValueError as e:
            print(st.red("  " + str(e)))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="scbe-code", description="type tokens, see the perfect code")
    ap.add_argument("tokens", nargs="*", help="token stream, e.g. + sqrt * inc /")
    ap.add_argument("--lang", action="append", help="language face (repeatable); default python")
    ap.add_argument("--all", action="store_true", help="every language face")
    ap.add_argument("--repl", action="store_true", help="interactive hit-Enter loop")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)
    color = not a.no_color
    langs = P.languages() if a.all else (a.lang or ["python"])
    if a.repl or not a.tokens:
        return _repl(langs, color)
    try:
        print(render(" ".join(a.tokens), langs, color))
        return 0
    except ValueError as e:
        print(_S(_style_enabled(color)).red(str(e)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
