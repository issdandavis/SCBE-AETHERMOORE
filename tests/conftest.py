"""
SCBE Test Configuration
=======================

Shared fixtures and configuration for all test tiers.
"""

import pytest
import sys
import os
import importlib
import math
import tempfile
import shutil
import uuid
from pathlib import Path
from ctypes.util import find_library
from typing import List
from dataclasses import dataclass

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

# Ensure repo-local `src/` wins over any installed modules with the same names.
# CI has observed an installed `governance` module being imported before tests,
# which breaks imports like `from governance.*` even when tests later tweak sys.path.
# IMPORTANT: _SRC_ROOT must come BEFORE _REPO_ROOT on sys.path so that
# the repo's primary `src/` package tree is imported first for modules that only
# exist there (qc_lattice, governance, browser-facing adapters, etc.). Shared
# modules must still keep the same public contract across both trees.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SRC_ROOT))
sys.modules.pop("governance", None)
# Purge ALL symphonic_cipher submodules so the src/ variant is cleanly imported.
for _k in list(sys.modules):
    if _k == "symphonic_cipher" or _k.startswith("symphonic_cipher."):
        del sys.modules[_k]

# Force-load the src/ variant immediately so collection-time imports find it.
import symphonic_cipher as _sc_check
if getattr(_sc_check, "_VARIANT", None) != "src":
    # Wrong variant loaded — purge again and re-import with only src/ on path
    for _k in list(sys.modules):
        if _k == "symphonic_cipher" or _k.startswith("symphonic_cipher."):
            del sys.modules[_k]
    import importlib as _il
    _sc_check = _il.import_module("symphonic_cipher")
del _sc_check

# Keep pytest temp factories inside the repo workspace so Windows temp ACL issues
# do not break tmp_path/tmpdir-based tests.
_PYTEST_TEMP_PARENT = Path(__file__).resolve().parents[1] / "artifacts" / "pytest_temp_root"
_PYTEST_TEMP_PARENT.mkdir(parents=True, exist_ok=True)
_PYTEST_TEMP_ROOT = _PYTEST_TEMP_PARENT / f"session-{uuid.uuid4().hex[:8]}"
_PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_PYTEST_TEMP_ROOT)
os.environ["TMPDIR"] = str(_PYTEST_TEMP_ROOT)
os.environ["TEMP"] = str(_PYTEST_TEMP_ROOT)
os.environ["TMP"] = str(_PYTEST_TEMP_ROOT)


def _repo_local_mkdtemp(suffix=None, prefix=None, dir=None):
    """Create a repo-local temp dir without relying on Windows stdlib ACL setup.

    Python 3.14 on this Windows lane can create TemporaryDirectory/mkdtemp paths
    that immediately become inaccessible to the same interpreter. Building the
    directory directly under the repo-local pytest temp root avoids that ACL
    behavior while keeping test isolation deterministic.
    """

    base = Path(dir) if dir is not None else _PYTEST_TEMP_ROOT
    base.mkdir(parents=True, exist_ok=True)
    name = f"{prefix or 'tmp'}{uuid.uuid4().hex[:8]}{suffix or ''}"
    path = base / name
    path.mkdir(parents=True, exist_ok=False)
    return str(path.resolve())


class _RepoLocalTemporaryDirectory:
    def __init__(self, suffix=None, prefix=None, dir=None, ignore_cleanup_errors=False):
        self.name = _repo_local_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self._ignore_cleanup_errors = ignore_cleanup_errors

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)


tempfile.mkdtemp = _repo_local_mkdtemp
tempfile.TemporaryDirectory = _RepoLocalTemporaryDirectory


@pytest.fixture
def tmp_path():
    """Repo-local replacement for pytest's temp-path fixture on Windows.

    Some environments in this repo cannot create or recycle pytest's default
    temp roots due to ACL and sandbox interactions. A simple repo-local temp
    directory keeps file-based tests deterministic and avoids fixture setup
    failures unrelated to the code under test.
    """
    path = _PYTEST_TEMP_ROOT / f"case-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# Compatibility alias for ai_brain package imports that may resolve through
