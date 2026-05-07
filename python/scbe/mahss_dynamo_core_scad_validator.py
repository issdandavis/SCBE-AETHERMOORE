"""Structural validator for the crypto-seeded Dynamo Core ``.scad`` output.

This is NOT a full OpenSCAD parser — it does not verify that the
geometry renders, that the modules produce a valid manifold, or that
the auxetic sheath compiles to a non-empty STL. It DOES catch the
failure modes the Python emitter could realistically introduce:

1. Unmatched braces / parentheses / brackets (from typos or future edits).
2. Perturb table length mismatch with ``num_ridges``.
3. Seed decimal/hex inconsistency (the `seed = N; // hex H` line).
4. Required top-level constants and modules missing from the source.
5. Out-of-range perturb values (exceed the documented physical bound).

When OpenSCAD itself is on the box, prefer ``openscad --check file.scad``
over this — that is the rigorous validation. This module is the cheap
"did the emitter produce something coherent" gate that runs offline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScadValidation:
    path: str | None = None
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


_BRACE_PAIRS = {"{": "}", "(": ")", "[": "]"}
_OPENERS = set(_BRACE_PAIRS.keys())
_CLOSERS = {v: k for k, v in _BRACE_PAIRS.items()}


def _strip_comments(src: str) -> str:
    """Remove // line comments and /* ... */ block comments. OpenSCAD's
    rules match C/C++."""

    # Block comments first (non-greedy)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    # Line comments
    src = re.sub(r"//[^\n]*", "", src)
    return src


def _check_balance(src: str, result: ScadValidation) -> None:
    """Walk the source (comments stripped, strings respected) and verify
    every opener has a matching closer in LIFO order."""

    stack: list[tuple[str, int, int]] = []  # (char, line, col)
    line, col = 1, 0
    in_string = False
    escape = False
    for ch in src:
        col += 1
        if ch == "\n":
            line += 1
            col = 0
            in_string = False  # OpenSCAD strings don't span lines
            escape = False
            continue
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in _OPENERS:
            stack.append((ch, line, col))
        elif ch in _CLOSERS:
            if not stack:
                result.fail(f"unmatched {ch!r} at line {line} col {col}")
                return
            opener, oline, ocol = stack.pop()
            expected = _BRACE_PAIRS[opener]
            if ch != expected:
                result.fail(
                    f"mismatched bracket: opened {opener!r} at line {oline} "
                    f"col {ocol}, but found {ch!r} at line {line} col {col}"
                )
                return
    for opener, oline, ocol in stack:
        result.fail(f"unclosed {opener!r} at line {oline} col {ocol}")


_REQUIRED_CONSTANTS = ("phi", "golden_angle", "R_tung", "t_sheath", "r_throat", "c_z", "num_ridges", "mesh_height", "seed", "perturb_mm")
_REQUIRED_MODULES = ("seeded_hyperbolic_ridge", "auxetic_sheath")


def validate_dynamo_core_scad(source: str, *, path: str | None = None) -> ScadValidation:
    """Run all structural checks on the .scad source string.

    Returns a :class:`ScadValidation` whose ``ok`` flag is False if any
    error fired. Warnings do not fail validation but surface things the
    OpenSCAD parser would also flag (e.g. unused declarations)."""

    result = ScadValidation(path=path)
    stripped = _strip_comments(source)
    _check_balance(stripped, result)
    if not result.ok:
        return result

    # Required constants and modules
    for name in _REQUIRED_CONSTANTS:
        if not re.search(rf"\b{re.escape(name)}\s*=", stripped):
            result.fail(f"missing required top-level constant {name!r}")
    for name in _REQUIRED_MODULES:
        if not re.search(rf"\bmodule\s+{re.escape(name)}\b", stripped):
            result.fail(f"missing required module {name!r}")

    # Perturb table length must equal num_ridges
    nrm = re.search(r"\bnum_ridges\s*=\s*(\d+)\s*;", stripped)
    pmm = re.search(r"\bperturb_mm\s*=\s*\[([^\]]+)\];", stripped)
    if nrm and pmm:
        n = int(nrm.group(1))
        values = [v.strip() for v in pmm.group(1).split(",") if v.strip()]
        result.facts["num_ridges"] = n
        result.facts["perturb_table_length"] = len(values)
        if len(values) != n:
            result.fail(
                f"perturb_mm length {len(values)} does not match "
                f"num_ridges = {n}"
            )
        # Parse perturb values; each must be a finite float
        try:
            parsed = [float(v) for v in values]
            result.facts["perturb_max_abs_mm"] = max(abs(v) for v in parsed) if parsed else 0.0
        except ValueError as exc:
            result.fail(f"perturb_mm contains non-numeric value: {exc}")
            parsed = []
        # Sanity: at perturb_scale_mm=0.5 and bound=0.05 the absolute cap
        # is 0.025 mm. Allow slack for non-default scales but flag values
        # over 1 mm — those would print visibly wrong.
        if parsed and any(abs(v) > 1.0 for v in parsed):
            result.warn("perturb_mm contains values > 1 mm — confirm perturb_scale_mm intentionally large")

    # seed decimal must equal int(seed_hex, 16)
    sm = re.search(r"\bseed\s*=\s*(\d+)\s*;\s*//\s*hex\s+([0-9a-fA-F]+)", source)
    if sm:
        seed_dec = int(sm.group(1))
        seed_hex = int(sm.group(2), 16)
        result.facts["seed_decimal"] = seed_dec
        result.facts["seed_hex"] = sm.group(2)
        if seed_dec != seed_hex:
            result.fail(
                f"seed decimal {seed_dec} != hex {sm.group(2)} ({seed_hex}); "
                "emitter is producing inconsistent values"
            )

    # Top-level call to auxetic_sheath() and the difference() block
    if "color(\"Red\") auxetic_sheath();" not in source and "auxetic_sheath()" not in source:
        result.fail("auxetic_sheath() never invoked at top level")
    if "difference()" not in source:
        result.fail("top-level difference() block missing — geometry would be empty")
    # The difference must contain at least one cylinder (the tungsten shell)
    if "cylinder(" not in stripped:
        result.fail("no cylinder() primitive found — tungsten shell missing")

    return result


def validate_scad_file(path: Path) -> ScadValidation:
    """Convenience: read a file and validate it."""

    p = Path(path)
    if not p.exists():
        return ScadValidation(path=str(p), ok=False, errors=[f"file not found: {p}"])
    return validate_dynamo_core_scad(p.read_text(encoding="utf-8"), path=str(p))
