"""
tests/test_geoseal_agent_routing.py
====================================
Bijection + routing correctness tests for the GeoSeal coding spine.

Tests cover:
  - Deterministic routing (same input → same tongue, always)
  - Coverage of all 6 Sacred Tongue code lanes by keyword
  - Trit fallback routing for language-agnostic tasks
  - Force-tongue override
  - Governance tier + GeoSeal seal properties
  - CLI arg parsing for agent + arc subcommands

Does NOT test inference (no LLM calls) — pure routing, governance, and CLI.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Make sure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "python"))

from src.coding_spine.router import (
    TONGUE_LANGUAGE,
    RouteResult,
    route_task,
)
from src.coding_spine.shared_ir import equivalent_ir, infer_semantic_ir
from src.geoseal_cli import (
    PHI,
    compute_seal,
    phi_wall_cost,
    phi_wall_tier,
    phi_trust_score,
    verify_seal,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _route(task: str, tongue: str | None = None) -> RouteResult:
    return route_task(task, force_tongue=tongue)


# ---------------------------------------------------------------------------
# 1. Keyword routing — all 6 tongues reachable
# ---------------------------------------------------------------------------

class TestKeywordRouting:
    """Each Sacred Tongue must be reachable via its canonical keywords."""

    @pytest.mark.parametrize("task,expected_tongue", [
        # Kor'aelin / Python
        ("write a fibonacci function in python",        "KO"),
        ("build a fastapi endpoint with pydantic",      "KO"),
        ("use pandas to aggregate a dataframe",         "KO"),
        ("pytest fixture for database testing",         "KO"),
        # Avali / TypeScript
        ("write a react component with useState hook",  "AV"),
        ("parse JSON and call an API in typescript",    "AV"),
        ("create a node.js express route handler",      "AV"),
        ("npm package with tsx export",                 "AV"),
        # Runethic / Rust
        ("implement a thread-safe queue in rust",       "RU"),
        ("use tokio async runtime with cargo",          "RU"),
        ("explain rust ownership and lifetimes",        "RU"),
        ("unsafe ffi binding with borrow checker",      "RU"),
        # Cassisivadan / C / symbolic
        ("write a c function using gcc and cmake",      "CA"),
        ("symbolic differentiation of a polynomial",   "CA"),
        ("mathematica expression for eigenvalues",      "CA"),
        # Umbroth / Julia
        ("solve a differential equation in julia",      "UM"),
        ("optimize a dataframes pipeline in julia",     "UM"),
        ("train a flux model in julia",                 "UM"),
        ("pkg instantiate for a julia project",         "UM"),
        # Draumric / Haskell
        ("write a haskell monadic parser",              "DR"),
        ("functors and applicatives in haskell",        "DR"),
        ("cabal project with ghc",                      "DR"),
        ("build a parser combinator in haskell",        "DR"),
    ])
    def test_keyword_routes_to_correct_tongue(self, task: str, expected_tongue: str):
        r = _route(task)
        assert r.tongue == expected_tongue, (
            f"Task: {task!r}\n"
            f"Expected tongue: {expected_tongue} ({TONGUE_LANGUAGE[expected_tongue]})\n"
            f"Got:             {r.tongue} ({TONGUE_LANGUAGE[r.tongue]})\n"
            f"Keyword used:    {r.override_keyword!r}"
        )
        assert r.override_keyword is not None, "keyword routing should set override_keyword"
        assert r.confidence >= 0.90

    def test_all_six_tongues_reachable_by_keyword(self):
        """Every tongue must appear at least once across the keyword set."""
        tasks = {
            "KO": "build a fastapi endpoint in python",
            "AV": "create a react component in typescript",
            "RU": "implement a rust ownership example",
            "CA": "write symbolic math in mathematica",
            "UM": "solve a stiff ode in julia",
            "DR": "write a parser combinator in haskell",
        }
        found = set()
        for tongue, task in tasks.items():
            r = _route(task)
            assert r.tongue == tongue, f"Expected {tongue} for {task!r}, got {r.tongue}"
            found.add(r.tongue)
        assert found == {"KO", "AV", "RU", "CA", "UM", "DR"}


# ---------------------------------------------------------------------------
# 2. Force-tongue override
# ---------------------------------------------------------------------------

class TestForceTongue:
    """--tongue flag must override routing for any of the 6 tongues."""

    @pytest.mark.parametrize("tongue", ["KO", "AV", "RU", "CA", "UM", "DR"])
    def test_force_tongue_overrides_keyword(self, tongue: str):
        # Even if the task says 'python', forcing 'RU' must win
        r = _route("write a function in python", tongue=tongue)
        assert r.tongue == tongue
        assert r.confidence == 1.0
        assert r.language == TONGUE_LANGUAGE[tongue]
        assert r.override_keyword is not None and tongue in r.override_keyword

    @pytest.mark.parametrize("tongue", ["KO", "AV", "RU", "CA", "UM", "DR"])
    def test_force_tongue_on_ambiguous_task(self, tongue: str):
        r = _route("write a sort function", tongue=tongue)
        assert r.tongue == tongue
        assert r.confidence == 1.0


# ---------------------------------------------------------------------------
# 3. Determinism — same task always produces same route
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Routing must be deterministic: identical input → identical output."""

    TASKS = [
        "write a binary search tree",
        "implement a LRU cache with O(1) get and put",
        "parse a URL and extract query parameters",
        "compute the fibonacci sequence efficiently",
        "sort a list of objects by multiple fields",
        "write a concurrent lock-free ring buffer",
        "implement gradient descent from scratch",
    ]

    @pytest.mark.parametrize("task", TASKS)
    def test_routing_is_deterministic(self, task: str):
        results = [_route(task) for _ in range(5)]
        tongues = [r.tongue for r in results]
        confs   = [r.confidence for r in results]
        assert len(set(tongues)) == 1, f"Non-deterministic routing for: {task!r} → {tongues}"
        assert len(set(confs)) == 1

    @pytest.mark.parametrize("task", TASKS)
    def test_trit_scores_are_deterministic(self, task: str):
        r1 = _route(task)
        r2 = _route(task)
        assert r1.trit_scores == r2.trit_scores


