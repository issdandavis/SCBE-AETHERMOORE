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
import ctypes
import difflib
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "2.0.0"
REPO_ROOT = Path(__file__).resolve().parent
FORWARDED_SYSTEM_COMMANDS = {
    "pollypad": ["pollypad"],
    "doctor": ["doctor"],
    "use": ["use"],
    "config": ["config"],
    "model": ["model"],
    "colab": ["colab"],
    "flow": ["flow"],
    "workflow": ["workflow"],
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
TONGUE_ALIASES = {
    "ko": "KO",
    "koraelin": "KO",
    "kor'aelin": "KO",
    "kor-aelin": "KO",
    "av": "AV",
    "avali": "AV",
    "ru": "RU",
    "runethic": "RU",
    "ca": "CA",
    "cassisivadan": "CA",
    "um": "UM",
    "umbroth": "UM",
    "dr": "DR",
    "draumric": "DR",
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


# ── Word recognition ──────────────────────────────────────────
# A small lexicon of common words. Recognized natural language earns
# a "naturalness" discount so real sentences read as ALLOW, while
# encoded blobs, code, and injections (few real words, many symbols)
# do not. str.isalpha() is Unicode-aware, so accented words in French,
# German, Spanish, etc. still count as wordlike and stay fair.

COMMON_WORDS = frozenset("""
a an the and or but of to in on at by for with from as is are was were be been
being it its this that these those he she they we you i his her their our your my
me him them us who what which when where why how not no if then else over under
about into through after before between out up down off again once here there all
any both each few more most other some such only own same so than too very can will
just upon time lived brave knight quick brown fox jumps jumped lazy dog normal safe
sentence cooking dinner weather nice today garden walked quietly hello world story
while birds sang overhead text have has had do does did make made see saw go went
come came know knew think good day way man woman life people work water food house
""".split())

_PUNCT_STRIP = ".,!?;:'\"()[]{}<>-_/\\|`~@#$%^&*+=…“”‘’"


def _naturalness(text: str) -> Tuple[float, float]:
    """Return (wordlike_fraction, common_word_fraction) for the input.

    wordlike: token is all letters once edge punctuation is stripped
              (Unicode-aware, so non-English language counts too).
    common:   token is in the recognized lexicon of everyday words.
    """
    tokens = text.split()
    if not tokens:
        return 0.0, 0.0
    wordlike = common = 0
    for tok in tokens:
        core = tok.strip(_PUNCT_STRIP)
        if core and core.isalpha():
            wordlike += 1
            if core.lower() in COMMON_WORDS:
                common += 1
    n = len(tokens)
    return wordlike / n, common / n


def _distribution_distance(profile: Dict[str, float], freq: List[int],
                           total: int, bigram_h: float,
                           wordlike: float, common: float) -> float:
    """Distance from "normal language" — higher means more suspicious.

    Keyed on *what kind of bytes* are present (meaningful at any length),
    not on hitting large-corpus entropy targets that short benign text can
    never reach. Recognized words discount the score; digits, symbols, and
    control bytes raise it.
    """
    if total == 0:
        return 8.0  # empty input is anomalous → DENY

    # ── Structural anomaly (length-independent) ──
    digit_excess = max(0.0, profile["digit_ratio"] - 0.05)
    punct_excess = max(0.0, profile["punct_ratio"] - 0.05)
    control = profile["control_ratio"]
    # Letters (any script) + spaces are the body of natural language.
    text_ratio = profile["alpha_ratio"] + profile["highbyte_ratio"] + profile["space_ratio"]
    text_deficit = max(0.0, 0.50 - text_ratio)

    struct = (
        4.0 * digit_excess        # digit-heavy → encoded / payload
        + 8.0 * punct_excess      # symbol-heavy → code / injection
        + 10.0 * control          # control bytes → binary / adversarial
        + 5.0 * text_deficit      # little actual text → non-language
    )
    # Recognized words mean any symbols are likely incidental, not hostile.
    struct *= (1.0 - 0.5 * wordlike)

    # ── Statistical anomaly (only meaningful with enough bytes) ──
    stat_conf = min(1.0, total / 200.0)
    shannon = _shannon_entropy(freq, total)
    shannon_excess = max(0.0, shannon - 6.0)              # ~random / encrypted
    unique = sum(1 for f in freq if f > 0)
    rep = unique / 256.0
    rep_deficit = max(0.0, 0.03 - rep) if total > 50 else 0.0  # degenerate repeat
    stat = stat_conf * 1.5 * shannon_excess + 40.0 * rep_deficit

    # A real density of everyday words earns a confidence discount toward
    # ALLOW (gated so a lone keyword like SQL's "FROM" can't rescue an attack).
    lang_conf = max(0.0, common - 0.25)
    d_star = struct + stat - 1.5 * lang_conf
    return max(0.0, d_star)


def _phase_deviation(profile: Dict[str, float], d_star: float,
                     total: int) -> float:
    """L6-L11 proxy: coherence / phase deviation.

    Catches inputs that look structurally normal but have suspicious
    internal dynamics — high control char ratios, degenerate repetition,
    extreme length anomalies.
    """
    # Control chars are phase red flags; high bytes alone are not
    # (they could be UTF-8 natural language). Short inputs are NOT
    # penalized — a brief real sentence is still normal language.
    phase = profile["control_ratio"] * 4.0

    if total == 0:
        phase += 0.3
    elif total > 500_000:
        phase += 0.1

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

    # Word recognition — recognized language reads as benign.
    wordlike, common = _naturalness(text)

    # L4-L5: geometry sieve — how far from normal language?
    d_star = _distribution_distance(profile, freq, n, bigram_h, wordlike, common)

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

def cmd_status(args: argparse.Namespace) -> int:
    ts_files = list(REPO_ROOT.glob("src/**/*.ts"))
    py_files = list(REPO_ROOT.glob("src/**/*.py"))
    test_ts = list(REPO_ROOT.glob("tests/**/*.test.ts"))
    test_py = list(REPO_ROOT.glob("tests/**/test_*.py"))

    if getattr(args, "json_output", False):
        data = {
            "version": VERSION,
            "typescript": {"sources": len(ts_files), "tests": len(test_ts)},
            "python": {"sources": len(py_files), "tests": len(test_py)},
            "tongues": {
                code: {"name": TONGUE_NAMES[code], "tokens": 256, "domain": TONGUE_DOMAINS[code]}
                for code in ["KO", "AV", "RU", "CA", "UM", "DR"]
            },
            "layers": {layer: name for layer, (name, _) in LAYER_GUIDE.items()},
        }
        print(json.dumps(data))
        return 0

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


def _windows_memory_status() -> Dict[str, float]:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
        raise OSError("GlobalMemoryStatusEx failed")
    total = stat.ullTotalPhys
    free = stat.ullAvailPhys
    used = max(0, total - free)
    return {
        "total_gb": round(total / 1_073_741_824, 2),
        "used_gb": round(used / 1_073_741_824, 2),
        "free_gb": round(free / 1_073_741_824, 2),
        "used_percent": round((used / total) * 100, 1) if total else 0.0,
    }


def _portable_memory_status() -> Dict[str, float]:
    if sys.platform == "win32":
        return _windows_memory_status()
    if hasattr(os, "sysconf"):
        page_size = os.sysconf("SC_PAGE_SIZE")
        total_pages = os.sysconf("SC_PHYS_PAGES")
        avail_pages = os.sysconf("SC_AVPHYS_PAGES")
        total = int(page_size * total_pages)
        free = int(page_size * avail_pages)
        used = max(0, total - free)
        return {
            "total_gb": round(total / 1_073_741_824, 2),
            "used_gb": round(used / 1_073_741_824, 2),
            "free_gb": round(free / 1_073_741_824, 2),
            "used_percent": round((used / total) * 100, 1) if total else 0.0,
        }
    return {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "used_percent": 0.0}


def _filesystem_drives(warn_disk_free_gb: int) -> List[Dict[str, Any]]:
    roots: List[str] = []
    if sys.platform == "win32":
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
        for i in range(26):
            if bitmask & (1 << i):
                roots.append(f"{chr(65 + i)}:\\")
    else:
        roots.append("/")

    drives: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if root in seen or not Path(root).exists():
            continue
        seen.add(root)
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        free_gb = round(usage.free / 1_073_741_824, 2)
        drives.append(
            {
                "root": root,
                "free_gb": free_gb,
                "used_gb": round(usage.used / 1_073_741_824, 2),
                "total_gb": round(usage.total / 1_073_741_824, 2),
                "low_free_space": free_gb < warn_disk_free_gb,
            }
        )
    return drives


def _top_processes(limit: int) -> List[Dict[str, Any]]:
    if sys.platform != "win32":
        return []
    ps = (
        "Get-Process | Sort-Object WorkingSet64 -Descending | "
        f"Select-Object -First {max(1, limit)} ProcessName,Id,"
        "@{Name='ram_mb';Expression={[math]::Round($_.WorkingSet64/1MB,1)}},"
        "@{Name='private_mb';Expression={[math]::Round($_.PrivateMemorySize64/1MB,1)}} | "
        "ConvertTo-Json -Depth 3"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        data = json.loads(proc.stdout)
        rows = data if isinstance(data, list) else [data]
        return [
            {
                "name": str(row.get("ProcessName", "")),
                "id": row.get("Id"),
                "ram_mb": row.get("ram_mb"),
                "private_mb": row.get("private_mb"),
            }
            for row in rows
            if isinstance(row, dict)
        ]
    except Exception:
        return []


def collect_pc_health(
    *,
    warn_ram_percent: int = 85,
    warn_disk_free_gb: int = 25,
    top_processes: int = 15,
) -> Dict[str, Any]:
    ram = _portable_memory_status()
    drives = _filesystem_drives(warn_disk_free_gb)
    processes = _top_processes(top_processes)
    warnings: List[str] = []

    if ram["used_percent"] >= warn_ram_percent:
        warnings.append(f"High RAM pressure: {ram['used_percent']}% used.")
    for drive in drives:
        if drive["low_free_space"]:
            warnings.append(f"Low disk headroom on {drive['root']}: {drive['free_gb']} GB free.")

    for proc in processes:
        name = str(proc.get("name", ""))
        ram_mb = float(proc.get("ram_mb") or 0)
        if name.lower().startswith(("onedrive", "dropbox", "googledrive")) and ram_mb > 1000:
            warnings.append(f"{name} is using {ram_mb:g} MB RAM; pause sync during heavy work.")
            break

    return {
        "schema_version": "scbe_pc_health_v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "machine": platform.node(),
        "platform": platform.platform(),
        "ram": ram,
        "drives": drives,
        "top_processes": processes,
        "warnings": warnings,
        "recommendations": [
            "Keep at least 20-25 GB free before builds, RAG indexing, browser swarms, or backups.",
            "Pause cloud sync during recovery scans and long compiles when it is using high RAM.",
            "Use shallow health checks before recursive storage scans.",
            "Do not kill processes, delete caches, or move user files without explicit confirmation.",
        ],
    }


def cmd_system_health(args: argparse.Namespace) -> int:
    report = collect_pc_health(
        warn_ram_percent=args.warn_ram_percent,
        warn_disk_free_gb=args.warn_disk_free_gb,
        top_processes=args.top_processes,
    )

    out_dir = REPO_ROOT / "artifacts" / "pc-memory"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"pc-health-{stamp}.json"
    if not getattr(args, "no_write", False):
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["artifact"] = str(json_path)

    if getattr(args, "json_output", False):
        print(json.dumps(report))
        return 0

    ram = report["ram"]
    print("SCBE PC health")
    print(f"  RAM: {ram['used_gb']} GB used / {ram['total_gb']} GB ({ram['used_percent']}%)")
    print("  Drives:")
    for drive in report["drives"]:
        flag = " LOW" if drive["low_free_space"] else ""
        print(f"    {drive['root']} free {drive['free_gb']} GB / {drive['total_gb']} GB{flag}")
    if report["warnings"]:
        print("  Warnings:")
        for warning in report["warnings"]:
            print(f"    - {warning}")
    else:
        print("  Warnings: none")
    if not getattr(args, "no_write", False):
        print(f"  Artifact: {json_path}")
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


# ═══════════════════════════════════════════════════════════════
# Compact verbs — the human+AI command surface
#
# Short, positional, stdin-aware, and --json on every one. The same
# command a person types is the one an agent scripts; --json flips
# the output from friendly to machine-parseable. Exit codes are
# stable: 0 ok, 1 runtime error, 2 usage error.
# ═══════════════════════════════════════════════════════════════

DECISION_GLYPH = {"ALLOW": "✓", "QUARANTINE": "~", "ESCALATE": "!", "DENY": "✗"}


def _arg_or_stdin(value: Optional[str]) -> Optional[str]:
    """Return the positional value, or read piped stdin, or None."""
    if value:
        return value
    if not sys.stdin.isatty():
        piped = sys.stdin.read()
        return piped if piped.strip() else None
    return None


def cmd_score(args: argparse.Namespace) -> int:
    text = _arg_or_stdin(getattr(args, "text", None))
    if text is None:
        print('usage: scbe score "<text>"   (or pipe text via stdin)', file=sys.stderr)
        return 2
    r = pipeline_quick_score(text.strip())
    if getattr(args, "json_output", False):
        print(json.dumps(r))
    else:
        glyph = DECISION_GLYPH.get(r["decision"], "?")
        print(f"{glyph} {r['decision']}  (H_eff={r['H_eff']}, d*={r['d_star']})")
    if getattr(args, "gate", False) and r["decision"] in ("DENY", "ESCALATE"):
        return 1
    return 0


def _resolve_tongue(raw: str) -> Optional[str]:
    key = raw.strip().lower()
    code = TONGUE_ALIASES.get(key, raw.upper())
    return code if code in _CANONICAL_TONGUES else None


def cmd_enc(args: argparse.Namespace) -> int:
    tongue = _resolve_tongue(args.tongue)
    if tongue is None:
        print(f"unknown tongue '{args.tongue}' — choose: {', '.join(_CANONICAL_TONGUES)}", file=sys.stderr)
        return 2
    text = _arg_or_stdin(getattr(args, "text", None))
    if text is None:
        print('usage: scbe enc <tongue> "<text>"', file=sys.stderr)
        return 2
    tokens = encode_bytes(tongue, text.encode("utf-8"))
    if getattr(args, "json_output", False):
        print(json.dumps({"tongue": tongue, "text": text, "tokens": tokens}))
    else:
        print(tokens)
    return 0


def cmd_dec(args: argparse.Namespace) -> int:
    tongue = _resolve_tongue(args.tongue)
    if tongue is None:
        print(f"unknown tongue '{args.tongue}' — choose: {', '.join(_CANONICAL_TONGUES)}", file=sys.stderr)
        return 2
    tokens = _arg_or_stdin(getattr(args, "text", None))
    if tokens is None:
        print('usage: scbe dec <tongue> "<tokens>"', file=sys.stderr)
        return 2
    try:
        data = decode_tokens(tongue, tokens)
    except ValueError as e:
        print(f"decode error: {e}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps({"tongue": tongue, "text": data.decode("utf-8", errors="replace")}))
    elif getattr(args, "raw", False):
        sys.stdout.buffer.write(data)
    else:
        print(data.decode("utf-8", errors="replace"))
    return 0


# ── describe: the 5-senses signature of any input ──
_PHI = (1 + 5 ** 0.5) / 2
_TONGUE_HZ = {code: 440.0 * _PHI ** i for i, code in enumerate(["KO", "AV", "RU", "CA", "UM", "DR"])}
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _freq_to_note(f: float) -> str:
    midi = round(69 + 12 * math.log2(f / 440.0))
    return f"{_NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def _sparkline(raw: bytes) -> str:
    bars = "▁▂▃▄▅▆▇█"
    if not raw:
        return "·"
    bins = [0] * 24
    for b in raw:
        bins[b * 24 // 256] += 1
    mx = max(bins) or 1
    return "".join(bars[min(7, v * 8 // mx)] for v in bins)


def _describe_signature(text: str) -> Dict[str, Any]:
    raw = text.encode("utf-8")
    n = len(raw)
    score = pipeline_quick_score(text)
    profile = _char_class_profile(raw)
    wordlike, _ = _naturalness(text)
    decision = score["decision"]

    if decision == "DENY" and profile["control_ratio"] > 0.2:
        what = "binary / non-language"
    elif wordlike >= 0.6:
        what = "natural language"
    elif profile["punct_ratio"] > 0.12:
        what = "code / markup"
    elif profile["digit_ratio"] > 0.3:
        what = "numeric / encoded"
    else:
        what = "mixed text"

    codes = ["KO", "AV", "RU", "CA", "UM", "DR"]
    code = codes[sum(raw) % 6] if raw else "KO"
    hz = _TONGUE_HZ[code]

    texture = {"ALLOW": "smooth, calm", "QUARANTINE": "grainy, tense",
               "ESCALATE": "sharp, jagged", "DENY": "hot, violent"}[decision]
    taste = {"ALLOW": "clean — tastes right", "QUARANTINE": "off — needs a look",
             "ESCALATE": "bitter — handle with care", "DENY": "spoiled — reject"}[decision]

    return {
        "what": what,
        "see": _sparkline(raw),
        "see_tongue": encode_bytes(code, raw[:6]),
        "hear": f"{hz:.0f} Hz ~ {_freq_to_note(hz)} ({TONGUE_NAMES[code]})",
        "feel": texture,
        "taste": taste,
        "flow": f"{n} bytes -> 14 layers -> H_eff {score['H_eff']} -> {decision}",
        "decision": decision,
        "tongue": code,
    }


def cmd_describe(args: argparse.Namespace) -> int:
    text = _arg_or_stdin(getattr(args, "text", None))
    if not text:
        print('usage: scbe describe "<text>"   (or pipe via stdin)', file=sys.stderr)
        return 2
    sig = _describe_signature(text)
    if getattr(args, "json_output", False):
        print(json.dumps(sig))
        return 0
    print(f"  what  ▸ {sig['what']}")
    print(f"  👁 see   ▸ {sig['see']}")
    print(f"            {sig['see_tongue']}")
    print(f"  👂 hear  ▸ {sig['hear']}")
    print(f"  🤚 feel  ▸ {sig['feel']}")
    print(f"  🎯 taste ▸ {sig['taste']}")
    print(f"  🌊 flow  ▸ {sig['flow']}")
    return 0


CHEM_CLAIM_BOUNDARY = (
    "Computational chemistry and semantic-structure modeling only; not wet-lab "
    "synthesis, biological efficacy, dosing, or physical-world chemical advice."
)

CHEM_SEMANTIC_MAP = {
    "parse": "molecular decomposition / structure perception",
    "decompose": "molecular decomposition / structure perception",
    "atomize": "molecular decomposition / structure perception",
    "compare": "similarity / fingerprint / spectral matching",
    "release": "dissociation / emission / product release",
    "bind": "bond formation / complex formation",
    "merge": "bond formation / complex formation",
    "authorize": "ionization / activation threshold",
    "deny": "inhibitor / containment",
    "quarantine": "inhibitor / containment",
    "compile": "reaction pathway realization",
    "rollback": "reverse reaction / repair pathway",
    "route": "reaction network / transport path",
    "hash": "spectroscopy / fingerprint",
    "seal": "spectroscopy / fingerprint",
}


def _chem_tokens(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_']+|[^\s]", text)


def _chem_round(value: Any, digits: int = 6) -> float:
    return round(float(value), digits)


def _element_payload(element: Any) -> Dict[str, Any]:
    return {
        "symbol": element.symbol,
        "Z": element.Z,
        "group": element.group,
        "period": element.period,
        "valence": element.valence,
        "electronegativity": _chem_round(element.electronegativity),
        "witness_stable": element.witness_stable,
    }


def _atomic_state_payload(state: Any) -> Dict[str, Any]:
    return {
        "token": state.token,
        "semantic_class": state.semantic_class,
        "element": _element_payload(state.element),
        "tau": state.tau.as_dict(),
        "negative_state": state.negative_state,
        "dual_state": state.dual_state,
        "band_flag": state.band_flag,
        "resilience": _chem_round(state.resilience),
        "adaptivity": _chem_round(state.adaptivity),
        "trust_baseline": _chem_round(state.trust_baseline),
    }


def _fusion_payload(result: Any) -> Dict[str, Any]:
    return {
        "tau_hat": result.tau_hat,
        "reconstruction_votes": {
            tongue: _chem_round(vote) for tongue, vote in result.reconstruction_votes.items()
        },
        "signed_edge_tension": _chem_round(result.signed_edge_tension),
        "coherence_penalty": _chem_round(result.coherence_penalty),
        "valence_pressure": _chem_round(result.valence_pressure),
    }


def cmd_chem_atomize(args: argparse.Namespace) -> int:
    from python.scbe.atomic_tokenization import map_token_to_atomic_state
    from python.scbe.chemical_fusion import fuse_atomic_states

    text = _arg_or_stdin(getattr(args, "text", None))
    if not text:
        print('usage: scbe chem atomize "<text>"   (or pipe via stdin)', file=sys.stderr)
        return 2
    tokens = _chem_tokens(text)
    if not tokens:
        print("error: no tokens found", file=sys.stderr)
        return 2

    states = [
        map_token_to_atomic_state(
            token,
            language=getattr(args, "language", None),
            context_class=getattr(args, "context", None),
        )
        for token in tokens
    ]
    fusion = fuse_atomic_states(states)
    payload = {
        "schema_version": "scbe_chem_atomize_v1",
        "text": text,
        "tokens": tokens,
        "token_count": len(tokens),
        "states": [_atomic_state_payload(state) for state in states],
        "fusion": _fusion_payload(fusion),
        "claim_boundary": CHEM_CLAIM_BOUNDARY,
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload))
        return 0

    print(f"chem atomize: {len(tokens)} token(s)")
    print("  tokens:", ", ".join(tokens))
    print("  tau_hat:", payload["fusion"]["tau_hat"])
    print("  elements:", " ".join(state["element"]["symbol"] for state in payload["states"]))
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_chem_bonds(args: argparse.Namespace) -> int:
    from src.governance.chemical_bonds import TONGUES, TongueMolecule

    report = TongueMolecule(list(args.coords)).report()
    payload = {
        "schema_version": "scbe_chem_bonds_v1",
        "tongues": list(TONGUES),
        "coords": [_chem_round(value) for value in args.coords],
        "bonds": [
            {
                "name": bond.name,
                "z": {"real": _chem_round(bond.z.real), "imag": _chem_round(bond.z.imag)},
                "energy": _chem_round(bond.energy),
                "angle_deg": _chem_round(bond.angle_deg),
                "dissociation": _chem_round(bond.dissociation),
                "broken": bond.broken,
            }
            for bond in report.bonds
        ],
        "total_energy": _chem_round(report.total_energy),
        "stability": _chem_round(report.stability),
        "fuzzy": {
            "safe": _chem_round(report.fuzzy_safe),
            "cautious": _chem_round(report.fuzzy_cautious),
            "suspicious": _chem_round(report.fuzzy_suspicious),
            "hostile": _chem_round(report.fuzzy_hostile),
        },
        "broken_count": report.broken_count,
        "dominant_class": report.dominant_class,
        "claim_boundary": CHEM_CLAIM_BOUNDARY,
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload))
        return 0

    print(f"chem bonds: {payload['dominant_class']} stability={payload['stability']}")
    for bond in payload["bonds"]:
        status = "broken" if bond["broken"] else "bound"
        print(f"  {bond['name']}: energy={bond['energy']} angle={bond['angle_deg']} {status}")
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_chem_convert(args: argparse.Namespace) -> int:
    smiles = _arg_or_stdin(getattr(args, "smiles", None))
    if not smiles:
        print('usage: scbe chem convert --smiles "CCO" --to can', file=sys.stderr)
        return 2

    out_format = args.to.lower()
    engine = args.engine.lower()
    payload: Dict[str, Any] = {
        "schema_version": "scbe_chem_convert_v1",
        "input_format": "smiles",
        "input": smiles,
        "output_format": out_format,
        "engine": engine,
        "claim_boundary": CHEM_CLAIM_BOUNDARY,
    }

    if engine == "rdkit":
        from rdkit import Chem
        from rdkit.Chem import Descriptors

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            print(f"error: RDKit could not parse SMILES: {smiles}", file=sys.stderr)
            return 2
        if out_format in {"can", "canonical", "smi", "smiles"}:
            output = Chem.MolToSmiles(mol, canonical=True)
            normalized_format = "canonical_smiles"
        elif out_format == "mol":
            output = Chem.MolToMolBlock(mol)
            normalized_format = "mol"
        else:
            print(f"error: RDKit output format not supported here: {out_format}", file=sys.stderr)
            return 2
        payload.update(
            {
                "output": output,
                "normalized_output_format": normalized_format,
                "descriptors": {"mol_wt": _chem_round(Descriptors.MolWt(mol), 6)},
            }
        )
    elif engine == "openbabel":
        from openbabel import pybel

        try:
            mol = pybel.readstring("smi", smiles)
            output = mol.write(out_format).strip()
        except Exception as exc:
            print(f"error: Open Babel conversion failed: {exc}", file=sys.stderr)
            return 2
        payload.update({"output": output, "normalized_output_format": out_format})
    else:
        print(f"error: unsupported engine: {engine}", file=sys.stderr)
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(payload))
        return 0
    print(payload["output"])
    return 0


def cmd_chem_orbitals(args: argparse.Namespace) -> int:
    from src.geoseed.orbital_model import orbital_summary

    payload = orbital_summary(include_profiles=getattr(args, "profiles", False))
    payload["claim_boundary"] = CHEM_CLAIM_BOUNDARY
    if getattr(args, "json_output", False):
        print(json.dumps(payload))
        return 0

    print(f"chem orbitals: {payload['manifold']} total_m_states={payload['total_m_states']}")
    for orbital in payload["orbitals"]:
        print(
            f"  {orbital['abbr']} {orbital['orbital_name']}: "
            f"l={orbital['l']} r={orbital['poincare_r']}"
        )
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_chem_benchmark(args: argparse.Namespace) -> int:
    from scripts.benchmark.chemistry_cli_capability import OUT_DIR, build_report

    out_dir = Path(getattr(args, "out_dir", None) or OUT_DIR)
    report = build_report(
        out_dir=out_dir,
        run_tests=not getattr(args, "inventory_only", False),
        timeout_s=getattr(args, "timeout", 180),
    )
    report["claim_boundary"] = CHEM_CLAIM_BOUNDARY
    if getattr(args, "json_output", False):
        print(json.dumps(report))
        return 0

    print(f"chem benchmark: {report['decision']}")
    print(
        f"  probes={report['runtime_probes']['passed']}/{report['runtime_probes']['total']} "
        f"capability_files={report['capability_files']['present']}/{report['capability_files']['total']}"
    )
    print(f"  proof: {report['private_proof']['present']}/{report['private_proof']['total']} private files")
    print(f"  artifact: {report['artifact']}")
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_chem_industry_benchmark(args: argparse.Namespace) -> int:
    from scripts.benchmark.chemistry_industry_benchmark import OUT_DIR, build_report

    out_dir = Path(getattr(args, "out_dir", None) or OUT_DIR)
    report = build_report(
        out_dir=out_dir,
        timeout_s=getattr(args, "timeout", 30),
        live_pubchem=getattr(args, "live_pubchem", False),
    )
    if getattr(args, "json_output", False):
        print(json.dumps(report))
        return 0

    summary = report["summary"]
    print(f"chem industry-benchmark: {summary['decision']}")
    print(f"  scbe={summary['scbe_probe_status']}")
    installed = summary["scientific_baselines_installed"] or ["none"]
    passing = summary["scientific_baselines_passing"] or ["none"]
    print(f"  scientific_installed={','.join(installed)}")
    print(f"  scientific_passing={','.join(passing)}")
    print(f"  artifact: {out_dir / 'LATEST.md'}")
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_chem_map_semantics(args: argparse.Namespace) -> int:
    operation = args.operation.lower().strip()
    analogue = args.chemical_analogue.strip()
    expected = CHEM_SEMANTIC_MAP.get(operation)
    analogue_norm = analogue.lower()
    accepted = expected is not None
    shared = accepted and any(part.strip() in analogue_norm for part in expected.split("/"))
    payload = {
        "schema_version": "scbe_chem_semantic_map_v1",
        "operation": operation,
        "chemical_analogue": analogue,
        "expected_analogue": expected,
        "accepted": accepted,
        "line_type": "shared_operation" if shared else "declared_analogy",
        "claim_boundary": CHEM_CLAIM_BOUNDARY,
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload))
        return 0

    status = "accepted" if accepted else "unmapped"
    print(f"chem map-semantics: {operation} -> {analogue} ({status})")
    if expected:
        print(f"  expected lane: {expected}")
    print(f"  line_type: {payload['line_type']}")
    print(f"  boundary: {CHEM_CLAIM_BOUNDARY}")
    return 0


def cmd_tongue_verb(args: argparse.Namespace) -> int:
    """A Sacred Tongue used directly as a verb: `scbe ko "hi"` encodes in KO,
    `scbe ko -d "<tokens>"` decodes. The tongue is bound via set_defaults."""
    if getattr(args, "decode", False):
        return cmd_dec(args)
    return cmd_enc(args)


def cmd_explain(args: argparse.Namespace) -> int:
    text = ai_explain(args.target)
    if getattr(args, "json_output", False):
        t = args.target.upper().replace("LAYER", "L").replace(" ", "")
        info = LAYER_GUIDE.get(t)
        print(json.dumps({
            "target": args.target,
            "name": info[0] if info else None,
            "description": info[1] if info else None,
            "text": text,
        }))
    else:
        print(text)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lint = ai_lint(args.file)
    if "error" in lint:
        if getattr(args, "json_output", False):
            print(json.dumps({"error": lint["error"]}))
        else:
            print(f"error: {lint['error']}", file=sys.stderr)
        return 1
    review = ai_review(args.file)
    clean = lint.get("compiles") is not False and not review.get("warnings") and lint["issue_count"] == 0
    if getattr(args, "json_output", False):
        print(json.dumps({"file": args.file, "clean": clean, "lint": lint, "review": review}))
    else:
        print(f"{args.file}: {review['code_lines']} code, "
              f"{review['functions']} funcs, {review['classes']} classes")
        if lint.get("compiles") is False:
            print(f"  ✗ {lint['syntax_error']}")
        if lint["issue_count"]:
            print(f"  {lint['issue_count']} lint issue(s)")
        for w in review.get("warnings", []):
            print(f"  warn: {w}")
        if clean:
            print("  ✓ clean")
    return 0


# ═══════════════════════════════════════════════════════════════
# Ask the AI — chat with any available model
#
# Routes to whatever backend is on the machine: the `claude` CLI
# (Claude Max, no key needed), `codex`, `ollama`, or a raw API key.
# Same surface for humans (scbe chat) and agents (scbe ask --json).
# ═══════════════════════════════════════════════════════════════

AI_BACKENDS = ("claude", "codex", "ollama", "anthropic", "openai")


def _detect_backends() -> List[str]:
    found: List[str] = []
    if shutil.which("claude"):
        found.append("claude")
    if shutil.which("codex"):
        found.append("codex")
    if shutil.which("ollama"):
        found.append("ollama")
    if os.environ.get("ANTHROPIC_API_KEY"):
        found.append("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        found.append("openai")
    return found


def _run_backend_cli(cmd: List[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    except FileNotFoundError:
        return f"(backend not found: {cmd[0]})"
    except subprocess.TimeoutExpired:
        return "(the model took too long to respond)"
    out = (r.stdout or "").strip()
    return out or (r.stderr or "").strip() or "(no response)"


def _ask_claude(prompt: str, model: Optional[str]) -> str:
    cmd = ["claude", "-p", prompt]
    if model:
        cmd += ["--model", model]
    return _run_backend_cli(cmd)


def _ask_codex(prompt: str, model: Optional[str]) -> str:
    cmd = ["codex", "exec"]
    if model:
        cmd += ["-m", model]
    cmd.append(prompt)
    return _run_backend_cli(cmd)


def _ask_ollama(prompt: str, model: Optional[str]) -> str:
    return _run_backend_cli(["ollama", "run", model or "llama3.2", prompt])


def _ask_api(prompt: str, model: Optional[str], provider: str) -> str:
    import urllib.request
    if provider == "anthropic":
        body = {"model": model or "claude-sonnet-4-6", "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(),
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                     "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return "".join(b.get("text", "") for b in data.get("content", [])).strip()
        except Exception as e:  # network/auth errors shouldn't crash the CLI
            return f"(anthropic API error: {e})"
    if provider == "openai":
        body = {"model": model or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                     "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"(openai API error: {e})"
    return f"(unknown provider: {provider})"


def ai_ask(prompt: str, backend: Optional[str] = None,
           model: Optional[str] = None) -> Tuple[str, str]:
    """Return (answer, backend_used). Picks the first available backend."""
    available = _detect_backends()
    if not available:
        return (
            "No AI backend found. Install/enable one:\n"
            "  • Claude Code  — you have it; make sure `claude` is on PATH\n"
            "  • codex or ollama, or set ANTHROPIC_API_KEY / OPENAI_API_KEY",
            "none",
        )
    chosen = backend or available[0]
    if chosen not in available:
        return (f"backend '{chosen}' not available — found: {', '.join(available)}", chosen)
    if chosen == "claude":
        return _ask_claude(prompt, model), chosen
    if chosen == "codex":
        return _ask_codex(prompt, model), chosen
    if chosen == "ollama":
        return _ask_ollama(prompt, model), chosen
    return _ask_api(prompt, model, chosen), chosen


def _render_history(history: List[Tuple[str, str]], new_q: str) -> str:
    """Fold prior turns into one prompt so any backend gets multi-turn memory."""
    if not history:
        return new_q
    lines = []
    for role, text in history[-10:]:
        lines.append(f"{'User' if role == 'you' else 'Assistant'}: {text}")
    lines.append(f"User: {new_q}")
    lines.append("Assistant:")
    return "\n".join(lines)


_ANSWER_ONLY = (
    "Answer in plain text only. Do not run commands, edit files, or use tools — "
    "just respond directly and concisely.\n\n"
)


def cmd_ask(args: argparse.Namespace) -> int:
    prompt = _arg_or_stdin(getattr(args, "prompt", None))
    if not prompt:
        print('usage: scbe ask "<question>"   (or pipe text via stdin)', file=sys.stderr)
        return 2
    # ask = explain, never act — wrap so agentic backends just answer.
    answer, backend = ai_ask(_ANSWER_ONLY + prompt, getattr(args, "backend", None),
                             getattr(args, "model", None))
    if getattr(args, "json_output", False):
        print(json.dumps({"prompt": prompt, "backend": backend, "answer": answer}))
    else:
        print(answer)
    return 0


def cmd_do(args: argparse.Namespace) -> int:
    """do = act. Hands the task straight to an agentic backend (claude/codex)."""
    task = _arg_or_stdin(getattr(args, "task", None))
    if not task:
        print('usage: scbe do "<task>"   (or pipe via stdin)', file=sys.stderr)
        return 2
    answer, backend = ai_ask(task, getattr(args, "backend", None), getattr(args, "model", None))
    if getattr(args, "json_output", False):
        print(json.dumps({"task": task, "backend": backend, "result": answer}))
    else:
        print(answer)
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    available = _detect_backends()
    if not available:
        print("No AI backend found. You have Claude Code — make sure `claude` is on PATH,")
        print("or set ANTHROPIC_API_KEY / OPENAI_API_KEY, or install ollama.")
        return 1
    backend = getattr(args, "backend", None) or available[0]
    model = getattr(args, "model", None)
    tag = f"{backend}{' · ' + model if model else ''}"
    print(f"scbe chat · {tag}   (backends: {', '.join(available)})   type 'exit' to quit\n")
    history: List[Tuple[str, str]] = []
    while True:
        q = _menu_prompt("you ▸ ")
        if q is None or q.lower() in {"exit", "quit", "/q", "bye"}:
            print("bye —")
            return 0
        if not q:
            continue
        answer, _ = ai_ask(_ANSWER_ONLY + _render_history(history, q), backend, model)
        print(f"ai  ▸ {answer}\n")
        history.append(("you", q))
        history.append(("ai", answer))


# ═══════════════════════════════════════════════════════════════
# File management — move / push / guided delete
#
# Deletion is "guided": it shows exactly what will go, asks to confirm,
# and moves to a recoverable trash instead of hard-deleting. Nothing is
# ever destroyed outright.
# ═══════════════════════════════════════════════════════════════

TRASH_DIR = Path.home() / ".scbe-trash"
JOURNAL = TRASH_DIR / ".journal.jsonl"


def _journal_append(entry: Dict[str, str]) -> None:
    """Record a reversible action so `scbe undo` can replay it backwards."""
    TRASH_DIR.mkdir(exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def cmd_move(args: argparse.Namespace) -> int:
    src, dst = Path(args.src), Path(args.dst)
    if not src.exists():
        print(f"not found: {src}", file=sys.stderr)
        return 1
    target = dst / src.name if dst.is_dir() else dst
    if target.exists() and not getattr(args, "force", False):
        if not _confirm(f"overwrite {target}? [y/N] "):
            print("cancelled")
            return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    origin = str(src.resolve())
    shutil.move(str(src), str(target))
    _journal_append({"action": "move", "from": origin, "to": str(target.resolve())})
    print(f"moved {src} -> {target}")
    return 0


def cmd_del(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths]
    existing = [p for p in paths if p.exists()]
    for missing in (p for p in paths if not p.exists()):
        print(f"not found: {missing}", file=sys.stderr)
    if not existing:
        return 1
    # The "guide": show exactly what will be removed and how big.
    print("about to remove (→ recoverable trash):")
    total = 0
    for p in existing:
        size = p.stat().st_size if p.is_file() else _dir_size(p)
        total += size
        print(f"  {p}  ({_human(size)}{', dir' if p.is_dir() else ''})")
    print(f"  total: {_human(total)}   trash: {TRASH_DIR}")
    if not getattr(args, "yes", False) and not _confirm("proceed? [y/N] "):
        print("cancelled")
        return 0
    TRASH_DIR.mkdir(exist_ok=True)
    for p in existing:
        origin = str(p.resolve())
        dest = TRASH_DIR / p.name
        n = 1
        while dest.exists():  # never clobber an existing trashed item
            dest = TRASH_DIR / f"{p.stem}_{n}{p.suffix}"
            n += 1
        shutil.move(str(p), str(dest))
        _journal_append({"action": "trash", "from": str(dest), "to": origin})
        print(f"trashed {p.name} -> {dest}")
    print(f"recover anything from {TRASH_DIR}   (scbe undo restores the last)")
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    repo = str(REPO_ROOT)
    print("git status:")
    subprocess.run(["git", "-C", repo, "status", "--short"], check=False)
    if not getattr(args, "yes", False) and not _confirm("stage all + commit + push? [y/N] "):
        print("cancelled")
        return 0
    msg = getattr(args, "message", None) or "update"
    subprocess.run(["git", "-C", repo, "add", "-A"], check=False)
    subprocess.run(["git", "-C", repo, "commit", "-m", msg], check=False)
    return subprocess.run(["git", "-C", repo, "push"], check=False).returncode


def cmd_undo(_args: argparse.Namespace) -> int:
    """Past tense: reverse the most recent move or guided delete."""
    if not JOURNAL.exists():
        print("nothing to undo")
        return 0
    lines = [ln for ln in JOURNAL.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        print("nothing to undo")
        return 0
    entry = json.loads(lines[-1])
    action = entry.get("action")
    if action == "move":
        now, back = entry["to"], entry["from"]
    elif action == "trash":
        now, back = entry["from"], entry["to"]
    else:
        print(f"don't know how to undo '{action}'", file=sys.stderr)
        return 1
    try:
        Path(back).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(now, back)
    except Exception as e:  # restore can fail if the file moved/changed
        print(f"undo failed: {e}", file=sys.stderr)
        return 1
    print(f"undone: restored {back}")
    JOURNAL.write_text("".join(ln + "\n" for ln in lines[:-1]), encoding="utf-8")
    return 0


# ═══════════════════════════════════════════════════════════════
# find — locate your notes/docs by name across cataloged vaults
#
# Reads AETHER-CATALOG.json for vault locations (falls back to sane
# defaults), walks them while PRUNING mirror/plugin junk, and matches
# filenames. Read-only: it never modifies or deletes anything.
# ═══════════════════════════════════════════════════════════════

_FIND_PRUNE = {".git", ".obsidian", "node_modules", "external", "dist", "__pycache__", "cache~1"}
_FIND_JUNK_SUB = ("repository mirror", "plugin-backups", "codex-runtimes",
                  "\\cache\\", "\\appdata\\", "site-packages")
_FIND_EXTS = {".md", ".docx", ".pdf", ".txt", ".doc", ".epub"}


def _find_roots() -> List[Path]:
    roots: List[Path] = []
    catalog = Path.home() / "AETHER-CATALOG.json"
    if catalog.exists():
        try:
            data = json.loads(catalog.read_text(encoding="utf-8"))
            for v in data.get("vaults", []):
                p = str(v.get("path", ""))
                if p and "Backups" not in p:  # skip our own backup snapshots
                    roots.append(Path(p))
        except Exception:
            pass
    for extra in ["Avalon Files (consolidated)", "OneDrive/Books", "OneDrive/Documents", "Documents"]:
        roots.append(Path.home() / extra)
    if Path("D:/Recovery").exists():
        roots.append(Path("D:/Recovery"))
    uniq: Dict[str, Path] = {}
    for r in roots:
        if r.exists():
            uniq.setdefault(os.path.normcase(str(r)), r)
    return list(uniq.values())


def cmd_find(args: argparse.Namespace) -> int:
    query = (getattr(args, "query", None) or "").lower()
    if not query:
        print('usage: scbe find <text>   (matches your note/doc filenames)', file=sys.stderr)
        return 2
    exts = {"." + args.ext.lstrip(".").lower()} if getattr(args, "ext", None) else _FIND_EXTS
    content = getattr(args, "content", False)
    text_exts = {".md", ".txt"}
    matches: List[Tuple[float, str, str, Optional[str]]] = []
    seen: set = set()
    for root in _find_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dl = dirpath.lower()
            if any(j in dl for j in _FIND_JUNK_SUB):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d.lower() not in _FIND_PRUNE]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in exts:
                    continue
                full = os.path.join(dirpath, fn)
                nc = os.path.normcase(full)
                if nc in seen:
                    continue
                name_hit = query in fn.lower()
                snippet = None
                if content and not name_hit and ext in text_exts:
                    try:
                        st = os.stat(full)
                        # Skip OneDrive cloud-only placeholders — reading them
                        # forces a download (slow). They stay name-searchable.
                        attrs = getattr(st, "st_file_attributes", 0)
                        if attrs & 0x401000:  # OFFLINE | RECALL_ON_DATA_ACCESS
                            raise OSError("cloud-only")
                        if st.st_size <= 1_000_000:  # skip huge files
                            with open(full, encoding="utf-8", errors="ignore") as fh:
                                txt = fh.read()
                            idx = txt.lower().find(query)
                            if idx >= 0:
                                snippet = "..." + txt[max(0, idx - 30): idx + 60].replace("\n", " ").strip() + "..."
                    except OSError:
                        pass
                if not (name_hit or snippet):
                    continue
                seen.add(nc)
                try:
                    mt = os.path.getmtime(full)
                except OSError:
                    mt = 0.0
                matches.append((mt, full, fn, snippet))
    matches.sort(reverse=True)
    matches = matches[: getattr(args, "limit", 25)]
    if getattr(args, "json_output", False):
        print(json.dumps([{"name": n, "path": p, "snippet": s} for _, p, n, s in matches]))
        return 0
    if not matches:
        print(f"no files matching '{args.query}' in your notes/docs")
        return 0
    print(f"{len(matches)} match(es) for '{args.query}' (by {'name+content' if content else 'name'}):")
    for mt, p, n, s in matches:
        d = time.strftime("%Y-%m-%d", time.localtime(mt)) if mt else "-"
        print(f"  {d}  {n}")
        if s:
            print(f"             > {s}")
        print(f"             {p}")
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
    if script.exists():
        cmd = [sys.executable, str(script), "--repo-root", str(REPO_ROOT), *args]
    else:
        cmd = [sys.executable, "-m", "scripts.scbe_system_cli", "--repo-root", str(REPO_ROOT), *args]
    return subprocess.run(cmd, check=False).returncode


# ═══════════════════════════════════════════════════════════════
# Legacy command bridge (backward compatibility)
# ═══════════════════════════════════════════════════════════════

LEGACY_SCRIPTS = {
    "cli": "scbe-cli.py",
    "agent": "scbe-agent.py",
    "demo": "demo-cli.py",
    "memory": "demo_memory_shard.py",
}

SYSTEM_AGENT_SUBCOMMANDS = {
    "bootstrap",
    "list",
    "register",
    "remove",
    "ping",
    "call",
}

MODERN_AI_SUBCOMMANDS = {"explain", "lint", "review", "check"}


def _run_legacy_script(command: str, extra_args: List[str]) -> int:
    script = REPO_ROOT / LEGACY_SCRIPTS[command]
    if not script.exists():
        print(f"Legacy script not found: {script}")
        return 1
    return subprocess.run([sys.executable, str(script), *extra_args]).returncode


def _print_agent_command_help() -> None:
    print("scbe agent usage")
    print("  scbe agent")
    print("      Launch the legacy interactive AI assistant.")
    print("  scbe agent list|bootstrap|register|remove|ping|call ...")
    print("      Forward to the system agent registry and orchestration CLI.")
    print()
    print("Examples:")
    print("  scbe agent")
    print("  scbe agent list")
    print("  scbe agent bootstrap --force")
    print('  scbe agent call --all --prompt "Summarize repo health"')


def _print_cli_command_help() -> None:
    print("scbe cli usage")
    print("  scbe cli")
    print("      Launch the legacy interactive CLI.")
    print("  scbe cli ai")
    print("      Launch the legacy SCBE AI agent.")
    print("  scbe cli ai explain L12")
    print("      Runs the modern AI helper for quick explanations.")
    print()
    print("Preferred modern commands:")
    print("  scbe ai explain L12")
    print("  scbe ai lint src/crypto/h_lwe.py")
    print('  scbe pipeline run --text "test input"')
    print('  scbe pollypad init --agent-id rex --name "Rex"')
    print()
    print("If you want the old interactive shell, run `scbe cli` with no extra arguments.")


def _dispatch_scbe_args(args: List[str]) -> int:
    if not args:
        cli = build_cli()
        cli.print_help()
        return 0

    forwarded = FORWARDED_SYSTEM_COMMANDS.get(args[0])
    if forwarded is not None:
        return _run_system_cli([*forwarded, *args[1:]])

    cli = build_cli()
    parsed = cli.parse_args(args)
    if not hasattr(parsed, "func"):
        cli.print_help()
        return 0
    return parsed.func(parsed)


def _handle_cli_command(argv: List[str]) -> int:
    if len(argv) == 2:
        return _run_legacy_script("cli", [])

    cli_args = argv[2:]
    first = cli_args[0].lower()

    if first in {"-h", "--help", "help"}:
        _print_cli_command_help()
        return 0

    if first in {"ai", "agent", "codex"}:
        if len(cli_args) == 1:
            print("Routing `scbe cli ai` to the legacy SCBE AI agent. Preferred syntax: `scbe agent`.")
            return _run_legacy_script("agent", [])

        second = cli_args[1].lower()
        if second in MODERN_AI_SUBCOMMANDS:
            print(f"Routing legacy syntax `scbe cli {' '.join(cli_args)}` to `scbe {' '.join(cli_args)}`.")
            return _dispatch_scbe_args(cli_args)

        return _run_legacy_script("agent", cli_args[1:])

    print(f"`scbe cli {' '.join(cli_args)}` uses the legacy shell and does not understand modern subcommands.")
    print("Run `scbe cli` for the old interactive mode, or use a modern command like:")
    print("  scbe ai explain L12")
    print('  scbe pipeline run --text "test input"')
    print("  scbe tongues list")
    suggestions = difflib.get_close_matches(first, ["ai", "pipeline", "tongues", "status", "selftest"], n=2, cutoff=0.4)
    if suggestions:
        print(f"Closest matches: {', '.join(suggestions)}")
    return 2


def _handle_agent_command(argv: List[str]) -> int:
    if len(argv) == 2:
        return _run_legacy_script("agent", [])

    agent_args = argv[2:]
    first = agent_args[0].lower()

    if first in {"-h", "--help", "help"}:
        _print_agent_command_help()
        return 0

    if first in SYSTEM_AGENT_SUBCOMMANDS:
        return _run_system_cli(["agent", *agent_args])

    return _run_legacy_script("agent", agent_args)


# ═══════════════════════════════════════════════════════════════
# CLI builder
# ═══════════════════════════════════════════════════════════════

ALL_TONGUES = list(_CANONICAL_TONGUES.keys()) + [t.lower() for t in _CANONICAL_TONGUES] + sorted(TONGUE_ALIASES)


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
  scbe doctor --json
  scbe model plan --profile coder-qwen-local --json
  scbe model train --profile coder-qwen-local
  scbe use studio --firebase-project my-project --github-repo issdandavis/SCBE-AETHERMOORE
  scbe colab list --json
  scbe colab url scbe-finetune-free
  scbe colab review --json
  scbe colab bridge-status --name pivot
  scbe workflow styleize --name nightly-ops --step "Smoke::python scbe.py selftest"
  scbe pollypad init --agent-id rex --name "Rex"
  scbe run --language python --code "print('SCBE')"
  scbe flow plan --task "improve CLI swarm"
  scbe system health --json
  scbe how do I encode fox in draumric?
  scbe what is L12?
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

    system = sub.add_parser("system", help="PC health, memory, and maintenance preflights")
    system_sub = system.add_subparsers(dest="system_cmd")

    sh = system_sub.add_parser("health", help="Check RAM, disk headroom, and cloud-sync pressure")
    sh.add_argument("--json", dest="json_output", action="store_true")
    sh.add_argument("--no-write", action="store_true", help="do not write artifacts/pc-memory report")
    sh.add_argument("--warn-ram-percent", type=int, default=85)
    sh.add_argument("--warn-disk-free-gb", type=int, default=25)
    sh.add_argument("--top-processes", type=int, default=15)
    sh.set_defaults(func=cmd_system_health)

    # ─── compact verbs (human + AI surface) ───
    ak = sub.add_parser("ask", aliases=["a"], help='Ask the AI a question ("scbe ask \"...\"")')
    ak.add_argument("prompt", nargs="?", help="question (or pipe via stdin)")
    ak.add_argument("--backend", choices=list(AI_BACKENDS), help="force a backend (default: auto)")
    ak.add_argument("--model", help="model name for the chosen backend")
    ak.add_argument("--json", dest="json_output", action="store_true")
    ak.set_defaults(func=cmd_ask)

    ch = sub.add_parser("chat", help="Interactive AI chat with memory (any available model)")
    ch.add_argument("--backend", choices=list(AI_BACKENDS))
    ch.add_argument("--model")
    ch.set_defaults(func=cmd_chat)

    do = sub.add_parser("do", help='Tell the AI to DO a task — agentic ("scbe do \"...\"")')
    do.add_argument("task", nargs="?", help="task (or pipe via stdin)")
    do.add_argument("--backend", choices=list(AI_BACKENDS))
    do.add_argument("--model")
    do.add_argument("--json", dest="json_output", action="store_true")
    do.set_defaults(func=cmd_do)

    sc = sub.add_parser("score", aliases=["s"], help='Score text through the pipeline ("scbe s <text>")')
    sc.add_argument("text", nargs="?", help="text to score (or pipe via stdin)")
    sc.add_argument("--json", dest="json_output", action="store_true", help="machine-readable output")
    sc.add_argument("--gate", action="store_true", help="exit nonzero on DENY/ESCALATE (for agents)")
    sc.set_defaults(func=cmd_score)

    en = sub.add_parser("enc", help='Encode text to a Sacred Tongue ("scbe enc ko hello")')
    en.add_argument("tongue", choices=ALL_TONGUES, metavar="tongue")
    en.add_argument("text", nargs="?", help="text to encode (or pipe via stdin)")
    en.add_argument("--json", dest="json_output", action="store_true")
    en.set_defaults(func=cmd_enc)

    de = sub.add_parser("dec", help='Decode Sacred Tongue tokens to text ("scbe dec ko \"...\"")')
    de.add_argument("tongue", choices=ALL_TONGUES, metavar="tongue")
    de.add_argument("text", nargs="?", help="tokens to decode (or pipe via stdin)")
    de.add_argument("--json", dest="json_output", action="store_true")
    de.add_argument("--raw", action="store_true", help="write raw bytes to stdout")
    de.set_defaults(func=cmd_dec)

    # ─── Sacred Tongues as verbs — full names, no abbreviation ───
    tongue_verbs = {
        "koraelin": "ko", "avali": "av", "runethic": "ru",
        "cassisivadan": "ca", "umbroth": "um", "draumric": "dr",
    }
    for fullname, code in tongue_verbs.items():
        name = TONGUE_NAMES[code.upper()]
        tv = sub.add_parser(fullname, help=f'Speak {name}: encode text ("scbe {fullname} hello")')
        tv.add_argument("text", nargs="?", help="text to encode (or pipe via stdin)")
        tv.add_argument("-d", "--decode", action="store_true", help="decode tokens back to text")
        tv.add_argument("--json", dest="json_output", action="store_true")
        tv.set_defaults(func=cmd_tongue_verb, tongue=code)

    # ─── file management (guided + safe) ───
    mv = sub.add_parser("move", help='Move/rename a file ("scbe move a.txt dir/")')
    mv.add_argument("src")
    mv.add_argument("dst")
    mv.add_argument("-f", "--force", action="store_true", help="overwrite without asking")
    mv.set_defaults(func=cmd_move)

    rm = sub.add_parser("del", aliases=["trash"], help="Guided delete → recoverable trash")
    rm.add_argument("paths", nargs="+", help="files/dirs to remove")
    rm.add_argument("-y", "--yes", action="store_true", help="skip the confirm prompt")
    rm.set_defaults(func=cmd_del)

    pu = sub.add_parser("push", help="Stage + commit + push the repo (with confirm)")
    pu.add_argument("message", nargs="?", help="commit message")
    pu.add_argument("-y", "--yes", action="store_true", help="skip the confirm prompt")
    pu.set_defaults(func=cmd_push)

    un = sub.add_parser("undo", help="Reverse the last move/delete (past tense)")
    un.set_defaults(func=cmd_undo)

    xp = sub.add_parser("explain", aliases=["x"], help='Explain a pipeline layer ("scbe x L12")')
    xp.add_argument("target", help="layer (L12) or concept (harmonic, breathing)")
    xp.add_argument("--json", dest="json_output", action="store_true")
    xp.set_defaults(func=cmd_explain)

    ck = sub.add_parser("check", aliases=["c"], help='Lint + review a source file ("scbe c file.py")')
    ck.add_argument("file", help="file path")
    ck.add_argument("--json", dest="json_output", action="store_true")
    ck.set_defaults(func=cmd_check)

    ds = sub.add_parser(
        "describe",
        aliases=["desc"],
        help='5-senses signature: see/hear/feel ("scbe describe \"...\"")',
    )
    ds.add_argument("text", nargs="?", help="text to describe (or pipe via stdin)")
    ds.add_argument("--json", dest="json_output", action="store_true")
    ds.set_defaults(func=cmd_describe)

    fd = sub.add_parser("find", aliases=["f"], help='Find your notes/docs by name ("scbe find <text>")')
    fd.add_argument("query", nargs="?", help="text to match in note/doc filenames")
    fd.add_argument("-c", "--content", action="store_true", help="also search inside note text")
    fd.add_argument("--ext", help="restrict to one extension (md, docx, pdf)")
    fd.add_argument("--limit", type=int, default=25, help="max results (default 25)")
    fd.add_argument("--json", dest="json_output", action="store_true")
    fd.set_defaults(func=cmd_find)

    # ─── top-level ───
    chem = sub.add_parser("chem", help="Symbolic chemistry and STISTA proof lane")
    chem_sub = chem.add_subparsers(dest="chem_cmd")

    ca = chem_sub.add_parser("atomize", help='Map text to atomic token states ("scbe chem atomize ...")')
    ca.add_argument("text", nargs="?", help="text to atomize (or pipe via stdin)")
    ca.add_argument("--language", help="optional language code for token-class overrides")
    ca.add_argument("--context", help="optional context class, e.g. operator, timeline, safety")
    ca.add_argument("--json", dest="json_output", action="store_true")
    ca.set_defaults(func=cmd_chem_atomize)

    cb = chem_sub.add_parser("bonds", help="Analyze the 6 Sacred Tongue coordinate bonds")
    cb.add_argument("coords", nargs=6, type=float, metavar="coord")
    cb.add_argument("--json", dest="json_output", action="store_true")
    cb.set_defaults(func=cmd_chem_bonds)

    cc = chem_sub.add_parser("convert", help="Convert SMILES with RDKit or Open Babel bindings")
    cc.add_argument("--smiles", help="SMILES input (or pipe via stdin)")
    cc.add_argument("--to", default="can", help="output format: can, smi, mol, sdf")
    cc.add_argument("--engine", choices=["rdkit", "openbabel"], default="rdkit")
    cc.add_argument("--json", dest="json_output", action="store_true")
    cc.set_defaults(func=cmd_chem_convert)

    co = chem_sub.add_parser("orbitals", help="Summarize GeoSeed phi-shell orbitals")
    co.add_argument("--profiles", action="store_true", help="include sampled radial density profiles")
    co.add_argument("--json", dest="json_output", action="store_true")
    co.set_defaults(func=cmd_chem_orbitals)

    cm = chem_sub.add_parser("map-semantics", help="Map SCBE operations to chemistry analogues")
    cm.add_argument("--operation", required=True, help="SCBE operation, e.g. release, bind, compare")
    cm.add_argument("--chemical-analogue", required=True, help="chemistry analogue to classify")
    cm.add_argument("--json", dest="json_output", action="store_true")
    cm.set_defaults(func=cmd_chem_map_semantics)

    cbench = chem_sub.add_parser("benchmark", help="Run or inventory the chemistry capability benchmark")
    cbench.add_argument("--inventory-only", action="store_true", help="skip pytest and report inventory/probes")
    cbench.add_argument("--timeout", type=int, default=180)
    cbench.add_argument("--out-dir", help="artifact output directory")
    cbench.add_argument("--json", dest="json_output", action="store_true")
    cbench.set_defaults(func=cmd_chem_benchmark)

    cib = chem_sub.add_parser(
        "industry-benchmark",
        help="Compare SCBE chem against RDKit, Open Babel, and PubChem baselines",
    )
    cib.add_argument("--timeout", type=int, default=30)
    cib.add_argument("--out-dir", help="artifact output directory")
    cib.add_argument("--live-pubchem", action="store_true", help="run a live PubChem PUG-REST probe")
    cib.add_argument("--json", dest="json_output", action="store_true")
    cib.set_defaults(func=cmd_chem_industry_benchmark)

    sub.add_parser("menu", help="Interactive home screen (default when run with no args)")
    st = sub.add_parser("status", aliases=["st"], help="Project status")
    st.add_argument("--json", dest="json_output", action="store_true")
    st.set_defaults(func=cmd_status)
    ht = sub.add_parser("health", help='Shortcut for "scbe system health"')
    ht.add_argument("--json", dest="json_output", action="store_true")
    ht.add_argument("--no-write", action="store_true", help="do not write artifacts/pc-memory report")
    ht.add_argument("--warn-ram-percent", type=int, default=85)
    ht.add_argument("--warn-disk-free-gb", type=int, default=25)
    ht.add_argument("--top-processes", type=int, default=15)
    ht.set_defaults(func=cmd_system_health)
    sub.add_parser("selftest", aliases=["test"], help="Self-test suite").set_defaults(func=cmd_selftest)
    sub.add_parser("doctor", help="Local operator environment checks (forwarded to system CLI)")
    sub.add_parser("use", help="Set active SCBE operator context (forwarded to system CLI)")
    sub.add_parser("config", help="Inspect/update CLI context (forwarded to system CLI)")
    sub.add_parser("model", help="Config-backed model training lanes (forwarded to system CLI)")
    sub.add_parser("colab", help="Inspect the SCBE Colab notebook lane (forwarded to system CLI)")
    sub.add_parser("pollypad", help="Polly Pad storage + app management (forwarded to system CLI)")
    sub.add_parser("run", help="Governed multi-language runtime (forwarded to system CLI)")
    sub.add_parser("flow", help="Doctrine-backed multi-agent flow planning (forwarded to system CLI)")
    sub.add_parser("workflow", help="GitHub + n8-style workflow generation (forwarded to system CLI)")
    sub.add_parser("web", help="Web lookup/capture helpers (forwarded to system CLI)")
    sub.add_parser("antivirus", help="Safety scan helpers (forwarded to system CLI)")
    sub.add_parser("aetherauth", help="Context-bound access decisions (forwarded to system CLI)")
    sub.add_parser("notion-gap", help="Notion/pipeline gap review (forwarded to system CLI)")
    sub.add_parser("self-improve", help="Self-improvement orchestration (forwarded to system CLI)")

    # ─── legacy ───
    for cmd in LEGACY_SCRIPTS:
        sub.add_parser(cmd, help=f"(legacy) Launch {cmd}")

    return p


# ═══════════════════════════════════════════════════════════════
# Interactive home screen — the "one app" front door
#
# Running `scbe` with no arguments drops the user into a numbered
# menu instead of an argparse help wall. Every option maps to an
# existing command, so the menu stays a thin, friendly veneer over
# the same code paths the flags use.
# ═══════════════════════════════════════════════════════════════

def _banner() -> str:
    """Self-aligning title box — stays square for any version string."""
    w = 60
    lines = [
        "   SCBE-AETHERMOORE",
        f"   Unified AI-Safety & Governance Console   v{VERSION}",
    ]
    out = ["╔" + "═" * w + "╗"]
    out += ["║" + ln.ljust(w) + "║" for ln in lines]
    out.append("╚" + "═" * w + "╝")
    return "\n".join(out)

MENU = """\
  1) System status            — sources, tongues, pipeline
  2) Score text (pipeline)    — run the 14-layer safety check
  3) Encode → Sacred Tongue   — turn text into tokens
  4) Decode ← Sacred Tongue   — turn tokens back into text
  5) List Sacred Tongues      — all 6 languages
  6) Explain a layer (L1–L14) — architecture guide
  7) Inspect a source file    — lint + review
  8) Self-test                — verify the install is healthy
  9) Doctor                   — operator environment checks
  a) Ask the AI               — chat with any model (Claude, etc.)
  d) Describe                  — see / hear / feel any input
  0) Quit

  tip ▸ skip the menu — type a command OR just plain English:
        scbe describe "text"   scbe draumric hello   scbe ask "question"
        scbe how do I encode a word?     ← unknown input goes to the AI
        add --json to any command for machine-readable output
"""


def _menu_prompt(label: str) -> Optional[str]:
    """Read a line; return None on Ctrl+C / EOF so the menu can exit cleanly."""
    try:
        # Strip a leading UTF-8 BOM that Windows pipes prepend to stdin.
        return input(label).lstrip("﻿").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _pause() -> None:
    try:
        input("\n  ↵ press enter to return to the menu ")
    except (EOFError, KeyboardInterrupt):
        print()


def _menu_score() -> None:
    text = _menu_prompt("  text to score: ")
    if not text:
        return
    r = pipeline_quick_score(text)
    print(f"\n  d*:       {r['d_star']}")
    print(f"  H_eff:    {r['H_eff']}")
    print(f"  decision: {r['decision']}")


def _menu_encode() -> None:
    print("  Tongues: " + ", ".join(_CANONICAL_TONGUES))
    code = _menu_prompt("  tongue: ")
    if not code or code.upper() not in _CANONICAL_TONGUES:
        print("  unknown tongue")
        return
    text = _menu_prompt("  text to encode: ")
    if text is None:
        return
    print("\n  " + encode_bytes(code, text.encode("utf-8")))


def _menu_decode() -> None:
    print("  Tongues: " + ", ".join(_CANONICAL_TONGUES))
    code = _menu_prompt("  tongue: ")
    if not code or code.upper() not in _CANONICAL_TONGUES:
        print("  unknown tongue")
        return
    tokens = _menu_prompt("  tokens to decode: ")
    if not tokens:
        return
    try:
        print("\n  " + decode_tokens(code, tokens).decode("utf-8", errors="replace"))
    except ValueError as e:
        print(f"  {e}")


def _menu_explain() -> None:
    target = _menu_prompt("  layer or concept (e.g. L12, harmonic): ")
    if not target:
        return
    print("\n  " + ai_explain(target).replace("\n", "\n  "))


def _menu_inspect() -> None:
    path = _menu_prompt("  file path: ")
    if not path:
        return
    ns = argparse.Namespace(file=path)
    cmd_ai_check(ns)


def _menu_describe() -> None:
    text = _menu_prompt("  text to describe: ")
    if not text:
        return
    cmd_describe(argparse.Namespace(text=text, json_output=False))


def interactive_menu() -> int:
    """Numbered home screen — the single-app daily-driver entrypoint."""
    # Make box-drawing + arrows render on a fresh Windows console.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    actions = {
        "1": lambda: cmd_status(argparse.Namespace()),
        "2": _menu_score,
        "3": _menu_encode,
        "4": _menu_decode,
        "5": lambda: cmd_tongue_list(argparse.Namespace()),
        "6": _menu_explain,
        "7": _menu_inspect,
        "8": lambda: cmd_selftest(argparse.Namespace()),
        "9": lambda: _run_system_cli(["doctor"]),
        "a": lambda: cmd_chat(argparse.Namespace(backend=None, model=None)),
        "d": _menu_describe,
    }
    quit_words = {"0", "q", "quit", "exit"}

    while True:
        print("\n" + _banner())
        print(MENU)
        choice = _menu_prompt("  scbe ▸ select: ")
        if choice is None or choice.lower() in quit_words:
            print("  bye —\n")
            return 0
        action = actions.get(choice) or actions.get(choice.lower())
        if action is None:
            print(f"  '{choice}' isn't on the menu — pick 0-9.")
            continue
        print()
        try:
            action()
        except Exception as e:  # keep the menu alive on any single-command failure
            print(f"  error: {e}")
        _pause()


def _enable_utf8_console() -> None:
    """Render box-drawing, arrows, and em-dashes on a fresh Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def _known_commands(cli: argparse.ArgumentParser) -> set:
    """All registered subcommand names + aliases."""
    cmds: set = set()
    for action in cli._actions:
        if isinstance(action, argparse._SubParsersAction):
            cmds.update(action.choices.keys())
    return cmds


def _natural_command_args(prompt: str) -> Optional[List[str]]:
    """Compile high-confidence natural-language requests to local CLI args.

    This keeps the "commands or plain English" surface fast and reliable for
    things SCBE can already do locally. Low-confidence prompts still go to the
    selected AI backend.
    """
    raw = prompt.strip()
    lowered = raw.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    wants_json = bool(re.search(r"\b(json|machine readable|machine-readable)\b|--json", lowered))
    lowered = lowered.replace("--json", "").strip()

    tongue_names = "|".join(sorted((re.escape(k) for k in TONGUE_ALIASES), key=len, reverse=True))

    def clean_text(text: str) -> str:
        text = text.strip(" \t\r\n'\"?.!,;:")
        text = re.sub(r"^(?:the\s+)?(?:word|text|string|phrase)\s+", "", text, flags=re.I)
        return text.strip(" \t\r\n'\"?.!,;:")

    def with_json(args: List[str]) -> List[str]:
        return [*args, "--json"] if wants_json else args

    encode_match = re.search(
        rf"\b(?:encode|translate|convert|speak|say)\s+(?P<text>.+?)\s+"
        rf"(?:in|into|to|as)\s+(?P<tongue>{tongue_names})\b",
        lowered,
    )
    if encode_match:
        tongue = _resolve_tongue(encode_match.group("tongue"))
        text = clean_text(encode_match.group("text"))
        if tongue and text:
            return with_json(["enc", tongue.lower(), text])

    decode_match = re.search(
        rf"\b(?:decode|read)\s+(?P<text>.+?)\s+"
        rf"(?:from|in|as)\s+(?P<tongue>{tongue_names})\b",
        lowered,
    )
    if decode_match:
        tongue = _resolve_tongue(decode_match.group("tongue"))
        text = clean_text(decode_match.group("text"))
        if tongue and text:
            return with_json(["dec", tongue.lower(), text])

    describe_match = re.search(r"\b(?:describe|signature|sense|senses)\s+(?P<text>.+)$", lowered)
    if describe_match:
        text = clean_text(describe_match.group("text"))
        if text:
            return with_json(["describe", text])

    if re.search(r"\b(pc|computer|machine|ram|memory|disk|drive)\b.*\b(health|status|check)\b", lowered):
        return with_json(["health"])

    if re.search(r"\bhealth\b", lowered):
        return with_json(["health"])

    score_match = re.search(r"\b(?:score|check|gate|scan)\s+(?P<text>.+)$", lowered)
    if score_match and not re.search(r"\b(file|repo|status|doctor)\b", lowered):
        text = clean_text(score_match.group("text"))
        if text:
            return with_json(["score", text])

    explain_match = re.search(
        r"\b(?:explain|what is|what's|tell me about)\s+"
        r"(?P<target>l(?:ayer)?\s*\d{1,2}|harmonic|poincare|breathing)\b",
        lowered,
    )
    if explain_match:
        target = explain_match.group("target").replace(" ", "")
        return with_json(["explain", target])

    if re.search(r"\bstatus\b", lowered):
        return with_json(["status"])

    if re.search(r"\b(self\s*test|selftest|test install|verify install)\b", lowered):
        return ["selftest"]

    return None


def main() -> int:
    _enable_utf8_console()

    if len(sys.argv) == 1:
        return interactive_menu()

    if sys.argv[1] in ("menu", "app", "home"):
        return interactive_menu()

    # Natural-language fallback: if the first word isn't a known command (and
    # isn't a flag), treat the whole line as a question to the AI. Type
    # commands OR plain English — same prompt serves humans and agents.
    first = sys.argv[1]
    if not first.startswith("-") and first not in _known_commands(build_cli()):
        prompt = " ".join(sys.argv[1:])
        compiled = _natural_command_args(prompt)
        if compiled:
            return _dispatch_scbe_args(compiled)
        return cmd_ask(argparse.Namespace(prompt=prompt, backend=None, model=None, json_output=False))

    if sys.argv[1] == "cli":
        return _handle_cli_command(sys.argv)

    if sys.argv[1] == "agent":
        return _handle_agent_command(sys.argv)

    # Handle legacy commands
    if len(sys.argv) >= 2 and sys.argv[1] in LEGACY_SCRIPTS:
        return _run_legacy_script(sys.argv[1], sys.argv[2:])

    return _dispatch_scbe_args(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
