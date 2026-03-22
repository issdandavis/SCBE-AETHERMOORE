#!/usr/bin/env python3
"""
scbe — Unified SCBE-AETHERMOORE CLI

Single entry point for all SCBE operations with built-in AI task assistant.

Usage:
  scbe tongues encode --tongue ko --text "hello"
  scbe tongues decode --tongue ko --as-text --text "nav'or nav'uu"
  scbe tongues list
  scbe pipeline run --text "test input"
  scbe ai explain L12
  scbe ai lint src/crypto/h_lwe.py
  scbe ai review src/harmonic/mmx.ts
  scbe ai check src/harmonic/pipeline14.ts
  scbe selftest
  scbe status

Legacy commands (backward compat):
  scbe cli       — Launch interactive CLI
  scbe agent     — Launch AI agent
  scbe demo      — Run demo

@module cli/scbe
@layer Layer 14
@component Unified CLI + AI Onboard
@version 2.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "2.0.0"
REPO_ROOT = Path(__file__).resolve().parent
SCBE_PACKAGE_ROOT = REPO_ROOT / "src" / "scbe"

# Allow the root CLI module to behave as a package when other modules import
# `scbe.context_encoder` while `scbe.py` is already loaded.
if SCBE_PACKAGE_ROOT.is_dir():
    __path__ = [str(SCBE_PACKAGE_ROOT)]

FORWARDED_SYSTEM_COMMANDS = {
    "agent": ["agent"],
    "pollypad": ["pollypad"],
    "web": ["web"],
    "antivirus": ["antivirus"],
    "aetherauth": ["aetherauth"],
    "notion-gap": ["notion-gap"],
    "self-improve": ["self-improve"],
    "run": ["runtime", "run"],
}

# Handle SIGPIPE gracefully
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, OSError):
    pass  # Windows


# ═══════════════════════════════════════════════════════════════
# Canonical Sacred Tongue tables
# Source of truth: packages/kernel/src/sacredTongues.ts
# ═══════════════════════════════════════════════════════════════

_CANONICAL_TONGUES: Dict[str, Tuple[List[str], List[str]]] = {
    "KO": (
        ["sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
         "ra", "med", "gal", "lan", "joy", "good", "nex", "vara"],
        ["a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
         "or", "il", "an", "en", "un", "ir", "oth", "esh"],
    ),
    "AV": (
        ["saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
         "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide"],
        ["a", "e", "i", "o", "u", "y", "la", "re",
         "na", "sa", "to", "mi", "ve", "ri", "en", "ul"],
    ),
    "RU": (
        ["khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
         "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron"],
        ["ak", "eth", "ik", "ul", "or", "ar", "um", "on",
         "ir", "esh", "nul", "vek", "dra", "kh", "va", "th"],
    ),
    "CA": (
        ["bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
         "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass"],
        ["a", "e", "i", "o", "u", "y", "ta", "na",
         "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh"],
    ),
    "UM": (
        ["veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
         "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade"],
        ["a", "e", "i", "o", "u", "ae", "sh", "th",
         "ak", "ul", "or", "ir", "en", "on", "vek", "nul"],
    ),
    "DR": (
        ["anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
         "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember"],
        ["a", "e", "i", "o", "u", "ae", "rak", "mek",
         "tharn", "grond", "vek", "ul", "or", "ar", "en", "on"],
    ),
}

TONGUE_NAMES = {
    "KO": "Kor'aelin", "AV": "Avali", "RU": "Runethic",
    "CA": "Cassisivadan", "UM": "Umbroth", "DR": "Draumric",
}
TONGUE_DOMAINS = {
    "KO": "nonce/flow/intent", "AV": "aad/header/metadata", "RU": "salt/binding",
    "CA": "ciphertext/bitcraft", "UM": "redaction/veil", "DR": "tag/structure",
}


def _encode_byte(tongue: str, b: int) -> str:
    prefixes, suffixes = _CANONICAL_TONGUES[tongue]
    return f"{prefixes[(b >> 4) & 0xF]}'{suffixes[b & 0xF]}"


def _build_decode_map(tongue: str) -> Dict[str, int]:
    return {_encode_byte(tongue, i): i for i in range(256)}


# Pre-built decode maps — avoids rebuilding on every call
_DECODE_CACHE: Dict[str, Dict[str, int]] = {
    t: _build_decode_map(t) for t in _CANONICAL_TONGUES
}


def encode_bytes(tongue: str, data: bytes) -> str:
    tongue = tongue.upper()
    return " ".join(_encode_byte(tongue, b) for b in data)


def decode_tokens(tongue: str, text: str) -> bytes:
    tongue = tongue.upper()
    dmap = _DECODE_CACHE.get(tongue) or _build_decode_map(tongue)
    tokens = text.strip().split()
    out = bytearray()
    for tok in tokens:
        if tok in dmap:
            out.append(dmap[tok])
        else:
            raise ValueError(f"Unknown token '{tok}' in tongue {tongue}")
    return bytes(out)


# ═══════════════════════════════════════════════════════════════
# Pipeline (lightweight — no scipy/numpy required)
#
# Natural sieve: each layer preserves the input's shape and catches
# what it naturally catches.  Sand falls through; gold stays on the mesh.
#
#   L1-L3 proxy  →  raw byte statistics (character sieve)
#   L4-L5 proxy  →  distance from reference distribution (geometry sieve)
#   L6-L11 proxy →  variance / coherence check (dynamics sieve)
#   L12-L13      →  H(d, pd) = 1/(1+d+2*pd) → risk decision
# ═══════════════════════════════════════════════════════════════

# Reference byte-frequency distribution for "normal English prose".
# Derived from the character class ratios of a 100K-word fiction corpus.
_REF_PROFILE = {
    "alpha_ratio": 0.78,      # letters dominate
    "digit_ratio": 0.02,      # sparse digits
    "space_ratio": 0.16,      # word gaps
    "punct_ratio": 0.03,      # commas, periods, quotes
    "control_ratio": 0.0,     # zero control chars
    "highbyte_ratio": 0.0,    # zero non-ASCII in English baseline
    "shannon": 4.2,           # bits/byte for English text
    "bigram_shannon": 7.5,    # bits per character pair
    "repetition": 0.35,       # unique_bytes / total_bytes (moderate diversity)
}


def _byte_frequency(raw: bytes) -> List[int]:
    """Count occurrences of each byte value 0-255."""
    freq = [0] * 256
    for b in raw:
        freq[b] += 1
    return freq


def _shannon_entropy(freq: List[int], total: int) -> float:
    """Shannon entropy in bits/byte from a frequency table."""
    if total == 0:
        return 0.0
    h = 0.0
    for f in freq:
        if f > 0:
            p = f / total
            h -= p * math.log2(p)
    return h


def _bigram_entropy(raw: bytes) -> float:
    """Shannon entropy of byte pairs (bigrams)."""
    if len(raw) < 2:
        return 0.0
    counts: Dict[int, int] = {}
    for i in range(len(raw) - 1):
        key = (raw[i] << 8) | raw[i + 1]
        counts[key] = counts.get(key, 0) + 1
    total = len(raw) - 1
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def _char_class_profile(raw: bytes) -> Dict[str, float]:
    """L1-L3 proxy: decompose input into character class ratios."""
    n = len(raw) or 1  # avoid division by zero
    alpha = digit = space = punct = control = highbyte = 0
    for b in raw:
        if 65 <= b <= 90 or 97 <= b <= 122:
            alpha += 1
        elif 48 <= b <= 57:
            digit += 1
        elif b in (32, 9, 10, 13):
            space += 1
        elif 33 <= b <= 47 or 58 <= b <= 64 or 91 <= b <= 96 or 123 <= b <= 126:
            punct += 1
        elif b < 32 or b == 127:
            control += 1
        else:
            highbyte += 1
    return {
        "alpha_ratio": alpha / n,
        "digit_ratio": digit / n,
        "space_ratio": space / n,
        "punct_ratio": punct / n,
        "control_ratio": control / n,
        "highbyte_ratio": highbyte / n,
    }


def _distribution_distance(profile: Dict[str, float], freq: List[int],
                            total: int, bigram_h: float) -> float:
    """L4-L5 proxy: distance from reference distribution.

    Returns d* in [0, ~5] — higher means further from normal text.
    """
    # Treat alpha + highbyte together as "text characters" so that
    # non-Latin scripts (Japanese, Arabic, Cyrillic, etc.) aren't
    # penalized for having high bytes — they're still natural language.
    text_ratio = profile.get("alpha_ratio", 0.0) + profile.get("highbyte_ratio", 0.0)
    ref_text_ratio = _REF_PROFILE["alpha_ratio"] + _REF_PROFILE["highbyte_ratio"]

    # Ratio divergence on structural axes (text vs digits vs control)
    ratio_div = (
        (text_ratio - ref_text_ratio) ** 2
        + (profile.get("digit_ratio", 0.0) - _REF_PROFILE["digit_ratio"]) ** 2
        + (profile.get("space_ratio", 0.0) - _REF_PROFILE["space_ratio"]) ** 2
        + (profile.get("punct_ratio", 0.0) - _REF_PROFILE["punct_ratio"]) ** 2
        + (profile.get("control_ratio", 0.0) - _REF_PROFILE["control_ratio"]) ** 2 * 4.0
    )

    # Shannon divergence from reference
    shannon = _shannon_entropy(freq, total)
    shannon_div = abs(shannon - _REF_PROFILE["shannon"]) / 8.0

    # Bigram divergence
    bigram_div = abs(bigram_h - _REF_PROFILE["bigram_shannon"]) / 16.0

    # Repetition divergence: unique bytes / total
    unique_bytes = sum(1 for f in freq if f > 0)
    rep = unique_bytes / 256.0 if total > 0 else 0.0
    rep_div = abs(rep - _REF_PROFILE["repetition"])

    # Weighted combination — ratio divergence dominates because it captures
    # the coarsest structural signal (what KIND of bytes are present).
    # The sqrt on ratio_div keeps the scale human-readable.
    d_star = (
        5.0 * math.sqrt(ratio_div)    # character class mismatch
        + 1.5 * shannon_div            # information density mismatch
        + 1.0 * bigram_div             # sequential pattern mismatch
        + 0.8 * rep_div                # byte diversity mismatch
    )

    return d_star


def _phase_deviation(profile: Dict[str, float], d_star: float,
                     total: int) -> float:
    """L6-L11 proxy: coherence / phase deviation.

    Catches inputs that look structurally normal but have suspicious
    internal dynamics — high control char ratios, degenerate repetition,
    extreme length anomalies.
    """
    # Control chars are phase red flags; high bytes alone are not
    # (they could be UTF-8 natural language)
    phase = profile["control_ratio"] * 4.0

    # Extreme length: very short or very long inputs get a small bump
    if total == 0:
        phase += 0.3
    elif total < 5:
        phase += 0.15
    elif total > 500_000:
        phase += 0.1

    # Near-zero d* but high digit ratio = possible encoded payload
    if d_star < 0.3 and profile["digit_ratio"] > 0.3:
        phase += 0.2

    return min(phase, 2.0)


def pipeline_quick_score(text: str) -> Dict[str, Any]:
    """Lightweight 14-layer scoring — natural sieve, no hash.

    Each stage preserves the input's statistical shape and catches
    what it naturally catches.  The canonical formula
    H(d, pd) = 1/(1 + d + 2*pd) compresses the findings into a
    bounded safety score in (0, 1].
    """
    raw = text.encode("utf-8")
    n = len(raw)

    # L1-L3: character sieve — let the input's natural shape emerge
    freq = _byte_frequency(raw)
    profile = _char_class_profile(raw)
    bigram_h = _bigram_entropy(raw)

    # L4-L5: geometry sieve — how far from normal text?
    d_star = _distribution_distance(profile, freq, n, bigram_h)

    # L6-L11: dynamics sieve — coherence and phase checks
    pd = _phase_deviation(profile, d_star, n)

    # L12: harmonic wall — canonical bounded formula
    H_eff = 1.0 / (1.0 + d_star + 2.0 * pd)

    # L13: risk decision
    if H_eff >= 0.75:
        decision = "ALLOW"
    elif H_eff >= 0.45:
        decision = "QUARANTINE"
    elif H_eff >= 0.2:
        decision = "ESCALATE"
    else:
        decision = "DENY"

    # Poincare ball coordinate for display (tanh projection of d*)
    x_poincare = math.tanh(d_star)

    # Provenance digest (for audit trail, not for scoring)
    digest = hashlib.sha256(raw).digest()

    return {
        "input_len": n,
        "d_star": round(d_star, 6),
        "x_poincare": round(x_poincare, 6),
        "H_eff": round(H_eff, 6),
        "phase_deviation": round(pd, 6),
        "decision": decision,
        "digest_hex": digest[:16].hex(),
    }


# ═══════════════════════════════════════════════════════════════
# AI Onboard — lightweight code task assistant
# ═══════════════════════════════════════════════════════════════

LAYER_GUIDE = {
    "L1": ("Complex Context", "Realification of complex-valued input"),
    "L2": ("Realification", "Complex -> real projection, norm preservation (Unitarity axiom)"),
    "L3": ("Weighted Transform", "Langues metric / Sacred Tongues 6D weighting (Locality axiom)"),
    "L4": ("Poincare Embedding", "Map to Poincare ball via tanh projection (Unitarity axiom)"),
    "L5": ("Hyperbolic Distance", "Poincare ball distance — invariant under Mobius (Symmetry axiom)"),
    "L6": ("Breathing", "Oscillatory modulation for dynamic stability (Causality axiom)"),
    "L7": ("Mobius Phase", "Mobius transformation phase alignment (Unitarity axiom)"),
    "L8": ("Multi-Well Realms", "Hamiltonian multi-well energy landscapes (Locality axiom)"),
    "L9": ("Spectral Coherence", "FFT coherence analysis (Symmetry axiom)"),
    "L10": ("Spin Coherence", "Spin-state alignment verification (Symmetry axiom)"),
    "L11": ("Triadic Temporal", "3-way temporal distance measure (Causality axiom)"),
    "L12": ("Harmonic Wall", "H(d,p) = 1/(1+d+2pd) — exponential cost scaling (Symmetry axiom)"),
    "L13": ("Risk Decision", "ALLOW/QUARANTINE/ESCALATE/DENY governance (Causality axiom)"),
    "L14": ("Audio Axis", "FFT telemetry, sonification, cymatic output (Composition axiom)"),
}


def ai_explain(target: str) -> str:
    """Explain a layer or concept."""
    t = target.upper().replace("LAYER", "L").replace(" ", "")
    if t in LAYER_GUIDE:
        name, desc = LAYER_GUIDE[t]
        return f"{t}: {name}\n  {desc}"
    for k, (name, desc) in LAYER_GUIDE.items():
        if t in name.upper() or t in desc.upper():
            return f"{k}: {name}\n  {desc}"
    return f"Unknown target: {target}. Try L1-L14, or a concept like 'harmonic', 'breathing', 'poincare'."


def ai_lint(filepath: str) -> Dict[str, Any]:
    """Lint a source file — check syntax, headers, coding patterns."""
    p = Path(filepath)
    if not p.exists():
        return {"error": f"File not found: {filepath}"}

    issues: List[str] = []
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append(f"  L{i}: line too long ({len(line)} > 120 chars)")
        if "TODO" in line.upper() or "FIXME" in line.upper() or "HACK" in line.upper():
            issues.append(f"  L{i}: {line.strip()[:80]}")

    has_header = "@file" in content[:500] or "@module" in content[:500]
    has_layer = "@layer" in content[:1000]

    result: Dict[str, Any] = {
        "file": filepath,
        "lines": len(lines),
        "has_header": has_header,
        "has_layer_tag": has_layer,
        "issues": issues[:20],
        "issue_count": len(issues),
    }

    if p.suffix == ".py":
        try:
            compile(content, filepath, "exec")
            result["compiles"] = True
        except SyntaxError as e:
            result["compiles"] = False
            result["syntax_error"] = f"Line {e.lineno}: {e.msg}"

    return result


def ai_review(filepath: str) -> Dict[str, Any]:
    """Quick code review — structure, complexity, patterns."""
    p = Path(filepath)
    if not p.exists():
        return {"error": f"File not found: {filepath}"}

    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    blank = sum(1 for l in lines if not l.strip())
    comments = sum(1 for l in lines if l.strip().startswith(("#", "//", "*", "/*")))
    code_lines = len(lines) - blank - comments

    if p.suffix in (".ts", ".js"):
        funcs = sum(1 for l in lines if "function " in l or "=> {" in l)
        classes = sum(1 for l in lines if l.strip().startswith(("class ", "export class")))
    else:
        funcs = sum(1 for l in lines if l.strip().startswith("def "))
        classes = sum(1 for l in lines if l.strip().startswith("class "))

    max_indent = max((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)

    warnings: List[str] = []
    if code_lines > 500:
        warnings.append(f"Large file ({code_lines} code lines) — consider splitting")
    if max_indent > 24:
        warnings.append(f"Deep nesting (max indent: {max_indent} spaces)")
    if funcs > 30:
        warnings.append(f"Many functions ({funcs}) — consider module decomposition")

    return {
        "file": filepath,
        "total_lines": len(lines),
        "code_lines": code_lines,
        "blank_lines": blank,
        "comment_lines": comments,
        "functions": funcs,
        "classes": classes,
        "max_indent": max_indent,
        "warnings": warnings,
        "verdict": "OK" if not warnings else f"{len(warnings)} suggestion(s)",
    }


# ═══════════════════════════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════════════════════════

def cmd_status(_args: argparse.Namespace) -> int:
    ts_files = list(REPO_ROOT.glob("src/**/*.ts"))
    py_files = list(REPO_ROOT.glob("src/**/*.py"))
    test_ts = list(REPO_ROOT.glob("tests/**/*.test.ts"))
    test_py = list(REPO_ROOT.glob("tests/**/test_*.py"))

    print(f"SCBE-AETHERMOORE v{VERSION}")
    print(f"  TypeScript: {len(ts_files)} sources, {len(test_ts)} tests")
    print(f"  Python:     {len(py_files)} sources, {len(test_py)} tests")
    print()
    print("Sacred Tongues:")
    for code in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        prefixes, suffixes = _CANONICAL_TONGUES[code]
        print(f"  {code} ({TONGUE_NAMES[code]}): {len(prefixes)*len(suffixes)} tokens — {TONGUE_DOMAINS[code]}")
    print()
    print("14-Layer Pipeline:")
    for layer, (name, _) in LAYER_GUIDE.items():
        print(f"  {layer}: {name}")
    return 0


def cmd_tongue_encode(args: argparse.Namespace) -> int:
    tongue = args.tongue.upper()
    data = args.text.encode("utf-8") if getattr(args, "text", None) else sys.stdin.buffer.read()
    print(encode_bytes(tongue, data))
    return 0


def cmd_tongue_decode(args: argparse.Namespace) -> int:
    tongue = args.tongue.upper()
    text = args.text if getattr(args, "text", None) else sys.stdin.read()
    data = decode_tokens(tongue, text)
    if getattr(args, "as_text", False):
        print(data.decode("utf-8", errors="replace"))
    else:
        sys.stdout.buffer.write(data)
    return 0


def cmd_tongue_list(_args: argparse.Namespace) -> int:
    for code in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        prefixes, suffixes = _CANONICAL_TONGUES[code]
        print(f"{code} — {TONGUE_NAMES[code]} ({TONGUE_DOMAINS[code]})")
        print(f"  Prefixes: {', '.join(prefixes)}")
        print(f"  Suffixes: {', '.join(suffixes)}")
        print(f"  Samples:  {_encode_byte(code, 0)}, {_encode_byte(code, 42)}, {_encode_byte(code, 255)}")
        print()
    return 0


def cmd_pipeline_run(args: argparse.Namespace) -> int:
    text = args.text if getattr(args, "text", None) else sys.stdin.read().strip()
    result = pipeline_quick_score(text)
    if getattr(args, "json_output", False):
        print(json.dumps(result, indent=2))
    else:
        print(f"Input:    {text[:60]}{'...' if len(text) > 60 else ''}")
        print(f"d*:       {result['d_star']}")
        print(f"x:        {result['x_poincare']}")
        print(f"H_eff:    {result['H_eff']}")
        print(f"Decision: {result['decision']}")
    return 0


def cmd_ai_explain(args: argparse.Namespace) -> int:
    print(ai_explain(args.target))
    return 0


def cmd_ai_lint(args: argparse.Namespace) -> int:
    result = ai_lint(args.file)
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    print(f"File: {result['file']} ({result['lines']} lines)")
    if result.get("compiles") is False:
        print(f"  SYNTAX ERROR: {result['syntax_error']}")
    elif result.get("compiles") is True:
        print("  Compiles: OK")
    print(f"  Header: {'yes' if result['has_header'] else 'MISSING'}")
    print(f"  @layer:  {'yes' if result['has_layer_tag'] else 'MISSING'}")
    if result["issues"]:
        print(f"  Issues ({result['issue_count']}):")
        for iss in result["issues"]:
            print(f"    {iss}")
    else:
        print("  No issues found")
    return 0


def cmd_ai_review(args: argparse.Namespace) -> int:
    result = ai_review(args.file)
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    print(f"File: {result['file']}")
    print(f"  Lines: {result['total_lines']} total, {result['code_lines']} code, "
          f"{result['blank_lines']} blank, {result['comment_lines']} comments")
    print(f"  Functions: {result['functions']}, Classes: {result['classes']}")
    print(f"  Max indent: {result['max_indent']} spaces")
    print(f"  Verdict: {result['verdict']}")
    for w in result.get("warnings", []):
        print(f"    - {w}")
    return 0


def cmd_ai_check(args: argparse.Namespace) -> int:
    """Full lint + review."""
    lint_result = ai_lint(args.file)
    review_result = ai_review(args.file)
    if "error" in lint_result:
        print(f"Error: {lint_result['error']}")
        return 1

    print(f"=== {args.file} ===")
    print(f"  {review_result['code_lines']} code, "
          f"{review_result['functions']} funcs, {review_result['classes']} classes")

    all_ok = True
    if lint_result.get("compiles") is False:
        print(f"  FAIL: {lint_result['syntax_error']}")
        all_ok = False
    if not lint_result["has_header"]:
        print("  WARN: missing @file/@module header")
    if lint_result["issue_count"] > 0:
        print(f"  LINT: {lint_result['issue_count']} issue(s)")
        for iss in lint_result["issues"][:5]:
            print(f"    {iss}")
    for w in review_result.get("warnings", []):
        print(f"  REVIEW: {w}")
        all_ok = False

    if all_ok and lint_result["issue_count"] == 0:
        print("  All checks passed")
    return 0


def cmd_docs_scan(_args: argparse.Namespace) -> int:
    """Delegate to doc_verifier.py for doc scanning."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "training" / "doc_verifier.py")],
    ).returncode


