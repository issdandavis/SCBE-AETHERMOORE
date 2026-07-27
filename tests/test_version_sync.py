"""Every place that declares a version must agree.

Caught at 4.3.0 release time: pyproject.toml said 4.3.0 and
src/scbe_aethermoore/__init__.py said 3.3.0. A wheel built from that installs as 4.3.0
while `scbe-scan --version` and `scbe_aethermoore.__version__` both report 3.3.0 — and
3.3.0 is a real prior release, so nothing looks broken; it just quietly disagrees with
itself. PyPI forbids re-uploading a version, so shipping it means burning the number and
releasing 4.3.1 to fix a string.

package.json is included because the repo publishes to npm and PyPI from the same tag.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def _dunder_version() -> str:
    # Parsed, not imported: importing pulls in the whole package (and numpy), which is a
    # lot of machinery to read one string literal, and it would mask a syntax error here
    # as an unrelated import failure.
    text = (ROOT / "src" / "scbe_aethermoore" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    assert m, "no __version__ found in src/scbe_aethermoore/__init__.py"
    return m.group(1)


def test_package_dunder_matches_pyproject():
    assert _dunder_version() == _pyproject_version(), (
        f"__version__ is {_dunder_version()!r} but pyproject.toml declares "
        f"{_pyproject_version()!r} — the installed package would misreport its own version"
    )


def test_npm_version_matches_pyproject():
    npm = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    assert npm == _pyproject_version(), (
        f"package.json is {npm!r} but pyproject.toml declares {_pyproject_version()!r} — "
        "both publish from the same tag, so they must agree"
    )


def test_version_is_pep440_release():
    """A release version, not a dev/local marker that PyPI would reject or sort oddly."""
    assert re.fullmatch(
        r"\d+\.\d+\.\d+", _pyproject_version()
    ), f"{_pyproject_version()!r} is not a plain X.Y.Z release version"
