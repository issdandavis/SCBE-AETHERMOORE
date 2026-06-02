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
import logging
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.getLogger("oqs.oqs").disabled = True

if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

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
from src.tokenizer.code_weight_packets import (
    analyze_chemical_composition,
    resolve_element,
    semantic_operation_signature_from_tokens,
)
from src.tokenizer.code_weight_packets import _semantic_class as _stisa_semantic_class
from src.crypto.geoseal_execution_gate import (
    DEFAULT_AUDIT_SECRET_ENV,
    DEFAULT_EXEC_AUDIT_LOG,
    TIER_RANK,
    append_sealed_exec_audit,
    execute_governed_command,
    scan_command,
)
from src.crypto.geoseal_legitimacy import CoarseLocation, run_legitimacy_trial
from src.research_navigation import (
    build_research_evidence_packet,
    build_youtube_navigation_packet,
)
from src.coding_board.pipeline import run_coding_trial
from src.agentic.meet_in_the_middle import (
    CodeHalf,
    SeamContract,
    merge_halves,
)
from src.cli.param_binding import BoundCommand, bind_subparser
from pydantic import ConfigDict, Field
from typing import Literal as _Literal

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


_RUNNER_TEMP_NAMES: Dict[str, Tuple[str, str]] = {
    "GO": (".go", "geoseal_go_"),
    "ZI": (".zig", "geoseal_zi_"),
}


def _runner_temp_name(tongue: str) -> Tuple[str, str]:
    try:
        return _RUNNER_TEMP_NAMES[tongue]
    except KeyError as exc:  # pragma: no cover - guarded by _runner_for mode
        raise ValueError(f"no file-runner temp mapping for {tongue}") from exc


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
    gate_max_tier: str = "QUARANTINE",
    gate_audit_log: Optional[Path] = DEFAULT_EXEC_AUDIT_LOG,
    gate_audit_secret: Optional[str] = None,
    gate_audit_secret_env: str = DEFAULT_AUDIT_SECRET_ENV,
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

        suffix, prefix = _runner_temp_name(tongue)
        fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(wrapped)
        argv = list(argv_prefix) + [str(tmp_path)]
    else:
        argv = list(argv_prefix) + [wrapped]
    gate_command = shlex.join(str(part) for part in argv)
    gate_decision = scan_command(gate_command)
    if TIER_RANK[gate_decision.tier] > TIER_RANK[gate_max_tier]:
        result.error = f"execution gate {gate_decision.tier}: exceeds max tier {gate_max_tier}"
        if gate_audit_log is not None:
            append_sealed_exec_audit(
                {
                    "version": "geoseal-run-exec-gate-v1",
                    "timestamp": time.time(),
                    "op": op,
                    "tongue": tongue,
                    "command": gate_command,
                    "max_tier": gate_max_tier,
                    "decision": gate_decision.to_dict(),
                    "ran": False,
                },
                audit_log=gate_audit_log,
                audit_secret=gate_audit_secret,
                audit_secret_env=gate_audit_secret_env,
            )
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        return result
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
    if gate_audit_log is not None:
        append_sealed_exec_audit(
            {
                "version": "geoseal-run-exec-gate-v1",
                "timestamp": time.time(),
                "op": op,
                "tongue": tongue,
                "command": gate_command,
                "max_tier": gate_max_tier,
                "decision": gate_decision.to_dict(),
                "ran": result.ran,
                "returncode": result.returncode,
                "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
                "error": result.error,
            },
            audit_log=gate_audit_log,
            audit_secret=gate_audit_secret,
            audit_secret_env=gate_audit_secret_env,
        )
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
    bits_text = getattr(args, "bits", None) or getattr(args, "bits_option", None) or ""
    bit_chunks = [tok for tok in re.split(r"[\s,]+", bits_text.strip()) if tok]
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


def _read_tongue_program_source(args: argparse.Namespace) -> tuple[str, str]:
    source = getattr(args, "content", None)
    source_name = getattr(args, "source_name", None) or "inline"
    source_file = getattr(args, "source_file", None)
    if source_file:
        path = Path(source_file)
        source = path.read_text(encoding="utf-8")
        source_name = getattr(args, "source_name", None) or path.name
    if source is None:
        source = sys.stdin.read()
        source_name = getattr(args, "source_name", None) or "stdin"
    return source, source_name


def cmd_tongue_compile(args: argparse.Namespace) -> int:
    from src.sacred_tongues_toolchain import SacredTonguesToolchainError, compile_packet

    try:
        source, source_name = _read_tongue_program_source(args)
        packet = compile_packet(source, source_name=source_name)
        output = getattr(args, "output", None)
        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if getattr(args, "output_format", "json") == "bin":
                out_path.write_bytes(bytes(packet["bytecode"]))
            else:
                out_path.write_text(json.dumps(packet["bytecode"], indent=2) + "\n", encoding="utf-8")
            packet["output_path"] = str(out_path)
        print(json.dumps(packet))
        return 0
    except SacredTonguesToolchainError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


def cmd_tongue_run(args: argparse.Namespace) -> int:
    from src.sacred_tongues_toolchain import SacredTonguesToolchainError, compile_packet, load_program, run_packet

    try:
        program_file = getattr(args, "program_file", None)
        compile_payload = None
        if program_file:
            program = load_program(Path(program_file))
            source_name = Path(program_file).name
        else:
            source, source_name = _read_tongue_program_source(args)
            compile_payload = compile_packet(source, source_name=source_name)
            program = compile_payload["bytecode"]
        run_payload = run_packet(program, max_steps=int(getattr(args, "max_steps", 10000)))
        payload = {
            "schema_version": "geoseal_tongue_run_v1",
            "source_name": source_name,
            "compile": compile_payload,
            "run": run_payload,
        }
        if getattr(args, "json", False):
            print(json.dumps(payload))
        else:
            for value in run_payload["output"]:
                print(value)
        return 0
    except SacredTonguesToolchainError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


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
    semantic_operation = semantic_operation_signature_from_tokens(lexical_tokens, language=language)
    semantic["operation_signature"] = semantic_operation
    semantic["operation_path"] = semantic_operation["operation_path"]
    semantic["interchange_key"] = semantic_operation["interchange_key"]
    definitions = [
        {"symbol": name, "kind": kind}
        for kind, name in re.findall(r"\b(import|class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", source)
    ]
    class_names = set(re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", source))
    function_names = set(re.findall(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source))
    stisa_rows = []
    stisa_elements: list[dict[str, Any]] = []
    for tok in lexical_tokens:
        semantic_class = _stisa_semantic_class(tok)
        element = resolve_element(tok, semantic_class)
        stisa_elements.append(element)
        stisa_rows.append(
            {
                "token": tok,
                "semantic_class": semantic_class,
                "feature_vector": [float(x) for x in element["feat"]],
            }
        )
    stisa_chemistry = analyze_chemical_composition(
        lexical_tokens, stisa_elements, operation_path=semantic_operation["operation_path"]
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
                    "Z",
                    "group",
                    "period",
                    "valence",
                    "chi",
                    "band",
                    "tongue_id",
                    "reserved",
                ]
            ],
            "token_rows": stisa_rows,
            "binary_groups": ([{"group_id": "g0", "tokens": lexical_tokens[:8]}] if lexical_tokens else []),
            "chemical_composition": stisa_chemistry,
        },
        "chemical_composition": stisa_chemistry,
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
        "semantic_operation_signature": semantic_operation,
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
            "Z",
            "group",
            "period",
            "valence",
            "chi",
            "band",
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


def _load_agent_endurance_example(name: str) -> dict[str, Any]:
    path = Path("schemas") / "examples" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def cmd_agent_endurance_pack(args: argparse.Namespace) -> int:
    """Generate a local Agent Endurance v1 artifact bundle."""
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    round_id = args.round_id
    regimen = _load_agent_endurance_example("agent_endurance_regimen_v1.example.json")
    taskset = _load_agent_endurance_example("agent_endurance_taskset_v1.example.json")
    run_report = _load_agent_endurance_example("agent_endurance_run_report_v1.example.json")

    regimen["created_at_utc"] = now
    regimen["default_permission_mode"] = args.permission_mode
    taskset["taskset_id"] = round_id
    taskset["regimen_id"] = regimen["regimen_id"]
    taskset["created_at_utc"] = now
    metadata = dict(taskset.get("metadata") or {})
    metadata["round_id"] = round_id
    metadata["generated_by"] = "geoseal agent-endurance-pack"
    taskset["metadata"] = metadata

    run_report["run_id"] = f"{round_id}-run"
    run_report["taskset_id"] = taskset["taskset_id"]
    run_report["regimen_id"] = regimen["regimen_id"]
    run_report["timestamp_utc"] = now
    run_report["permission_mode"] = args.permission_mode
    run_report["candidate_id"] = args.candidate_id
    run_report["evidence"] = {
        "history_path": ".scbe/geoseal_calls.jsonl",
        "task_trace_path": str(out_dir / "task_trace.jsonl"),
        "stdout_log_path": str(out_dir / "stdout.log"),
        "raw_report_path": str(out_dir / "raw.json"),
    }

    paths = {
        "regimen": out_dir / "agent_endurance_regimen_v1.json",
        "taskset": out_dir / "agent_endurance_taskset_v1.json",
        "run_report": out_dir / "agent_endurance_run_report_v1.json",
        "manifest": out_dir / "agent_endurance_manifest.json",
    }
    _write_json_artifact(paths["regimen"], regimen)
    _write_json_artifact(paths["taskset"], taskset)
    _write_json_artifact(paths["run_report"], run_report)

    manifest = {
        "schema_version": "geoseal_agent_endurance_pack_v1",
        "round_id": round_id,
        "permission_mode": args.permission_mode,
        "candidate_id": args.candidate_id,
        "created_at_utc": now,
        "paths": {key: str(path) for key, path in paths.items()},
    }
    _write_json_artifact(paths["manifest"], manifest)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"schema={manifest['schema_version']} round_id={round_id}")
        print(f"output_dir={out_dir}")
    return 0