def cmd_docs_verify(args: argparse.Namespace) -> int:
    manifest_path = args.manifest
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "training" / "doc_verifier.py"), "--check", manifest_path],
    ).returncode


def cmd_docs_attest(args: argparse.Namespace) -> int:
    out_path = getattr(args, "out", "training/doc_manifest.json")
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "training" / "doc_verifier.py"),
         "--attest", args.members, "--out", out_path],
    ).returncode


def cmd_selftest(_args: argparse.Namespace) -> int:
    errors = 0
    print("=== SCBE Unified CLI Self-Test ===\n")

    # Tongue roundtrip
    print("[1] Tongue Roundtrip")
    for tongue in _CANONICAL_TONGUES:
        original = b"hello SCBE world! \x00\xff"
        encoded = encode_bytes(tongue, original)
        decoded = decode_tokens(tongue, encoded)
        if decoded != original:
            print(f"  FAIL: {tongue} roundtrip")
            errors += 1
        else:
            print(f"  {tongue}: OK ({len(encoded.split())} tokens)")

    # Cross-tongue
    print("\n[2] Cross-Tongue")
    ko_enc = encode_bytes("KO", b"cross test")
    ko_dec = decode_tokens("KO", ko_enc)
    av_enc = encode_bytes("AV", ko_dec)
    av_dec = decode_tokens("AV", av_enc)
    if av_dec != b"cross test":
        print("  FAIL: KO->AV roundtrip")
        errors += 1
    else:
        print("  KO->AV roundtrip: OK")

    # Pipeline
    print("\n[3] Pipeline")
    score = pipeline_quick_score("test input")
    if score["decision"] not in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY"):
        print("  FAIL: invalid decision")
        errors += 1
    else:
        print(f"  Score: H_eff={score['H_eff']}, decision={score['decision']}")

    # AI lint self-check
    print("\n[4] AI Onboard")
    lint = ai_lint(__file__)
    if lint.get("compiles") is False:
        print(f"  FAIL: self-lint error: {lint['syntax_error']}")
        errors += 1
    else:
        print(f"  Self-lint: OK ({lint['lines']} lines, {lint['issue_count']} issues)")

    print()
    if errors == 0:
        print("selftest OK — all checks passed")
    else:
        print(f"selftest FAILED — {errors} error(s)")
    return 1 if errors else 0


