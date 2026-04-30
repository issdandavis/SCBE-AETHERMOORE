from __future__ import annotations

import hashlib
import re
from typing import Any


FIELD_DEFINITIONS = [
    {"name": "Z_proxy"},
    {"name": "group_proxy"},
    {"name": "period_proxy"},
    {"name": "valence_proxy"},
    {"name": "chi_proxy"},
    {"name": "band_flag"},
    {"name": "tongue_id"},
    {"name": "reserved"},
]

LANGUAGE_TONGUES = {
    "python": "KO",
    "typescript": "AV",
    "rust": "RU",
    "c": "CA",
    "julia": "UM",
    "haskell": "DR",
}

TONGUE_PREFIX = {
    "KO": "kor",
    "AV": "nurel",
    "RU": "run",
    "CA": "cass",
    "UM": "umb",
    "DR": "dra",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _lexical_tokens(source: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|->|=>|::|[^\s]", source)


def _semantic_class(token: str) -> str:
    lowered = token.lower()
    if lowered in {"return", "if", "else", "for", "while", "def", "fn", "function", "let", "const"}:
        return "ACTION"
    if lowered in {"none", "null", "nothing", "true", "false"} or len(token) == 1:
        return "INERT_WITNESS"
    if token in {"+", "-", "*", "/", "=", "==", "!=", "<", ">", "<=", ">=", "->", "=>", "::"}:
        return "RELATION"
    return "ENTITY"


def _element_for(token: str, semantic_class: str) -> dict[str, Any]:
    if semantic_class == "INERT_WITNESS":
        return {
            "symbol": "He",
            "Z": 2,
            "group": 18,
            "period": 1,
            "valence": 0,
            "electronegativity": 0.0,
            "witness_stable": True,
        }
    if semantic_class == "RELATION":
        return {
            "symbol": "Si",
            "Z": 14,
            "group": 14,
            "period": 3,
            "valence": 4,
            "electronegativity": 1.9,
            "witness_stable": False,
        }
    if semantic_class == "ACTION":
        return {
            "symbol": "C",
            "Z": 6,
            "group": 14,
            "period": 2,
            "valence": 4,
            "electronegativity": 2.55,
            "witness_stable": False,
        }
    return {
        "symbol": "Fe",
        "Z": 26,
        "group": 8,
        "period": 4,
        "valence": 2,
        "electronegativity": 1.8,
        "witness_stable": False,
    }


def _feature_vector(element: dict[str, Any], semantic_class: str) -> list[float]:
    return [
        float(element["Z"]),
        float(element["group"]),
        float(element["period"]),
        float(element["valence"]),
        float(element["electronegativity"]),
        1.0 if semantic_class in {"ACTION", "ENTITY"} else 0.0,
        1.0,
        0.0,
    ]


def _transport_tokens(source: str, tongue: str) -> list[str]:
    prefix = TONGUE_PREFIX.get(tongue, "tok")
    names = ("a", "e", "i", "o", "u", "y", "en", "ul", "la", "sa")
    return [f"{prefix}'{names[byte % len(names)]}" for byte in source.encode("utf-8")]


def _lane_alignment(language: str, tongue: str) -> dict[str, Any]:
    expected = {
        "python": ["python"],
        "typescript": ["typescript"],
        "rust": ["rust"],
        "c": ["c"],
        "julia": ["julia"],
        "haskell": ["haskell"],
    }.get(language, [language])
    return {
        "active_profile": "coding_system_full_v1",
        "reference_profile": "coding_system_full_v1",
        "contract_tongues": [tongue],
        "expected_lanes": expected,
        "actual_lanes": [language],
        "reference_lanes": expected,
        "mismatch_lanes": [],
        "mismatch_count": 0,
        "degradation_score": 0.0,
        "failure_mode": "none",
        "operational_failure_risk": "LOW",
        "cross_profile_divergence": False,
    }


def _quarks(tokens: list[str]) -> list[str]:
    lowered = {token.lower() for token in tokens}
    result: list[str] = []
    if lowered & {"def", "fn", "function"}:
        result.append("function_shape")
    if "return" in lowered:
        result.append("return_flow")
    if lowered & {"+", "-", "*", "/"}:
        result.append("arithmetic_transform")
    if lowered & {"if", "else", "?", ":"}:
        result.append("control_guard")
    if lowered & {"for", "while", "map", "iter"}:
        result.append("iteration_flow")
    return result or ["semantic_operation"]


def build_code_weight_packet(source: str, *, language: str, source_name: str = "") -> dict[str, Any]:
    tokens = _lexical_tokens(source)
    tongue = LANGUAGE_TONGUES.get(language.lower(), "KO")
    rows = []
    atomic_states = []
    for token in tokens:
        semantic_class = _semantic_class(token)
        element = _element_for(token, semantic_class)
        rows.append(
            {
                "token": token,
                "semantic_class": semantic_class,
                "feature_vector": _feature_vector(element, semantic_class),
            }
        )
        atomic_states.append({"token": token, "element": element})

    source_bytes = source.encode("utf-8")
    transport_tokens = _transport_tokens(source, tongue)
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    token_sha = hashlib.sha256(" ".join(transport_tokens).encode("utf-8")).hexdigest()
    return {
        "schema_version": "scbe-code-weight-packet-v1",
        "source_name": source_name,
        "language": language,
        "source_sha256": source_sha,
        "lexical_tokens": tokens,
        "stisa": {
            "field_definitions": FIELD_DEFINITIONS,
            "token_rows": rows,
        },
        "atomic_states": atomic_states,
        "binary": {"bits": [f"{byte:08b}" for byte in source_bytes]},
        "transport": {
            "tongue": tongue,
            "tokens": transport_tokens,
            "source_sha256": source_sha,
            "token_sha256": token_sha,
        },
        "route": {"tongue": tongue, "language": language},
        "semantic_expression": {"quarks": _quarks(tokens)},
        "lane_alignment": _lane_alignment(language, tongue),
        "content_sha256": _sha256_text(source),
    }


__all__ = ["build_code_weight_packet"]
