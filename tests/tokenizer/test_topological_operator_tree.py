from __future__ import annotations

import json

import pytest

from src.tokenizer.topological_operator_tree import (
    bootstrap_seed,
    build_topological_t_tree,
    discrete_t_operator,
    operator_signature_packet,
    tokenize_operation_text,
)


def test_discrete_t_self_seeds_to_one_for_valid_field_values() -> None:
    for value in [2, 3, 4, 17, 255, 4096, 65536]:
        assert discrete_t_operator(value, value, value) == 1
        assert bootstrap_seed(value) == 1


def test_tokenizer_builds_nested_t_tree_for_koraelin_command() -> None:
    tokens = tokenize_operation_text("korah aelin dahru")

    tree = build_topological_t_tree(tokens)

    assert tree.kind == "T"
    assert tree.children[0].label == "korah"
    assert tree.children[1].kind == "T"
    assert tree.children[1].children[0].label == "aelin"
    assert tree.children[1].children[1].label == "dahru"
    assert tree.children[2].kind == "seed"
    assert tree.children[2].value == 1


def test_operator_signature_packet_is_stable_and_binary_hex_visible() -> None:
    packet_a = operator_signature_packet("korah aelin dahru")
    packet_b = operator_signature_packet("korah aelin dahru")

    assert packet_a == packet_b
    assert packet_a["floating_point_policy"] == "forbidden for consensus signatures"
    assert packet_a["purpose"].startswith("deterministic AI operations routing")
    assert len(packet_a["signature"]["hex"]) == 32
    assert set(packet_a["signature"]["binary"]).issubset({"0", "1"})
    assert len(packet_a["signature"]["binary"]) == 64
    assert "korah aelin dahru" not in json.dumps(packet_a)


def test_operator_signature_changes_when_tree_order_changes() -> None:
    packet_a = operator_signature_packet("korah aelin dahru")
    packet_b = operator_signature_packet("korah dahru aelin")

    assert packet_a["root_value"] != packet_b["root_value"]
    assert packet_a["signature"]["sha256"] != packet_b["signature"]["sha256"]


def test_unknown_operation_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown operation token"):
        tokenize_operation_text("korah unknown dahru")
