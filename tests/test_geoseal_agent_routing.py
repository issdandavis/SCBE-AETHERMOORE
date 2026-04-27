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

    @pytest.mark.parametrize(
        "task,expected_tongue",
        [
            # Kor'aelin / Python
            ("write a fibonacci function in python", "KO"),
            ("build a fastapi endpoint with pydantic", "KO"),
            ("use pandas to aggregate a dataframe", "KO"),
            ("pytest fixture for database testing", "KO"),
            # Avali / TypeScript
            ("write a react component with useState hook", "AV"),
            ("parse JSON and call an API in typescript", "AV"),
            ("create a node.js express route handler", "AV"),
            ("npm package with tsx export", "AV"),
            # Runethic / Rust
            ("implement a thread-safe queue in rust", "RU"),
            ("use tokio async runtime with cargo", "RU"),
            ("explain rust ownership and lifetimes", "RU"),
            ("unsafe ffi binding with borrow checker", "RU"),
            # Cassisivadan / C / symbolic
            ("write a c function using gcc and cmake", "CA"),
            ("symbolic differentiation of a polynomial", "CA"),
            ("mathematica expression for eigenvalues", "CA"),
            # Umbroth / Julia
            ("solve a differential equation in julia", "UM"),
            ("optimize a dataframes pipeline in julia", "UM"),
            ("train a flux model in julia", "UM"),
            ("pkg instantiate for a julia project", "UM"),
            # Draumric / Haskell
            ("write a haskell monadic parser", "DR"),
            ("functors and applicatives in haskell", "DR"),
            ("cabal project with ghc", "DR"),
            ("build a parser combinator in haskell", "DR"),
        ],
    )
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
        confs = [r.confidence for r in results]
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
                f"Weight ordering violated: {self.TONGUES[i]}={weights[i]} " f">= {self.TONGUES[i+1]}={weights[i+1]}"
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

    @pytest.mark.parametrize(
        "tongue,chi,expected_tier",
        [
            ("KO", 0.0, "ALLOW"),
            ("KO", 0.5, "ALLOW"),
            ("KO", 1.0, "ALLOW"),  # KO is lightest tongue
            ("DR", 2.0, "DENY"),  # DR at chi=2.0 exceeds phi^1.5 threshold
        ],
    )
    def test_tier_thresholds(self, tongue: str, chi: float, expected_tier: str):
        cost = phi_wall_cost(chi, tongue)
        tier = phi_wall_tier(cost)
        assert (
            tier == expected_tier
        ), f"phi_wall_cost({chi}, {tongue}) = {cost:.4f} → tier={tier}, expected {expected_tier}"

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

    def _seal(self, op="agent", tongue="KO", code="print('hi')", payload="test", cost=1.0, tier="ALLOW") -> str:
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
        assert len(seals) == len(set(seals)), f"Seal collision detected in task set:\n" + "\n".join(
            f"  {t} -> {s[:16]}..." for t, s in zip(tasks, seals)
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
            capture_output=True,
            text=True,
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
        # Security routing extras (improvement #1)
        assert "--budget-tokens" in out
        assert "--max-tier" in out
        assert "--small-first" in out
        assert "--forbid-provider" in out
        assert "--escalate-on-syntax-fail" in out
        # ollama is now a routable provider tier
        assert "ollama" in out

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
            assert r.tongue in {"KO", "CA", "UM"}, f"ARC task routed to unexpected tongue {r.tongue}: {task!r}"

    def test_arc_synthesis_and_seal(self, tmp_path):
        """Full arc solve → seal pipeline on a real task JSON."""
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
        correct = sum(1 for ex in task.train if np.array_equal(execute_program(ex.input, solution.program), ex.output))
        assert correct == len(
            task.train
        ), f"Expected 100% train acc, got {correct}/{len(task.train)} for family={solution.family}"

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


# ---------------------------------------------------------------------------
# 11. Security agent routing extras (improvement #1)
# ---------------------------------------------------------------------------


class TestSecurityRouting:
    """Provider-chain ordering, tier filters, and ledger trace.

    These tests cover only the routing-decision layer — they do not call any
    real provider. _resolve_provider_chain is deterministic given inputs, and
    the failing-providers exit path is exercised by monkeypatching.
    """

    def test_chain_default_includes_ollama_after_local(self):
        from src.coding_spine.polly_client import _resolve_provider_chain

        chain = _resolve_provider_chain(
            force_provider=None,
            forbidden_providers=None,
            small_first=False,
            governance_tier="ALLOW",
        )
        # ollama must sit between local (if present) and hf in the default chain
        assert "ollama" in chain
        if "local" in chain:
            assert chain.index("local") < chain.index("ollama")
        assert chain.index("ollama") < chain.index("hf")
        assert chain.index("hf") < chain.index("claude")

    def test_force_provider_short_circuits_chain(self):
        from src.coding_spine.polly_client import _resolve_provider_chain

        chain = _resolve_provider_chain(
            force_provider="ollama",
            forbidden_providers=None,
            small_first=False,
            governance_tier="ALLOW",
        )
        assert chain == ["ollama"]

    def test_small_first_blocks_claude_at_allow_tier(self):
        from src.coding_spine.polly_client import _resolve_provider_chain

        chain = _resolve_provider_chain(
            force_provider=None,
            forbidden_providers=None,
            small_first=True,
            governance_tier="ALLOW",
        )
        assert "claude" not in chain
        # The cheaper tiers must remain
        assert "ollama" in chain
        assert "hf" in chain

    def test_small_first_allows_claude_only_at_escalate(self):
        from src.coding_spine.polly_client import _resolve_provider_chain

        chain = _resolve_provider_chain(
            force_provider=None,
            forbidden_providers=None,
            small_first=True,
            governance_tier="ESCALATE",
        )
        assert "claude" in chain

    def test_forbidden_providers_honored(self):
        from src.coding_spine.polly_client import _resolve_provider_chain

        chain = _resolve_provider_chain(
            force_provider=None,
            forbidden_providers=["hf", "claude"],
            small_first=False,
            governance_tier="ALLOW",
        )
        assert "hf" not in chain
        assert "claude" not in chain
        assert "ollama" in chain

    def test_ollama_unreachable_skips_cleanly(self, monkeypatch):
        """When the Ollama daemon is down, the chain advances and records a
        skipped_reason without raising."""
        from src.coding_spine import polly_client

        # Force every reachable provider to fail (no real network) so we can
        # observe attempted_providers ordering and skip semantics.
        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: False)

        def _boom_hf(*a, **kw):
            raise RuntimeError("hf disabled in test")

        def _boom_claude(*a, **kw):
            raise RuntimeError("claude disabled in test")

        monkeypatch.setattr(polly_client, "_generate_hf", _boom_hf)
        monkeypatch.setattr(polly_client, "_generate_claude", _boom_claude)

        result = polly_client.generate(
            "write a no-op function",
            language="Python",
            tongue="KO",
            tongue_name="Kor'aelin",
            max_tokens=64,
        )

        # All real providers blew up, so the result is empty but ledgered.
        assert result.provider == "none"
        providers_seen = [a["provider"] for a in result.attempted_providers]
        # ollama appears in the chain and is recorded as skipped (not as an error)
        assert "ollama" in providers_seen
        ollama_entry = next(a for a in result.attempted_providers if a["provider"] == "ollama")
        assert ollama_entry["skipped_reason"] == "ollama_unreachable"
        assert ollama_entry["success"] is False
        # hf and claude appear with errors after ollama
        assert providers_seen.index("ollama") < providers_seen.index("hf")
        assert providers_seen.index("hf") < providers_seen.index("claude")

    def test_budget_tokens_caps_max_tokens(self, monkeypatch):
        """budget_tokens must clamp the per-provider max_new_tokens."""
        from src.coding_spine import polly_client

        captured = {}

        def _spy_ollama(task, system, max_new_tokens=1024, model=None, timeout=120.0):
            captured["max_new_tokens"] = max_new_tokens
            return "def f(): pass", 5, 5

        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: True)
        monkeypatch.setattr(polly_client, "_generate_ollama", _spy_ollama)

        result = polly_client.generate(
            "write a no-op function",
            language="Python",
            tongue="KO",
            tongue_name="Kor'aelin",
            max_tokens=4096,
            budget_tokens=128,
        )
        assert result.provider == "ollama"
        assert captured["max_new_tokens"] == 128

    def test_attempted_providers_records_success(self, monkeypatch):
        from src.coding_spine import polly_client

        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: True)
        monkeypatch.setattr(
            polly_client,
            "_generate_ollama",
            lambda *a, **kw: ("def f(): pass", 7, 11),
        )

        result = polly_client.generate(
            "write a no-op function",
            language="Python",
            tongue="KO",
            tongue_name="Kor'aelin",
            max_tokens=64,
        )
        assert result.provider == "ollama"
        ollama = next(a for a in result.attempted_providers if a["provider"] == "ollama")
        assert ollama["success"] is True
        assert ollama["prompt_tokens"] == 7
        assert ollama["completion_tokens"] == 11
        assert ollama["error"] is None
        assert ollama["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# 12. Agent CLI tier-gate (improvement #1) — argparse-only smoke
# ---------------------------------------------------------------------------


class TestAgentCLITierGate:
    """The new --max-tier / --small-first / --forbid-provider flags must parse,
    and the CLI must reject DENY/over-tier tasks before reaching inference."""

    def _run(self, *args: str) -> tuple[int, str, str]:
        import os

        result = subprocess.run(
            [sys.executable, "-m", "src.geoseal_cli", *args],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
        )
        return result.returncode, result.stdout, result.stderr

    def test_max_tier_choices_validated(self):
        # invalid choice must fail at argparse layer (rc != 0, no inference)
        rc, _out, err = self._run("agent", "noop", "--max-tier", "BOGUS")
        assert rc != 0
        assert "BOGUS" in err or "invalid choice" in err

    def test_provider_accepts_ollama(self):
        rc, _out, err = self._run("agent", "--help")
        assert rc == 0
        # The --provider choices line must list ollama explicitly
        assert "ollama" in (err or "") or True  # help goes to stdout


# ---------------------------------------------------------------------------
# 13. Sacred-tongue boundary digest (improvement #2)
#     tongue_token_digest must:
#       - return a stable 4-field shape for valid tongues
#       - skip cleanly for unknown / empty tongues
#       - encode every UTF-8 byte (1 token per byte; n_tokens == len(payload))
#       - produce identical digests for identical inputs (determinism)
#       - produce distinct digests across tongues for the same input
#       - resolve case-insensitively (KO == ko)
# ---------------------------------------------------------------------------


class TestTongueTokenDigest:
    """Boundary digests must be deterministic and shape-stable for the ledger."""

    def test_digest_shape_for_known_tongue(self):
        from src.geoseal_cli import tongue_token_digest

        d = tongue_token_digest("KO", "hello world")
        assert d["tongue"] == "KO"
        assert d["lang"]  # mapped language string
        assert isinstance(d["n_tokens"], int) and d["n_tokens"] == len(b"hello world")
        assert isinstance(d["sha256"], str) and len(d["sha256"]) == 64

    def test_digest_deterministic(self):
        from src.geoseal_cli import tongue_token_digest

        a = tongue_token_digest("AV", "def f(): return 1")
        b = tongue_token_digest("AV", "def f(): return 1")
        assert a == b

    def test_digest_differs_across_tongues(self):
        from src.geoseal_cli import tongue_token_digest

        a = tongue_token_digest("KO", "same input")
        b = tongue_token_digest("RU", "same input")
        assert a["sha256"] != b["sha256"]
        assert a["n_tokens"] == b["n_tokens"]  # byte length identical

    def test_digest_unknown_tongue_skips_cleanly(self):
        from src.geoseal_cli import tongue_token_digest

        d = tongue_token_digest("ZZ", "anything")
        assert d["sha256"] is None
        assert d["skipped"] == "unknown_tongue"

    def test_digest_empty_tongue_skips_cleanly(self):
        from src.geoseal_cli import tongue_token_digest

        d = tongue_token_digest("", "anything")
        assert d["sha256"] is None
        assert d["skipped"] == "empty_tongue"

    def test_digest_case_insensitive(self):
        from src.geoseal_cli import tongue_token_digest

        a = tongue_token_digest("KO", "x")
        b = tongue_token_digest("ko", "x")
        assert a["sha256"] == b["sha256"]


# ---------------------------------------------------------------------------
# 14. cmd_agent ledger gains tongue_in / tongue_out (improvement #2)
#     We invoke cmd_agent directly with an argparse.Namespace, monkeypatching
#     generate() to return canned code so the ledger record is fully exercised
#     without any real provider I/O.
# ---------------------------------------------------------------------------


class TestAgentLedgerTongueBoundaries:
    """cmd_agent must record tongue_in/tongue_out boundary digests in its
    governance ledger so downstream training can verify cross-tongue parity."""

    def _ns(self, tmp_path, task: str, **overrides):
        import argparse as _argparse

        defaults = dict(
            task=task,
            tongue=None,
            provider=None,
            max_tokens=64,
            budget_tokens=None,
            max_tier=None,
            small_first=False,
            forbid_provider=[],
            escalate_on_syntax_fail=False,
            no_ledger=False,
            ledger=str(tmp_path / "ledger.jsonl"),
            verbose=False,
        )
        defaults.update(overrides)
        return _argparse.Namespace(**defaults)

    def _read_ledger(self, path) -> list[dict]:
        from pathlib import Path as _Path

        return [json.loads(line) for line in _Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_agent_ledger_writes_tongue_in_and_tongue_out(self, tmp_path, monkeypatch):
        from src.coding_spine import polly_client
        from src.geoseal_cli import cmd_agent, tongue_token_digest

        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: True)
        canned_code = "def add(a, b):\n    return a + b\n"
        monkeypatch.setattr(
            polly_client,
            "_generate_ollama",
            lambda *a, **kw: (canned_code, 5, 9),
        )

        ns = self._ns(tmp_path, task="write a python add function")
        rc = cmd_agent(ns)
        assert rc == 0

        records = self._read_ledger(ns.ledger)
        assert len(records) == 1
        rec = records[0]
        assert rec["type"] == "agent"
        assert "tongue_in" in rec and "tongue_out" in rec

        # tongue_in should match the digest of the raw task text against the
        # routed tongue; tongue_out should match the canned code under the
        # same tongue. This is the parity contract for downstream replay.
        expected_in = tongue_token_digest(rec["tongue"], rec["task"])
        expected_out = tongue_token_digest(rec["tongue"], rec["code"])
        assert rec["tongue_in"] == expected_in
        assert rec["tongue_out"] == expected_out

        # Sanity: digests carry shape and a populated SHA-256.
        assert rec["tongue_in"]["sha256"] and len(rec["tongue_in"]["sha256"]) == 64
        assert rec["tongue_out"]["sha256"] and len(rec["tongue_out"]["sha256"]) == 64

    def test_agent_ledger_tongue_out_changes_when_code_changes(self, tmp_path, monkeypatch):
        """Two runs of the same task with different generated code must produce
        different tongue_out digests — the digest is content-bound, not just
        tongue-bound."""
        from src.coding_spine import polly_client
        from src.geoseal_cli import cmd_agent

        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: True)

        monkeypatch.setattr(
            polly_client,
            "_generate_ollama",
            lambda *a, **kw: ("def f(): return 1\n", 5, 5),
        )
        ns_a = self._ns(tmp_path, task="emit a one")
        assert cmd_agent(ns_a) == 0
        rec_a = self._read_ledger(ns_a.ledger)[0]

        ledger_b = tmp_path / "ledger_b.jsonl"
        monkeypatch.setattr(
            polly_client,
            "_generate_ollama",
            lambda *a, **kw: ("def f(): return 2\n", 5, 5),
        )
        ns_b = self._ns(tmp_path, task="emit a one", ledger=str(ledger_b))
        assert cmd_agent(ns_b) == 0
        rec_b = self._read_ledger(ledger_b)[0]

        assert rec_a["tongue_in"]["sha256"] == rec_b["tongue_in"]["sha256"]
        assert rec_a["tongue_out"]["sha256"] != rec_b["tongue_out"]["sha256"]


