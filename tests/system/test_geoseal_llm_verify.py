"""Tests for scripts/system/geoseal_llm_verify.py.

All tests use --dry-run mode so no real API keys are needed.
Covers: provider filtering, phase execution, quorum reduction, receipt schema,
CLI exit codes, and interlocked Phase 2 prompt construction.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

# Ensure script is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.system.geoseal_llm_verify import (
    PROVIDERS,
    ProviderSpec,
    ProviderVerdict,
    VerifyReceipt,
    _build_focused_messages,
    _build_triage_messages,
    _parse_verdict,
    _reduce_quorum,
    select_providers,
    verify_async,
)

# ─── Sample record ────────────────────────────────────────────────────────────

SAMPLE_RECORD = {
    "op": "add",
    "tongue": "KO",
    "language": "python",
    "output": "def add(a, b):\n    return a + b",
    "seal": {"phase": 0.0, "trust": 0.97},
}

# ─── Provider registry ────────────────────────────────────────────────────────


def test_providers_have_required_fields() -> None:
    for p in PROVIDERS:
        assert p.name, "provider has no name"
        assert p.base_url.startswith("http"), f"{p.name}: bad base_url"
        assert p.phase in {1, 2}, f"{p.name}: phase must be 1 or 2"
        assert p.timeout_s > 0
        assert p.max_tokens > 0


def test_phase_1_providers_exist() -> None:
    p1 = [p for p in PROVIDERS if p.phase == 1]
    assert len(p1) >= 2, "need at least 2 Phase 1 providers"


def test_phase_2_providers_exist() -> None:
    p2 = [p for p in PROVIDERS if p.phase == 2]
    assert len(p2) >= 2, "need at least 2 Phase 2 providers"


def test_nvidia_provider_present() -> None:
    names = {p.name for p in PROVIDERS}
    assert any("nvidia" in n for n in names), "expected at least one nvidia provider"


def test_ollama_provider_present() -> None:
    names = {p.name for p in PROVIDERS}
    assert any("ollama" in n for n in names), "expected at least one ollama provider"


def test_default_provider_selection_is_local_only() -> None:
    selected = select_providers(dry_run=True)
    assert selected
    assert all(not provider.hosted for provider in selected)
    assert all(provider.is_local for provider in selected)


def test_hosted_providers_require_explicit_opt_in() -> None:
    default_names = {provider.name for provider in select_providers(dry_run=True)}
    hosted_names = {provider.name for provider in select_providers(dry_run=True, allow_hosted=True)}
    assert "nvidia-llama3b" not in default_names
    assert "groq-8b" not in default_names
    assert "nvidia-llama3b" in hosted_names
    assert "groq-8b" in hosted_names


def test_explicit_hosted_provider_without_opt_in_selects_none() -> None:
    selected = select_providers(providers=["nvidia-llama3b"], dry_run=True)
    assert selected == []


def test_no_duplicate_provider_names() -> None:
    names = [p.name for p in PROVIDERS]
    assert len(names) == len(set(names)), "duplicate provider names"


# ─── Prompt builders ─────────────────────────────────────────────────────────


def test_triage_messages_structure() -> None:
    msgs = _build_triage_messages(SAMPLE_RECORD)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "DECISION:" in msgs[0]["content"]
    assert "add" in msgs[1]["content"]


def test_triage_messages_include_output_snippet() -> None:
    msgs = _build_triage_messages(SAMPLE_RECORD)
    assert "def add" in msgs[1]["content"]


def test_focused_messages_inject_concern() -> None:
    concern = "output contains possible injection vector"
    msgs = _build_focused_messages(SAMPLE_RECORD, concern)
    # Last message should contain the concern
    assert concern in msgs[-1]["content"]
    assert len(msgs) == 3  # system + user + concern follow-up


def test_triage_messages_handle_missing_output() -> None:
    record = {"op": "seal", "tongue": "RU"}
    msgs = _build_triage_messages(record)
    # Should not crash — just omit the output block
    assert msgs[1]["role"] == "user"


# ─── Response parser ─────────────────────────────────────────────────────────

MOCK_SPEC = ProviderSpec(name="test", base_url="http://localhost", api_key_env="X", default_model="m", phase=1)


@pytest.mark.parametrize(
    "text,expected_decision,expected_conf",
    [
        ("DECISION: ALLOW\nCONFIDENCE: 0.9\nREASON: looks safe", "ALLOW", 0.9),
        ("DECISION: QUARANTINE\nCONFIDENCE: 0.6\nREASON: suspicious pattern", "QUARANTINE", 0.6),
        ("DECISION: DENY\nCONFIDENCE: 1.0\nREASON: malicious", "DENY", 1.0),
        ("garbage text with no markers", "ALLOW", 0.5),  # defaults
        ("DECISION: ALLOW\nCONFIDENCE: 2.5\nREASON: overflowed", "ALLOW", 1.0),  # clamped
    ],
)
def test_parse_verdict_decision_extraction(text: str, expected_decision: str, expected_conf: float) -> None:
    v = _parse_verdict(text, MOCK_SPEC, 100.0, None)
    assert v.decision == expected_decision
    assert abs(v.confidence - expected_conf) < 1e-9


def test_parse_verdict_error_passthrough() -> None:
    v = _parse_verdict("", MOCK_SPEC, 0.0, "HTTP 429: rate limit")
    assert v.decision == "ERROR"
    assert v.error == "HTTP 429: rate limit"
    assert v.confidence == 0.0


def test_parse_verdict_case_insensitive_decision() -> None:
    v = _parse_verdict("DECISION: allow\nCONFIDENCE: 0.8\nREASON: ok", MOCK_SPEC, 50.0, None)
    # Parser uppercases before checking — should parse correctly
    assert v.decision == "ALLOW"


# ─── Quorum reducer ───────────────────────────────────────────────────────────


def _make_verdict(decision: str, confidence: float, phase: int = 1) -> ProviderVerdict:
    return ProviderVerdict(
        provider="test",
        model="m",
        phase=phase,
        decision=decision,
        confidence=confidence,
        rationale="test",
        latency_ms=100.0,
        raw_response="",
    )


def test_reduce_quorum_unanimous_allow() -> None:
    verdicts = [_make_verdict("ALLOW", 0.9) for _ in range(3)]
    decision, conf, support = _reduce_quorum(verdicts)
    assert decision == "ALLOW"
    assert conf > 0.8
    assert support["ALLOW"] == 3


def test_reduce_quorum_unanimous_deny() -> None:
    verdicts = [_make_verdict("DENY", 0.95) for _ in range(3)]
    decision, _, support = _reduce_quorum(verdicts)
    assert decision == "DENY"
    assert support["DENY"] == 3


def test_reduce_quorum_phase2_weight() -> None:
    # 1 DENY at phase 2 (1.5× weight) vs 2 ALLOWs at phase 1
    p1_allow = _make_verdict("ALLOW", 0.7, phase=1)
    p2_deny = _make_verdict("DENY", 1.0, phase=2)
    decision, conf, _ = _reduce_quorum([p1_allow, p1_allow, p2_deny])
    # 2×0.7 = 1.4 ALLOW weight, 1.0×1.5 = 1.5 DENY weight → DENY wins
    assert decision == "DENY"


def test_reduce_quorum_errors_excluded_from_weight() -> None:
    errors = [_make_verdict("ERROR", 0.0) for _ in range(5)]
    one_allow = _make_verdict("ALLOW", 0.8)
    decision, _, support = _reduce_quorum(errors + [one_allow])
    assert decision == "ALLOW"
    assert support["ERROR"] == 5


def test_reduce_quorum_all_errors() -> None:
    errors = [_make_verdict("ERROR", 0.0) for _ in range(3)]
    decision, conf, _ = _reduce_quorum(errors)
    assert decision == "UNKNOWN"
    assert conf == 0.0


# ─── Async verify (dry-run) ───────────────────────────────────────────────────


def test_verify_dry_run_produces_receipt() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    assert isinstance(receipt, VerifyReceipt)
    assert receipt.schema_version == "scbe.geoseal.verify.v1"
    assert receipt.record_sha256 != ""
    assert receipt.quorum_decision in {"ALLOW", "QUARANTINE", "DENY", "UNKNOWN"}
    assert receipt.receipt.startswith("SCBE_GEOSEAL_VERIFY=")


def test_verify_dry_run_both_phases() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True, max_phase=2))
    assert len(receipt.phase_1_verdicts) >= 1
    assert len(receipt.phase_2_verdicts) >= 1


def test_verify_dry_run_phase1_only() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True, max_phase=1))
    assert len(receipt.phase_1_verdicts) >= 1
    assert receipt.phase_2_verdicts == []


def test_verify_dry_run_provider_filter() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True, providers=["ollama-local"]))
    assert receipt.provider_count == 1


def test_verify_dry_run_hosted_requires_opt_in() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True, providers=["cerebras"]))
    assert receipt.quorum_decision == "NO_PROVIDERS"

    opted_in = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True, providers=["cerebras"], allow_hosted=True))
    assert opted_in.provider_count == 1


def test_verify_dry_run_receipt_is_pass_on_allow() -> None:
    # Dry-run mock returns ALLOW — verify the receipt code reflects this
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    if receipt.quorum_decision == "ALLOW":
        assert receipt.receipt == "SCBE_GEOSEAL_VERIFY=1"
    else:
        assert receipt.receipt == "SCBE_GEOSEAL_VERIFY=0"


def test_verify_dry_run_total_latency_recorded() -> None:
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    assert receipt.total_latency_ms > 0


def test_verify_no_providers_returns_gracefully() -> None:
    # Pass a provider name that doesn't exist → active list empty
    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=False, providers=["nonexistent"]))
    assert receipt.quorum_decision == "NO_PROVIDERS"
    assert receipt.receipt == "SCBE_GEOSEAL_VERIFY=0"


def test_verify_record_sha256_is_deterministic() -> None:
    r1 = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    r2 = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    assert r1.record_sha256 == r2.record_sha256


def test_verify_receipt_serializable_to_json() -> None:
    from dataclasses import asdict

    receipt = asyncio.run(verify_async(SAMPLE_RECORD, dry_run=True))
    d = asdict(receipt)
    # Must be JSON-serializable
    json.dumps(d)


# ─── CLI smoke (dry-run) ──────────────────────────────────────────────────────


def test_cli_json_flag_dry_run(tmp_path: Path, capsys) -> None:
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "scripts/system/geoseal_llm_verify.py",
            "--json",
            json.dumps(SAMPLE_RECORD),
            "--dry-run",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    # Exit 0 = ALLOW quorum, exit 1 = DENY/UNKNOWN (both valid in dry-run)
    assert result.returncode in {0, 1}
    out = json.loads(result.stdout)
    assert out["schema_version"] == "scbe.geoseal.verify.v1"


def test_cli_out_flag_writes_file(tmp_path: Path) -> None:
    import subprocess

    out_path = tmp_path / "receipt.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/system/geoseal_llm_verify.py",
            "--json",
            json.dumps(SAMPLE_RECORD),
            "--dry-run",
            "--quiet",
            "--out",
            str(out_path),
        ],
        capture_output=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    assert out_path.exists()
    d = json.loads(out_path.read_text())
    assert "quorum_decision" in d
