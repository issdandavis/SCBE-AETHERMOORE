"""SCBE-AETHERMOORE single-file launcher.

This is the executable companion to docs/SCBE_AETHERMOORE_ONE_PAGER.md.
It is shipped as scripts/bootstrap/aethermoore.pyz — a Python zipapp
that runs anywhere Python 3.9+ is installed (no extra deps).

Behavior:
  python aethermoore.pyz            -> interactive menu
  python aethermoore.pyz pitch      -> print the one-pager (read-only)
  python aethermoore.pyz check      -> environment smoke check
  python aethermoore.pyz aetherdesk -> launch the operator shell
  python aethermoore.pyz paths      -> print canonical file pointers
  python aethermoore.pyz --help     -> show this help
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

LAUNCHER_VERSION = "0.1.0"

PITCH = textwrap.dedent("""
    SCBE-AETHERMOORE - one-paragraph pitch
    ======================================

    AI safety/governance framework that uses hyperbolic geometry
    (Poincare ball model) to make adversarial drift exponentially more
    expensive than legitimate use, while a 14-layer pipeline emits
    cryptographic receipts (GeoSeal) for every gate decision so auditors
    can replay months later.

    Three deployable surfaces:
      1. GeoSeal       — cryptographic receipts (aetherdesk_receipt_v0)
      2. AetherDesk    — local operator shell (npm run aetherdesk)
      3. Mechanical    — bijective compile-CA path: 64 tier-1 opcodes
                         compile to Python/TypeScript/Go without an LLM
                         call. Bench: 4-5x faster than local Ollama,
                         $0 vs Sonnet's projected per-call cost.

    Author: Issac Davis (Port Angeles, WA). SAM.gov UEI J4NXHM6N5F59
    ACTIVE through 2026-04-13. CAGE 1EXD5. DARPA CLARA + MATHBAC on
    file. Repo: github.com/issdandavis/SCBE-AETHERMOORE.

    Read the full one-pager: docs/SCBE_AETHERMOORE_ONE_PAGER.md
    """).strip()

PATHS = textwrap.dedent("""
    Canonical file pointers
    =======================
      Architecture overview     docs/LAYER_INDEX.md
                                docs/SYSTEM_ARCHITECTURE.md
      Canonical spec            docs/SPEC.md
      14-layer pipeline (TS)    src/harmonic/pipeline14.ts
      Harmonic wall             src/harmonic/harmonicScaling.ts
      Sacred Tongues (Python)   src/symphonic_cipher/scbe_aethermoore/
                                  axiom_grouped/langues_metric.py
      Mechanical coding CLI     scripts/agents/scbe_code.py
      AetherDesk operator shell aetherdesk/server.js
                                aetherdesk/public/index.html
      Mechanical-coding bench   scripts/benchmark/
                                  aetherdesk_mechanical_coding_bench.py
      Runnable book chapters    book/ai-governance-fundamentals/
                                  chapter-*.md
      Federal docs              docs/contracting/
                                docs/specs/ta1_mathematical_challenges_v1.md
    """).strip()

MENU = textwrap.dedent("""
    SCBE-AETHERMOORE launcher v{ver}
    --------------------------------
      [1] Read the one-paragraph pitch
      [2] Print canonical file pointers
      [3] Run environment smoke check
      [4] Launch AetherDesk operator shell (npm run aetherdesk)
      [Q] Quit
    """)


def _is_scbe_root(d: Path) -> bool:
    pkg = d / "package.json"
    if not pkg.exists():
        return False
    try:
        return '"scbe-aethermoore"' in pkg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _project_root() -> Path:
    """Best-effort project root detection.

    The .pyz can be moved anywhere, so we walk up from cwd looking for
    a package.json whose name is "scbe-aethermoore". Falls back to cwd.
    """
    here = Path.cwd().resolve()
    for parent in [here, *here.parents]:
        if _is_scbe_root(parent):
            return parent
    return here


def cmd_pitch(_args) -> int:
    print(PITCH)
    return 0


def cmd_paths(_args) -> int:
    print(PATHS)
    return 0


def cmd_check(_args) -> int:
    print(f"SCBE-AETHERMOORE launcher v{LAUNCHER_VERSION}")
    print()
    py = sys.version_info
    py_ok = py >= (3, 9)
    print(f"  python      {py.major}.{py.minor}.{py.micro:<3}  {'OK' if py_ok else 'NEED >= 3.9'}")

    node = shutil.which("node")
    if node:
        try:
            v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=5)
            print(f"  node        {v.stdout.strip():<7}  found at {node}")
        except Exception as exc:
            print(f"  node        ?       found but failed: {exc}")
    else:
        print("  node        --      MISSING (needed for AetherDesk)")

    npm = shutil.which("npm")
    if npm:
        try:
            v = subprocess.run([npm, "--version"], capture_output=True, text=True, timeout=5)
            print(f"  npm         {v.stdout.strip():<7}  found at {npm}")
        except Exception as exc:
            print(f"  npm         ?       found but failed: {exc}")
    else:
        print("  npm         --      MISSING (needed for AetherDesk)")

    root = _project_root()
    here_ok = _is_scbe_root(root)
    print()
    print(f"  Project root detected: {root}")
    print(f"  SCBE-AETHERMOORE root: {'OK' if here_ok else 'NOT FOUND (run from inside the repo)'}")

    return 0 if (py_ok and here_ok) else 1


def cmd_aetherdesk(_args) -> int:
    npm = shutil.which("npm")
    if not npm:
        print("npm not found — install Node 18+ first.", file=sys.stderr)
        return 2
    root = _project_root()
    if not (root / "package.json").exists():
        print(f"no package.json at {root} — cd into the repo first.", file=sys.stderr)
        return 2
    print(f"launching AetherDesk via `npm run aetherdesk` in {root}")
    print("(open http://127.0.0.1:5717 in a browser; Ctrl+C to stop)")
    try:
        return subprocess.call([npm, "run", "aetherdesk"], cwd=str(root))
    except KeyboardInterrupt:
        return 130


def cmd_menu(_args) -> int:
    while True:
        print(MENU.format(ver=LAUNCHER_VERSION))
        try:
            choice = input("choice> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if choice in {"q", "quit", "exit"}:
            return 0
        if choice == "1":
            cmd_pitch(None)
        elif choice == "2":
            cmd_paths(None)
        elif choice == "3":
            cmd_check(None)
        elif choice == "4":
            return cmd_aetherdesk(None)
        else:
            print(f"unknown choice: {choice!r}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="aethermoore.pyz",
        description="SCBE-AETHERMOORE single-file launcher.",
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("pitch", help="print the one-paragraph pitch")
    sub.add_parser("paths", help="print canonical file pointers")
    sub.add_parser("check", help="environment smoke check")
    sub.add_parser("aetherdesk", help="launch AetherDesk operator shell")
    sub.add_parser("menu", help="interactive menu (default)")
    args = parser.parse_args(argv)

    handlers = {
        None: cmd_menu,
        "menu": cmd_menu,
        "pitch": cmd_pitch,
        "paths": cmd_paths,
        "check": cmd_check,
        "aetherdesk": cmd_aetherdesk,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
