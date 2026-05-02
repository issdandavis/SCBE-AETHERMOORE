from __future__ import annotations

from scripts.eval.smoke_geoseal_coding_agent_hf import _ca_plan


def test_ca_plan_routes_abs_add_through_deterministic_tool_lane() -> None:
    result = _ca_plan("abs(a)+abs(b)")
    assert result["ok"] is True
    assert result["ops"] == ["abs", "abs", "add"]
    assert result["hex_sequence"] == ["0x09", "0x09", "0x00"]
    assert result["tool"] == "scbe_code.ca-plan"
