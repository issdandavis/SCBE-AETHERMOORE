#!/usr/bin/env python3
"""
Canonical Code Preprocessor — Stage -1 for SCBE Translateral Training

All music is the same band of notes arranged in slightly different ways.
All code is the same band of primitives arranged in slightly different ways.

This script turns raw code atoms into canonical graph IR with:
  - Code notes   (finite primitive vocabulary — the "notes" of code)
  - Multigraph IR (control-flow + data-flow + scope + sequence edges)
  - Spectral features (topological summary from graph Laplacian)
  - Hyperbolic coordinates (Poincare disk placement via SCBE harmonic wall)
  - Consensus scores (structural validity + threat alignment + inverse consistency)

Then generates the "C" condition for A/B/C testing:
  A = round5_code_baseline_l3.jsonl         (L3 only — mainstream LLM view)
  B = round5_code_multiview_l0l3.jsonl      (L0-L3 — structural vision)
  C = round6_canonical_ir_l3.jsonl          (L-1 + L0-L3 — full canonical IR)

The question: does adding the canonical representation layer on top of
multi-view training produce a measurable improvement in code understanding?

Usage:
    python scripts/canonicalize_code_atoms.py [--count 10000] [--seed 42]
"""

from __future__ import annotations

import ast
import json
import math
import hashlib
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# --- numpy (optional, for spectral eigenfeatures) ---
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore[assignment]

# --- Constants ---
PHI = (1 + math.sqrt(5)) / 2
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "training-data" / "sft"

# --- Import existing generator (same directory) ---
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from generate_translateral_code_sft import (
        ATOMS,
        THREATS,
        COMPLEXITY_MODIFIERS,
        LANGUAGES,
        build_l0_view,
        build_l1_view,
        build_l2_view,
        build_l3_view,
        generate_instruction,
    )
except ImportError as e:
    print(f"ERROR: Could not import from generate_translateral_code_sft: {e}")
    print("Ensure scripts/generate_translateral_code_sft.py exists.")
    sys.exit(1)


# ============================================================================
# SECTION 1: CODE NOTES VOCABULARY
# ============================================================================
# The finite primitive alphabet of all programs.  Like music notes, the set
# is small and fixed — mastery is arrangement, not invention.

NOTE_MAP: dict[type, str] = {
    # ── Control flow ──
    ast.If: "BRANCH",
    ast.For: "LOOP",
    ast.While: "LOOP",
    ast.Try: "ERROR_TRAP",
    ast.ExceptHandler: "ERROR_CATCH",
    ast.With: "RESOURCE_SCOPE",
    ast.Return: "RETURN",
    ast.Yield: "STREAM",
    ast.YieldFrom: "STREAM",
    ast.Raise: "SIGNAL",
    ast.Assert: "GUARD",
    ast.Break: "LOOP_EXIT",
    ast.Continue: "LOOP_SKIP",
    ast.Pass: "NOP",
    # ── Data operations ──
    ast.Assign: "BIND",
    ast.AugAssign: "BIND_MUTATE",
    ast.AnnAssign: "BIND_TYPED",
    ast.Delete: "DEALLOCATE",
    # ── Definitions ──
    ast.FunctionDef: "FUNC_DEF",
    ast.AsyncFunctionDef: "FUNC_DEF_ASYNC",
    ast.ClassDef: "TYPE_DEF",
    ast.Lambda: "FUNC_ANON",
    # ── Imports ──
    ast.Import: "LOAD",
    ast.ImportFrom: "LOAD",
    # ── Expressions ──
    ast.Call: "CALL",
    ast.Subscript: "INDEX",
    ast.Attribute: "ACCESS",
    ast.BinOp: "TRANSFORM",
    ast.UnaryOp: "TRANSFORM",
    ast.Compare: "COMPARE",
    ast.BoolOp: "LOGIC",
    # ── Comprehensions ──
    ast.ListComp: "COMPREHEND",
    ast.SetComp: "COMPREHEND",
    ast.DictComp: "COMPREHEND",
    ast.GeneratorExp: "COMPREHEND",
    # ── Scope ──
    ast.Global: "SCOPE_ESCAPE",
    ast.Nonlocal: "SCOPE_ESCAPE",
}