def _run_system_cli(args: List[str]) -> int:
    script = REPO_ROOT / "scripts" / "scbe-system-cli.py"
    if not script.exists():
        print(f"System CLI not found: {script}")
        return 1
    return subprocess.run(
        [sys.executable, str(script), "--repo-root", str(REPO_ROOT), *args],
        check=False,
    ).returncode


# ═══════════════════════════════════════════════════════════════
# Legacy command bridge (backward compatibility)
# ═══════════════════════════════════════════════════════════════

LEGACY_SCRIPTS = {
    "cli": "scbe-cli.py",
    "agent": "scbe-agent.py",
    "demo": "demo-cli.py",
    "memory": "demo_memory_shard.py",
}


# ═══════════════════════════════════════════════════════════════
# CLI builder
# ═══════════════════════════════════════════════════════════════

ALL_TONGUES = list(_CANONICAL_TONGUES.keys()) + [t.lower() for t in _CANONICAL_TONGUES]


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scbe",
        description="SCBE-AETHERMOORE — Unified CLI for crypto, governance, and AI safety",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scbe tongues encode --tongue ko --text "hello"
  scbe tongues decode --tongue ko --as-text --text "nav'or nav'uu"
  scbe tongues list
  scbe pipeline run --text "test input"
  scbe pipeline run --json --text "analyze this"
  scbe ai explain L12
  scbe ai lint src/crypto/h_lwe.py
  scbe ai review src/harmonic/mmx.ts
  scbe ai check src/harmonic/pipeline14.ts
  scbe docs scan                            Discover and count docs
  scbe docs verify                          Verify existing manifest
  scbe docs attest claude,gpt,sonar         Attest with 3 council members
  scbe selftest
  scbe status

