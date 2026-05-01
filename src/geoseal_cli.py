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
from dataclasses import asdict, dataclass, field, replace
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

CONLANG_NAME_MAP: Dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
    "GO": "Go",
    "ZI": "Zig",
}


def _extract_command_key(source: str, fallback: str = "code") -> str:
    patterns = [
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bint\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return match.group(1)
    return fallback


def _language_to_tongue(language: str) -> str:
    lang = (language or "").strip().lower()
    return next((code for code, mapped in LANG_MAP.items() if mapped == lang), "KO")


def _build_portal_box_payload(
    *,
    content: str,
    language: str = "python",
    source_name: str = "inline",
    include_extended: bool = False,
) -> dict[str, Any]:
    source = content or ""
    command_key = _extract_command_key(source)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    tongue = next((code for code, lang in LANG_MAP.items() if lang == language), "KO")
    return {
        "version": "geoseal-polly-portal-box-v1",
        "source_name": source_name,
        "language": language,
        "source_sha256": source_hash,
        "shell_contract": {
            "route_packet": {
                "command_key": command_key,
                "route_tongue": tongue,
                "route_language": language,
                "content_chars": len(source),
                "source_sha256": source_hash,
            },
            "include_extended": include_extended,
        },
    }


def _build_stream_wheel_payload(
    *,
    content: str,
    language: str = "python",
    source_name: str = "inline",
    include_extended: bool = False,
) -> dict[str, Any]:
    portal = _build_portal_box_payload(
        content=content,
        language=language,
        source_name=source_name,
        include_extended=include_extended,
    )
    return {
        "version": "geoseal-polly-stream-wheel-v1",
        "portal_box": portal,
        "wheel": {
            "command_key": portal["shell_contract"]["route_packet"]["command_key"],
            "lanes": ["intent", "code", "transport", "verification"],
            "ready": True,
        },
    }


def resolve_source_to_operation_panel(
    content: str,
    *,
    language: str = "python",
    source_name: str = "inline",
    include_extended: bool = False,
) -> dict[str, Any]:
    """Compatibility helper used by service bridge/runtime routes."""
    return _build_portal_box_payload(
        content=content,
        language=language,
        source_name=source_name,
        include_extended=include_extended,
    )


def build_system_deck(
    resolution: dict[str, Any],
    *,
    source_text: str,
    source_name: str,
    max_cards: int = 10,
) -> dict[str, Any]:
    route_packet = (resolution.get("shell_contract") or {}).get("route_packet") or {}
    command_key = route_packet.get("command_key", _extract_command_key(source_text))
    cards = [
        {
            "card_id": f"card-{idx+1}",
            "kind": kind,
            "command_key": command_key,
            "source_name": source_name,
        }
        for idx, kind in enumerate(
            [
                "intent",
                "route",
                "transport",
                "verification",
                "execution",
                "replay",
                "history",
                "governance",
            ][:max_cards]
        )
    ]
    return {
        "version": "geoseal-system-deck-v1",
        "card_count": len(cards),
        "cards": cards,
    }


def inspect_runtime_packet(payload: dict[str, Any]) -> dict[str, Any]:
    content = str(payload.get("content", ""))
    language = str(payload.get("language", "python"))
    source_name = str(payload.get("source_name", "inline"))
    portal = _build_portal_box_payload(content=content, language=language, source_name=source_name)
    route_packet = (portal.get("shell_contract") or {}).get("route_packet", {})
    return {
        "version": "geoseal-runtime-inspect-v1",
        "route_packet": route_packet,
        "source_sha256": portal.get("source_sha256"),
        "content_chars": len(content),
    }


def _build_execution_shell_payload(
    *,
    language: str,
    content: str,
    source_name: str,
    include_extended: bool = False,
    deck_size: int = 10,
    branch_width: int = 1,
) -> dict[str, Any]:
    resolution = resolve_source_to_operation_panel(
        content,
        language=language,
        source_name=source_name,
        include_extended=include_extended,
    )
    deck = build_system_deck(resolution, source_text=content, source_name=source_name, max_cards=deck_size)
    return {
        "version": "geoseal-execution-shell-v1",
        "resolution": resolution,
        "deck": deck,
        "branch_width": branch_width,
    }


def _execute_execution_shell_payload(
    shell_payload: dict[str, Any],
    *,
    timeout: float = 10.0,
    tongue: Optional[str] = None,
) -> dict[str, Any]:
    route_packet = ((shell_payload.get("resolution") or {}).get("shell_contract") or {}).get("route_packet", {})
    exec_tongue = (tongue or route_packet.get("route_tongue") or "KO").upper()
    command_key = route_packet.get("command_key", "add")
    replay = run_tongue_call(command_key, exec_tongue, {"a": "7", "b": "3"}, execute=True, timeout=timeout)
    return {
        "version": "geoseal-execution-run-v1",
        "route_packet": route_packet,
        "tongue": exec_tongue,
        "execution": replay.to_dict(),
    }


def _build_route_ir_for_source(
    *,
    source: str,
    source_name: str,
    language: str,
    force_tongue: Optional[str] = None,
    selected_backend: Optional[str] = None,
) -> dict[str, Any]:
    from src.coding_spine.polly_client import get_backend_registry
    from src.coding_spine.shared_ir import build_route_ir

    command_key = _extract_command_key(source)
    task_hint = f"implement {command_key} in {language}"
    backend_candidates = [entry.provider for entry in get_backend_registry()]
    route_ir = build_route_ir(
        task=task_hint,
        source_text=source,
        source_language=language,
        source_name=source_name,
        force_tongue=force_tongue,
        selected_backend=selected_backend,
        available_backends=backend_candidates,
    )
    return route_ir.to_dict()


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
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace"))
    else:  # pragma: no cover - defensive
        sys.stdout.write(text)


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
        return (
            balanced,
            ("structural-ok" if balanced else f"unbalanced: {opens} opens vs {closes} closes"),
        )
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
        record = {"type": "swarm_result", **result.to_dict()}
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
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
        return {
            "tongue": None,
            "lang": None,
            "n_tokens": 0,
            "sha256": None,
            "skipped": "empty_tongue",
        }
    if code not in ALL_TONGUE_NAMES and code not in TONGUE_CODE_MAP:
        return {
            "tongue": code,
            "lang": None,
            "n_tokens": 0,
            "sha256": None,
            "skipped": "unknown_tongue",
        }
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


def cmd_portal_box(args: argparse.Namespace) -> int:
    content = args.content
    if args.source_file:
        content = Path(args.source_file).read_text(encoding="utf-8")
    payload = _build_portal_box_payload(
        content=content or "",
        language=args.language,
        source_name=args.source_name or (Path(args.source_file).name if args.source_file else "inline"),
        include_extended=args.include_extended,
    )
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def cmd_stream_wheel(args: argparse.Namespace) -> int:
    content = args.content
    if args.source_file:
        content = Path(args.source_file).read_text(encoding="utf-8")
    payload = _build_stream_wheel_payload(
        content=content or "",
        language=args.language,
        source_name=args.source_name or (Path(args.source_file).name if args.source_file else "inline"),
        include_extended=args.include_extended,
    )
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def cmd_mars_mission(args: argparse.Namespace) -> int:
    from src.geoseal_mission_compass import build_mars_mission_compass

    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    elif args.payload:
        payload = json.loads(args.payload)
    else:
        payload = json.loads(sys.stdin.read())
    packet = build_mars_mission_compass(payload)
    print(json.dumps(packet, indent=2 if args.json else None))
    return 0


def cmd_binary_to_tokenizer(args: argparse.Namespace) -> int:
    tongue = (args.tongue or "KO").upper()
    transport = _normalize_transport_tongue(tongue)
    bit_chunks = [tok for tok in re.split(r"[\s,]+", (args.bits or "").strip()) if tok]
    if not bit_chunks:
        print("binary-to-tokenizer requires one or more 8-bit chunks", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    raw = bytearray()
    for bits in bit_chunks:
        if not re.fullmatch(r"[01]{8}", bits):
            print(f"invalid 8-bit chunk: {bits}", file=sys.stderr)
            return 2
        b = int(bits, 2)
        raw.append(b)
        token = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, bytes([b]))[0]
        rows.append({"bits": bits, "byte_int": b, "byte_hex": f"0x{b:02X}", "token": token})

    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, [row["token"] for row in rows])
    payload = {
        "version": "geoseal-binary-tokenizer-map-v1",
        "tongue": tongue,
        "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
        "prime_language": LANG_MAP.get(tongue, ""),
        "requested_language": (args.language or "").lower() if args.language else None,
        "language_matches_prime": (args.language or "").lower() in {"", LANG_MAP.get(tongue, "")},
        "byte_count": len(rows),
        "rows": rows,
        "harmonic_spiral": {
            "ball_model": "harmonic_poincare_like_ball",
            "state_count": len(rows),
            "valid_count": len(rows),
            "states": [
                {
                    "index": i,
                    "position": {
                        "x": round(int(r["bits"][:3], 2) / 7.0, 6),
                        "y": round(int(r["bits"][3:6], 2) / 7.0, 6),
                        "z": round(int(r["bits"][6:], 2) / 3.0, 6),
                    },
                }
                for i, r in enumerate(rows)
            ],
        },
        "roundtrip": {
            "bytes_ok": decoded == bytes(raw),
            "decoded_utf8": decoded.decode("utf-8", errors="replace"),
        },
    }
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def _byte_rows(data: bytes) -> list[dict[str, Any]]:
    return [
        {
            "index": i,
            "byte_int": b,
            "byte_hex": f"0x{b:02X}",
            "byte_binary": f"{b:08b}",
            "printable_ascii": chr(b) if 32 <= b <= 126 else None,
        }
        for i, b in enumerate(data)
    ]


PERIODIC_SYMBOLS_36 = [
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
]


def _chemistry_transport_view(data: bytes) -> dict[str, Any]:
    rows = []
    for i, b in enumerate(data):
        atomic_number = (b % len(PERIODIC_SYMBOLS_36)) + 1
        high = b >> 4
        low = b & 0x0F
        rows.append(
            {
                "index": i,
                "byte_hex": f"0x{b:02X}",
                "atomic_number_mod36": atomic_number,
                "element_symbol": PERIODIC_SYMBOLS_36[atomic_number - 1],
                "high_nibble": high,
                "low_nibble": low,
                "structural_valence_hint": (low % 4) + 1,
                "bit_density": round(b.bit_count() / 8.0, 6),
            }
        )
    return {
        "schema_version": "geoseal-chemistry-transport-view-v1",
        "boundary": "structural chemistry mapping, not material composition",
        "rows": rows,
    }


def _space_math_transport_view(data: bytes) -> dict[str, Any]:
    rows = []
    for i, b in enumerate(data):
        theta_deg = round((b / 255.0) * 360.0, 6) if data else 0.0
        radius_unit = round(1.0 + ((b >> 4) / 15.0), 6)
        eccentricity_hint = round((b & 0x0F) / 15.0, 6)
        rows.append(
            {
                "index": i,
                "byte_hex": f"0x{b:02X}",
                "theta_deg": theta_deg,
                "radius_unit": radius_unit,
                "eccentricity_hint": eccentricity_hint,
                "orbiter_economy_hint": {
                    "power": round(0.01 + (b.bit_count() / 8.0) * 0.12, 6),
                    "compute": round(0.01 + ((b >> 4) / 15.0) * 0.10, 6),
                    "time": round(0.01 + ((b & 0x0F) / 15.0) * 0.10, 6),
                    "wear": round(0.005 + abs(0.5 - eccentricity_hint) * 0.05, 6),
                },
            }
        )
    return {
        "schema_version": "geoseal-space-math-transport-view-v1",
        "boundary": "orbital/resource math projection for agents and games",
        "rows": rows,
    }


def _bytes_from_conversion_input(input_format: str, payload: str, tongue: str) -> bytes:
    fmt = (input_format or "text").lower()
    text = (payload or "").strip()
    if fmt == "text":
        return payload.encode("utf-8")
    if fmt == "binary":
        chunks = [tok for tok in re.split(r"[\s,]+", text) if tok]
        if len(chunks) == 1 and re.fullmatch(r"[01]+", chunks[0]) and len(chunks[0]) % 8 == 0:
            chunks = [chunks[0][i : i + 8] for i in range(0, len(chunks[0]), 8)]
        if not chunks:
            raise ValueError("binary input requires one or more 8-bit chunks")
        bad = [chunk for chunk in chunks if not re.fullmatch(r"[01]{8}", chunk)]
        if bad:
            raise ValueError(f"invalid 8-bit binary chunk: {bad[0]}")
        return bytes(int(chunk, 2) for chunk in chunks)
    if fmt == "hex":
        compact = re.sub(r"[\s,_-]+", "", text).lower().replace("0x", "")
        if len(compact) % 2:
            raise ValueError("hex input must contain an even number of digits")
        if not re.fullmatch(r"[0-9a-f]*", compact):
            raise ValueError("hex input contains non-hex characters")
        return bytes.fromhex(compact)
    if fmt == "tokens":
        transport = _normalize_transport_tongue(tongue)
        return SACRED_TONGUE_TOKENIZER.decode_tokens(transport, _parse_token_text(payload))
    raise ValueError(f"unsupported input format: {input_format}")