# Semantic categories — balance across these tells you what KIND of code it is
NOTE_CATEGORIES = {
    "control": {"BRANCH", "LOOP", "LOOP_EXIT", "LOOP_SKIP", "RETURN", "NOP"},
    "data": {
        "BIND", "BIND_MUTATE", "BIND_TYPED", "DEALLOCATE",
        "INDEX", "ACCESS", "TRANSFORM", "COMPARE", "LOGIC",
    },
    "safety": {"ERROR_TRAP", "ERROR_CATCH", "GUARD", "SIGNAL", "RESOURCE_SCOPE"},
    "structure": {"FUNC_DEF", "FUNC_DEF_ASYNC", "TYPE_DEF", "FUNC_ANON", "LOAD"},
    "composition": {"CALL", "COMPREHEND", "STREAM"},
    "scope": {"SCOPE_ESCAPE"},
}

# Language-specific projection notes (appended to core notes)
LANGUAGE_PROJECTIONS = {
    "python": ["GC_MANAGED", "DUCK_TYPED", "INDENT_SCOPED"],
    "typescript": ["TYPE_ANNOTATED", "PROTOTYPE_CHAIN", "EVENT_LOOP"],
    "rust": ["OWNERSHIP", "BORROW_CHECK", "LIFETIME_BOUND", "NO_GC"],
    "go": ["GOROUTINE_SAFE", "CHANNEL_COMM", "DEFER_CLEANUP", "GC_MANAGED"],
    "sql": ["SET_OPERATION", "DECLARATIVE", "TRANSACTION_BOUND"],
}

# Domain -> angular sector (radians) for Poincare disk embedding
DOMAIN_SECTORS: dict[str, float] = {
    "fundamentals": 0.0,
    "data_structures": math.pi / 3,
    "io_serialization": 2 * math.pi / 3,
    "networking": math.pi,
    "security": 4 * math.pi / 3,
    "concurrency": 5 * math.pi / 3,
    "caching": math.pi / 6,
    "distributed_systems": math.pi / 2,
    "observability": 5 * math.pi / 6,
    "configuration": 7 * math.pi / 6,
    "validation": 3 * math.pi / 2,
    "database": 11 * math.pi / 6,
}

TIER_DEPTH = {"basic": 0.3, "intermediate": 0.55, "advanced": 0.8}

# What notes defend against each threat — the "score" of a good defense
THREAT_DEFENSES: dict[str, set[str]] = {
    "type_confusion": {"GUARD", "COMPARE", "BIND_TYPED"},
    "unbounded_iteration": {"GUARD", "LOOP_EXIT", "COMPARE"},
    "float_precision": {"COMPARE", "GUARD", "TRANSFORM"},
    "exception_swallowing": {"ERROR_TRAP", "ERROR_CATCH", "SIGNAL"},
    "hash_dos": {"GUARD", "COMPARE"},
    "unbounded_memory": {"GUARD", "COMPARE", "DEALLOCATE"},
    "stack_overflow_via_depth": {"GUARD", "COMPARE", "LOOP_EXIT"},
    "billion_laughs": {"GUARD", "COMPARE", "RESOURCE_SCOPE"},
    "toctou_race": {"RESOURCE_SCOPE", "GUARD"},
    "dns_rebinding": {"GUARD", "COMPARE"},
    "slowloris": {"GUARD", "RESOURCE_SCOPE", "COMPARE"},
    "timing_oracle": {"GUARD", "COMPARE"},
    "nonce_reuse": {"GUARD", "BIND"},
    "algorithm_confusion": {"GUARD", "COMPARE", "BIND_TYPED"},
    "privilege_escalation": {"GUARD", "COMPARE", "ERROR_TRAP"},
    "deadlock": {"RESOURCE_SCOPE", "GUARD"},
    "sql_injection_via_identifier": {"GUARD", "COMPARE"},
    "compensation_failure": {"ERROR_TRAP", "ERROR_CATCH"},
    "timing_side_channel": {"GUARD", "COMPARE"},
    "secret_in_logs": {"GUARD", "COMPARE"},
    "unicode_homoglyph": {"GUARD", "COMPARE"},
    "log_injection": {"GUARD", "COMPARE"},
    "cache_poisoning": {"GUARD", "COMPARE"},
}

