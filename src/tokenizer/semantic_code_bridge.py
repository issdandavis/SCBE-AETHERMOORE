from __future__ import annotations

import hashlib
from typing import Any

from src.cli.cross_build_ir import QuarantineError, cross_build
from src.tokenizer.code_weight_packets import build_code_weight_packet

SCHEMA_VERSION = "scbe-semantic-code-bridge-v1"

OPERATION_ATOM_MAP = {
    "function_definition": "FLOW",
    "return_flow": "FLOW",
    "arithmetic": "TRANSFORM",
    "assignment": "TRANSFORM",
    "iteration_flow": "FLOW",
    "control_guard": "BLOCK",
    "comparison": "BLOCK",
    "semantic_operation": "TRANSFORM",
}


def _operation_kind(path_item: str) -> str:
    return path_item.split(":", 1)[0].split("/", 1)[0]


def semantic_atom_for_operation(path_item: str) -> str:
    """Map a language-agnostic operation path item into a semantic atom id."""

    return OPERATION_ATOM_MAP.get(_operation_kind(path_item), "TRANSFORM")


def _channel_between(left: str, right: str) -> str:
    if left == "FLOW" and right == "BLOCK":
        return "bifurcation"
    if left == "BLOCK" and right == "FLOW":
        return "merge"
    if right == "TRANSFORM":
        return "pipe"
    if left == "TRANSFORM" and right == "FLOW":
        return "pipe"
    return "dot_to_dot"


def build_semantic_code_bridge(
    sources: dict[str, str],
    *,
    source_prefix: str = "sample",
) -> dict[str, Any]:
    """Align source snippets by semantic operation path while preserving source packets.

    This is not a full source-code compiler. It proves the bridge layer:
    language-specific source packets remain hash-bound, while equivalent code
    operations converge to the same interchange key and semantic atom path.
    """

    packets = {
        language: build_code_weight_packet(source, language=language, source_name=f"{source_prefix}.{language}")
        for language, source in sources.items()
    }
    signatures = {language: packet["semantic_operation_signature"] for language, packet in packets.items()}
    interchange_keys = {signature["interchange_key"] for signature in signatures.values()}
    operation_paths = {tuple(signature["operation_path"]) for signature in signatures.values()}
    reference_path = list(next(iter(operation_paths))) if operation_paths else []
    semantic_atoms = [semantic_atom_for_operation(item) for item in reference_path]
    workflow_edges = [
        {
            "from": semantic_atoms[index],
            "to": semantic_atoms[index + 1],
            "channel": _channel_between(semantic_atoms[index], semantic_atoms[index + 1]),
            "operation_from": reference_path[index],
            "operation_to": reference_path[index + 1],
        }
        for index in range(max(len(semantic_atoms) - 1, 0))
    ]

    bridge_payload = {
        "schema_version": SCHEMA_VERSION,
        "languages": sorted(sources),
        "interchange_keys": sorted(interchange_keys),
        "operation_paths": [list(path) for path in sorted(operation_paths)],
        "semantic_atoms": semantic_atoms,
        "workflow_edges": workflow_edges,
    }
    bridge_hash = hashlib.sha256(repr(bridge_payload).encode("utf-8")).hexdigest()

    return {
        **bridge_payload,
        "bridge_hash": bridge_hash,
        "aligned": len(interchange_keys) == 1 and len(operation_paths) == 1,
        "bijective_packet_preservation": {
            language: {
                "source_sha256": packet["source_sha256"],
                "transport_tongue": packet["transport"]["tongue"],
                "transport_token_sha256": packet["transport"]["token_sha256"],
                "lexical_tokens_preserved": signature["preservation"]["lexical_tokens_preserved"],
                "identifier_names_preserved_in_atoms": signature["preservation"]["identifier_names_preserved_in_atoms"],
            }
            for language, packet in packets.items()
            for signature in [signatures[language]]
        },
        "packets": packets,
    }


def semantic_atom_for_lattice_band(band: str) -> str:
    """Map the lexicon-bounded cross-build IR band into semantic atom space."""

    normalized = band.upper()
    if normalized in {"ARITHMETIC", "AGGREGATION"}:
        return "TRANSFORM"
    if normalized in {"COMPARISON", "LOGIC"}:
        return "BLOCK"
    return "TRANSFORM"


def build_lexicon_cross_compile_bridge(src_code: str, src_tongue: str, dst_tongue: str) -> dict[str, Any]:
    """Prove the lexicon-bounded cross-compile path and attach semantic atoms.

    This wraps the existing Tier 1 cross-build sphere:
    source tongue -> shared LatticeOp IR -> destination tongue.

    It deliberately returns quarantine as data so cloud agents can try a move
    safely without pretending arbitrary source parsing succeeded.
    """

    try:
        result = cross_build(src_code, src_tongue, dst_tongue)
    except QuarantineError as exc:
        return {
            "schema_version": "scbe-semantic-lexicon-cross-compile-v1",
            "aligned": False,
            "quarantined": True,
            "error": type(exc).__name__,
            "message": str(exc),
            "src_code": src_code,
            "src_tongue": src_tongue,
            "dst_tongue": dst_tongue,
        }

    semantic_atom = semantic_atom_for_lattice_band(result.ir.band)
    payload = {
        "schema_version": "scbe-semantic-lexicon-cross-compile-v1",
        "aligned": True,
        "quarantined": False,
        "src_code": result.src_code,
        "src_tongue": result.src_tongue,
        "src_language": result.src_language,
        "dst_code": result.dst_code,
        "dst_tongue": result.dst_tongue,
        "dst_language": result.dst_language,
        "ir": result.ir.model_dump(),
        "semantic_atoms": [semantic_atom],
        "workflow_edges": [
            {
                "from": result.src_tongue,
                "to": "LatticeOp",
                "channel": "bifurcation",
                "state_rule": "lift source syntax into the shared frozen IR or quarantine",
            },
            {
                "from": "LatticeOp",
                "to": result.dst_tongue,
                "channel": "merge",
                "state_rule": "emit destination syntax only when the IR contains all required bindings",
            },
        ],
    }
    payload["bridge_hash"] = hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()
    return payload


__all__ = [
    "build_lexicon_cross_compile_bridge",
    "build_semantic_code_bridge",
    "semantic_atom_for_lattice_band",
    "semantic_atom_for_operation",
]
