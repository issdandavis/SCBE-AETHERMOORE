from pathlib import Path

SPEC = Path("docs/specs/TOKENIZER_EXECUTION_LATTICE_ROLE_v1.md")


def test_tokenizer_role_spec_exists_and_names_boundary() -> None:
    text = SPEC.read_text(encoding="utf-8").lower()

    assert "semantic execution lattice" in text
    assert "not a security tokenizer" in text
    assert "not a security boundary" in text

    for security_layer in [
        "governance gates",
        "crypto/sealing",
        "capability controls",
        "execution policy",
        "verification layers",
    ]:
        assert security_layer in text


def test_tokenizer_role_spec_preserves_semantic_transport_split() -> None:
    text = SPEC.read_text(encoding="utf-8").lower()

    for layer_name in ["semantic phrase", "metric payload", "transport packet"]:
        assert layer_name in text

    for responsibility in [
        "cross-language mapping",
        "cross-domain mapping",
        "message + code co-representation",
        "intent-preserving transformation",
        "bijective reversibility",
    ]:
        assert responsibility in text


def test_tokenizer_role_spec_points_to_runtime_separation() -> None:
    text = SPEC.read_text(encoding="utf-8").lower()

    assert "crypto secures it" in text
    assert "governance permits it" in text
    assert "the tokenizer makes it understandable" in text
    assert "do not use tokenizer reversibility as proof that an action is safe" in text
