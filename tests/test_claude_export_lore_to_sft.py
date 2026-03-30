from __future__ import annotations

from scripts.claude_export_lore_to_sft import chunk_text, is_candidate_doc, is_noise_doc, lore_score


def test_is_noise_doc_rejects_ui_dump() -> None:
    text = "Skip to content\nOpen sidebar\nChatGPT 4.5\nSaved memory full\nYou said:"
    assert is_noise_doc("A FUll log.txt", text) is True


def test_candidate_doc_accepts_lore_manuscript() -> None:
    text = (
        "The Spiral of Avalon follows Izack, Polly, Aria, and Clay through Avalon Academy. "
        "The World Tree and Sacred Tongues shape collaborative magic across the realm.\n\n"
    ) * 50
    assert lore_score("Avalon story", "The Spiral of Avalon.txt", text) >= 4
    assert is_candidate_doc("Avalon story", "The Spiral of Avalon.txt", text, min_doc_chars=1200) is True


def test_chunk_text_splits_long_paragraphs() -> None:
    text = ("Alpha " * 1600) + "\n\n" + ("Beta " * 1600)
    chunks = chunk_text(text, target=4000, hard_max=5000)
    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)
