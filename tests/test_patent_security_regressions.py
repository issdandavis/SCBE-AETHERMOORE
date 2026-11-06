"""Attack-case regression tests; load both on-disk Python variants explicitly."""

import importlib.util
import itertools
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_variant(tree, relative):
    name = "_patent_regression_" + tree.replace("/", "_") + relative.replace("/", "_").replace(".", "_")
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / tree / relative)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


@pytest.fixture(params=["src/symphonic_cipher", "symphonic_cipher"])
def cfi_module(request):
    return load_variant(request.param, "topological_cfi.py")


def graph(module, n, edges):
    cfg = module.ControlFlowGraph()
    for i in range(n):
        cfg.add_vertex(module.BasicBlock(i, [str(i)], i, i))
    for a, b in edges:
        cfg.add_edge(module.CFGEdge(a, b, "jump"))
    return cfg


def test_every_known_block_transition_matches_directed_policy(cfi_module):
    edges = {(0, 1), (1, 2), (2, 3)}
    monitor = cfi_module.TopologicalCFI()
    monitor.initialize(graph(cfi_module, 4, edges))
    for a, b in itertools.product(range(4), repeat=2):
        assert (monitor.check_transition(a, b) == cfi_module.CFIResult.VALID) == ((a, b) in edges)


def test_policy_is_frozen_until_explicit_reinitialization(cfi_module):
    cfg = graph(cfi_module, 3, [(0, 1), (1, 2)])
    monitor = cfi_module.TopologicalCFI()
    monitor.initialize(cfg)
    cfg.add_edge(cfi_module.CFGEdge(0, 2, "jump"))
    assert monitor.check_transition(0, 2) == cfi_module.CFIResult.VIOLATION
    monitor.initialize(cfg)
    assert monitor.check_transition(0, 2) == cfi_module.CFIResult.VALID


def test_uninitialized_symbolic_path_cannot_authorize(cfi_module):
    assert cfi_module.TopologicalCFI().verify_execution_path(["a", "b"])["valid"] is False


def test_explicit_loop_is_legal_and_skipped_edge_is_not(cfi_module):
    monitor = cfi_module.TopologicalCFI()
    monitor.initialize(graph(cfi_module, 3, [(0, 1), (1, 0), (1, 2)]))
    assert monitor.verify_execution_path(["0", "1", "0", "1", "2"])["valid"] is True
    assert monitor.verify_execution_path(["0", "2"])["valid"] is False


def test_single_vertex_self_loop(cfi_module):
    monitor = cfi_module.TopologicalCFI()
    monitor.initialize(graph(cfi_module, 1, [(0, 0)]))
    assert monitor.check_transition(0, 0) == cfi_module.CFIResult.VALID


def test_invalid_reinitialization_revokes_old_policy(cfi_module):
    monitor = cfi_module.TopologicalCFI()
    monitor.initialize(graph(cfi_module, 2, [(0, 1)]))
    bad = graph(cfi_module, 2, [(0, 99)])
    with pytest.raises(ValueError):
        monitor.initialize(bad)
    assert monitor.check_transition(0, 1) != cfi_module.CFIResult.VALID


def test_all_small_directed_graphs_against_path_oracle(cfi_module):
    for n in range(1, 5):
        possible = list(itertools.permutations(range(n), 2))
        for mask in range(1 << len(possible)):
            edges = {edge for bit, edge in enumerate(possible) if mask & (1 << bit)}
            expected = any(
                all((a, b) in edges for a, b in zip(order, order[1:])) for order in itertools.permutations(range(n))
            )
            actual, reason = cfi_module.HamiltonianTester(graph(cfi_module, n, edges)).is_hamiltonian()
            assert actual == expected, (n, edges, reason)


@pytest.mark.parametrize("tree", ["src/symphonic_cipher", "symphonic_cipher"])
def test_geometry_does_not_inflate_security_strength(tree):
    constants = load_variant(tree, "scbe_aethermoore/constants.py")
    for d, ratio in [(1, 1.5), (6, 2.0), (100, 10.0)]:
        assert constants.security_bits(128, d, ratio) == 128
        assert constants.security_level(2**128, d, ratio) == 2**128
    assert constants.harmonic_scale(6, 1.5) > 1


@pytest.mark.parametrize("tree", ["src/symphonic_cipher", "symphonic_cipher"])
def test_wave_simulator_requires_explicit_opt_in(tree):
    module = load_variant(tree, "scbe_aethermoore/dual_lattice.py")
    with pytest.raises(RuntimeError, match="simulation"):
        module.DualLatticeConsensus()
    demo = module.DualLatticeConsensus(allow_simulation=True)
    assert demo.simulation_only is True


def test_invalid_path_and_block_inputs_cannot_authorize(cfi_module):
    monitor = cfi_module.TopologicalCFI()
    assert monitor.verify_execution_path(["0", "1"])["hamiltonian_tested"] is False
    monitor.initialize(graph(cfi_module, 2, [(0, 1)]))
    for path in [None, "01", [], ["0"], [0, 1], ["0", []], ["0", "01"]]:
        assert monitor.verify_execution_path(path)["valid"] is False
    for a, b in [(False, 1), (0, True), (0, math.nan), (0, 99), (99, 1)]:
        assert monitor.check_transition(a, b) != cfi_module.CFIResult.VALID


def test_all_small_directed_transition_policies(cfi_module):
    # Include self-loops: 2^(n*n) policies, not just Hamiltonian graphs.
    for n in range(1, 4):
        possible = list(itertools.product(range(n), repeat=2))
        for mask in range(1 << len(possible)):
            edges = {edge for bit, edge in enumerate(possible) if mask & (1 << bit)}
            monitor = cfi_module.TopologicalCFI()
            monitor.initialize(graph(cfi_module, n, edges))
            for a, b in possible:
                valid = monitor.check_transition(a, b) == cfi_module.CFIResult.VALID
                assert valid == ((a, b) in edges), (n, edges, a, b)


@pytest.mark.parametrize("tree", ["src/symphonic_cipher", "symphonic_cipher"])
def test_invalid_security_score_inputs_are_rejected(tree):
    constants = load_variant(tree, "scbe_aethermoore/constants.py")
    for baseline, d, ratio in [(math.nan, 1, 1.5), (128, 0, 1.5), (128, 1, math.inf)]:
        with pytest.raises(ValueError):
            constants.security_bits(baseline, d, ratio)
