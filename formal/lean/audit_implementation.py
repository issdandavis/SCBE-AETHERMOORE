"""Bounded source-correspondence checks; these are not universal Lean proofs.

Load exact files under --repo, record hashes, and fail if a named contract fails.
No training imports, writes to runtime state, or network calls.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

SOURCES = {
    "codec": "src/crypto/sacred_tongues.py",
    "cfi": "src/symphonic_cipher/topological_cfi.py",
    "layers": "src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py",
    "full": "src/symphonic_cipher/scbe_aethermoore/full_system.py",
}


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


def audit(repo):
    import numpy as np

    checks = []

    def check(name, operation):
        try:
            count = operation()
            checks.append({"contract": name, "status": "PASS", "cases": count})
        except Exception as exc:
            checks.append({"contract": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

    def require(condition, detail):
        if not condition:
            raise AssertionError(detail)

    def codecs():
        mod = load_file("_scbe_audit_codec", repo / SOURCES["codec"])
        codec = mod.SacredTongueTokenizer()
        raw = bytes(range(256))
        codes = list(mod.TONGUES)
        require(len(codes) == 6, "Expected six tables")
        for tongue in codes:
            tokens = codec.encode_bytes(tongue, raw)
            require(len(tokens) == len(set(tokens)) == 256, "Non-bijective vocabulary")
            require(codec.decode_tokens(tongue, tokens) == raw, "Byte round-trip failed")
            require(codec.decode_tokens(tongue, []) == b"", "Empty sequence failed")
        for a, b in itertools.product(codes, repeat=2):
            first = codec.encode_bytes(a, raw)
            second = codec.encode_bytes(b, codec.decode_tokens(a, first))
            back = codec.encode_bytes(a, codec.decode_tokens(b, second))
            require(back == first, f"Translation failed: {a}, {b}")
        return 6 * 256 + 36 * 256 + 6

    def layers():
        return load_file("_scbe_audit_layers", repo / SOURCES["layers"])

    def score():
        mod = layers()
        count = 0
        for d, p in itertools.product([0, 0.125, 0.5, 1, 3, 100, 10000], [0, 0.125, 0.5, 1, 100]):
            value = mod.layer_12_harmonic_scaling(d, p)
            oracle = float(1 / (1 + Fraction(d) + 2 * Fraction(p)))
            require(math.isclose(value, oracle, rel_tol=1e-13), f"Score mismatch: {d}, {p}")
            require(0 < value <= 1, f"Score outside range: {d}, {p}")
            count += 1
        return count

    def invalid_score():
        mod = layers()
        for d, p in [(math.nan, 0), (math.inf, 0), (-1, 0), (0, -1), (0, math.nan)]:
            try:
                value = mod.layer_12_harmonic_scaling(d, p)
            except ValueError:
                continue
            raise AssertionError(f"Invalid domain accepted: d={d}, p={p}, result={value}")
        return 5

    def geometry():
        mod = layers()
        rng = np.random.default_rng(20260918)
        for _ in range(64):
            # Well inside the ball: no clamping should be active.
            u, v = rng.uniform(-0.1, 0.1, (2, 6))
            arg = 1 + 2 * float(np.dot(u - v, u - v)) / ((1 - float(np.dot(u, u))) * (1 - float(np.dot(v, v))))
            got = mod.layer_5_hyperbolic_distance(u, v)
            require(math.isclose(got, math.acosh(arg), rel_tol=1e-12), "Poincare mismatch")
            require(math.isclose(got, mod.layer_5_hyperbolic_distance(v, u)), "Asymmetry")
            require(mod.layer_5_hyperbolic_distance(u, u) == 0, "Nonzero self-distance")
        return 64 * 3

    def cfi():
        mod = load_file("_scbe_audit_cfi", repo / SOURCES["cfi"])
        count = 0
        pairs = [(a, b) for a in range(3) for b in range(3) if a != b]
        for bits in range(1 << len(pairs)):
            edges = {pair for i, pair in enumerate(pairs) if bits & (1 << i)}
            cfg = mod.ControlFlowGraph()
            for i in range(3):
                cfg.add_vertex(mod.BasicBlock(i, ["nop"], i, i + 1))
            for a, b in edges:
                cfg.add_edge(mod.CFGEdge(a, b, "jump"))
            gate = mod.TopologicalCFI()
            gate.initialize(cfg)
            for a, b in itertools.product(range(-1, 4), repeat=2):
                actual = gate.check_transition(a, b) == mod.CFIResult.VALID
                require(actual == ((a, b) in edges), f"Wrong edge result: graph={bits}, edge={a,b}")
                count += 1
        # Changing the source graph after initialization must not change its policy.
        cfg = mod.ControlFlowGraph()
        for i in range(3):
            cfg.add_vertex(mod.BasicBlock(i, ["nop"], i, i + 1))
        cfg.add_edge(mod.CFGEdge(0, 1, "jump"))
        cfg.add_edge(mod.CFGEdge(1, 2, "jump"))
        gate = mod.TopologicalCFI()
        gate.initialize(cfg)
        cfg.add_edge(mod.CFGEdge(2, 0, "jump"))
        require(gate.check_transition(2, 0) != mod.CFIResult.VALID, "Mutable policy")
        require(gate.check_transition(True, 2) != mod.CFIResult.VALID, "Boolean accepted as ID")
        require(not gate.verify_execution_path(["0", "2"])["valid"], "Illegal unique path accepted")
        require(gate.verify_execution_path(["0", "1", "2"])["valid"], "Legal path rejected")
        return count + 4

    def breathing_contract():
        mod = layers()
        point = np.array([0.25, 0.0])
        distance = mod.layer_5_hyperbolic_distance(np.zeros(2), point)
        for t in (0.0, 15.0, 30.0, 45.0, 60.0):
            factor = mod.breathing_factor(t)
            require(0.4 - 1e-12 <= factor <= 2.5 + 1e-12, "Breathing factor outside positive bounds")
            moved = mod.layer_6_breathing(point, t)
            require(np.allclose(mod.layer_6_inverse(moved, t), point), "Breathing inverse failed")
            after = mod.layer_5_hyperbolic_distance(np.zeros(2), moved)
            require(math.isclose(after, factor * distance, rel_tol=1e-10), "Radial distance law failed")
        return 15

    def composition():
        directory = (repo / SOURCES["full"]).parent
        alias = "_scbe_audit_full_package"
        package = ModuleType(alias)
        package.__path__ = [str(directory)]
        sys.modules[alias] = package
        full = importlib.import_module(alias + ".full_system")
        require(Path(full.__file__).resolve() == (repo / SOURCES["full"]).resolve(), "Wrong import")
        rank = {"ALLOW": 0, "REVIEW": 1, "QUARANTINE": 1, "DENY": 2, "SNAP": 3}
        levels = {"ALLOW": "LOW", "REVIEW": "MEDIUM", "DENY": "HIGH", "SNAP": "CRITICAL"}
        count = 0
        for cold, mode, d in itertools.product([False, True], list(full.GovernanceMode), levels):
            risk_value = {"ALLOW": 0.0, "REVIEW": 0.5, "DENY": 0.8, "SNAP": 0.999}[d]
            # Explicit boundary fixture isolates the aggregator from the L13 producer.
            risk = full.RiskAssessment(risk_value, risk_value, full.RiskLevel[levels[d]], 0, 1.0, d)
            system = full.SCBEFullSystem(mode=mode)
            decision, _, _ = system._compute_final_decision(
                risk_assessment=risk,
                entropy_zone="OPTIMAL",
                entropy_rate=1.0,
                manifold_divergence=0.0,
                topology_valid=True,
                tau_flow=1.0,
                q_fidelity=1.0,
                is_cold_start=cold,
            )
            require(
                rank[decision.value] >= rank[d], f"Refusal weakened: {mode.name}, cold={cold}, {d}->{decision.value}"
            )
            count += 1
        return count

    for name, op in [
        ("six_codec_tables", codecs),
        ("L12_exact_formula_samples", score),
        ("L12_invalid_domain_rejection", invalid_score),
        ("L5_interior_geometry_samples", geometry),
        ("frozen_directed_CFI", cfi),
        ("full_system_refusal_precedence", composition),
        ("L6_positive_deformation_contract", breathing_contract),
    ]:
        check(name, op)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.output.exists():
        parser.error("Refusing to overwrite an evidence receipt")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    result = {
        "schema": "scbe-lean-correspondence/v1",
        "repository": str(repo),
        "head": head.stdout.strip(),
        "scope": "Finite implementation checks, not whole-program verification or security assurance",
        "sources": {
            name: {"path": rel, "sha256": hashlib.sha256((repo / rel).read_bytes()).hexdigest()}
            for name, rel in SOURCES.items()
        },
        "checks": audit(repo),
    }
    result["passed"] = all(row["status"] == "PASS" for row in result["checks"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"head": result["head"], "passed": result["passed"], "checks": result["checks"]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
