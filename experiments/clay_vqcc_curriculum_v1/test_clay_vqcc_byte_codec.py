from __future__ import annotations

import pytest

import clay_vqcc_byte_codec as codec


def parent_vocab_fixture() -> list[str]:
    specials_and_ascii = [
        "\x00",
        "\x02",
        "\x1f",
        "\x03",
        " ",
        *list("0123456789"),
        ":",
        "=",
        ">",
        "C",
        "K",
    ]
    assert len(specials_and_ascii) == 20
    return [*specials_and_ascii, *(codec.byte_token(value) for value in range(256))]


def test_all_256_byte_values_round_trip() -> None:
    payload = bytes(range(256))
    tokens = codec.encode_bytes(payload)
    assert len(tokens) == 256
    assert len(set(tokens)) == 256
    assert codec.decode_bytes(tokens) == payload


def test_multilingual_vqcc_prompt_round_trips_through_utf8_bytes() -> None:
    prompt = "TASK=FINDING_BINDING_V1\nQUESTION=φ / qubit / Yoruba: ẹ̀jọ\nANSWER="
    tokens = codec.encode_text(prompt)
    assert codec.decode_text(tokens) == prompt
    assert all(codec.BYTE_TOKEN_BASE <= ord(token) < codec.BYTE_TOKEN_BASE + 256 for token in tokens)
    assert not any(token in prompt for token in tokens)


def test_task_specific_label_grammar_is_strict() -> None:
    assert codec.decode_label("finding_binding", codec.encode_label("finding_binding", "A")) == "A"
    assert codec.decode_label("gate_count", codec.encode_label("gate_count", "T")) == "T"
    with pytest.raises(codec.ByteCodecError, match="not valid"):
        codec.encode_label("finding_binding", "T")
    with pytest.raises(codec.ByteCodecError, match="exactly one"):
        codec.decode_label("gate_count", codec.encode_text("AB"))
    with pytest.raises(codec.ByteCodecError, match="outside"):
        codec.decode_label("gate_count", ("A",))


def test_parent_vocab_coverage_and_label_ids_use_byte_tokens() -> None:
    vocab = parent_vocab_fixture()
    receipt = codec.validate_parent_vocab(vocab)
    assert receipt["vocab_size"] == 276
    assert receipt["all_byte_tokens_present"] is True
    assert receipt["literal_labels_used"] is False
    stoi = {token: index for index, token in enumerate(vocab)}
    assert receipt["label_token_ids"]["finding_binding"] == {
        "A": stoi[codec.byte_token(ord("A"))],
        "B": stoi[codec.byte_token(ord("B"))],
    }
    assert receipt["label_token_ids"]["gate_count"]["T"] == stoi[
        codec.byte_token(ord("T"))
    ]


def test_vocab_validation_fails_on_missing_byte_or_hash_drift() -> None:
    vocab = parent_vocab_fixture()
    missing = vocab.copy()
    missing[-1] = "X"
    with pytest.raises(codec.ByteCodecError, match="lacks byte tokens"):
        codec.validate_parent_vocab(missing)
    with pytest.raises(codec.ByteCodecError, match="hash differs"):
        codec.validate_parent_vocab(vocab, expected_sha256="0" * 64)
