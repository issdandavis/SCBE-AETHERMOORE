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
    agent <task>        route task via atomic tokenizer -> Polly -> GeoSeal stamp
    cursor <task>       delegate a bounded repo task to Cursor Agent

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
import os
import re
import shlex
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
    EXTENDED_TONGUE_NAMES,
    LANG_MAP,
    LEXICON,
    TONGUE_NAMES,
    emit_all_tongues,
    emit_code,
    emit_extended,
    feature_vector,
    lookup,
    trit_vector,
)
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER
from src.contracts.operation_panel import resolve_source_to_operation_panel
from src.contracts.runtime_contract import inspect_runtime_packet
from src.contracts.system_cards import build_system_deck, play_system_card

PHI = (1 + 5**0.5) / 2

# phi-weight per tongue — same as Sacred Tongue weighting system
TONGUE_PHI_WEIGHTS: Dict[str, float] = {
    "KO": 1.00,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090,
    "GO": 4.236,  # GO inherits CA weight (CA parent)
    "ZI": 2.618,  # ZI inherits RU weight (RU parent)
}

# phi-wall tier thresholds (phi^0.5, phi^1.0, phi^1.5)
_TIER_ALLOW = PHI**0.5  # 1.272
_TIER_QUARANTINE = PHI**1.0  # 1.618
_TIER_ESCALATE = PHI**1.5  # 2.058


def phi_wall_cost(chi: float, tongue: str, R: float = 5.0) -> float:
    """H(d,R) = phi^d / (1 + e^-R) where d = chi * tongue_phi_weight (normalised).

    chi is the lexicon entry risk score [0,1].
    tongue phi-weight scales d so Draumric ops cost phi^5× more than Kor'aelin.
    d is normalised to [0,1.5] range by dividing by max tongue weight (11.09).
    """
    w = TONGUE_PHI_WEIGHTS.get(tongue, 1.0)
    d = (chi * w) / 11.090  # normalise to [0, 1.5]
    return (PHI**d) / (1.0 + math.exp(-R))


def phi_wall_tier(cost: float) -> str:
    """Map phi-wall cost to governance tier using phi-spiral thresholds."""
    if cost < _TIER_ALLOW:
        return "ALLOW"
    elif cost < _TIER_QUARANTINE:
        return "QUARANTINE"
    elif cost < _TIER_ESCALATE:
        return "ESCALATE"
    return "DENY"


def phi_trust_score(cost: float) -> float:
    """Continuous trust score [0,1] — inverse of normalised phi cost."""
    return min(1.0, max(0.0, 1.0 - (cost - 1.0) / (_TIER_ESCALATE - 1.0)))


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
TONGUE_CODE_MAP = {t.upper(): t.lower() for t in TONGUE_NAMES}


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
    # phi-wall governance fields
    phi_cost: float = 0.0
    tier: str = "ALLOW"
    trust_score: float = 1.0

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


def compute_seal(
    op: str,
    tongue: str,
    code: str,
    payload: str = "",
    phi_cost: float = 0.0,
    tier: str = "ALLOW",
) -> str:
    """GeoSeal signature: tongue phase + phi-wall cost + sha256.

    The seal is geometry-bound: same op in a higher-cost tongue (e.g. DR vs KO)
    produces a different seal because phi_cost and tier are included in the hash.
    This makes the seal deterministic AND encoding-aware.
    """
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
    h.update(b"|")
    h.update(f"{phi_cost:.8f}".encode("utf-8"))
    h.update(b"|")
    h.update(tier.encode("utf-8"))
    return h.hexdigest()


def verify_seal(
    expected: str,
    op: str,
    tongue: str,
    code: str,
    payload: str = "",
    phi_cost: float = 0.0,
    tier: str = "ALLOW",
) -> bool:
    return compute_seal(op, tongue, code, payload, phi_cost, tier) == expected