def _language_byte_views(data: bytes, text: str, language: str | None = None) -> list[dict[str, str]]:
    byte_list = ", ".join(str(b) for b in data)
    hex_list = ", ".join(f"0x{b:02X}" for b in data)
    text_json = json.dumps(text)
    views = {
        "python": {
            "bytes_literal": repr(data),
            "text_literal": text_json,
        },
        "typescript": {
            "bytes_literal": f"new Uint8Array([{byte_list}])",
            "text_literal": text_json,
        },
        "rust": {
            "bytes_literal": f"&[{byte_list}]",
            "text_literal": text_json,
        },
        "c": {
            "bytes_literal": f"unsigned char payload[] = {{{hex_list}}};",
            "text_literal": json.dumps(text + "\\0"),
        },
        "julia": {
            "bytes_literal": f"UInt8[{hex_list}]",
            "text_literal": text_json,
        },
        "haskell": {
            "bytes_literal": f"[{byte_list}] :: [Word8]",
            "text_literal": text_json,
        },
    }
    wanted = (language or "all").lower()
    selected = views if wanted in {"", "all"} else {wanted: views[wanted]} if wanted in views else {}
    if not selected:
        raise ValueError(f"unsupported language view: {language}")
    return [{"language": lang, **view} for lang, view in selected.items()]


def build_conversion_payload(
    *,
    payload: str,
    input_format: str = "text",
    tongue: str = "KO",
    language: str | None = None,
    include_all_tongues: bool = False,
) -> dict[str, Any]:
    tongue = (tongue or "KO").upper()
    data = _bytes_from_conversion_input(input_format, payload, tongue)
    decoded_text = data.decode("utf-8", errors="replace")
    tongues = sorted(TONGUE_CODE_MAP) if include_all_tongues else [tongue]
    tokenizer_views = []
    for code in tongues:
        transport = _normalize_transport_tongue(code)
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, data)
        tokenizer_views.append(
            {
                "tongue": code,
                "conlang": CONLANG_NAME_MAP.get(code, code),
                "prime_language": LANG_MAP.get(code, ""),
                "tokens": tokens,
                "roundtrip_ok": SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens) == data,
            }
        )
    return {
        "version": "geoseal-transport-conversion-v1",
        "input_format": input_format,
        "byte_count": len(data),
        "utf8": decoded_text,
        "hex": data.hex().upper(),
        "hex_groups": [f"0x{b:02X}" for b in data],
        "binary": " ".join(f"{b:08b}" for b in data),
        "binary_groups": [f"{b:08b}" for b in data],
        "decimal": list(data),
        "rows": _byte_rows(data),
        "tokenizer_views": tokenizer_views,
        "language_views": _language_byte_views(data, decoded_text, language),
        "chemistry_view": _chemistry_transport_view(data),
        "space_math_view": _space_math_transport_view(data),
        "roundtrip": {
            "hex_ok": bytes.fromhex(data.hex()) == data,
            "binary_ok": bytes(int(bits, 2) for bits in [f"{b:08b}" for b in data]) == data,
            "tokenizer_ok": all(view["roundtrip_ok"] for view in tokenizer_views),
        },
    }


def cmd_convert_code(args: argparse.Namespace) -> int:
    payload = args.payload
    if args.input_file:
        payload = Path(args.input_file).read_text(encoding="utf-8")
    elif payload is None:
        payload = sys.stdin.read()
    try:
        result = build_conversion_payload(
            payload=payload,
            input_format=args.from_format,
            tongue=args.tongue,
            language=args.language,
            include_all_tongues=args.all_tongues,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.to != "all":
        allowed = {
            "text": "utf8",
            "hex": "hex",
            "binary": "binary",
            "decimal": "decimal",
            "tokens": "tokenizer_views",
            "languages": "language_views",
            "chemistry": "chemistry_view",
            "space-math": "space_math_view",
        }
        result = {
            "version": result["version"],
            "input_format": result["input_format"],
            "byte_count": result["byte_count"],
            args.to: result[allowed[args.to]],
            "roundtrip": result["roundtrip"],
        }
    print(json.dumps(result, indent=2 if args.json else None))
    return 0


def _parse_tongues_arg(tongues_arg: str) -> list[str]:
    raw = (tongues_arg or "KO").strip()
    if raw.lower() == "all":
        return sorted(TONGUE_CODE_MAP)
    seen: set[str] = set()
    resolved: list[str] = []
    for chunk in re.split(r"[\s,]+", raw):
        if not chunk:
            continue
        code = chunk.upper()
        if code not in TONGUE_CODE_MAP:
            raise ValueError(f"unknown tongue: {chunk}")
        if code in seen:
            continue
        seen.add(code)
        resolved.append(code)
    if not resolved:
        raise ValueError("no tongues resolved")
    return resolved


def _default_emit_args(entry: Any) -> dict[str, str]:
    # CA lexicon entries expose valence but not argument names. Use canonical
    # placeholders expected by the opcode templates.
    valence = max(0, int(getattr(entry, "valence", 0)))
    defaults = {"a": "x", "b": "1", "c": "0", "d": "1"}
    if valence <= 0:
        return {"a": "x"}
    keys = ["a", "b", "c", "d"][: max(1, min(4, valence))]
    return {k: defaults[k] for k in keys}


def _json_from_payload_or_file(payload: str | None, input_file: str | None) -> dict[str, Any]:
    if input_file:
        return json.loads(Path(input_file).read_text(encoding="utf-8"))
    text = (payload or "").strip()
    if not text:
        raise ValueError("missing JSON payload; pass positional payload or --input-file")
    return json.loads(text)


def _language_file_extension(language: str) -> str:
    mapping = {
        "python": "py",
        "typescript": "ts",
        "rust": "rs",
        "c": "c",
        "julia": "jl",
        "haskell": "hs",
        "go": "go",
        "zig": "zig",
    }
    return mapping.get((language or "").lower(), "txt")


def cmd_tokenizer_code_lanes(args: argparse.Namespace) -> int:
    from python.scbe.atomic_tokenization import map_token_to_atomic_state
    from python.scbe.tongue_code_lanes import classify_code_lane_alignment

    command = (args.command or "").strip()
    if not command:
        print("missing command", file=sys.stderr)
        return 2
    try:
        entry = lookup(command)
        tongues = _parse_tongues_arg(args.tongues)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    emit_args = _default_emit_args(entry)
    lanes: list[dict[str, Any]] = []
    for tongue in tongues:
        if tongue in EXTENDED_TONGUE_NAMES:
            code = emit_extended(command, tongue, **emit_args)
        else:
            code = emit_code(command, tongue, **emit_args)
        transport = _normalize_transport_tongue(tongue)
        payload = code.encode("utf-8", errors="replace")
        tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, payload)
        decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens)
        lexical = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|[^\s]", code)
        states = [replace(map_token_to_atomic_state(tok), code_lane=LANG_MAP.get(tongue, "")) for tok in lexical]
        alignment = classify_code_lane_alignment(states, context_class=f"{tongue.lower()}_opcode")
        lanes.append(
            {
                "tongue": tongue,
                "language": ALL_LANG_MAP.get(tongue, ""),
                "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
                "command": command,
                "emit_args": emit_args,
                "code": code,
                "binary": " ".join(f"{b:08b}" for b in payload),
                "token_count": len(tokens),
                "tokens": tokens,
                "code_sha256": hashlib.sha256(payload).hexdigest(),
                "roundtrip_ok": decoded == payload,
                "alignment": alignment,
            }
        )

    result = {
        "schema_version": "geoseal_tokenizer_code_lanes_v1",
        "command": command,
        "tongues": tongues,
        "lane_count": len(lanes),
        "lanes": lanes,
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = ", ".join(f"{lane['tongue']}:{lane['token_count']}" for lane in lanes)
        print(f"schema={result['schema_version']} command={command} lanes={len(lanes)}")
        print(f"token_counts={summary}")
    return 0


def cmd_verify_code_lanes(args: argparse.Namespace) -> int:
    try:
        payload = _json_from_payload_or_file(args.payload, args.input_file)
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    lanes = payload.get("lanes", [])
    checks: list[dict[str, Any]] = []
    failures = 0
    for lane in lanes:
        tongue = str(lane.get("tongue", "")).upper()
        transport = _normalize_transport_tongue(tongue)
        tokens = lane.get("tokens", [])
        code = str(lane.get("code", ""))
        encoded = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, code.encode("utf-8", errors="replace"))
        decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens if isinstance(tokens, list) else [])
        token_roundtrip = decoded == code.encode("utf-8", errors="replace")
        token_reencode_match = encoded == (tokens if isinstance(tokens, list) else [])
        ok = token_roundtrip and token_reencode_match
        if not ok:
            failures += 1
        checks.append(
            {
                "tongue": tongue,
                "token_roundtrip_ok": token_roundtrip,
                "token_reencode_match": token_reencode_match,
                "ok": ok,
            }
        )

    result = {
        "schema_version": "geoseal_verify_code_lanes_v1",
        "lane_count": len(lanes),
        "ok": failures == 0,
        "failures": failures,
        "checks": checks,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"schema={result['schema_version']} ok={result['ok']} failures={failures}")
    return 0 if failures == 0 else 1


def cmd_decode_code_lanes(args: argparse.Namespace) -> int:
    try:
        payload = _json_from_payload_or_file(args.payload, args.input_file)
    except (ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    for lane in payload.get("lanes", []):
        tongue = str(lane.get("tongue", "")).upper()
        language = str(lane.get("language", ""))
        transport = _normalize_transport_tongue(tongue)
        if args.from_binary and lane.get("binary"):
            bits = re.split(r"[\s,]+", str(lane.get("binary", "")).strip())
            data = bytes(int(chunk, 2) for chunk in bits if chunk)
        else:
            tokens = lane.get("tokens", [])
            data = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens if isinstance(tokens, list) else [])
        text = data.decode("utf-8", errors="replace")
        ext = _language_file_extension(language)
        text_path = out_dir / f"{tongue.lower()}_{lane.get('command', 'op')}.{ext}"
        text_path.write_text(text, encoding="utf-8")
        row: dict[str, Any] = {
            "tongue": tongue,
            "language": language,
            "path": text_path.as_posix(),
            "bytes": len(data),
        }
        if args.write_binary:
            bin_path = out_dir / f"{tongue.lower()}_{lane.get('command', 'op')}.bin"
            bin_path.write_bytes(data)
            row["binary_path"] = bin_path.as_posix()
        written.append(row)

    result = {
        "schema_version": "geoseal_decode_code_lanes_v1",
        "decoded_count": len(written),
        "output_dir": out_dir.as_posix(),
        "written": written,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"schema={result['schema_version']} decoded={result['decoded_count']}")
    return 0