# legacy/broken repo symlink paths. Uses threading timeout to prevent hangs
# from heavy transitive imports (scipy, matplotlib) on Windows.
def _register_ai_brain_aliases():
    try:
        _ai_pkg = importlib.import_module("src.symphonic_cipher.scbe_aethermoore.ai_brain")
        sys.modules.setdefault("symphonic_cipher.scbe_aethermoore.ai_brain", _ai_pkg)
        for _name in (
            "unified_state",
            "detection",
            "bft_consensus",
            "multiscale_spectrum",
            "mirror_shift",
            "governance_adapter",
            "fsgs",
            "hamiltonian_braid",
            "dual_ternary",
            "dual_lattice",
            "cymatic_voxel_net",
            "tri_manifold_lattice",
        ):
            try:
                _mod = importlib.import_module(f"src.symphonic_cipher.scbe_aethermoore.ai_brain.{_name}")
                sys.modules.setdefault(f"symphonic_cipher.scbe_aethermoore.ai_brain.{_name}", _mod)
            except Exception:
                continue
    except Exception:
        pass

    # Bridge src-only sub-packages that don't exist in root symphonic_cipher.
    # The root and src/ variants have different math (see CLAUDE.md), but many
    # sub-packages (game/, concept_blocks/, multimodal/, etc.) and modules
    # (trinary.py, gate_swap.py, etc.) only exist under src/.
    _SRC_ONLY_SUBPACKAGES = (
        # Directories
        "game",
        "concept_blocks",
        "multimodal",
        "rosetta",
        "qc_lattice",
        # Modules
        "trinary",
        "negabinary",
        "gate_swap",
        "flock_shepherd",
        "quasicrystal_lattice",
        "sacred_eggs",
        "sacred_eggs_ref",
        "sacred_egg_registry",
        "sacred_egg_integrator",
        "adaptive_navigator",
        "decision_telemetry",
        "cli_toolkit",
        "convert_to_sft",
        "genesis_protocol",
        "qr_cube_kdf",
        "aethercode_layer4_integration",
        "aetherlex_extract",
        "layer13_hive_integration",
        "polyglot_layer12_integration",
        "tri_mechanism_detector",
        "_scipy_compat",
    )
    for _subpkg in _SRC_ONLY_SUBPACKAGES:
        try:
            _mod = importlib.import_module(f"src.symphonic_cipher.scbe_aethermoore.{_subpkg}")
            sys.modules.setdefault(f"symphonic_cipher.scbe_aethermoore.{_subpkg}", _mod)
        except Exception:
            continue
    # Also bridge sub-modules within bridged packages (one level deep)
    _SRC_BASE = Path(__file__).resolve().parents[1] / "src" / "symphonic_cipher" / "scbe_aethermoore"
    for _subpkg in _SRC_ONLY_SUBPACKAGES:
        _pkg_dir = _SRC_BASE / _subpkg
        if _pkg_dir.is_dir():
            for _f in _pkg_dir.glob("*.py"):
                _child = _f.stem
                if _child.startswith("_"):
                    continue
                try:
                    _mod = importlib.import_module(f"src.symphonic_cipher.scbe_aethermoore.{_subpkg}.{_child}")
                    sys.modules.setdefault(f"symphonic_cipher.scbe_aethermoore.{_subpkg}.{_child}", _mod)
                except Exception:
                    continue


import threading as _threading

_t = _threading.Thread(target=_register_ai_brain_aliases, daemon=True)
_t.start()
_t.join(timeout=10)  # Give it 10 seconds max, then move on
del _t, _threading


# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio
R_FIFTH = 1.5  # Perfect fifth harmonic ratio


# =============================================================================
# TEST DATA FACTORIES
# =============================================================================


@dataclass
class TestVector:
    """Standard test vector for SCBE operations."""

    position: List[int]
    agent: str
    topic: str
    context: str
    expected_decision: str
    description: str


