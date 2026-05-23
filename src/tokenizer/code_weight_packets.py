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
    # Natural programming languages
    "python": "KO",
    "typescript": "AV",
    "javascript": "AV",
    "rust": "RU",
    "c": "CA",
    "cpp": "CA",
    "c++": "CA",
    "csharp": "CA",
    "julia": "UM",
    "haskell": "DR",
    # Markup / document languages
    "html": "RU",
    "css": "CA",
    "markdown": "AV",
    # Data / config languages
    "json": "DR",
    "yaml": "DR",
    "toml": "DR",
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


# ─── Domain-specific token classification tables ─────────────────────────────

_HTML_STRUCTURE = frozenset(
    {
        "<div>",
        "<span>",
        "<section>",
        "<article>",
        "<header>",
        "<footer>",
        "<main>",
        "<nav>",
        "<aside>",
        "<p>",
        "<ul>",
        "<ol>",
        "<li>",
        "<h1>",
        "<h2>",
        "<h3>",
        "<h4>",
        "<h5>",
        "<h6>",
        "<table>",
        "<tr>",
        "<td>",
        "<th>",
        "<form>",
        "<button>",
        "<select>",
        "<input>",
        "<label>",
        "<figure>",
        "<figcaption>",
        "<blockquote>",
    }
)
_HTML_ACTION = frozenset(
    {
        "<script>",
        "<style>",
        "<link>",
        "<meta>",
        "<iframe>",
        "<canvas>",
        "<video>",
        "<audio>",
        "<template>",
    }
)
_HTML_RELATION = frozenset(
    {
        "href",
        "src",
        "id",
        "class",
        "type",
        "name",
        "value",
        "action",
        "method",
        "rel",
        "for",
        "data",
        "alt",
        "title",
        "placeholder",
        "disabled",
        "checked",
        "selected",
    }
)

_MD_STRUCTURE = frozenset({"#", "##", "###", "####", "#####", "######"})
_MD_RELATION = frozenset({"[", "!["})
_MD_ACTION = frozenset({"```", "`", "**", "*", "_", "__", "~~", "---"})

_C_ACTION = frozenset(
    {
        "if",
        "else",
        "for",
        "while",
        "do",
        "return",
        "break",
        "continue",
        "switch",
        "case",
        "default",
        "goto",
    }
)
_C_STRUCTURE = frozenset({"struct", "union", "enum", "typedef"})
_C_RELATION = frozenset({"->", ".", "&"})
_C_INERT = frozenset({"void", "null", "nullptr", "false", "true", "none"})

_CPP_ACTION = _C_ACTION | frozenset(
    {
        "new",
        "delete",
        "throw",
        "try",
        "catch",
        "noexcept",
        "explicit",
        "inline",
        "virtual",
        "override",
        "final",
    }
)
_CPP_STRUCTURE = _C_STRUCTURE | frozenset({"class", "template", "namespace"})
_CPP_RELATION = _C_RELATION | frozenset({"::", ".*", "->*"})

_RUST_ACTION = frozenset(
    {
        "fn",
        "impl",
        "mod",
        "pub",
        "use",
        "return",
        "if",
        "else",
        "for",
        "while",
        "loop",
        "match",
        "let",
        "mut",
        "async",
        "await",
        "where",
        "dyn",
        "move",
        "unsafe",
        "extern",
        "crate",
    }
)
_RUST_STRUCTURE = frozenset({"struct", "enum", "trait", "type", "union"})
_RUST_RELATION = frozenset({"&", "->", "::", ".", "=>", "?", "ref"})
_RUST_INERT = frozenset({"None", "false", "true", "()"})