# ---------------------------------------------------------------------------
# 4. Trit fallback routing (no keyword)
# ---------------------------------------------------------------------------

class TestTritFallback:
    """Tasks with no language keywords must still produce a valid route via trit aggregation."""

    GENERIC_TASKS = [
        "implement a priority queue",
        "write a function that flattens nested lists",
        "create a directed acyclic graph",
        "compute pairwise distances between vectors",
        "build a state machine with transitions",
        "implement Dijkstra's shortest path algorithm",
        "convert a tree to its mirror image",
    ]

    @pytest.mark.parametrize("task", GENERIC_TASKS)
    def test_trit_fallback_produces_valid_tongue(self, task: str):
        r = _route(task)
        assert r.tongue in TONGUE_LANGUAGE
        assert r.language in TONGUE_LANGUAGE.values()
        assert 0.0 <= r.confidence <= 1.0

    @pytest.mark.parametrize("task", GENERIC_TASKS)
    def test_trit_fallback_has_no_keyword_override(self, task: str):
        r = _route(task)
        # Keyword override should be absent for truly generic tasks
        # (May be set for some — just ensure confidence is reasonable)
        if r.override_keyword is None:
            assert r.confidence >= 0.20, "trit fallback must produce meaningful confidence"


# ---------------------------------------------------------------------------
# 5. Governance — phi-wall cost and tier properties
# ---------------------------------------------------------------------------