@pytest.fixture
def golden_ratio():
    """Golden ratio constant."""
    return PHI


@pytest.fixture
def harmonic_ratio():
    """Perfect fifth harmonic ratio."""
    return R_FIFTH


@pytest.fixture
def legitimate_request():
    """Fixture for legitimate (ALLOW) request."""
    return TestVector(
        position=[1, 2, 3, 5, 8, 13],  # Fibonacci - harmonic
        agent="trusted_agent",
        topic="memory",
        context="internal",
        expected_decision="ALLOW",
        description="Trusted internal agent with harmonic position",
    )


@pytest.fixture
def suspicious_request():
    """Fixture for suspicious (QUARANTINE) request."""
    return TestVector(
        position=[99, 99, 99, 99, 99, 99],  # Edge position
        agent="external_agent",
        topic="secrets",
        context="external",
        expected_decision="QUARANTINE",
        description="External agent at edge position",
    )


@pytest.fixture
def malicious_request():
    """Fixture for malicious (DENY) request."""
    return TestVector(
        position=[0, 0, 0, 0, 0, 0],  # Origin attack
        agent="malicious_bot",
        topic="admin",
        context="untrusted",
        expected_decision="DENY",
        description="Untrusted bot targeting admin",
    )


@pytest.fixture
def valid_api_key():
    """Valid API key for authenticated endpoints."""
    return "demo_key_12345"


@pytest.fixture
def invalid_api_key():
    """Invalid API key for rejection tests."""
    return "invalid_key_00000"


# =============================================================================
# MOCK OBJECTS
# =============================================================================


@pytest.fixture
def mock_scbe_result():
    """Mock SCBE pipeline result."""
    return {
        "decision": "ALLOW",
        "risk_base": 0.15,
        "risk_prime": 0.23,
        "H": 1.53,
        "d_star": 0.42,
        "coherence": {"spectral": 0.92, "spin": 0.88, "temporal": 0.95},
        "geometry": {"hyperbolic_dist": 0.42, "poincare_norm": 0.38},
    }


@pytest.fixture
def sacred_tongue_tokens():
    """Sacred Tongue token mappings."""
    return {
        "KO": "kor_nonce_token",
        "AV": "ava_aad_token",
        "RU": "run_salt_token",
        "CA": "cas_cipher_token",
        "UM": "umb_redact_token",
        "DR": "dra_tag_token",
    }


# =============================================================================
# MATHEMATICAL HELPERS
# =============================================================================


@pytest.fixture
def hyperbolic_distance():
    """Hyperbolic distance function (requires numpy)."""
    if not NUMPY_AVAILABLE:
        pytest.skip("numpy not installed")

    def _hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
        """Calculate hyperbolic distance in Poincaré ball."""
        u_norm_sq = np.sum(u**2)
        v_norm_sq = np.sum(v**2)
        diff_norm_sq = np.sum((u - v) ** 2)

        # Clamp to avoid numerical issues
        u_norm_sq = min(u_norm_sq, 0.9999)
        v_norm_sq = min(v_norm_sq, 0.9999)

        numerator = 2 * diff_norm_sq
        denominator = (1 - u_norm_sq) * (1 - v_norm_sq)

        if denominator <= 0:
            return float("inf")

        arg = 1 + numerator / denominator
        return np.arccosh(max(arg, 1.0))

    return _hyperbolic_distance


@pytest.fixture
def harmonic_scaling():
    """Harmonic scaling: score = 1 / (1 + d + 2 * phase_deviation)."""

    def _harmonic_scaling(d: float, phase_deviation: float = 0.0) -> float:
        return 1.0 / (1.0 + d + 2.0 * phase_deviation)

    return _harmonic_scaling


# =============================================================================
# PERFORMANCE HELPERS
# =============================================================================


@pytest.fixture
def performance_timer():
    """Context manager for timing operations."""
    import time

    class Timer:
        def __init__(self):
            self.elapsed = 0.0

        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start

    return Timer