def semantic_class_for_domain(token: str, language: str) -> str:
    """Return the semantic class for a token given its source language.

    Returns one of: ACTION, STRUCTURE, RELATION, INERT_WITNESS, ENTITY.
    Falls back to the generic ``_semantic_class`` for unrecognised language/token pairs.
    """
    lang = language.lower()

    if lang == "html":
        lower = token.lower()
        if lower in _HTML_STRUCTURE:
            return "STRUCTURE"
        if lower in _HTML_ACTION:
            return "ACTION"
        if lower in _HTML_RELATION:
            return "RELATION"

    elif lang == "markdown":
        if token in _MD_STRUCTURE:
            return "STRUCTURE"
        if token in _MD_RELATION:
            return "RELATION"
        if token in _MD_ACTION:
            return "ACTION"

    elif lang == "c":
        lower = token.lower()
        if lower in _C_ACTION:
            return "ACTION"
        if lower in _C_STRUCTURE:
            return "STRUCTURE"
        if token in _C_RELATION:
            return "RELATION"
        if lower in _C_INERT:
            return "INERT_WITNESS"

    elif lang in ("cpp", "c++"):
        lower = token.lower()
        if lower in _CPP_ACTION:
            return "ACTION"
        if lower in _CPP_STRUCTURE:
            return "STRUCTURE"
        if token in _CPP_RELATION:
            return "RELATION"
        if lower in _C_INERT:
            return "INERT_WITNESS"

    elif lang == "rust":
        if token in _RUST_ACTION:
            return "ACTION"
        if token in _RUST_STRUCTURE:
            return "STRUCTURE"
        if token in _RUST_RELATION:
            return "RELATION"
        if token in _RUST_INERT:
            return "INERT_WITNESS"

    return _semantic_class(token)


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


def resolve_element(token: str, semantic_class: str | None = None) -> dict[str, Any]:
    """Resolve a token into the STISA element proxy shape used by GeoSeal CLI."""

    semantic = semantic_class or _semantic_class(token)
    element = dict(_element_for(token, semantic))
    element["feat"] = _feature_vector(element, semantic)
    return element


def analyze_chemical_composition(
    tokens: list[str],
    elements: list[dict[str, Any]],
    *,
    operation_path: list[str] | None = None,
) -> dict[str, Any]:
    """Summarize the token-element proxy mix for STISA/GeoSeal packet surfaces."""

    symbol_counts: dict[str, int] = {}
    total_z = 0.0
    total_valence = 0.0
    stable_witnesses = 0
    for element in elements:
        symbol = str(element.get("symbol", "?"))
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        total_z += float(element.get("Z", 0.0))
        total_valence += float(element.get("valence", 0.0))
        if element.get("witness_stable"):
            stable_witnesses += 1

    count = max(len(elements), 1)
    return {
        "schema_version": "scbe-stisa-chemical-composition-v1",
        "token_count": len(tokens),
        "element_count": len(elements),
        "symbol_counts": symbol_counts,
        "dominant_symbol": max(symbol_counts, key=symbol_counts.get) if symbol_counts else None,
        "average_z": total_z / count,
        "average_valence": total_valence / count,
        "stable_witness_count": stable_witnesses,
        "operation_path": operation_path or [],
    }


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


def _token_roles(tokens: list[str]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for index, token in enumerate(tokens):
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            lowered = token.lower()
            if lowered in {
                "class",
                "const",
                "def",
                "else",
                "false",
                "fn",
                "for",
                "function",
                "if",
                "let",
                "none",
                "null",
                "return",
                "true",
                "while",
            }:
                role = "keyword"
            else:
                role = "identifier"
        elif re.fullmatch(r"\d+(?:\.\d+)?", token):
            role = "literal:number"
        elif token in {'"', "'", "`"}:
            role = "literal:string_delimiter"
        elif token in {"+", "-", "*", "/", "%"}:
            role = "operator:arithmetic"
        elif token in {"==", "!=", "<", ">", "<=", ">="}:
            role = "operator:comparison"
        elif token in {"=", "+=", "-=", "*=", "/=", "%="}:
            role = "operator:assignment"
        elif token in {"(", ")", "{", "}", "[", "]", ",", ":", ";", "->", "=>", "::"}:
            role = "punctuator"
        else:
            role = "symbol"
        roles.append({"index": index, "token": token, "role": role})
    return roles


def _find_after(tokens: list[str], candidates: set[str], start: int = 0) -> int | None:
    for index in range(start, len(tokens)):
        if tokens[index].lower() in candidates:
            return index
    return None


def _function_name(tokens: list[str], language: str) -> str | None:
    lowered = [token.lower() for token in tokens]
    for keyword in ("def", "fn", "function"):
        if keyword in lowered:
            index = lowered.index(keyword)
            if index + 1 < len(tokens) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tokens[index + 1]):
                return tokens[index + 1]

    # C-like declarations often arrive as: int add(int a, int b) { ... }
    if language.lower() in {"c", "cpp", "c++", "java", "go"}:
        for index in range(1, len(tokens) - 1):
            if tokens[index + 1] == "(" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tokens[index]):
                if tokens[index].lower() not in {"if", "for", "while", "switch", "return"}:
                    return tokens[index]
    return None


