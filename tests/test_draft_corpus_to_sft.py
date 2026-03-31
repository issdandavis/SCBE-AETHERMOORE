from __future__ import annotations

from pathlib import Path

from scripts import draft_corpus_to_sft as draft


def test_collect_rows_keeps_lore_text_file(tmp_path: Path) -> None:
    root = tmp_path / "drafts"
    root.mkdir()
    lore = root / "avalon_chapter.txt"
    lore.write_text(
        (
            "The Spiral of Avalon follows Izack, Polly, Aria, and Clay through Avalon Academy. "
            "The World Tree and Sacred Tongues shape collaborative magic across the realm.\n\n"
        )
        * 50,
        encoding="utf-8",
    )

    rows, stats = draft.collect_rows([str(root)], chunk_target=4000, chunk_max=5000, min_doc_chars=1200)
    assert stats["files_total"] == 1
    assert stats["files_kept"] == 1
    assert rows
    assert rows[0]["metadata"]["document_name"] == "avalon_chapter.txt"


def test_collect_rows_extracts_html_and_skips_noise(tmp_path: Path) -> None:
    root = tmp_path / "drafts"
    root.mkdir()
    noise = root / "A FUll log.html"
    noise.write_text("<html><body>Skip to content Open sidebar ChatGPT 4.5 Saved memory full</body></html>", encoding="utf-8")
    lore = root / "shore.html"
    lore.write_text(
        "<html><body><h1>Shore to King</h1><p>Izack and Polly study the Sacred Tongues and the World Tree at Avalon Academy.</p>"
        * 80
        + "</body></html>",
        encoding="utf-8",
    )

    rows, stats = draft.collect_rows([str(root)], chunk_target=4000, chunk_max=5000, min_doc_chars=1200)
    assert stats["files_total"] == 2
    assert stats["files_kept"] == 1
    assert stats["files_skipped_noise"] == 1
    assert rows[0]["metadata"]["document_name"] == "shore.html"