def _write_stdout_safe(text: str) -> None:
    """Write text without crashing on Windows console codepage limitations."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))
        sys.stdout.buffer.write(b"\n")
    else:  # pragma: no cover - defensive
        sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        sys.stdout.write("\n")


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


def _cursor_agent_path() -> Optional[Path]:
    """Locate the installed Cursor Agent wrapper."""
    env_path = os.environ.get("CURSOR_AGENT_CMD")
    candidates = [
        Path(env_path) if env_path else None,
        Path.home() / "AppData" / "Local" / "cursor-agent" / "agent.cmd",
        Path.home() / "AppData" / "Local" / "Programs" / "cursor-agent" / "agent.cmd",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def syntax_check(tongue: str, code: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """Syntax-check a code fragment for a compiled tongue.

    Uses real compilers when available, falls back to structural brace-balance check.
    """
    compiler_map: Dict[str, Tuple[Optional[str], Optional[List[str]], Optional[str]]] = {
        "RU": (
            shutil.which("rustc"),
            ["rustc", "--edition=2021", "--crate-type=lib", "-"],
            f"fn _check() {{ let _ = {code}; }}",
        ),
        "CA": (
            shutil.which("gcc"),
            ["gcc", "-fsyntax-only", "-x", "c", "-"],
            f"int _check() {{ return (int)({code}); }}",
        ),
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
    # phi-wall governance — cost scales with tongue weight × chi risk score
    cost = phi_wall_cost(entry.chi, tongue)
    tier = phi_wall_tier(cost)
    trust = phi_trust_score(cost)
    result = SwarmCallResult(
        op=op,
        tongue=tongue,
        language=language,
        code=fragment,
        ran=False,
        phase=ALL_TONGUE_PHASES[tongue],
        seal=compute_seal(op, tongue, fragment, phi_cost=cost, tier=tier),
        phi_cost=cost,
        tier=tier,
        trust_score=trust,
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


def _read_payload_arg_or_stdin(value: Optional[str]) -> str:
    if value is not None:
        return value
    return sys.stdin.read()


def _parse_token_text(text: str) -> List[str]:
    return [part.strip() for part in text.replace(",", " ").split() if part.strip()]


def _normalize_transport_tongue(tongue: str) -> str:
    code = tongue.upper()
    if code not in TONGUE_CODE_MAP:
        raise KeyError(f"unknown tongue: {tongue}")
    return TONGUE_CODE_MAP[code]


def tongue_token_digest(tongue: str, text: str) -> Dict[str, object]:
    """Return a Sacred-Tongue boundary digest for `text`.

    Encodes via the byte-level Sacred Tongue tokenizer and summarizes to a
    fixed-shape record: tongue code, mapped language name, token count, and
    a SHA-256 over the concatenated token stream. This keeps ledgers compact
    while still letting downstream training reconstruct cross-tongue parity
    proofs without storing the full encoded stream.
    """
    code = (tongue or "").upper()
    if not code:
        return {"tongue": None, "lang": None, "n_tokens": 0, "sha256": None, "skipped": "empty_tongue"}
    if code not in ALL_TONGUE_NAMES and code not in TONGUE_CODE_MAP:
        return {"tongue": code, "lang": None, "n_tokens": 0, "sha256": None, "skipped": "unknown_tongue"}
    transport = TONGUE_CODE_MAP.get(code, code.lower())
    payload = (text or "").encode("utf-8", errors="replace")
    try:
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, payload)
    except Exception as exc:  # pragma: no cover - defensive, tokenizer is total
        return {
            "tongue": code,
            "lang": ALL_LANG_MAP.get(code),
            "n_tokens": 0,
            "sha256": None,
            "skipped": f"encode_error:{exc.__class__.__name__}",
        }
    joined = " ".join(tokens).encode("utf-8")
    digest = hashlib.sha256(joined).hexdigest()
    return {
        "tongue": code,
        "lang": ALL_LANG_MAP.get(code),
        "n_tokens": len(tokens),
        "sha256": digest,
    }


def cmd_encode_cmd(args: argparse.Namespace) -> int:
    payload = _read_payload_arg_or_stdin(args.payload)
    tongue = _normalize_transport_tongue(args.tongue)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, payload.encode("utf-8"))
    print(" ".join(tokens))
    return 0


def cmd_decode_cmd(args: argparse.Namespace) -> int:
    token_text = _read_payload_arg_or_stdin(args.tokens)
    tongue = _normalize_transport_tongue(args.tongue)
    tokens = _parse_token_text(token_text)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, tokens)
    sys.stdout.write(decoded.decode("utf-8", errors="replace"))
    return 0


def cmd_xlate_cmd(args: argparse.Namespace) -> int:
    token_text = _read_payload_arg_or_stdin(args.tokens)
    src = _normalize_transport_tongue(args.src)
    dst = _normalize_transport_tongue(args.dst)
    tokens = _parse_token_text(token_text)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(src, tokens)
    out_tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(dst, decoded)
    print(" ".join(out_tokens))
    return 0


def cmd_atomic(args: argparse.Namespace) -> int:
    entry = lookup(args.op)
    trits = trit_vector(entry.name).tolist()
    features = feature_vector(entry.name).tolist()
    record = {
        "op_id": entry.op_id,
        "name": entry.name,
        "band": entry.band,
        "chi": entry.chi,
        "valence": entry.valence,
        "trit": trits,
        "feat": features,
        "languages": {tongue: ALL_LANG_MAP[tongue] for tongue in entry.code},
        "code": entry.code if args.show_code else None,
        "note": entry.note,
    }
    print(json.dumps(record, indent=2))
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
    tongues = [t.strip().upper() for t in args.tongues.split(",") if t.strip()] if args.tongues else list(TONGUE_NAMES)
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

    # Per-call sacred-tongue boundary digests for downstream parity training.
    # Written as a single 'swarm_tokens' summary record so we don't disturb the
    # per-call records emitted inside swarm_dispatch.
    if ledger is not None and result.calls:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        swarm_in_payload = json.dumps({"op": result.op, "args": kv}, sort_keys=True)
        per_call_tokens = []
        for call in result.calls:
            call_tongue = getattr(call, "tongue", None)
            call_code = getattr(call, "code", "") or ""
            call_stdout = getattr(call, "stdout", "") or ""
            per_call_tokens.append(
                {
                    "tongue": call_tongue,
                    "tongue_in": tongue_token_digest(call_tongue, swarm_in_payload),
                    "tongue_out_code": tongue_token_digest(call_tongue, call_code),
                    "tongue_out_stdout": tongue_token_digest(call_tongue, call_stdout),
                }
            )
        record = {
            "type": "swarm_tokens",
            "op": result.op,
            "tongues": tongues,
            "consensus_hash": result.consensus_hash,
            "quorum_ok": result.quorum_ok,
            "calls": per_call_tokens,
            "timestamp": time.time(),
        }
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.quorum_ok else 1


def cmd_seal(args: argparse.Namespace) -> int:
    tongue = (args.tongue or "KO").upper()
    phi_cost = getattr(args, "phi_cost", 0.0)
    tier = getattr(args, "tier", "ALLOW")
    seal = compute_seal(args.op or "seal", tongue, args.payload, phi_cost=phi_cost, tier=tier)
    print(f"tongue={tongue} phase={ALL_TONGUE_PHASES.get(tongue, 0.0):.6f} phi_cost={phi_cost:.4f} tier={tier}")
    print(f"seal={seal}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    tongue = (args.tongue or "KO").upper()
    phi_cost = getattr(args, "phi_cost", 0.0)
    tier = getattr(args, "tier", "ALLOW")
    ok = verify_seal(args.seal, args.op or "seal", tongue, args.payload, phi_cost=phi_cost, tier=tier)
    print("OK" if ok else "MISMATCH")
    return 0 if ok else 1


def _build_portal_box_payload(
    *,
    language: str,
    content: str,
    source_name: str = "<memory>",
    include_extended: bool = False,
    deck_size: int = 10,
    branch_width: int = 1,
) -> Dict[str, Any]:
    resolution = resolve_source_to_operation_panel(
        content,
        language=language,
        source_name=source_name,
        include_extended=include_extended,
    )
    deck = build_system_deck(
        resolution,
        source_text=content,
        source_name=source_name,
        include_extended=include_extended,
        deck_size=deck_size,
    )
    route_packet = dict(resolution["runtime_packet"])
    return {
        "version": "geoseal-polly-portal-box-v1",
        "branch_width": branch_width,
        "shell_contract": {
            "schema_version": "geoseal-shell-contract-v1",
            "route_packet": route_packet,
            "operator_signature": resolution["operator_signature"],
        },
        "deck": deck,
    }


def _build_stream_wheel_payload(portal_payload: Dict[str, Any]) -> Dict[str, Any]:
    cards = portal_payload.get("deck", {}).get("cards", [])
    return {
        "version": "geoseal-polly-stream-wheel-v1",
        "portal_box_version": portal_payload.get("version"),
        "wheel": [
            {
                "index": idx,
                "card_id": card.get("card_id"),
                "kind": card.get("kind"),
                "route_tongue": card.get("route_tongue"),
            }
            for idx, card in enumerate(cards)
        ],
        "shell_contract": portal_payload.get("shell_contract", {}),
    }


def _build_execution_shell_payload(
    *,
    language: str,
    content: str,
    source_name: str = "<memory>",
    include_extended: bool = False,
    deck_size: int = 10,
    branch_width: int = 1,
) -> Dict[str, Any]:
    portal_payload = _build_portal_box_payload(
        language=language,
        content=content,
        source_name=source_name,
        include_extended=include_extended,
        deck_size=deck_size,
        branch_width=branch_width,
    )
    return {
        "version": "geoseal-execution-shell-v1",
        "portal_box": portal_payload,
        "route_packet": portal_payload["shell_contract"]["route_packet"],
    }


def _execute_execution_shell_payload(
    shell_payload: Dict[str, Any],
    *,
    timeout: float = 10.0,
    tongue: Optional[str] = None,
) -> Dict[str, Any]:
    route_packet = shell_payload.get("route_packet") or {}
    command_key = str(route_packet.get("command_key") or "identity")
    route_tongue = (tongue or route_packet.get("route_tongue") or "KO").upper()
    args = {"a": "4", "b": "6"}
    try:
        lookup(command_key)
    except Exception:
        return {
            "ok": False,
            "route_packet": route_packet,
            "error": f"unsupported command_key: {command_key}",
        }
    call = run_tongue_call(command_key, route_tongue, args, execute=True, timeout=timeout)
    return {
        "ok": bool(call.ran and call.returncode == 0),
        "route_packet": route_packet,
        "execution": call.to_dict(),
    }


def cmd_portal_box(args: argparse.Namespace) -> int:
    payload = _build_portal_box_payload(
        language=args.language,
        content=args.content,
        source_name=args.source_name,
        include_extended=args.include_extended,
        deck_size=args.deck_size,
        branch_width=args.branch_width,
    )
    print(json.dumps(payload, indent=2 if not args.json else None))
    return 0


def cmd_stream_wheel(args: argparse.Namespace) -> int:
    portal = _build_portal_box_payload(
        language=args.language,
        content=args.content,
        source_name=args.source_name,
        include_extended=args.include_extended,
        deck_size=args.deck_size,
        branch_width=args.branch_width,
    )
    print(json.dumps(_build_stream_wheel_payload(portal), indent=2 if not args.json else None))
    return 0


def cmd_inspect_runtime(args: argparse.Namespace) -> int:
    payload = inspect_runtime_packet(
        {
            "language": args.language,
            "content": args.content,
            "source_name": args.source_name,
        }
    )
    print(json.dumps(payload, indent=2 if not args.json else None))
    return 0


def cmd_run_route(args: argparse.Namespace) -> int:
    shell_payload = _build_execution_shell_payload(
        language=args.language,
        content=args.content,
        source_name=args.source_name,
        include_extended=args.include_extended,
        deck_size=args.deck_size,
        branch_width=args.branch_width,
    )
    result = _execute_execution_shell_payload(shell_payload, timeout=args.timeout, tongue=args.tongue)
    print(json.dumps(result, indent=2 if not args.json else None))
    return 0 if result.get("ok") else 1


def cmd_shell(args: argparse.Namespace) -> int:
    """Run one nested GeoSeal command string through the same parser."""
    nested = shlex.split(args.command, posix=False)
    if nested and nested[0] in {"geoseal", "python", "py"}:
        nested = nested[1:]
    return main(nested)


def cmd_agent(args: argparse.Namespace) -> int:
    """Route a natural-language coding task through the coding spine.

    Pipeline:
        task -> atomic trit router -> tongue/language selection
             -> Polly (or Claude fallback) -> code generation
             -> GeoSeal stamp -> SFT log
    """
    # Lazy imports — keeps the CLI fast when agent subcommand is not used
    try:
        from src.coding_spine.router import route_task
        from src.coding_spine.polly_client import generate
        from src.coding_spine.shared_ir import infer_semantic_ir
    except ImportError as exc:
        print(f"coding spine not available: {exc}", file=sys.stderr)
        return 2

    task = args.task
    force_tongue = (args.tongue or "").upper() or None
    force_provider = args.provider or None
    max_tokens = args.max_tokens
    budget_tokens = getattr(args, "budget_tokens", None)
    max_tier = getattr(args, "max_tier", None)
    small_first = bool(getattr(args, "small_first", False))
    forbid_provider = list(getattr(args, "forbid_provider", []) or [])
    escalate_on_syntax_fail = bool(getattr(args, "escalate_on_syntax_fail", False))
    verbose = args.verbose

    # 1. Route the task
    route = route_task(task, force_tongue=force_tongue)
    semantic_ir = infer_semantic_ir(task, force_tongue=force_tongue)
    if verbose:
        kw = f" (keyword: {route.override_keyword!r})" if route.override_keyword else ""
        print(f"[route] {route.full_name} ({route.tongue}) -> {route.language} | conf={route.confidence:.2f}{kw}")
        print(f"[route] trits: {route.trit_scores}")
        print(f"[ir] {semantic_ir.signature}")

    # 2. Check phi-wall governance on the task itself
    # Use a nominal chi=0.2 for free-form agent tasks (low-risk generation)
    chi = 0.2
    phi_cost = phi_wall_cost(chi, route.tongue)
    tier = phi_wall_tier(phi_cost)
    trust = phi_trust_score(phi_cost)

    if tier == "DENY":
        print(f"[governance] DENY — phi_cost={phi_cost:.4f} exceeds threshold", file=sys.stderr)
        return 3

    # --max-tier gate: refuse anything more severe than the cap.
    _TIER_RANK = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}
    if max_tier is not None and _TIER_RANK[tier] > _TIER_RANK[max_tier]:
        print(
            f"[governance] tier={tier} exceeds --max-tier={max_tier} (phi_cost={phi_cost:.4f})",
            file=sys.stderr,
        )
        return 3

    if verbose:
        print(f"[governance] tier={tier} phi_cost={phi_cost:.4f} trust={trust:.3f}")

    # 3. Generate code (with optional syntax-fail escalation across tiers)
    forbidden = list(forbid_provider)
    result = generate(
        task,
        language=route.language,
        tongue=route.tongue,
        tongue_name=route.full_name,
        max_tokens=max_tokens,
        force_provider=force_provider,
        forbidden_providers=forbidden,
        small_first=small_first,
        governance_tier=tier,
        budget_tokens=budget_tokens,
    )

    syntax_history: list[dict] = []
    if escalate_on_syntax_fail and not result.error and result.code:
        ok, msg = syntax_check(route.tongue, result.code)
        syntax_history.append({"provider": result.provider, "ok": ok, "msg": msg})
        if verbose:
            print(f"[syntax] provider={result.provider} ok={ok} msg={msg}")
        # Escalate up the provider chain while syntax fails. Each retry forbids
        # the prior provider so generate() falls through to the next tier.
        while not ok and result.provider != "none":
            forbidden.append(result.provider)
            if verbose:
                print(f"[escalate] syntax_check failed on {result.provider}; retrying with forbid={forbidden}")
            result = generate(
                task,
                language=route.language,
                tongue=route.tongue,
                tongue_name=route.full_name,
                max_tokens=max_tokens,
                force_provider=None,
                forbidden_providers=forbidden,
                small_first=small_first,
                governance_tier=tier,
                budget_tokens=budget_tokens,
            )
            if result.error or not result.code:
                break
            ok, msg = syntax_check(route.tongue, result.code)
            syntax_history.append({"provider": result.provider, "ok": ok, "msg": msg})
            if verbose:
                print(f"[syntax] provider={result.provider} ok={ok} msg={msg}")

    if result.error:
        print(f"[error] {result.error}", file=sys.stderr)
        return 1

    if verbose:
        print(f"[generate] provider={result.provider} model={result.model}")
        print(f"[generate] prompt_tokens={result.prompt_tokens} completion_tokens={result.completion_tokens}")
        if result.attempted_providers:
            chain = " -> ".join(
                f"{a['provider']}({'ok' if a['success'] else (a.get('skipped_reason') or 'err')})"
                for a in result.attempted_providers
            )
            print(f"[chain] {chain}")

    # 4. GeoSeal stamp
    seal = compute_seal("agent", route.tongue, result.code, task, phi_cost, tier)

    # 5. Print output
    print(f"# tongue={route.full_name} ({route.tongue}) lang={route.language} tier={tier} seal={seal[:16]}...")
    _write_stdout_safe(result.code)

    # 6. SFT log — write as governance record to .scbe/geoseal_calls.jsonl
    ledger = Path(args.ledger) if not args.no_ledger else None
    if ledger is not None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "type": "agent",
            "task": task,
            "tongue": route.tongue,
            "tongue_name": route.full_name,
            "language": route.language,
            "confidence": route.confidence,
            "override_keyword": route.override_keyword,
            "trit_scores": route.trit_scores,
            "semantic_ir": semantic_ir.to_dict(),
            "phi_cost": phi_cost,
            "tier": tier,
            "trust_score": trust,
            "provider": result.provider,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "code": result.code,
            "seal": seal,
            "tongue_in": tongue_token_digest(route.tongue, task),
            "tongue_out": tongue_token_digest(route.tongue, result.code or ""),
            "routing": {
                "max_tier": max_tier,
                "small_first": small_first,
                "forbid_provider": list(forbid_provider),
                "budget_tokens": budget_tokens,
                "attempted_providers": result.attempted_providers,
                "syntax_history": syntax_history,
            },
            "timestamp": time.time(),
            # SFT training format alongside raw record
            "sft": {
                "messages": [
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": result.code},
                ]
            },
        }
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        if verbose:
            print(f"[ledger] written to {ledger}")

    return 0


def cmd_arc(args: argparse.Namespace) -> int:
    """Load an ARC task, synthesize a program, and optionally export ONNX.

    Pipeline:
        JSON task file -> ARCTask -> synthesize_program -> apply to test inputs
        -> GeoSeal stamp -> optionally export ONNX -> log to ledger
    """
    try:
        # structural_encode uses bare `from crypto.*` — add src/ so it resolves
        _src_path = str(Path(__file__).resolve().parent)
        if _src_path not in sys.path:
            sys.path.insert(0, _src_path)
        from src.neurogolf.arc_io import load_arc_task
        from src.neurogolf.solver import synthesize_program, execute_program
    except ImportError as exc:
        print(f"neurogolf not available: {exc}", file=sys.stderr)
        return 2

    task_path = Path(args.task_file)
    if not task_path.exists():
        print(f"task file not found: {task_path}", file=sys.stderr)
        return 1

    task = load_arc_task(task_path)
    verbose = args.verbose

    if verbose:
        print(f"[arc] task_id={task.task_id}  train={len(task.train)}  test_inputs={len(task.test_inputs)}")

    # Synthesize program
    solution = synthesize_program(task)

    # Score on training examples
    correct = 0
    total = len(task.train)
    for ex in task.train:
        pred = execute_program(ex.input, solution.program)
        if pred.shape == ex.output.shape and (pred == ex.output).all():
            correct += 1

    train_acc = correct / total if total > 0 else 0.0

    # Apply to test inputs
    test_outputs = [execute_program(inp, solution.program) for inp in task.test_inputs]

    # GeoSeal stamp — use UM tongue (Julia/math) for ARC since it is symbolic reasoning
    tongue = "UM"
    chi = 0.15  # ARC synthesis is structured, low-risk
    phi_cost = phi_wall_cost(chi, tongue)
    tier = phi_wall_tier(phi_cost)
    seal_payload = f"{task.task_id}:{solution.family}"
    seal = compute_seal("arc", tongue, solution.family, seal_payload, phi_cost, tier)

    # Print summary
    print(f"task_id={task.task_id}")
    print(f"family={solution.family}")
    print(f"train_acc={train_acc:.2f} ({correct}/{total})")
    print(f"tier={tier} phi_cost={phi_cost:.4f}")
    print(f"seal={seal[:16]}...")
    print(f"steps={len(solution.program.steps)}")

    if args.json:
        record = {
            "task_id": task.task_id,
            "family": solution.family,
            "train_acc": train_acc,
            "n_steps": len(solution.program.steps),
            "steps": [{"op": s.op, "args": s.args} for s in solution.program.steps],
            "test_outputs": [o.tolist() for o in test_outputs],
            "phi_cost": phi_cost,
            "tier": tier,
            "seal": seal,
        }
        print(json.dumps(record, indent=2))
    elif verbose:
        print(f"\nprogram steps:")
        for i, step in enumerate(solution.program.steps):
            print(f"  {i}: {step.op}  {step.args}")
        print(f"\ntest outputs ({len(test_outputs)}):")
        for i, out in enumerate(test_outputs):
            print(f"  [{i}] shape={out.shape}")
            for row in out:
                print(f"    {[int(v) for v in row]}")

    # ONNX export
    if args.onnx:
        try:
            from src.neurogolf.onnx_emit import export_program_onnx

            onnx_path = Path(args.onnx_out or f"{task.task_id}.onnx")
            export_program_onnx(solution.program, onnx_path)
            print(f"onnx={onnx_path}")
        except Exception as exc:
            print(f"[warn] onnx export failed: {exc}", file=sys.stderr)

    # Write ledger
    ledger = Path(args.ledger) if not args.no_ledger else None
    if ledger is not None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        # Boundary digests: input is the task identity + family seed; output is the
        # serialized synthesized program (deterministic, semantic-preserving).
        arc_in_payload = json.dumps({"task_id": task.task_id, "n_train": total}, sort_keys=True)
        arc_out_payload = json.dumps(
            {
                "family": solution.family,
                "steps": [{"op": s.op, "args": s.args} for s in solution.program.steps],
            },
            sort_keys=True,
        )
        log = {
            "type": "arc",
            "task_id": task.task_id,
            "task_file": str(task_path),
            "family": solution.family,
            "train_acc": train_acc,
            "n_steps": len(solution.program.steps),
            "phi_cost": phi_cost,
            "tier": tier,
            "seal": seal,
            "tongue_in": tongue_token_digest(tongue, arc_in_payload),
            "tongue_out": tongue_token_digest(tongue, arc_out_payload),
            "timestamp": time.time(),
        }
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log) + "\n")
        if verbose:
            print(f"[ledger] written to {ledger}")

    if solution.family == "no_program":
        return 2  # synthesizer could not match — distinct from error (1) and solved (0)
    return 0 if train_acc >= 1.0 else 1


def cmd_cursor(args: argparse.Namespace) -> int:
    """Run Cursor Agent as a bounded repo worker from the GeoSeal shell."""
    cursor_agent = _cursor_agent_path()
    if cursor_agent is None:
        print("cursor agent not found; install Cursor Agent or set CURSOR_AGENT_CMD", file=sys.stderr)
        return 2

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"workspace not found: {workspace}", file=sys.stderr)
        return 1

    argv: List[str] = [
        str(cursor_agent),
        "-p",
        "--trust",
        "--workspace",
        str(workspace),
    ]

    if args.model:
        argv.extend(["--model", args.model])
    if args.mode:
        argv.extend(["--mode", args.mode])
    if args.force:
        argv.append("--force")
    if args.output_format:
        argv.extend(["--output-format", args.output_format])
        if args.output_format == "stream-json" and args.stream_partial_output:
            argv.append("--stream-partial-output")
    if args.continue_session:
        argv.append("--continue")

    argv.append(args.task)

    started = time.time()
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(workspace),
    )
    duration_ms = (time.time() - started) * 1000.0

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if stdout:
        _write_stdout_safe(stdout.rstrip())
    if stderr:
        print(stderr.rstrip(), file=sys.stderr)

    ledger = Path(args.ledger) if not args.no_ledger else None
    if ledger is not None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        # Cursor is a freeform repo worker — no routed tongue. Use DR (Draumric /
        # Markdown) as the transport tongue for boundary digests; that's the
        # narrative tongue and the safest default for natural-language tasks.
        cursor_tongue = "DR"
        record = {
            "type": "cursor",
            "task": args.task,
            "workspace": str(workspace),
            "model": args.model,
            "mode": args.mode,
            "forced": bool(args.force),
            "output_format": args.output_format,
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "stdout": stdout,
            "stderr": stderr,
            "tongue_in": tongue_token_digest(cursor_tongue, args.task),
            "tongue_out": tongue_token_digest(cursor_tongue, stdout),
            "timestamp": time.time(),
        }
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        if args.verbose:
            print(f"[ledger] written to {ledger}")

    return proc.returncode


# ---------------------------------------------------------------------------
# Workflow runner — declarative `.geoseal.yaml` chains for small-LLM pipelines
# ---------------------------------------------------------------------------

WORKFLOW_OP_KINDS = {"agent", "seal"}
WORKFLOW_VALID_TIERS = {"ALLOW", "QUARANTINE", "ESCALATE"}
WORKFLOW_VALID_PROVIDERS = {"local", "ollama", "hf", "claude"}
_WORKFLOW_REF_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_.\-]*)\}")


@dataclass
class WorkflowStepResult:
    step_id: str
    op: str
    tongue: str
    tier: str
    seal: str
    code: str = ""
    error: Optional[str] = None
    provider: Optional[str] = None
    phi_cost: float = 0.0
    duration_ms: float = 0.0
    tongue_in: Optional[Dict[str, object]] = None
    tongue_out: Optional[Dict[str, object]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_workflow_spec(path: Path) -> Dict[str, Any]:
    """Load a workflow spec from a `.geoseal.yaml`/`.yml`/`.json` file."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment guard
            raise SystemExit(f"PyYAML required for {suffix} workflows: {exc}")
        spec = yaml.safe_load(text) or {}
    elif suffix == ".json":
        spec = json.loads(text) if text.strip() else {}
    else:
        raise SystemExit(f"unsupported workflow extension: {suffix}")
    if not isinstance(spec, dict):
        raise SystemExit(f"workflow root must be a mapping, got {type(spec).__name__}")
    return spec


