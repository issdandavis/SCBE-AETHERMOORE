"""MANIFEST.in must physically ship every package setup.py declares.

The two files answer different questions and nothing forced them to agree:

    setup.py      what the WHEEL DECLARES  (find_packages over src/)
    MANIFEST.in   what the SDIST CONTAINS  (recursive-include lines)

`python -m build` — which is what .github/workflows/pypi-publish.yml runs — builds the
sdist first and then builds the wheel FROM THAT SDIST. So a package declared in setup.py
but absent from MANIFEST.in is declared and not shipped: pip installs it happily, then
every import raises ModuleNotFoundError.

That is exactly what shipped as 4.2.1, twice over:

  1. `recursive-exclude src *.egg-info *` — the trailing bare `*` is a catch-all that
     matched every file under src/, deleting all ten packages from the sdist.
  2. Even with that fixed, `scbe_aethermoore` and `neurogolf` were never in the include
     list at all.

Building a wheel straight from the tree (`pip wheel .`, `python -m build --wheel`) hides
both, because that path never consults MANIFEST.in. The bug only appears on the release
path — which is the one path nobody runs by hand.
"""

from __future__ import annotations

import re
from pathlib import Path

from setuptools import find_packages

ROOT = Path(__file__).resolve().parents[1]


def _setup_py_globals() -> dict:
    """SRC_INCLUDE / SRC_EXCLUDE straight out of setup.py, without importing it.

    Importing setup.py executes setup(), which would try to parse pytest's argv.
    """
    text = (ROOT / "setup.py").read_text(encoding="utf-8")
    out = {}
    for name in ("SRC_INCLUDE", "SRC_EXCLUDE"):
        m = re.search(rf"^{name}\s*=\s*\[(.*?)\]", text, re.S | re.M)
        assert m, f"{name} not found in setup.py"
        out[name] = re.findall(r'"([^"]+)"', m.group(1))
    return out


def _declared_top_level() -> set[str]:
    g = _setup_py_globals()
    pkgs = find_packages(str(ROOT / "src"), include=g["SRC_INCLUDE"], exclude=g["SRC_EXCLUDE"])
    return {p.split(".")[0] for p in pkgs}


def _manifest_text() -> str:
    return (ROOT / "MANIFEST.in").read_text(encoding="utf-8")


def _manifest_included() -> set[str]:
    return set(re.findall(r"^recursive-include\s+src/([A-Za-z0-9_]+)", _manifest_text(), re.M))


def test_manifest_includes_every_declared_package():
    declared, included = _declared_top_level(), _manifest_included()
    missing = declared - included
    assert not missing, (
        f"setup.py declares {sorted(missing)} but MANIFEST.in has no "
        f"`recursive-include src/<pkg> *.py` for them — they will be declared in the wheel "
        "and absent from it, so the installed package raises ModuleNotFoundError"
    )


def test_manifest_has_no_catch_all_exclude_over_src():
    """A bare `*` pattern on a recursive-exclude of src wipes out every package.

    `recursive-exclude src *.egg-info *` reads like it excludes egg-info; the trailing
    token is a separate pattern matching everything.
    """
    for line in _manifest_text().splitlines():
        line = line.strip()
        if not line.startswith("recursive-exclude"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        directory, patterns = parts[1], parts[2:]
        if directory.rstrip("/") == "src" and "*" in patterns:
            raise AssertionError(
                f"MANIFEST.in line {line!r} contains a bare '*' pattern over src/ — this "
                "excludes every source file from the sdist and produces an empty wheel"
            )
