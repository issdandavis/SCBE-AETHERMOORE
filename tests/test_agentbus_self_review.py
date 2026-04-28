"""
Regression tests for scripts/system/agentbus_self_review.py.

Pins the source_outcomes recognition: when the research bus ships a complete
`source_outcomes` array (one entry per checked source, each with a status),
the analyzer must NOT flag silent_error or sources_vs_findings_ratio even
though `errors:[]` is empty and findings_count < sources_checked.

Without this, the analyzer false-positives against a bus that already fixed
the silent-drop problem by structuring outcomes per source (PR #1228).
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "system" / "agentbus_self_review.py"
spec = importlib.util.spec_from_file_location("agentbus_self_review", SCRIPT)
asr = importlib.util.module_from_spec(spec)
sys.modules["agentbus_self_review"] = asr
spec.loader.exec_module(asr)


def _research_with_outcomes():
    return {
        "sources_checked": 5,
        "findings": [{"confidence": 0.7}, {"confidence": 0.6}, {"confidence": 0.9}],
        "errors": [],
        "source_outcomes": [
            {"url": "https://a", "status": "matched", "score": 0.9, "reason": ""},
            {"url": "https://b", "status": "matched", "score": 0.8, "reason": ""},
            {"url": "https://c", "status": "matched", "score": 0.85, "reason": ""},
            {"url": "https://d", "status": "below_threshold", "score": 0.0, "reason": ""},
            {"url": "https://e", "status": "below_threshold", "score": 0.0, "reason": ""},
        ],
    }


def test_silent_error_clears_when_source_outcomes_complete():
    findings = asr.check_silent_error(_research_with_outcomes())
    assert findings == [], f"silent_error should clear with full source_outcomes, got {findings}"


def test_ratio_clears_when_source_outcomes_complete():
    findings = asr.check_sources_vs_findings(_research_with_outcomes())
    assert findings == [], f"ratio should clear with full source_outcomes, got {findings}"


def test_silent_error_still_fires_when_outcomes_missing():
    research = _research_with_outcomes()
    del research["source_outcomes"]
    findings = asr.check_silent_error(research)
    assert len(findings) == 1
    assert findings[0].category == "silent_error"


def test_silent_error_still_fires_when_outcomes_partial():
    research = _research_with_outcomes()
    research["source_outcomes"] = research["source_outcomes"][:3]
    findings = asr.check_silent_error(research)
    assert len(findings) == 1
    assert findings[0].category == "silent_error"


def test_silent_error_still_fires_when_status_missing_on_entry():
    research = _research_with_outcomes()
    research["source_outcomes"][0] = {"url": "https://a", "score": 0.9}
    findings = asr.check_silent_error(research)
    assert len(findings) == 1


def test_ratio_still_fires_when_outcomes_partial():
    research = _research_with_outcomes()
    research["source_outcomes"] = research["source_outcomes"][:2]
    findings = asr.check_sources_vs_findings(research)
    assert len(findings) == 1
    assert findings[0].category == "sources_vs_findings_ratio"