# Domain affinity: what notes "belong" to each domain manifold
DOMAIN_AFFINITY: dict[str, set[str]] = {
    "fundamentals": {"BIND", "BIND_TYPED", "BIND_MUTATE", "CALL", "RETURN", "BRANCH", "LOOP", "FUNC_DEF", "COMPARE", "TRANSFORM"},
    "data_structures": {"BIND", "INDEX", "ACCESS", "LOOP", "COMPARE", "COMPREHEND", "FUNC_DEF", "RETURN", "TRANSFORM"},
    "io_serialization": {"BIND", "CALL", "ERROR_TRAP", "ERROR_CATCH", "RESOURCE_SCOPE", "STREAM", "TRANSFORM", "GUARD"},
    "networking": {"CALL", "ERROR_TRAP", "ERROR_CATCH", "GUARD", "RESOURCE_SCOPE", "SIGNAL", "BIND", "STREAM"},
    "security": {"GUARD", "ERROR_TRAP", "ERROR_CATCH", "COMPARE", "SIGNAL", "RESOURCE_SCOPE", "BIND_TYPED", "CALL"},
    "concurrency": {"CALL", "BIND", "GUARD", "RESOURCE_SCOPE", "SIGNAL", "LOOP", "FUNC_DEF_ASYNC", "ERROR_TRAP"},
    "caching": {"BIND", "INDEX", "ACCESS", "COMPARE", "GUARD", "CALL", "RETURN", "DEALLOCATE"},
    "distributed_systems": {"CALL", "ERROR_TRAP", "ERROR_CATCH", "GUARD", "SIGNAL", "RESOURCE_SCOPE", "STREAM", "LOOP"},
    "observability": {"CALL", "BIND", "GUARD", "TRANSFORM", "STREAM", "ERROR_TRAP", "SIGNAL", "COMPARE"},
    "configuration": {"BIND", "BIND_TYPED", "GUARD", "COMPARE", "BRANCH", "CALL", "ERROR_TRAP", "RETURN"},
    "validation": {"GUARD", "COMPARE", "BRANCH", "ERROR_TRAP", "ERROR_CATCH", "BIND_TYPED", "RETURN", "CALL"},
    "database": {"CALL", "ERROR_TRAP", "ERROR_CATCH", "RESOURCE_SCOPE", "BIND", "GUARD", "TRANSFORM", "STREAM"},
}

# Notes that appear in nearly every domain — universal glue, not diagnostic
UNIVERSAL_NOTES: set[str] = {"CALL", "BIND", "RETURN"}


def compute_boundary_operators(
    notes: list[str],
    atom: dict,
    hyperbolic: dict[str, Any],
) -> dict[str, Any]:
    """Classify notes into RETAIN / DEFER / LIFT and compute complement residual.

    For a given domain manifold M_i:
      RETAIN: notes native to M_i (local manifold membership)
      DEFER:  notes in UNIVERSAL_NOTES (ambiguous, belong everywhere)
      LIFT:   notes foreign to M_i — candidates for boundary projection

    Complement residual R_i:
      Expected notes for M_i that are ABSENT — the inverse null space.
      These represent what the code *should* have but doesn't.

    Boundary lift:
      Foreign notes are projected into hyperbolic space at fractional angles
      between the source domain sector and the target domain's sector.
      This creates controlled cross-domain incursion paths.
    """
    domain = atom.get("domain", "fundamentals")
    native_notes = DOMAIN_AFFINITY.get(domain, set())
    note_set = set(notes)

    retained: list[str] = []
    deferred: list[str] = []
    lifted: list[str] = []

    for note in notes:
        if note in UNIVERSAL_NOTES:
            deferred.append(note)
        elif note in native_notes:
            retained.append(note)
        else:
            lifted.append(note)

    # Complement residual: expected notes that are absent
    complement_residual = sorted(native_notes - note_set - UNIVERSAL_NOTES)

    # Boundary score: how much of the code lives outside its own domain?
    total = max(len(notes), 1)
    boundary_score = len(lifted) / total

    # Lift targets: for each lifted note, find the domain(s) it belongs to
    # and compute fractional angles for cross-domain projection
    source_angle = DOMAIN_SECTORS.get(domain, 0.0)
    lift_targets: list[dict[str, Any]] = []

    for note in set(lifted):
        target_domains = [d for d, ns in DOMAIN_AFFINITY.items() if note in ns and d != domain]
        if not target_domains:
            continue
        for td in target_domains:
            target_angle = DOMAIN_SECTORS.get(td, 0.0)
            # Fractional angle: 60% interpolation from source toward target
            # This places the lifted note in the boundary zone, not fully in the target
            frac_angle = source_angle + 0.6 * _angle_diff(source_angle, target_angle)
            lift_targets.append({
                "note": note,
                "from_domain": domain,
                "to_domain": td,
                "fractional_angle": round(frac_angle % (2 * math.pi), 4),
            })

    # Complement density: fraction of expected notes that are absent
    expected_specific = native_notes - UNIVERSAL_NOTES
    complement_density = len(complement_residual) / max(len(expected_specific), 1)

    return {
        "retain_count": len(retained),
        "defer_count": len(deferred),
        "lift_count": len(lifted),
        "retained": retained,
        "deferred": deferred,
        "lifted": lifted,
        "complement_residual": complement_residual,
        "complement_density": round(complement_density, 3),
        "boundary_score": round(boundary_score, 3),
        "lift_targets": lift_targets,
    }


