#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Package Builder
================================

Builds the complete SCBE package with all modules.

Usage:
    python build_package.py [--test] [--clean] [--install]

Options:
    --test      Run tests before building
    --clean     Clean build artifacts first
    --install   Install after building
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command and return success status."""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode == 0


def clean_build():
    """Clean build artifacts."""
    print("\n=== Cleaning build artifacts ===")
    dirs_to_remove = [
        "src/dist",
        "src/build",
        "src/*.egg-info",
        "src/scbe_aethermoore.egg-info",
    ]
    for pattern in dirs_to_remove:
        for path in Path(".").glob(pattern):
            if path.exists():
                print(f"Removing {path}")
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()


def run_tests():
    """Run the test suite."""
    print("\n=== Running Tests ===")

    # Python tests
    print("\n--- Python Tests ---")
    if not run_command("python -m pytest tests/ -v --tb=short -q"):
        print("WARNING: Some Python tests failed")

    # Physics tests
    print("\n--- Physics Simulation Tests ---")
    run_command("python src/physics_sim/test_physics_comprehensive.py")

    # AI Orchestration test
    print("\n--- AI Orchestration Tests ---")
    run_command(
        "python -c \"from src.ai_orchestration.security import PromptSanitizer; print('Security module OK')\""
    )
    run_command(
        "python -c \"from src.science_packs import get_total_pack_count; print(f'Science packs: {get_total_pack_count()}')\""
    )


def build_package():
    """Build the Python package."""
    print("\n=== Building Package ===")

    # Ensure build tools are installed
    run_command("pip install --upgrade build wheel")

    # Build the package
    os.chdir("src")
    success = run_command("python -m build")
    os.chdir("..")

    if success:
        print("\n=== Build Complete ===")
        # List built files
        dist_path = Path("src/dist")
        if dist_path.exists():
            print("\nBuilt packages:")
            for f in dist_path.iterdir():
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name} ({size_mb:.2f} MB)")
    else:
        print("\n!!! Build Failed !!!")
        return False

    return True


def install_package():
    """Install the built package."""
    print("\n=== Installing Package ===")

    wheel_files = list(Path("src/dist").glob("*.whl"))
    if wheel_files:
        latest_wheel = max(wheel_files, key=lambda p: p.stat().st_mtime)
        run_command(f"pip install {latest_wheel} --force-reinstall")
    else:
        print("No wheel file found, installing from source")
        run_command("pip install -e src/[all]")


def print_summary():
    """Print build summary."""
    print("\n" + "=" * 60)
    print("  SCBE-AETHERMOORE v3.1.0 Build Summary")
    print("=" * 60)

    # Count modules
    modules = {
        "symphonic_cipher": len(list(Path("src/symphonic_cipher").rglob("*.py"))),
        "physics_sim": len(list(Path("src/physics_sim").rglob("*.py"))),
        "ai_orchestration": len(list(Path("src/ai_orchestration").rglob("*.py"))),
        "science_packs": len(list(Path("src/science_packs").rglob("*.py"))),
    }

    print("\nModules:")
    for name, count in modules.items():
        print(f"  {name}: {count} files")

    print("\nFeatures:")
    print("  - 14-Layer Security Stack")
    print("  - Post-Quantum Cryptography (ML-KEM-768, ML-DSA)")
    print("  - AI Orchestration (6 agent types)")
    print("  - Prompt Injection Prevention (40+ patterns)")
    print("  - Physics Simulation Engine (9 modules)")
    print("  - Science Packs (29 knowledge modules)")
    print("  - Hash-Chained Audit Logging")
    print("  - Interactive Setup Assistant")

    print("\nInstallation:")
    print("  pip install src/dist/scbe_aethermoore-3.1.0-py3-none-any.whl")
    print("  # or")
    print("  pip install -e src/[all]")

    print("\nQuick Start:")
    print("  python -m ai_orchestration.setup_assistant")

    print("\n" + "=" * 60)


def main():
    args = sys.argv[1:]

    # Parse arguments
    do_test = "--test" in args
    do_clean = "--clean" in args
    do_install = "--install" in args

    print("=" * 60)
    print("  SCBE-AETHERMOORE Package Builder")
    print("=" * 60)

    # Change to project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    if do_clean:
        clean_build()

    if do_test:
        run_tests()

    if build_package():
        if do_install:
            install_package()
        print_summary()
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