# =============================================================================
# TEST MARKERS
# =============================================================================


# =============================================================================
# LIBOQS AVAILABILITY CHECK
# =============================================================================


def _liboqs_available() -> bool:
    """
    Check whether liboqs shared library appears available.

    Important:
    - Do NOT import `oqs` here because liboqs-python can trigger auto-install
      side effects during import when the shared library is missing.
    - Keep this probe side-effect free so test collection always succeeds.
    """
    if os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {"1", "true", "yes"}:
        return False

    # Fast path: system linker can resolve oqs
    if find_library("oqs") or find_library("liboqs"):
        return True

    # Path probes for local installs
    candidates: List[Path] = []
    oqs_install = os.getenv("OQS_INSTALL_PATH")
    if oqs_install:
        base = Path(oqs_install)
    else:
        base = Path.home() / "_oqs"

    candidates.extend(
        [
            base / "lib" / "liboqs.so",
            base / "lib64" / "liboqs.so",
            base / "lib" / "liboqs.dylib",
            base / "lib64" / "liboqs.dylib",
            base / "bin" / "liboqs.dll",
            base / "lib" / "liboqs.dll",
            Path("/usr/local/lib/liboqs.so"),
            Path("/usr/local/lib/liboqs.dylib"),
            Path("/usr/lib/liboqs.so"),
        ]
    )

    return any(p.exists() for p in candidates)


LIBOQS_AVAILABLE = _liboqs_available()

# Skip decorator for tests requiring liboqs
requires_liboqs = pytest.mark.skipif(not LIBOQS_AVAILABLE, reason="liboqs-python not installed (optional dependency)")


# =============================================================================
# CRYPTOGRAPHY AVAILABILITY CHECK
# =============================================================================


def _cryptography_available() -> bool:
    """Check whether the cryptography package is functional (includes cffi backend).

    The cryptography package uses Rust (PyO3) bindings that can trigger a
    pyo3_runtime.PanicException when the cffi backend is missing.  This panic
    bypasses normal Python exception handling, so we probe the cffi backend
    *before* touching the cryptography package itself.
    """
    try:
        import _cffi_backend  # noqa: F401
    except ImportError:
        return False
    try:
        from cryptography.fernet import Fernet  # noqa: F401

        return True
    except Exception:
        return False


CRYPTOGRAPHY_AVAILABLE = _cryptography_available()

# Skip decorator for tests requiring cryptography
requires_cryptography = pytest.mark.skipif(
    not CRYPTOGRAPHY_AVAILABLE,
    reason="cryptography package not functional (cffi backend missing)",
)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "enterprise: Enterprise-grade tests (compliance, security)")
    config.addinivalue_line("markers", "professional: Professional/industry standard tests")
    config.addinivalue_line("markers", "homebrew: Quick developer feedback tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "crypto: Cryptographic tests")
    config.addinivalue_line("markers", "math: Mathematical verification tests")
    config.addinivalue_line("markers", "governance: Governance decision tests")
    config.addinivalue_line("markers", "pqc: Post-quantum cryptography tests")
    config.addinivalue_line("markers", "requires_liboqs: Tests requiring liboqs-python")
    config.addinivalue_line("markers", "requires_cryptography: Tests requiring cryptography package")


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests that require unavailable optional dependencies."""
    if not LIBOQS_AVAILABLE:
        skip_liboqs = pytest.mark.skip(reason="liboqs-python not installed (optional dependency)")
        for item in items:
            if "requires_liboqs" in item.keywords or "pqc" in item.keywords:
                item.add_marker(skip_liboqs)

    if not CRYPTOGRAPHY_AVAILABLE:
        skip_crypto = pytest.mark.skip(reason="cryptography package not functional (cffi backend missing)")
        for item in items:
            if "requires_cryptography" in item.keywords or "security" in item.keywords:
                item.add_marker(skip_crypto)