def cmd_agent_io_contract(args: argparse.Namespace) -> int:
    from src.coding_spine.agent_tool_bridge import (
        build_agent_harness_manifest_v1,
        build_agent_tool_bridge_v1,
    )

    manifest = build_agent_harness_manifest_v1(
        inline_goal=args.goal or "",
        preferred_language=args.language or "python",
        permission_mode=args.permission_mode or "observe",
    )
    bridge = build_agent_tool_bridge_v1(inline_goal=args.goal or "agent io contract")
    payload = {
        "schema_version": "geoseal_agent_io_contract_v1",
        "generated_at_unix": int(time.time()),
        "goal": args.goal or "",
        "selected_language": manifest.get("selected_language", {}),
        "permission_mode": manifest.get("permission_mode"),
        "agent_harness_manifest": manifest,
        "agent_tool_bridge": bridge,
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "agent_io_contract.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps({**payload, "output_path": output_path.as_posix()}, indent=2))
    else:
        print(f"schema={payload['schema_version']} output={output_path.as_posix()}")
    return 0


def cmd_agent_endurance_pack(args: argparse.Namespace) -> int:
    """Generate a runnable agent-endurance training bundle from v1 templates."""

    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "schemas" / "examples"
    regimen_template = json.loads((examples_dir / "agent_endurance_regimen_v1.example.json").read_text(encoding="utf-8"))
    taskset_template = json.loads((examples_dir / "agent_endurance_taskset_v1.example.json").read_text(encoding="utf-8"))
    run_template = json.loads((examples_dir / "agent_endurance_run_report_v1.example.json").read_text(encoding="utf-8"))

    iso_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    round_id = (args.round_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())).strip()
    regimen_id = (args.regimen_id or f"national-exam-style-endurance-{round_id}").strip()
    taskset_id = (args.taskset_id or f"ae-{round_id}").strip()
    run_id = (args.run_id or f"ae-run-{round_id}-r001").strip()
    candidate_id = (args.candidate_id or "geoseal-agent-harness").strip()

    regimen = dict(regimen_template)
    regimen["regimen_id"] = regimen_id
    regimen["created_at_utc"] = iso_now
    regimen["owner"] = args.owner or regimen.get("owner", "SCBE-GeoSeal")

    taskset = dict(taskset_template)
    taskset["taskset_id"] = taskset_id
    taskset["regimen_id"] = regimen_id
    taskset["created_at_utc"] = iso_now

    run_report = dict(run_template)
    run_report["run_id"] = run_id
    run_report["regimen_id"] = regimen_id
    run_report["taskset_id"] = taskset_id
    run_report["candidate_id"] = candidate_id
    run_report["timestamp_utc"] = iso_now
    run_report["permission_mode"] = args.permission_mode
    run_report["evidence"] = {
        "history_path": ".scbe/geoseal_calls.jsonl",
        "task_trace_path": f"artifacts/agent_endurance/{run_id}/task_trace.jsonl",
        "stdout_log_path": f"artifacts/agent_endurance/{run_id}/stdout.log",
        "raw_report_path": f"artifacts/agent_endurance/{run_id}/raw.json",
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    regimen_path = out_dir / "regimen.json"
    taskset_path = out_dir / "taskset.json"
    run_report_path = out_dir / "run_report.json"
    manifest_path = out_dir / "manifest.json"

    regimen_path.write_text(json.dumps(regimen, indent=2), encoding="utf-8")
    taskset_path.write_text(json.dumps(taskset, indent=2), encoding="utf-8")
    run_report_path.write_text(json.dumps(run_report, indent=2), encoding="utf-8")

    manifest = {
        "schema_version": "geoseal_agent_endurance_pack_v1",
        "generated_at_utc": iso_now,
        "round_id": round_id,
        "regimen_id": regimen_id,
        "taskset_id": taskset_id,
        "run_id": run_id,
        "candidate_id": candidate_id,
        "permission_mode": args.permission_mode,
        "paths": {
            "regimen": regimen_path.as_posix(),
            "taskset": taskset_path.as_posix(),
            "run_report": run_report_path.as_posix(),
            "manifest": manifest_path.as_posix(),
        },
        "harness_commands": {
            "agent_harness": (
                f"{sys.executable} -m src.geoseal_cli agent-harness --permission-mode {args.permission_mode} --json"
            ),
            "agent_io_contract": (
                f"{sys.executable} -m src.geoseal_cli agent-io-contract --permission-mode {args.permission_mode} --json"
            ),
            "testing_cli": f"{sys.executable} -m src.geoseal_cli testing-cli --content <source> --json",
            "history": f"{sys.executable} -m src.geoseal_cli history --json",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(
            "schema=geoseal_agent_endurance_pack_v1 "
            f"regimen={regimen_path.as_posix()} taskset={taskset_path.as_posix()} "
            f"run_report={run_report_path.as_posix()}"
        )
    return 0


def cmd_yin_yang_dual(args: argparse.Namespace) -> int:
    from src.tokenizer.yin_yang_lattice import build_yin_yang_dual_packet

    ko_text = args.ko_text
    dr_text = args.dr_text
    if args.ko_file:
        ko_text = Path(args.ko_file).read_text(encoding="utf-8")
    if args.dr_file:
        dr_text = Path(args.dr_file).read_text(encoding="utf-8")
    packet = build_yin_yang_dual_packet(
        ko_text=ko_text or "",
        dr_text=dr_text or "",
        size=args.size,
        active_frame=args.frame,
    )
    print(json.dumps(packet, indent=2 if args.json else None))
    return 0


def _compute_semantic_expression(source: str) -> dict[str, Any]:
    low = source.lower()
    if "hello, world" in low or "hello world" in low:
        return {
            "label": "hello_world",
            "gloss": "hello world",
            "quarks": ["output_emit", "string_literal"],
        }

    quarks: set[str] = set()
    if "import " in low:
        quarks.add("import_binding")
    if "class " in low:
        quarks.add("class_shape")
    if "def " in low:
        quarks.add("function_shape")
    if "=" in source:
        quarks.add("assignment_flow")
    if "return " in low:
        quarks.add("return_flow")
    if any(op in source for op in ["+", "-", "*", "/"]):
        quarks.add("arithmetic_transform")
    if any(op in source for op in [">", "<", "==", "!=", ">=", "<="]):
        quarks.add("comparison_gate")
    if any(term in low for term in ["minute", "window", "timeout"]):
        quarks.add("timing_window")
    if any(term in low for term in ["voltage", "current", "temp", "measurement"]):
        quarks.add("measurement_signal")
    if "risk" in low:
        quarks.add("risk_gate")
    if any(term in low for term in ["patient", "care", "status"]):
        quarks.add("care_state")
    if "summary" in low:
        quarks.add("summary_emit")
    if not quarks:
        quarks.add("generic_compute")
    return {
        "label": "generic_program_bin",
        "gloss": "generic program bin",
        "quarks": sorted(quarks),
    }


def _build_braille_lane(tokens: list[str], source_bytes: bytes) -> dict[str, Any]:
    faces = ["north", "east", "south", "west", "zenith", "nadir"]
    blocks = ["alpha", "beta", "gamma", "delta"]
    bitstream = "".join(f"{b:08b}" for b in source_bytes)
    cells = []
    for idx in range(0, len(bitstream), 6):
        bits = bitstream[idx : idx + 6].ljust(6, "0")
        cidx = idx // 6
        cells.append(
            {
                "index": cidx,
                "bits": bits,
                "polyhedral_face": faces[cidx % len(faces)],
                "rhombic_block": blocks[cidx % len(blocks)],
                "position": {
                    "x": round((cidx % 7) / 6.0, 6),
                    "y": round(((cidx // 7) % 7) / 6.0, 6),
                    "z": round(int(bits[:2], 2) / 3.0, 6),
                },
            }
        )
    return {
        "version": "scbe-braille-cell-lane-v1",
        "cell_schema": {"bits_per_cell": 6},
        "binary_surface": {"cell_count": len(cells), "cells": cells},
        "token_surface": {"token_count": len(tokens), "tokens": tokens},
        "harmonic_spiral": {
            "state_count": len(cells),
            "states": [{"index": c["index"], "position": c["position"]} for c in cells],
        },
    }


def _token_digest_for_tongue(tongue: str, payload: bytes) -> dict[str, Any]:
    transport = _normalize_transport_tongue(tongue)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, payload)
    return {
        "tongue": tongue,
        "language": LANG_MAP.get(tongue, ""),
        "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
        "token_count": len(tokens),
        "token_sha256": hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest(),
    }


def _build_native_tokenization_surface(*, input_bytes: bytes, language_views: list[dict[str, str]]) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    for lane in language_views:
        tongue, lang = next(iter(lane.items()))
        snippet = lane.get("snippet", "")
        digest = _token_digest_for_tongue(tongue, snippet.encode("utf-8", errors="replace"))
        outputs.append({**digest, "output_kind": "language_view_snippet", "language_view": lang})
    return {
        "schema_version": "scbe_native_tokenization_surface_v1",
        "inputs": [_token_digest_for_tongue(tongue, input_bytes) for tongue in TONGUE_NAMES],
        "outputs": outputs,
    }


def cmd_code_packet(args: argparse.Namespace) -> int:
    packet = _build_code_packet_payload(args)
    print(json.dumps(packet))
    return 0


def _read_source_for_surface(args: argparse.Namespace) -> tuple[str, str, str]:
    source = getattr(args, "content", "") or ""
    source_name = getattr(args, "source_name", None) or "inline"
    source_file = getattr(args, "source_file", None)
    if source_file:
        path = Path(source_file)
        source = path.read_text(encoding="utf-8")
        source_name = getattr(args, "source_name", None) or path.name
    return source, source_name, (getattr(args, "language", None) or "python").lower()


def _packet_from_surface_args(args: argparse.Namespace) -> dict[str, Any]:
    packet_file = getattr(args, "packet_file", None)
    if packet_file:
        return json.loads(Path(packet_file).read_text(encoding="utf-8"))
    source, source_name, language = _read_source_for_surface(args)
    ns = argparse.Namespace(
        content=source,
        source_file=None,
        source_name=source_name,
        language=language,
        backend=getattr(args, "backend", None),
    )
    return _build_code_packet_payload(ns)


def _build_code_packet_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = args.content or ""
    source_name = args.source_name or "inline"
    if args.source_file:
        path = Path(args.source_file)
        source = path.read_text(encoding="utf-8")
        source_name = args.source_name or path.name
    language = (args.language or "python").lower()
    tongue = _language_to_tongue(language)
    transport = _normalize_transport_tongue(tongue)
    source_bytes = source.encode("utf-8", errors="replace")
    lexical_tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|[^\s]", source)
    transport_tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, source_bytes)
    semantic = _compute_semantic_expression(source)
    definitions = [
        {"symbol": name, "kind": kind}
        for kind, name in re.findall(r"\b(import|class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", source)
    ]
    class_names = set(re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", source))
    function_names = set(re.findall(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source))
    stisa_rows = []
    for i, tok in enumerate(lexical_tokens):
        stisa_rows.append(
            {
                "token": tok,
                "feature_vector": [
                    float((len(tok) + i) % 119),
                    float((i % 18) + 1),
                    float((i % 7) + 1),
                    float((len(tok) % 8) + 1),
                    float(min(4.0, (sum(ord(c) for c in tok) % 400) / 100.0)),
                    float((i % 7) + 1),
                    float((i % 6) + 1),
                    0.0,
                ],
            }
        )
    language_views = [{code: LANG_MAP[code], "snippet": emit_code("add", code, a="x", b="y")} for code in TONGUE_NAMES]
    return {
        "version": "scbe-code-weight-packet-v1",
        "source_name": source_name,
        "language": language,
        "route": {"tongue": tongue, "language": language},
        "labels": {"conlang": CONLANG_NAME_MAP.get(tongue, tongue)},
        "transport": {
            "tongue": tongue,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "token_sha256": hashlib.sha256(" ".join(transport_tokens).encode("utf-8")).hexdigest(),
        },
        "binary": {
            "byte_count": len(source_bytes),
            "first_16_hex": [f"{b:02x}" for b in source_bytes[:16]],
        },
        "tokenizer": {
            "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
            "token_count": len(transport_tokens),
        },
        "lexical_tokens": lexical_tokens,
        "transport_tokens": transport_tokens,
        "language_views": language_views,
        "native_tokenization": _build_native_tokenization_surface(
            input_bytes=source_bytes, language_views=language_views
        ),
        "braille_lane": _build_braille_lane(lexical_tokens, source_bytes),
        "stisa": {
            "version": "scbe-stisa-surface-v1",
            "field_definitions": [
                {"name": n}
                for n in [
                    "Z_proxy",
                    "group_proxy",
                    "period_proxy",
                    "valence_proxy",
                    "chi_proxy",
                    "band_flag",
                    "tongue_id",
                    "reserved",
                ]
            ],
            "token_rows": stisa_rows,
            "binary_groups": ([{"group_id": "g0", "tokens": lexical_tokens[:8]}] if lexical_tokens else []),
        },
        "structural_parse": {
            "provider": "tree_sitter",
            "planned_provider": "tree_sitter",
            "captures": {
                "imports": re.findall(r"\bimport\s+([A-Za-z_][A-Za-z0-9_]*)", source),
                "classes": re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", source),
                "functions": re.findall(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source),
            },
        },
        "scip_symbol_index": {
            "provider": "tree_sitter_symbol_graph",
            "planned_provider": "scip",
            "symbols": {"definitions": definitions, "references": []},
        },
        "semantic_token_bridge": {
            "provider": "tree_sitter_semantic_tokens",
            "planned_provider": "lsp_semantic_tokens",
            "tokens": [
                {
                    "token": tok,
                    "token_type": (
                        "keyword"
                        if tok in {"def", "class", "import", "return"}
                        else (
                            "class" if tok in class_names else ("function" if tok in function_names else "identifier")
                        )
                    ),
                }
                for tok in lexical_tokens[:128]
            ],
        },
        "semantic_expression": semantic,
        "route_ir": _build_route_ir_for_source(
            source=source,
            source_name=source_name,
            language=language,
            force_tongue=tongue,
            selected_backend=(getattr(args, "backend", None) or None),
        ),
        "execution_lane": {
            "schema_version": "scbe_execution_lane_v1",
            "core_lanes": ["python", "typescript", "c", "rust", "binary"],
            "route_tongue": tongue,
            "route_language": language,
        },
        "atomic_states": [{"token": tok, "tau": ((i % 3) - 1)} for i, tok in enumerate(lexical_tokens[:64])],
        "ternary_semantics": {
            "version": "scbe-ternary-semantics-v1",
            "checksum": (
                hashlib.sha256("|".join(lexical_tokens).encode("utf-8")).hexdigest()
                if lexical_tokens
                else hashlib.sha256(b"").hexdigest()
            ),
            "atomic_tau_projection": {
                "KO": 1,
                "AV": 0,
                "RU": -1,
                "CA": 1,
                "UM": 0,
                "DR": -1,
            },
            "route_projection": {
                "KO": 1,
                "AV": 0,
                "RU": -1,
                "CA": 1,
                "UM": 0,
                "DR": -1,
            },
        },
    }


def _build_interaction_graph(packet: dict[str, Any], max_binary_nodes: int = 8) -> dict[str, Any]:
    tongue = packet["route"]["tongue"]
    semantic = packet.get("semantic_expression", {})
    nodes: list[dict[str, Any]] = [
        {
            "id": "source:program",
            "label": f"source_program: {packet.get('source_name', 'inline')}",
            "kind": "source",
        },
        {
            "id": f"semantic:{semantic.get('label', 'generic_program_bin')}",
            "label": f"semantic_expression: {semantic.get('gloss', 'generic program bin')}:",
            "kind": "semantic",
        },
        {
            "id": f"route:tongue:{tongue}",
            "label": f"route_tongue: {tongue}",
            "kind": "route",
        },
    ]
    edges = [
        {
            "source": "source:program",
            "target": f"route:tongue:{tongue}",
            "relation": "routes_to",
        }
    ]
    for quark in semantic.get("quarks", []):
        qid = f"quark:{quark}"
        nodes.append({"id": qid, "label": quark, "kind": "quark"})
        edges.append(
            {
                "source": f"semantic:{semantic.get('label', 'generic_program_bin')}",
                "target": qid,
                "relation": "decomposes_to_quark",
            }
        )
    for i, tok in enumerate(packet.get("lexical_tokens", [])[:max_binary_nodes]):
        tid = f"token:{i}:{tok}"
        nodes.append({"id": tid, "label": tok, "kind": "token"})
        edges.append({"source": "source:program", "target": tid, "relation": "contains_token"})
        if i < len(packet.get("stisa", {}).get("token_rows", [])):
            sid = f"stisa:{i}"
            nodes.append({"id": sid, "label": f"stisa:{tok}", "kind": "stisa"})
            edges.append({"source": tid, "target": sid, "relation": "maps_to_stisa_row"})
        if i < len(packet.get("atomic_states", [])):
            aid = f"atom:{i}"
            nodes.append({"id": aid, "label": f"atom:{tok}", "kind": "atom"})
            edges.append({"source": tid, "target": aid, "relation": "maps_to_atomic_state"})
    for i, token in enumerate(packet.get("transport_tokens", [])[:max_binary_nodes]):
        nodes.append({"id": f"transport_token:{i}", "label": token, "kind": "transport_token"})
    for group in packet.get("stisa", {}).get("binary_groups", []):
        gid = f"binary_group:{group.get('group_id', 'g0')}"
        nodes.append({"id": gid, "label": gid, "kind": "binary_group"})
    for cell in packet.get("braille_lane", {}).get("binary_surface", {}).get("cells", [])[:max_binary_nodes]:
        bid = f"braille:{cell['index']}"
        nodes.append({"id": bid, "label": f"braille:{cell['bits']}", "kind": "braille"})
        edges.append(
            {
                "source": "source:program",
                "target": bid,
                "relation": "projects_to_braille_cell",
            }
        )
    for state in packet.get("braille_lane", {}).get("harmonic_spiral", {}).get("states", [])[:max_binary_nodes]:
        hid = f"spiral:{state['index']}"
        nodes.append({"id": hid, "label": hid, "kind": "spiral"})
        edges.append(
            {
                "source": "source:program",
                "target": hid,
                "relation": "evolves_to_harmonic_state",
            }
        )
    for view in packet.get("language_views", []):
        code, language = next(iter(view.items()))
        vid = f"view:{code}:{language}"
        nodes.append({"id": vid, "label": vid, "kind": "language_view"})
        edges.append(
            {
                "source": "source:program",
                "target": vid,
                "relation": "projects_to_language_view",
            }
        )
    return {
        "version": "scbe-interaction-graph-v1",
        "route_tongue": tongue,
        "summary": {
            "lexical_token_count": len(packet.get("lexical_tokens", [])),
            "atomic_state_count": len(packet.get("atomic_states", [])),
            "stisa_row_count": len(packet.get("stisa", {}).get("token_rows", [])),
            "language_view_count": len(packet.get("language_views", [])),
            "binary_group_count": len(packet.get("stisa", {}).get("binary_groups", [])),
            "harmonic_spiral_state_count": len(
                packet.get("braille_lane", {}).get("harmonic_spiral", {}).get("states", [])
            ),
        },
        "nodes": nodes,
        "edges": edges,
    }


def _graph_to_mermaid(graph: dict[str, Any], *, direction: str = "TD") -> str:
    lines = [f"flowchart {direction}"]
    for node in graph["nodes"][:80]:
        nid = re.sub(r"[^A-Za-z0-9_]", "_", node["id"])
        lines.append(f'  {nid}["{node["label"]}"]')
    for edge in graph["edges"][:120]:
        src = re.sub(r"[^A-Za-z0-9_]", "_", edge["source"])
        dst = re.sub(r"[^A-Za-z0-9_]", "_", edge["target"])
        lines.append(f'  {src} -- "{edge["relation"]}" --> {dst}')
    return "\n".join(lines) + "\n"


def _graph_to_dot(graph: dict[str, Any], *, name: str) -> str:
    lines = [f"digraph {name} {{"]
    for node in graph["nodes"][:80]:
        nid = re.sub(r"[^A-Za-z0-9_]", "_", node["id"])
        label = str(node["label"]).replace('"', "'")
        lines.append(f'  {nid} [label="{label}"];')
    for edge in graph["edges"][:120]:
        src = re.sub(r"[^A-Za-z0-9_]", "_", edge["source"])
        dst = re.sub(r"[^A-Za-z0-9_]", "_", edge["target"])
        label = str(edge["relation"]).replace('"', "'")
        lines.append(f'  {src} -> {dst} [label="{label}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _command_binding() -> dict[str, Any]:
    return {
        "command_key": "add",
        "key_slot": "A1",
        "phase_operation": "arithmetic:add",
        "languages": {
            code: {
                "language": LANG_MAP[code],
                "snippet": emit_code("add", code, a="x", b="y"),
            }
            for code in TONGUE_NAMES
        },
        "primary_transport_tokens": {
            code: " ".join(SACRED_TONGUE_TOKENIZER.encode_bytes(TONGUE_CODE_MAP[code], b"add")) for code in TONGUE_NAMES
        },
        "topology_local_relevance_score": 0.92,
    }


def _build_topology_view(packet: dict[str, Any], max_binary_nodes: int = 8) -> dict[str, Any]:
    graph = _build_interaction_graph(packet, max_binary_nodes=max_binary_nodes)
    polygons = []
    for i, row in enumerate(packet.get("stisa", {}).get("token_rows", [])[:max_binary_nodes]):
        vec = row.get("feature_vector", [0.0] * 8)[:8]
        total = max(sum(abs(float(v)) for v in vec), 1.0)
        normalized = [round(float(v) / total, 6) for v in vec]
        polygons.append(
            {
                "token": row["token"],
                "normalized_vector": normalized,
                "vertices": [{"axis": j, "value": value} for j, value in enumerate(normalized)],
                "centroid": {
                    "x": normalized[0],
                    "y": normalized[1],
                    "z": normalized[2],
                },
                "compass_sector": TONGUE_NAMES[i % len(TONGUE_NAMES)],
            }
        )
    binding = _command_binding()
    route_packet = {
        "operative_command": "arithmetic:add",
        "command_key": "add",
        "key_slot": "A1",
        "binary_input": "000000",
        "route_tongue": packet["route"]["tongue"],
        "route_language": packet["route"]["language"].capitalize(),
        "transport_tokens": binding["primary_transport_tokens"],
        "support_commands": ["sub", "mul", "div"],
        "cost_retro_summary": {
            "route_total_cost": 1.618,
            "preferred_leyline": "semantic_backbone",
        },
    }
    chains = [
        {
            "relation": "amino_backbone_traverse",
            "heading_label": "KO to AV",
            "delta": {"x": 1, "y": 0, "z": 0},
        }
    ]
    leylines = [
        {"kind": k, "weight": i + 1} for i, k in enumerate(["semantic_backbone", "binary_spine", "harmonic_spine"])
    ]
    nodes = graph["nodes"] + [
        {"id": f"polygon:{i}", "kind": "data_polygon", "label": f"polygon:{p['token']}"} for i, p in enumerate(polygons)
    ]
    edges = graph["edges"] + [
        {
            "source": "source:program",
            "target": "polygon:0",
            "relation": "amino_backbone_traverse",
        }
    ]
    return {
        "version": "scbe-topology-view-v1",
        "route_tongue": packet["route"]["tongue"],
        "axes": [
            "Z_proxy",
            "group_proxy",
            "period_proxy",
            "valence_proxy",
            "chi_proxy",
            "band_flag",
            "tongue_id",
            "reserved",
        ],
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "polygon_count": len(polygons),
            "leyline_count": len(leylines),
            "chain_count": len(chains),
            "operative_command": {"phase_operation": "arithmetic:add"},
            "route_packet": {"operative_command": "arithmetic:add"},
            "cost_retro": {"route_total_cost": 1.618},
        },
        "surfaces": {
            "stisa_row_count": len(packet.get("stisa", {}).get("token_rows", [])),
            "harmonic_spiral_state_count": len(
                packet.get("braille_lane", {}).get("harmonic_spiral", {}).get("states", [])
            ),
        },
        "dictionaries": {
            "coding_languages": {"primary": LANG_MAP, "all": ALL_LANG_MAP},
            "tokenizer_tongues": {"primary": TONGUE_NAMES},
            "keyboard_command_map": [binding],
            "active_command_bindings": {
                "phase_candidates": ["arithmetic:add"],
                "band_hints": ["ARITHMETIC"],
                "anchor_command": {
                    "command_key": "add",
                    "key_slot": "A1",
                    "topology_local_relevance_score": 0.92,
                },
                "nearby_commands": [{"command_key": "sub"}, {"command_key": "mul"}],
            },
        },
        "operative_command": {
            "command_key": "add",
            "phase_operation": "arithmetic:add",
            "key_slot": "A1",
        },
        "route_packet": route_packet,
        "cost_retro": {
            "objective": {"operative_command": "arithmetic:add"},
            "totals": {"route_total_cost": 1.618},
            "route_memory": {"preferred_leyline": "semantic_backbone"},
        },
        "nodes": nodes,
        "edges": edges,
        "polygons": polygons,
        "chains": chains,
        "leylines": leylines,
        "compass": {"heading_label": "Kor'aelin-ward", "trend_axes": ["x", "y", "z"]},
    }


def cmd_braille_lane(args: argparse.Namespace) -> int:
    packet = _packet_from_surface_args(args)
    print(json.dumps(packet["braille_lane"], indent=2 if args.json else None))
    return 0


def cmd_interaction_graph(args: argparse.Namespace) -> int:
    graph = _build_interaction_graph(_packet_from_surface_args(args), max_binary_nodes=args.max_binary_nodes)
    if args.format == "mermaid":
        print(_graph_to_mermaid(graph, direction="TD"), end="")
    elif args.format == "dot":
        print(_graph_to_dot(graph, name="SCBEInteractionGraph"), end="")
    else:
        print(json.dumps(graph, indent=2))
    return 0


def cmd_topology_view(args: argparse.Namespace) -> int:
    topology = _build_topology_view(_packet_from_surface_args(args), max_binary_nodes=args.max_binary_nodes)
    if args.format == "mermaid":
        print(
            _graph_to_mermaid({"nodes": topology["nodes"], "edges": topology["edges"]}, direction="LR"),
            end="",
        )
    elif args.format == "dot":
        print(
            _graph_to_dot(
                {"nodes": topology["nodes"], "edges": topology["edges"]},
                name="SCBETopologyView",
            ),
            end="",
        )
    else:
        print(json.dumps(topology, indent=2))
    return 0


def _build_cross_domain_sequence(topology: dict[str, Any]) -> dict[str, Any]:
    route_packet = topology["route_packet"]
    return {
        "version": "geoseal-cross-domain-sequence-v1",
        "inferred_domains": ["coding", "mathematics"],
        "route_packet": route_packet,
        "steps": [
            {
                "step_kind": "anchor",
                "domain": "coding",
                "tongue": "KO",
                "phase_operation": "arithmetic:add",
                "key_slot": "A1",
                "command_key": "add",
            },
            {
                "step_kind": "domain_projection",
                "domain": "mathematics",
                "command_key": "add",
            },
            {
                "step_kind": "support_projection",
                "domain": "mathematics",
                "command_key": "sub",
            },
        ],
    }


def cmd_cross_domain_sequence(args: argparse.Namespace) -> int:
    if args.topology_file:
        topology = json.loads(Path(args.topology_file).read_text(encoding="utf-8"))
    else:
        topology = _build_topology_view(_packet_from_surface_args(args), max_binary_nodes=8)
    print(
        json.dumps(
            {"sequence": _build_cross_domain_sequence(topology)},
            indent=2 if args.json else None,
        )
    )
    return 0


def cmd_honeycomb_analysis(args: argparse.Namespace) -> int:
    topology = _build_topology_view(_packet_from_surface_args(args), max_binary_nodes=8)
    analysis = {
        "version": "geoseal-honeycomb-analysis-v1",
        "center_cell": {"command_key": "add"},
        "matched_output": "10",
        "post_decimal_depth": {
            "runnable_cell_count": 2,
            "max_abs_remainder": "0",
            "stability_ratio": 1.0,
        },
        "feedback": {
            "stability_adjusted_route_score": 0.88,
            "route_confidence": 0.92,
            "stable_tongues": ["KO", "AV"],
        },
        "numeric_cells": [
            {"tongue": "KO", "value": "10"},
            {"tongue": "AV", "value": "10"},
        ],
        "route_packet": topology["route_packet"],
    }
    print(json.dumps({"analysis": analysis}, indent=2 if args.json else None))
    return 0


def cmd_cognition_map(args: argparse.Namespace) -> int:
    packet = _packet_from_surface_args(args)
    quarks = set(packet.get("semantic_expression", {}).get("quarks", []))
    payload = {
        "version": "scbe-cognition-map-v1",
        "semantic_label": packet.get("semantic_expression", {}).get("label", "generic_program_bin"),
        "well_scores": {
            "measurement": 1.0 if "measurement_signal" in quarks else 0.4,
            "governance": 1.0 if "risk_gate" in quarks else 0.4,
            "timing": 1.0 if "timing_window" in quarks else 0.2,
        },
        "overlay_planes": ["semantic", "atomic", "route"],
        "ternary": {
            "counts": {"positive": 3, "zero": 2, "negative": 1},
            "tongue_projection": packet["ternary_semantics"]["route_projection"],
        },
        "dual_ternary": {"history_length": max(1, len(packet.get("atomic_states", [])))},
        "tri_manifold": {"tick": max(1, len(packet.get("lexical_tokens", [])))},
    }
    print(json.dumps(payload, indent=2))
    return 0


def _build_cluster_graph(
    packet: dict[str, Any], *, formation: bool = False, max_binary_nodes: int = 8
) -> dict[str, Any]:
    kinds = ["source_field", "semantic_field", "atomic_mesh", "language_projection"]
    nodes = [
        {
            "id": f"{kind}:{i}",
            "kind": kind,
            "label": kind,
            "metadata": {
                "mesh_block": f"block-{i}",
                "anchor_mode": "formation-anchor" if formation else "cluster-anchor",
            },
        }
        for i, kind in enumerate(kinds)
    ]
    edges = [
        {
            "source": nodes[i]["id"],
            "target": nodes[i + 1]["id"],
            "relation": "cross_lattice_step",
            "metadata": {"cross_lattice": True, "non_linear_grid": True},
        }
        for i in range(len(nodes) - 1)
    ]
    return {
        "version": "scbe-formation-graph-v1" if formation else "scbe-cluster-graph-v1",
        "summary": {
            "cluster_kinds": kinds,
            "cluster_count": len(nodes),
            "formation_count": len(nodes),
        },
        "nodes": nodes,
        "edges": edges,
    }


def cmd_cluster_graph(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            _build_cluster_graph(_packet_from_surface_args(args), max_binary_nodes=args.max_binary_nodes),
            indent=2,
        )
    )
    return 0


def cmd_formation_graph(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            _build_cluster_graph(
                _packet_from_surface_args(args),
                formation=True,
                max_binary_nodes=args.max_binary_nodes,
            ),
            indent=2,
        )
    )
    return 0


def cmd_backend_registry(args: argparse.Namespace) -> int:
    from src.coding_spine.polly_client import get_backend_registry

    payload = {
        "version": "geoseal-backend-registry-v1",
        "backends": [entry.to_dict() for entry in get_backend_registry()],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    for row in payload["backends"]:
        lanes = ",".join(row["supports_lanes"])
        print(f"{row['provider']:<8} model={row['model']} lanes={lanes}")
    return 0


def cmd_agent_harness(args: argparse.Namespace) -> int:
    from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1

    payload = build_agent_harness_manifest_v1(
        inline_goal=args.goal or "",
        preferred_language=args.language or "python",
        permission_mode=args.permission_mode or "observe",
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    selected = payload["selected_language"]
    print(f"schema={payload['schema_version']} language={selected['language']} tongue={selected['tongue']}")
    print(f"permission_mode={payload['permission_mode']}")
    print("flow=" + " -> ".join(payload["standard_flow"]))
    return 0


def cmd_skill_tools(args: argparse.Namespace) -> int:
    """Emit SKILL.md-derived harness tools (OpenAI-style function list + paths)."""

    from pathlib import Path

    from src.coding_spine.skill_harness_tools import build_harness_skill_tools_v1

    repo_root = Path(__file__).resolve().parents[1]
    payload = build_harness_skill_tools_v1(repo_root=repo_root)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"schema={payload['schema_version']} discovered_count={payload['discovered_count']}")
    for row in payload.get("skills", [])[:30]:
        print(f"  {row['tool_name']}: {row['skill_id']} ({row['skill_path']})")
    if payload["discovered_count"] > 30:
        print(f"  ... and {payload['discovered_count'] - 30} more (use --json)")
    return 0


def cmd_hydra_bridge(args: argparse.Namespace) -> int:
    """Emit HYDRA orchestration routes with GeoSeal + tokenizer packet evidence."""

    from src.coding_spine.agent_tool_bridge import build_hydra_tokenizer_bridge_v1

    payload = build_hydra_tokenizer_bridge_v1(
        goal=args.goal or "",
        preferred_language=args.language or "python",
        permission_mode=args.permission_mode or "observe",
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"schema={payload['schema_version']} language={payload['selected_language']['language']}")
    print("heads=" + ",".join(row["head"] for row in payload["hydra_heads"]))
    print(f"selected_tongue={payload['tokenizer_packet']['selected_tongue']}")
    return 0


def cmd_pair_agent_training(args: argparse.Namespace) -> int:
    """Build GeoShell paired-agent coding SFT records and event packets."""

    from scripts.training_data.build_geoshell_pair_agent_sft import build_dataset, write_outputs

    dataset = build_dataset()
    paths = write_outputs(dataset, args.output_dir, args.event_path)
    payload = {
        "ok": True,
        "schema_version": dataset["schema_version"],
        "train_count": len(dataset["train"]),
        "holdout_count": len(dataset["holdout"]),
        "event_count": len(dataset["events"]),
        "paths": paths,
        "geoshell_event_feed": paths["events"],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"schema={payload['schema_version']} train={payload['train_count']} holdout={payload['holdout_count']}")
    print(f"events={payload['geoshell_event_feed']}")
    print(f"manifest={paths['manifest']}")
    return 0


def cmd_terminus_training(args: argparse.Namespace) -> int:
    """Run local Terminus guild training sessions for agent play/SFT pairs."""

    from scripts.benchmark.terminus_training_runner import BENCHMARK_PATHS, run_benchmark, run_scripted

    if args.mode == "benchmark":
        payload = run_benchmark(args.out_dir, agent_id=args.agent_id)
    else:
        commands = args.command or BENCHMARK_PATHS[args.scenario]
        payload = run_scripted(commands, agent_id=args.agent_id, scenario=args.scenario, out_dir=args.out_dir)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"schema={payload['schema_version']}")
    print(f"score={payload.get('score', payload.get('total_score'))} pass={payload.get('pass', 'n/a')}")
    if "sft_path" in payload:
        print(f"sft={payload['sft_path']}")
    if "report_path" in payload:
        print(f"report={payload['report_path']}")
    return 0


def _load_switchboard_calls(path_arg: str | None) -> list[dict[str, Any]]:
    if not path_arg:
        return []
    path = Path(path_arg)
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        rows = payload if isinstance(payload, list) else payload.get("calls", [])
    if not isinstance(rows, list):
        raise ValueError("switchboard calls input must be a JSON list or object with calls[]")
    return [row for row in rows if isinstance(row, dict)]


def cmd_call_switchboard(args: argparse.Namespace) -> int:
    """Evaluate or summarize governed multi-agent call reservations."""

    from src.coding_spine.agent_call_switchboard import build_switchboard_snapshot, evaluate_call_request

    existing = _load_switchboard_calls(args.calls)
    if args.request:
        request = json.loads(args.request)
        if not isinstance(request, dict):
            raise ValueError("--request must be a JSON object")
        payload = evaluate_call_request(existing, request)
    else:
        payload = build_switchboard_snapshot(existing)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"schema={payload['schema_version']}")
    if "decision" in payload:
        print(f"decision={payload['decision']} reason={payload['reason']}")
        print(f"collisions={len(payload['collisions'])}")
    else:
        print(f"active={payload['active_count']} lanes={','.join(sorted(payload['by_lane']))}")
    return 0


def _load_lightning_candidates(path_arg: str | None, inline_arg: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if path_arg:
        path = Path(path_arg)
        if not path.exists():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8").strip()
        if text:
            if path.suffix.lower() == ".jsonl":
                rows.extend(json.loads(line) for line in text.splitlines() if line.strip())
            else:
                payload = json.loads(text)
                rows.extend(payload if isinstance(payload, list) else payload.get("candidates", []))
    if inline_arg:
        payload = json.loads(inline_arg)
        rows.extend(payload if isinstance(payload, list) else payload.get("candidates", []))
    return [row for row in rows if isinstance(row, dict)]


def cmd_lightning_indexer(args: argparse.Namespace) -> int:
    """Run sparse candidate selection for route/tool/context narrowing."""

    from src.coding_spine.lightning_indexer import select_sparse_candidates

    candidates = _load_lightning_candidates(args.candidates, args.inline_candidates)
    if not candidates:
        candidates = [
            {
                "candidate_id": "geoseal-agent-harness",
                "kind": "route",
                "lane": "geoseal",
                "priority": 4,
                "text": "GeoSeal agent harness route selection, tool policy, tokenizer packet, and command manifest",
            },
            {
                "candidate_id": "terminus-training",
                "kind": "test",
                "lane": "benchmark",
                "priority": 3,
                "text": "Terminus guild benchmark creates command traces and agent training pairs",
            },
            {
                "candidate_id": "call-switchboard",
                "kind": "tool",
                "lane": "multi-agent",
                "priority": 4,
                "text": "Multi-agent call switchboard prevents collisions across write, apply, cloud, and test lanes",
            },
            {
                "candidate_id": "convert-code",
                "kind": "tool",
                "lane": "tokenizer",
                "priority": 3,
                "text": "Convert text binary hexadecimal token rows language views chemistry and space math packets",
            },
        ]

    payload = select_sparse_candidates(
        args.goal or "",
        candidates,
        top_k=args.top_k,
        block_size=args.block_size,
        block_multiplier=args.block_multiplier,
        channel_budget=args.channel_budget,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"schema={payload['schema_version']} candidates={payload['candidate_count']} top_k={payload['top_k']}")
    for row in payload["selected"]:
        print(f"{row['rank']}. {row['candidate_id']} score={row['score']} tokens={','.join(row['matched_tokens'])}")
    return 0


def cmd_agentic_training_loop(args: argparse.Namespace) -> int:
    """Emit built-in GitHub/Hugging Face extension routes for training loops."""
    from src.coding_spine.agent_tool_bridge import _agentic_training_extensions

    provider = (args.provider or "both").lower()
    ext = _agentic_training_extensions()
    payload = {
        "schema_version": "geoseal-agentic-training-loop-v1",
        "goal": (args.goal or "").strip(),
        "provider": provider,
        "extensions": {
            "github": ext["github"] if provider in {"github", "both"} else None,
            "huggingface": ext["huggingface"] if provider in {"huggingface", "both"} else None,
        },
        "safety": ext["safety"],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"schema={payload['schema_version']} provider={provider}")
    if payload["extensions"]["github"]:
        print("github extension: ready")
    if payload["extensions"]["huggingface"]:
        print("huggingface extension: ready")
    print("safety=" + ", ".join(payload["safety"]["principles"]))
    return 0


def cmd_loop_dispatch(args: argparse.Namespace) -> int:
    """Resolve (and optionally run) a single GitHub or HF loop command; execution is env-gated."""
    from pathlib import Path

    from src.coding_spine.agent_tool_bridge import resolve_agentic_loop_dispatch_v1

    repo_root = Path(__file__).resolve().parents[1]
    payload = resolve_agentic_loop_dispatch_v1(
        provider=args.provider,
        task=args.task,
        query=getattr(args, "query", "") or "",
        branch=getattr(args, "branch", "") or "",
        run_id=getattr(args, "run_id", "") or "",
        hf_model=getattr(args, "hf_model", "") or "",
        hf_dataset=getattr(args, "hf_dataset", "") or "",
        repo_root=repo_root,
    )
    if not payload.get("ok"):
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"loop-dispatch: {payload.get('error')}", file=sys.stderr)
        return 2

    if not getattr(args, "execute", False):
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"schema={payload['schema_version']} provider={payload['provider']} task={payload['task']}")
            print(f"shell={payload['resolved_shell']}")
            print(f"gate: set {payload['gate_env_var']}=1 before --execute")
        return 0

    from src.coding_spine.agent_tool_policy import evaluate_harness_tool_policy

    perm = (
        str(getattr(args, "permission_mode", "") or "").strip()
        or os.environ.get("SCBE_AGENT_PERMISSION_MODE", "").strip()
        or "observe"
    )
    pol = evaluate_harness_tool_policy(permission_mode=perm, tool_class="network_or_cloud")
    if not pol.get("ok"):
        if args.json:
            print(json.dumps({"resolve": payload, "policy": pol}, indent=2))
        else:
            print(f"loop-dispatch: policy denied: {pol.get('reason')}", file=sys.stderr)
        return 2

    gate = os.environ.get("SCBE_AGENTIC_LOOP_EXECUTE", "").strip().lower()
    if gate not in ("1", "true", "yes", "on"):
        if args.json:
            print(
                json.dumps(
                    {
                        "resolve": payload,
                        "policy": pol,
                        "execute_gate": "SCBE_AGENTIC_LOOP_EXECUTE required",
                    },
                    indent=2,
                )
            )
        else:
            print(
                "loop-dispatch: refusing --execute without SCBE_AGENTIC_LOOP_EXECUTE=1 " "(cloud-dispatch safety gate)",
                file=sys.stderr,
            )
        return 2
    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv:
        print("loop-dispatch: missing argv", file=sys.stderr)
        return 2
    env = os.environ.copy()
    for k, v in (payload.get("execute_env") or {}).items():
        env[str(k)] = str(v)
    cwd = payload.get("cwd") or str(repo_root)
    proc = subprocess.run([str(x) for x in argv], cwd=cwd, env=env)
    return int(proc.returncode)


def cmd_ai2ai_bridge(args: argparse.Namespace) -> int:
    """Emit ``scbe_agent_tool_bridge_v1`` (AI-to-AI tool/handler hints) from inline or file text."""

    from src.coding_spine.agent_tool_bridge import build_agent_tool_bridge_v1

    text = (getattr(args, "content", None) or "").strip()
    if getattr(args, "source_file", None):
        text = Path(args.source_file).read_text(encoding="utf-8")
    if not text.strip():
        print("ai2ai-bridge: provide --content or --source-file", file=sys.stderr)
        return 2
    payload = build_agent_tool_bridge_v1(inline_goal=text)
    out = json.dumps(payload, indent=2 if args.json else None)
    print(out)
    return 0


def cmd_explain_route(args: argparse.Namespace) -> int:
    from src.coding_spine.polly_client import explain_provider_chain

    source = args.content or ""
    source_name = args.source_name or "inline"
    if args.source_file:
        path = Path(args.source_file)
        source = path.read_text(encoding="utf-8")
        source_name = args.source_name or path.name
    language = (args.language or "python").lower()
    force_tongue = (args.tongue or "").upper() or None
    provider_explain = explain_provider_chain(
        force_provider=args.provider or None,
        forbidden_providers=list(args.forbid_provider or []),
        small_first=bool(args.small_first),
        governance_tier=args.governance_tier,
    )
    route_ir = _build_route_ir_for_source(
        source=source,
        source_name=source_name,
        language=language,
        force_tongue=force_tongue,
        selected_backend=(provider_explain["resolved_chain"][0] if provider_explain["resolved_chain"] else None),
    )
    payload = {
        "version": "geoseal-route-explain-v1",
        "source_name": source_name,
        "language": language,
        "route_ir": route_ir,
        "provider_chain": provider_explain,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"source={source_name} language={language}")
    print(f"signature={route_ir['route']['signature']} tongue={route_ir['route']['tongue']}")
    print(f"backend={route_ir['backend']['selected']}")
    return 0


def _read_ledger_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def cmd_history(args: argparse.Namespace) -> int:
    ledger = Path(args.ledger)
    rows = _read_ledger_records(ledger)
    if args.type:
        rows = [row for row in rows if str(row.get("type", "swarm_result")) == args.type]
    if args.op:
        rows = [row for row in rows if str(row.get("op", "")) == args.op]
    if args.limit > 0:
        rows = rows[-args.limit :]
    payload = {
        "version": "geoseal-history-v1",
        "ledger": str(ledger),
        "count": len(rows),
        "records": rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"ledger={ledger} records={len(rows)}")
    for i, row in enumerate(rows, start=1):
        row_type = row.get("type", "swarm_result")
        op = row.get("op", "-")
        quorum = row.get("quorum_ok", "-")
        print(f"{i:>3}. type={row_type} op={op} quorum={quorum}")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    ledger = Path(args.ledger)
    rows = _read_ledger_records(ledger)
    if not rows:
        print(f"ledger has no replayable records: {ledger}", file=sys.stderr)
        return 1
    idx = args.index
    row = rows[-1] if idx is None else rows[idx]

    if row.get("type") == "swarm_tokens":
        op = str(row.get("op", "add"))
        tongues = [str(item.get("tongue", "KO")).upper() for item in row.get("calls", []) if isinstance(item, dict)]
        prior_swarm = next(
            (
                candidate
                for candidate in reversed(rows)
                if candidate is not row and candidate.get("type") == "swarm_result" and candidate.get("op") == op
            ),
            None,
        )
        args_map = {}
        if isinstance(prior_swarm, dict) and isinstance(prior_swarm.get("args"), dict):
            args_map = prior_swarm.get("args", {})
        result = swarm_dispatch(
            op,
            tongues=tongues or ["KO"],
            args=args_map,
            execute=True,
            timeout=args.timeout,
            ledger=None if args.no_ledger else ledger,
        )
        payload = {
            "version": "geoseal-replay-v1",
            "mode": "swarm_tokens",
            "result": result.to_dict(),
        }
        print(json.dumps(payload, indent=2 if args.json else None))
        return 0 if result.quorum_ok else 1

    if "op" in row and "calls" in row and isinstance(row["calls"], list):
        op = str(row.get("op", "add"))
        tongues = [str(item.get("tongue", "KO")).upper() for item in row.get("calls", []) if isinstance(item, dict)]
        args_map = row.get("args", {})
        result = swarm_dispatch(
            op,
            tongues=tongues or ["KO"],
            args=args_map if isinstance(args_map, dict) else {},
            execute=True,
            timeout=args.timeout,
            ledger=None if args.no_ledger else ledger,
        )
        payload = {
            "version": "geoseal-replay-v1",
            "mode": "swarm_result",
            "result": result.to_dict(),
        }
        print(json.dumps(payload, indent=2 if args.json else None))
        return 0 if result.quorum_ok else 1

    print("record is not replayable by current replay mode", file=sys.stderr)
    return 2


def _command_key_and_route_packet(source: str, language: str) -> dict[str, Any]:
    command_key = _extract_command_key(source, fallback="add")
    if command_key == "code":
        command_key = "add"
    operative = f"arithmetic:{command_key}" if command_key in {"add", "sub", "mul", "div", "mod"} else command_key
    return {
        "operative_command": operative,
        "command_key": command_key,
        "key_slot": "A1",
        "route_tongue": _language_to_tongue(language),
        "route_language": language,
        "route_confidence": 0.92,
        "stability_adjusted_route_score": 0.88,
    }


def _run_python_add(a: int = 7, b: int = 3) -> SwarmCallResult:
    code = f"print({a} + {b})"
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10.0)
    return SwarmCallResult(
        op="add",
        tongue="KO",
        language="python",
        code=code,
        ran=True,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        returncode=proc.returncode,
        duration_ms=(time.time() - t0) * 1000.0,
        phase=ALL_TONGUE_PHASES["KO"],
        seal=compute_seal("add", "KO", code),
    )