def cmd_call_switchboard(args: argparse.Namespace) -> int:
    from src.coding_spine.agent_call_switchboard import evaluate_call_request

    calls: list[dict[str, Any]] = []
    if args.calls:
        loaded = json.loads(Path(args.calls).read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise SystemExit("--calls must point to a JSON array")
        calls = loaded
    if getattr(args, "inline_calls", None):
        loaded = json.loads(args.inline_calls)
        if not isinstance(loaded, list):
            raise SystemExit("--inline-calls must be a JSON array")
        calls.extend(loaded)
    request = json.loads(args.request)
    payload = evaluate_call_request(calls, request)
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def cmd_lightning_indexer(args: argparse.Namespace) -> int:
    from src.coding_spine.lightning_indexer import select_sparse_candidates

    candidates: list[dict[str, Any]] = []
    if args.candidates_file:
        loaded = json.loads(Path(args.candidates_file).read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise SystemExit("--candidates-file must point to a JSON array")
        candidates = loaded
    if args.inline_candidates:
        loaded = json.loads(args.inline_candidates)
        if not isinstance(loaded, list):
            raise SystemExit("--inline-candidates must be a JSON array")
        candidates.extend(loaded)
    payload = select_sparse_candidates(
        args.goal,
        candidates,
        top_k=args.top_k,
        block_size=args.block_size,
        channel_budget=args.channel_budget,
    )
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    from src.coding_spine.command_compiler import compile_intent_to_plan

    payload = compile_intent_to_plan(
        intent=" ".join(args.intent or []),
        permission_mode=args.permission_mode,
        preferred_language=args.language,
        requested_tool=args.tool,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{payload['schema_version']} tool={payload['tool']['class']} "
            f"decision={payload['policy']['decision']} runnable={payload['command']['runnable']}"
        )
        if payload["command"]["template"]:
            print(payload["command"]["template"])
    return 0 if payload["policy"]["decision"] != "DENY" else 2


def cmd_domino(args: argparse.Namespace) -> int:
    from src.coding_spine.domino_workflow import build_domino_workflow_from_specs

    payload = build_domino_workflow_from_specs(
        list(args.tile or []),
        start=args.start,
        allow_rotation=not args.no_rotate,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    chain = payload.get("chain") or []
    print(
        f"{payload['schema']} complete={payload['summary']['complete']} chain_length={payload['summary']['chain_length']}"
    )
    print("chain=" + " -> ".join(f"{tile['tile_id']}({tile['left']}|{tile['right']})" for tile in chain))
    if payload.get("blocked"):
        print("blocked=" + ",".join(tile["tile_id"] for tile in payload["blocked"]))
    if payload.get("contacts"):
        print("contacts=" + str(len(payload["contacts"])))
    return 0


def cmd_loop_dispatch(args: argparse.Namespace) -> int:
    from src.coding_spine.agent_tool_policy import (
        evaluate_harness_tool_policy,
        geoseal_command_to_tool_class,
    )

    tool_class = geoseal_command_to_tool_class("loop-dispatch", execute=bool(args.execute))
    policy = evaluate_harness_tool_policy(
        permission_mode=args.permission_mode,
        tool_class=tool_class,
    )
    payload = {
        "schema_version": "scbe_loop_dispatch_plan_v1",
        "provider": args.provider,
        "task": args.task,
        "execute": bool(args.execute),
        "policy": policy,
    }
    if args.execute and policy.get("ok"):
        execute_armed = os.environ.get("SCBE_AGENTIC_LOOP_EXECUTE", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        payload["execute_gate"] = {
            "armed": execute_armed,
            "decision": "ALLOW" if execute_armed else "QUARANTINE",
            "reason": "set SCBE_AGENTIC_LOOP_EXECUTE=1 to perform external loop dispatch",
        }
        if not execute_armed:
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print("loop-dispatch execute gate is not armed")
            return 2
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{payload['schema_version']} provider={args.provider} task={args.task} " f"decision={policy['decision']}"
        )
    return 0 if policy.get("ok") else 2


def cmd_assist(args: argparse.Namespace) -> int:
    from scripts.system.micro_agent_assist import (
        build_advice,
        post_packet,
        render_text,
        resolve_bus,
    )

    repo_root = Path(args.repo_root).resolve()
    bus_path = resolve_bus(repo_root, Path(args.bus) if args.bus else None)
    advice = build_advice(
        task=args.task,
        agent=args.agent,
        repo_root=repo_root,
        bus_path=bus_path,
    )
    if args.post:
        packet = post_packet(
            bus_path,
            sender=args.agent,
            recipient=args.recipient,
            task_id="MICRO-ASSIST",
            status="verify",
            seam=advice["lane"],
            claim_paths=advice["suggested_paths"],
            summary=f"{advice['intent']}: {advice['first_action']}",
            next_action="Follow micro-assist suggested paths and verify commands.",
            proof=advice["verify_commands"],
        )
        advice["posted_packet_id"] = packet["packet_id"]
    if args.json:
        print(json.dumps(advice, indent=2, sort_keys=True))
    else:
        print(render_text(advice))
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
    gate = scan_command(args.command)
    append_sealed_exec_audit(
        {
            "version": "geoseal-shell-gate-v1",
            "timestamp": time.time(),
            "command": args.command,
            "max_tier": args.max_tier,
            "decision": gate.to_dict(),
            "ran": False,
        },
        audit_log=Path(args.audit_log),
        audit_secret=args.audit_secret,
        audit_secret_env=args.audit_secret_env,
    )
    if TIER_RANK[gate.tier] > TIER_RANK[args.max_tier]:
        if args.json:
            print(
                json.dumps(
                    {
                        "version": "geoseal-shell-v1",
                        "gate": gate.to_dict(),
                        "ran": False,
                    },
                    indent=2,
                )
            )
        else:
            print(f"[gate] {gate.tier}: blocked nested command")
            for finding in gate.findings:
                print(f"  - {finding.rule}: {finding.message}")
        return 2
    tokens = shlex.split(args.command)
    if not tokens:
        raise SystemExit("--command is empty")
    nested_parser = build_parser()
    nested_args = nested_parser.parse_args(tokens)
    return nested_args.func(nested_args)


def _strip_argv_separator(argv: Any) -> Any:
    """Drop a leading '--' that argparse REMAINDER captures verbatim."""
    if isinstance(argv, list) and argv and argv[0] == "--":
        return argv[1:]
    return argv


def cmd_exec(args: argparse.Namespace) -> int:
    claimed_paths = args.claimed_path or []
    cleaned = _strip_argv_separator(args.command)
    command = subprocess.list2cmdline(cleaned) if isinstance(cleaned, list) else cleaned
    if not command:
        print("exec command is empty", file=sys.stderr)
        return 2
    result = execute_governed_command(
        command,
        cwd=Path(args.cwd) if args.cwd else None,
        timeout=args.timeout,
        max_tier=args.max_tier,
        claimed_paths=claimed_paths,
        audit_log=None if args.no_audit else Path(args.audit_log),
        audit_secret=args.audit_secret,
        audit_secret_env=args.audit_secret_env,
    )
    payload = {"version": "geoseal-exec-v1", **result.to_dict()}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        decision = result.decision
        print(f"[gate] tier={decision.tier} allowed={decision.allowed} ran={result.ran}")
        for finding in decision.findings:
            print(f"  - {finding.rule}: {finding.message}")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.error:
            print(f"error: {result.error}", file=sys.stderr)
        if result.audit_written:
            print(f"[audit] sealed record appended to {args.audit_log}")
    if not result.ran:
        return 2
    return result.returncode or 0


def cmd_legitimacy_trial(args: argparse.Namespace) -> int:
    location = CoarseLocation(
        source=args.location_source,
        label=args.location_label,
        confidence=args.location_confidence,
    )
    cleaned = _strip_argv_separator(args.command)
    command = subprocess.list2cmdline(cleaned) if isinstance(cleaned, list) and cleaned else None
    payload = run_legitimacy_trial(
        goal=args.goal,
        expected_tool=args.tool,
        origin=args.origin,
        expected_state=args.expected_state,
        privacy=args.privacy,
        command=command,
        workspace=Path(args.workspace) if args.workspace else None,
        location=location,
        network_state=args.network_state,
    )
    decision = payload["decision"]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"[legitimacy] decision={decision['decision']} "
            f"allowed_cli={decision['allowed_cli']} score={decision['score']}"
        )
        for finding in decision["findings"]:
            print(f"  - {finding['rule']}: {finding['message']}")
        print(f"[seal] packet_sha256={decision['packet_sha256']}")
    if decision["decision"] == "DENY":
        return 3
    if decision["decision"] == "ESCALATE":
        return 2
    if decision["decision"] == "PROBE_ONLY":
        return 1
    return 0


def cmd_research_nav(args: argparse.Namespace) -> int:
    content = None
    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    elif args.content:
        content = args.content
    packet = build_research_evidence_packet(
        url=args.url,
        content=content,
        fetch=not args.no_fetch,
        max_links=args.max_links,
        timeout=args.timeout,
    ).to_dict()
    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        print(f"[research-nav] status={packet['status']} title={packet['title'] or '-'}")
        print(f"[research-nav] url={packet['resolved_url']}")
        print(
            f"[research-nav] verdict={packet['security'].get('verdict')} "
            f"decision={packet['security'].get('governance_decision')}"
        )
        print(packet["text_excerpt"][:500])
    return 0 if packet["status"] not in {"fetch_error"} else 1


def cmd_youtube_nav(args: argparse.Namespace) -> int:
    packet = build_youtube_navigation_packet(
        target=args.target,
        fetch_metadata=args.fetch_metadata,
        fetch_transcript=args.fetch_transcript,
        languages=args.language or ["en"],
        max_links=args.max_links,
    )
    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        transcript = packet["transcript"]
        print(f"[youtube-nav] video_id={packet['video_id']}")
        print(f"[youtube-nav] url={packet['canonical_url']}")
        print(
            f"[youtube-nav] metadata={packet['metrics']['has_metadata']} "
            f"transcript={transcript['available']} segments={transcript['segment_count']}"
        )
        if transcript["text_excerpt"]:
            print(transcript["text_excerpt"][:500])
        if transcript["error"]:
            print(f"[youtube-nav] transcript_error={transcript['error']}", file=sys.stderr)
    return 0 if not packet["transcript"]["error"] else 1


def cmd_coding_trial(args: argparse.Namespace) -> int:
    location = CoarseLocation(
        source=args.location_source,
        label=args.location_label,
        confidence=args.location_confidence,
    )
    cleaned = _strip_argv_separator(args.command)
    payload = run_coding_trial(
        goal=args.goal,
        command=cleaned if isinstance(cleaned, list) else [str(cleaned)],
        workspace=Path(args.workspace) if args.workspace else None,
        origin=args.origin,
        expected_tool=args.tool,
        expected_state=args.expected_state,
        privacy=args.privacy,
        location=location,
        network_state=args.network_state,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        legitimacy = payload["legitimacy"]["decision"]
        probe = payload["probe"]
        print(
            f"[coding-trial] legitimacy={legitimacy['decision']} "
            f"probe={probe['mode']} legal={probe['legal']} accepted={payload['accepted']}"
        )
        if probe.get("reason"):
            print(f"[coding-trial] reason={probe['reason']}")
    if payload["legitimacy"]["decision"]["decision"] == "DENY":
        return 3
    if payload["accepted"]:
        return 0
    return 1


# ---------------------------------------------------------------------------
#  seal-here: example port to the BoundCommand parameter-binding framework
#
#  This is the migration template for step 6 of the scope-of-mind sequence.
#  Future subcommands should declare a BoundCommand subclass + handler and
#  register via `bind_subparser()` instead of free-form argparse calls.
# ---------------------------------------------------------------------------

# Named locations for the location-by-name parameter set.
_NAMED_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "port-angeles": (48.1181, -123.4307),
    "sequim": (48.0792, -123.1027),
    "seattle": (47.6062, -122.3321),
}


class SealHereCommand(BoundCommand):
    """Seal a payload to a geographic fence — name a place or give coordinates."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        parameter_sets={
            "by-name": ["location_name"],
            "by-coords": ["lat", "lon"],
        },
    )

    secret: str = Field(..., description="Secret used to seal the packet (required)")
    payload: str = Field(..., description="Payload string to seal (required)")
    radius_km: float = Field(
        5.0,
        ge=0.1,
        le=100.0,
        description="Fence radius in kilometers (1-100)",
    )
    location_name: Optional[_Literal["port-angeles", "sequim", "seattle"]] = Field(
        None,
        description="Use a known named location (port-angeles | sequim | seattle)",
    )
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude in degrees")
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude in degrees")
    label: str = Field("seal-here", description="Audit label for the sealed packet")
    tongue: _Literal["ko", "av", "ru", "ca", "um", "dr"] = Field(
        "ko",
        description="Sacred Tongue used as transport for the sealed bytes",
    )


def _handle_seal_here(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.crypto.geo_fenced_seal import seal_with_geo_fence

    cmd = bound  # narrow type
    assert isinstance(cmd, SealHereCommand)

    if cmd.location_name is not None:
        lat, lon = _NAMED_LOCATIONS[cmd.location_name]
    else:
        # parameter-set validation already guaranteed lat+lon are present here
        lat, lon = float(cmd.lat or 0.0), float(cmd.lon or 0.0)

    fence = {"lat": lat, "lon": lon, "radius_m": cmd.radius_km * 1000.0}
    packet = seal_with_geo_fence(
        secret=cmd.secret.encode("utf-8"),
        payload=cmd.payload.encode("utf-8"),
        geo_fence=fence,
        label=cmd.label,
        tongue=cmd.tongue,
    )
    summary = {
        "version": "geoseal-seal-here-v1",
        "fence": fence,
        "tongue": cmd.tongue,
        "label": cmd.label,
        "token_count": packet["token_count"],
        "source_sha256": packet["source_sha256"],
        "token_sha256": packet["token_sha256"],
    }
    print(json.dumps(summary, indent=2))
    return 0


#  cross-build: bijective sphere — any tongue in, any tongue out via the
#  shared LatticeOp IR. Tier 1 covers 57/64 lexicon ops × 30 directed pairs.
# ---------------------------------------------------------------------------


class CrossBuildCommand(BoundCommand):
    """Translate lexicon-rendered code from one Sacred Tongue to another."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        # Parameter sets are discriminated by ONE unique field per set.
        # Shared inputs like --src-code / --src-tongue feed whichever
        # set the discriminator selected, so they don't go in here.
        parameter_sets={
            "single": ["dst_tongue"],
            "broadcast": ["all_tongues"],
            "info": ["list_ops"],
        },
    )

    src_code: Optional[str] = Field(
        None,
        description="Lexicon-rendered source snippet to lift into the lattice IR",
    )
    src_tongue: Optional[_Literal["KO", "AV", "RU", "CA", "UM", "DR"]] = Field(
        None, description="Source tongue (one of KO|AV|RU|CA|UM|DR)"
    )
    dst_tongue: Optional[_Literal["KO", "AV", "RU", "CA", "UM", "DR"]] = Field(
        None, description="Destination tongue for single-target translation"
    )
    all_tongues: bool = Field(
        False,
        description="Broadcast: emit the IR in every tongue except the source",
    )
    list_ops: bool = Field(
        False,
        description="Print the 57 Tier 1 participating ops and the 7 excluded ops",
    )


def _handle_cross_build(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.cross_build_ir import (
        QuarantineError,
        TIER1_EXCLUDED_OPS,
        TIER1_PARTICIPATING_OPS,
        cross_build,
        emit_from_ir,
        lift_to_lattice,
    )

    cmd = bound
    assert isinstance(cmd, CrossBuildCommand)

    if cmd.list_ops:
        print(
            json.dumps(
                {
                    "version": "geoseal-cross-build-v1",
                    "tier": 1,
                    "participating_count": len(TIER1_PARTICIPATING_OPS),
                    "participating_ops": list(TIER1_PARTICIPATING_OPS),
                    "excluded_count": len(TIER1_EXCLUDED_OPS),
                    "excluded_ops": list(TIER1_EXCLUDED_OPS),
                    "tongues": ["KO", "AV", "RU", "CA", "UM", "DR"],
                },
                indent=2,
            )
        )
        return 0

    try:
        if cmd.all_tongues:
            ir = lift_to_lattice(cmd.src_code or "", cmd.src_tongue or "")
            translations: Dict[str, str] = {}
            for tongue in ("KO", "AV", "RU", "CA", "UM", "DR"):
                if tongue == cmd.src_tongue:
                    continue
                translations[tongue] = emit_from_ir(ir, tongue)
            payload = {
                "version": "geoseal-cross-build-v1",
                "mode": "broadcast",
                "src_tongue": cmd.src_tongue,
                "src_code": cmd.src_code,
                "ir": ir.model_dump(),
                "translations": translations,
            }
        else:
            result = cross_build(cmd.src_code or "", cmd.src_tongue or "", cmd.dst_tongue or "")
            payload = {
                "version": "geoseal-cross-build-v1",
                "mode": "single",
                "src_tongue": result.src_tongue,
                "src_language": result.src_language,
                "dst_tongue": result.dst_tongue,
                "dst_language": result.dst_language,
                "src_code": result.src_code,
                "dst_code": result.dst_code,
                "ir": result.ir.model_dump(),
            }
    except QuarantineError as exc:
        err = {
            "version": "geoseal-cross-build-v1",
            "verdict": "QUARANTINE",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        # Structured output always goes to stdout — exit code carries the
        # verdict. Keeps JSON parseable even when stderr has unrelated noise
        # (liboqs warnings, etc).
        print(json.dumps(err, indent=2))
        return 2

    print(json.dumps(payload, indent=2))
    return 0


#  route: SLM-router CLI surface — natural-language intent -> LatticeOp.
#  Two modes: AUTO (SLM picks unsupplied stages) and MANUAL (caller pins
#  every stage; SLM is never invoked, deterministic dispatch).
# ---------------------------------------------------------------------------


class RouteCommand(BoundCommand):
    """Route a natural-language intent through the SCBE Tier 1 SLM router."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        # Discriminated by the mode flag. MANUAL requires op_name + dst_tongue;
        # AUTO accepts anything from intent-only up to fully pinned.
        parameter_sets={
            "auto": ["intent"],
            "manual": ["manual"],
        },
    )

    intent: Optional[str] = Field(
        None,
        description="Natural-language description of what to do (used by AUTO mode SLM prompts)",
    )
    manual: bool = Field(
        False,
        description="MANUAL mode: SLM never called, requires --op-name and --dst-tongue",
    )
    op_name: Optional[str] = Field(
        None,
        description="Pin the lexicon op (e.g. add, mul, xor) — skips band+op SLM stages",
    )
    band: Optional[_Literal["ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION"]] = Field(
        None, description="Pin the operation band — skips band SLM stage"
    )
    dst_tongue: Optional[_Literal["KO", "AV", "RU", "CA", "UM", "DR"]] = Field(
        None, description="Pin the destination tongue — skips tongue SLM stage"
    )
    arg: List[str] = Field(
        default_factory=list,
        description="Repeatable arg binding `name=value` (e.g. --arg a=x --arg b=y)",
    )
    emit: bool = Field(
        False,
        description="After routing, emit code in the resolved dst_tongue (adds dst_code to output)",
    )
    emit_all: bool = Field(
        False,
        description="After routing, emit code in ALL 6 tongues (adds translations map)",
    )
    raw: bool = Field(
        False,
        description=(
            "Pipe-friendly: emitted code to stdout, JSON envelope to stderr. "
            "Requires --emit (single tongue); ignored with --emit-all."
        ),
    )
    ollama_model: Optional[str] = Field(
        None,
        description="Override Ollama model name (default qwen2.5:1.5b-instruct-q4_K_M)",
    )
    ollama_host: str = Field("http://localhost:11434", description="Ollama server URL")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Reject SLM stages below this confidence")
    timeout_seconds: float = Field(30.0, ge=0.1, le=300.0, description="Per-classify timeout")
    no_ledger: bool = Field(
        False,
        description="Skip persisting this dispatch to the promotion ledger (stateless mode)",
    )
    ledger_path: Optional[str] = Field(
        None,
        description="Override promotion-ledger path (default: .scbe/route_ledger.jsonl)",
    )
    promotion_threshold: int = Field(
        3,
        ge=2,
        le=100,
        description="Recurrence count at which a trace becomes a promotion candidate",
    )


def _parse_args_pairs(pairs: List[str]) -> Dict[str, str]:
    """Parse `name=value` style flags into a dict. Refuses malformed pairs
    with a clear error so silent loss doesn't happen at the CLI boundary."""
    out: Dict[str, str] = {}
    for raw in pairs:
        if "=" not in raw:
            raise ValueError(f"--arg must be name=value, got {raw!r}")
        k, v = raw.split("=", 1)
        k = k.strip()
        if not k:
            raise ValueError(f"--arg has empty name: {raw!r}")
        out[k] = v
    return out


def _handle_route(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.slm_router import (
        LatticeRouter,
        Mode,
        OllamaAdapter,
        QuarantineError,
    )

    cmd = bound
    assert isinstance(cmd, RouteCommand)

    try:
        args_dict = _parse_args_pairs(cmd.arg)
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "version": "geoseal-route-v1",
                    "verdict": "QUARANTINE",
                    "error_type": "ArgParseError",
                    "message": str(exc),
                },
                indent=2,
            )
        )
        return 2

    mode = Mode.MANUAL if cmd.manual else Mode.AUTO

    # Build adapter — Ollama in production, but routing without an adapter is
    # legitimate in fully-pinned manual mode (caller never calls SLM).
    if mode is Mode.MANUAL and cmd.op_name and cmd.dst_tongue:
        # Use a no-op adapter that asserts if invoked — manual mode should
        # never hit it.
        class _ForbiddenAdapter:
            def classify(self, prompt: str, choices):  # noqa: ANN001
                raise RuntimeError("MANUAL mode adapter must not be called")

        adapter = _ForbiddenAdapter()
    else:
        kwargs = {"host": cmd.ollama_host}
        if cmd.ollama_model:
            kwargs["model"] = cmd.ollama_model
        adapter = OllamaAdapter(**kwargs)

    router = LatticeRouter(
        adapter,
        min_confidence=cmd.min_confidence,
        adapter_timeout=cmd.timeout_seconds,
    )

    try:
        result = router.route(
            intent=cmd.intent or "",
            args=args_dict,
            mode=mode,
            band=cmd.band,
            op_name=cmd.op_name,
            dst_tongue=cmd.dst_tongue,
        )
    except QuarantineError as exc:
        err = {
            "version": "geoseal-route-v1",
            "verdict": "QUARANTINE",
            "mode": mode.value,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(err, indent=2))
        router.close()
        return 2
    finally:
        # close() is idempotent — fine to call after both success and the
        # quarantine return path above.
        pass

    payload = {
        "version": "geoseal-route-v1",
        "mode": mode.value,
        "verdict": "ALLOW",
        "op_name": result.op.op_name,
        "op_id": result.op.op_id,
        "band": result.op.band,
        "dst_tongue": result.dst_tongue,
        "args": dict(result.op.args),
        "confidence": result.confidence,
        "reasoning": list(result.reasoning),
    }

    # Optional emit step — after routing succeeds, render the LatticeOp
    # into one or all six target tongues. This closes the NL->IR->code
    # loop in a single CLI call, which is what agentic loops actually
    # want as a one-shot primitive.
    if cmd.emit or cmd.emit_all:
        from src.cli.cross_build_ir import (
            QuarantineError as _IRQuarantine,
            emit_from_ir,
        )

        try:
            if cmd.emit_all:
                tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
                payload["translations"] = {t: emit_from_ir(result.op, t) for t in tongues}
                # The "primary" dst_code is still the routed tongue.
                payload["dst_code"] = payload["translations"][result.dst_tongue]
            else:
                payload["dst_code"] = emit_from_ir(result.op, result.dst_tongue)
        except _IRQuarantine as exc:
            err = {
                "version": "geoseal-route-v1",
                "verdict": "QUARANTINE",
                "stage": "emit",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
            print(json.dumps(err, indent=2))
            router.close()
            return 2

    # Promotion ledger — persist this dispatch's trace so frequent
    # invocations surface as candidates for subcommand promotion. This
    # is the floating-tower mechanic: the CLI grows new named primitives
    # from agent usage patterns, not from a release cycle.
    if not cmd.no_ledger:
        try:
            from src.cli.command_trace import PromotionLedger, record_session

            ledger_path = Path(cmd.ledger_path) if cmd.ledger_path else Path(".scbe/route_ledger.jsonl")
            ledger = PromotionLedger.load(ledger_path, threshold=cmd.promotion_threshold)
            # Build a synthetic argv that captures the *normalised* dispatch
            # rather than the raw CLI flags. Two invocations that resolve to
            # the same op + args + tongue should hash identically regardless
            # of whether they came in via --intent or --manual.
            normalised_argv = (
                "geoseal",
                "route",
                "--op-name",
                result.op.op_name,
                "--dst-tongue",
                result.dst_tongue,
            ) + tuple(flag for k, v in sorted(result.op.args.items()) for flag in ("--arg", f"{k}={v}"))
            trace = record_session(normalised_argv, env=os.environ)
            entry = ledger.observe(trace)
            ledger.save(ledger_path)
            payload["ledger"] = {
                "path": str(ledger_path),
                "digest": entry.digest,
                "count": entry.count,
                "is_candidate": entry.count >= cmd.promotion_threshold,
                "threshold": cmd.promotion_threshold,
            }
        except Exception as exc:
            # Ledger is best-effort — never fail the route on persistence error.
            payload["ledger_error"] = f"{type(exc).__name__}: {exc}"

    # Output routing — `--raw` puts emitted code on stdout for clean
    # piping (e.g. `geoseal route ... --emit --raw | bash`). The JSON
    # envelope still goes somewhere so audit trails aren't lost.
    if cmd.raw and cmd.emit and not cmd.emit_all:
        print(payload["dst_code"])
        sys.stderr.write(json.dumps(payload, indent=2) + "\n")
    else:
        print(json.dumps(payload, indent=2))
    router.close()
    return 0


#  promote / aliases / alias / unpromote — the floating-tower self-modify path.
#
#  Workflow:
#    geoseal route ... (×N times)        -> ledger accumulates digests
#    geoseal promotions                  -> see candidates above threshold
#    geoseal promote --digest <hex> --as <name>
#    geoseal aliases                     -> list registered aliases
#    geoseal alias <name> [--arg ...]    -> invoke the saved dispatch
#    geoseal unpromote --alias <name>    -> remove
# ---------------------------------------------------------------------------


class PromoteCommand(BoundCommand):
    """Upgrade a ledger candidate into a registered alias."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        # Either name a specific digest or take the top current candidate.
        parameter_sets={
            "by-digest": ["digest"],
            "latest": ["latest"],
        },
    )

    name: str = Field(
        ...,
        description="Alias name to register (lowercase letters/digits/hyphens, max 64 chars)",
    )
    digest: Optional[str] = Field(
        None,
        description="Specific ledger digest to promote (use `geoseal promotions` to list)",
    )
    latest: bool = Field(False, description="Promote the current top candidate (highest count)")
    ledger_path: str = Field(".scbe/route_ledger.jsonl", description="Path to the route promotion ledger")
    registry_path: str = Field(".scbe/route_aliases.json", description="Path to the alias registry")
    overwrite: bool = Field(False, description="Replace an existing alias with the same name")
    threshold: int = Field(
        3,
        ge=1,
        le=1000,
        description="Recurrence threshold required to promote (matches `geoseal promotions`)",
    )


class AliasesCommand(BoundCommand):
    """List registered aliases."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    registry_path: str = Field(".scbe/route_aliases.json", description="Path to the alias registry")


class AliasCommand(BoundCommand):
    """Invoke a registered alias — dispatches in MANUAL mode using the
    stored op + tongue + default args, with caller-supplied --arg overrides."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: str = Field(..., description="Alias name to invoke")
    arg: List[str] = Field(
        default_factory=list,
        description="Repeatable arg override `name=value`; missing keys fall back to alias defaults",
    )
    emit: bool = Field(False, description="Render LatticeOp into dst_tongue (adds dst_code)")
    emit_all: bool = Field(False, description="Render in all 6 tongues")
    raw: bool = Field(False, description="Emit code to stdout, envelope to stderr")
    registry_path: str = Field(".scbe/route_aliases.json", description="Path to the alias registry")


class UnpromoteCommand(BoundCommand):
    """Remove a registered alias."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    alias: str = Field(..., description="Alias name to remove")
    registry_path: str = Field(".scbe/route_aliases.json", description="Path to the alias registry")


def _handle_promote(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.alias_registry import AliasError, AliasRegistry
    from src.cli.command_trace import PromotionLedger

    cmd = bound
    assert isinstance(cmd, PromoteCommand)

    ledger = PromotionLedger.load(Path(cmd.ledger_path), threshold=cmd.threshold)

    # Resolve which entry to promote.
    if cmd.latest:
        candidates = ledger.candidates()
        if not candidates:
            err = {
                "version": "geoseal-promote-v1",
                "verdict": "QUARANTINE",
                "error_type": "NoCandidate",
                "message": (f"no ledger entry has crossed threshold={cmd.threshold} " f"in {cmd.ledger_path}"),
            }
            print(json.dumps(err, indent=2))
            return 2
        target = candidates[0]
    else:
        target = ledger.entries.get(cmd.digest or "")
        if target is None:
            err = {
                "version": "geoseal-promote-v1",
                "verdict": "QUARANTINE",
                "error_type": "DigestNotFound",
                "message": f"digest {cmd.digest!r} not in ledger {cmd.ledger_path}",
            }
            print(json.dumps(err, indent=2))
            return 2
        if target.count < cmd.threshold:
            err = {
                "version": "geoseal-promote-v1",
                "verdict": "QUARANTINE",
                "error_type": "BelowThreshold",
                "message": (f"digest {cmd.digest} has count={target.count}, " f"below threshold={cmd.threshold}"),
            }
            print(json.dumps(err, indent=2))
            return 2

    # Recover dispatch shape from the normalised sample_argv.
    op_name, dst_tongue, default_args = _parse_normalised_argv(target.sample_argv)
    if op_name is None or dst_tongue is None:
        err = {
            "version": "geoseal-promote-v1",
            "verdict": "QUARANTINE",
            "error_type": "MalformedSampleArgv",
            "message": f"could not parse sample_argv: {list(target.sample_argv)}",
        }
        print(json.dumps(err, indent=2))
        return 2

    registry = AliasRegistry.load(Path(cmd.registry_path))
    try:
        entry = registry.register(
            cmd.name,
            op_name=op_name,
            dst_tongue=dst_tongue,
            default_args=default_args,
            source_digest=target.digest,
            promoted_from_count=target.count,
            overwrite=cmd.overwrite,
        )
    except AliasError as exc:
        err = {
            "version": "geoseal-promote-v1",
            "verdict": "QUARANTINE",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(err, indent=2))
        return 2
    registry.save(Path(cmd.registry_path))

    payload = {
        "version": "geoseal-promote-v1",
        "verdict": "ALLOW",
        "registry_path": cmd.registry_path,
        "promoted": entry.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _handle_aliases(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.alias_registry import AliasRegistry

    cmd = bound
    assert isinstance(cmd, AliasesCommand)
    path = Path(cmd.registry_path)
    registry = AliasRegistry.load(path)
    payload = {
        "version": "geoseal-aliases-list-v1",
        "registry_path": str(path),
        "registry_exists": path.exists(),
        "alias_count": len(registry.aliases),
        "aliases": [e.to_dict() for e in registry.list_aliases()],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _handle_alias(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.alias_registry import AliasNotFoundError, AliasRegistry
    from src.cli.cross_build_ir import (
        QuarantineError as _IRQuarantine,
        emit_from_ir,
    )

    cmd = bound
    assert isinstance(cmd, AliasCommand)
    registry = AliasRegistry.load(Path(cmd.registry_path))
    try:
        entry = registry.lookup(cmd.name)
    except AliasNotFoundError as exc:
        err = {
            "version": "geoseal-alias-invoke-v1",
            "verdict": "QUARANTINE",
            "error_type": "AliasNotFoundError",
            "message": str(exc),
        }
        print(json.dumps(err, indent=2))
        return 2

    # Merge default_args with caller overrides.
    try:
        overrides = _parse_args_pairs(cmd.arg)
    except ValueError as exc:
        err = {
            "version": "geoseal-alias-invoke-v1",
            "verdict": "QUARANTINE",
            "error_type": "ArgParseError",
            "message": str(exc),
        }
        print(json.dumps(err, indent=2))
        return 2
    merged_args = {**dict(entry.default_args), **overrides}

    # Build LatticeOp directly via the lexicon — alias dispatch is
    # deterministic and bypasses the SLM router entirely.
    from src.ca_lexicon import LEXICON_BY_NAME
    from src.cli.cross_build_ir import LatticeOp, TIER1_PARTICIPATING_OPS

    if entry.op_name not in LEXICON_BY_NAME:
        err = {
            "version": "geoseal-alias-invoke-v1",
            "verdict": "QUARANTINE",
            "error_type": "StaleAlias",
            "message": f"alias {cmd.name!r} references unknown op {entry.op_name!r}",
        }
        print(json.dumps(err, indent=2))
        return 2
    if entry.op_name not in TIER1_PARTICIPATING_OPS:
        err = {
            "version": "geoseal-alias-invoke-v1",
            "verdict": "QUARANTINE",
            "error_type": "StaleAlias",
            "message": f"alias {cmd.name!r} op {entry.op_name!r} excluded from Tier 1",
        }
        print(json.dumps(err, indent=2))
        return 2

    lex_entry = LEXICON_BY_NAME[entry.op_name]
    op = LatticeOp.from_entry(lex_entry, merged_args)

    payload = {
        "version": "geoseal-alias-invoke-v1",
        "verdict": "ALLOW",
        "alias": entry.name,
        "op_name": op.op_name,
        "op_id": op.op_id,
        "band": op.band,
        "dst_tongue": entry.dst_tongue,
        "args": dict(op.args),
    }

    if cmd.emit or cmd.emit_all:
        try:
            if cmd.emit_all:
                tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
                payload["translations"] = {t: emit_from_ir(op, t) for t in tongues}
                payload["dst_code"] = payload["translations"][entry.dst_tongue]
            else:
                payload["dst_code"] = emit_from_ir(op, entry.dst_tongue)
        except _IRQuarantine as exc:
            err = {
                "version": "geoseal-alias-invoke-v1",
                "verdict": "QUARANTINE",
                "stage": "emit",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
            print(json.dumps(err, indent=2))
            return 2

    if cmd.raw and cmd.emit and not cmd.emit_all:
        print(payload["dst_code"])
        sys.stderr.write(json.dumps(payload, indent=2) + "\n")
    else:
        print(json.dumps(payload, indent=2))
    return 0


def _handle_unpromote(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.alias_registry import AliasNotFoundError, AliasRegistry

    cmd = bound
    assert isinstance(cmd, UnpromoteCommand)
    registry = AliasRegistry.load(Path(cmd.registry_path))
    try:
        removed = registry.unregister(cmd.alias)
    except AliasNotFoundError as exc:
        err = {
            "version": "geoseal-unpromote-v1",
            "verdict": "QUARANTINE",
            "error_type": "AliasNotFoundError",
            "message": str(exc),
        }
        print(json.dumps(err, indent=2))
        return 2
    registry.save(Path(cmd.registry_path))
    payload = {
        "version": "geoseal-unpromote-v1",
        "verdict": "ALLOW",
        "removed": removed.to_dict(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _parse_normalised_argv(argv: tuple) -> tuple:
    """Recover (op_name, dst_tongue, args_dict) from the normalised
    sample_argv stored by the route handler.

    The normalised shape is:
      ("geoseal", "route", "--op-name", <op>, "--dst-tongue", <tongue>,
       "--arg", "k1=v1", "--arg", "k2=v2", ...)
    """
    op_name = None
    dst_tongue = None
    args: Dict[str, str] = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--op-name" and i + 1 < len(argv):
            op_name = argv[i + 1]
            i += 2
        elif token == "--dst-tongue" and i + 1 < len(argv):
            dst_tongue = argv[i + 1]
            i += 2
        elif token == "--arg" and i + 1 < len(argv):
            pair = argv[i + 1]
            if "=" in pair:
                k, v = pair.split("=", 1)
                args[k] = v
            i += 2
        else:
            i += 1
    return op_name, dst_tongue, args


#  promotions: list candidates from the route ledger.
# ---------------------------------------------------------------------------


class PromotionsCommand(BoundCommand):
    """List recurrence candidates from the route promotion ledger."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    ledger_path: str = Field(
        ".scbe/route_ledger.jsonl",
        description="Path to the promotion ledger (default .scbe/route_ledger.jsonl)",
    )
    threshold: int = Field(
        3,
        ge=1,
        le=1000,
        description="Recurrence count at which an entry surfaces as a candidate",
    )
    show_all: bool = Field(
        False,
        description="Include all entries (below threshold too), not just candidates",
    )


def _handle_promotions(bound: BoundCommand, ns: argparse.Namespace) -> int:
    from src.cli.command_trace import PromotionLedger

    cmd = bound
    assert isinstance(cmd, PromotionsCommand)

    path = Path(cmd.ledger_path)
    ledger = PromotionLedger.load(path, threshold=cmd.threshold)

    if cmd.show_all:
        rows = sorted(ledger.entries.values(), key=lambda e: e.count, reverse=True)
    else:
        rows = ledger.candidates()

    payload = {
        "version": "geoseal-promotions-v1",
        "ledger_path": str(path),
        "ledger_exists": path.exists(),
        "threshold": cmd.threshold,
        "total_entries": len(ledger.entries),
        "candidate_count": len(ledger.candidates()),
        "shown_count": len(rows),
        "shown": [
            {
                "digest": e.digest,
                "count": e.count,
                "first_seen_us": e.first_seen_us,
                "last_seen_us": e.last_seen_us,
                "sample_argv": list(e.sample_argv),
                "is_candidate": e.count >= cmd.threshold,
            }
            for e in rows
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_swarm_exec(args: argparse.Namespace) -> int:
    """Run the meet-in-the-middle protocol with two pre-written halves and
    optionally execute the merged module through the SCBE execution gate.

    Each half is a Python source file containing a SEAM_MARKER comment. The
    declared seam contract (names + optional types) is encoded through the
    bijective Sacred Tongues tokenizer for byte-equal verification at the
    meeting line. Convergent halves are merged into a temp file and run
    through the same gate as `geoseal exec`.
    """
    forward_path = Path(args.forward)
    reverse_path = Path(args.reverse)
    if not forward_path.is_file():
        print(f"forward half not found: {forward_path}", file=sys.stderr)
        return 2
    if not reverse_path.is_file():
        print(f"reverse half not found: {reverse_path}", file=sys.stderr)
        return 2

    seam_names = tuple(n.strip() for n in (args.seam_names or "").split(",") if n.strip())
    if not seam_names:
        print("--seam-names is required (comma-separated identifiers)", file=sys.stderr)
        return 2
    seam_types = tuple(t.strip() for t in (args.seam_types or "").split(",") if t.strip())
    if seam_types and len(seam_types) != len(seam_names):
        print("--seam-types must be empty or parallel to --seam-names", file=sys.stderr)
        return 2

    try:
        contract = SeamContract(names=seam_names, types=seam_types)
    except ValueError as exc:
        print(f"invalid seam contract: {exc}", file=sys.stderr)
        return 2

    fwd = CodeHalf(
        direction="forward",
        code=forward_path.read_text(encoding="utf-8"),
        declared_seam=contract,
    )
    rev = CodeHalf(
        direction="reverse",
        code=reverse_path.read_text(encoding="utf-8"),
        declared_seam=contract,
    )

    # First, do an in-process merge with execute=False so we can show seam
    # convergence diagnostics without invoking the merged module yet.
    report = merge_halves(fwd, rev, execute=False)

    base_payload: Dict[str, Any] = {
        "version": "geoseal-swarm-exec-v1",
        "tongue": args.tongue.lower(),
        "seam_contract": {
            "names": list(contract.names),
            "types": list(contract.types),
            "tongue_hash": contract.seam_tongue_hash(args.tongue.lower()),
        },
        "converged": report.converged,
        "forward_seam_hash": report.forward_seam_hash,
        "reverse_seam_hash": report.reverse_seam_hash,
        "diagnostics": report.diagnostics,
        "merged_source": report.merged_source if report.converged else None,
    }

    if not report.converged:
        if args.json:
            print(json.dumps(base_payload, indent=2))
        else:
            print(f"[swarm-exec] converged=False  seam_tongue_hash={base_payload['seam_contract']['tongue_hash'][:16]}")
            for diag in report.diagnostics:
                print(f"  - {diag}")
        return 2

    if not args.execute:
        # convergence-only mode
        if args.json:
            print(json.dumps(base_payload, indent=2))
        else:
            print(f"[swarm-exec] converged=True  seam_tongue_hash={base_payload['seam_contract']['tongue_hash'][:16]}")
            print(f"  forward_hash: {report.forward_seam_hash[:16]}")
            print(f"  reverse_hash: {report.reverse_seam_hash[:16]}")
            print(f"  merged source: {len(report.merged_source or '')} bytes (use --execute to run)")
        return 0

    # Execute the merged module through the SCBE execution gate.
    with tempfile.TemporaryDirectory(prefix="geoseal-swarm-") as tmp:
        merged_path = Path(tmp) / "merged.py"
        merged_path.write_text(report.merged_source or "", encoding="utf-8")
        # Quote the path so a space in tmp doesn't break the gate's parser.
        command_str = f'"{sys.executable}" "{merged_path}"'

        gate_result = execute_governed_command(
            command_str,
            cwd=Path(args.cwd) if args.cwd else None,
            timeout=args.timeout,
            max_tier=args.max_tier,
            claimed_paths=args.claimed_path or [],
            audit_log=None if args.no_audit else Path(args.audit_log),
            audit_secret=args.audit_secret,
            audit_secret_env=args.audit_secret_env,
        )

    payload = {
        **base_payload,
        "gate": gate_result.to_dict(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        decision = gate_result.decision
        print(f"[swarm-exec] converged=True  seam_tongue_hash={base_payload['seam_contract']['tongue_hash'][:16]}")
        print(f"[gate] tier={decision.tier} allowed={decision.allowed} ran={gate_result.ran}")
        for finding in decision.findings:
            print(f"  - {finding.rule}: {finding.message}")
        if gate_result.stdout:
            print(gate_result.stdout.rstrip())
        if gate_result.stderr:
            print(gate_result.stderr.rstrip(), file=sys.stderr)
        if gate_result.error:
            print(f"error: {gate_result.error}", file=sys.stderr)
        if gate_result.audit_written:
            print(f"[audit] sealed record appended to {args.audit_log}")

    if not gate_result.ran:
        return 2
    return gate_result.returncode or 0


def cmd_validate_line(args: argparse.Namespace) -> int:
    cleaned = _strip_argv_separator(args.command)
    command = subprocess.list2cmdline(cleaned) if isinstance(cleaned, list) else cleaned
    decision = scan_command(command, claimed_paths=args.claimed_path or [])
    pill = f"[{decision.tier}:{'PASS' if decision.allowed else 'BLOCK'}]"
    payload = {
        "version": "geoseal-validate-line-v1",
        "pill": pill,
        "command_sha256": decision.command_sha256,
        "decision": decision.to_dict(),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(pill)
        for finding in decision.findings:
            print(f"  - {finding.rule}: {finding.message}")
    return 0 if decision.allowed else 2


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
    call = run_tongue_call(
        args.op,
        tongue,
        kv,
        execute=True,
        timeout=args.timeout,
        gate_max_tier=args.gate_max_tier,
        gate_audit_log=None if args.no_gate_audit else Path(args.gate_audit_log),
        gate_audit_secret=args.gate_audit_secret,
        gate_audit_secret_env=args.gate_audit_secret_env,
    )
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


# ---------------------------------------------------------------------------
# api-graph: self-describing skill tree of the GeoSeal CLI
# ---------------------------------------------------------------------------

_SKILL_TIER_LABELS: Dict[str, str] = {
    "L1": "inspect",
    "L2": "analyze",
    "L3": "route",
    "L4": "execute",
    "L5": "govern",
    "L6": "orchestrate",
}

# (tier, tongue, band, deps, description)
_SKILL_TREE_META: Dict[str, Tuple[str, str, str, List[str], str]] = {
    "ops": ("L1", "KO", "LEXICON", [], "List all 64 lexicon ops"),
    "atomic": ("L1", "KO", "LEXICON", ["ops"], "Inspect atomic substrate row for an op"),
    "emit": ("L1", "KO", "LEXICON", ["ops"], "Emit code for an op in any tongue"),
    "encode-cmd": ("L1", "KO", "TOKENIZER", [], "Encode payload via Sacred Tongue tokenizer"),
    "decode-cmd": ("L1", "KO", "TOKENIZER", ["encode-cmd"], "Decode Sacred Tongue token stream to plaintext"),
    "xlate-cmd": ("L1", "AV", "TOKENIZER", ["encode-cmd", "decode-cmd"], "Translate token stream across tongues"),
    "binary-to-tokenizer": ("L1", "KO", "TOKENIZER", ["encode-cmd"], "Map binary bytes to Sacred Tongue token rows"),
    "yin-yang-dual": ("L2", "DR", "TOKENIZER", ["encode-cmd", "decode-cmd"], "Build KO/DR yin-yang dual token packet"),
    "tongue-compile": ("L2", "KO", "TOOLCHAIN", ["encode-cmd"], "Compile Sacred Tongues .sts assembly to VM bytecode"),
    "tongue-run": ("L4", "KO", "TOOLCHAIN", ["tongue-compile"], "Run Sacred Tongues .sts program in bounded VM"),
    "code-packet": ("L2", "KO", "ANALYSIS", ["emit"], "Build SCBE weighted code packet from source"),
    "braille-lane": ("L2", "KO", "ANALYSIS", ["code-packet"], "Build braille/polyhedral cell lane from source"),
    "interaction-graph": ("L2", "AV", "ANALYSIS", ["code-packet"], "Build source/token/STISA/atomic interaction graph"),
    "topology-view": ("L2", "AV", "ANALYSIS", ["interaction-graph"], "Build topology view with polygons and leylines"),
    "cluster-graph": ("L2", "RU", "ANALYSIS", ["topology-view"], "Build cross-lattice cluster graph"),
    "formation-graph": ("L2", "RU", "ANALYSIS", ["cluster-graph"], "Build cross-lattice formation graph"),
    "cross-domain-sequence": ("L2", "CA", "ANALYSIS", ["topology-view"], "Build cross-domain route sequence"),
    "honeycomb-analysis": ("L2", "CA", "ANALYSIS", ["topology-view"], "Analyze route cell execution stability"),
    "cognition-map": ("L2", "UM", "ANALYSIS", ["topology-view"], "Build cognitive well/ternary overlay map"),
    "mars-mission": ("L2", "KO", "ANALYSIS", ["topology-view"], "Build Mars mission compass/minimap packet"),
    "api-graph": ("L2", "DR", "ANALYSIS", [], "Self-describing skill tree of the GeoSeal CLI"),
    "seal": ("L3", "KO", "GOVERNANCE", ["emit"], "Apply GeoSeal phase signature to a payload"),
    "verify": ("L3", "KO", "GOVERNANCE", ["seal"], "Verify a GeoSeal signature"),
    "seal-here": ("L3", "KO", "GOVERNANCE", ["seal"], "Geo-fence seal (PowerShell parameter-bound)"),
    "backend-registry": ("L3", "KO", "ROUTING", [], "List backend providers and lane support"),
    "portal-box": ("L3", "KO", "ROUTING", ["code-packet"], "Build local portal-box route packet"),
    "stream-wheel": ("L3", "AV", "ROUTING", ["portal-box"], "Build local stream-wheel route packet"),
    "code-roundtrip": (
        "L3",
        "RU",
        "TOOLCHAIN",
        ["encode-cmd", "decode-cmd"],
        "Encode/decode/execute code roundtrip through tongue",
    ),
    "explain-route": ("L3", "KO", "ROUTING", ["backend-registry"], "Explain route IR and backend chain for a source"),
    "route": ("L3", "KO", "ROUTING", ["explain-route"], "Route intent via SLM (auto or manual)"),
    "run": ("L4", "KO", "EXECUTION", ["emit", "seal"], "Run lexicon op in one tongue subprocess"),
    "swarm": ("L4", "KO", "EXECUTION", ["run"], "Dispatch op to swarm of tongue bots with BFT consensus"),
    "cross-build": ("L4", "RU", "EXECUTION", ["emit"], "Bijective A→lattice IR→B tongue translation"),
    "swarm-exec": (
        "L4",
        "RU",
        "EXECUTION",
        ["swarm", "cross-build"],
        "Meet-in-the-middle codegen through bijective seam",
    ),
    "exec": ("L4", "CA", "EXECUTION", ["seal"], "Run command through GeoSeal execution gate"),
    "shell": ("L4", "CA", "EXECUTION", ["exec"], "Run nested GeoSeal command string"),
    "arc": ("L4", "UM", "EXECUTION", ["run"], "Synthesize + apply ARC task program"),
    "agent": ("L4", "KO", "AGENT", ["route", "backend-registry"], "Route coding task via Polly → GeoSeal stamp"),
    "cursor": ("L4", "DR", "AGENT", ["agent"], "Delegate bounded repo task to Cursor Agent"),
    "testing-cli": ("L4", "KO", "TESTING", ["run", "seal"], "Build testing playback packet and execute"),
    "project-scaffold": ("L4", "KO", "SCAFFOLD", ["agent", "route"], "Create lightweight project scaffold from intent"),
    "legitimacy-trial": ("L5", "KO", "GOVERNANCE", ["seal", "exec"], "Evaluate time/location/workspace/intent context"),
    "coding-trial": ("L5", "KO", "GOVERNANCE", ["legitimacy-trial"], "Legitimacy trial plus compiler/test probe"),
    "validate-line": ("L5", "KO", "GOVERNANCE", ["exec"], "Preflight command line — PSReadLine-style verdict"),
    "history": ("L5", "KO", "AUDIT", ["run", "swarm"], "Show execution history from ledger"),
    "replay": ("L5", "KO", "AUDIT", ["history"], "Replay a previous ledger record"),
    "workflow": ("L5", "DR", "GOVERNANCE", ["agent", "seal"], "Declarative .geoseal.yaml workflow runner"),
    "promotions": ("L5", "KO", "PROMOTION", ["route"], "List dispatch patterns above promotion threshold"),
    "promote": ("L5", "KO", "PROMOTION", ["promotions"], "Register recurring dispatch as a named alias"),
    "aliases": ("L5", "KO", "PROMOTION", ["promote"], "List registered alias names and dispatch shape"),
    "alias": ("L5", "KO", "PROMOTION", ["promote"], "Invoke a registered alias deterministically"),
    "unpromote": ("L5", "KO", "PROMOTION", ["promote"], "Remove a registered alias"),
    "compile": ("L6", "AV", "ORCHESTRATION", ["route", "agent-harness"], "Compile intent into agent-bus command plan"),
    "agent-harness": (
        "L6",
        "KO",
        "ORCHESTRATION",
        ["route", "backend-registry"],
        "Emit model-neutral agent harness manifest",
    ),
    "agent-endurance-pack": ("L6", "KO", "ORCHESTRATION", ["agent-harness"], "Generate Agent Endurance v1 spec bundle"),
    "call-switchboard": ("L6", "CA", "ORCHESTRATION", ["route", "seal"], "Evaluate multi-agent call reservation"),
    "lightning-indexer": ("L6", "RU", "ORCHESTRATION", ["call-switchboard"], "Select sparse agent context candidates"),
    "loop-dispatch": (
        "L6",
        "AV",
        "ORCHESTRATION",
        ["agent", "legitimacy-trial"],
        "Policy-gated external agent loop dispatch",
    ),
    "assist": ("L6", "KO", "ORCHESTRATION", ["route", "compile"], "Local micro-assist for terminal agents"),
    "domino": ("L6", "DR", "ORCHESTRATION", ["workflow"], "Arrange domino workflow tiles with contact transfer"),
    "terminus-training": ("L6", "UM", "TRAINING", ["swarm", "agent"], "Run Terminus guild agent training"),
    "pair-agent-training": ("L6", "KO", "TRAINING", ["agent", "workflow"], "Build GeoShell pair-agent SFT dataset"),
}


def _build_api_skill_tree(
    *,
    tier_filter: Optional[str] = None,
    tongue_filter: Optional[str] = None,
    band_filter: Optional[str] = None,
    cmd_filter: Optional[str] = None,
    show_params: bool = False,
) -> Dict[str, Any]:
    # Build forward (cmd→what it unlocks) and reverse (cmd→what requires it) maps
    # over the full meta before filtering so depth and unlock counts are global.
    fwd: Dict[str, List[str]] = {c: [] for c in _SKILL_TREE_META}
    for cmd_name, (_, _, _, deps, _) in _SKILL_TREE_META.items():
        for dep in deps:
            if dep in fwd:
                fwd[dep].append(cmd_name)

    # BFS depth from entry points (commands with no deps in the full graph)
    entry_points = {c for c, (_, _, _, deps, _) in _SKILL_TREE_META.items() if not deps}
    depth_map: Dict[str, int] = {c: 0 for c in entry_points}
    queue = list(entry_points)
    while queue:
        cur = queue.pop(0)
        for child in fwd.get(cur, []):
            new_depth = depth_map[cur] + 1
            if child not in depth_map or depth_map[child] < new_depth:
                depth_map[child] = new_depth
                queue.append(child)

    param_counts: Dict[str, int] = {}
    if show_params:
        try:
            p = build_parser()
            for action_group in p._subparsers._group_actions:
                for name, sub_p in action_group.choices.items():
                    param_counts[name] = sum(1 for a in sub_p._actions if a.dest not in ("help",))
        except Exception:
            pass

    # If --cmd is set, include only that command and its full dep chain + what it unlocks
    if cmd_filter and cmd_filter in _SKILL_TREE_META:
        focus: set = {cmd_filter}
        # ancestors
        stack = list(_SKILL_TREE_META[cmd_filter][3])
        while stack:
            c = stack.pop()
            if c in _SKILL_TREE_META and c not in focus:
                focus.add(c)
                stack.extend(_SKILL_TREE_META[c][3])
        # direct children
        for child in fwd.get(cmd_filter, []):
            focus.add(child)
        active = focus
    else:
        active = set()
        for cmd_name, (tier, tongue, band, _deps, _desc) in _SKILL_TREE_META.items():
            if tier_filter and tier != tier_filter:
                continue
            if tongue_filter and tongue != tongue_filter:
                continue
            if band_filter and band != band_filter:
                continue
            active.add(cmd_name)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for cmd_name in sorted(active):
        tier, tongue, band, deps, desc = _SKILL_TREE_META[cmd_name]
        phi_tier = phi_wall_tier(phi_wall_cost(0.2, tongue))
        unlocks_global = fwd.get(cmd_name, [])
        node: Dict[str, Any] = {
            "id": f"cmd:{cmd_name}",
            "cmd": cmd_name,
            "label": cmd_name,
            "tier": tier,
            "tier_label": _SKILL_TIER_LABELS.get(tier, tier),
            "tongue": tongue,
            "conlang": CONLANG_NAME_MAP.get(tongue, tongue),
            "band": band,
            "phi_tier": phi_tier,
            "phi_weight": TONGUE_PHI_WEIGHTS.get(tongue, 1.0),
            "description": desc,
            "depth": depth_map.get(cmd_name, 0),
            "entry_point": cmd_name in entry_points,
            "requires": deps,
            "unlocks": unlocks_global,
            "unlocks_count": len(unlocks_global),
        }
        if show_params and cmd_name in param_counts:
            node["param_count"] = param_counts[cmd_name]
        nodes.append(node)
        for dep in deps:
            if dep in active:
                edges.append(
                    {
                        "source": f"cmd:{dep}",
                        "target": f"cmd:{cmd_name}",
                        "relation": "unlocks",
                    }
                )

    by_tier: Dict[str, List[str]] = {}
    by_band: Dict[str, List[str]] = {}
    by_tongue: Dict[str, List[str]] = {}
    for n in nodes:
        by_tier.setdefault(n["tier"], []).append(n["cmd"])
        by_band.setdefault(n["band"], []).append(n["cmd"])
        by_tongue.setdefault(n["tongue"], []).append(n["cmd"])

    # Top commands by unlock count (most powerful)
    top_unlocks = sorted(nodes, key=lambda n: n["unlocks_count"], reverse=True)[:5]
    all_entries = [n["cmd"] for n in nodes if n["entry_point"]]
    max_depth = max((n["depth"] for n in nodes), default=0)

    return {
        "version": "geoseal-api-skill-tree-v2",
        "summary": {
            "total_commands": len(nodes),
            "total_edges": len(edges),
            "entry_points": all_entries,
            "max_depth": max_depth,
            "top_unlocking": [{"cmd": n["cmd"], "unlocks": n["unlocks_count"]} for n in top_unlocks],
            "tiers": {t: len(c) for t, c in sorted(by_tier.items())},
            "bands": {b: len(c) for b, c in sorted(by_band.items())},
            "tongues": {t: len(c) for t, c in sorted(by_tongue.items())},
        },
        "tier_labels": _SKILL_TIER_LABELS,
        "nodes": nodes,
        "edges": edges,
        "by_tier": by_tier,
        "by_band": by_band,
        "by_tongue": by_tongue,
    }


def _skill_tree_to_mermaid(tree: Dict[str, Any], *, direction: str = "LR") -> str:
    lines = [
        f"flowchart {direction}",
        "  classDef L1 fill:#e0f2fe,stroke:#0ea5e9",
        "  classDef L2 fill:#dbeafe,stroke:#3b82f6",
        "  classDef L3 fill:#ede9fe,stroke:#8b5cf6",
        "  classDef L4 fill:#fce7f3,stroke:#ec4899",
        "  classDef L5 fill:#fee2e2,stroke:#ef4444",
        "  classDef L6 fill:#fef3c7,stroke:#f59e0b",
    ]
    for tier in sorted(set(n["tier"] for n in tree["nodes"])):
        tier_label = _SKILL_TIER_LABELS.get(tier, tier)
        tier_nodes = [n for n in tree["nodes"] if n["tier"] == tier]
        lines.append(f'  subgraph {tier}["{tier}: {tier_label}"]')
        for n in tier_nodes:
            nid = re.sub(r"[^A-Za-z0-9_]", "_", n["id"])
            entry_mark = " ★" if n["entry_point"] else ""
            unlock_mark = f" +{n['unlocks_count']}" if n["unlocks_count"] else ""
            lines.append(f'    {nid}["{n["cmd"]}{entry_mark}{unlock_mark}<br/>{n["tongue"]} {n["band"]}"]:::{tier}')
        lines.append("  end")
    for edge in tree["edges"]:
        src = re.sub(r"[^A-Za-z0-9_]", "_", edge["source"])
        dst = re.sub(r"[^A-Za-z0-9_]", "_", edge["target"])
        lines.append(f"  {src} --> {dst}")
    return "\n".join(lines) + "\n"


def _skill_tree_to_dot(tree: Dict[str, Any]) -> str:
    tier_colors = {
        "L1": "#e0f2fe",
        "L2": "#dbeafe",
        "L3": "#ede9fe",
        "L4": "#fce7f3",
        "L5": "#fee2e2",
        "L6": "#fef3c7",
    }
    tier_borders = {
        "L1": "#0ea5e9",
        "L2": "#3b82f6",
        "L3": "#8b5cf6",
        "L4": "#ec4899",
        "L5": "#ef4444",
        "L6": "#f59e0b",
    }
    lines = [
        "digraph GeoSealSkillTree {",
        "  rankdir=LR;",
        '  graph [fontname="Courier" fontsize=11];',
        '  node [shape=box fontname="Courier" fontsize=10 style=filled];',
        '  edge [fontname="Courier" fontsize=9];',
    ]
    for tier in sorted(set(n["tier"] for n in tree["nodes"])):
        tier_label = _SKILL_TIER_LABELS.get(tier, tier)
        tier_nodes = [n for n in tree["nodes"] if n["tier"] == tier]
        fill = tier_colors.get(tier, "#ffffff")
        border = tier_borders.get(tier, "#999999")
        lines.append(f"  subgraph cluster_{tier} {{")
        lines.append(f'    label="{tier}: {tier_label}";')
        lines.append(f'    style=filled; fillcolor="{fill}"; color="{border}"; penwidth=2;')
        for n in tier_nodes:
            nid = re.sub(r"[^A-Za-z0-9_]", "_", n["id"])
            entry = "★ " if n["entry_point"] else ""
            unlock = f" +{n['unlocks_count']}" if n["unlocks_count"] else ""
            label = f"{entry}{n['cmd']}{unlock}\\n{n['tongue']} | {n['band']}\\nd={n['depth']}"
            border_c = border if not n["entry_point"] else "#f97316"
            lines.append(f'    {nid} [label="{label}" color="{border_c}"];')
        lines.append("  }")
    for edge in tree["edges"]:
        src = re.sub(r"[^A-Za-z0-9_]", "_", edge["source"])
        dst = re.sub(r"[^A-Za-z0-9_]", "_", edge["target"])
        lines.append(f'  {src} -> {dst} [color="#94a3b8"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _skill_tree_to_ascii(tree: Dict[str, Any]) -> str:
    _TIER_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6"]
    W = 80
    lines: List[str] = [
        "GeoSeal API Skill Tree",
        "─" * W,
    ]
    by_tier = tree["by_tier"]
    node_map = {n["cmd"]: n for n in tree["nodes"]}
    s = tree["summary"]

    # Header stats
    entries = ", ".join(s["entry_points"][:6]) + ("…" if len(s["entry_points"]) > 6 else "")
    lines.append(
        f"  {s['total_commands']} commands  {s['total_edges']} edges  depth={s['max_depth']}  entries: {entries}"
    )
    top = "  top: " + "  ".join(f"{r['cmd']}(+{r['unlocks']})" for r in s["top_unlocking"][:5])
    lines.append(top)
    lines.append("─" * W)

    for tier in _TIER_ORDER:
        cmds = by_tier.get(tier, [])
        if not cmds:
            continue
        tier_label = _SKILL_TIER_LABELS.get(tier, tier)
        tier_count = len(cmds)
        lines.append(f"\n  {tier}  {tier_label.upper()}  ({tier_count})")
        lines.append("  " + "─" * (W - 2))

        bands: Dict[str, List[str]] = {}
        for cmd in sorted(cmds):
            bands.setdefault(node_map[cmd]["band"], []).append(cmd)

        for band, band_cmds in sorted(bands.items()):
            lines.append(f"    ▸ {band}")
            band_cmds_sorted = sorted(band_cmds)
            for i, cmd in enumerate(band_cmds_sorted):
                n = node_map[cmd]
                is_last = i == len(band_cmds_sorted) - 1
                branch = "└─" if is_last else "├─"
                entry_star = "★ " if n["entry_point"] else "  "
                unlock_tag = f"+{n['unlocks_count']}" if n["unlocks_count"] else "  "
                # requires summary (only names, no tier prefix)
                req_s = ""
                if n["requires"]:
                    reqs = ", ".join(n["requires"][:3])
                    req_s = f"  ← {reqs}"
                    if len(n["requires"]) > 3:
                        req_s += f" +{len(n['requires'])-3}"
                # description: wrap at terminal width
                desc = n["description"]
                lines.append(
                    f"      {branch} {entry_star}{cmd:<26} {n['tongue']} d={n['depth']} "
                    f"[{unlock_tag:>3}] {desc}" + req_s
                )

    lines.append("\n" + "─" * W)
    lines.append("  ★ = entry point (no prerequisites)   [+N] = commands this unlocks")
    lines.append("  d=N = depth from nearest entry point  ← = requires these commands")
    return "\n".join(lines) + "\n"


def _skill_tree_cmd_focus(tree: Dict[str, Any], cmd: str) -> str:
    """Single-command focus: show what it needs and what it unlocks."""
    node_map = {n["cmd"]: n for n in tree["nodes"]}
    if cmd not in node_map:
        return f"command not found in tree: {cmd}\n"
    n = node_map[cmd]
    lines = [
        f"  {cmd}",
        f"  {'─' * (len(cmd) + 2)}",
        f"  tier:    {n['tier']} ({n['tier_label']})",
        f"  tongue:  {n['tongue']} ({n['conlang']})",
        f"  band:    {n['band']}",
        f"  depth:   {n['depth']}",
        f"  phi:     φ{n['phi_weight']:.3f}  ({n['phi_tier']})",
        f"  entry:   {'yes ★' if n['entry_point'] else 'no'}",
        f"",
        f"  {n['description']}",
    ]
    if n["requires"]:
        lines += ["", "  REQUIRES:"]
        for dep in n["requires"]:
            dep_n = node_map.get(dep)
            if dep_n:
                lines.append(f"    ← {dep:<28} {dep_n['tier']} {dep_n['tongue']}  {dep_n['description'][:40]}")
            else:
                lines.append(f"    ← {dep}  (outside current filter)")
    if n["unlocks"]:
        lines += ["", "  UNLOCKS:"]
        for child in sorted(n["unlocks"]):
            child_n = node_map.get(child)
            if child_n:
                lines.append(f"    → {child:<28} {child_n['tier']} {child_n['tongue']}  {child_n['description'][:40]}")
            else:
                lines.append(f"    → {child}")
    return "\n".join(lines) + "\n"


def cmd_bench_api(args: argparse.Namespace) -> int:
    """Benchmark api-graph build + render across all format/filter variants."""
    import time

    N = int(getattr(args, "runs", 5))
    verbose = bool(getattr(args, "verbose", False))

    formats = ["json", "mermaid", "dot", "tree"]
    def _time_n(fn, n: int) -> Dict[str, float]:
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        return {
            "min_ms": round(times[0], 2),
            "med_ms": round(times[len(times) // 2], 2),
            "max_ms": round(times[-1], 2),
            "mean_ms": round(sum(times) / len(times), 2),
        }

    results: List[Dict[str, Any]] = []

    # --- build phase ---
    def _build_full():
        _build_api_skill_tree()

    r = _time_n(_build_full, N)
    results.append({"label": "build (62 cmd, no filter)", **r})
    if verbose:
        print(f"  build          min={r['min_ms']}ms  med={r['med_ms']}ms  max={r['max_ms']}ms")

    # --- format rendering ---
    tree_full = _build_api_skill_tree()
    for fmt in formats:

        def _render(f=fmt, t=tree_full):
            if f == "mermaid":
                _skill_tree_to_mermaid(t)
            elif f == "dot":
                _skill_tree_to_dot(t)
            elif f == "tree":
                _skill_tree_to_ascii(t)
            else:
                json.dumps(t)

        r = _time_n(_render, N)
        results.append({"label": f"render:{fmt}", **r})
        if verbose:
            print(f"  render:{fmt:<8} min={r['min_ms']}ms  med={r['med_ms']}ms  max={r['max_ms']}ms")

    # --- tier filters ---
    for tf in ["L1", "L3", "L6"]:

        def _build_tier(t=tf):
            _build_api_skill_tree(tier_filter=t)

        r = _time_n(_build_tier, N)
        results.append({"label": f"build:tier={tf}", **r})
        if verbose:
            print(f"  tier={tf}          min={r['min_ms']}ms  med={r['med_ms']}ms")

    # --- tongue filters ---
    for tng in ["KO", "DR"]:

        def _build_tongue(tn=tng):
            _build_api_skill_tree(tongue_filter=tn)

        r = _time_n(_build_tongue, N)
        results.append({"label": f"build:tongue={tng}", **r})
        if verbose:
            print(f"  tongue={tng}        min={r['min_ms']}ms  med={r['med_ms']}ms")

    # --- cmd focus ---
    def _build_focus():
        _build_api_skill_tree(cmd_filter="seal")

    r = _time_n(_build_focus, N)
    results.append({"label": "build:cmd=seal", **r})

    # --- summary ---
    all_means = [r2["mean_ms"] for r2 in results]
    summary = {
        "version": "geoseal-bench-api-v1",
        "runs_per_variant": N,
        "variants": len(results),
        "overall_mean_ms": round(sum(all_means) / len(all_means), 2),
        "slowest": max(results, key=lambda x: x["med_ms"])["label"],
        "fastest": min(results, key=lambda x: x["med_ms"])["label"],
    }
    out = {"summary": summary, "results": results}
    if getattr(args, "json", False):
        print(json.dumps(out, indent=2))
    else:
        W = 72
        print(f"{'─' * W}")
        print(f"  bench-api  {N} runs/variant  {len(results)} variants")
        print(f"{'─' * W}")
        for row in results:
            bar_fill = int(min(row["med_ms"] / 5, 20))
            bar = "█" * bar_fill + "░" * (20 - bar_fill)
            print(f"  {row['label']:<34} {bar}  med={row['med_ms']}ms")
        print(f"{'─' * W}")
        print(f"  overall mean: {summary['overall_mean_ms']}ms")
        print(f"  slowest: {summary['slowest']}")
        print(f"  fastest: {summary['fastest']}")
    return 0


def cmd_api_graph(args: argparse.Namespace) -> int:
    tier_filter = (getattr(args, "tier", None) or "").upper() or None
    tongue_filter = (getattr(args, "tongue", None) or "").upper() or None
    band_filter = (getattr(args, "band", None) or "").upper() or None
    cmd_filter = (getattr(args, "cmd_focus", None) or "").lower() or None
    show_params = bool(getattr(args, "show_params", False))

    tree = _build_api_skill_tree(
        tier_filter=tier_filter,
        tongue_filter=tongue_filter,
        band_filter=band_filter,
        cmd_filter=cmd_filter,
        show_params=show_params,
    )

    fmt = (getattr(args, "format", None) or "json").lower()
    if fmt == "mermaid":
        print(_skill_tree_to_mermaid(tree, direction="LR"), end="")
    elif fmt == "dot":
        print(_skill_tree_to_dot(tree), end="")
    elif fmt == "tree":
        if cmd_filter:
            print(_skill_tree_cmd_focus(tree, cmd_filter), end="")
        else:
            print(_skill_tree_to_ascii(tree), end="")
    else:
        print(json.dumps(tree, indent=2 if getattr(args, "json", False) else None))
    return 0


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
        "--bits",
        default=None,
        dest="bits_option",
        help="One or more 8-bit chunks. Equivalent to the positional bits argument.",
    )
    p_binary.add_argument(
        "--language",
        default=None,
        help="Optional requested language for prime-lane check",
    )
    p_binary.add_argument("--json", action="store_true")
    p_binary.add_argument("bits", nargs="?", default="", help="Space/comma separated 8-bit chunks")
    p_binary.set_defaults(func=cmd_binary_to_tokenizer)

    p_code_packet = sub.add_parser("code-packet", help="Build SCBE weighted code packet from source")
    p_code_packet.add_argument("--content", default="", help="Inline source content")
    p_code_packet.add_argument("--source-file", default=None, help="Read source content from file")
    p_code_packet.add_argument("--source-name", default=None)
    p_code_packet.add_argument("--language", default="python")
    p_code_packet.add_argument("--backend", default=None, choices=["local", "ollama", "hf", "claude"])
    p_code_packet.set_defaults(func=cmd_code_packet)

    p_tongue_compile = sub.add_parser(
        "tongue-compile",
        help="Compile Sacred Tongues .sts assembly into bounded VM bytecode",
    )
    p_tongue_compile.add_argument("--content", default=None, help="Inline .sts source; defaults to stdin")
    p_tongue_compile.add_argument("--source-file", default=None, help="Read .sts source from file")
    p_tongue_compile.add_argument("--source-name", default=None)
    p_tongue_compile.add_argument("--output", default=None, help="Optional bytecode output path")
    p_tongue_compile.add_argument("--output-format", default="json", choices=["json", "bin"])
    p_tongue_compile.set_defaults(func=cmd_tongue_compile)

    p_tongue_run = sub.add_parser(
        "tongue-run",
        help="Compile/run Sacred Tongues .sts assembly in the bounded VM",
    )
    p_tongue_run.add_argument("--content", default=None, help="Inline .sts source; defaults to stdin")
    p_tongue_run.add_argument("--source-file", default=None, help="Read .sts source from file")
    p_tongue_run.add_argument("--program-file", default=None, help="Run existing bytecode .json or .bin")
    p_tongue_run.add_argument("--source-name", default=None)
    p_tongue_run.add_argument("--max-steps", type=int, default=10000)
    p_tongue_run.add_argument("--json", action="store_true")
    p_tongue_run.set_defaults(func=cmd_tongue_run)

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

    p_endurance = sub.add_parser("agent-endurance-pack", help="Generate Agent Endurance v1 spec bundle")
    p_endurance.add_argument("--round-id", required=True, help="Round/taskset identifier")
    p_endurance.add_argument(
        "--permission-mode",
        default="workspace-write",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
        dest="permission_mode",
    )
    p_endurance.add_argument("--candidate-id", default="geoseal-agent-harness")
    p_endurance.add_argument("--output-dir", required=True, help="Directory for generated endurance artifacts")
    p_endurance.add_argument("--json", action="store_true")
    p_endurance.set_defaults(func=cmd_agent_endurance_pack)

    p_switchboard = sub.add_parser("call-switchboard", help="Evaluate a multi-agent call reservation")
    p_switchboard.add_argument("--calls", default=None, help="Existing call reservations JSON array")
    p_switchboard.add_argument("--inline-calls", default=None, help="Existing call reservations JSON array")
    p_switchboard.add_argument("--request", required=True, help="Requested call JSON object")
    p_switchboard.add_argument("--json", action="store_true")
    p_switchboard.set_defaults(func=cmd_call_switchboard)

    p_indexer = sub.add_parser("lightning-indexer", help="Select sparse agent context candidates")
    p_indexer.add_argument("--goal", required=True)
    p_indexer.add_argument("--inline-candidates", default=None, help="Candidate JSON array")
    p_indexer.add_argument("--candidates-file", default=None, help="Candidate JSON array file")
    p_indexer.add_argument("--top-k", type=int, default=8)
    p_indexer.add_argument("--block-size", type=int, default=16)
    p_indexer.add_argument("--channel-budget", type=int, default=3)
    p_indexer.add_argument("--json", action="store_true")
    p_indexer.set_defaults(func=cmd_lightning_indexer)

    p_compile = sub.add_parser("compile", help="Compile intent into an SCBE agent-bus command plan")
    p_compile.add_argument("intent", nargs=argparse.REMAINDER)
    p_compile.add_argument(
        "--permission-mode",
        default="observe",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
    )
    p_compile.add_argument("--language", default="python")
    p_compile.add_argument("--tool", default=None, help="Force harness tool class")
    p_compile.add_argument("--json", action="store_true")
    p_compile.set_defaults(func=cmd_compile)

    p_domino = sub.add_parser("domino", help="Arrange domino workflow tiles with contact dot transfer")
    p_domino.add_argument(
        "tile",
        nargs="+",
        help="Tile specs like gather:intent|evidence:1/3 or evidence|patch",
    )
    p_domino.add_argument("--start", default=None, help="Start tile id or left contract")
    p_domino.add_argument("--no-rotate", action="store_true", help="Disable automatic tile rotation")
    p_domino.add_argument("--json", action="store_true")
    p_domino.set_defaults(func=cmd_domino)

    p_loop_dispatch = sub.add_parser("loop-dispatch", help="Policy-gated external agent loop dispatch")
    p_loop_dispatch.add_argument("--provider", required=True)
    p_loop_dispatch.add_argument("--task", required=True)
    p_loop_dispatch.add_argument(
        "--permission-mode",
        default="observe",
        choices=["observe", "workspace-write", "cloud-dispatch", "maintenance"],
    )
    p_loop_dispatch.add_argument("--execute", action="store_true")
    p_loop_dispatch.add_argument("--json", action="store_true")
    p_loop_dispatch.set_defaults(func=cmd_loop_dispatch)

    p_assist = sub.add_parser("assist", help="Run local micro-assist for terminal agents")
    p_assist.add_argument("task", help="Task text to classify and route")
    p_assist.add_argument("--agent", default="agent.codex")
    p_assist.add_argument("--recipient", default="agent.claude")
    p_assist.add_argument("--repo-root", default=str(Path.cwd()))
    p_assist.add_argument("--bus", default=None)
    p_assist.add_argument("--post", action="store_true", help="Post advice to centerline bus")
    p_assist.add_argument("--json", action="store_true")
    p_assist.set_defaults(func=cmd_assist)

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
    p_shell.add_argument(
        "--max-tier",
        default="ALLOW",
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
        dest="max_tier",
        help="Highest execution-gate tier allowed for the nested command",
    )
    p_shell.add_argument("--audit-log", default=str(DEFAULT_EXEC_AUDIT_LOG))
    p_shell.add_argument("--audit-secret", default=None)
    p_shell.add_argument("--audit-secret-env", default=DEFAULT_AUDIT_SECRET_ENV)
    p_shell.add_argument("--json", action="store_true")
    p_shell.set_defaults(func=cmd_shell)

    p_exec = sub.add_parser("exec", help="Run an external command through the GeoSeal execution gate")
    p_exec.add_argument("command", nargs=argparse.REMAINDER, help="Command to parse, scan, and execute")
    p_exec.add_argument("--cwd", default=None, help="Working directory for the subprocess")
    p_exec.add_argument("--timeout", type=float, default=30.0)
    p_exec.add_argument(
        "--max-tier",
        default="ALLOW",
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
        dest="max_tier",
        help="Highest execution-gate tier allowed to run",
    )
    p_exec.add_argument(
        "--claimed-path",
        action="append",
        default=[],
        dest="claimed_path",
        help="Path prefix the command is allowed to touch; repeatable",
    )
    p_exec.add_argument("--audit-log", default=str(DEFAULT_EXEC_AUDIT_LOG))
    p_exec.add_argument("--audit-secret", default=None)
    p_exec.add_argument("--audit-secret-env", default=DEFAULT_AUDIT_SECRET_ENV)
    p_exec.add_argument("--no-audit", action="store_true")
    p_exec.add_argument("--json", action="store_true")
    p_exec.set_defaults(func=cmd_exec)

    p_legitimacy = sub.add_parser(
        "legitimacy-trial",
        help="Evaluate time/location/workspace/intent context before opening CLI/tool authority",
    )
    p_legitimacy.add_argument("--goal", required=True, help="Human-readable goal or command intent")
    p_legitimacy.add_argument("--tool", required=True, help="Expected tool/op, e.g. terminal.command.request")
    p_legitimacy.add_argument(
        "--origin",
        default="user",
        choices=["user", "agent", "workflow"],
        help="Who is requesting authority",
    )
    p_legitimacy.add_argument("--expected-state", default="unspecified")
    p_legitimacy.add_argument("--privacy", default="local_only", choices=["local_only", "hosted"])
    p_legitimacy.add_argument("--workspace", default=None, help="Workspace root for write/execute authority")
    p_legitimacy.add_argument(
        "--location-source",
        default="unknown",
        choices=["user_confirmed", "network", "device", "simulated", "unknown"],
    )
    p_legitimacy.add_argument("--location-label", default="unknown")
    p_legitimacy.add_argument("--location-confidence", type=float, default=0.0)
    p_legitimacy.add_argument(
        "--network-state",
        default="unknown",
        choices=["offline", "local", "online", "unknown"],
    )
    p_legitimacy.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Optional command shape to parse/scan after --",
    )
    p_legitimacy.add_argument("--json", action="store_true")
    p_legitimacy.set_defaults(func=cmd_legitimacy_trial)

    p_research_nav = sub.add_parser(
        "research-nav",
        help="Build a structured evidence packet for a web source without ad-hoc scraping output",
    )
    p_research_nav.add_argument("--url", required=True)
    p_research_nav.add_argument("--content", default=None, help="Inline content for offline packet tests")
    p_research_nav.add_argument("--content-file", default=None, help="Read source content from a local file")
    p_research_nav.add_argument(
        "--no-fetch", action="store_true", help="Do not fetch URL; use inline/local content only"
    )
    p_research_nav.add_argument("--max-links", type=int, default=20)
    p_research_nav.add_argument("--timeout", type=float, default=12.0)
    p_research_nav.add_argument("--json", action="store_true")
    p_research_nav.set_defaults(func=cmd_research_nav)

    p_youtube_nav = sub.add_parser(
        "youtube-nav",
        help="Build a structured YouTube navigation packet with optional transcript evidence",
    )
    p_youtube_nav.add_argument("target", help="YouTube URL or 11-character video ID")
    p_youtube_nav.add_argument("--fetch-metadata", action="store_true", help="Fetch the YouTube watch page")
    p_youtube_nav.add_argument(
        "--fetch-transcript", action="store_true", help="Fetch transcript via youtube-transcript-api"
    )
    p_youtube_nav.add_argument(
        "--language", action="append", default=None, help="Transcript language; repeat for fallbacks"
    )
    p_youtube_nav.add_argument("--max-links", type=int, default=20)
    p_youtube_nav.add_argument("--json", action="store_true")
    p_youtube_nav.set_defaults(func=cmd_youtube_nav)

    p_coding_trial = sub.add_parser(
        "coding-trial",
        help="Run legitimacy trial plus a non-destructive compiler/test probe for a coding command",
    )
    p_coding_trial.add_argument("--goal", required=True)
    p_coding_trial.add_argument("--tool", default="terminal.command.request")
    p_coding_trial.add_argument("--origin", default="user", choices=["user", "agent", "workflow"])
    p_coding_trial.add_argument("--expected-state", default="unspecified")
    p_coding_trial.add_argument("--privacy", default="local_only", choices=["local_only", "hosted"])
    p_coding_trial.add_argument("--workspace", default=None)
    p_coding_trial.add_argument(
        "--location-source",
        default="unknown",
        choices=["user_confirmed", "network", "device", "simulated", "unknown"],
    )
    p_coding_trial.add_argument("--location-label", default="unknown")
    p_coding_trial.add_argument("--location-confidence", type=float, default=0.0)
    p_coding_trial.add_argument(
        "--network-state",
        default="unknown",
        choices=["offline", "local", "online", "unknown"],
    )
    p_coding_trial.add_argument("--timeout", type=float, default=30.0)
    p_coding_trial.add_argument("command", nargs=argparse.REMAINDER)
    p_coding_trial.add_argument("--json", action="store_true")
    p_coding_trial.set_defaults(func=cmd_coding_trial)

    # ────────────────────────────────────────────────────────────────────
    # seal-here — first subcommand on the BoundCommand parameter-binding
    # framework. Demonstrates Mandatory, ValidateRange, ValidateSet (via
    # Literal), and ParameterSetName (location-by-name vs location-by-coords).
    # ────────────────────────────────────────────────────────────────────
    p_seal_here = sub.add_parser(
        "seal-here",
        help="Seal a payload to a geographic fence (PowerShell-style parameter-bound subcommand)",
    )
    bind_subparser(p_seal_here, SealHereCommand, _handle_seal_here)

    # cross-build (alias: xb) — bijective sphere translation across tongues.
    p_cross_build = sub.add_parser(
        "cross-build",
        aliases=["xb"],
        help="Translate lexicon code A->lattice IR->B (Tier 1: 57 ops, 30 directed pairs)",
    )
    bind_subparser(p_cross_build, CrossBuildCommand, _handle_cross_build)

    # route — Tier 1 SLM router. AUTO mode picks unsupplied stages via
    # local Ollama; MANUAL mode requires the caller to pin every stage.
    p_route = sub.add_parser(
        "route",
        help="Route an intent through the SLM (auto) or pin every stage (manual)",
    )
    bind_subparser(p_route, RouteCommand, _handle_route)

    # promotions — list recurrence candidates from the route ledger.
    p_promotions = sub.add_parser(
        "promotions",
        help="List dispatch patterns that have crossed the promotion threshold",
    )
    bind_subparser(p_promotions, PromotionsCommand, _handle_promotions)

    # promote — upgrade a ledger candidate into a registered alias.
    p_promote = sub.add_parser(
        "promote",
        help="Register a recurring dispatch as a named alias",
    )
    bind_subparser(p_promote, PromoteCommand, _handle_promote)

    # aliases — list registered aliases.
    p_aliases = sub.add_parser(
        "aliases",
        help="List registered alias names + their dispatch shape",
    )
    bind_subparser(p_aliases, AliasesCommand, _handle_aliases)

    # alias — invoke a registered alias.
    p_alias = sub.add_parser(
        "alias",
        help="Invoke a registered alias (deterministic dispatch via stored op + tongue)",
    )
    bind_subparser(p_alias, AliasCommand, _handle_alias)

    # unpromote — remove a registered alias.
    p_unpromote = sub.add_parser(
        "unpromote",
        help="Remove a registered alias",
    )
    bind_subparser(p_unpromote, UnpromoteCommand, _handle_unpromote)

    p_swarm_exec = sub.add_parser(
        "swarm-exec",
        help="Meet-in-the-middle codegen: merge two halves through the bijective seam, then run through the gate",
    )
    p_swarm_exec.add_argument("--forward", required=True, help="Path to the forward (input → seam) half")
    p_swarm_exec.add_argument("--reverse", required=True, help="Path to the reverse (seam → output) half")
    p_swarm_exec.add_argument(
        "--seam-names",
        required=True,
        dest="seam_names",
        help="Comma-separated identifiers that must agree at the seam",
    )
    p_swarm_exec.add_argument(
        "--seam-types",
        default="",
        dest="seam_types",
        help="Optional comma-separated type strings parallel to --seam-names",
    )
    p_swarm_exec.add_argument(
        "--tongue",
        default="ko",
        help="Sacred Tongue used for seam canonicalization (default: ko)",
    )
    p_swarm_exec.add_argument(
        "--execute",
        action="store_true",
        help="Actually run the merged module through the gate",
    )
    p_swarm_exec.add_argument("--cwd", default=None, help="Working directory for the merged-module subprocess")
    p_swarm_exec.add_argument("--timeout", type=float, default=30.0)
    p_swarm_exec.add_argument(
        "--max-tier",
        default="ALLOW",
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
        dest="max_tier",
        help="Highest execution-gate tier allowed to run the merged module",
    )
    p_swarm_exec.add_argument(
        "--claimed-path",
        action="append",
        default=[],
        dest="claimed_path",
        help="Path prefix the merged module is allowed to touch; repeatable",
    )
    p_swarm_exec.add_argument("--audit-log", default=str(DEFAULT_EXEC_AUDIT_LOG))
    p_swarm_exec.add_argument("--audit-secret", default=None)
    p_swarm_exec.add_argument("--audit-secret-env", default=DEFAULT_AUDIT_SECRET_ENV)
    p_swarm_exec.add_argument("--no-audit", action="store_true")
    p_swarm_exec.add_argument("--json", action="store_true")
    p_swarm_exec.set_defaults(func=cmd_swarm_exec)

    p_validate_line = sub.add_parser(
        "validate-line",
        help="Preflight a command line and print a PSReadLine-style gate verdict",
    )
    p_validate_line.add_argument("command", nargs=argparse.REMAINDER)
    p_validate_line.add_argument(
        "--claimed-path",
        action="append",
        default=[],
        dest="claimed_path",
        help="Path prefix the line is allowed to touch; repeatable",
    )
    p_validate_line.add_argument("--json", action="store_true")
    p_validate_line.set_defaults(func=cmd_validate_line)

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
    p_run.add_argument(
        "--gate-max-tier",
        default="QUARANTINE",
        choices=["ALLOW", "QUARANTINE", "ESCALATE"],
        dest="gate_max_tier",
        help="Highest execution-gate tier allowed for the generated subprocess",
    )
    p_run.add_argument("--gate-audit-log", default=str(DEFAULT_EXEC_AUDIT_LOG))
    p_run.add_argument("--gate-audit-secret", default=None)
    p_run.add_argument("--gate-audit-secret-env", default=DEFAULT_AUDIT_SECRET_ENV)
    p_run.add_argument("--no-gate-audit", action="store_true")
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

    p_terminus = sub.add_parser(
        "terminus-training",
        help="Run Terminus guild agent training (benchmark or scripted scenario)",
    )
    p_terminus.add_argument("--mode", choices=["benchmark", "scripted"], default="benchmark")
    p_terminus.add_argument("--scenario", default="guild_math_intro", help="Scenario name for scripted mode")
    p_terminus.add_argument("--agent-id", default="benchmark-agent")
    p_terminus.add_argument("--out-dir", default="artifacts/terminus_training")
    p_terminus.add_argument("--json", action="store_true")
    p_terminus.set_defaults(func=cmd_terminus_training)

    p_yy = sub.add_parser("yin-yang-dual", help="Build a KO/DR yin-yang dual token packet")
    p_yy.add_argument("--ko-text", required=True)
    p_yy.add_argument("--dr-text", required=True)
    p_yy.add_argument("--frame", type=int, choices=[0, 1], default=0, help="Active frame: 0=KO, 1=DR")
    p_yy.add_argument("--size", type=int, default=9, help="Odd surface size >= 5")
    p_yy.add_argument("--json", action="store_true")
    p_yy.set_defaults(func=cmd_yin_yang_dual)

    p_pair = sub.add_parser(
        "pair-agent-training",
        help="Build the GeoShell Builder/Navigator pair-agent SFT dataset",
    )
    p_pair.add_argument("--output-dir", default="training-data/sft")
    p_pair.add_argument("--event-path", default="artifacts/geoshell/pair_agent/latest_events.json")
    p_pair.add_argument("--json", action="store_true")
    p_pair.set_defaults(func=cmd_pair_agent_training)

    p_api_graph = sub.add_parser(
        "api-graph",
        help="Show the GeoSeal CLI skill tree (API graph of all subcommands)",
    )
    p_api_graph.add_argument(
        "--format",
        default="json",
        choices=["json", "mermaid", "dot", "tree"],
        help="Output format: json | mermaid | dot | tree (ASCII)",
    )
    p_api_graph.add_argument("--tier", default=None, help="Filter by skill tier L1-L6")
    p_api_graph.add_argument("--tongue", default=None, help="Filter by tongue KO|AV|RU|CA|UM|DR")
    p_api_graph.add_argument(
        "--band", default=None, help="Filter by band e.g. LEXICON|ANALYSIS|ROUTING|EXECUTION|GOVERNANCE|ORCHESTRATION"
    )
    p_api_graph.add_argument(
        "--show-params",
        action="store_true",
        dest="show_params",
        help="Attach parser param counts to each node",
    )
    p_api_graph.add_argument(
        "--cmd",
        default=None,
        dest="cmd_focus",
        metavar="CMD",
        help="Focus on a single command: show its deps, what it unlocks, and all metadata",
    )
    p_api_graph.add_argument("--json", action="store_true")
    p_api_graph.set_defaults(func=cmd_api_graph)

    p_bench_api = sub.add_parser("bench-api", help="Benchmark api-graph build + render performance")
    p_bench_api.add_argument("--runs", type=int, default=5, help="Iterations per variant (default 5)")
    p_bench_api.add_argument("--verbose", action="store_true", help="Print each variant as it runs")
    p_bench_api.add_argument("--json", action="store_true", help="Emit JSON report")
    p_bench_api.set_defaults(func=cmd_bench_api)

    return p


def cmd_terminus_training(args: argparse.Namespace) -> int:
    """Bridge the geoseal CLI to the Terminus guild training runner."""
    from scripts.benchmark.terminus_training_runner import (
        BENCHMARK_PATHS,
        run_benchmark,
        run_scripted,
    )

    out_dir = Path(args.out_dir)
    try:
        if args.mode == "scripted":
            if args.scenario not in BENCHMARK_PATHS:
                raise SystemExit(
                    f"error: unknown scenario {args.scenario!r}; choose from {', '.join(sorted(BENCHMARK_PATHS))}"
                )
            payload = run_scripted(
                BENCHMARK_PATHS[args.scenario],
                agent_id=args.agent_id,
                scenario=args.scenario,
                out_dir=out_dir,
            )
        else:
            payload = run_benchmark(out_dir, agent_id=args.agent_id)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        raise SystemExit(f"error: {exc}")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        score = payload.get("total_score", payload.get("score"))
        print(f"pass={payload.get('pass', 'n/a')} score={score}")
    return 0


def cmd_yin_yang_dual(args: argparse.Namespace) -> int:
    """Bridge the geoseal CLI to the KO/DR yin-yang dual token builder."""
    from src.tokenizer.yin_yang_lattice import build_yin_yang_dual_packet

    try:
        packet = build_yin_yang_dual_packet(
            ko_text=args.ko_text,
            dr_text=args.dr_text,
            size=args.size,
            active_frame=args.frame,
        )
    except (ValueError, KeyError) as exc:
        raise SystemExit(f"error: {exc}")
    if args.json:
        print(json.dumps(packet, indent=2))
    else:
        print(f"active={packet['active_tongue']} schema={packet['schema_version']}")
    return 0


def cmd_pair_agent_training(args: argparse.Namespace) -> int:
    """Bridge the geoseal CLI to the GeoShell pair-agent SFT builder."""
    from scripts.training_data.build_geoshell_pair_agent_sft import (
        build_dataset,
        write_outputs,
    )

    try:
        dataset = build_dataset()
        paths = write_outputs(dataset, Path(args.output_dir), Path(args.event_path))
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(f"error: {exc}")
    payload = {
        "ok": True,
        "train_count": len(dataset["train"]),
        "holdout_count": len(dataset["holdout"]),
        "paths": paths,
        "geoshell_event_feed": paths["events"],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ok train={payload['train_count']} holdout={payload['holdout_count']} " f"manifest={paths['manifest']}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