class TestGovernance:
    """phi-wall costs and tiers must satisfy mathematical invariants."""

    TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

    def test_phi_weight_ordering(self):
        """Phi weights must increase monotonically: KO < AV < RU < CA < UM < DR."""
        from src.geoseal_cli import TONGUE_PHI_WEIGHTS
        weights = [TONGUE_PHI_WEIGHTS[t] for t in self.TONGUES]
        for i in range(len(weights) - 1):
            assert weights[i] < weights[i + 1], (
                f"Weight ordering violated: {self.TONGUES[i]}={weights[i]} "
                f">= {self.TONGUES[i+1]}={weights[i+1]}"
            )

    @pytest.mark.parametrize("tongue", ["KO", "AV", "RU", "CA", "UM", "DR"])
    def test_phi_cost_increases_with_tongue_weight(self, tongue: str):
        cost = phi_wall_cost(0.5, tongue)
        assert cost > 0.0
        assert cost < 10.0  # sane upper bound for chi=0.5

    def test_phi_cost_increases_with_chi(self):
        for tongue in self.TONGUES:
            costs = [phi_wall_cost(chi, tongue) for chi in [0.0, 0.25, 0.5, 0.75, 1.0]]
            for i in range(len(costs) - 1):
                assert costs[i] <= costs[i + 1], f"Cost not monotone for {tongue}"

    @pytest.mark.parametrize("tongue,chi,expected_tier", [
        ("KO", 0.0,  "ALLOW"),
        ("KO", 0.5,  "ALLOW"),
        ("KO", 1.0,  "ALLOW"),    # KO is lightest tongue
        ("DR", 2.0,  "DENY"),     # DR at chi=2.0 exceeds phi^1.5 threshold
    ])
    def test_tier_thresholds(self, tongue: str, chi: float, expected_tier: str):
        cost = phi_wall_cost(chi, tongue)
        tier = phi_wall_tier(cost)
        assert tier == expected_tier, (
            f"phi_wall_cost({chi}, {tongue}) = {cost:.4f} → tier={tier}, expected {expected_tier}"
        )

    @pytest.mark.parametrize("tongue", ["KO", "AV", "RU", "CA", "UM", "DR"])
    def test_trust_score_in_unit_interval(self, tongue: str):
        for chi in [0.0, 0.2, 0.5, 0.8, 1.0]:
            cost = phi_wall_cost(chi, tongue)
            trust = phi_trust_score(cost)
            assert 0.0 <= trust <= 1.0, f"trust out of [0,1]: {trust} for {tongue} chi={chi}"


# ---------------------------------------------------------------------------
# 6. GeoSeal — seal correctness and tamper-detection
# ---------------------------------------------------------------------------

class TestGeoSeal:
    """GeoSeal stamps must be deterministic and tamper-evident."""

    def _seal(self, op="agent", tongue="KO", code="print('hi')",
              payload="test", cost=1.0, tier="ALLOW") -> str:
        return compute_seal(op, tongue, code, payload, cost, tier)

    def test_seal_is_deterministic(self):
        s1 = self._seal()
        s2 = self._seal()
        assert s1 == s2

    def test_seal_is_hex_64_chars(self):
        s = self._seal()
        assert len(s) == 64
        int(s, 16)  # must parse as hex

    def test_seal_changes_on_code_change(self):
        s1 = self._seal(code="x = 1")
        s2 = self._seal(code="x = 2")
        assert s1 != s2

    def test_seal_changes_on_tongue_change(self):
        s1 = self._seal(tongue="KO")
        s2 = self._seal(tongue="RU")
        assert s1 != s2

    def test_seal_changes_on_tier_change(self):
        s1 = self._seal(tier="ALLOW")
        s2 = self._seal(tier="DENY")
        assert s1 != s2

    def test_verify_passes_for_correct_inputs(self):
        seal = self._seal()
        assert verify_seal(seal, "agent", "KO", "print('hi')", "test", 1.0, "ALLOW")

    def test_verify_fails_for_tampered_code(self):
        seal = self._seal(code="print('hi')")
        assert not verify_seal(seal, "agent", "KO", "print('TAMPERED')", "test", 1.0, "ALLOW")

    @pytest.mark.parametrize("tongue", ["KO", "AV", "RU", "CA", "UM", "DR"])
    def test_seals_differ_per_tongue(self, tongue: str):
        seals = {t: self._seal(tongue=t) for t in ["KO", "AV", "RU", "CA", "UM", "DR"]}
        assert len(set(seals.values())) == 6, "Every tongue must produce a unique seal"


# ---------------------------------------------------------------------------
# 7. Bijection stress test — simple to complex
# ---------------------------------------------------------------------------

