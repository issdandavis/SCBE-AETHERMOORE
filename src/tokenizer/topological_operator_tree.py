from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

FIELD_PRIME = 65537
FIELD_GENERATOR = 3
FIELD_LOG_A = 31337
FIELD_LOG_B = 17

TreeKind = Literal["leaf", "seed", "T"]

DEFAULT_OPERATION_LEXICON: dict[str, int] = {
    "korah": 0,
    "aelin": 1,
    "dahru": 2,
    "melik": 3,
    "sorin": 4,
    "tivar": 5,
    "ulmar": 6,
    "vexin": 7,
    "zephyr": 8,
}


@dataclass(frozen=True)
class OperatorNode:
    kind: TreeKind
    value: int
    label: str | None = None
    children: tuple["OperatorNode", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "value": self.value,
            "children": [child.to_dict() for child in self.children],
        }


def _field(value: int) -> int:
    return int(value) % FIELD_PRIME


def _field_inverse(value: int) -> int:
    value = _field(value)
    if value == 0:
        raise ValueError("zero has no inverse in the operator field")
    return pow(value, FIELD_PRIME - 2, FIELD_PRIME)


def discrete_exp_like(value: int) -> int:
    return pow(FIELD_GENERATOR, _field(value) % (FIELD_PRIME - 1), FIELD_PRIME)


def discrete_log_like(value: int) -> int:
    mapped = (FIELD_LOG_A * _field(value) + FIELD_LOG_B) % FIELD_PRIME
    return mapped if mapped else 1


def discrete_t_operator(x: int, y: int, z: int) -> int:
    """Deterministic finite-field T analogue with T(v,v,v) == 1.

    This is an AI-operations packet primitive, not a cryptographic primitive.
    It preserves the self-seeding shape without relying on hardware-dependent
    floating-point exp/log implementations.
    """

    exp_x = discrete_exp_like(x)
    exp_y = discrete_exp_like(y)
    log_x = discrete_log_like(x)
    log_z = discrete_log_like(z)
    return _field(exp_x * _field_inverse(log_x) * log_z * _field_inverse(exp_y))


def bootstrap_seed(value: int) -> int:
    return discrete_t_operator(value, value, value)


def token_field_value(token_id: int) -> int:
    return _field(int(token_id) + 2)


def tokenize_operation_text(
    text: str,
    *,
    lexicon: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    active_lexicon = lexicon or DEFAULT_OPERATION_LEXICON
    tokens: list[dict[str, Any]] = []
    for index, raw in enumerate(text.lower().split()):
        word = raw.strip(" \t\r\n.,;:!?()[]{}\"'")
        if not word:
            continue
        if word not in active_lexicon:
            raise ValueError(f"unknown operation token: {word}")
        token_id = active_lexicon[word]
        tokens.append(
            {
                "index": index,
                "word": word,
                "id": token_id,
                "field_value": token_field_value(token_id),
            }
        )
    if not tokens:
        raise ValueError("operation text did not contain known tokens")
    return tokens


def _leaf(token: dict[str, Any]) -> OperatorNode:
    return OperatorNode(kind="leaf", label=str(token["word"]), value=int(token["field_value"]))


def _seed_node(seed: int) -> OperatorNode:
    return OperatorNode(kind="seed", label="T(v,v,v)", value=seed)


def _t_node(x: OperatorNode, y: OperatorNode, z: OperatorNode) -> OperatorNode:
    return OperatorNode(
        kind="T",
        label="discrete_T",
        value=discrete_t_operator(x.value, y.value, z.value),
        children=(x, y, z),
    )


def build_topological_t_tree(tokens: list[dict[str, Any]]) -> OperatorNode:
    if not tokens:
        raise ValueError("at least one token is required")
    seed_value = bootstrap_seed(int(tokens[0]["field_value"]))
    seed = _seed_node(seed_value)
    leaves = [_leaf(token) for token in tokens]
    if len(leaves) == 1:
        return _t_node(leaves[0], leaves[0], leaves[0])
    if len(leaves) == 2:
        return _t_node(leaves[0], leaves[1], seed)

    current = _t_node(leaves[-2], leaves[-1], seed)
    for leaf in reversed(leaves[:-2]):
        current = _t_node(leaf, current, seed)
    return current


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def operator_signature_packet(text: str, *, lexicon: dict[str, int] | None = None) -> dict[str, Any]:
    tokens = tokenize_operation_text(text, lexicon=lexicon)
    tree = build_topological_t_tree(tokens)
    tree_payload = tree.to_dict()
    token_payload = [
        {
            "index": token["index"],
            "word": token["word"],
            "id": token["id"],
            "field_value": token["field_value"],
        }
        for token in tokens
    ]
    packet_core = {
        "field": {
            "prime": FIELD_PRIME,
            "generator": FIELD_GENERATOR,
            "log_a": FIELD_LOG_A,
            "log_b": FIELD_LOG_B,
        },
        "tokens": token_payload,
        "tree": tree_payload,
        "root_value": tree.value,
    }
    signature_hex = _hash_payload(packet_core)
    return {
        "schema_version": "scbe-topological-operator-tree-v1",
        "purpose": "deterministic AI operations routing signal; not cryptographic authentication",
        "floating_point_policy": "forbidden for consensus signatures",
        **packet_core,
        "signature": {
            "sha256": signature_hex,
            "hex": signature_hex[:32],
            "binary": "".join(f"{int(char, 16):04b}" for char in signature_hex[:16]),
        },
    }


__all__ = [
    "DEFAULT_OPERATION_LEXICON",
    "FIELD_PRIME",
    "OperatorNode",
    "bootstrap_seed",
    "build_topological_t_tree",
    "discrete_t_operator",
    "operator_signature_packet",
    "tokenize_operation_text",
]
