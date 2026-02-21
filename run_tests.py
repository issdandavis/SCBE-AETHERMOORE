#!/usr/bin/env python3
"""
SCBE Test Runner
================

Convenient script to run tests at different levels:
- homebrew: Quick (<30s) smoke tests for development
- professional: Industry-standard tests
- enterprise: Full compliance and security tests
- all: Complete test suite

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py homebrew           # Quick development tests
    python run_tests.py professional       # Industry standard tests
    python run_tests.py enterprise         # Compliance tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --fast             # Skip slow tests
"""

import subprocess
import sys
import argparse
import time
from pathlib import Path


def run_tests(
    tier: str = "all",
    coverage: bool = False,
    fast: bool = False,
    verbose: bool = True,
    stop_on_fail: bool = False,
    preflight: bool = False
):
    """Run tests at the specified tier level."""

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Tier-specific test targets (reduces noisy collection from unrelated modules)
    tier_targets = {
        "integration": [
            "tests/test_integration_full.py",
            "tests/test_federated_orchestrator.py",
            "tests/test_kernel_manifest.py",
        ],
        "crypto": [
            "tests/crypto/",
        ],
        "api": [
            "tests/test_scbe_comprehensive.py",
            "tests/test_governance_adapter.py",
        ],
        "homebrew": [
            "tests/test_homebrew_quick.py",
            "tests/test_federated_orchestrator.py",
        ],
        "release": [
            "tests/test_federated_orchestrator.py",
            "tests/test_kernel_manifest.py",
        ],
    }

    targets = tier_targets.get(tier, ["tests/"])
    cmd.extend(targets)

    # Tier selection
    tier_markers = {
        "homebrew": "homebrew",
        "professional": "professional",
        "enterprise": "enterprise",
        "integration": "integration",
        "property": "property",
        "api": "api",
        "crypto": "crypto",
        "math": "math",
        "release": "not slow",
    }

    marker_expr = None
    if tier != "all" and tier in tier_markers:
        marker_expr = tier_markers[tier]

    # Verbosity
    if verbose:
        cmd.append("-v")

    # Coverage
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])

    # Fast mode (skip slow tests)
    if fast:
        marker_expr = f"({marker_expr}) and not slow" if marker_expr else "not slow"

    if marker_expr:
        cmd.extend(["-m", marker_expr])

    # Stop on first failure
    if stop_on_fail:
        cmd.append("-x")

    # Short traceback
    cmd.append("--tb=short")

    print("=" * 70)
    print(f"SCBE Test Runner - Tier: {tier.upper()}")
    print("=" * 70)
    print(f"Command: {' '.join(cmd)}")
    print("-" * 70)

    start_time = time.time()

    if preflight:
        preflight_files = [
            "training/federated_orchestrator.py",
            "training/trigger_vertex_training.py",
            "training/kernel_manifest.py",
        ]
        pf_cmd = ["python", "-m", "py_compile", *preflight_files]
        print("Preflight:", " ".join(pf_cmd))
        pf = subprocess.run(pf_cmd, cwd=Path(__file__).parent)
        if pf.returncode != 0:
            print("Preflight failed; aborting test run.")
            return pf.returncode

    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    elapsed = time.time() - start_time

    print("-" * 70)
    print(f"Completed in {elapsed:.2f}s")
    print(f"Exit code: {result.returncode}")
    print("=" * 70)

    return result.returncode


def print_help():
    """Print detailed help information."""
    help_text = """
SCBE Test Suite - Three-Tier Testing Architecture
=================================================

TIERS:
------
  homebrew     Quick smoke tests for development (~30s)
               - Basic functionality checks
               - Sanity tests
               - Fast feedback loop

  professional Industry-standard tests (~2-5 min)
               - API endpoint tests
               - Mathematical verification
               - Request/response validation

  enterprise   Compliance and security tests (~5-10 min)
               - NIST PQC compliance
               - Cryptographic correctness
               - Security hardening
               - Audit trail verification

SPECIAL MODES:
--------------
  integration  End-to-end integration tests
  property     Property-based tests (Hypothesis)
  api          API-specific tests
  crypto       Cryptographic tests
  math         Mathematical verification tests
  release      Stable release-gate tests (small, deterministic)

EXAMPLES:
---------
  python run_tests.py                      # Run all tests
  python run_tests.py homebrew             # Quick tests only
  python run_tests.py professional --cov   # Professional + coverage
  python run_tests.py enterprise -x        # Enterprise, stop on fail
  python run_tests.py --fast               # Skip slow tests
  python run_tests.py release --preflight  # Deterministic release gate

TEST FILES:
-----------
  tests/test_homebrew_quick.py        - Quick developer tests
  tests/test_professional_api.py      - API endpoint tests
  tests/test_professional_math.py     - Mathematical tests
  tests/test_enterprise_compliance.py - Compliance tests
  tests/test_property_based.py        - Property-based tests
  tests/test_integration_full.py      - Integration tests
"""
    print(help_text)


def main():
    parser = argparse.ArgumentParser(
        description="SCBE Test Runner - Run tests at different tier levels",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "tier",
        nargs="?",
        default="all",
        choices=["all", "homebrew", "professional", "enterprise", "integration", "property", "api", "crypto", "math", "release"],
        help="Test tier to run (default: all)"
    )

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )

    parser.add_argument(
        "--fast", "-f",
        action="store_true",
        help="Skip slow tests"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce verbosity"
    )

    parser.add_argument(
        "--stop-on-fail", "-x",
        action="store_true",
        help="Stop on first failure"
    )

    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run syntax preflight (py_compile) for key training scripts before pytest"
    )

    parser.add_argument(
        "--help-tiers",
        action="store_true",
        help="Show detailed help about test tiers"
    )

    args = parser.parse_args()

    if args.help_tiers:
        print_help()
        return 0

    return run_tests(
        tier=args.tier,
        coverage=args.coverage,
        fast=args.fast,
        verbose=not args.quiet,
        stop_on_fail=args.stop_on_fail,
        preflight=args.preflight
    )


if __name__ == "__main__":
    sys.exit(main())
