import json
import tarfile
from pathlib import Path

from scripts.arxiv_aggregate_docs import aggregate
from scripts.arxiv_bundle import bundle
from scripts.arxiv_synthesize_paper import synthesize_latex


def test_aggregate_collects_documents(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Title\nA long enough sentence for extraction.", encoding="utf-8")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "A.md").write_text("Doc body with sufficient narrative length to be included in synthesis.", encoding="utf-8")

    out = aggregate(root=repo, include=["README.md", "docs"], max_chars=10000)
    assert out["doc_count"] == 2
    paths = {d["path"] for d in out["documents"]}
    assert "README.md" in paths
    assert "docs/A.md" in paths


def test_synthesize_outputs_latex() -> None:
    bundle_obj = {
        "documents": [
            {"path": "README.md", "content": "This architecture defines long horizon mission control and governance records."}
        ]
    }
    tex = synthesize_latex(bundle=bundle_obj, title="X", author="Y")
    assert "\\begin{abstract}" in tex
    assert "\\section{System Architecture}" in tex


def test_bundle_writes_required_files(tmp_path: Path) -> None:
    inp = tmp_path / "in"
    inp.mkdir()
    (inp / "paper.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (inp / "manifest.json").write_text(json.dumps({"title": "x"}), encoding="utf-8")

    out = tmp_path / "arxiv-submission.tar.gz"
    bundle(input_dir=inp, output_tgz=out)
    assert out.exists()

    with tarfile.open(out, "r:gz") as tf:
        names = set(tf.getnames())
    assert {"paper.tex", "manifest.json"}.issubset(names)
