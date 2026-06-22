"""Offline tests for universal_port (no model, no network, no MCP SDK needed).

Proves the missing layer: the four DEFAULT modalities normalize correctly (text/audio/visual/agentic),
audio/visual are honest when no backend is wired, the permission gate refuses destructive input, an
agentic call is governed + sealed, and the SAME registry is reachable over every transport (api/mcp/http).
"""

from __future__ import annotations

from python.helm.tool_trajectory import _safe_calc
from python.scbe.universal_port import AGENTIC, AUDIO, TEXT, VISUAL, Envelope, UniversalPort, tool_action


def _port() -> UniversalPort:
    p = UniversalPort()
    p.register_tool(
        tool_action(
            "calc",
            "evaluate arithmetic",
            lambda d: _safe_calc(str(d.get("expr", ""))),
            params={"expr": "string"},
        )
    )
    return p


# ---- modality adapters (the default inputs) ----------------------------------------------------
def test_text_modality_normalizes_and_routes():
    out = _port().handle(Envelope(TEXT, "Classify the number 91 by its prime structure."))
    assert out["decision"] == "ROUTED" and out["route"] == "classify" and out["modality"] == TEXT


def test_audio_predecoded_payload_routes_without_a_backend():
    out = _port().handle(Envelope(AUDIO, {"transcript": "Classify the number 7 by its prime structure."}))
    assert out["decision"] == "ROUTED" and out["route"] == "classify"


def test_audio_without_backend_is_honest_not_fabricated():
    out = _port().handle(Envelope(AUDIO, {"bytes": "<raw audio>"}))
    assert out["decision"] == "NEEDS_BACKEND" and out["detail"]["needs_backend"] == AUDIO


def test_wired_backend_is_used():
    p = _port()
    p.register_backend(AUDIO, lambda _raw: "Classify the number 13 by its prime structure.")
    out = p.handle(Envelope(AUDIO, b"<raw audio bytes>"))
    assert out["decision"] == "ROUTED" and out["route"] == "classify"


def test_visual_ocr_payload_routes():
    out = _port().handle(Envelope(VISUAL, {"ocr": "What is the capital of France?"}))
    assert out["decision"] == "ROUTED" and out["route"] == "judge"


# ---- governance: the gate decides, not the model ----------------------------------------------
def test_destructive_text_is_refused_at_the_gate():
    out = _port().handle(Envelope(TEXT, "delete all the files in my home directory"))
    assert out["decision"] == "REFUSED" and out["reason"] == "permission"


# ---- agentic direct tool call: governed + sealed ----------------------------------------------
def test_agentic_call_is_governed_and_sealed():
    out = _port().handle(Envelope(AGENTIC, {"tool": "calc", "args": {"expr": "6*7"}}))
    assert out["route"] == AGENTIC and out["decision"] == "ALLOWED"
    assert out["result"] == "42" and isinstance(out["seal"], str) and out["seal"]


def test_agentic_unknown_tool_is_not_fabricated():
    out = _port().handle(Envelope(AGENTIC, {"tool": "nope", "args": {}}))
    assert out["decision"] == "NO_ACTION"


# ---- execute path (deterministic executor, no real model) -------------------------------------
def test_execute_path_runs_deterministic_classify_backend():
    # an `ask` is present so handle() executes; classify uses the sieve (no model call) -> exact answer
    p = UniversalPort(ask=lambda _prompt: "")
    out = p.handle(Envelope(TEXT, "Classify the number 91 by its prime structure."))
    assert out["decision"] == "OK" and out["result"] == "composite"


# ---- multi-port: one registry, many transports -------------------------------------------------
def test_one_registry_reachable_over_every_transport():
    p = _port()
    # in-process API
    rec = p.call("calc", {"expr": "2+2"})
    assert rec["decision"] == "ALLOWED" and rec["result"] == "4"
    # MCP surface lists the tool + the universal meta-tool
    mcp_names = [t["name"] for t in p.mcp_tools()]
    assert "calc" in mcp_names and "universal_handle" in mcp_names
    # HTTP surface has a route for the tool + the /handle endpoint
    paths = [r["path"] for r in p.http_routes()]
    assert "/tool/calc" in paths and "/handle" in paths
    # the manifest ties them together over the SAME registry
    t = p.transports()
    assert set(t["modalities"]) >= {TEXT, AUDIO, VISUAL, AGENTIC}
    assert "calc" in t["mcp"] and "/tool/calc" in t["http"]


def test_no_adapter_for_unknown_modality():
    out = _port().handle(Envelope("smell", "..."))
    assert out["decision"] == "NO_ADAPTER"


# ---- verify + escalate: never ship a wrong result silently -------------------------------------
def _compute_ask(code_out: str, direct_out: str):
    """A scripted station/manager: returns a code block for the 'write a program' prompt, a direct
    number for the cross-check prompt. Lets us drive the QC cross-check deterministically (no model)."""

    def ask(prompt):
        if "Write a short Python program" in prompt:
            return "```python\nprint(%s)\n```" % code_out
        return direct_out  # the differential 'answer with only the number' branch

    return ask


def test_judge_comes_back_honest_unverified():
    # judge has no real verifier -> the port must NOT claim a trust guarantee
    p = UniversalPort(ask=lambda _p: "paris")
    out = p.handle(Envelope(TEXT, "What is the capital of France?"))
    assert out["route"] == "judge" and out["decision"] == "UNVERIFIED"
    assert out["verified"] is False and out["has_verifier"] is False and "paris" in out["result"]


def test_compute_cross_check_verifies_without_escalation():
    # station's executed answer (6) agrees with its direct answer (6) -> verified, no manager needed
    p = UniversalPort(ask=_compute_ask("6", "6"))
    out = p.handle(Envelope(TEXT, "What is the sum of 2 and 4?"))
    assert out["route"] == "compute" and out["decision"] == "OK"
    assert out["verified"] is True and out["escalated"] is False and out["result"] == "6"


def test_compute_qc_failure_escalates_to_manager():
    # station ships 5 but its own cross-check says 6 -> QC fails -> manager redoes it and verifies
    p = UniversalPort(ask=_compute_ask("5", "6"), manager=_compute_ask("6", "6"))
    out = p.handle(Envelope(TEXT, "What is the sum of 2 and 4?"))
    assert out["decision"] == "OK" and out["verified"] is True
    assert out["escalated"] is True and out["result"] == "6"  # the manager's verified answer shipped