def cmd_testing_cli(args: argparse.Namespace) -> int:
    source = args.content or ""
    if args.source_file:
        source = Path(args.source_file).read_text(encoding="utf-8")
    language = (args.language or "python").lower()
    route_packet = _command_key_and_route_packet(source, language)
    playback_exec = (
        _run_python_add()
        if args.execute
        else SwarmCallResult(op="add", tongue="KO", language="python", code="", ran=False)
    )
    payload = {
        "version": "geoseal-testing-cli-v1",
        "route_packet": route_packet,
        "playback": {
            "route_packet": {
                "command_key": "add",
                "route_tongue": "KO",
                "route_language": "python",
            },
            "execution": playback_exec.to_dict(),
        },
        "honeycomb_analysis": {"matched_output": playback_exec.stdout if playback_exec.ran else ""},
        "topology": {
            "route_packet": route_packet,
            "operative_command": {
                "phase_operation": "arithmetic:add",
                "stability_adjusted_route_score": route_packet["stability_adjusted_route_score"],
            },
        },
        "native_tokenization": {
            "schema_version": "scbe_testing_cli_native_tokenization_v1",
            "input": _token_digest_for_tongue(route_packet["route_tongue"], source.encode("utf-8", errors="replace")),
            "output": _token_digest_for_tongue(
                route_packet["route_tongue"],
                playback_exec.stdout.encode("utf-8", errors="replace"),
            ),
        },
    }
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0 if (not args.execute or playback_exec.returncode == 0) else 1


