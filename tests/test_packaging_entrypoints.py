"""Every declared console script must import. This is the test that was missing.

Published 4.2.1 shipped FOUR broken console scripts. `pip install scbe-aethermoore` succeeded,
then the first command in the README -- `scbe-scan "hello world"` -- died with
`ModuleNotFoundError: No module named 'scbe_aethermoore'`. The wheel contained only `scbe.py`
and a directory literally named `python/`; none of the src-layout packages were included.

Nothing in CI noticed, because the test suite imports modules from the SOURCE TREE, where they
all resolve. A source-tree import test can never see a packaging bug -- the whole failure lives
in the gap between "the code exists" and "the code is shipped".

So this test reads the declared entry points out of pyproject.toml and checks that each target
module is importable and each callable actually exists. It is deliberately cheap: no build, no
venv, no network. It would not have caught the 4.2.1 wheel by itself (the modules import fine
from source), which is why `scripts/check_wheel_entrypoints.py` exists as the companion that
builds a wheel and installs it clean.

What this one DOES catch, and what it caught on 2026-07-27: an entry point naming a module that
is excluded from packaging. `scbe-system` pointed at `scripts.scbe_system_cli`, and `scripts*`
is in SRC_EXCLUDE, so the command could never work once installed no matter how the wheel was
built.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
SETUP_PY = ROOT / "setup.py"


def _declared_scripts() -> list[tuple[str, str]]:
    """[(command, "module:callable")] from pyproject's [project.scripts].

    Line-based rather than a single regex. The first version used
    `^\\[project\\.scripts\\]\\s*$(.*?)^\\[` and matched nothing, because `\\s*` is greedy and
    swallowed the newline, leaving `$` with nowhere to match. Walking lines is both correct
    and obvious, and a parsing bug here would silently turn this whole file into a no-op --
    which is why test_at_least_one_script_declared exists below.
    """
    out: list[tuple[str, str]] = []
    inside = False
    for raw in PYPROJECT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            inside = line == "[project.scripts]"
            continue
        if not inside or not line or line.startswith("#"):
            continue
        m = re.match(r'^([\w.-]+)\s*=\s*"([^"]+)"', line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def _packaging_excludes() -> list[str]:
    """SRC_EXCLUDE patterns from setup.py — modules these match are never shipped."""
    text = SETUP_PY.read_text(encoding="utf-8")
    block = re.search(r"SRC_EXCLUDE\s*=\s*\[(.*?)\]", text, re.S)
    if not block:
        return []
    return re.findall(r'"([^"]+)"', block.group(1))


def test_at_least_one_script_declared():
    assert _declared_scripts(), "no [project.scripts] found — parsing is wrong, not the config"


@pytest.mark.parametrize("command,target", _declared_scripts())
def test_entry_point_target_is_importable(command, target):
    """The module resolves and the callable exists."""
    module_name, _, func_name = target.partition(":")
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - the failure message is the point
        pytest.fail(
            f"console script {command!r} targets {module_name!r}, which does not import: "
            f"{type(exc).__name__}: {exc}"
        )
    assert hasattr(module, func_name), (
        f"console script {command!r} targets {target!r} but {module_name} has no {func_name!r}"
    )


@pytest.mark.parametrize("command,target", _declared_scripts())
def test_entry_point_module_is_actually_packaged(command, target):
    """An entry point must not name a module that packaging excludes.

    This is the check that would have caught `scbe-system = "scripts.scbe_system_cli:main"`:
    it imports fine from the repo, and is unreachable once installed.
    """
    top = target.partition(":")[0].split(".")[0]
    for pattern in _packaging_excludes():
        base = pattern.rstrip("*").rstrip(".")
        if base and top == base:
            pytest.fail(
                f"console script {command!r} targets top-level {top!r}, but setup.py "
                f"SRC_EXCLUDE contains {pattern!r} — the module is not shipped, so the "
                "installed command will raise ModuleNotFoundError. Either package it or "
                "drop the entry point."
            )
    # a shipped module must live under src/ or be the root scbe.py module
    if top != "scbe" and not (ROOT / "src" / top).exists():
        pytest.fail(
            f"console script {command!r} targets top-level {top!r}, which is not under src/ "
            "and is not the root scbe module — it will not be in the wheel."
        )
