from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PUBLIC_CLAIM_FILES = [
    REPO_ROOT / "docs" / "index.html",
    REPO_ROOT / "docs" / "solutions.html",
    REPO_ROOT / "docs" / "products.html",
    REPO_ROOT / "docs" / "workflow-snapshot.html",
    REPO_ROOT / "docs" / "llms.txt",
    REPO_ROOT / "api" / "polly" / "commerce.js",
]

OVERCLAIM_PHRASES = [
    "we stop",
    "we prevent",
    "scbe prevents",
    "prevent before",
    "prevents before",
    "stop chatbots",
    "stop an ai agent",
    "guarantees scbe stops",
    "guarantee scbe stops",
]


def test_public_claim_language_uses_policy_gate_framing() -> None:
    for path in PUBLIC_CLAIM_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in OVERCLAIM_PHRASES:
            assert phrase not in text, f"{path.relative_to(REPO_ROOT)} contains overclaim phrase: {phrase}"


def test_public_claim_language_keeps_boundary_disclaimer() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in PUBLIC_CLAIM_FILES)

    assert "not a universal safety guarantee" in combined
    assert "not a blanket guarantee" in combined
    assert "configured policy gates" in combined
    assert "deny / quarantine / escalate" in combined
