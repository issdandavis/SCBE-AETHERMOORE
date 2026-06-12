"""Regression locks for the tongue-multiplex probe (scripts/eval/tongue_multiplex_probe.py)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
_PROBE = _REPO / "scripts" / "eval" / "tongue_multiplex_probe.py"

sys.path.insert(0, str(_REPO))
_spec = importlib.util.spec_from_file_location("tongue_multiplex_under_test", _PROBE)
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

rng = np.random.default_rng(7)


def test_multiplex_is_bijective_six_way():
    for _ in range(50):
        v = rng.standard_normal(T.N) + 1j * rng.standard_normal(T.N)
        lam = T.pathways(v)
        assert np.linalg.norm(T.F_inv @ lam - v) < 1e-12
        # the circulant's first column reconstructs the token
        assert np.allclose(T.circulant(v)[:, 0], v)


def test_dropping_a_viewing_breaks_the_bijection():
    v = rng.standard_normal(T.N) + 1j * rng.standard_normal(T.N)
    lam = T.pathways(v)
    lam[2] = 0.0
    assert np.linalg.norm(T.F_inv @ lam - v) > 0.1  # not automatic — it's a real property


def test_cyclic_ops_keep_pathways_independent_generic_ops_bleed():
    g = rng.standard_normal(T.N) + 1j * rng.standard_normal(T.N)
    assert T.coupling(T.circulant(g)) < 1e-10  # cyclic -> no bleed
    A = rng.standard_normal((T.N, T.N)) + 1j * rng.standard_normal((T.N, T.N))
    assert T.coupling(A) > 0.5  # generic -> bleeds


def test_fourier_basis_only_special_for_cyclic_signals():
    # structured (2 cyclic modes) -> Fourier concentrates, random basis does not
    Q, _ = np.linalg.qr(rng.standard_normal((T.N, T.N)) + 1j * rng.standard_normal((T.N, T.N)))
    spec = np.zeros(T.N, complex)
    spec[[1, 4]] = [2 + 1j, 1 - 1j]
    v = T.F_inv @ spec
    pr_dft = T.participation_ratio(T.F @ v)
    pr_rnd = T.participation_ratio(Q.conj().T @ v)
    assert pr_dft < 0.7 * pr_rnd  # the viewing is load-bearing here


def test_layered_reasoning_two_tongues_separable():
    a = T.F_inv @ (np.eye(T.N)[1] * 3.0)
    b = T.F_inv @ (np.eye(T.N)[4] * 2.0)
    lam = T.pathways(a + b)
    assert np.abs(lam[1]) > 1e-9 and np.abs(lam[4]) > 1e-9
    assert np.allclose(lam[[0, 2, 3, 5]], 0, atol=1e-9)
    only_a = T.F_inv @ (lam * (np.arange(T.N) != 4))
    assert np.linalg.norm(only_a - a) < 1e-12


def test_phi_weighting_couples_pathways():
    # honest design constraint: phi is diagonal in tongue basis -> dense in pathway basis
    assert T.coupling(np.diag(T.PHI_W)) > 0.3
    assert T.coupling(np.eye(T.N)) < 1e-10
