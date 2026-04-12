"""GeoSeal CLI — swarm dispatcher across the 6 Sacred Tongue languages.

One entry point that takes a tokenizer op from the CA Unified Multilingual
Lexicon, emits the corresponding code snippet in any / all tongues, optionally
runs it in a language-specific subprocess, and wraps the result in a GeoSeal
governance stamp (tongue phase + hyperbolic trust).

Tongue -> language map (from ca_lexicon):
    KO -> python       (Kor'aelin)
    AV -> typescript   (Avali)       -- runs via node, compiles TS inline
    RU -> rust         (Runethic)    -- requires rustc toolchain
    CA -> c            (Cassisivadan)-- requires a C compiler
    UM -> julia        (Umbroth)
    DR -> haskell      (Draumric)    -- requires runghc

Subcommands:
    ops                 list every op in the 64-op lexicon
    emit <op>           emit code in all 6 tongues (or --tongue KO)
    run  <op>           emit and execute the op (uses runnable tongues only)
    swarm <op>          dispatch the op to multiple tongue bots in one call
    seal  <payload>     apply a GeoSeal phase signature to an arbitrary string
    verify <seal>       verify an existing seal against a payload

Every swarm / run call is written as a governance record to
    .scbe/geoseal_calls.jsonl
so the training pipeline can replay every swarm invocation as SFT data.

Usage:
    python -m src.geoseal_cli ops
    python -m src.geoseal_cli emit div --a x --b y
    python -m src.geoseal_cli run  add --a 2 --b 3 --tongue KO
    python -m src.geoseal_cli swarm add --a 2 --b 3 --tongues KO,AV,UM
    python -m src.geoseal_cli seal  "hello world" --tongue KO
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.ca_lexicon import (
    ALL_LANG_MAP,
    ALL_TONGUE_NAMES,
    EXTENDED_LANG_MAP,
    EXTENDED_TONGUE_NAMES,
    LANG_MAP,
    LEXICON,
    LEXICON_BY_NAME,
    TONGUE_NAMES,
    TONGUE_PARENT,
    emit_all_tongues,
    emit_all_tongues_extended,
    emit_code,
    emit_extended,
    lookup,
)

PHI = (1 + 5**0.5) / 2

TONGUE_PHASES: Dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

EXTENDED_TONGUE_PHASES: Dict[str, float] = {
    "GO": 7 * math.pi / 6,
    "ZI": math.pi / 2,
}

ALL_TONGUE_PHASES: Dict[str, float] = {**TONGUE_PHASES, **EXTENDED_TONGUE_PHASES}

DEFAULT_LEDGER = Path(".scbe/geoseal_calls.jsonl")


@dataclass
class SwarmCallResult:
    op: str
    tongue: str
    language: str
    code: str
    ran: bool
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None
    duration_ms: float = 0.0
    phase: float = 0.0
    seal: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmResult:
    op: str
    args: Dict[str, str]
    calls: List[SwarmCallResult] = field(default_factory=list)
    timestamp: float = 0.0
    quorum_ok: bool = False
    consensus_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.op,
            "args": self.args,
            "timestamp": self.timestamp,
            "quorum_ok": self.quorum_ok,
            "consensus_hash": self.consensus_hash,
            "calls": [c.to_dict() for c in self.calls],
        }


def compute_seal(op: str, tongue: str, code: str, payload: str = "") -> str:
    """GeoSeal signature: tongue phase + sha256 of (op|tongue|code|payload)."""
    phase = ALL_TONGUE_PHASES[tongue]
    h = hashlib.sha256()
    h.update(op.encode("utf-8"))
    h.update(b"|")
    h.update(tongue.encode("utf-8"))
    h.update(b"|")
    h.update(code.encode("utf-8"))
    h.update(b"|")
    h.update(payload.encode("utf-8"))
    h.update(b"|")
    h.update(f"{phase:.12f}".encode("utf-8"))
    return h.hexdigest()


def verify_seal(expected: str, op: str, tongue: str, code: str, payload: str = "") -> bool:
    return compute_seal(op, tongue, code, payload) == expected


def _runner_for(tongue: str) -> Optional[Tuple[List[str], str]]:
    """Return (argv_prefix, mode) for a runnable tongue, or None."""
    if tongue == "KO":
        return ([sys.executable, "-c"], "inline")
    if tongue == "AV":
        node = shutil.which("node")
        if node:
            return ([node, "-e"], "inline")
    if tongue == "UM":
        julia = shutil.which("julia")
        if julia:
            return ([julia, "-e"], "inline")
    if tongue == "DR":
        runghc = shutil.which("runghc") or shutil.which("runhaskell")
        if runghc:
            return ([runghc, "-e"], "inline")
    if tongue == "GO":
        go_bin = shutil.which("go")
        if go_bin:
            return ([go_bin, "run"], "file")
    if tongue == "ZI":
        zig_bin = shutil.which("zig")
        if zig_bin:
            return ([zig_bin, "run"], "file")
    return None


def syntax_check(tongue: str, code: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """Syntax-check a code fragment for a compiled tongue.

    Uses real compilers when available, falls back to structural brace-balance check.
    """
    compiler_map: Dict[str, Tuple[Optional[str], Optional[List[str]], Optional[str]]] = {
        "RU": (shutil.which("rustc"),
               ["rustc", "--edition=2021", "--crate-type=lib", "-"],
               f"fn _check() {{ let _ = {code}; }}"),
        "CA": (shutil.which("gcc"),
               ["gcc", "-fsyntax-only", "-x", "c", "-"],
               f"int _check() {{ return (int)({code}); }}"),
        "GO": (shutil.which("go"), None, None),
        "ZI": (shutil.which("zig"), None, None),
    }
    if tongue not in compiler_map:
        return (True, "not a compiled tongue")
    binary, argv, wrapper = compiler_map[tongue]
    if binary is None or argv is None:
        opens = code.count("(") + code.count("{") + code.count("[")
        closes = code.count(")") + code.count("}") + code.count("]")
        balanced = opens == closes
        return (balanced, "structural-ok" if balanced else f"unbalanced: {opens} opens vs {closes} closes")
    try:
        proc = subprocess.run(argv, input=wrapper, capture_output=True, text=True, timeout=timeout)
        return (proc.returncode == 0, proc.stderr.strip() or "ok")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (False, str(exc))


def _wrap_for_execution(tongue: str, code_fragment: str) -> str:
    """Turn a lexicon fragment into a printable expression."""
    if tongue == "KO":
        return f"print({code_fragment})"
    if tongue == "AV":
        return f"console.log({code_fragment})"
    if tongue == "UM":
        return f"println({code_fragment})"
    if tongue == "DR":
        return f"print $ {code_fragment}"
    if tongue == "GO":
        return (
            'package main\nimport ("fmt"; "math")\n'
            f"var _ = math.MaxInt64\n"
            f"func main() {{ fmt.Println({code_fragment}) }}"
        )
    if tongue == "ZI":
        return (
            'const std = @import("std");\n'
            "pub fn main() !void {\n"
            f'    try std.io.getStdOut().writer().print("{{}}\\n", .{{{code_fragment}}});\n'
            "}"
        )
    return code_fragment


def run_tongue_call(
    op: str,
    tongue: str,
    args: Dict[str, str],
    execute: bool = True,
    timeout: float = 10.0,
) -> SwarmCallResult:
    """Emit code for a single tongue and optionally run it."""
    if tongue not in ALL_TONGUE_NAMES:
        raise ValueError(f"unknown tongue: {tongue}")
    entry = lookup(op)
    if tongue in EXTENDED_TONGUE_NAMES:
        fragment = emit_extended(op, tongue, **args)
    else:
        fragment = emit_code(op, tongue, **args)
    language = ALL_LANG_MAP[tongue]
    result = SwarmCallResult(
        op=op,
        tongue=tongue,
        language=language,
        code=fragment,
        ran=False,
        phase=ALL_TONGUE_PHASES[tongue],
        seal=compute_seal(op, tongue, fragment),
    )
    if not execute:
        return result
    runner = _runner_for(tongue)
    if runner is None:
        result.error = f"no local runtime for {tongue}/{language}"
        return result
    argv_prefix, mode = runner
    wrapped = _wrap_for_execution(tongue, fragment)
    tmp_path: Optional[Path] = None
    if mode == "file":
        import tempfile
        suffix = ".go" if tongue == "GO" else ".zig"
        fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix=f"geoseal_{tongue.lower()}_")
        tmp_path = Path(tmp_name)
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(wrapped)
        argv = list(argv_prefix) + [str(tmp_path)]
    else:
        argv = list(argv_prefix) + [wrapped]
    t0 = time.time()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result.ran = True
        result.stdout = proc.stdout.strip()
        result.stderr = proc.stderr.strip()
        result.returncode = proc.returncode
    except subprocess.TimeoutExpired:
        result.error = "timeout"
    except FileNotFoundError as exc:
        result.error = f"runtime not found: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    result.duration_ms = (time.time() - t0) * 1000.0
    # chi note is advisory, not blocking; still attach for governance
    _ = entry.chi
    return result


def swarm_dispatch(
    op: str,
    tongues: List[str],
    args: Dict[str, str],
    execute: bool = True,
    timeout: float = 10.0,
    ledger: Optional[Path] = DEFAULT_LEDGER,
) -> SwarmResult:
    """Dispatch one op to a list of tongue agents. BFT-lite consensus."""
    result = SwarmResult(op=op, args=dict(args), timestamp=time.time())
    for t in tongues:
        call = run_tongue_call(op, t, args, execute=execute, timeout=timeout)
        result.calls.append(call)
    successful = [c for c in result.calls if c.ran and c.returncode == 0]
    if successful:
        outputs = sorted({c.stdout for c in successful if c.stdout})
        if len(outputs) == 1:
            result.quorum_ok = True
            result.consensus_hash = hashlib.sha256(outputs[0].encode("utf-8")).hexdigest()
        elif len(outputs) > 1:
            tally: Dict[str, int] = {}
            for c in successful:
                tally[c.stdout] = tally.get(c.stdout, 0) + 1
            top, count = max(tally.items(), key=lambda kv: kv[1])
            if count * 2 > len(successful):
                result.quorum_ok = True
                result.consensus_hash = hashlib.sha256(top.encode("utf-8")).hexdigest()
    if ledger is not None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result.to_dict()) + "\n")
    return result


def list_ops(band: Optional[str] = None) -> List[Tuple[int, str, str, float]]:
    out = []
    for eid, entry in sorted(LEXICON.items()):
        if band and entry.band != band.upper():
            continue
        out.append((eid, entry.name, entry.band, entry.chi))
    return out


def _parse_kv_args(pairs: List[str]) -> Dict[str, str]:
    args: Dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"arg must be key=value: {p}")
        k, v = p.split("=", 1)
        args[k] = v
    return args


def cmd_ops(args: argparse.Namespace) -> int:
    for eid, name, band, chi in list_ops(band=args.band):
        print(f"  0x{eid:02X}  {name:<14} band={band:<11} chi={chi:.2f}")
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    kv = _parse_kv_args(args.args)
    if args.tongue:
        tongue = args.tongue.upper()
        if tongue not in TONGUE_NAMES:
            print(f"unknown tongue: {tongue}", file=sys.stderr)
            return 2
        code = emit_code(args.op, tongue, **kv)
        seal = compute_seal(args.op, tongue, code)
        print(f"{tongue} ({LANG_MAP[tongue]}): {code}")
        print(f"seal: {seal}")
        return 0
    results = emit_all_tongues(args.op, **kv)
    for t, code in results.items():
        seal = compute_seal(args.op, t, code)
        print(f"{t} ({LANG_MAP[t]:>10}): {code}")
        if args.show_seal:
            print(f"              seal: {seal}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    kv = _parse_kv_args(args.args)
    tongue = (args.tongue or "KO").upper()
    call = run_tongue_call(args.op, tongue, kv, execute=True, timeout=args.timeout)
    print(f"op={call.op} tongue={call.tongue} lang={call.language}")
    print(f"code: {call.code}")
    if call.error:
        print(f"error: {call.error}")
    if call.ran:
        print(f"stdout: {call.stdout}")
        if call.stderr:
            print(f"stderr: {call.stderr}")
        print(f"returncode={call.returncode}  {call.duration_ms:.1f} ms")
    print(f"seal: {call.seal}")
    return 0 if (call.ran and call.returncode == 0) else 1


def cmd_swarm(args: argparse.Namespace) -> int:
    kv = _parse_kv_args(args.args)
    tongues = (
        [t.strip().upper() for t in args.tongues.split(",") if t.strip()]
        if args.tongues
        else list(TONGUE_NAMES)
    )
    unknown = [t for t in tongues if t not in ALL_TONGUE_NAMES]
    if unknown:
        print(f"unknown tongues: {unknown}", file=sys.stderr)
        return 2
    ledger = None if args.no_ledger else Path(args.ledger)
    result = swarm_dispatch(
        args.op,
        tongues,
        kv,
        execute=not args.no_run,
        timeout=args.timeout,
        ledger=ledger,
    )
    print(f"swarm op={result.op} tongues={','.join(tongues)} n={len(result.calls)}")
    for call in result.calls:
        status = "ok" if (call.ran and call.returncode == 0) else (call.error or "skip")
        out = call.stdout or ""
        print(f"  {call.tongue} ({call.language:>10}): {status:<20} {out}")
    print(f"quorum_ok={result.quorum_ok}  consensus={result.consensus_hash[:12] or '-'}")
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.quorum_ok else 1


def cmd_seal(args: argparse.Namespace) -> int:
    tongue = (args.tongue or "KO").upper()
    seal = compute_seal(args.op or "seal", tongue, args.payload)
    print(f"tongue={tongue} phase={ALL_TONGUE_PHASES.get(tongue, 0.0):.6f}")
    print(f"seal={seal}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    tongue = (args.tongue or "KO").upper()
    ok = verify_seal(args.seal, args.op or "seal", tongue, args.payload)
    print("OK" if ok else "MISMATCH")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="geoseal", description="GeoSeal swarm CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ops = sub.add_parser("ops", help="List tokenizer ops")
    p_ops.add_argument("--band", default=None, help="ARITHMETIC|LOGIC|COMPARISON|AGGREGATION")
    p_ops.set_defaults(func=cmd_ops)

    p_emit = sub.add_parser("emit", help="Emit code for an op")
    p_emit.add_argument("op")
    p_emit.add_argument("--tongue", default=None)
    p_emit.add_argument("--show-seal", action="store_true", dest="show_seal")
    p_emit.add_argument("args", nargs="*", help="kwargs as key=value pairs")
    p_emit.set_defaults(func=cmd_emit)

    p_run = sub.add_parser("run", help="Run an op in one tongue subprocess")
    p_run.add_argument("op")
    p_run.add_argument("--tongue", default="KO")
    p_run.add_argument("--timeout", type=float, default=10.0)
    p_run.add_argument("args", nargs="*")
    p_run.set_defaults(func=cmd_run)

    p_swarm = sub.add_parser("swarm", help="Dispatch an op to a swarm of tongue bots")
    p_swarm.add_argument("op")
    p_swarm.add_argument("--tongues", default=None, help="comma-separated (default: all 6)")
    p_swarm.add_argument("--timeout", type=float, default=10.0)
    p_swarm.add_argument("--no-run", action="store_true", help="Emit only, don't execute")
    p_swarm.add_argument("--no-ledger", action="store_true", help="Skip writing ledger")
    p_swarm.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_swarm.add_argument("--json", action="store_true")
    p_swarm.add_argument("args", nargs="*")
    p_swarm.set_defaults(func=cmd_swarm)

    p_seal = sub.add_parser("seal", help="Apply a GeoSeal signature to a payload")
    p_seal.add_argument("payload")
    p_seal.add_argument("--op", default=None)
    p_seal.add_argument("--tongue", default="KO")
    p_seal.set_defaults(func=cmd_seal)

    p_verify = sub.add_parser("verify", help="Verify a GeoSeal signature")
    p_verify.add_argument("seal")
    p_verify.add_argument("payload")
    p_verify.add_argument("--op", default=None)
    p_verify.add_argument("--tongue", default="KO")
    p_verify.set_defaults(func=cmd_verify)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