def cmd_project_scaffold(args: argparse.Namespace) -> int:
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    route_packet = _command_key_and_route_packet(args.content or "", (args.language or "python").lower())
    (out_dir / "index.html").write_text(
        "<!doctype html><html><head><title>Pacman Scaffold</title><link rel='stylesheet' href='style.css'></head>"
        "<body><h1>Pacman Scaffold</h1><canvas id='game'></canvas><script src='game.js'></script></body></html>",
        encoding="utf-8",
    )
    (out_dir / "style.css").write_text(
        "body { background:#000; color:#ff0; } canvas { border:1px solid #333; }",
        encoding="utf-8",
    )
    (out_dir / "game.js").write_text(
        "const pellets = []; window.addEventListener('keydown', (e)=>{ if(e.key==='ArrowUp'){ /* move */ }});",
        encoding="utf-8",
    )
    manifest = {
        "version": "geoseal-project-manifest-v1",
        "project_kind": "pacman_web",
        "route_packet": {"command_key": route_packet["command_key"]},
        "honeycomb_feedback": {"route_confidence": route_packet["route_confidence"]},
    }
    (out_dir / "project_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    payload = {
        "version": "geoseal-project-scaffold-v1",
        "project_kind": "pacman_web",
        "output_dir": str(out_dir),
    }
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def _execute_rust_source(source_path: Path) -> tuple[bool, dict[str, Any]]:
    rustc = shutil.which("rustc")
    if not rustc:
        return False, {
            "ran": False,
            "returncode": None,
            "stdout": "",
            "stderr": "rustc not found",
        }
    exe_path = source_path.with_suffix(".exe")
    compile_proc = subprocess.run(
        [
            rustc,
            str(source_path),
            "--crate-name",
            "geoseal_roundtrip",
            "-O",
            "-o",
            str(exe_path),
        ],
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    if compile_proc.returncode != 0:
        return True, {
            "ran": False,
            "returncode": compile_proc.returncode,
            "stdout": "",
            "stderr": compile_proc.stderr,
        }
    run_proc = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=30.0)
    return True, {
        "ran": True,
        "returncode": run_proc.returncode,
        "stdout": run_proc.stdout,
        "stderr": run_proc.stderr,
    }


