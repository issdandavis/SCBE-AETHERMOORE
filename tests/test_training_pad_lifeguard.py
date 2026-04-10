"""
Tests for src/training_pad/lifeguard.py
=======================================

Covers:
- Severity enum
- LifeGuardNote dataclass
- Pattern matching: SECURITY_PATTERNS, QUALITY_PATTERNS, PERF_PATTERNS
- LifeGuard.observe (pattern scanning + structure checks)
- LifeGuard.review_execution (error parsing + output checks)
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Prevent import chain: training_pad.__init__ -> pad -> sft_recorder -> training.auto_marker
# The auto_marker module may not exist; mock it before importing training_pad submodules.
if "training.auto_marker" not in sys.modules:
    sys.modules["training.auto_marker"] = MagicMock()

from training_pad.cell import Cell, CellStatus
from training_pad.lifeguard import (
    Severity,
    LifeGuardNote,
    SECURITY_PATTERNS,
    QUALITY_PATTERNS,
    PERF_PATTERNS,
    LifeGuard,
)


# ============================================================
# Severity Enum
# ============================================================

@pytest.mark.unit
class TestSeverity:
    def test_values(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARN.value == "warn"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"

    def test_four_levels(self):
        assert len(Severity) == 4


# ============================================================
# LifeGuardNote
# ============================================================

@pytest.mark.unit
class TestLifeGuardNote:
    def test_to_dict(self):
        note = LifeGuardNote(
            category="security",
            severity=Severity.CRITICAL,
            message="eval detected",
            line=5,
            suggestion="use ast.literal_eval()",
        )
        d = note.to_dict()
        assert d["severity"] == "critical"
        assert d["category"] == "security"
        assert d["line"] == 5

    def test_default_suggestion(self):
        note = LifeGuardNote(category="lint", severity=Severity.WARN, message="test")
        assert note.suggestion == ""

    def test_default_metadata(self):
        note = LifeGuardNote(category="lint", severity=Severity.WARN, message="test")
        assert note.metadata == {}


# ============================================================
# Pattern lists
# ============================================================

@pytest.mark.unit
class TestPatterns:
    def test_security_patterns_exist(self):
        assert len(SECURITY_PATTERNS) > 0

    def test_quality_patterns_exist(self):
        assert len(QUALITY_PATTERNS) > 0

    def test_perf_patterns_exist(self):
        assert len(PERF_PATTERNS) > 0

    def test_all_patterns_have_3_elements(self):
        for p in SECURITY_PATTERNS + QUALITY_PATTERNS + PERF_PATTERNS:
            assert len(p) == 3


# ============================================================
# LifeGuard.observe — security patterns
# ============================================================

@pytest.mark.unit
class TestObserveSecurity:
    def test_detects_eval(self):
        lg = LifeGuard()
        cell = Cell(code="result = eval(user_input)")
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0
        assert any("eval" in n.message.lower() for n in security)

    def test_detects_exec(self):
        lg = LifeGuard()
        cell = Cell(code="exec(code_string)")
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0

    def test_detects_os_system(self):
        lg = LifeGuard()
        cell = Cell(code='os.system("rm -rf /")')
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0

    def test_detects_hardcoded_secret(self):
        lg = LifeGuard()
        cell = Cell(code='api_key = "sk-abcdefghijklmnop"')
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0

    def test_detects_pickle_load(self):
        lg = LifeGuard()
        cell = Cell(code="data = pickle.load(f)")
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0

    def test_detects_sql_injection(self):
        lg = LifeGuard()
        cell = Cell(code='query = f"SELECT * FROM users WHERE id = {user_id}"')
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) > 0

    def test_security_notes_are_critical(self):
        lg = LifeGuard()
        cell = Cell(code="eval(x)")
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        for n in security:
            assert n.severity == Severity.CRITICAL

    def test_clean_code_no_security_notes(self):
        lg = LifeGuard()
        cell = Cell(code="x = 1 + 2\nprint(x)")
        notes = lg.observe(cell)
        security = [n for n in notes if n.category == "security"]
        assert len(security) == 0


# ============================================================
# LifeGuard.observe — quality patterns
# ============================================================

@pytest.mark.unit
class TestObserveQuality:
    def test_detects_bare_except(self):
        lg = LifeGuard()
        cell = Cell(code="try:\n    pass\nexcept:\n    pass")
        notes = lg.observe(cell)
        lint = [n for n in notes if n.category == "lint"]
        assert len(lint) > 0

    def test_detects_wildcard_import(self):
        lg = LifeGuard()
        cell = Cell(code="from os import *")
        notes = lg.observe(cell)
        lint = [n for n in notes if n.category == "lint"]
        assert len(lint) > 0

    def test_detects_todo(self):
        lg = LifeGuard()
        cell = Cell(code="x = 1  # TODO: fix this")
        notes = lg.observe(cell)
        lint = [n for n in notes if n.category == "lint"]
        assert len(lint) > 0

    def test_detects_type_equality(self):
        lg = LifeGuard()
        cell = Cell(code='if type(x) == int:')
        notes = lg.observe(cell)
        lint = [n for n in notes if n.category == "lint"]
        assert len(lint) > 0


# ============================================================
# LifeGuard.observe — performance patterns
# ============================================================

@pytest.mark.unit
class TestObservePerformance:
    def test_detects_range_len(self):
        lg = LifeGuard()
        cell = Cell(code="for i in range(len(items)):")
        notes = lg.observe(cell)
        perf = [n for n in notes if n.category == "performance"]
        assert len(perf) > 0

    def test_detects_time_sleep(self):
        lg = LifeGuard()
        cell = Cell(code="time.sleep(10)")
        notes = lg.observe(cell)
        perf = [n for n in notes if n.category == "performance"]
        assert len(perf) > 0


# ============================================================
# LifeGuard.observe — structure checks
# ============================================================

@pytest.mark.unit
class TestObserveStructure:
    def test_long_cell_warns(self):
        lg = LifeGuard()
        cell = Cell(code="\n".join(f"x_{i} = {i}" for i in range(250)))
        notes = lg.observe(cell)
        style = [n for n in notes if n.category == "style"]
        assert any("250" in n.message for n in style)

    def test_missing_docstring_noted(self):
        lg = LifeGuard()
        cell = Cell(
            language="python",
            code="def calculate(x, y):\n    return x + y"
        )
        notes = lg.observe(cell)
        style = [n for n in notes if n.category == "style"]
        assert any("docstring" in n.message.lower() for n in style)

    def test_private_function_no_docstring_warning(self):
        """Private functions (def _foo) should not trigger docstring warning."""
        lg = LifeGuard()
        cell = Cell(
            language="python",
            code="def _helper(x):\n    return x + 1"
        )
        notes = lg.observe(cell)
        style = [n for n in notes if "docstring" in n.message.lower()]
        assert len(style) == 0

    def test_empty_code_no_notes(self):
        lg = LifeGuard()
        cell = Cell(code="")
        notes = lg.observe(cell)
        assert len(notes) == 0

    def test_whitespace_only_no_notes(self):
        lg = LifeGuard()
        cell = Cell(code="   \n   \n   ")
        notes = lg.observe(cell)
        assert len(notes) == 0


# ============================================================
# LifeGuard.observe — records feedback on cell
# ============================================================

@pytest.mark.unit
class TestObserveFeedback:
    def test_feedback_recorded_on_cell(self):
        lg = LifeGuard()
        cell = Cell(code="eval(x)")
        notes = lg.observe(cell)
        assert len(cell.feedback) > 0

    def test_clean_code_no_feedback(self):
        lg = LifeGuard()
        cell = Cell(code="x = 1")
        notes = lg.observe(cell)
        assert len(cell.feedback) == 0


# ============================================================
# LifeGuard.review_execution
# ============================================================

@pytest.mark.unit
class TestReviewExecution:
    def test_module_not_found(self):
        lg = LifeGuard()
        cell = Cell(code="import foobar")
        notes = lg.review_execution(
            cell, stdout="", stderr="ModuleNotFoundError: No module named 'foobar'",
            success=False,
        )
        assert len(notes) > 0
        assert any("foobar" in n.message for n in notes)

    def test_syntax_error(self):
        lg = LifeGuard()
        cell = Cell(code="def foo(")
        notes = lg.review_execution(
            cell, stdout="", stderr="SyntaxError: unexpected EOF",
            success=False,
        )
        assert len(notes) > 0
        assert any("syntax" in n.message.lower() for n in notes)

    def test_type_error(self):
        lg = LifeGuard()
        cell = Cell(code="1 + 'a'")
        notes = lg.review_execution(
            cell, stdout="", stderr="TypeError: unsupported operand",
            success=False,
        )
        assert len(notes) > 0

    def test_name_error(self):
        lg = LifeGuard()
        cell = Cell(code="print(undefined_var)")
        notes = lg.review_execution(
            cell, stdout="",
            stderr="NameError: name 'undefined_var' is not defined",
            success=False,
        )
        assert len(notes) > 0
        assert any("undefined_var" in n.message for n in notes)

    def test_large_output_warning(self):
        lg = LifeGuard()
        cell = Cell(code="print('x' * 200000)")
        notes = lg.review_execution(
            cell, stdout="x" * 200_000, stderr="", success=True,
        )
        assert len(notes) > 0
        assert any("large output" in n.message.lower() for n in notes)

    def test_success_normal_output_no_notes(self):
        lg = LifeGuard()
        cell = Cell(code="print('hello')")
        notes = lg.review_execution(
            cell, stdout="hello", stderr="", success=True,
        )
        assert len(notes) == 0

    def test_failure_without_known_error_no_notes(self):
        lg = LifeGuard()
        cell = Cell(code="x")
        notes = lg.review_execution(
            cell, stdout="", stderr="SomeRandomError: oops",
            success=False,
        )
        assert len(notes) == 0

    def test_review_records_feedback(self):
        lg = LifeGuard()
        cell = Cell(code="import foobar")
        lg.review_execution(
            cell, stdout="",
            stderr="ModuleNotFoundError: No module named 'foobar'",
            success=False,
        )
        assert len(cell.feedback) > 0


# ============================================================
# Extra patterns
# ============================================================

@pytest.mark.unit
class TestExtraPatterns:
    def test_custom_pattern_detected(self):
        lg = LifeGuard(extra_patterns=[
            (r"DANGEROUS_CALL\(\)", "Custom dangerous call detected", "security"),
        ])
        cell = Cell(code="result = DANGEROUS_CALL()")
        notes = lg.observe(cell)
        assert any("Custom dangerous call" in n.message for n in notes)

    def test_line_number_reported(self):
        lg = LifeGuard()
        cell = Cell(code="x = 1\ny = 2\nresult = eval(z)")
        notes = lg.observe(cell)
        eval_notes = [n for n in notes if "eval" in n.message.lower()]
        assert len(eval_notes) > 0
        assert eval_notes[0].line == 3
