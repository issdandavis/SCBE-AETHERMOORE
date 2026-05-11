"""Tests for the Schrödinger code-wave generator primitives."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from scripts.eval import schrodinger_codewave_generator as sw

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_indicator_masks_mark_required_and_forbidden() -> None:
    vocab = ["umbroth", "haskell", "molecule", "def ", "return", "atom", "atomicity"]
    req_mask, forb_mask = sw._build_indicator_masks(
        vocab, required=["UMBROTH", "haskell"], forbidden=["molecule", "atom"]
    )
    # required: 'umbroth' and 'haskell' should be marked
    assert req_mask[vocab.index("umbroth")] >= 1.0
    assert req_mask[vocab.index("haskell")] >= 1.0
    assert req_mask[vocab.index("def ")] == 0.0
    # forbidden: 'molecule' and 'atom' but NOT 'atomicity' (word-boundary)
    assert forb_mask[vocab.index("molecule")] >= 1.0
    assert forb_mask[vocab.index("atom")] >= 1.0
    assert forb_mask[vocab.index("atomicity")] == 0.0


def test_step_picks_required_token_under_strong_alpha() -> None:
    # 8-vocab toy: base prefers index 0; required token is the NEIGHBOR
    # of the base favorite. Even modest tunneling should redirect.
    base_logits = np.array([4.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0], dtype=np.float32)
    req_mask = np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    forb_mask = np.zeros(8, dtype=np.float32)
    cfg = sw.SchrodingerConfig(alpha_required=10.0, beta_forbidden=0.0, n_steps=20, tau=0.5)
    chosen = sw.schrodinger_step_logits(base_logits, req_mask, forb_mask, cfg)
    assert chosen == 1


def test_step_long_distance_tunneling_with_more_evolution_time() -> None:
    # Same logits as above, but required is FAR from base favorite.
    # Long evolution + larger 1/m allows the wavefunction to reach it.
    base_logits = np.array([4.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0], dtype=np.float32)
    req_mask = np.array([0, 0, 0, 0, 0, 1, 0, 0], dtype=np.float32)
    forb_mask = np.zeros(8, dtype=np.float32)
    cfg = sw.SchrodingerConfig(
        alpha_required=15.0, beta_forbidden=0.0, n_steps=80, tau=0.5, inverse_mass=1.0
    )
    chosen = sw.schrodinger_step_logits(base_logits, req_mask, forb_mask, cfg)
    assert chosen == 5


def test_step_avoids_forbidden_token_under_strong_beta() -> None:
    base_logits = np.array([0.0, 0.0, 4.0, 0.0, 0.0, 0.5, 0.0, 0.0], dtype=np.float32)
    req_mask = np.array([0, 0, 0, 0, 0, 1, 0, 0], dtype=np.float32)
    forb_mask = np.array([0, 0, 1, 0, 0, 0, 0, 0], dtype=np.float32)  # forbid base's favorite
    cfg = sw.SchrodingerConfig(alpha_required=8.0, beta_forbidden=20.0, n_steps=12, tau=0.4)
    chosen = sw.schrodinger_step_logits(base_logits, req_mask, forb_mask, cfg)
    assert chosen != 2  # the forbidden / base-favorite token must be avoided
    # Either the required token (5) or some other tunneled candidate; not the wall.


def test_step_falls_back_to_argmax_when_evolution_collapses() -> None:
    # Pathological: V is huge everywhere -> phase rotation only, no kinetic
    # mixing under the chosen tau means |psi|^2 is approximately the base
    # distribution. Without inverse_mass=0 the kinetic term still acts; we
    # set it tiny so this collapses to base argmax.
    base_logits = np.array([0.1, 5.0, 0.1, 0.1], dtype=np.float32)
    req_mask = np.zeros(4, dtype=np.float32)
    forb_mask = np.zeros(4, dtype=np.float32)
    cfg = sw.SchrodingerConfig(
        alpha_required=0.0, beta_forbidden=0.0, inverse_mass=0.0, n_steps=4, tau=0.1
    )
    chosen = sw.schrodinger_step_logits(base_logits, req_mask, forb_mask, cfg)
    assert chosen == 1


def test_evolve_real_time_preserves_norm() -> None:
    """Real-time Schrödinger evolution is unitary; sum |psi|^2 is conserved."""
    rng = np.random.default_rng(42)
    n = 32
    p = np.abs(rng.standard_normal(n))
    p = p / p.sum()
    psi = np.sqrt(p).astype(np.complex128)
    V = rng.standard_normal(n).astype(np.float64)
    cfg = sw.SchrodingerConfig(n_steps=10, tau=0.2, inverse_mass=0.5, imaginary_time=False)
    k_grid = np.fft.fftfreq(n) * (2.0 * np.pi)
    out = sw._evolve_wavefunction(psi.copy(), V, cfg, k_grid)
    assert np.isclose((np.abs(out) ** 2).sum(), 1.0, atol=1e-6)


def test_evolve_imaginary_time_renormalizes_to_unit_probability() -> None:
    """Imaginary-time evolution renormalizes per step; sum |psi|^2 stays = 1."""
    rng = np.random.default_rng(7)
    n = 32
    p = np.abs(rng.standard_normal(n))
    p = p / p.sum()
    psi = np.sqrt(p).astype(np.complex128)
    V = rng.standard_normal(n).astype(np.float64)
    cfg = sw.SchrodingerConfig(n_steps=10, tau=0.2, inverse_mass=0.5, imaginary_time=True)
    k_grid = np.fft.fftfreq(n) * (2.0 * np.pi)
    out = sw._evolve_wavefunction(psi.copy(), V, cfg, k_grid)
    assert np.isclose((np.abs(out) ** 2).sum(), 1.0, atol=1e-6)


def test_factory_returns_callable() -> None:
    f = sw.make_schrodinger_generator(model_id="dummy/never-loaded", max_new_tokens=8)
    assert callable(f)


def test_bakeoff_script_direct_schrodinger_dry_run(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "eval" / "diffusion_codegen_bakeoff.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
            "--schrodinger-only",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert list(tmp_path.glob("diffusion_bakeoff_*.json"))


def test_active_subset_includes_top_k_and_required_tokens() -> None:
    base_logits = np.array([0.5, 0.1, 0.9, 0.3, 0.05, 0.7, 0.05, 0.05], dtype=np.float32)
    req_mask = np.array([0, 0, 0, 0, 1, 0, 0, 1], dtype=np.float32)  # forces 4, 7
    active = sw._select_active_subset(base_logits, req_mask, top_k=3)
    s = set(int(i) for i in active)
    # Top-3 by logit are indices {2, 5, 0}; required adds {4, 7}.
    assert {2, 5, 0}.issubset(s)
    assert {4, 7}.issubset(s)
    # Result must be deduplicated and sorted
    assert list(active) == sorted(s)


def test_active_subset_disabled_returns_full_range() -> None:
    base = np.zeros(16, dtype=np.float32)
    req = np.zeros(16, dtype=np.float32)
    active = sw._select_active_subset(base, req, top_k=0)
    assert list(active) == list(range(16))


def test_step_with_active_subset_preserves_required_pull() -> None:
    """Active-subset variant still pulls amplitude into a required token
    that the AR baseline would have skipped."""
    n = 256
    rng = np.random.default_rng(0)
    base_logits = rng.standard_normal(n).astype(np.float32) * 0.1
    base_logits[0] = 5.0  # base favorite
    req_mask = np.zeros(n, dtype=np.float32)
    req_mask[1] = 1.0  # adjacent required
    forb_mask = np.zeros(n, dtype=np.float32)
    cfg = sw.SchrodingerConfig(
        alpha_required=10.0, beta_forbidden=0.0, n_steps=20, tau=0.5, active_top_k=64
    )
    chosen = sw.schrodinger_step_logits(base_logits, req_mask, forb_mask, cfg)
    assert chosen == 1


def test_active_top_k_dramatically_reduces_evolution_size() -> None:
    """Sanity: with V=152000 and K=256, evolution operates on ~256 elements,
    not 152000. Verified by inspecting the active subset returned."""
    n = 152_000
    rng = np.random.default_rng(1)
    # Strictly-ordered base logits so the top-K is unambiguous.
    base_logits = rng.standard_normal(n).astype(np.float32)
    # Force index 42 to be a guaranteed-out-of-top-K low value.
    base_logits[42] = -1000.0
    req_mask = np.zeros(n, dtype=np.float32)
    req_mask[42] = 1.0
    active = sw._select_active_subset(base_logits, req_mask, top_k=256)
    # 256 top-K + 1 required-but-not-in-top-K = 257
    assert active.shape[0] == 257
    assert 42 in active.tolist()
    # And massively smaller than the full vocab.
    assert active.shape[0] < n / 100
