from pathlib import Path

from scripts.system.colab_workflow_catalog import extract_embedded_colab_url, resolve_notebook_payload


def test_extract_embedded_colab_url_from_real_notebook() -> None:
    notebook = Path("notebooks/spiralverse_protocol_training_generator.ipynb")
    url = extract_embedded_colab_url(notebook)
    assert url.startswith("https://colab.research.google.com/gist/")
    assert "spiralverse-protocol-ai-training-data-generator.ipynb" in url


def test_resolve_notebook_payload_prefers_embedded_url_when_present() -> None:
    payload = resolve_notebook_payload("generator")
    assert payload["embedded_colab_url"].startswith("https://colab.research.google.com/gist/")
    assert payload["colab_url"] == payload["embedded_colab_url"]
    assert payload["fallback_colab_url"].startswith("https://colab.research.google.com/github/")


def test_resolve_notebook_payload_falls_back_to_github_url_when_no_embedded_link() -> None:
    payload = resolve_notebook_payload("finetune")
    assert payload["embedded_colab_url"] == ""
    assert payload["colab_url"] == payload["fallback_colab_url"]
    assert payload["colab_url"].startswith("https://colab.research.google.com/github/")


def test_canonical_notebook_resolves_and_falls_back_to_github_url() -> None:
    payload = resolve_notebook_payload("canonical")
    assert payload["name"] == "canonical-training-lane"
    assert payload["embedded_colab_url"] == ""
    assert payload["colab_url"] == payload["fallback_colab_url"]
    assert payload["colab_url"].startswith("https://colab.research.google.com/github/")
