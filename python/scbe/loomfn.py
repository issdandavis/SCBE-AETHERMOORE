"""loomfn: data structures (arrays) and user-defined functions (call/return, recursion) that
emit into many language faces and are verified by EXECUTION -- the layer past loomflow's
straight-line + branching scalar core.

loomflow proved that branching/looping programs run identically across faces via a dispatch
loop (a `while` over a program counter, one `if pc == k` arm per instruction -- no goto). loomfn
keeps that exact shape and adds the two things a real language needs:

  * ARRAYS (the heap): `arr A` / `push A x` / `pop d A` / `get d A i` / `set A i x` / `alen d A`.
    Arrays are shared/global (a heap), so a function mutating one is visible to its caller.
  * FUNCTIONS (the stack): `func name p1..pn` ... `ret x`, called by `call d name a1..an`.
    Calling convention is caller-saves: a call snapshots all scalar slots, zeroes them, binds the
    params, and jumps; `ret` restores the snapshot and delivers the result into `d`. That gives
    real local scoping and real RECURSION (factorial, fibonacci) -- not just inline blocks.
  * STRINGS (text): a string is just a heap array of character codes, so every array op already
    works on it (alen = length, get = char-at, push = append-char). The text layer adds only what
    codes alone can't express: `str A "literal"` (load a literal's codes into array A), `prints A`
    (print A decoded as text), `char d c` (one character -> its code, for comparisons), `concat A B`
    (append B's codes onto A), and `mod d x y` (used by fizzbuzz; identical semantics on every face).
    The answer a program is verified on can now be TEXT (compared as a string) or a number.

The value model is index-based: scalar slots live in one flat array `s` (name->index resolved at
emit time), which makes a call-frame snapshot a single copy of `s` in every language. A Python
interpreter of the IR is the reference; every emitted face is RUN and compared to it, so
"functions and data structures work across languages" is a tested fact, not a claim.

Locally verifiable faces here: python, javascript (node), rust (rustc). C/others can follow once
a toolchain exists -- this never reports a face as agreeing unless it actually ran and matched.

    const n 5 / call r fact n / print r / halt
    func fact n / const one 1 / le b n one / brz b rec / ret one
    label rec / sub m n one / call fr fact m / mul res n fr / ret res     # -> 120, py+js+rust
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

Instr = Tuple[str, Tuple[str, ...]]

_ARITH = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
_CMP = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "==", "ne": "!="}
_ARR = {"arr", "push", "pop", "get", "set", "alen"}
_FN = {"func", "ret", "call"}
_STR = {"str", "prints", "char", "concat"}  # text values are heap arrays of char codes
_OPS = (
    {"const", "mov", "inc", "dec", "label", "jmp", "brz", "print", "halt", "mod"}
    | set(_ARITH)
    | set(_CMP)
    | _ARR
    | _FN
    | _STR
)


def _unquote(tok: str) -> str:
    """Strip surrounding double quotes from a string/char literal token."""
    return tok[1:-1] if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"' else tok


def _tokenize(line: str) -> List[str]:
    """Whitespace-split, but keep a double-quoted literal (which may contain spaces) as one token."""
    toks: List[str] = []
    i, n = 0, len(line)
    while i < n:
        if line[i].isspace():
            i += 1
            continue
        if line[i] == '"':
            j = line.find('"', i + 1)
            if j < 0:
                raise ValueError("unterminated string literal in %r" % line)
            toks.append(line[i : j + 1])
            i = j + 1
        else:
            j = i
            while j < n and not line[j].isspace():
                j += 1
            toks.append(line[i:j])
            i = j
    return toks


def parse(text: str) -> List[Instr]:
    """Parse the line-based assembly into (op, args) instructions (; and # are comments).

    Note: `/` separates instructions and `;`/`#` start comments, so a string literal cannot contain
    those three characters -- a deliberate limit of this tiny assembler, not of the value model.
    """
    prog: List[Instr] = []
    for raw in text.replace("/", "\n").splitlines():
        line = raw.split(";", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        parts = _tokenize(line)
        op, args = parts[0].lower(), tuple(parts[1:])
        if op not in _OPS:
            raise ValueError("unknown op %r (have %s)" % (op, ", ".join(sorted(_OPS))))
        prog.append((op, args))
    return prog


def _classify(op: str, a: Tuple[str, ...]) -> Tuple[List[str], List[str]]:
    """Return (scalar slot names, array names) referenced by this instruction."""
    sc: List[str] = []
    ar: List[str] = []
    if op == "const":
        sc = [a[0]]
    elif op == "mov":
        sc = [a[0], a[1]]
    elif op in _ARITH or op in _CMP or op == "mod":
        sc = [a[0], a[1], a[2]]
    elif op == "char":  # a[1] is a character literal (data), not a slot
        sc = [a[0]]
    elif op in ("str", "prints"):  # a[1] of str is a literal; the array is the value
        ar = [a[0]]
    elif op == "concat":
        ar = [a[0], a[1]]
    elif op in ("inc", "dec", "print", "brz"):
        sc = [a[0]]
    elif op == "arr":
        ar = [a[0]]
    elif op == "push":
        ar, sc = [a[0]], [a[1]]
    elif op == "pop":
        sc, ar = [a[0]], [a[1]]
    elif op == "get":
        sc, ar = [a[0], a[2]], [a[1]]
    elif op == "set":
        ar, sc = [a[0]], [a[1], a[2]]
    elif op == "alen":
        sc, ar = [a[0]], [a[1]]
    elif op == "func":
        sc = list(a[1:])  # params (a[0] is the function name)
    elif op == "ret":
        sc = list(a[:1])  # optional return slot
    elif op == "call":
        sc = [a[0]] + list(a[2:])  # dest + arg slots (a[1] is the function name)
    return sc, ar


def _labels(prog: Sequence[Instr]) -> Dict[str, int]:
    return {a[0]: i for i, (op, a) in enumerate(prog) if op == "label"}


def _funcs(prog: Sequence[Instr]) -> Dict[str, Tuple[int, List[str]]]:
    return {a[0]: (i, list(a[1:])) for i, (op, a) in enumerate(prog) if op == "func"}


def _ordered(prog: Sequence[Instr], which: int) -> List[str]:
    names: List[str] = []
    for op, a in prog:
        for n in _classify(op, a)[which]:
            if n not in names:
                names.append(n)
    return names


def _slots(prog: Sequence[Instr]) -> List[str]:
    return _ordered(prog, 0)


def _arrays(prog: Sequence[Instr]) -> List[str]:
    return _ordered(prog, 1)


# --- the reference interpreter -------------------------------------------------


def interpret(prog: Sequence[Instr], step_limit: int = 1_000_000) -> List[float]:
    """Run the IR directly (the reference every face is compared against); return printed values."""
    labels, funcs = _labels(prog), _funcs(prog)
    s: Dict[str, float] = {n: 0.0 for n in _slots(prog)}
    h: Dict[str, List[float]] = {n: [] for n in _arrays(prog)}
    call: List[Tuple[int, str, Dict[str, float]]] = []  # (return_pc, dest, saved scalar slots)
    out: List = []  # printed answers: a float (print) or a str (prints)
    pc, steps = 0, 0
    while 0 <= pc < len(prog):
        steps += 1
        if steps > step_limit:
            raise RuntimeError("step limit exceeded (infinite loop?)")
        op, a = prog[pc]
        if op == "const":
            s[a[0]] = float(a[1])
            pc += 1
        elif op == "mov":
            s[a[0]] = s[a[1]]
            pc += 1
        elif op in _ARITH:
            x, y = s[a[1]], s[a[2]]
            s[a[0]] = x + y if op == "add" else x - y if op == "sub" else x * y if op == "mul" else x / y
            pc += 1
        elif op in _CMP:
            x, y = s[a[1]], s[a[2]]
            r = {"lt": x < y, "le": x <= y, "gt": x > y, "ge": x >= y, "eq": x == y, "ne": x != y}[op]
            s[a[0]] = 1.0 if r else 0.0
            pc += 1
        elif op == "inc":
            s[a[0]] += 1.0
            pc += 1
        elif op == "dec":
            s[a[0]] -= 1.0
            pc += 1
        elif op == "arr":
            h[a[0]] = []
            pc += 1
        elif op == "push":
            h[a[0]].append(s[a[1]])
            pc += 1
        elif op == "pop":
            s[a[0]] = h[a[1]].pop()
            pc += 1
        elif op == "get":
            s[a[0]] = h[a[1]][int(s[a[2]])]
            pc += 1
        elif op == "set":
            h[a[0]][int(s[a[1]])] = s[a[2]]
            pc += 1
        elif op == "alen":
            s[a[0]] = float(len(h[a[1]]))
            pc += 1
        elif op == "mod":
            x, y = s[a[1]], s[a[2]]
            s[a[0]] = x - y * float(int(x / y))  # truncated (C/JS/Rust %) -- identical on every face
            pc += 1
        elif op == "str":
            h[a[0]] = [float(ord(ch)) for ch in _unquote(a[1])]
            pc += 1
        elif op == "char":
            s[a[0]] = float(ord(_unquote(a[1])))
            pc += 1
        elif op == "concat":
            h[a[0]].extend(h[a[1]])
            pc += 1
        elif op == "prints":
            out.append("".join(chr(int(c)) for c in h[a[0]]))
            pc += 1
        elif op == "label" or op == "func":
            pc += 1
        elif op == "jmp":
            pc = labels[a[0]]
        elif op == "brz":
            pc = labels[a[1]] if s[a[0]] == 0.0 else pc + 1
        elif op == "call":
            if a[1] not in funcs:
                raise ValueError("call to unknown function %r" % (a[1],))
            entry, params = funcs[a[1]]
            vals = [s[x] for x in a[2:]]
            call.append((pc + 1, a[0], dict(s)))
            for n in s:
                s[n] = 0.0
            for p, v in zip(params, vals):
                s[p] = v
            pc = entry + 1
        elif op == "ret":
            result = s[a[0]] if a else 0.0
            rp, dst, saved = call.pop()
            s.update(saved)
            s[dst] = result
            pc = rp
        elif op == "print":
            out.append(s[a[0]])
            pc += 1
        elif op == "halt":
            break
    return out


# --- per-language dispatch-loop emit (python / javascript / rust) --------------
# Scalar slots live in a flat array `s` indexed by slot id; arrays in `h`; a call snapshots `s`
# onto a parallel stack, zeroes it, binds params, and jumps. Same shape in every language.


def _num(v: str) -> str:
    return repr(float(v))


def _arm(prog, k, lang, six, aix, labels, funcs, nslots) -> List[str]:
    """The source lines (effect(s) + pc update) for instruction k in `lang`."""
    op, a = prog[k]

    def S(name):  # a scalar slot reference -> "s[<index>]"
        return "s[%d]" % six[name]

    def nxt(target):
        return "pc = %d" % target if lang == "python" else "pc = %d;" % target

    semi = "" if lang == "python" else ";"
    idx = {"python": "int(%s)", "javascript": "Math.trunc(%s)", "rust": "%s as usize"}[lang]

    if op == "const":
        return ["%s = %s%s" % (S(a[0]), _num(a[1]), semi), nxt(k + 1)]
    if op == "mov":
        return ["%s = %s%s" % (S(a[0]), S(a[1]), semi), nxt(k + 1)]
    if op in _ARITH:
        return ["%s = %s %s %s%s" % (S(a[0]), S(a[1]), _ARITH[op], S(a[2]), semi), nxt(k + 1)]
    if op in _CMP:
        cond = "%s %s %s" % (S(a[1]), _CMP[op], S(a[2]))
        tern = {
            "python": "(1.0 if %s else 0.0)",
            "javascript": "(%s ? 1.0 : 0.0)",
            "rust": "if %s { 1.0 } else { 0.0 }",
        }[lang]
        return ["%s = %s%s" % (S(a[0]), tern % cond, semi), nxt(k + 1)]
    if op == "inc":
        return ["%s = %s + 1.0%s" % (S(a[0]), S(a[0]), semi), nxt(k + 1)]
    if op == "dec":
        return ["%s = %s - 1.0%s" % (S(a[0]), S(a[0]), semi), nxt(k + 1)]
    if op == "arr":
        clear = {"python": "h[%d] = []", "javascript": "h[%d] = [];", "rust": "h[%d].clear();"}[lang]
        return [clear % aix[a[0]], nxt(k + 1)]
    if op == "push":
        push = {"python": "h[%d].append(%s)", "javascript": "h[%d].push(%s);", "rust": "h[%d].push(%s);"}[lang]
        return [push % (aix[a[0]], S(a[1])), nxt(k + 1)]
    if op == "pop":
        pop = {"python": "%s = h[%d].pop()", "javascript": "%s = h[%d].pop();", "rust": "%s = h[%d].pop().unwrap();"}[
            lang
        ]
        return [pop % (S(a[0]), aix[a[1]]), nxt(k + 1)]
    if op == "get":
        return ["%s = h[%d][%s]%s" % (S(a[0]), aix[a[1]], idx % S(a[2]), semi), nxt(k + 1)]
    if op == "set":
        return ["h[%d][%s] = %s%s" % (aix[a[0]], idx % S(a[1]), S(a[2]), semi), nxt(k + 1)]
    if op == "alen":
        ln = {
            "python": "%s = float(len(h[%d]))",
            "javascript": "%s = h[%d].length;",
            "rust": "%s = h[%d].len() as f64;",
        }[lang]
        return [ln % (S(a[0]), aix[a[1]]), nxt(k + 1)]
    if op == "mod":
        # truncated remainder, kept identical on every face: native % on js/rust, the same formula on python
        if lang == "python":
            expr = "%s - %s * float(int(%s / %s))" % (S(a[1]), S(a[2]), S(a[1]), S(a[2]))
        else:
            expr = "%s %% %s" % (S(a[1]), S(a[2]))
        return ["%s = %s%s" % (S(a[0]), expr, semi), nxt(k + 1)]
    if op == "str":
        codes = ", ".join(_num(str(ord(ch))) for ch in _unquote(a[1]))
        lit = {"python": "h[%d] = [%s]", "javascript": "h[%d] = [%s];", "rust": "h[%d] = vec![%s];"}[lang]
        return [lit % (aix[a[0]], codes), nxt(k + 1)]
    if op == "char":
        return ["%s = %s%s" % (S(a[0]), repr(float(ord(_unquote(a[1])))), semi), nxt(k + 1)]
    if op == "concat":
        cc = {
            "python": "h[%d].extend(h[%d])" % (aix[a[0]], aix[a[1]]),
            "javascript": "for (const _e of h[%d]) h[%d].push(_e);" % (aix[a[1]], aix[a[0]]),
            "rust": "{ let _b = h[%d].clone(); h[%d].extend(_b); }" % (aix[a[1]], aix[a[0]]),
        }[lang]
        return [cc, nxt(k + 1)]
    if op == "prints":
        pr = {
            "python": "_out.append(''.join(chr(int(_c)) for _c in h[%d]))" % aix[a[0]],
            "javascript": "console.log(h[%d].map(_c => String.fromCharCode(_c)).join(''));" % aix[a[0]],
            "rust": '{ let _s: String = h[%d].iter().map(|c| (*c as u8) as char).collect(); println!("{}", _s); }'
            % aix[a[0]],
        }[lang]
        return [pr, nxt(k + 1)]
    if op == "label" or op == "func":
        return [nxt(k + 1)]
    if op == "jmp":
        return [nxt(labels[a[0]])]
    if op == "brz":
        tgt, fall = labels[a[1]], k + 1
        cond = "%s == 0.0" % S(a[0])
        if lang == "python":
            return ["pc = %d if %s else %d" % (tgt, cond, fall)]
        return (
            ["if (%s) { pc = %d; } else { pc = %d; }" % (cond, tgt, fall)]
            if lang != "rust"
            else ["if %s { pc = %d; } else { pc = %d; }" % (cond, tgt, fall)]
        )
    if op == "call":
        entry = funcs[a[1]][0] + 1
        params = funcs[a[1]][1]
        argv = ", ".join(S(x) for x in a[2:])
        binds = "; ".join("s[%d] = _v[%d]" % (six[p], i) for i, p in enumerate(params))
        if lang == "python":
            out = ["_v = [%s]" % argv]
            out.append("_cs_ret.append(%d); _cs_dst.append(%d); _cs_save.append(s[:])" % (k + 1, six[a[0]]))
            out.append("for _z in range(%d): s[_z] = 0.0" % nslots)
            if binds:
                out.append(binds)
            out.append("pc = %d" % entry)
            return out
        if lang == "javascript":
            out = ["const _v = [%s];" % argv]
            out.append("_cs_ret.push(%d); _cs_dst.push(%d); _cs_save.push(s.slice());" % (k + 1, six[a[0]]))
            out.append("for (let _z = 0; _z < %d; _z++) s[_z] = 0.0;" % nslots)
            if binds:
                out.append(binds + ";")
            out.append("pc = %d;" % entry)
            return out
        out = ["let _v: Vec<f64> = vec![%s];" % argv]
        out.append("_cs_ret.push(%d); _cs_dst.push(%d); _cs_save.push(s.clone());" % (k + 1, six[a[0]]))
        out.append("for _z in 0..%d { s[_z] = 0.0; }" % nslots)
        if binds:
            out.append(binds + ";")
        out.append("pc = %d;" % entry)
        return out
    if op == "ret":
        rv = S(a[0]) if a else "0.0"
        if lang == "python":
            return [
                "_r = %s" % rv,
                "_ssave = _cs_save.pop(); _sdst = _cs_dst.pop(); _sret = _cs_ret.pop()",
                "s[:] = _ssave; s[_sdst] = _r; pc = _sret",
            ]
        if lang == "javascript":
            return [
                "const _r = %s;" % rv,
                "const _ssave = _cs_save.pop(); const _sdst = _cs_dst.pop(); const _sret = _cs_ret.pop();",
                "for (let _z = 0; _z < %d; _z++) s[_z] = _ssave[_z];" % nslots,
                "s[_sdst] = _r; pc = _sret;",
            ]
        return [
            "let _r = %s;" % rv,
            "let _ssave = _cs_save.pop().unwrap(); let _sdst = _cs_dst.pop().unwrap(); "
            "let _sret = _cs_ret.pop().unwrap();",
            "for _z in 0..%d { s[_z] = _ssave[_z]; }" % nslots,
            "s[_sdst] = _r; pc = _sret;",
        ]
    if op == "print":
        pr = {
            "python": "_out.append(%s)" % S(a[0]),
            "javascript": "console.log(%s);" % S(a[0]),
            "rust": 'println!("{}", %s);' % S(a[0]),
        }[lang]
        return [pr, nxt(k + 1)]
    if op == "halt":
        return [nxt(-1)]
    raise ValueError("no emit for op %r" % (op,))


def emit(prog: Sequence[Instr], lang: str) -> str:
    """Emit the program as a dispatch loop in `lang` (python / javascript / rust)."""
    if lang not in ("python", "javascript", "rust"):
        raise ValueError("loomfn emits python/javascript/rust (got %r)" % (lang,))
    labels, funcs = _labels(prog), _funcs(prog)
    slots, arrs = _slots(prog), _arrays(prog)
    six = {n: i for i, n in enumerate(slots)}
    aix = {n: i for i, n in enumerate(arrs)}
    ns, na, n = len(slots), len(arrs), len(prog)
    arms = [_arm(prog, k, lang, six, aix, labels, funcs, ns) for k in range(n)]

    if lang == "python":
        body = [
            "    s = [0.0] * %d" % max(ns, 1),
            "    h = [[] for _ in range(%d)]" % na,
            "    _cs_ret = []",
            "    _cs_dst = []",
            "    _cs_save = []",
            "    _out = []",
            "    pc = 0",
            "    while 0 <= pc < %d:" % n,
        ]
        for k, lines in enumerate(arms):
            body.append("        if pc == %d:" % k if k == 0 else "        elif pc == %d:" % k)
            body += ["            " + ln for ln in lines]
        body += ["        else:", "            pc = -1", "    return _out[-1] if _out else None"]
        return "def run():\n" + "\n".join(body) + "\n\n\nif __name__ == '__main__':\n    print(run())\n"

    if lang == "javascript":
        lines = [
            "function run() {",
            "  let s = new Array(%d).fill(0.0);" % max(ns, 1),
            "  let h = Array.from({length: %d}, () => []);" % na,
            "  let _cs_ret = [], _cs_dst = [], _cs_save = [];",
            "  let _out = [];",
            "  let pc = 0;",
            "  while (pc >= 0 && pc < %d) {" % n,
        ]
        for k, arm in enumerate(arms):
            kw = "if" if k == 0 else "} else if"
            lines.append("    %s (pc == %d) {" % (kw, k))
            lines += ["      " + ln for ln in arm]
        lines += [
            "    } else { pc = -1; }",
            "  }",
            "  return _out.length ? _out[_out.length - 1] : null;",
            "}",
            "run();",
        ]
        return "\n".join(lines) + "\n"

    # rust
    lines = [
        "fn run() -> Option<f64> {",
        "    let mut s: Vec<f64> = vec![0.0; %d];" % max(ns, 1),
        "    let mut h: Vec<Vec<f64>> = vec![vec![]; %d];" % na,
        "    let mut _cs_ret: Vec<i64> = vec![];",
        "    let mut _cs_dst: Vec<usize> = vec![];",
        "    let mut _cs_save: Vec<Vec<f64>> = vec![];",
        "    let mut _out: Vec<f64> = vec![];",
        "    let mut pc: i64 = 0;",
        "    while pc >= 0 && pc < %d {" % n,
    ]
    for k, arm in enumerate(arms):
        kw = "if" if k == 0 else "} else if"
        lines.append("        %s pc == %d {" % (kw, k))
        lines += ["            " + ln for ln in arm]
    lines += ["        } else { pc = -1; }", "    }", "    _out.last().copied()", "}"]
    lines += ["fn main() {", "    let _ = run();", "}"]
    # silence unused-mut warnings for programs without arrays/functions
    return "#![allow(unused_mut, unused_variables)]\n" + "\n".join(lines) + "\n"


# --- run each emitted face and compare to the reference ------------------------
_RUN = {"python": None, "javascript": "node", "rust": "rustc"}


def _parse_float(line: Optional[str]) -> Optional[float]:
    if line is None:
        return None
    if line.lower() in ("nan", "-nan"):
        return float("nan")
    try:
        return float(line)
    except ValueError:
        return None


def _face_line(prog: Sequence[Instr], lang: str) -> Optional[str]:
    """Emit + run a face; return its last stdout line verbatim (a number OR a text answer)."""
    src = emit(prog, lang)
    with tempfile.TemporaryDirectory() as td:
        ext = {"python": "py", "javascript": "js", "rust": "rs"}[lang]
        f = Path(td) / ("prog." + ext)
        f.write_text(src, encoding="utf-8")
        if lang == "python":
            stdout = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, timeout=30).stdout
        elif lang == "javascript":
            stdout = subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=30).stdout
        else:
            exe = Path(td) / ("prog.exe" if shutil.which("cmd") else "prog")
            subprocess.run(
                ["rustc", "-O", str(f), "-o", str(exe)], capture_output=True, text=True, timeout=120, check=True
            )
            stdout = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30).stdout
    lines = stdout.strip().splitlines()
    line = lines[-1].strip() if lines else ""
    return None if line in ("", "None", "null") else line


def run_face(prog: Sequence[Instr], lang: str) -> Optional[float]:
    """Back-compatible numeric runner: the face's last line parsed as a float (None if it is text)."""
    return _parse_float(_face_line(prog, lang))


def verify(prog: Sequence[Instr], faces: Sequence[str] = ("python", "javascript", "rust")) -> dict:
    """Run the reference, then every face with a local toolchain; compare each honestly.

    The answer is whatever the program printed last -- a number (compared within 1e-9) or text
    (compared as an exact string). A face only counts as AGREE if it actually ran and matched.
    """
    ref = interpret(prog)
    reference = ref[-1] if ref else None
    text_answer = isinstance(reference, str)
    results: Dict[str, dict] = {}
    for lang in faces:
        tool = _RUN.get(lang, "<none>")
        if tool is not None and shutil.which(tool) is None:
            results[lang] = {"status": "NO_TOOLCHAIN", "value": None}
            continue
        try:
            line = _face_line(prog, lang)
        except Exception as e:
            results[lang] = {"status": "ERROR", "value": None, "note": "%s: %s" % (type(e).__name__, e)}
            continue
        if text_answer:
            value: object = line
            agree = line == reference
        else:
            value = _parse_float(line)
            agree = value == reference or (
                value is not None and reference is not None and abs(value - reference) <= 1e-9
            )
        results[lang] = {"status": "AGREE" if agree else "DISAGREE", "value": value}
    verified = [lang for lang, r in results.items() if r["status"] == "AGREE"]
    return {
        "reference": reference,
        "results": results,
        "verified": verified,
        "verified_count": len(verified),
        "disagree": [lang for lang, r in results.items() if r["status"] == "DISAGREE"],
    }


EXAMPLES = {
    # build [1..5] in an array, then sum the array -> 15  (data structure + loop)
    "array_sum": "arr xs / const i 1 / const n 5 / label fill / le t i n / brz t sums / push xs i / inc i / jmp fill / "
    "label sums / const acc 0 / const j 0 / alen len xs / label sl / lt c j len / brz c done / get v xs j / "
    "add acc acc v / inc j / jmp sl / label done / print acc / halt",
    # find the max of [3,7,2,9,4] -> 9  (array indexing + branch)
    "array_max": "arr xs / const v 3 / push xs v / const v 7 / push xs v / const v 2 / push xs v / const v 9 / "
    "push xs v / const v 4 / push xs v / const j 0 / alen len xs / get m xs j / inc j / label lp / lt c j len / "
    "brz c done / get v xs j / gt g v m / brz g skip / mov m v / label skip / inc j / jmp lp / label done / "
    "print m / halt",
    # a 2-arg function -> 7  (call/return, params)
    "add_fn": "const a 3 / const b 4 / call r addup a b / print r / halt / func addup x y / add s x y / ret s",
    # recursive factorial 5! -> 120  (recursion via the frame stack)
    "factorial_recursive": "const n 5 / call r fact n / print r / halt / func fact n / const one 1 / le b n one / "
    "brz b rec / ret one / label rec / sub m n one / call fr fact m / mul res n fr / ret res",
    # recursive fibonacci fib(10) -> 55  (two recursive calls per frame)
    "fib_recursive": "const n 10 / call r fib n / print r / halt / func fib n / const two 2 / lt b n two / brz b rec / "
    "ret n / label rec / const one 1 / sub x n one / call fa fib x / sub y n two / call fb fib y / add z fa fb / "
    "ret z",
    # a function that sums a shared (heap) array -> 60  (functions + data structures together)
    "sum_array_fn": "arr xs / const v 10 / push xs v / const v 20 / push xs v / const v 30 / push xs v / "
    "call r total / print r / halt / func total / const acc 0 / const j 0 / alen len xs / label sl / lt c j len / "
    "brz c done / get e xs j / add acc acc e / inc j / jmp sl / label done / ret acc",
    # reverse a string -> "olleh"  (text in, text out: str literal + index + prints)
    "string_reverse": 'str s "hello" / arr r / alen n s / const one 1 / const i 0 / label lp / lt c i n / '
    "brz c done / sub k n one / sub k k i / get ch s k / push r ch / inc i / jmp lp / label done / prints r / halt",
    # concatenate two strings -> "foobar"  (concat op)
    "string_concat": 'str a "foo" / str b "bar" / concat a b / prints a / halt',
    # fizzbuzz on 15 -> "FizzBuzz"  (mod + a text branch: (n%3)+(n%5)==0)
    "fizzbuzz_15": "const n 15 / const three 3 / const five 5 / mod x n three / mod y n five / add z x y / "
    'brz z fb / str no "no" / prints no / halt / label fb / str yes "FizzBuzz" / prints yes / halt',
    # is the first character of "(ab)" an open paren -> 1  (char literal + string index + compare)
    "char_match": 'str s "(ab)" / const z 0 / get c s z / char op "(" / eq r c op / print r / halt',
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-loomfn", description="arrays + functions across language faces, verified")
    ap.add_argument("example", nargs="?", default="factorial_recursive", choices=sorted(EXAMPLES))
    ap.add_argument("--emit", help="print the emitted source for one face (python/javascript/rust)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    prog = parse(EXAMPLES[a.example])
    if a.emit:
        print(emit(prog, a.emit))
        return 0
    r = verify(prog)
    print("LOOMFN  %s  (arrays + functions)  reference=%s" % (a.example, r["reference"]))
    print("  verified faces: %d  ->  %s" % (r["verified_count"], ", ".join(r["verified"]) or "(none)"))
    for lang in sorted(r["results"]):
        d = r["results"][lang]
        print("    %-12s %-12s value=%s%s" % (lang, d["status"], d["value"], "  " + d.get("note", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
