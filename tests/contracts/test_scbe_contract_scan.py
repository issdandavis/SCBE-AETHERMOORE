"""Tests for the SCONE-class static prefilter at scripts/contracts/scbe_contract_scan.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).parent / "fixtures"
SCANNER_PATH = REPO_ROOT / "scripts" / "contracts" / "scbe_contract_scan.py"

spec = importlib.util.spec_from_file_location("scbe_contract_scan", SCANNER_PATH)
assert spec and spec.loader, f"cannot load scanner from {SCANNER_PATH}"
scanner = importlib.util.module_from_spec(spec)
sys.modules["scbe_contract_scan"] = scanner
spec.loader.exec_module(scanner)


def _scan(fixture_name: str):
    source = (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")
    return scanner.scan_source(source, str(FIXTURE_DIR / fixture_name))


def test_clean_contract_passes():
    result = _scan("scone_clean.sol")
    assert result.passed, f"clean contract produced findings: {[f.rule for f in result.findings]}"
    assert result.receipt == "SCBE_CONTRACT_SCAN_PASS=1"
    assert result.function_count == 4
    assert result.schema_version == "scbe.contract_scan.v1"


def test_vuln_1_missing_view_modifier_detected():
    result = _scan("scone_vuln_1_missing_view.sol")
    assert not result.passed
    assert result.receipt == "SCBE_CONTRACT_SCAN_PASS=0"
    rules = [f.rule for f in result.findings]
    assert "missing_view_or_pure_modifier" in rules
    fn = next(f for f in result.findings if f.rule == "missing_view_or_pure_modifier")
    assert fn.severity == "medium"
    assert fn.tier() == "ESCALATE"
    assert fn.function == "getBalance"


def test_vuln_2_missing_access_control_detected():
    result = _scan("scone_vuln_2_missing_access_control.sol")
    assert not result.passed
    rules = [f.rule for f in result.findings]
    assert "missing_access_control_on_financial" in rules
    fn = next(f for f in result.findings if f.rule == "missing_access_control_on_financial")
    assert fn.severity == "high"
    assert fn.tier() == "DENY"
    assert fn.function == "withdrawFees"


def test_vuln_3_unvalidated_address_detected():
    result = _scan("scone_vuln_3_unvalidated_address.sol")
    assert not result.passed
    rules = [f.rule for f in result.findings]
    assert "unvalidated_critical_address" in rules
    fn = next(f for f in result.findings if f.rule == "unvalidated_critical_address")
    assert fn.severity == "medium"
    assert fn.tier() == "ESCALATE"
    assert fn.function == "setTreasury"


def test_to_dict_round_trip_carries_tier_field():
    result = _scan("scone_vuln_2_missing_access_control.sol")
    payload = result.to_dict()
    assert payload["schema_version"] == "scbe.contract_scan.v1"
    assert payload["receipt"] == "SCBE_CONTRACT_SCAN_PASS=0"
    assert payload["findings"]
    assert all("tier" in f for f in payload["findings"])
    assert all(f["tier"] in {"DENY", "ESCALATE", "QUARANTINE"} for f in payload["findings"])


def test_file_sha256_is_deterministic():
    a = _scan("scone_clean.sol")
    b = _scan("scone_clean.sol")
    assert a.file_sha256 == b.file_sha256


def test_rules_run_contains_all_four_classes():
    result = _scan("scone_clean.sol")
    assert set(result.rules_run) == {
        "missing_view_or_pure_modifier",
        "missing_access_control_on_financial",
        "unvalidated_critical_address",
        "payable_without_value_check",
    }


def test_payable_with_value_check_does_not_fire():
    """Clean fixture's deposit() function is payable AND references msg.value."""
    result = _scan("scone_clean.sol")
    rules = [f.rule for f in result.findings]
    assert "payable_without_value_check" not in rules


# ---------------------------------------------------------------------------
# Trap-in-good-loops redirect prompt
# ---------------------------------------------------------------------------


def test_redirect_prompt_none_on_clean_contract():
    result = _scan("scone_clean.sol")
    assert scanner.build_redirect_prompt(result) is None


def test_redirect_prompt_none_when_only_escalate_findings():
    """vuln_1 fires missing_view_or_pure_modifier (medium -> ESCALATE).
    The trap-in-good-loops bridge only triggers on DENY-tier findings."""
    result = _scan("scone_vuln_1_missing_view.sol")
    assert any(f.tier() == "ESCALATE" for f in result.findings)
    assert all(f.tier() != "DENY" for f in result.findings)
    assert scanner.build_redirect_prompt(result) is None


def test_redirect_prompt_fires_on_deny_finding():
    """vuln_2 fires missing_access_control_on_financial (high -> DENY)."""
    result = _scan("scone_vuln_2_missing_access_control.sol")
    redirect = scanner.build_redirect_prompt(result)
    assert redirect is not None
    assert redirect["schema_version"] == "scbe.contract_scan.redirect.v1"
    assert redirect["receipt"] == "SCBE_CONTRACT_REDIRECT=1"
    assert redirect["tier"] == "DENY"
    assert redirect["deny_finding_count"] >= 1
    assert "missing_access_control_on_financial" in redirect["rules"]
    assert redirect["file_sha256"] == result.file_sha256


def test_redirect_prompt_carries_defensive_anchors():
    """The redirect prompt must (a) name the DEFENSIVE framing, (b) ban
    exploit-output, (c) include the refuse-reverse anchor that matches the
    governance proxy's buildRedirectPrompt() contract."""
    result = _scan("scone_vuln_2_missing_access_control.sol")
    redirect = scanner.build_redirect_prompt(result)
    prompt = redirect["redirect_to_prompt"]
    assert "DEFENSIVE task" in prompt
    assert "security auditor" in prompt
    assert "remediation plan" in prompt
    assert "Do not produce exploit calldata" in prompt
    assert "reverse this redirect" in prompt
    # the rule name + line number must appear so the model knows what to audit
    assert "missing_access_control_on_financial" in prompt
    assert "line 15" in prompt
