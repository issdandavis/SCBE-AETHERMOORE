"""The PyInstaller spec must bundle every src/ package that scbe.py imports.

`scbe.py` reaches its dependencies through a RUNTIME shim:

    SRC_ROOT = REPO_ROOT / "src"
    if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from scbe_aethermoore import _intent_screen

That works from a checkout and fails twice over in a frozen binary:

  * PyInstaller's Analysis is STATIC. It cannot follow a computed `sys.path.insert`, so
    with `pathex=['.']` it never found the package and never froze it in.
  * The shim cannot rescue it at runtime either — in a frozen app `Path(__file__).parent`
    is the extraction directory, so `REPO_ROOT/src` does not exist and the insert is a
    no-op.

Result: every released binary died on its first command with
`ModuleNotFoundError: No module named 'scbe_aethermoore'`. build-binaries had never once
succeeded across its whole run history, so nothing flagged it.

The fix needs BOTH `'src'` on pathex and a `collect_submodules` call, and this test checks
both — a spec with one and not the other still produces a broken binary.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "scbe.spec"
ENTRY = ROOT / "scbe.py"


def _spec_code() -> str:
    """scbe.spec with comments stripped.

    Necessary because this file's own comments quote the broken configuration verbatim
    (`pathex=['.']`) to explain it. The first version regexed the raw text, matched the
    comment instead of the real assignment, and failed against a correct spec — the
    explanation of the bug reproduced the bug.
    """
    out = []
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(line.split("  #", 1)[0])
    return "\n".join(out)


def _src_packages() -> set[str]:
    return {p.name for p in (ROOT / "src").iterdir() if (p / "__init__.py").exists()}


def _entry_imports_from_src() -> set[str]:
    """Top-level packages scbe.py imports that live under src/.

    Regex rather than `ast` on purpose: the point is what the FROZEN entry script
    references, and a plain scan cannot be fooled by the import sitting after a
    conditional sys.path mutation the way an importability check could.
    """
    text = ENTRY.read_text(encoding="utf-8")
    found = set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
    return found & _src_packages()


def test_entry_actually_imports_something_from_src():
    """Guards the guard: if this returns nothing, the checks below are vacuous."""
    assert _entry_imports_from_src(), "parsed no src/ imports out of scbe.py — the regex is wrong, not the spec"


def test_spec_puts_src_on_pathex():
    spec = _spec_code()
    m = re.search(r"pathex\s*=\s*\[([^\]]*)\]", spec)
    assert m, "no pathex in scbe.spec"
    entries = {e.strip().strip("\"'") for e in m.group(1).split(",") if e.strip()}
    assert "src" in entries, (
        f"scbe.spec pathex is {sorted(entries)} — without 'src', PyInstaller cannot resolve "
        "the packages scbe.py imports and silently builds a binary that dies on startup"
    )


@pytest.mark.parametrize("pkg", sorted(_entry_imports_from_src()))
def test_spec_collects_each_imported_src_package(pkg):
    spec = _spec_code()
    collected = set(re.findall(r"collect_submodules\(\s*['\"]([A-Za-z0-9_.]+)['\"]", spec))
    tops = {c.split(".")[0] for c in collected}
    assert pkg in tops, (
        f"scbe.py imports {pkg!r} from src/, but scbe.spec never collects it. The frozen "
        f"binary will raise ModuleNotFoundError: No module named '{pkg}'. Add "
        f"hiddenimports += collect_submodules({pkg!r})"
    )
