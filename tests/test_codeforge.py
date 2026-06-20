"""End-to-end tests for codeforge — messy intent -> verified cross-language code + receipt."""

from python.codeforge import forge


def test_forge_add_runs_end_to_end():
    cat = forge("please add 3 and 4")
    assert cat.ok is True
    assert [r.status for r in cat.receipts] == ["ok", "ok", "ok", "ok", "ok"]
    res = cat.result
    assert res["op"] == "add" and res["operands"] == [3, 4]
    assert res["verified"] is True and res["behavioral_ok"] is True
    assert "def run()" in res["source"]["python"]
    assert "function run()" in res["source"]["javascript"]
    assert "#include <stdio.h>" in res["source"]["c"]
    assert cat.chain_digest  # tamper-evident proof of the whole run


def test_forge_multiply_runs_end_to_end():
    cat = forge("multiply 6 by 7")
    assert cat.ok is True
    assert cat.result["op"] == "multiply" and cat.result["operands"] == [6, 7]
    assert cat.result["verified"] is True and cat.result["behavioral_ok"] is True


def test_forge_unknown_request_drifts_gracefully():
    cat = forge("paint a fence blue")
    assert cat.ok is False
    assert cat.receipts[0].phase == "understand" and cat.receipts[0].status == "drift"
    assert cat.result is None  # nothing shipped


def test_forge_is_deterministic():
    assert forge("add 3 and 4").chain_digest == forge("add 3 and 4").chain_digest


def test_forge_default_operands_when_unspecified():
    cat = forge("just add some numbers")
    assert cat.ok is True
    assert cat.result["operands"] == [3, 4]  # sensible defaults
