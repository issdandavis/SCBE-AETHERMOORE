"""
SCBE Tier-2 AST Compiler — GAP-2 close.

Walks a Python AST (or TypeScript via structural heuristics) and maps
every node to a Sacred Tongue atom, then aggregates into a DimVec and
emits a 48-bit hex semantic fingerprint.

Cross-domain proof:
  Python/TS source → AST node taxonomy → 6D Sacred Tongue geometry
  → valence-weighted DimVec → harmonic wall scoring
"""

from __future__ import annotations

import ast
import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# DimVec type and atom profiles (mirrors semantic-bridge.ts)
# ---------------------------------------------------------------------------

DimVec = Tuple[float, float, float, float, float, float]  # KO AV RU CA UM DR

# Atom profiles: (dims, valence)
ATOM_PROFILES: Dict[str, Tuple[DimVec, int]] = {
    "BLOCK":     ((0.85, 0.10, 0.90, 0.88, 0.80, 0.05), 2),
    "TRANSFORM": ((0.50, 0.82, 0.78, 0.92, 0.15, 0.55), 4),
    "FLOW":      ((0.60, 0.95, 0.55, 0.25, 0.45, 0.80), 3),
    "WATER":     ((0.88, 0.90, 0.20, 0.10, 0.50, 0.60), 2),
    "ANNOUNCE":  ((0.60, 0.30, 0.88, 0.18, 0.38, 0.92), 3),
    "EXPAND":    ((0.55, 0.82, 0.58, 0.88, 0.20, 0.74), 4),
    "REQUEST":   ((0.82, 0.18, 0.48, 0.12, 0.92, 0.10), 2),
    "PIVOT":     ((0.30, 0.75, 0.40, 0.62, 0.68, 0.45), 3),
    "CARRY":     ((0.70, 0.55, 0.72, 0.80, 0.30, 0.38), 3),
    "HOLD":      ((0.40, 0.10, 0.35, 0.08, 0.22, 0.15), 1),
}


def _weighted_add(acc: list[float], dims: DimVec, valence: int) -> None:
    for i, v in enumerate(dims):
        acc[i] += v * valence


def _normalize(acc: list[float]) -> DimVec:
    max_v = max(acc) or 1.0
    return tuple(min(1.0, v / max_v) for v in acc)  # type: ignore[return-value]


def dimvec_to_hex(dims: DimVec) -> str:
    """Quantize DimVec to 8 bits per axis → 12-char hex."""
    return "".join(format(int(d * 255), "02x") for d in dims)


def hex_to_dimvec(h: str) -> DimVec:
    """Inverse of dimvec_to_hex (lossy at 1/255 precision)."""
    assert len(h) == 12
    return tuple(int(h[i:i+2], 16) / 255.0 for i in range(0, 12, 2))  # type: ignore


def cosine_similarity(a: DimVec, b: DimVec) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb > 0 else 0.0


# ---------------------------------------------------------------------------
# Python AST → atom classification
# ---------------------------------------------------------------------------

# Maps AST node type name → atom name
_AST_NODE_ATOM: Dict[str, str] = {
    # Control / constraint → BLOCK
    "If": "BLOCK", "Try": "BLOCK", "ExceptHandler": "BLOCK",
    "Assert": "BLOCK", "Raise": "BLOCK", "With": "BLOCK",
    "Match": "BLOCK",
    # Definitions / declarations → ANNOUNCE (create contract)
    "FunctionDef": "ANNOUNCE", "AsyncFunctionDef": "ANNOUNCE",
    "ClassDef": "ANNOUNCE",
    # Calls / computations → TRANSFORM
    "Call": "TRANSFORM", "BinOp": "TRANSFORM", "UnaryOp": "TRANSFORM",
    "AugAssign": "TRANSFORM", "NamedExpr": "TRANSFORM",
    # Assignment / mutation → TRANSFORM
    "Assign": "TRANSFORM", "AnnAssign": "TRANSFORM",
    # Imports → FLOW
    "Import": "FLOW", "ImportFrom": "FLOW",
    # Return / yield → FLOW
    "Return": "FLOW", "Yield": "FLOW", "YieldFrom": "FLOW",
    # Loops → FLOW
    "For": "FLOW", "AsyncFor": "FLOW", "While": "FLOW",
    # Comprehensions → EXPAND
    "ListComp": "EXPAND", "SetComp": "EXPAND", "DictComp": "EXPAND",
    "GeneratorExp": "EXPAND",
    # Literals / constants → WATER
    "Constant": "WATER", "JoinedStr": "WATER",
    # Logical comparisons → CARRY (backed assertion)
    "Compare": "CARRY", "BoolOp": "CARRY",
    # Delete / global → PIVOT
    "Delete": "PIVOT", "Global": "PIVOT", "Nonlocal": "PIVOT",
    # Pass / ellipsis → HOLD
    "Pass": "HOLD", "Ellipsis": "HOLD",
}


@dataclass
class NodeRecord:
    node_type: str
    atom: str
    lineno: int
    depth: int