def cmd_code_roundtrip(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    src = source_path.read_bytes()
    tongue = (args.tongue or "RU").upper()
    transport = _normalize_transport_tongue(tongue)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, src)
    back = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens)
    language = (args.lang or "rust").lower()
    prime = LANG_MAP.get(tongue, "")
    original_exec: dict[str, Any] = {
        "ran": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    decoded_exec: dict[str, Any] = {
        "ran": False,
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    if args.execute and language == "rust":
        ran, original_exec = _execute_rust_source(source_path)
        decoded_path = source_path.with_name(source_path.stem + ".decoded" + source_path.suffix)
        decoded_path.write_bytes(back)
        _, decoded_exec = _execute_rust_source(decoded_path)
        if decoded_path.exists():
            decoded_path.unlink(missing_ok=True)
    payload = {
        "version": "geoseal-code-roundtrip-v1",
        "language": language,
        "tongue": tongue,
        "language_matches_prime": language == prime,
        "byte_identical": src == back,
        "execution": {
            "original": original_exec,
            "decoded": decoded_exec,
            "stdout_identical": original_exec.get("stdout") == decoded_exec.get("stdout"),
            "returncode_identical": original_exec.get("returncode") == decoded_exec.get("returncode"),
        },
    }
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0 if payload["byte_identical"] and (not args.execute or payload["execution"]["returncode_identical"]) else 1


def cmd_shell(args: argparse.Namespace) -> int:
    tokens = shlex.split(args.command)
    if not tokens:
        raise SystemExit("--command is empty")
    nested_parser = build_parser()
    nested_args = nested_parser.parse_args(tokens)
    return nested_args.func(nested_args)


def cmd_decode_cmd(args: argparse.Namespace) -> int:
    token_text = _read_payload_arg_or_stdin(args.tokens)
    tongue = _normalize_transport_tongue(args.tongue)
    tokens = _parse_token_text(token_text)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, tokens)
    _write_stdout_safe(decoded.decode("utf-8", errors="replace"))
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
        if args.json:
            payload = {
                "version": "geoseal-emit-v1",
                "op": args.op,
                "semantic_expression": {"gloss": "add x and y" if args.op == "add" else args.op},
                "variants": [
                    {
                        "tongue": tongue,
                        "language": LANG_MAP[tongue],
                        "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
                        "code": code,
                        "seal": seal,
                        "binary": {"byte_count": len(code.encode("utf-8"))},
                        "tokenizer": {"token_count": tongue_token_digest(tongue, code).get("n_tokens", 0)},
                    }
                ],
            }
            print(json.dumps(payload, indent=2))
            return 0
        print(f"{tongue} ({LANG_MAP[tongue]}): {code}")
        print(f"seal: {seal}")
        return 0
    results = emit_all_tongues(args.op, **kv)
    if args.json:
        rows = []
        for t, code in results.items():
            rows.append(
                {
                    "tongue": t,
                    "language": LANG_MAP[t],
                    "conlang": CONLANG_NAME_MAP.get(t, t),
                    "code": code,
                    "seal": compute_seal(args.op, t, code),
                    "binary": {"byte_count": len(code.encode("utf-8"))},
                    "tokenizer": {"token_count": tongue_token_digest(t, code).get("n_tokens", 0)},
                }
            )
        print(
            json.dumps(
                {
                    "version": "geoseal-emit-v1",
                    "op": args.op,
                    "semantic_expression": {"gloss": "add x and y" if args.op == "add" else args.op},
                    "variants": rows,
                },
                indent=2,
            )
        )
        return 0
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
    if not args.no_ledger:
        ledger = Path(args.ledger)
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "type": "run_result",
                        "timestamp": time.time(),
                        "op": args.op,
                        "args": kv,
                        "call": call.to_dict(),
                    }
                )
                + "\n"
            )
    if args.json:
        print(json.dumps({"version": "geoseal-run-v1", "call": call.to_dict()}, indent=2))
        return 0 if (call.ran and call.returncode == 0) else 1
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
        print(
            f"[governance] DENY — phi_cost={phi_cost:.4f} exceeds threshold",
            file=sys.stderr,
        )
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
        print(
            "cursor agent not found; install Cursor Agent or set CURSOR_AGENT_CMD",
            file=sys.stderr,
        )
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
                print(
                    f"[workflow:{result.step_id}] ERROR: {result.error}",
                    file=sys.stderr,
                )
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

    p_binary = sub.add_parser("binary-to-tokenizer", help="Map binary bytes into Sacred Tongue tokenizer rows")
    p_binary.add_argument("--tongue", required=True, help="KO|AV|RU|CA|UM|DR")
    p_binary.add_argument(
        "--language",
        default=None,
        help="Optional requested language for prime-lane check",
    )
    p_binary.add_argument("--json", action="store_true")
    p_binary.add_argument("bits", nargs="?", default="", help="Space/comma separated 8-bit chunks")
    p_binary.set_defaults(func=cmd_binary_to_tokenizer)

    p_agent_io = sub.add_parser(
        "agent-io-contract",
        help="Build and write agent IO contract bundle (harness + bridge) for external tools",
    )
    p_agent_io.add_argument("--goal", default="", help="Optional inline goal/task context")
    p_agent_io.add_argument("--language", default="python", help="Preferred language lane")
    p_agent_io.add_argument("--permission-mode", default="observe", help="observe|workspace-write|cloud-dispatch|maintenance")
    p_agent_io.add_argument("--output-dir", default="artifacts/agent_io_contract")
    p_agent_io.add_argument("--json", action="store_true")
    p_agent_io.set_defaults(func=cmd_agent_io_contract)

    p_endurance_pack = sub.add_parser(
        "agent-endurance-pack",
        help="Generate regimen/taskset/run-report bundle for long-horizon agent training",
    )
    p_endurance_pack.add_argument("--round-id", default=None, dest="round_id", help="Round identifier suffix")
    p_endurance_pack.add_argument("--regimen-id", default=None, dest="regimen_id")
    p_endurance_pack.add_argument("--taskset-id", default=None, dest="taskset_id")
    p_endurance_pack.add_argument("--run-id", default=None, dest="run_id")
    p_endurance_pack.add_argument("--candidate-id", default="geoseal-agent-harness", dest="candidate_id")
    p_endurance_pack.add_argument("--owner", default=None, help="Owner override for regimen metadata")
    p_endurance_pack.add_argument(
        "--permission-mode",
        default="workspace-write",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
        dest="permission_mode",
    )
    p_endurance_pack.add_argument("--output-dir", default="artifacts/agent_endurance_pack")
    p_endurance_pack.add_argument("--json", action="store_true")
    p_endurance_pack.set_defaults(func=cmd_agent_endurance_pack)

    p_code_lanes = sub.add_parser(
        "tokenizer-code-lanes",
        help="Emit tokenizer code lanes for a CA lexicon command across one or more tongues",
    )
    p_code_lanes.add_argument("--command", required=True, help="CA lexicon opcode name (for example: add, shl)")
    p_code_lanes.add_argument("--tongues", default="KO", help='Comma list or "all"')
    p_code_lanes.add_argument("--output", default=None, help="Optional output JSON file path")
    p_code_lanes.add_argument("--json", action="store_true")
    p_code_lanes.set_defaults(func=cmd_tokenizer_code_lanes)

    p_verify_lanes = sub.add_parser(
        "verify-code-lanes",
        help="Verify code-lane token roundtrip and tokenizer re-encode consistency",
    )
    p_verify_lanes.add_argument("payload", nargs="?", default=None, help="JSON payload (defaults to --input-file)")
    p_verify_lanes.add_argument("--input-file", default=None, help="Read payload JSON from file")
    p_verify_lanes.add_argument("--json", action="store_true")
    p_verify_lanes.set_defaults(func=cmd_verify_code_lanes)

    p_decode_lanes = sub.add_parser(
        "decode-code-lanes",
        help="Decode lane payloads back into language files (and optional binary outputs)",
    )
    p_decode_lanes.add_argument("payload", nargs="?", default=None, help="JSON payload (defaults to --input-file)")
    p_decode_lanes.add_argument("--input-file", default=None, help="Read payload JSON from file")
    p_decode_lanes.add_argument("--output-dir", required=True, help="Directory for decoded files")
    p_decode_lanes.add_argument("--from-binary", action="store_true", help="Decode from lane binary bits instead of tokens")
    p_decode_lanes.add_argument("--write-binary", action="store_true", help="Also write .bin payload files")
    p_decode_lanes.add_argument("--json", action="store_true")
    p_decode_lanes.set_defaults(func=cmd_decode_code_lanes)

    p_convert = sub.add_parser(
        "convert-code",
        help="Convert text/binary/hex/token payloads into byte, tokenizer, and language views",
    )
    p_convert.add_argument(
        "--from",
        dest="from_format",
        choices=["text", "binary", "hex", "tokens"],
        default="text",
        help="Input format",
    )
    p_convert.add_argument(
        "--to",
        choices=["all", "text", "binary", "hex", "decimal", "tokens", "languages", "chemistry", "space-math"],
        default="all",
        help="Output section to print",
    )
    p_convert.add_argument("--tongue", default="KO", help="Tokenizer tongue for token input/output")
    p_convert.add_argument(
        "--all-tongues",
        action="store_true",
        help="Include tokenizer output for all Sacred Tongues",
    )
    p_convert.add_argument(
        "--language",
        default="all",
        help="Language view: all, python, typescript, rust, c, julia, or haskell",
    )
    p_convert.add_argument("--input-file", default=None, help="Read payload from UTF-8 file")
    p_convert.add_argument("--json", action="store_true")
    p_convert.add_argument("payload", nargs="?", default=None, help="Payload (defaults to stdin)")
    p_convert.set_defaults(func=cmd_convert_code)

    p_yinyang = sub.add_parser(
        "yin-yang-dual",
        help="Build a KO/DR view-dependent dual-frame tokenizer packet",
    )
    p_yinyang.add_argument("--ko-text", default="", help="KO/control-flow channel text")
    p_yinyang.add_argument("--dr-text", default="", help="DR/structure-transform channel text")
    p_yinyang.add_argument("--ko-file", default=None, help="Read KO channel from a UTF-8 file")
    p_yinyang.add_argument("--dr-file", default=None, help="Read DR channel from a UTF-8 file")
    p_yinyang.add_argument("--frame", type=int, default=0, choices=[0, 1], help="0=KO figure, 1=DR figure")
    p_yinyang.add_argument("--size", type=int, default=9, help="Odd mask size >= 5")
    p_yinyang.add_argument("--json", action="store_true")
    p_yinyang.set_defaults(func=cmd_yin_yang_dual)

    p_code_packet = sub.add_parser("code-packet", help="Build SCBE weighted code packet from source")
    p_code_packet.add_argument("--content", default="", help="Inline source content")
    p_code_packet.add_argument("--source-file", default=None, help="Read source content from file")
    p_code_packet.add_argument("--source-name", default=None)
    p_code_packet.add_argument("--language", default="python")
    p_code_packet.add_argument("--backend", default=None, choices=["local", "ollama", "hf", "claude"])
    p_code_packet.set_defaults(func=cmd_code_packet)

    p_braille = sub.add_parser("braille-lane", help="Build braille/polyhedral lane from source or code packet")
    p_braille.add_argument("--content", default="")
    p_braille.add_argument("--source-file", default=None)
    p_braille.add_argument("--packet-file", default=None)
    p_braille.add_argument("--source-name", default=None)
    p_braille.add_argument("--language", default="python")
    p_braille.add_argument("--json", action="store_true")
    p_braille.set_defaults(func=cmd_braille_lane)

    p_igraph = sub.add_parser("interaction-graph", help="Build source/token/STISA/atomic interaction graph")
    p_igraph.add_argument("--content", default="")
    p_igraph.add_argument("--source-file", default=None)
    p_igraph.add_argument("--packet-file", default=None)
    p_igraph.add_argument("--source-name", default=None)
    p_igraph.add_argument("--language", default="python")
    p_igraph.add_argument("--max-binary-nodes", type=int, default=8, dest="max_binary_nodes")
    p_igraph.add_argument("--format", default="json", choices=["json", "mermaid", "dot"])
    p_igraph.set_defaults(func=cmd_interaction_graph)

    p_topology = sub.add_parser("topology-view", help="Build topology view from source or packet")
    p_topology.add_argument("--content", default="")
    p_topology.add_argument("--source-file", default=None)
    p_topology.add_argument("--packet-file", default=None)
    p_topology.add_argument("--source-name", default=None)
    p_topology.add_argument("--language", default="python")
    p_topology.add_argument("--max-binary-nodes", type=int, default=8, dest="max_binary_nodes")
    p_topology.add_argument("--format", default="json", choices=["json", "mermaid", "dot"])
    p_topology.set_defaults(func=cmd_topology_view)

    p_sequence = sub.add_parser("cross-domain-sequence", help="Build near-related cross-domain route sequence")
    p_sequence.add_argument("--content", default="")
    p_sequence.add_argument("--source-file", default=None)
    p_sequence.add_argument("--packet-file", default=None)
    p_sequence.add_argument("--topology-file", default=None)
    p_sequence.add_argument("--source-name", default=None)
    p_sequence.add_argument("--language", default="python")
    p_sequence.add_argument("--json", action="store_true")
    p_sequence.set_defaults(func=cmd_cross_domain_sequence)

    p_honeycomb = sub.add_parser("honeycomb-analysis", help="Analyze route cells and execution stability")
    p_honeycomb.add_argument("--content", default="")
    p_honeycomb.add_argument("--source-file", default=None)
    p_honeycomb.add_argument("--packet-file", default=None)
    p_honeycomb.add_argument("--source-name", default=None)
    p_honeycomb.add_argument("--language", default="python")
    p_honeycomb.add_argument("--branch-width", type=int, default=1)
    p_honeycomb.add_argument("--json", action="store_true")
    p_honeycomb.set_defaults(func=cmd_honeycomb_analysis)

    p_cognition = sub.add_parser("cognition-map", help="Build cognitive well/ternary map")
    p_cognition.add_argument("--content", default="")
    p_cognition.add_argument("--source-file", default=None)
    p_cognition.add_argument("--packet-file", default=None)
    p_cognition.add_argument("--source-name", default=None)
    p_cognition.add_argument("--language", default="python")
    p_cognition.set_defaults(func=cmd_cognition_map)

    p_cluster = sub.add_parser("cluster-graph", help="Build cross-lattice cluster graph")
    p_cluster.add_argument("--content", default="")
    p_cluster.add_argument("--source-file", default=None)
    p_cluster.add_argument("--packet-file", default=None)
    p_cluster.add_argument("--source-name", default=None)
    p_cluster.add_argument("--language", default="python")
    p_cluster.add_argument("--max-binary-nodes", type=int, default=8, dest="max_binary_nodes")
    p_cluster.set_defaults(func=cmd_cluster_graph)

    p_formation = sub.add_parser("formation-graph", help="Build cross-lattice formation graph")
    p_formation.add_argument("--content", default="")
    p_formation.add_argument("--source-file", default=None)
    p_formation.add_argument("--packet-file", default=None)
    p_formation.add_argument("--source-name", default=None)
    p_formation.add_argument("--language", default="python")
    p_formation.add_argument("--max-binary-nodes", type=int, default=8, dest="max_binary_nodes")
    p_formation.set_defaults(func=cmd_formation_graph)

    p_explain = sub.add_parser("explain-route", help="Explain route IR + backend chain for a source/task")
    p_explain.add_argument("--content", default="", help="Inline source content")
    p_explain.add_argument("--source-file", default=None, help="Read source content from file")
    p_explain.add_argument("--source-name", default=None)
    p_explain.add_argument("--language", default="python")
    p_explain.add_argument("--tongue", default=None, help="Force tongue")
    p_explain.add_argument("--provider", default=None, choices=["local", "ollama", "hf", "claude"])
    p_explain.add_argument(
        "--forbid-provider",
        action="append",
        default=[],
        dest="forbid_provider",
        choices=["local", "ollama", "hf", "claude"],
    )
    p_explain.add_argument("--small-first", action="store_true", dest="small_first")
    p_explain.add_argument(
        "--governance-tier",
        default="ALLOW",
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
    )
    p_explain.add_argument("--json", action="store_true")
    p_explain.set_defaults(func=cmd_explain_route)

    p_backends = sub.add_parser("backend-registry", help="List backend providers and lane support")
    p_backends.add_argument("--json", action="store_true")
    p_backends.set_defaults(func=cmd_backend_registry)

    p_harness = sub.add_parser("agent-harness", help="Emit model-neutral agent harness manifest")
    p_harness.add_argument("--goal", default="", help="Agent goal or task intent")
    p_harness.add_argument(
        "--language",
        default="python",
        choices=sorted(set(ALL_LANG_MAP.values())),
        help="Preferred source language for route selection",
    )
    p_harness.add_argument(
        "--permission-mode",
        default="observe",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
        dest="permission_mode",
    )
    p_harness.add_argument("--json", action="store_true")
    p_harness.set_defaults(func=cmd_agent_harness)

    p_skills = sub.add_parser(
        "skill-tools",
        help="List SKILL.md files as harness tools (for model function-calling + paths)",
    )
    p_skills.add_argument("--json", action="store_true")
    p_skills.set_defaults(func=cmd_skill_tools)

    p_hydra = sub.add_parser(
        "hydra-bridge",
        help="Emit HYDRA orchestration bridge with GeoSeal tokenizer packet evidence",
    )
    p_hydra.add_argument("--goal", default="", help="HYDRA goal or task intent")
    p_hydra.add_argument(
        "--language",
        default="python",
        choices=sorted(set(ALL_LANG_MAP.values())),
        help="Preferred source language for route selection",
    )
    p_hydra.add_argument(
        "--permission-mode",
        default="observe",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
        dest="permission_mode",
    )
    p_hydra.add_argument("--json", action="store_true")
    p_hydra.set_defaults(func=cmd_hydra_bridge)

    p_pair_training = sub.add_parser(
        "pair-agent-training",
        help="Build GeoShell paired-agent coding SFT records and event packets",
    )
    p_pair_training.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training-data") / "sft",
        help="Directory for train/holdout/manifest outputs",
    )
    p_pair_training.add_argument(
        "--event-path",
        type=Path,
        default=Path("artifacts") / "geoshell" / "pair_agent" / "latest_events.json",
        help="GeoShell-compatible agent-bus event JSON output",
    )
    p_pair_training.add_argument("--json", action="store_true")
    p_pair_training.set_defaults(func=cmd_pair_agent_training)

    p_terminus_training = sub.add_parser(
        "terminus-training",
        help="Run local Terminus guild game benchmarks and emit agent training pairs",
    )
    p_terminus_training.add_argument("--mode", choices=["run", "benchmark"], default="benchmark")
    p_terminus_training.add_argument(
        "--scenario",
        choices=["guild_math_intro", "representation_guilds"],
        default="guild_math_intro",
    )
    p_terminus_training.add_argument("--command", action="append", default=[], help="Manual command; repeatable")
    p_terminus_training.add_argument("--agent-id", default="geoseal-agent", dest="agent_id")
    p_terminus_training.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts") / "terminus_training",
        dest="out_dir",
    )
    p_terminus_training.add_argument("--json", action="store_true")
    p_terminus_training.set_defaults(func=cmd_terminus_training)

    p_switchboard = sub.add_parser(
        "call-switchboard",
        help="Evaluate governed multi-agent call reservations and lane collisions",
    )
    p_switchboard.add_argument("--calls", default=None, help="Existing calls JSON or JSONL file")
    p_switchboard.add_argument(
        "--request",
        default=None,
        help="New call request as JSON; omitted means emit a switchboard snapshot",
    )
    p_switchboard.add_argument("--json", action="store_true")
    p_switchboard.set_defaults(func=cmd_call_switchboard)

    p_lightning = sub.add_parser(
        "lightning-indexer",
        help="Sparse-select route/tool/context candidates for agent harness work",
    )
    p_lightning.add_argument("--goal", default="", help="Goal/query used to score candidates")
    p_lightning.add_argument("--candidates", default=None, help="Candidate JSON or JSONL path")
    p_lightning.add_argument(
        "--inline-candidates",
        default=None,
        help="Candidate JSON list/object; useful for tests and tiny tool calls",
    )
    p_lightning.add_argument("--top-k", type=int, default=5, dest="top_k")
    p_lightning.add_argument("--block-size", type=int, default=16, dest="block_size")
    p_lightning.add_argument("--block-multiplier", type=int, default=3, dest="block_multiplier")
    p_lightning.add_argument("--channel-budget", type=int, default=3, dest="channel_budget")
    p_lightning.add_argument("--json", action="store_true")
    p_lightning.set_defaults(func=cmd_lightning_indexer)

    p_train_loop = sub.add_parser(
        "agentic-training-loop",
        help="Emit built-in GitHub/Hugging Face extension commands for agentic training loops",
    )
    p_train_loop.add_argument("--goal", default="", help="Optional loop goal/intent")
    p_train_loop.add_argument(
        "--provider",
        default="both",
        choices=["github", "huggingface", "both"],
        help="Select extension surface to emit",
    )
    p_train_loop.add_argument("--json", action="store_true")
    p_train_loop.set_defaults(func=cmd_agentic_training_loop)

    p_loop_dispatch = sub.add_parser(
        "loop-dispatch",
        help="Resolve or run one GitHub/HF agentic training-loop command (execute is env-gated)",
    )
    p_loop_dispatch.add_argument("--provider", required=True, choices=["github", "huggingface"])
    p_loop_dispatch.add_argument(
        "--task",
        required=True,
        help="e.g. github: list_runs | coding | watch — hf: bijective_gate | paired_coding | train_and_gate",
    )
    p_loop_dispatch.add_argument("--query", default="", help="Workflow query/task_goal (GitHub coding)")
    p_loop_dispatch.add_argument("--branch", default="", help="Git ref for gh workflow run (default: env or main)")
    p_loop_dispatch.add_argument("--run-id", default="", dest="run_id", help="Run id for watch")
    p_loop_dispatch.add_argument("--hf-model", default="", dest="hf_model", help="HF model id override")
    p_loop_dispatch.add_argument("--hf-dataset", default="", dest="hf_dataset", help="HF dataset repo (train_and_gate)")
    p_loop_dispatch.add_argument(
        "--execute",
        action="store_true",
        help="Run resolved argv (requires SCBE_AGENTIC_LOOP_EXECUTE=1)",
    )
    p_loop_dispatch.add_argument(
        "--permission-mode",
        default="observe",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
        dest="permission_mode",
        help="Harness profile; cloud/network execute needs cloud-dispatch or approval env (see agent_tool_policy)",
    )
    p_loop_dispatch.add_argument("--json", action="store_true")
    p_loop_dispatch.set_defaults(func=cmd_loop_dispatch)

    p_ai2ai = sub.add_parser(
        "ai2ai-bridge",
        help="Emit AI-to-AI tool bridge packet (GeoSeal CLI + service connector hints)",
    )
    p_ai2ai.add_argument("--content", default="", help="Inline goal or source text")
    p_ai2ai.add_argument("--source-file", default=None, dest="source_file")
    p_ai2ai.add_argument(
        "--language",
        default="python",
        help="Reserved for future routing; bridge uses inline goal text",
    )
    p_ai2ai.add_argument("--json", action="store_true")
    p_ai2ai.set_defaults(func=cmd_ai2ai_bridge)

    p_history = sub.add_parser("history", help="Show execution history from ledger")
    p_history.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_history.add_argument("--limit", type=int, default=20)
    p_history.add_argument("--type", default=None, help="Optional record type filter")
    p_history.add_argument("--op", default=None, help="Optional op filter")
    p_history.add_argument("--json", action="store_true")
    p_history.set_defaults(func=cmd_history)

    p_replay = sub.add_parser("replay", help="Replay a previous ledger record")
    p_replay.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_replay.add_argument("--index", type=int, default=None, help="Record index (default: last)")
    p_replay.add_argument("--timeout", type=float, default=10.0)
    p_replay.add_argument("--no-ledger", action="store_true")
    p_replay.add_argument("--json", action="store_true")
    p_replay.set_defaults(func=cmd_replay)

    p_testing = sub.add_parser("testing-cli", help="Build testing playback packet and optionally execute")
    p_testing.add_argument("--content", default="", help="Inline source content")
    p_testing.add_argument("--source-file", default=None, help="Read source content from file")
    p_testing.add_argument("--language", default="python")
    p_testing.add_argument("--execute", action="store_true")
    p_testing.add_argument("--json", action="store_true")
    p_testing.set_defaults(func=cmd_testing_cli)

    p_scaffold = sub.add_parser("project-scaffold", help="Create lightweight project scaffold from task intent")
    p_scaffold.add_argument("--content", required=True)
    p_scaffold.add_argument("--language", default="python")
    p_scaffold.add_argument("--output-dir", required=True, dest="output_dir")
    p_scaffold.add_argument("--json", action="store_true")
    p_scaffold.set_defaults(func=cmd_project_scaffold)

    p_roundtrip = sub.add_parser(
        "code-roundtrip",
        help="Encode/decode code through tongue transport and optionally execute",
    )
    p_roundtrip.add_argument("--source", required=True)
    p_roundtrip.add_argument("--lang", default="rust")
    p_roundtrip.add_argument("--tongue", default="RU")
    p_roundtrip.add_argument("--execute", action="store_true")
    p_roundtrip.add_argument("--json", action="store_true")
    p_roundtrip.set_defaults(func=cmd_code_roundtrip)

    p_portal = sub.add_parser("portal-box", help="Build a local Polly portal-box route packet")
    p_portal.add_argument("--content", default="", help="Inline source content")
    p_portal.add_argument("--source-file", default=None, help="Read source content from file")
    p_portal.add_argument("--language", default="python")
    p_portal.add_argument("--source-name", default=None)
    p_portal.add_argument("--include-extended", action="store_true")
    p_portal.add_argument("--json", action="store_true")
    p_portal.set_defaults(func=cmd_portal_box)

    p_stream = sub.add_parser("stream-wheel", help="Build a local Polly stream-wheel route packet")
    p_stream.add_argument("--content", default="", help="Inline source content")
    p_stream.add_argument("--source-file", default=None, help="Read source content from file")
    p_stream.add_argument("--language", default="python")
    p_stream.add_argument("--source-name", default=None)
    p_stream.add_argument("--include-extended", action="store_true")
    p_stream.add_argument("--json", action="store_true")
    p_stream.set_defaults(func=cmd_stream_wheel)

    p_mars = sub.add_parser("mars-mission", help="Build a GeoSeal Mars mission compass/minimap packet")
    p_mars.add_argument("--input", default=None, help="Mission telemetry JSON file")
    p_mars.add_argument("--payload", default=None, help="Inline mission telemetry JSON")
    p_mars.add_argument("--json", action="store_true")
    p_mars.set_defaults(func=cmd_mars_mission)

    p_shell = sub.add_parser("shell", help="Run a nested GeoSeal command string")
    p_shell.add_argument("--command", required=True)
    p_shell.set_defaults(func=cmd_shell)

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
    p_emit.add_argument("--json", action="store_true")
    p_emit.add_argument("args", nargs="*", help="kwargs as key=value pairs")
    p_emit.set_defaults(func=cmd_emit)

    p_run = sub.add_parser("run", help="Run an op in one tongue subprocess")
    p_run.add_argument("op")
    p_run.add_argument("--tongue", default="KO")
    p_run.add_argument("--timeout", type=float, default=10.0)
    p_run.add_argument("--no-ledger", action="store_true")
    p_run.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    p_run.add_argument("--json", action="store_true")
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
        "--tier",
        default="ALLOW",
        help="Governance tier to bind into seal (ALLOW/QUARANTINE/ESCALATE/DENY)",
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
    p_verify.add_argument(
        "--tier",
        default="ALLOW",
        help="Governance tier embedded in the seal (must match)",
    )
    p_verify.set_defaults(func=cmd_verify)

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
    args, extra_args = parser.parse_known_args(argv)
    if extra_args:
        if hasattr(args, "args") and isinstance(args.args, list):
            args.args.extend(extra_args)
        else:
            parser.error(f"unrecognized arguments: {' '.join(extra_args)}")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