def _angle_diff(a: float, b: float) -> float:
    """Signed shortest angular distance from a to b on [0, 2*pi)."""
    d = (b - a) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return d


# ============================================================================
# SECTION 2: AST -> CODE NOTES EXTRACTION
# ============================================================================


def extract_notes(code_str: str) -> list[str]:
    """Parse Python code and extract the ordered sequence of code notes."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return ["PARSE_ERROR"]

    notes: list[str] = []
    for node in ast.walk(tree):
        note = NOTE_MAP.get(type(node))
        if note:
            notes.append(note)
    return notes if notes else ["EMPTY"]


def compute_note_histogram(notes: list[str]) -> dict[str, int]:
    return dict(Counter(notes))


def compute_category_balance(notes: list[str]) -> dict[str, float]:
    if not notes or notes[0] in ("PARSE_ERROR", "EMPTY"):
        return {cat: 0.0 for cat in NOTE_CATEGORIES}
    total = len(notes)
    balance = {}
    for cat, note_set in NOTE_CATEGORIES.items():
        count = sum(1 for n in notes if n in note_set)
        balance[cat] = round(count / total, 2)
    return balance


# ============================================================================
# SECTION 3: GRAPH IR CONSTRUCTION
# ============================================================================


class GraphIR:
    """Multigraph intermediate representation of code structure."""

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, str]] = []
        self._counter = 0

    def add_node(self, kind: str, label: str = "", line: int = 0) -> str:
        nid = f"n{self._counter}"
        self._counter += 1
        self.nodes.append({"id": nid, "kind": kind, "label": label, "line": line})
        return nid

    def add_edge(self, src: str, dst: str, edge_type: str) -> None:
        self.edges.append({"src": src, "dst": dst, "type": edge_type})

    def summary(self) -> dict[str, Any]:
        edge_types = Counter(e["type"] for e in self.edges)
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "edge_types": dict(edge_types),
        }


def build_graph_ir(code_str: str) -> GraphIR:
    """Build a multigraph IR from Python source code."""
    graph = GraphIR()

    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        graph.add_node("PARSE_ERROR", "unparseable")
        return graph

    # Phase 1: create nodes for significant AST elements
    node_map: dict[int, str] = {}  # python id(ast_node) -> graph node id
    for node in ast.walk(tree):
        note = NOTE_MAP.get(type(node))
        if note:
            label = ""
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                label = node.name
            line = getattr(node, "lineno", 0)
            nid = graph.add_node(note, label, line)
            node_map[id(node)] = nid

    # Phase 2: control-flow edges (AST parent -> child)
    for node in ast.walk(tree):
        parent_nid = node_map.get(id(node))
        if not parent_nid:
            continue
        for child in ast.iter_child_nodes(node):
            child_nid = node_map.get(id(child))
            if child_nid:
                graph.add_edge(parent_nid, child_nid, "control_flow")

    # Phase 3: sequence edges (consecutive statements in a body)
    for node in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody", "handlers"):
            block = getattr(node, attr, None)
            if not isinstance(block, list):
                continue
            prev_nid = None
            for stmt in block:
                stmt_nid = node_map.get(id(stmt))
                if stmt_nid and prev_nid:
                    graph.add_edge(prev_nid, stmt_nid, "sequence")
                if stmt_nid:
                    prev_nid = stmt_nid

    # Phase 4: branch edges (if/try -> alternative blocks)
    for node in ast.walk(tree):
        parent_nid = node_map.get(id(node))
        if not parent_nid:
            continue
        for attr in ("orelse", "finalbody", "handlers"):
            block = getattr(node, attr, None)
            if isinstance(block, list) and block:
                first_nid = node_map.get(id(block[0]))
                if first_nid:
                    graph.add_edge(parent_nid, first_nid, "branch_flow")

    # Phase 5: loop back-edges
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loop_nid = node_map.get(id(node))
            body = getattr(node, "body", [])
            if body and loop_nid:
                last_nid = node_map.get(id(body[-1]))
                if last_nid:
                    graph.add_edge(last_nid, loop_nid, "back_edge")

    # Phase 6: data-flow edges (variable def -> use, simplified)
    var_defs: dict[str, list[str]] = defaultdict(list)
    var_uses: dict[str, list[str]] = defaultdict(list)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            # Find nearest ancestor that has a graph node
            # Simplified: use the Name node's line to match closest statement node
            line = getattr(node, "lineno", 0)
            closest_nid = _find_closest_node(graph.nodes, line)
            if closest_nid:
                if isinstance(node.ctx, ast.Store):
                    var_defs[node.id].append(closest_nid)
                elif isinstance(node.ctx, ast.Load):
                    var_uses[node.id].append(closest_nid)

    for var_name in var_defs:
        if var_name in var_uses:
            for def_nid in var_defs[var_name]:
                for use_nid in var_uses[var_name]:
                    if def_nid != use_nid:
                        graph.add_edge(def_nid, use_nid, "data_flow")

    return graph


def _find_closest_node(nodes: list[dict], target_line: int) -> str | None:
    """Find the graph node on or nearest before a given line."""
    best = None
    best_dist = float("inf")
    for n in nodes:
        dist = abs(n["line"] - target_line)
        if dist < best_dist:
            best_dist = dist
            best = n["id"]
    return best


# ============================================================================
# SECTION 4: SPECTRAL FEATURES
# ============================================================================


def compute_spectral_features(graph: GraphIR) -> dict[str, Any]:
    """Compute topological features from the graph IR."""
    n = len(graph.nodes)
    m = len(graph.edges)

    if n == 0:
        return {
            "node_count": 0, "edge_count": 0, "density": 0.0,
            "max_degree": 0, "avg_degree": 0.0, "branch_factor": 0.0,
            "cycle_count": 0, "component_count": 0,
        }

    # Degree computation
    degree: Counter[str] = Counter()
    out_degree: Counter[str] = Counter()
    for e in graph.edges:
        degree[e["src"]] += 1
        degree[e["dst"]] += 1
        out_degree[e["src"]] += 1

    max_deg = max(degree.values()) if degree else 0
    avg_deg = sum(degree.values()) / n if n > 0 else 0.0

    # Density
    max_edges = n * (n - 1) if n > 1 else 1
    density = m / max_edges

    # Branch factor (avg out-degree of nodes with out-degree > 1)
    branching = [d for d in out_degree.values() if d > 1]
    branch_factor = sum(branching) / len(branching) if branching else 1.0

    # Cycles (approximate: count back_edge + loop notes)
    cycle_count = sum(1 for e in graph.edges if e["type"] == "back_edge")

    # Connected components (BFS on undirected view)
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph.edges:
        adj[e["src"]].add(e["dst"])
        adj[e["dst"]].add(e["src"])

    visited: set[str] = set()
    components = 0
    for node in graph.nodes:
        nid = node["id"]
        if nid not in visited:
            components += 1
            queue = [nid]
            while queue:
                curr = queue.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                queue.extend(adj[curr] - visited)

    result: dict[str, Any] = {
        "node_count": n,
        "edge_count": m,
        "density": round(density, 3),
        "max_degree": max_deg,
        "avg_degree": round(avg_deg, 2),
        "branch_factor": round(branch_factor, 2),
        "cycle_count": cycle_count,
        "component_count": components,
    }

    # numpy spectral eigenfeatures (if available)
    if HAS_NUMPY and 1 < n <= 200:
        try:
            id_to_idx = {node["id"]: i for i, node in enumerate(graph.nodes)}
            A = np.zeros((n, n), dtype=np.float64)
            for e in graph.edges:
                i, j = id_to_idx.get(e["src"]), id_to_idx.get(e["dst"])
                if i is not None and j is not None:
                    A[i, j] = 1.0
                    A[j, i] = 1.0  # undirected for Laplacian
            D = np.diag(A.sum(axis=1))
            L = D - A
            eigenvalues = np.sort(np.linalg.eigvalsh(L))
            result["laplacian_rank"] = int(np.sum(eigenvalues > 1e-10))
            if len(eigenvalues) > 1:
                result["algebraic_connectivity"] = round(float(eigenvalues[1]), 4)
            result["spectral_radius"] = round(float(eigenvalues[-1]), 4)
        except Exception:
            pass

    return result


# ============================================================================
# SECTION 5: HYPERBOLIC COORDINATES
# ============================================================================


def compute_hyperbolic_coords(
    atom: dict, notes: list[str], spectral: dict,
) -> dict[str, float | str]:
    """Compute Poincare disk coordinates for a code atom.

    Radius = f(complexity, depth, tier)  ->  tanh mapping to (0, 1)
    Angle  = domain sector + atom-specific perturbation
    Risk   = harmonic wall H(d, R) = R^(d^2) from SCBE math
    """
    domain = atom.get("domain", "fundamentals")
    tier = atom.get("tier", "basic")
    ast_info = atom.get("ast", {})
    complexity = ast_info.get("complexity", 1)
    depth = ast_info.get("depth", 1)
    node_count = spectral.get("node_count", 1)

    # Composite complexity score [0, 1]
    score = (
        0.3 * min(depth / 10.0, 1.0)
        + 0.3 * min(complexity / 15.0, 1.0)
        + 0.2 * min(node_count / 30.0, 1.0)
        + 0.2 * TIER_DEPTH.get(tier, 0.5)
    )

    # Map to Poincare ball radius via tanh (ensures r < 1)
    radius = math.tanh(score * 2.0)

    # Angle: domain sector + hash-derived perturbation for uniqueness
    base_angle = DOMAIN_SECTORS.get(domain, 0.0)
    h = int(hashlib.md5(atom["id"].encode()).hexdigest()[:8], 16)
    perturbation = (h % 1000) / 1000.0 * (math.pi / 6)
    angle = base_angle + perturbation

    # Cartesian in Poincare disk
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)

    # Cluster label
    cluster = f"{domain}_{tier}"

    # Risk distance via harmonic wall: R^(r^2)
    r = max(radius, 0.01)
    risk_distance = r ** (r ** 2)

    return {
        "radius": round(radius, 4),
        "angle": round(angle, 4),
        "x": round(x, 4),
        "y": round(y, 4),
        "cluster": cluster,
        "risk_distance": round(risk_distance, 4),
    }


# ============================================================================
# SECTION 6: CONSENSUS SCORES
# ============================================================================


def compute_consensus(
    notes: list[str], threat_id: str, atom: dict,
) -> dict[str, float]:
    """Compute consensus scores for the canonical IR.

    structural_validity: is the code well-formed?
    threat_alignment:    does the code defend against the assigned threat?
    inverse_consistency: does the atom have a meaningful inverse?
    """
    note_set = set(notes)

    # Structural validity
    has_entry = bool(note_set & {"FUNC_DEF", "FUNC_DEF_ASYNC", "TYPE_DEF"})
    has_exit = bool(note_set & {"RETURN", "STREAM"})
    has_safety = bool(note_set & {"ERROR_TRAP", "GUARD", "RESOURCE_SCOPE"})
    has_data = bool(note_set & {"BIND", "BIND_TYPED", "BIND_MUTATE"})
    structural = 0.3 + 0.2 * has_entry + 0.2 * has_exit + 0.15 * has_safety + 0.15 * has_data

    # Threat alignment
    required = THREAT_DEFENSES.get(threat_id, set())
    if required:
        present = note_set & required
        threat_score = len(present) / len(required)
    else:
        threat_score = 0.5

    # Inverse consistency
    has_inverse = bool(atom.get("inverse", "").strip())
    has_inverse_desc = bool(atom.get("inverse_desc", "").strip())
    inverse_score = 0.4 + 0.3 * has_inverse + 0.3 * has_inverse_desc

    return {
        "structural_validity": round(structural, 2),
        "threat_alignment": round(threat_score, 2),
        "inverse_consistency": round(inverse_score, 2),
    }


# ============================================================================
# SECTION 7: FULL CANONICAL IR BUILDER
# ============================================================================


def canonicalize_atom(atom: dict) -> dict[str, Any]:
    """Build the complete canonical IR for one code atom."""
    python_code = atom.get("python", "")

    notes = extract_notes(python_code)
    histogram = compute_note_histogram(notes)
    balance = compute_category_balance(notes)
    graph = build_graph_ir(python_code)
    graph_summary = graph.summary()
    spectral = compute_spectral_features(graph)
    hyperbolic = compute_hyperbolic_coords(atom, notes, spectral)
    boundary = compute_boundary_operators(notes, atom, hyperbolic)

    return {
        "notes": notes,
        "note_count": len(notes),
        "histogram": histogram,
        "category_balance": balance,
        "graph": graph_summary,
        "spectral": spectral,
        "hyperbolic": hyperbolic,
        "boundary": boundary,
    }


# ============================================================================
# SECTION 8: L-1 VIEW BUILDER
# ============================================================================


def build_l_minus_1_view(
    canonical: dict, consensus: dict, atom: dict, lang: str,
) -> str:
    """Build the L-1 (canonical IR) view as structured readable text."""
    notes = canonical["notes"]
    balance = canonical["category_balance"]
    spectral = canonical["spectral"]
    hyp = canonical["hyperbolic"]
    graph = canonical["graph"]
    boundary = canonical.get("boundary", {})
    ast_info = atom.get("ast", {})

    # Language projection notes
    lang_notes = LANGUAGE_PROJECTIONS.get(lang, [])
    full_notes = notes + lang_notes

    # Note sequence (cap at 24 for readability)
    note_str = " -> ".join(full_notes[:24])
    if len(full_notes) > 24:
        note_str += f" ... (+{len(full_notes) - 24})"

    # Category balance
    bal_parts = [f"{c}={int(p * 100)}%" for c, p in balance.items() if p > 0]
    bal_str = ", ".join(bal_parts) if bal_parts else "empty"

    # Graph edge breakdown
    edge_parts = [f"{cnt} {etype}" for etype, cnt in graph.get("edge_types", {}).items()]
    edge_str = ", ".join(edge_parts) if edge_parts else "none"

    lines = [
        f"[L-1:CANONICAL_IR] {atom['name']} ({lang})",
        f"  Code_Notes: {note_str}",
        f"  Note_Balance: {bal_str}",
        f"  Graph: {spectral['node_count']} nodes, {spectral['edge_count']} edges ({edge_str})",
        f"  Spectral: depth={ast_info.get('depth', '?')}, branching={spectral['branch_factor']}, "
        f"density={spectral['density']}, cycles={spectral['cycle_count']}",
        f"  Hyperbolic: r={hyp['radius']}, theta={hyp['angle']}, "
        f"cluster={hyp['cluster']}, risk_d={hyp['risk_distance']}",
        f"  Consensus: structural={consensus['structural_validity']}, "
        f"threat={consensus['threat_alignment']}, inverse={consensus['inverse_consistency']}",
    ]

    # Spectral extras if numpy was available
    if "algebraic_connectivity" in spectral:
        lines.append(
            f"  Spectral_Ext: lambda2={spectral['algebraic_connectivity']}, "
            f"radius={spectral.get('spectral_radius', 0)}, "
            f"rank={spectral.get('laplacian_rank', 0)}"
        )

    # Boundary-lift operators (complement residual / cross-domain incursion)
    if boundary:
        lines.append(
            f"  Boundary: RETAIN={boundary['retain_count']}, "
            f"DEFER={boundary['defer_count']}, LIFT={boundary['lift_count']} "
            f"| boundary_score={boundary['boundary_score']}"
        )
        comp_res = boundary.get("complement_residual", [])
        if comp_res:
            lines.append(
                f"  Complement_Residual: [{', '.join(comp_res)}] "
                f"(density={boundary['complement_density']})"
            )
        lift_targets = boundary.get("lift_targets", [])
        if lift_targets:
            # Show up to 4 lift targets for readability
            lift_strs = [
                f"{lt['note']}:{lt['from_domain']}->{lt['to_domain']}@{lt['fractional_angle']}"
                for lt in lift_targets[:4]
            ]
            extra = f" +{len(lift_targets) - 4}" if len(lift_targets) > 4 else ""
            lines.append(f"  Lift_Targets: {'; '.join(lift_strs)}{extra}")

    return "\n".join(lines)


# ============================================================================
# SECTION 9: DATASET GENERATOR
# ============================================================================


def generate_canonical_dataset(
    target_count: int = 10000,
    seed: int = 42,
) -> tuple[list[dict], dict]:
    """Generate the C-condition dataset: canonical IR + L0-L3 views."""
    rng = random.Random(seed)

    # Pre-compute canonical IR for each atom (language-independent core)
    print("Canonicalizing atoms...")
    canonical_cache: dict[str, dict] = {}
    for atom in ATOMS:
        canonical_cache[atom["id"]] = canonicalize_atom(atom)
    print(f"  {len(canonical_cache)} atoms canonicalized")

    # Build combinatorial space (mirrors round5 generator)
    threat_ids = list(THREATS.keys())
    combos: list[tuple] = []
    for atom in ATOMS:
        own_threat = atom["sniper"]
        for lang in LANGUAGES:
            if lang not in atom:
                continue
            for modifier in COMPLEXITY_MODIFIERS:
                # Primary threat
                combos.append((atom, lang, modifier, own_threat))
                # Cross-pollinate with all other threats
                for tid in threat_ids:
                    if tid != own_threat:
                        combos.append((atom, lang, modifier, tid))

    print(f"  Combo space: {len(combos)}")

    if len(combos) > target_count:
        combos = rng.sample(combos, target_count)
    rng.shuffle(combos)

    # Generate records
    records: list[dict] = []
    tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]

    for i, (atom, lang, modifier, threat_id) in enumerate(combos):
        canonical = canonical_cache[atom["id"]]
        threat = THREATS[threat_id]
        consensus = compute_consensus(canonical["notes"], threat_id, atom)

        # Build all views
        l_minus_1 = build_l_minus_1_view(canonical, consensus, atom, lang)
        l0 = build_l0_view(atom, lang, modifier)
        l1 = build_l1_view(atom, modifier)
        l2 = build_l2_view(atom, threat, modifier)
        l3 = build_l3_view(atom, lang)

        # Instruction (same as A/B conditions for fair comparison)
        instruction = generate_instruction(atom, lang, modifier, threat)

        # Tongue tag
        primary = tongues[i % len(tongues)]
        null_sample = rng.sample([t for t in tongues if t != primary], 3)
        tongue_tag = (
            f"[Tongue:{primary}|Null:{','.join(null_sample)}"
            f"|Layer:L-1-L3|Gov:ALLOW]"
        )

        # Assemble: canonical IR prepended to full multiview
        response = f"{l_minus_1}\n\n{l0}\n\n{l1}\n\n{l2}\n\n{l3}\n\n{tongue_tag}"

        text = (
            f"<|im_start|>user\n{instruction}<|im_end|>\n"
            f"<|im_start|>assistant\n{response}<|im_end|>"
        )
        records.append({"text": text})

        if (i + 1) % 2000 == 0:
            print(f"  Generated {i + 1}/{len(combos)} records...")

    stats = _compute_stats(records, canonical_cache)
    return records, stats


def _compute_stats(
    records: list[dict], canonical_cache: dict[str, dict],
) -> dict[str, Any]:
    """Compute dataset-level statistics."""
    texts = [r["text"] for r in records]
    unique_texts = len(set(texts))

    # Note distribution across all atoms
    all_notes: list[str] = []
    for cir in canonical_cache.values():
        all_notes.extend(cir["notes"])
    note_dist = dict(Counter(all_notes).most_common())

    # Averaged category balance
    avg_bal: dict[str, float] = defaultdict(float)
    for cir in canonical_cache.values():
        for cat, val in cir["category_balance"].items():
            avg_bal[cat] += val
    n = len(canonical_cache)
    avg_bal = {k: round(v / n, 3) for k, v in avg_bal.items()}

    # Hyperbolic spread
    radii = [cir["hyperbolic"]["radius"] for cir in canonical_cache.values()]
    node_counts = [cir["spectral"]["node_count"] for cir in canonical_cache.values()]

    return {
        "total_records": len(records),
        "unique_records": unique_texts,
        "uniqueness_pct": round(unique_texts / max(len(records), 1) * 100, 1),
        "atoms_canonicalized": n,
        "note_vocabulary_size": len(set(all_notes)),
        "note_distribution": note_dist,
        "avg_category_balance": avg_bal,
        "avg_hyperbolic_radius": round(sum(radii) / len(radii), 4) if radii else 0,
        "avg_graph_nodes": round(sum(node_counts) / len(node_counts), 1) if node_counts else 0,
    }


# ============================================================================
# SECTION 10: MAIN
# ============================================================================


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Canonical Code Preprocessor (Stage -1) for SCBE Training"
    )
    parser.add_argument("--count", type=int, default=10000, help="Target record count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print("=" * 72)
    print("CANONICAL CODE PREPROCESSOR -- Stage -1")
    print("Building the 'music theory' layer for code")
    print("=" * 72)

    start = time.time()

    records, stats = generate_canonical_dataset(args.count, args.seed)

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "round6_canonical_ir_l3.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    elapsed = time.time() - start

    # Report
    print()
    print("=" * 72)
    print("GENERATION COMPLETE")
    print("=" * 72)
    print(f"Records:              {stats['total_records']}")
    print(f"Unique:               {stats['unique_records']} ({stats['uniqueness_pct']}%)")
    print(f"Atoms canonicalized:  {stats['atoms_canonicalized']}")
    print(f"Note vocabulary:      {stats['note_vocabulary_size']} primitives")
    print(f"Avg graph nodes:      {stats['avg_graph_nodes']}")
    print(f"Avg hyperbolic r:     {stats['avg_hyperbolic_radius']}")
    print()
    print("Note distribution:")
    for note, count in list(stats["note_distribution"].items())[:12]:
        print(f"  {note:20s} {count}")
    print()
    print("Category balance (averaged across atoms):")
    for cat, val in stats["avg_category_balance"].items():
        print(f"  {cat:15s} {int(val * 100)}%")
    print()
    print(f"Output: {output_path}")
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"Size:   {size_mb:.1f} MB")
    print(f"Time:   {elapsed:.1f}s")
    print()
    print("A/B/C test files:")
    print(f"  A (baseline):   training-data/sft/round5_code_baseline_l3.jsonl")
    print(f"  B (multiview):  training-data/sft/round5_code_multiview_l0l3.jsonl")
    print(f"  C (canonical):  training-data/sft/{output_path.name}")
    print("=" * 72)


if __name__ == "__main__":
    main()
