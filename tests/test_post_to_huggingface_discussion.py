from pathlib import Path

from scripts.publish.post_to_huggingface_discussion import publish_discussion


def test_publish_discussion_dry_run(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text(
        "# Bounded AI Is the Shipping Pattern\n\n**By Issac Davis** | March 17, 2026\n\n---\n\nBody text.",
        encoding="utf-8",
    )

    result = publish_discussion(
        file_path=article,
        repo_id="issdandavis/phdm-21d-embedding",
        repo_type="model",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["payload"]["title"] == "Bounded AI Is the Shipping Pattern"
    assert result["payload"]["repo_id"] == "issdandavis/phdm-21d-embedding"
    assert "Body text." in result["payload"]["description"]
