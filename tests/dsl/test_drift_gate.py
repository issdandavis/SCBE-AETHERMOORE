"""Smoke tests for the DSL primitive drift check in
`scripts/eval/lexicon_dimension_report.py`.

Per L_dsl_synthesis Phase 2: the gate must
  1. detect the canonical 8 primitives in PRIMITIVE_TABLE,
  2. fail when a primitive is missing, and
  3. fail when an extra primitive appears.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "_lexgate_under_test",
    ROOT / "scripts" / "eval" / "lexicon_dimension_report.py",
)
_lexgate = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules["_lexgate_under_test"] = _lexgate
_SPEC.loader.exec_module(_lexgate)


def test_canonical_reference_has_eight():
    assert len(_lexgate.DSL_PRIMITIVES_REFERENCE) == 8


def test_parse_dsl_primitives_finds_canonical_set():
    found = _lexgate.parse_dsl_primitives(_lexgate.DSL_PRIMITIVES_FILE)
    assert found == set(_lexgate.DSL_PRIMITIVES_REFERENCE)


def test_diff_clean_when_canonical():
    findings: list = []
    _lexgate.diff_dsl_primitives(set(_lexgate.DSL_PRIMITIVES_REFERENCE), findings)
    assert findings == []


def test_diff_fails_on_missing(tmp_path):
    found = set(_lexgate.DSL_PRIMITIVES_REFERENCE) - {"seal"}
    findings: list = []
    _lexgate.diff_dsl_primitives(found, findings)
    assert any(f.severity == "fail" and f.expected == "seal" for f in findings)


def test_diff_fails_on_extra():
    found = set(_lexgate.DSL_PRIMITIVES_REFERENCE) | {"unauthorized_op"}
    findings: list = []
    _lexgate.diff_dsl_primitives(found, findings)
    assert any(f.severity == "fail" and f.found == "unauthorized_op" for f in findings)


def test_parse_dsl_primitives_reads_synthetic_block(tmp_path):
    """Regex must locate keys inside a PRIMITIVE_TABLE = { ... } literal."""
    fake = tmp_path / "fake_primitives.py"
    fake.write_text(
        textwrap.dedent(
            '''
            from typing import Callable, Dict
            PRIMITIVE_TABLE: Dict[str, Callable] = {
                "alpha": object,
                "beta": object,
                "gamma_op": object,
            }
            '''
        ),
        encoding="utf-8",
    )
    assert _lexgate.parse_dsl_primitives(fake) == {"alpha", "beta", "gamma_op"}