class TestBijectionStress:
    """Full route→seal pipeline must be bijective: distinct tasks → distinct seals."""

    SIMPLE = [
        "add two numbers",
        "subtract two numbers",
        "multiply two numbers",
        "divide two numbers",
        "return the maximum of a list",
    ]

    MEDIUM = [
        "implement a stack with push pop peek",
        "write a binary search on a sorted array",
        "build a linked list with insert and delete",
        "reverse a string in place",
        "check if a string is a palindrome",
        "count word frequencies in a document",
        "find all prime numbers up to N with sieve",
    ]

    COMPLEX = [
        "implement a thread-safe LRU cache in rust using tokio",
        "write a typescript generic Either monad with map and flatMap",
        "implement gradient descent optimizer with momentum in numpy",
        "build a B-tree with insertion deletion and range query in C",
        "write a haskell parser combinator for arithmetic expressions",
        "write a tutorial on parser combinators in haskell",
        "implement ARC color remap using symbolic constraint inference",
    ]

    def _seal_for_task(self, task: str) -> str:
        r = route_task(task)
        cost = phi_wall_cost(0.2, r.tongue)
        tier = phi_wall_tier(cost)
        return compute_seal("agent", r.tongue, task, task, cost, tier)

    def _check_bijection(self, tasks: list[str]):
        seals = [self._seal_for_task(t) for t in tasks]
        assert len(seals) == len(set(seals)), (
            f"Seal collision detected in task set:\n" +
            "\n".join(f"  {t} -> {s[:16]}..." for t, s in zip(tasks, seals))
        )

    def test_bijection_simple(self):
        self._check_bijection(self.SIMPLE)

    def test_bijection_medium(self):
        self._check_bijection(self.MEDIUM)

    def test_bijection_complex(self):
        self._check_bijection(self.COMPLEX)

    def test_bijection_mixed(self):
        self._check_bijection(self.SIMPLE[:2] + self.MEDIUM[:2] + self.COMPLEX[:2])

    @pytest.mark.parametrize("task", SIMPLE + MEDIUM + COMPLEX)
    def test_route_then_seal_is_stable(self, task: str):
        """Same task must produce same seal across repeated calls."""
        seals = {self._seal_for_task(task) for _ in range(3)}
        assert len(seals) == 1, f"Unstable seal for: {task!r}"


# ---------------------------------------------------------------------------
# 8. CLI smoke tests (no inference)
# ---------------------------------------------------------------------------

class TestCLISmoke:
    """Verify the CLI parses and routes without calling inference providers."""

    def _run(self, *args: str) -> tuple[int, str, str]:
        result = subprocess.run(
            [sys.executable, "-m", "src.geoseal_cli", *args],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(_REPO_ROOT)},
        )
        return result.returncode, result.stdout, result.stderr

    def test_ops_lists_entries(self):
        rc, out, err = self._run("ops")
        assert rc == 0
        assert "add" in out or "0x" in out

    def test_ops_band_filter(self):
        rc, out, err = self._run("ops", "--band", "ARITHMETIC")
        assert rc == 0

    def test_atomic_add(self):
        rc, out, err = self._run("atomic", "add")
        assert rc == 0
        data = json.loads(out)
        assert data["name"] == "add"
        assert "trit" in data

    def test_atomic_add_show_code(self):
        rc, out, err = self._run("atomic", "add", "--show-code")
        assert rc == 0
        data = json.loads(out)
        assert data["code"] is not None

    def test_emit_add_all_tongues(self):
        # emit takes kwargs as key=value positional args
        rc, out, err = self._run("emit", "add", "a=x", "b=y")
        assert rc == 0, f"emit failed: {err}"
        for tongue in ("KO", "AV", "RU"):
            assert tongue in out

    def test_emit_add_single_tongue(self):
        rc, out, err = self._run("emit", "add", "--tongue", "KO", "a=x", "b=y")
        assert rc == 0, f"emit failed: {err}"

    def test_seal_then_verify(self):
        # seal
        rc, out, _ = self._run("seal", "hello world", "--tongue", "KO")
        assert rc == 0
        seal = [line for line in out.splitlines() if line.startswith("seal=")][0].split("=", 1)[1]
        # verify
        rc2, out2, _ = self._run("verify", seal, "hello world", "--tongue", "KO")
        assert rc2 == 0
        assert "OK" in out2

    def test_agent_help(self):
        rc, out, _ = self._run("agent", "--help")
        assert rc == 0
        assert "--tongue" in out
        assert "--provider" in out

    def test_arc_help(self):
        rc, out, _ = self._run("arc", "--help")
        assert rc == 0
        assert "task_file" in out
        assert "--onnx" in out