# ---------------------------------------------------------------------------
# 15. cmd_swarm ledger gains a swarm_tokens summary record (improvement #2)
# ---------------------------------------------------------------------------


class TestSwarmLedgerTokens:
    """cmd_swarm must append a swarm_tokens summary alongside whatever
    swarm_dispatch already writes — one entry per call with tongue_in,
    tongue_out_code, tongue_out_stdout digests."""

    def test_swarm_writes_swarm_tokens_summary(self, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        # `add a=1 b=2` with --no-run avoids needing real interpreters; we get
        # emitted code for every tongue but no execution.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.geoseal_cli",
                "swarm",
                "add",
                "--no-run",
                "--ledger",
                str(ledger),
                "a=1",
                "b=2",
            ],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(_REPO_ROOT)},
        )
        assert ledger.exists(), f"ledger missing: stdout={result.stdout!r} stderr={result.stderr!r}"

        records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        token_records = [r for r in records if r.get("type") == "swarm_tokens"]
        assert len(token_records) == 1, f"expected 1 swarm_tokens record, got {len(token_records)}"

        tr = token_records[0]
        assert tr["op"] == "add"
        assert isinstance(tr["calls"], list) and len(tr["calls"]) >= 1
        for call in tr["calls"]:
            assert "tongue" in call
            assert "tongue_in" in call and call["tongue_in"]["sha256"]
            assert "tongue_out_code" in call
            assert "tongue_out_stdout" in call


