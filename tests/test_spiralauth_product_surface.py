from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_spiralauth_demo_uses_real_browser_hmac_and_boundary_copy() -> None:
    html = (ROOT / "public" / "spiralauth.html").read_text(encoding="utf-8")

    assert "crypto.subtle.importKey" in html
    assert "{ name: 'HMAC', hash: 'SHA-256' }" in html
    assert "The conlang layer is not encryption by itself" not in html
    assert "This demo does not claim a conlang is encryption" in html
    assert "keyed HMAC over the canonical envelope" in html


def test_spiralauth_package_states_ai_operations_boundary() -> None:
    doc = (ROOT / "docs" / "product-delivery" / "SPIRALAUTH_SELLABLE_PACKAGE.md").read_text(
        encoding="utf-8"
    )

    assert "It does not replace the SCBE security stack" in doc
    assert "Sacred Eggs and the separate authorization/security systems remain responsible" in doc
    assert "The conlang layer is not encryption by itself" in doc
    assert "Authority is handled separately by Sacred Eggs and the SCBE security stack" in doc
    assert "AI operation routing and audit" in doc
