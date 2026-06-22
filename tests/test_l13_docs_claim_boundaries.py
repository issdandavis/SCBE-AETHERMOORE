from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
L13_DOCS = [
    REPO_ROOT / "docs" / "specs" / "BIJECTIVE_TAMPER_L13.md",
    REPO_ROOT / "docs" / "specs" / "IDENTIFIER_CANONICALITY_L13.md",
]


def test_l13_docs_use_signal_language_not_universal_proof_language():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in L13_DOCS).lower()
    banned = [
        "the bijective compiler proved",
        "the bijective tamper signal proves",
        "this module fills that gap",
        "monotonic guarantee",
    ]
    for phrase in banned:
        assert phrase not in combined

    assert "static tamper signal" in combined
    assert "static signal" in combined
    assert "v1 results are python-gate results" in combined
