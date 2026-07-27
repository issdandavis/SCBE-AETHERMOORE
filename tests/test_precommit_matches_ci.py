"""The pre-commit hook must run the same checks CI runs.

A local hook that checks *less* than CI is worse than no hook: it returns green, you
commit, and main goes red anyway — so you learn to distrust the hook and start passing
--no-verify. Both red builds in this repo on 2026-07-27 came from exactly that gap. black
was clean each time; CI also runs flake8, which found an F841 unused local, and the
whitespace gate, which found trailing \\r from a merge resolution.

So this file pins the hook to the workflows. If someone tightens CI, this fails until the
hook is tightened too.

Note the asymmetry it protects: black covers src/ tests/ scripts/ agents/, while flake8
also covers hydra/. "I ran black" is not the same statement as "CI will pass."
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "pre-commit"
WORKFLOWS = ROOT / ".github" / "workflows"


def _ci_commands() -> list[str]:
    out: list[str] = []
    for wf in WORKFLOWS.glob("*.yml"):
        for m in re.finditer(r"^\s*run:\s*(.+)$", wf.read_text(encoding="utf-8"), re.M):
            line = m.group(1).strip()
            if re.match(r"^(python -m )?(black|flake8|ruff)\b", line):
                out.append(line)
    return out


def test_ci_actually_runs_these_linters():
    """Guards the guard — if this finds nothing, every assertion below is vacuous."""
    cmds = _ci_commands()
    assert cmds, "parsed no black/flake8/ruff commands out of .github/workflows"


@pytest.mark.parametrize("tool", ["black", "flake8", "ruff"])
def test_hook_runs_every_linter_ci_runs(tool):
    ci = [c for c in _ci_commands() if re.match(rf"^(python -m )?{tool}\b", c)]
    if not ci:
        pytest.skip(f"CI does not run {tool}")
    hook = HOOK.read_text(encoding="utf-8")
    assert tool in hook, (
        f"CI runs {tool} ({ci[0]!r}) but scripts/hooks/pre-commit never invokes it — "
        "the hook would pass while CI fails"
    )


def test_hook_uses_the_same_line_length_as_ci():
    """A hook formatting at a different width would fight CI on every commit."""
    hook = HOOK.read_text(encoding="utf-8")
    ci_widths = set(re.findall(r"--(?:max-)?line-length[= ](\d+)", " ".join(_ci_commands())))
    hook_widths = set(re.findall(r'"(\d{2,3})"', hook)) | set(re.findall(r"--(?:max-)?line-length[= ](\d+)", hook))
    assert ci_widths, "no line-length found in CI commands"
    assert ci_widths <= hook_widths, f"CI uses line-length {ci_widths}, hook uses {hook_widths}"


def test_hook_covers_every_directory_ci_lints():
    """flake8 lints hydra/ and black does not; the hook must cover the union, not one of them."""
    hook = HOOK.read_text(encoding="utf-8")
    ci_dirs: set[str] = set()
    for cmd in _ci_commands():
        ci_dirs |= {d for d in re.findall(r"\b([a-z_]+)/(?=\s|$)", cmd)}
    missing = {d for d in ci_dirs if f'"{d}/"' not in hook}
    assert not missing, (
        f"CI lints {sorted(missing)} but the hook's LINTED_DIRS omits them — "
        "staged files there would skip the hook and fail CI"
    )


def test_black_version_is_pinned_in_ci():
    """Formatters disagree across versions; an unpinned CI black reformats on its own schedule."""
    text = " ".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
    assert re.search(r"black==\d+\.\d+", text), "CI installs black unpinned — local and CI will drift"