Legacy (backward compat):
  scbe cli                          Interactive CLI
  scbe agent                        AI agent
  scbe demo                         Demo mode
  scbe pollypad init --agent-id rex --name "Rex"
  scbe run --language python --code "print('SCBE')"
        """,
    )
    sub = p.add_subparsers(dest="command")

    # ─── tongues ───
    tongues = sub.add_parser("tongues", help="Sacred Tongue tokenization")
    tongues_sub = tongues.add_subparsers(dest="tongue_cmd")

    te = tongues_sub.add_parser("encode", help="Encode bytes to tokens")
    te.add_argument("--tongue", required=True, choices=ALL_TONGUES)
    te.add_argument("--text", help="Inline text (default: stdin)")
    te.set_defaults(func=cmd_tongue_encode)

    td = tongues_sub.add_parser("decode", help="Decode tokens to bytes")
    td.add_argument("--tongue", required=True, choices=ALL_TONGUES)
    td.add_argument("--text", help="Token string (default: stdin)")
    td.add_argument("--as-text", action="store_true", help="Output UTF-8 text")
    td.set_defaults(func=cmd_tongue_decode)

    tl = tongues_sub.add_parser("list", help="List all 6 Sacred Tongues")
    tl.set_defaults(func=cmd_tongue_list)

    # ─── pipeline ───
    pipeline = sub.add_parser("pipeline", help="14-layer governance pipeline")
    pipeline_sub = pipeline.add_subparsers(dest="pipeline_cmd")

    pr = pipeline_sub.add_parser("run", help="Score input through pipeline")
    pr.add_argument("--text", help="Input text (default: stdin)")
    pr.add_argument("--json", dest="json_output", action="store_true")
    pr.set_defaults(func=cmd_pipeline_run)

    # ─── ai ───
    ai = sub.add_parser("ai", help="AI onboard — code task assistant")
    ai_sub = ai.add_subparsers(dest="ai_cmd")

    ae = ai_sub.add_parser("explain", help="Explain a pipeline layer (L1-L14)")
    ae.add_argument("target", help="Layer (L12) or concept (harmonic, breathing)")
    ae.set_defaults(func=cmd_ai_explain)

    al = ai_sub.add_parser("lint", help="Lint a source file")
    al.add_argument("file", help="File path")
    al.set_defaults(func=cmd_ai_lint)

    ar = ai_sub.add_parser("review", help="Quick code review")
    ar.add_argument("file", help="File path")
    ar.set_defaults(func=cmd_ai_review)

    ac = ai_sub.add_parser("check", help="Full lint + review")
    ac.add_argument("file", help="File path")
    ac.set_defaults(func=cmd_ai_check)

    # ─── docs ───
    docs = sub.add_parser("docs", help="Document verification (Round Table consensus)")
    docs_sub = docs.add_subparsers(dest="docs_cmd")

    ds = docs_sub.add_parser("scan", help="Scan and summarize project docs")
    ds.set_defaults(func=cmd_docs_scan)

    dv = docs_sub.add_parser("verify", help="Verify existing doc_manifest.json")
    dv.add_argument("--manifest", default="training/doc_manifest.json")
    dv.set_defaults(func=cmd_docs_verify)

    da = docs_sub.add_parser("attest", help="Attest docs with council members")
    da.add_argument("members", help="Comma-separated: claude,gpt,sonar,grok,gemini")
    da.add_argument("--out", default="training/doc_manifest.json")
    da.set_defaults(func=cmd_docs_attest)

    # ─── top-level ───
    sub.add_parser("status", help="Project status").set_defaults(func=cmd_status)
    sub.add_parser("selftest", help="Self-test suite").set_defaults(func=cmd_selftest)
    sub.add_parser("pollypad", help="Polly Pad storage + app management (forwarded to system CLI)")
    sub.add_parser("run", help="Governed multi-language runtime (forwarded to system CLI)")
    sub.add_parser("web", help="Web lookup/capture helpers (forwarded to system CLI)")
    sub.add_parser("antivirus", help="Safety scan helpers (forwarded to system CLI)")
    sub.add_parser("aetherauth", help="Context-bound access decisions (forwarded to system CLI)")
    sub.add_parser("notion-gap", help="Notion/pipeline gap review (forwarded to system CLI)")
    sub.add_parser("self-improve", help="Self-improvement orchestration (forwarded to system CLI)")

    # ─── legacy ───
    for cmd in LEGACY_SCRIPTS:
        sub.add_parser(cmd, help=f"(legacy) Launch {cmd}")

    return p


def main() -> int:
    if len(sys.argv) == 1:
        cli = build_cli()
        cli.print_help()
        return 0

    forwarded = FORWARDED_SYSTEM_COMMANDS.get(sys.argv[1])
    if forwarded is not None:
        return _run_system_cli([*forwarded, *sys.argv[2:]])

    cli = build_cli()

    # Handle legacy commands
    if len(sys.argv) >= 2 and sys.argv[1] in LEGACY_SCRIPTS:
        script = REPO_ROOT / LEGACY_SCRIPTS[sys.argv[1]]
        if script.exists():
            return subprocess.run([sys.executable, str(script)] + sys.argv[2:]).returncode
        else:
            print(f"Legacy script not found: {script}")
            return 1

    args = cli.parse_args()
    if not hasattr(args, "func"):
        cli.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
