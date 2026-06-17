"""Forced 'show thinking' mode for `scbe ask --think`.

Tested without a live API call: the request-body builder and the response parser
are pure functions. This proves (a) think=True forces adaptive thinking with
display:summarized + effort (the 2026 mechanism — budget_tokens is rejected on
Opus 4.7/4.8 and thinking.display defaults to "omitted"), and (b) the parser
surfaces the reasoning instead of dropping it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scbe  # noqa: E402


def test_body_without_think_is_plain() -> None:
    body = scbe._anthropic_body("hi", None, think=False)
    assert "thinking" not in body
    assert "output_config" not in body
    assert body["max_tokens"] == 1024


def test_body_with_think_forces_visible_adaptive_thinking() -> None:
    body = scbe._anthropic_body("hi", None, think=True)
    # adaptive (not budget_tokens) + display:summarized is what makes reasoning VISIBLE
    assert body["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert body["output_config"]["effort"] == "high"
    assert body["max_tokens"] > 1024  # thinking shares the budget; needs room


def test_extract_without_think_returns_answer_only() -> None:
    data = {"content": [{"type": "thinking", "thinking": "secret"}, {"type": "text", "text": "42"}]}
    assert scbe._anthropic_extract(data, think=False) == "42"


def test_extract_with_think_surfaces_reasoning() -> None:
    data = {"content": [{"type": "thinking", "thinking": "step 1; step 2"}, {"type": "text", "text": "42"}]}
    out = scbe._anthropic_extract(data, think=True)
    assert "[thinking]" in out and "step 1; step 2" in out and "42" in out


def test_extract_with_think_handles_omitted_empty_thinking() -> None:
    # Latest models default display:"omitted" -> thinking block present but empty.
    data = {"content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": "42"}]}
    out = scbe._anthropic_extract(data, think=True)
    assert "42" in out and "none surfaced" in out