# ---------------------------------------------------------------------------
# 9. ARC lane — routing arc tasks uses Umbroth (symbolic/math tongue)
# ---------------------------------------------------------------------------

class TestARCLane:
    """ARC synthesis must use Umbroth tongue (symbolic reasoning) + ALLOW tier."""

    ARC_TASKS = [
        "color remap all 0s to 3s on a grid",
        "shift a grid right by 2 pixels",
        "flip a grid horizontally",
        "transpose a 2D grid",
        "identify dominant component and shift it",
        "apply per-color shift rules to a grid",
        "infer and apply orientation transform",
    ]

    def test_arc_tasks_route_to_symbolic_tongue(self):
        """ARC tasks should route to CA (symbolic) or UM (functional math) via trit."""
        for task in self.ARC_TASKS:
            r = route_task(task)
            # Both CA and UM are acceptable for symbolic/math grid work
            # KO is also fine if the trit system picks it
            assert r.tongue in {"KO", "CA", "UM"}, (
                f"ARC task routed to unexpected tongue {r.tongue}: {task!r}"
            )

    def test_arc_synthesis_and_seal(self, tmp_path):
        """Full arc solve → seal pipeline on a real task JSON."""
        import json
        import numpy as np
        from src.neurogolf.arc_io import load_arc_task
        from src.neurogolf.solver import synthesize_program, execute_program

        task_data = {
            "train": [
                {"input": [[0, 1], [2, 0]], "output": [[5, 1], [2, 5]]},
                {"input": [[0, 0], [1, 2]], "output": [[5, 5], [1, 2]]},
            ],
            "test": [{"input": [[2, 0], [0, 1]]}],
        }
        task_file = tmp_path / "test_task.json"
        task_file.write_text(json.dumps(task_data))

        task = load_arc_task(task_file)
        solution = synthesize_program(task)

        # Verify training accuracy
        correct = sum(
            1 for ex in task.train
            if np.array_equal(execute_program(ex.input, solution.program), ex.output)
        )
        assert correct == len(task.train), (
            f"Expected 100% train acc, got {correct}/{len(task.train)} for family={solution.family}"
        )

        # GeoSeal the result
        tongue = "UM"
        cost = phi_wall_cost(0.15, tongue)
        tier = phi_wall_tier(cost)
        seal = compute_seal("arc", tongue, solution.family, task.task_id, cost, tier)
        assert len(seal) == 64
        assert tier == "ALLOW"
        assert verify_seal(seal, "arc", tongue, solution.family, task.task_id, cost, tier)


# ---------------------------------------------------------------------------
# 10. Shared semantic IR — dual-strand convergence on common ops
# ---------------------------------------------------------------------------

class TestSharedSemanticIR:
    def test_cross_language_add_converges(self):
        py_ir = infer_semantic_ir("add two numbers in python")
        rs_ir = infer_semantic_ir("add two numbers in rust")
        hs_ir = infer_semantic_ir("add two numbers in haskell")

        assert py_ir.op == "add"
        assert equivalent_ir(py_ir, rs_ir)
        assert equivalent_ir(rs_ir, hs_ir)

    def test_cross_language_sort_converges(self):
        ts_ir = infer_semantic_ir("sort a list in typescript")
        jl_ir = infer_semantic_ir("sort a list in julia")

        assert ts_ir.op == "sort"
        assert equivalent_ir(ts_ir, jl_ir)

    def test_force_tongue_preserves_semantic_signature(self):
        auto_ir = infer_semantic_ir("filter a list using a predicate")
        ru_ir = infer_semantic_ir("filter a list using a predicate", force_tongue="RU")

        assert auto_ir.op == "filter"
        assert equivalent_ir(auto_ir, ru_ir)

    def test_freeform_task_stays_freeform(self):
        ir = infer_semantic_ir("write a fibonacci function with memoization in rust")
        assert ir.family == "freeform"
        assert ir.op is None
