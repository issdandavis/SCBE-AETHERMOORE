from __future__ import annotations

from pathlib import Path

from scripts.system.verify_docs_publish_surface import verify_docs_surface


def test_verify_docs_surface_accepts_required_live_checkout(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<html><a href="https://buy.stripe.com/live_link">Buy</a></html>',
        encoding="utf-8",
    )
    (tmp_path / "support.html").write_text("<html>Support</html>", encoding="utf-8")

    ok, findings = verify_docs_surface(tmp_path, ["index.html", "support.html"], require_checkout=True)

    assert ok is True
    assert any("index.html: ok" == item for item in findings)


def test_verify_docs_surface_blocks_placeholder_checkout(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<html><a href="https://buy.stripe.com/test_123">Buy</a></html>',
        encoding="utf-8",
    )

    ok, findings = verify_docs_surface(tmp_path, ["index.html"], require_checkout=True)

    assert ok is False
    assert any(item.startswith("blocker:") for item in findings)