@dataclass
class CompileResult:
    source: str
    language: str
    dimvec: DimVec
    hex_fingerprint: str
    node_count: int
    atom_counts: Dict[str, int]
    dominant_atom: str
    sha256: str
    nodes: List[NodeRecord] = field(default_factory=list)

    def harmonic_score(self, safe_origin: Optional[DimVec] = None) -> float:
        """L12 harmonic wall: H(d, pd) = 1/(1 + φ*d_H + 2*pd)."""
        PHI = 1.6180339887
        if safe_origin is None:
            # Safe origin: observation-heavy, low reactivity
            safe_origin = (0.85, 0.15, 0.60, 0.30, 0.20, 0.40)
        d_H = 1.0 - cosine_similarity(self.dimvec, safe_origin)
        pd = self.atom_counts.get("BLOCK", 0) / max(self.node_count, 1)
        return 1.0 / (1.0 + PHI * d_H + 2.0 * pd)

    def risk_tier(self) -> str:
        s = self.harmonic_score()
        if s >= 0.60:
            return "ALLOW"
        if s >= 0.30:
            return "QUARANTINE"
        return "DENY"


class PythonASTCompiler(ast.NodeVisitor):
    def __init__(self) -> None:
        self._records: list[NodeRecord] = []
        self._depth = 0

    def generic_visit(self, node: ast.AST) -> None:
        ntype = type(node).__name__
        atom = _AST_NODE_ATOM.get(ntype)
        if atom:
            lineno = getattr(node, "lineno", 0)
            self._records.append(NodeRecord(ntype, atom, lineno, self._depth))
        self._depth += 1
        super().generic_visit(node)
        self._depth -= 1

    def compile(self, source: str) -> CompileResult:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = ast.parse(source, mode="eval") if source.strip().startswith("(") else None  # type: ignore
        if tree is None:
            return _empty_result(source, "python")
        self.visit(tree)
        return _build_result(source, "python", self._records)


# ---------------------------------------------------------------------------
# TypeScript structural compiler (regex-based, no full TS parser needed)
# ---------------------------------------------------------------------------

_TS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bif\s*\(|\belse\b|\btry\s*\{|\bcatch\s*\(|\bthrow\b"), "BLOCK"),
    (re.compile(r"\bfunction\b|\bclass\b|\bconst\b.*=.*=>\s*\{|\basync\b"), "ANNOUNCE"),
    (re.compile(r"\bimport\b|\bexport\b|\brequire\s*\("), "FLOW"),
    (re.compile(r"\breturn\b|\byield\b"), "FLOW"),
    (re.compile(r"\bfor\b|\bwhile\b|\b\.map\b|\b\.filter\b|\b\.reduce\b"), "FLOW"),
    (re.compile(r"\b\w+\s*\(.*\)|\bnew\b|\bawait\b"), "TRANSFORM"),
    (re.compile(r"[+\-*/%]=|=(?!=)|[+\-*/%]{2}"), "TRANSFORM"),
    (re.compile(r"['\"`].*?['\"`]|\b\d+\.?\d*\b"), "WATER"),
    (re.compile(r"\b===\b|\b!==\b|\b&&\b|\b\|\|\b|\b>\b|\b<\b"), "CARRY"),
    (re.compile(r"\bdelete\b|\bglobal\b|\bnamespace\b"), "PIVOT"),
    (re.compile(r"\.{3}|/\*\*|\*/\s*$"), "EXPAND"),
]


def _compile_typescript(source: str) -> CompileResult:
    records: list[NodeRecord] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        for pattern, atom in _TS_PATTERNS:
            if pattern.search(line):
                records.append(NodeRecord("TS:pattern", atom, lineno, 0))
    return _build_result(source, "typescript", records)


# ---------------------------------------------------------------------------
# Shared aggregation
# ---------------------------------------------------------------------------

def _empty_result(source: str, lang: str) -> CompileResult:
    dims: DimVec = (0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    return CompileResult(
        source=source, language=lang, dimvec=dims,
        hex_fingerprint=dimvec_to_hex(dims), node_count=0,
        atom_counts={}, dominant_atom="HOLD",
        sha256=hashlib.sha256(source.encode()).hexdigest(),
    )


def _build_result(source: str, lang: str, records: list[NodeRecord]) -> CompileResult:
    if not records:
        return _empty_result(source, lang)

    acc = [0.0] * 6
    atom_counts: Dict[str, int] = {}
    for rec in records:
        dims, valence = ATOM_PROFILES[rec.atom]
        _weighted_add(acc, dims, valence)
        atom_counts[rec.atom] = atom_counts.get(rec.atom, 0) + 1

    dimvec = _normalize(acc)
    dominant = max(atom_counts, key=lambda k: atom_counts[k])

    return CompileResult(
        source=source,
        language=lang,
        dimvec=dimvec,
        hex_fingerprint=dimvec_to_hex(dimvec),
        node_count=len(records),
        atom_counts=atom_counts,
        dominant_atom=dominant,
        sha256=hashlib.sha256(source.encode()).hexdigest(),
        nodes=records,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_python(source: str) -> CompileResult:
    return PythonASTCompiler().compile(source)


def compile_typescript(source: str) -> CompileResult:
    return _compile_typescript(source)


def compile_file(path: str | Path) -> CompileResult:
    p = Path(path)
    source = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
        return compile_typescript(source)
    return compile_python(source)


def cross_file_similarity(path_a: str | Path, path_b: str | Path) -> float:
    """Cosine similarity between two files' DimVecs — cross-domain semantic distance."""
    ra = compile_file(path_a)
    rb = compile_file(path_b)
    return cosine_similarity(ra.dimvec, rb.dimvec)
