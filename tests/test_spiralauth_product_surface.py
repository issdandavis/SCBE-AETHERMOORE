from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_spiralauth_demo_uses_real_browser_hmac_and_boundary_copy() -> None:
    html = (ROOT / "public" / "spiralauth.html").read_text(encoding="utf-8")

    assert "crypto.subtle.importKey" in html
    assert "{ name: 'HMAC', hash: 'SHA-256' }" in html
    assert "The conlang layer is not encryption by itself" not in html
    assert "This demo does not claim a conlang is encryption" in html
    assert "keyed HMAC over the canonical envelope" in html


def test_spiralauth_package_states_cryptographic_boundary() -> None:
    doc = (ROOT / "docs" / "product-delivery" / "SPIRALAUTH_SELLABLE_PACKAGE.md").read_text(
        encoding="utf-8"
    )

    assert "It does not replace cryptography" in doc
    assert "The conlang layer is not encryption by itself" in doc
    assert "The cryptographic boundary is standard keyed authentication" in doc
    assert "intent-bound authorization" in doc