def _extract_params(tokens: list[str], function_name: str | None) -> list[str]:
    if function_name is None:
        return []
    try:
        open_index = tokens.index("(", tokens.index(function_name))
    except ValueError:
        return []
    depth = 0
    params: list[str] = []
    current: list[str] = []
    for token in tokens[open_index + 1 :]:
        if token == "(":
            depth += 1
            current.append(token)
            continue
        if token == ")":
            if depth == 0:
                if current:
                    params.append(" ".join(current))
                break
            depth -= 1
            current.append(token)
            continue
        if token == "," and depth == 0:
            if current:
                params.append(" ".join(current))
                current = []
            continue
        current.append(token)
    return [param for param in params if param]


def _normalize_param(param: str) -> str:
    pieces = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\*|&|\.\.\.", param)
    identifiers = [piece for piece in pieces if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", piece)]
    if not identifiers:
        return "arg"
    return identifiers[-1]


def _operation_atoms(tokens: list[str], language: str) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = []
    function_name = _function_name(tokens, language)
    params = [_normalize_param(param) for param in _extract_params(tokens, function_name)]
    if function_name:
        atoms.append(
            {
                "kind": "function_definition",
                "name": function_name,
                "arity": len(params),
                "params": params,
            }
        )

    return_index = _find_after(tokens, {"return"})
    if return_index is not None:
        atoms.append({"kind": "return_flow"})

    arithmetic_ops = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod"}
    comparison_ops = {"==": "eq", "!=": "neq", "<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}
    for index, token in enumerate(tokens):
        if token in arithmetic_ops:
            atoms.append({"kind": "arithmetic", "operator": arithmetic_ops[token], "arity": 2, "token_index": index})
        elif token in comparison_ops:
            atoms.append({"kind": "comparison", "operator": comparison_ops[token], "arity": 2, "token_index": index})
        elif token in {"=", "+=", "-=", "*=", "/=", "%="}:
            operator = "assign" if token == "=" else f"{arithmetic_ops[token[0]]}_assign"
            atoms.append({"kind": "assignment", "operator": operator, "arity": 2, "token_index": index})

    if any(token.lower() in {"for", "while"} for token in tokens):
        atoms.append({"kind": "iteration_flow"})
    if any(token.lower() in {"if", "else"} for token in tokens):
        atoms.append({"kind": "control_guard"})
    return atoms


def _atom_key(atom: dict[str, Any]) -> str:
    kind = str(atom.get("kind", "operation"))
    if kind == "function_definition":
        return f"function_definition/{int(atom.get('arity', 0))}"
    operator = atom.get("operator")
    if operator:
        return f"{kind}:{operator}/{int(atom.get('arity', 0))}"
    return kind


def build_semantic_operation_signature(source: str, *, language: str) -> dict[str, Any]:
    tokens = _lexical_tokens(source)
    return semantic_operation_signature_from_tokens(tokens, language=language)


def semantic_operation_signature_from_tokens(tokens: list[str], *, language: str) -> dict[str, Any]:
    roles = _token_roles(tokens)
    atoms = _operation_atoms(tokens, language)
    operation_path = [_atom_key(atom) for atom in atoms] or ["semantic_operation"]
    interchange_payload = "|".join(operation_path)
    return {
        "schema_version": "scbe-semantic-operation-signature-v1",
        "source_language": language,
        "token_roles": roles,
        "operation_atoms": atoms,
        "operation_path": operation_path,
        "interchange_key": hashlib.sha256(interchange_payload.encode("utf-8")).hexdigest(),
        "interchange_payload": interchange_payload,
        "preservation": {
            "source_text_hash_bound": True,
            "lexical_tokens_preserved": True,
            "identifier_names_preserved_in_atoms": True,
            "language_specific_syntax_excluded_from_interchange_key": True,
        },
    }


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
    semantic_operation = semantic_operation_signature_from_tokens(tokens, language=language)
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
        "semantic_expression": {
            "quarks": _quarks(tokens),
            "operation_signature": semantic_operation,
            "interchange_key": semantic_operation["interchange_key"],
            "operation_path": semantic_operation["operation_path"],
        },
        "semantic_operation_signature": semantic_operation,
        "lane_alignment": _lane_alignment(language, tongue),
        "content_sha256": _sha256_text(source),
    }


__all__ = [
    "LANGUAGE_TONGUES",
    "analyze_chemical_composition",
    "build_code_weight_packet",
    "build_semantic_operation_signature",
    "resolve_element",
    "semantic_class_for_domain",
    "semantic_operation_signature_from_tokens",
]