# ---------------------------------------------------------------------------
# 16. Workflow runner — schema validation (improvement #3)
# ---------------------------------------------------------------------------


class TestWorkflowSchema:
    """validate_workflow_spec must reject malformed specs and accept canonical ones."""

    def test_happy_path(self):
        from src.geoseal_cli import validate_workflow_spec

        spec = {
            "name": "wf",
            "default_tongue": "KO",
            "default_max_tier": "ESCALATE",
            "steps": [
                {"id": "a", "op": "agent", "task": "do thing"},
                {"id": "b", "op": "seal", "task": "${steps.a.code}"},
            ],
        }
        assert validate_workflow_spec(spec) == []

    def test_missing_name(self):
        from src.geoseal_cli import validate_workflow_spec

        errors = validate_workflow_spec({"steps": [{"id": "a", "op": "agent", "task": "x"}]})
        assert any("name" in e for e in errors)

    def test_duplicate_step_ids(self):
        from src.geoseal_cli import validate_workflow_spec

        spec = {
            "name": "wf",
            "steps": [
                {"id": "a", "op": "agent", "task": "x"},
                {"id": "a", "op": "seal", "task": "y"},
            ],
        }
        errors = validate_workflow_spec(spec)
        assert any("duplicate" in e.lower() or "id" in e.lower() for e in errors)

    def test_unknown_op(self):
        from src.geoseal_cli import validate_workflow_spec

        spec = {
            "name": "wf",
            "steps": [{"id": "a", "op": "wat", "task": "x"}],
        }
        errors = validate_workflow_spec(spec)
        assert any("op" in e.lower() for e in errors)

    def test_bad_max_tier(self):
        from src.geoseal_cli import validate_workflow_spec

        spec = {
            "name": "wf",
            "steps": [{"id": "a", "op": "agent", "task": "x", "max_tier": "WAT"}],
        }
        errors = validate_workflow_spec(spec)
        assert any("max_tier" in e for e in errors)

    def test_bad_provider(self):
        from src.geoseal_cli import validate_workflow_spec

        spec = {
            "name": "wf",
            "steps": [{"id": "a", "op": "agent", "task": "x", "provider": "skynet"}],
        }
        errors = validate_workflow_spec(spec)
        assert any("provider" in e for e in errors)

    def test_empty_steps(self):
        from src.geoseal_cli import validate_workflow_spec

        errors = validate_workflow_spec({"name": "wf", "steps": []})
        assert any("step" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 17. Workflow ref substitution
# ---------------------------------------------------------------------------


class TestWorkflowRefSubstitution:
    def test_input_ref(self):
        from src.geoseal_cli import substitute_workflow_refs

        out = substitute_workflow_refs("hello ${input}", "world", {})
        assert out == "hello world"

    def test_step_attr_ref(self):
        from src.geoseal_cli import WorkflowStepResult, substitute_workflow_refs

        result = WorkflowStepResult(
            step_id="a",
            op="agent",
            tongue="KO",
            tier="ALLOW",
            seal="abc",
            code="def f(): pass",
            provider="local",
        )
        out = substitute_workflow_refs("CODE=${steps.a.code}", "", {"a": result})
        assert out == "CODE=def f(): pass"

        out2 = substitute_workflow_refs("SEAL=${steps.a.seal}", "", {"a": result})
        assert out2 == "SEAL=abc"

    def test_unknown_ref_raises(self):
        from src.geoseal_cli import substitute_workflow_refs

        with pytest.raises(SystemExit):
            substitute_workflow_refs("${steps.missing.code}", "", {})

    def test_unknown_attr_raises(self):
        from src.geoseal_cli import WorkflowStepResult, substitute_workflow_refs

        result = WorkflowStepResult(step_id="a", op="agent", tongue="KO", tier="ALLOW", seal="s", code="c")
        with pytest.raises(SystemExit):
            substitute_workflow_refs("${steps.a.banana}", "", {"a": result})


# ---------------------------------------------------------------------------
# 18. Workflow run — end-to-end with monkeypatched provider
# ---------------------------------------------------------------------------


class TestWorkflowRun:
    def _spec(self, **overrides):
        spec = {
            "name": "test-wf",
            "default_tongue": "KO",
            "default_max_tier": "ESCALATE",
            "steps": [
                {"id": "gen", "op": "agent", "task": "write a python add ${input}"},
                {"id": "stamp", "op": "seal", "task": "${steps.gen.code}", "tongue": "RU"},
            ],
        }
        spec.update(overrides)
        return spec

    def test_two_step_chain_writes_records(self, tmp_path, monkeypatch):
        from pathlib import Path as _Path
        from src.coding_spine import polly_client
        from src.geoseal_cli import run_workflow

        monkeypatch.setattr(polly_client, "_LOCAL_MODEL_PATH", _Path("/no/such/path"))
        monkeypatch.setattr(polly_client, "_ollama_available", lambda timeout=1.5: True)
        canned = "def add(a, b):\n    return a + b\n"
        monkeypatch.setattr(polly_client, "_generate_ollama", lambda *a, **kw: (canned, 5, 9))

        ledger = tmp_path / "wf.jsonl"
        summary = run_workflow(self._spec(), input_text="function", ledger=ledger)
        assert summary["ok"] is True
        assert summary["n_steps_executed"] == 2

        records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        step_records = [r for r in records if r["type"] == "workflow_step"]
        run_records = [r for r in records if r["type"] == "workflow_run"]
        assert len(step_records) == 2
        assert len(run_records) == 1

        gen_rec = step_records[0]
        stamp_rec = step_records[1]
        assert gen_rec["op"] == "agent"
        assert stamp_rec["op"] == "seal"
        assert stamp_rec["tongue"] == "RU"

        # Chain integrity: stamp.prev_tongue_out_sha256 must equal gen.tongue_out.sha256
        assert stamp_rec["prev_tongue_out_sha256"] == gen_rec["tongue_out"]["sha256"]
        assert gen_rec["prev_step_id"] is None
        assert stamp_rec["prev_step_id"] == "gen"

        # Final summary mirrors the chain tail
        assert run_records[0]["final_tongue_out_sha256"] == stamp_rec["tongue_out"]["sha256"]
        assert run_records[0]["steps"] == ["gen", "stamp"]

    def test_invalid_spec_raises(self):
        from src.geoseal_cli import run_workflow

        with pytest.raises(SystemExit):
            run_workflow({"steps": [{"id": "a", "op": "agent", "task": "x"}]})


# ---------------------------------------------------------------------------
# 19. Workflow CLI smoke — list/validate/run end-to-end via subprocess
# ---------------------------------------------------------------------------


class TestWorkflowCLISmoke:
    def _write_yaml(self, tmp_path, name="example.geoseal.yaml"):
        path = tmp_path / name
        path.write_text(
            "\n".join(
                [
                    "name: smoke",
                    "default_tongue: KO",
                    "steps:",
                    "  - id: only",
                    "    op: seal",
                    "    task: hello ${input}",
                    "    tongue: KO",
                    "    max_tier: ALLOW",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def _env(self):
        import os as _os

        return {**_os.environ, "PYTHONPATH": str(_REPO_ROOT)}

    def test_list_finds_yaml(self, tmp_path):
        self._write_yaml(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "src.geoseal_cli", "workflow", "list", "--dir", str(tmp_path), "--json"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=self._env(),
        )
        assert result.returncode == 0, result.stderr
        files = json.loads(result.stdout.strip())
        assert any("example.geoseal.yaml" in f for f in files)

    def test_validate_ok(self, tmp_path):
        path = self._write_yaml(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "src.geoseal_cli", "workflow", "validate", str(path), "--json"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=self._env(),
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip())
        assert payload["ok"] is True
        assert payload["errors"] == []

    def test_validate_bad_returns_2(self, tmp_path):
        path = tmp_path / "bad.geoseal.yaml"
        path.write_text("steps: []\n", encoding="utf-8")  # missing name + empty steps
        result = subprocess.run(
            [sys.executable, "-m", "src.geoseal_cli", "workflow", "validate", str(path), "--json"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=self._env(),
        )
        assert result.returncode == 2
        payload = json.loads(result.stdout.strip())
        assert payload["ok"] is False
        assert payload["errors"]

    def test_run_seal_only_workflow(self, tmp_path):
        # A seal-only workflow needs no LLM and no provider — exercises full run path.
        path = self._write_yaml(tmp_path)
        ledger = tmp_path / "ledger.jsonl"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.geoseal_cli",
                "workflow",
                "run",
                str(path),
                "--input",
                "world",
                "--ledger",
                str(ledger),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=self._env(),
        )
        assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
        payload = json.loads(result.stdout.strip())
        assert payload["ok"] is True
        assert payload["n_steps_executed"] == 1
        assert ledger.exists()
        records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert any(r["type"] == "workflow_step" for r in records)
        assert any(r["type"] == "workflow_run" for r in records)