def validate_workflow_spec(spec: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: List[str] = []
    if not isinstance(spec, dict):
        return ["workflow root must be a mapping"]
    if not spec.get("name"):
        errors.append("missing required field: name")
    default_tongue = spec.get("default_tongue")
    if default_tongue is not None and not isinstance(default_tongue, str):
        errors.append("default_tongue must be a string if present")
    default_max_tier = spec.get("default_max_tier")
    if default_max_tier is not None and default_max_tier not in WORKFLOW_VALID_TIERS:
        errors.append(f"default_max_tier invalid: {default_max_tier!r}")
    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty list")
        return errors
    seen_ids: set = set()
    for idx, step in enumerate(steps):
        prefix = f"steps[{idx}]"
        if not isinstance(step, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue
        sid = step.get("id")
        if not sid or not isinstance(sid, str):
            errors.append(f"{prefix}: missing/invalid id")
        elif sid in seen_ids:
            errors.append(f"{prefix}: duplicate id {sid!r}")
        else:
            seen_ids.add(sid)
        op = step.get("op")
        if op not in WORKFLOW_OP_KINDS:
            errors.append(f"{prefix}({sid}): op must be one of {sorted(WORKFLOW_OP_KINDS)}, got {op!r}")
        if "task" not in step:
            errors.append(f"{prefix}({sid}): missing required field 'task'")
        tongue = step.get("tongue")
        if tongue is not None and not isinstance(tongue, str):
            errors.append(f"{prefix}({sid}): tongue must be a string")
        max_tier = step.get("max_tier")
        if max_tier is not None and max_tier not in WORKFLOW_VALID_TIERS:
            errors.append(f"{prefix}({sid}): max_tier invalid {max_tier!r}")
        provider = step.get("provider")
        if provider is not None and provider not in WORKFLOW_VALID_PROVIDERS:
            errors.append(f"{prefix}({sid}): provider invalid {provider!r}")
        forbid = step.get("forbid_provider")
        if forbid is not None:
            if not isinstance(forbid, list):
                errors.append(f"{prefix}({sid}): forbid_provider must be a list")
            else:
                for fp in forbid:
                    if fp not in WORKFLOW_VALID_PROVIDERS:
                        errors.append(f"{prefix}({sid}): forbid_provider entry invalid {fp!r}")
    return errors


def substitute_workflow_refs(
    template: Any,
    input_text: str,
    step_outputs: Dict[str, WorkflowStepResult],
) -> Any:
    """Replace `${input}` / `${steps.<id>.code|seal|tongue|provider}` in templates."""
    if not isinstance(template, str):
        return template

    def _resolve(match: "re.Match[str]") -> str:
        ref = match.group(1)
        if ref == "input":
            return input_text or ""
        parts = ref.split(".")
        if len(parts) == 3 and parts[0] == "steps":
            sid, attr = parts[1], parts[2]
            if sid not in step_outputs:
                raise SystemExit(f"workflow ref ${{{ref}}}: unknown step {sid!r}")
            res = step_outputs[sid]
            if attr == "code":
                return res.code or ""
            if attr == "seal":
                return res.seal or ""
            if attr == "tongue":
                return res.tongue or ""
            if attr == "provider":
                return res.provider or ""
            raise SystemExit(f"workflow ref ${{{ref}}}: unsupported attr {attr!r}")
        raise SystemExit(f"workflow ref ${{{ref}}}: unrecognized reference syntax")

    return _WORKFLOW_REF_PATTERN.sub(_resolve, template)


def _resolve_step_setting(step: Dict[str, Any], spec: Dict[str, Any], key: str, default: Any = None) -> Any:
    if key in step and step[key] is not None:
        return step[key]
    default_key = f"default_{key}"
    if default_key in spec and spec[default_key] is not None:
        return spec[default_key]
    return default


def _run_workflow_step_agent(
    step: Dict[str, Any],
    spec: Dict[str, Any],
    input_text: str,
    step_outputs: Dict[str, WorkflowStepResult],
    verbose: bool = False,
) -> WorkflowStepResult:
    """Execute one workflow `agent` step in-process via the coding spine."""
    try:
        from src.coding_spine.router import route_task
        from src.coding_spine.polly_client import generate
    except ImportError as exc:  # pragma: no cover - import guard
        return WorkflowStepResult(
            step_id=step["id"],
            op="agent",
            tongue="KO",
            tier="DENY",
            seal="",
            error=f"coding spine not available: {exc}",
        )
    sid = step["id"]
    task_template = step.get("task", "")
    task = substitute_workflow_refs(task_template, input_text, step_outputs)
    force_tongue = _resolve_step_setting(step, spec, "tongue")
    if force_tongue:
        force_tongue = str(force_tongue).upper()
    force_provider = _resolve_step_setting(step, spec, "provider")
    max_tokens = int(_resolve_step_setting(step, spec, "max_tokens", default=1024))
    budget_tokens = _resolve_step_setting(step, spec, "budget_tokens")
    if budget_tokens is not None:
        budget_tokens = int(budget_tokens)
    max_tier = _resolve_step_setting(step, spec, "max_tier")
    small_first = bool(_resolve_step_setting(step, spec, "small_first", default=False))
    forbid_provider = list(_resolve_step_setting(step, spec, "forbid_provider", default=[]) or [])
    chi = float(_resolve_step_setting(step, spec, "chi", default=0.2))

    route = route_task(task, force_tongue=force_tongue)
    phi_cost = phi_wall_cost(chi, route.tongue)
    tier = phi_wall_tier(phi_cost)
    if verbose:
        print(f"[workflow:{sid}] route={route.full_name}({route.tongue}) tier={tier} cost={phi_cost:.4f}")
    if tier == "DENY":
        return WorkflowStepResult(
            step_id=sid,
            op="agent",
            tongue=route.tongue,
            tier=tier,
            seal="",
            phi_cost=phi_cost,
            error=f"phi-wall DENY at cost={phi_cost:.4f}",
            tongue_in=tongue_token_digest(route.tongue, task),
        )
    _TIER_RANK = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}
    if max_tier is not None and _TIER_RANK[tier] > _TIER_RANK[max_tier]:
        return WorkflowStepResult(
            step_id=sid,
            op="agent",
            tongue=route.tongue,
            tier=tier,
            seal="",
            phi_cost=phi_cost,
            error=f"tier={tier} exceeds max_tier={max_tier}",
            tongue_in=tongue_token_digest(route.tongue, task),
        )

    started = time.perf_counter()
    result = generate(
        task,
        language=route.language,
        tongue=route.tongue,
        tongue_name=route.full_name,
        max_tokens=max_tokens,
        force_provider=force_provider,
        forbidden_providers=forbid_provider,
        small_first=small_first,
        governance_tier=tier,
        budget_tokens=budget_tokens,
    )
    duration_ms = (time.perf_counter() - started) * 1000.0

    if result.error:
        return WorkflowStepResult(
            step_id=sid,
            op="agent",
            tongue=route.tongue,
            tier=tier,
            seal="",
            phi_cost=phi_cost,
            duration_ms=duration_ms,
            error=result.error,
            provider=result.provider,
            tongue_in=tongue_token_digest(route.tongue, task),
        )

    code = result.code or ""
    seal = compute_seal("workflow_agent", route.tongue, code, task, phi_cost, tier)
    return WorkflowStepResult(
        step_id=sid,
        op="agent",
        tongue=route.tongue,
        tier=tier,
        seal=seal,
        code=code,
        provider=result.provider,
        phi_cost=phi_cost,
        duration_ms=duration_ms,
        tongue_in=tongue_token_digest(route.tongue, task),
        tongue_out=tongue_token_digest(route.tongue, code),
    )


def _run_workflow_step_seal(
    step: Dict[str, Any],
    spec: Dict[str, Any],
    input_text: str,
    step_outputs: Dict[str, WorkflowStepResult],
    verbose: bool = False,
) -> WorkflowStepResult:
    """Execute a `seal` step — stamps an arbitrary payload (often a prior step's code)."""
    sid = step["id"]
    payload = substitute_workflow_refs(step.get("task", ""), input_text, step_outputs)
    tongue = _resolve_step_setting(step, spec, "tongue", default="KO")
    tongue = str(tongue).upper()
    if tongue not in ALL_TONGUE_PHASES:
        return WorkflowStepResult(
            step_id=sid,
            op="seal",
            tongue=tongue,
            tier="DENY",
            seal="",
            error=f"unknown tongue {tongue!r}",
        )
    chi = float(_resolve_step_setting(step, spec, "chi", default=0.1))
    phi_cost = phi_wall_cost(chi, tongue)
    tier = phi_wall_tier(phi_cost)
    seal = compute_seal("workflow_seal", tongue, payload, "", phi_cost, tier)
    if verbose:
        print(f"[workflow:{sid}] seal tongue={tongue} tier={tier} cost={phi_cost:.4f}")
    return WorkflowStepResult(
        step_id=sid,
        op="seal",
        tongue=tongue,
        tier=tier,
        seal=seal,
        code=payload,
        phi_cost=phi_cost,
        tongue_in=tongue_token_digest(tongue, payload),
        tongue_out=tongue_token_digest(tongue, seal),
    )


def run_workflow(
    spec: Dict[str, Any],
    input_text: str = "",
    ledger: Optional[Path] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Execute a validated workflow spec, threading tongue boundaries between steps."""
    errors = validate_workflow_spec(spec)
    if errors:
        raise SystemExit("workflow spec invalid:\n  - " + "\n  - ".join(errors))
    name = spec.get("name", "")
    description = spec.get("description", "")
    workflow_started = time.time()
    step_outputs: Dict[str, WorkflowStepResult] = {}
    step_records: List[Dict[str, Any]] = []
    prev_step_id: Optional[str] = None
    prev_tongue_out_sha: Optional[str] = None
    failed = False
    for idx, step in enumerate(spec["steps"]):
        op = step["op"]
        if op == "agent":
            result = _run_workflow_step_agent(step, spec, input_text, step_outputs, verbose=verbose)
        elif op == "seal":
            result = _run_workflow_step_seal(step, spec, input_text, step_outputs, verbose=verbose)
        else:  # pragma: no cover - already validated
            raise SystemExit(f"workflow op kind not implemented: {op}")
        step_outputs[result.step_id] = result
        record: Dict[str, Any] = {
            "type": "workflow_step",
            "workflow": name,
            "step_id": result.step_id,
            "step_index": idx,
            "op": result.op,
            "tongue": result.tongue,
            "tier": result.tier,
            "seal": result.seal,
            "phi_cost": result.phi_cost,
            "duration_ms": result.duration_ms,
            "provider": result.provider,
            "error": result.error,
            "tongue_in": result.tongue_in,
            "tongue_out": result.tongue_out,
            "prev_step_id": prev_step_id,
            "prev_tongue_out_sha256": prev_tongue_out_sha,
            "timestamp": time.time(),
        }
        step_records.append(record)
        if ledger is not None:
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        if result.error:
            failed = True
            if verbose:
                print(f"[workflow:{result.step_id}] ERROR: {result.error}", file=sys.stderr)
            break
        prev_step_id = result.step_id
        prev_tongue_out_sha = (result.tongue_out or {}).get("sha256") if result.tongue_out else None

    summary = {
        "type": "workflow_run",
        "workflow": name,
        "description": description,
        "input": input_text,
        "n_steps_total": len(spec["steps"]),
        "n_steps_executed": len(step_records),
        "ok": not failed,
        "started_at": workflow_started,
        "finished_at": time.time(),
        "steps": [r["step_id"] for r in step_records],
        "final_seal": step_records[-1]["seal"] if step_records else "",
        "final_tongue_out_sha256": prev_tongue_out_sha,
    }
    if ledger is not None:
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary) + "\n")
    summary["_records"] = step_records
    summary["_outputs"] = {sid: res.to_dict() for sid, res in step_outputs.items()}
    return summary


def _workflow_list_dir(directory: Path) -> List[Path]:
    return sorted(
        list(directory.glob("*.geoseal.yaml"))
        + list(directory.glob("*.geoseal.yml"))
        + list(directory.glob("*.geoseal.json"))
    )


def cmd_workflow(args: argparse.Namespace) -> int:
    mode = args.workflow_cmd
    if mode == "list":
        directory = Path(args.dir).resolve()
        if not directory.exists():
            print(f"workflow dir not found: {directory}", file=sys.stderr)
            return 1
        files = _workflow_list_dir(directory)
        if args.json:
            print(json.dumps([str(p) for p in files]))
        else:
            for p in files:
                print(p)
        return 0

    if mode == "validate":
        path = Path(args.workflow_file)
        if not path.exists():
            print(f"workflow file not found: {path}", file=sys.stderr)
            return 1
        spec = load_workflow_spec(path)
        errors = validate_workflow_spec(spec)
        if args.json:
            print(json.dumps({"file": str(path), "ok": not errors, "errors": errors}))
        else:
            if errors:
                print(f"INVALID: {path}", file=sys.stderr)
                for e in errors:
                    print(f"  - {e}", file=sys.stderr)
            else:
                print(f"OK: {path}")
        return 0 if not errors else 2

    if mode == "run":
        path = Path(args.workflow_file)
        if not path.exists():
            print(f"workflow file not found: {path}", file=sys.stderr)
            return 1
        spec = load_workflow_spec(path)
        input_text = args.input or ""
        if args.input_file:
            input_text = Path(args.input_file).read_text(encoding="utf-8")
        ledger = None if args.no_ledger else Path(args.ledger)
        summary = run_workflow(spec, input_text=input_text, ledger=ledger, verbose=args.verbose)
        if args.json:
            payload = {k: v for k, v in summary.items() if not k.startswith("_")}
            print(json.dumps(payload))
        else:
            status = "ok" if summary["ok"] else "FAILED"
            print(
                f"[workflow] {summary['workflow']} {status} "
                f"steps={summary['n_steps_executed']}/{summary['n_steps_total']} "
                f"final_seal={summary['final_seal'][:16] if summary['final_seal'] else '-'}"
            )
            if not summary["ok"]:
                last = summary["_records"][-1] if summary["_records"] else None
                if last and last.get("error"):
                    print(f"[workflow] last_error: {last['error']}", file=sys.stderr)
        return 0 if summary["ok"] else 1

    print(f"unknown workflow command: {mode}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="geoseal", description="GeoSeal swarm CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ops = sub.add_parser("ops", help="List tokenizer ops")
    p_ops.add_argument("--band", default=None, help="ARITHMETIC|LOGIC|COMPARISON|AGGREGATION")
    p_ops.set_defaults(func=cmd_ops)

    p_encode = sub.add_parser("encode-cmd", help="Encode payload through Sacred Tongues transport")
    p_encode.add_argument("--tongue", required=True, help="KO|AV|RU|CA|UM|DR")
    p_encode.add_argument("payload", nargs="?", default=None, help="Plaintext payload (defaults to stdin)")
    p_encode.set_defaults(func=cmd_encode_cmd)

    p_decode = sub.add_parser("decode-cmd", help="Decode Sacred Tongue tokens back to plaintext")
    p_decode.add_argument("--tongue", required=True, help="KO|AV|RU|CA|UM|DR")
    p_decode.add_argument("tokens", nargs="?", default=None, help="Token stream (defaults to stdin)")
    p_decode.set_defaults(func=cmd_decode_cmd)

    p_xlate = sub.add_parser("xlate-cmd", help="Translate Sacred Tongue token stream across tongues")
    p_xlate.add_argument("--src", required=True, help="Source tongue")
    p_xlate.add_argument("--dst", required=True, help="Destination tongue")
    p_xlate.add_argument("tokens", nargs="?", default=None, help="Token stream (defaults to stdin)")
    p_xlate.set_defaults(func=cmd_xlate_cmd)

    p_atomic = sub.add_parser("atomic", help="Inspect atomic substrate row for an op")
    p_atomic.add_argument("op")
    p_atomic.add_argument("--show-code", action="store_true", help="Include all code templates")
    p_atomic.set_defaults(func=cmd_atomic)

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
    p_seal.add_argument(
        "--phi-cost",
        type=float,
        default=0.0,
        dest="phi_cost",
        help="phi-wall cost to bind into seal (use agent-reported value to re-verify)",
    )
    p_seal.add_argument(
        "--tier", default="ALLOW", help="Governance tier to bind into seal (ALLOW/QUARANTINE/ESCALATE/DENY)"
    )
    p_seal.set_defaults(func=cmd_seal)

    p_verify = sub.add_parser("verify", help="Verify a GeoSeal signature")
    p_verify.add_argument("seal")
    p_verify.add_argument("payload")
    p_verify.add_argument("--op", default=None)
    p_verify.add_argument("--tongue", default="KO")
    p_verify.add_argument(
        "--phi-cost",
        type=float,
        default=0.0,
        dest="phi_cost",
        help="phi-wall cost embedded in the seal (must match what was used when sealing)",
    )
    p_verify.add_argument("--tier", default="ALLOW", help="Governance tier embedded in the seal (must match)")
    p_verify.set_defaults(func=cmd_verify)

    def add_runtime_source_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--language", required=True)
        parser.add_argument("--content", required=True)
        parser.add_argument("--source-name", default="<memory>", dest="source_name")
        parser.add_argument("--include-extended", action="store_true", dest="include_extended")
        parser.add_argument("--deck-size", type=int, default=10, dest="deck_size")
        parser.add_argument("--branch-width", type=int, default=1, dest="branch_width")
        parser.add_argument("--json", action="store_true")

    p_portal = sub.add_parser("portal-box", help="Build a GeoSeal portal-box payload")
    add_runtime_source_args(p_portal)
    p_portal.set_defaults(func=cmd_portal_box)

    p_stream = sub.add_parser("stream-wheel", help="Build a GeoSeal stream-wheel payload")
    add_runtime_source_args(p_stream)
    p_stream.set_defaults(func=cmd_stream_wheel)

    p_inspect = sub.add_parser("inspect", help="Inspect runtime routing packet")
    add_runtime_source_args(p_inspect)
    p_inspect.set_defaults(func=cmd_inspect_runtime)

    p_run_route = sub.add_parser("run-route", help="Build and execute a GeoSeal route")
    add_runtime_source_args(p_run_route)
    p_run_route.add_argument("--timeout", type=float, default=10.0)
    p_run_route.add_argument("--tongue", default=None)
    p_run_route.set_defaults(func=cmd_run_route)

    p_shell = sub.add_parser("shell", help="Execute a nested GeoSeal shell command")
    p_shell.add_argument("--command", required=True)
    p_shell.set_defaults(func=cmd_shell)

    p_agent = sub.add_parser("agent", help="Route a coding task via Polly + GeoSeal")
    p_agent.add_argument("task", help="Natural language coding task")
    p_agent.add_argument("--tongue", default=None, help="Force tongue (KO/AV/RU/CA/UM/DR)")
    p_agent.add_argument(
        "--provider",
        default=None,
        choices=["local", "ollama", "hf", "claude"],
        help="Force inference provider (default: local->ollama->hf->claude)",
    )
    p_agent.add_argument("--max-tokens", type=int, default=1024, dest="max_tokens")
    p_agent.add_argument(
        "--budget-tokens",
        type=int,
        default=None,
        dest="budget_tokens",
        help="Hard cap on completion tokens passed to the provider (small-LLM friendly)",
    )
    p_agent.add_argument(
        "--max-tier",
        default=None,
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
        dest="max_tier",
        help="Refuse routing if the phi-wall tier exceeds this severity",
    )
    p_agent.add_argument(
        "--small-first",
        action="store_true",
        dest="small_first",
        help="Reserve Claude for ESCALATE tier; prefer local/ollama/hf otherwise",
    )
    p_agent.add_argument(
        "--forbid-provider",
        action="append",
        default=[],
        dest="forbid_provider",
        choices=["local", "ollama", "hf", "claude"],
        help="Provider tier to exclude from routing (repeatable)",
    )
    p_agent.add_argument(
        "--escalate-on-syntax-fail",
        action="store_true",
        dest="escalate_on_syntax_fail",
        help="If output fails syntax_check, retry on next provider tier",
    )
    p_agent.add_argument("--no-ledger", action="store_true", help="Skip SFT log")
    p_agent.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_agent.add_argument("--verbose", "-v", action="store_true")
    p_agent.set_defaults(func=cmd_agent)

    p_arc = sub.add_parser("arc", help="Synthesize + apply an ARC task program")
    p_arc.add_argument("task_file", help="Path to ARC task JSON")
    p_arc.add_argument("--json", action="store_true", help="Machine-readable output")
    p_arc.add_argument("--onnx", action="store_true", help="Export program as ONNX")
    p_arc.add_argument("--onnx-out", default=None, dest="onnx_out", help="ONNX output path")
    p_arc.add_argument("--no-ledger", action="store_true", help="Skip ledger write")
    p_arc.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_arc.add_argument("--verbose", "-v", action="store_true")
    p_arc.set_defaults(func=cmd_arc)

    p_cursor = sub.add_parser("cursor", help="Delegate a bounded repo task to Cursor Agent")
    p_cursor.add_argument("task", help="Repo task to hand to Cursor Agent")
    p_cursor.add_argument("--workspace", default=str(Path.cwd()), help="Workspace directory")
    p_cursor.add_argument("--model", default=None, help="Cursor model override")
    p_cursor.add_argument("--mode", default=None, choices=["plan", "ask"], help="Cursor execution mode")
    p_cursor.add_argument("--force", action="store_true", help="Pass --force to Cursor Agent")
    p_cursor.add_argument(
        "--output-format",
        default="text",
        choices=["text", "json", "stream-json"],
        dest="output_format",
        help="Cursor CLI output format",
    )
    p_cursor.add_argument(
        "--stream-partial-output",
        action="store_true",
        dest="stream_partial_output",
        help="Enable stream-json partial output deltas",
    )
    p_cursor.add_argument("--continue-session", action="store_true", dest="continue_session")
    p_cursor.add_argument("--no-ledger", action="store_true", help="Skip ledger write")
    p_cursor.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_cursor.add_argument("--verbose", "-v", action="store_true")
    p_cursor.set_defaults(func=cmd_cursor)

    p_workflow = sub.add_parser("workflow", help="Declarative .geoseal.yaml workflow runner")
    wf_sub = p_workflow.add_subparsers(dest="workflow_cmd", required=True)

    p_wf_list = wf_sub.add_parser("list", help="List .geoseal.yaml workflows in a directory")
    p_wf_list.add_argument("--dir", default=".", help="Directory to scan")
    p_wf_list.add_argument("--json", action="store_true")
    p_wf_list.set_defaults(func=cmd_workflow, workflow_cmd="list")

    p_wf_val = wf_sub.add_parser("validate", help="Validate a workflow spec")
    p_wf_val.add_argument("workflow_file")
    p_wf_val.add_argument("--json", action="store_true")
    p_wf_val.set_defaults(func=cmd_workflow, workflow_cmd="validate")

    p_wf_run = wf_sub.add_parser("run", help="Run a workflow")
    p_wf_run.add_argument("workflow_file")
    p_wf_run.add_argument("--input", default=None, help="Initial input string")
    p_wf_run.add_argument("--input-file", default=None, dest="input_file")
    p_wf_run.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_wf_run.add_argument("--no-ledger", action="store_true")
    p_wf_run.add_argument("--json", action="store_true")
    p_wf_run.add_argument("--verbose", "-v", action="store_true")
    p_wf_run.set_defaults(func=cmd_workflow, workflow_cmd="run")

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
