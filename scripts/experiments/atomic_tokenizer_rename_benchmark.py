"""Rename/anonymization benchmark for the cross-primary atomic tokenizer.

This is intentionally a lightweight experiment runner. It avoids the heavy
GeoSeal CLI import path and reuses the existing MATHBAC cross-primary corpus
plus the current atomic feature extractor.

The purpose is diagnostic:
- If concept recovery survives concept-word removal, the signal is structural.
- If it collapses, the signal is lexical or override-table leakage.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.mathbac_cross_primary_atomic import (
    ATOMIC_SEMANTIC_CLASSES,
    TONGUES,
    _accuracy,
    _atomic_feature,
    _feature_keys,
    _l2_squared,
    _per_concept_accuracy,
    loo_nearest_concept,
)
from scripts.experiments.layered_geometry_semantic_packing import (
    DEFAULT_FEATURES as GEOMETRY_DEFAULT_FEATURES,
    build_benchmark as build_layered_geometry_benchmark,
    evaluate_shape as evaluate_geometry_shape,
    optimize_token_shape,
)
from python.scbe.atomic_tokenization import map_token_to_atomic_state

DEFAULT_INPUT = Path("artifacts/mathbac/cross_primary_atomic")
DEFAULT_OUTPUT = Path("artifacts/mathbac/atomic_tokenizer_rename_benchmark")
PERIODIC_TABLE = Path("artifacts/mathbac/periodic_table_full.json")
BINARY_MATRIX_SFT = Path("training-data/sft/binary_interpretation_matrix_v1.sft.jsonl")
DEFAULT_SHUFFLE_RUNS = 128
DEFAULT_SHUFFLE_SEED = 2659


CONCEPT_ALIASES: dict[str, list[str]] = {
    "fibonacci": ["fibonacci", "fib"],
    "factorial": ["factorial", "fact"],
    "gcd": ["greatest_common_divisor", "gcd"],
    "is_prime": ["is_prime", "prime", "primality"],
    "binary_search": ["binary_search", "bsearch", "binary search", "search"],
    "quicksort": ["quicksort", "quick_sort", "quick sort"],
    "bubble_sort": ["bubble_sort", "bubble sort"],
    "fizzbuzz": ["fizzbuzz", "fizz", "buzz"],
    "string_reverse": ["string_reverse", "string reverse", "reverse"],
    "palindrome": ["palindrome", "palindromic"],
    "count_vowels": ["count_vowels", "count vowels", "vowel", "vowels"],
    "sum_list": ["sum_list", "sum list", "sum", "total"],
    "max_in_list": ["max_in_list", "maximum", "max"],
    "matrix_transpose": ["matrix_transpose", "matrix transpose", "transpose", "matrix"],
}


GENERIC_REPLACEMENTS = [
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
]


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z_]{1,}")
HEX_DIGITS = "0123456789ABCDEF"
BYTE_CLASSES = ("control", "space", "digit", "upper", "lower", "symbol", "extended")
CODE_FLOW_KEYWORDS = (
    "if",
    "else",
    "elif",
    "for",
    "while",
    "return",
    "break",
    "continue",
    "match",
    "case",
    "switch",
    "where",
    "do",
    "then",
    "module",
    "function",
    "fn",
    "def",
    "let",
    "mut",
    "const",
    "var",
    "map",
    "filter",
    "fold",
    "zip",
    "range",
    "len",
    "length",
)
OPERATOR_PATTERNS = {
    "op_assign": "=",
    "op_compare": "==",
    "op_not_equal": "!=",
    "op_less": "<",
    "op_greater": ">",
    "op_plus": "+",
    "op_minus": "-",
    "op_mul": "*",
    "op_div": "/",
    "op_mod": "%",
    "op_colon": ":",
    "op_semicolon": ";",
    "op_comma": ",",
    "op_arrow": "->",
    "op_pipe": "|",
    "op_lambda": "\\",
}


@dataclass(frozen=True)
class Sample:
    concept: str
    primary: str
    path: Path
    source: str


def _sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _load_manifest(input_dir: Path) -> dict[str, Any]:
    return json.loads((input_dir / "manifest.json").read_text(encoding="utf-8"))


def _load_samples(input_dir: Path) -> list[Sample]:
    manifest = _load_manifest(input_dir)
    samples: list[Sample] = []
    for row in manifest["files"]:
        path = input_dir / row["relative_path"]
        samples.append(
            Sample(
                concept=row["concept"],
                primary=row["tongue"],
                path=path,
                source=path.read_text(encoding="utf-8"),
            )
        )
    samples.sort(key=lambda sample: (sample.concept, sample.primary))
    return samples


def _case_replacement(match: re.Match[str], replacement: str) -> str:
    text = match.group(0)
    if text.isupper():
        return replacement.upper()
    if text[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def anonymize_concept_words(source: str, concept: str) -> tuple[str, list[str]]:
    """Remove concept-specific words without trying to preserve executable syntax."""

    aliases = sorted(CONCEPT_ALIASES.get(concept, [concept]), key=len, reverse=True)
    changed: list[str] = []
    output = source
    for index, alias in enumerate(aliases):
        replacement = GENERIC_REPLACEMENTS[index % len(GENERIC_REPLACEMENTS)]
        # Match whole identifier fragments and prose words. Underscore-bearing
        # aliases need explicit boundaries because \b treats underscore as word.
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        output, count = pattern.subn(
            lambda match, rep=replacement: _case_replacement(match, rep),
            output,
        )
        if count:
            changed.append(alias)
    return output, changed


def _default_atomic_feature(text: str) -> dict[str, float]:
    return _atomic_feature(text)


def _load_periodic_table(table_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(table_path.read_text(encoding="utf-8"))
    elements = payload.get("elements")
    if not isinstance(elements, list) or not elements:
        raise ValueError(f"invalid periodic table payload: {table_path}")
    return elements


def load_binary_hex_lookup(path: Path = BINARY_MATRIX_SFT) -> dict[int, dict[str, str]]:
    """Load workbook-backed binary/decimal/hex rows for byte tracing."""

    lookup: dict[int, dict[str, str]] = {}
    if not path.exists():
        return lookup
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        sheet = record.get("metadata", {}).get("sheet")
        if sheet not in {"Binary-Decimal-Hex", "ASCII Table"}:
            continue
        content = record.get("messages", [{}])[1].get("content", "")
        fields: dict[str, str] = {}
        for chunk in content.split("Row facts:", 1)[-1].split(";"):
            if ":" not in chunk:
                continue
            key, value = chunk.split(":", 1)
            fields[key.strip()] = value.strip()
        decimal = fields.get("Decimal")
        if decimal and decimal.isdigit():
            byte_value = int(decimal)
            if 0 <= byte_value <= 255:
                lookup[byte_value] = {
                    "decimal": str(byte_value),
                    "binary": fields.get("Binary", f"0b{byte_value:08b}"),
                    "hex": fields.get("Hex", f"0x{byte_value:02X}"),
                    "character": fields.get("Character", ""),
                    "description": fields.get("Description", ""),
                    "source_sheet": sheet,
                }
    return lookup


def binary_hex_row(byte_value: int, lookup: dict[int, dict[str, str]]) -> dict[str, str]:
    row = lookup.get(byte_value)
    if row:
        return row
    return {
        "decimal": str(byte_value),
        "binary": f"0b{byte_value:08b}",
        "hex": f"0x{byte_value:02X}",
        "character": chr(byte_value) if 32 <= byte_value <= 126 else "",
        "description": "generated fallback; byte not present in workbook export",
        "source_sheet": "generated_fallback",
    }


def _byte_element_index(byte_value: int, size: int, mode: str) -> int:
    if mode == "mod":
        return byte_value % size
    if mode == "stride":
        return (byte_value * 47) % size
    if mode == "hex":
        # Hex mode is intentionally equivalent to decoding the workbook hex
        # row back into a byte before the stride. The value is the same as
        # stride, but the trace carries workbook-backed hex/binary metadata.
        return (int(f"{byte_value:02X}", 16) * 47) % size
    if mode == "hash":
        return int(sha256(bytes([byte_value])).hexdigest(), 16) % size
    raise ValueError(f"unknown byte map mode: {mode}")


def _byte_element(byte_value: int, table: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    return table[_byte_element_index(byte_value, len(table), mode)]


def _element_number(element: dict[str, Any]) -> float:
    value = element.get("number")
    if value is None:
        value = element.get("atomic_number")
    return float(value or 0.0)


def make_byte_periodic_feature(
    table: list[dict[str, Any]], *, mode: str = "stride"
) -> Callable[[str], dict[str, float]]:
    categories = sorted({str(item.get("category") or "unknown") for item in table})
    phases = sorted({str(item.get("phase") or "unknown") for item in table})
    keys = (
        [f"cat_{category}" for category in categories]
        + [f"phase_{phase}" for phase in phases]
        + ["en_mean", "period_mean", "group_mean", "byte_count"]
    )

    def feature(text: str) -> dict[str, float]:
        data = text.encode("utf-8")
        result = {key: 0.0 for key in keys}
        if not data:
            return result
        elements = [table[_byte_element_index(byte, len(table), mode)] for byte in data]
        category_counts = Counter(str(element.get("category") or "unknown") for element in elements)
        phase_counts = Counter(str(element.get("phase") or "unknown") for element in elements)
        n = float(len(elements))
        for category, count in category_counts.items():
            result[f"cat_{category}"] = count / n
        for phase, count in phase_counts.items():
            result[f"phase_{phase}"] = count / n
        result["en_mean"] = sum(float(element.get("electronegativity_pauling") or 0.0) for element in elements) / n
        result["period_mean"] = sum(float(element.get("period") or 0.0) for element in elements) / n
        result["group_mean"] = sum(float(element.get("group") or 0.0) for element in elements) / n
        result["byte_count"] = n
        return result

    feature.keys = keys  # type: ignore[attr-defined]
    return feature


def _byte_class(byte_value: int) -> str:
    if byte_value < 32 or byte_value == 127:
        return "control"
    if byte_value in {9, 10, 13, 32}:
        return "space"
    if 48 <= byte_value <= 57:
        return "digit"
    if 65 <= byte_value <= 90:
        return "upper"
    if 97 <= byte_value <= 122:
        return "lower"
    if byte_value <= 126:
        return "symbol"
    return "extended"


def make_binary_hex_chemistry_feature(
    table: list[dict[str, Any]],
    hex_lookup: dict[int, dict[str, str]],
    *,
    mode: str = "hex",
) -> Callable[[str], dict[str, float]]:
    """Feature head using workbook-backed binary/hex rows plus element traces."""

    element_symbols = sorted(str(item.get("symbol") or "?") for item in table)
    keys = (
        [f"high_nibble_{digit}" for digit in HEX_DIGITS]
        + [f"low_nibble_{digit}" for digit in HEX_DIGITS]
        + [f"popcount_{idx}" for idx in range(9)]
        + [f"byte_class_{name}" for name in BYTE_CLASSES]
        + [f"element_{symbol}" for symbol in element_symbols]
        + [f"element_pair_bucket_{idx:02d}" for idx in range(64)]
        + [
            "byte_count_log",
            "bit_density",
            "hex_source_coverage",
            "period_mean",
            "group_mean",
            "electronegativity_mean",
        ]
    )

    def feature(text: str) -> dict[str, float]:
        data = text.encode("utf-8")
        result = {key: 0.0 for key in keys}
        if not data:
            return result
        element_symbols_for_text: list[str] = []
        for byte_value in data:
            row = binary_hex_row(byte_value, hex_lookup)
            hex_value = row["hex"].removeprefix("0x").removeprefix("0X").upper().zfill(2)
            result[f"high_nibble_{hex_value[0]}"] += 1.0
            result[f"low_nibble_{hex_value[1]}"] += 1.0
            popcount = row["binary"].removeprefix("0b").count("1")
            result[f"popcount_{popcount}"] += 1.0
            result[f"byte_class_{_byte_class(byte_value)}"] += 1.0
            if row["source_sheet"] != "generated_fallback":
                result["hex_source_coverage"] += 1.0
            element = _byte_element(byte_value, table, mode)
            symbol = str(element.get("symbol") or "?")
            element_symbols_for_text.append(symbol)
            result[f"element_{symbol}"] += 1.0
            result["period_mean"] += float(element.get("period") or 0.0)
            result["group_mean"] += float(element.get("group") or 0.0)
            result["electronegativity_mean"] += float(element.get("electronegativity_pauling") or 0.0)
        n = float(len(data))
        for key in list(result):
            if (
                key.startswith("high_nibble_")
                or key.startswith("low_nibble_")
                or key.startswith("popcount_")
                or key.startswith("byte_class_")
                or key.startswith("element_")
            ):
                result[key] /= n
        for left, right in zip(element_symbols_for_text, element_symbols_for_text[1:]):
            bucket = int(sha256(f"{left}:{right}".encode("utf-8")).hexdigest(), 16) % 64
            result[f"element_pair_bucket_{bucket:02d}"] += 1.0
        if len(element_symbols_for_text) > 1:
            pair_n = float(len(element_symbols_for_text) - 1)
            for key in result:
                if key.startswith("element_pair_bucket_"):
                    result[key] /= pair_n
        result["byte_count_log"] = math.log1p(n)
        result["bit_density"] = sum(byte.bit_count() for byte in data) / (n * 8.0)
        result["hex_source_coverage"] /= n
        result["period_mean"] /= n
        result["group_mean"] /= n
        result["electronegativity_mean"] /= n
        return result

    feature.keys = keys  # type: ignore[attr-defined]
    return feature


def make_operational_flow_feature() -> Callable[[str], dict[str, float]]:
    """Rename-stable code/prose structure features that reinforce chemistry."""

    keys = (
        [f"kw_{keyword}" for keyword in CODE_FLOW_KEYWORDS]
        + list(OPERATOR_PATTERNS)
        + [
            "line_count_log",
            "avg_line_len",
            "indent_density",
            "token_count_log",
            "avg_token_len",
            "snake_token_frac",
            "upper_token_frac",
            "digit_token_frac",
            "bracket_density",
            "paren_density",
            "brace_density",
            "comment_marker_density",
            "prose_word_density",
        ]
    )

    def feature(text: str) -> dict[str, float]:
        result = {key: 0.0 for key in keys}
        lowered = text.lower()
        tokens = TOKEN_PATTERN.findall(text)
        token_count = float(len(tokens) or 1)
        for keyword in CODE_FLOW_KEYWORDS:
            result[f"kw_{keyword}"] = sum(1 for token in tokens if token.lower() == keyword) / token_count
        for key, pattern in OPERATOR_PATTERNS.items():
            result[key] = lowered.count(pattern) / max(1.0, float(len(text)))
        lines = text.splitlines() or [text]
        byte_len = max(1.0, float(len(text.encode("utf-8"))))
        result["line_count_log"] = math.log1p(len(lines))
        result["avg_line_len"] = sum(len(line) for line in lines) / max(1.0, float(len(lines)))
        result["indent_density"] = sum(len(line) - len(line.lstrip(" \t")) for line in lines) / byte_len
        result["token_count_log"] = math.log1p(len(tokens))
        result["avg_token_len"] = sum(len(token) for token in tokens) / token_count
        result["snake_token_frac"] = sum(1 for token in tokens if "_" in token) / token_count
        result["upper_token_frac"] = sum(1 for token in tokens if token.isupper()) / token_count
        result["digit_token_frac"] = sum(1 for token in tokens if any(ch.isdigit() for ch in token)) / token_count
        result["bracket_density"] = sum(text.count(ch) for ch in "[]") / byte_len
        result["paren_density"] = sum(text.count(ch) for ch in "()") / byte_len
        result["brace_density"] = sum(text.count(ch) for ch in "{}") / byte_len
        result["comment_marker_density"] = (
            text.count("#") + text.count("//") + text.count("--") + text.count("/*")
        ) / byte_len
        result["prose_word_density"] = sum(1 for token in tokens if len(token) >= 7) / token_count
        return result

    feature.keys = keys  # type: ignore[attr-defined]
    return feature


def combine_feature_heads(
    heads: list[tuple[str, Callable[[str], dict[str, float]], float]],
) -> Callable[[str], dict[str, float]]:
    def feature(text: str) -> dict[str, float]:
        combined: dict[str, float] = {}
        for name, head, weight in heads:
            for key, value in head(text).items():
                combined[f"{name}:{key}"] = float(value) * weight
        return combined

    return feature


def make_atomic_semantic_overlay_feature() -> Callable[[str], dict[str, float]]:
    """Semantic overlay lane from the current atomic tokenizer contract."""

    def feature(text: str) -> dict[str, float]:
        return _default_atomic_feature(text)

    return feature


GEOMETRY_TOKEN_FAMILIES = ("CALLABLE", "CONTROL_FLOW", "DATA_SYMBOL", "GOVERNANCE_GATE")
GEOMETRY_OUTER_SIDES = {
    "CALLABLE": 6,
    "CONTROL_FLOW": 8,
    "DATA_SYMBOL": 5,
    "GOVERNANCE_GATE": 7,
}


def _geometry_family_for_token(token: str, state_semantic_class: str) -> str:
    lowered = token.lower()
    if lowered in CODE_FLOW_KEYWORDS or state_semantic_class in {"RELATION", "TEMPORAL"}:
        return "CONTROL_FLOW"
    if lowered in {"allow", "deny", "quarantine", "escalate", "policy", "audit", "risk", "guard"}:
        return "GOVERNANCE_GATE"
    if state_semantic_class == "ACTION":
        return "CALLABLE"
    return "DATA_SYMBOL"


def make_layered_geometry_semantic_feature() -> Callable[[str], dict[str, float]]:
    """Layered geometry lane: stable outer token hull plus packed inner context.

    This feature does not claim geometry is semantics. It converts the current
    tokenizer's semantic class into an outer hull family, then adds bounded
    packing metrics from the independent geometry probe.
    """

    shape_reports = {
        family: evaluate_geometry_shape(
            optimize_token_shape(
                family,
                GEOMETRY_OUTER_SIDES[family],
                GEOMETRY_DEFAULT_FEATURES[family],
            )
        )
        for family in GEOMETRY_TOKEN_FAMILIES
    }
    keys = [f"geom_family_{family}" for family in GEOMETRY_TOKEN_FAMILIES] + [
        "geom_token_count_log",
        "geom_mean_fit_score",
        "geom_mean_semantic_loss",
        "geom_mean_utilization",
        "geom_mean_octave_links",
        "geom_mean_collision_count",
        "geom_mean_boundary_violations",
        "geom_control_to_callable_ratio",
        "geom_governance_to_data_ratio",
    ]

    def feature(text: str) -> dict[str, float]:
        result = {key: 0.0 for key in keys}
        tokens = TOKEN_PATTERN.findall(text)
        if not tokens:
            return result
        families: list[str] = []
        for token in tokens:
            state = map_token_to_atomic_state(token, language="en", context_class="operator")
            family = _geometry_family_for_token(token, state.semantic_class)
            families.append(family)
        n = float(len(families))
        counts = Counter(families)
        for family, count in counts.items():
            result[f"geom_family_{family}"] = count / n
        result["geom_token_count_log"] = math.log1p(n)
        result["geom_mean_fit_score"] = sum(shape_reports[family].fit_score for family in families) / n
        result["geom_mean_semantic_loss"] = sum(shape_reports[family].semantic_loss for family in families) / n
        result["geom_mean_utilization"] = sum(shape_reports[family].utilization for family in families) / n
        result["geom_mean_octave_links"] = sum(shape_reports[family].octave_link_count for family in families) / n
        result["geom_mean_collision_count"] = sum(shape_reports[family].collision_count for family in families) / n
        result["geom_mean_boundary_violations"] = (
            sum(shape_reports[family].boundary_violation_count for family in families) / n
        )
        result["geom_control_to_callable_ratio"] = counts["CONTROL_FLOW"] / max(1.0, float(counts["CALLABLE"]))
        result["geom_governance_to_data_ratio"] = counts["GOVERNANCE_GATE"] / max(1.0, float(counts["DATA_SYMBOL"]))
        return result

    feature.keys = keys  # type: ignore[attr-defined]
    feature.geometry_probe = build_layered_geometry_benchmark()  # type: ignore[attr-defined]
    return feature


def byte_periodic_signature(text: str, table: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    """Build a source-level molecule signature from byte->element traces."""

    data = text.encode("utf-8")
    if not data:
        return {
            "byte_count": 0,
            "category_fracs": {},
            "phase_fracs": {},
            "element_fracs": {},
            "atomic_number_mean": 0.0,
            "atomic_number_std": 0.0,
            "electronegativity_mean": 0.0,
            "period_mean": 0.0,
            "group_mean": 0.0,
        }
    elements = [_byte_element(byte, table, mode) for byte in data]
    category_counts = Counter(str(element.get("category") or "unknown") for element in elements)
    phase_counts = Counter(str(element.get("phase") or "unknown") for element in elements)
    element_counts = Counter(str(element.get("symbol") or "?") for element in elements)
    n = float(len(elements))
    atomic_numbers = [_element_number(element) for element in elements]
    atomic_mean = sum(atomic_numbers) / n
    atomic_var = sum((number - atomic_mean) ** 2 for number in atomic_numbers) / n
    return {
        "byte_count": len(elements),
        "category_fracs": {key: value / n for key, value in sorted(category_counts.items())},
        "phase_fracs": {key: value / n for key, value in sorted(phase_counts.items())},
        "element_fracs": {key: value / n for key, value in sorted(element_counts.items())},
        "atomic_number_mean": atomic_mean,
        "atomic_number_std": math.sqrt(atomic_var),
        "electronegativity_mean": sum(float(element.get("electronegativity_pauling") or 0.0) for element in elements)
        / n,
        "period_mean": sum(float(element.get("period") or 0.0) for element in elements) / n,
        "group_mean": sum(float(element.get("group") or 0.0) for element in elements) / n,
    }


def _signature_vector(signature: dict[str, Any]) -> dict[str, float]:
    vector: dict[str, float] = {
        "byte_count_log": math.log1p(float(signature["byte_count"])),
        "atomic_number_mean": float(signature["atomic_number_mean"]),
        "atomic_number_std": float(signature["atomic_number_std"]),
        "electronegativity_mean": float(signature["electronegativity_mean"]),
        "period_mean": float(signature["period_mean"]),
        "group_mean": float(signature["group_mean"]),
    }
    for key, value in signature["category_fracs"].items():
        vector[f"cat:{key}"] = float(value)
    for key, value in signature["phase_fracs"].items():
        vector[f"phase:{key}"] = float(value)
    for key, value in signature["element_fracs"].items():
        vector[f"element:{key}"] = float(value)
    return vector


def _l2_features(left: dict[str, float], right: dict[str, float], keys: list[str]) -> float:
    return math.sqrt(math.fsum((left.get(key, 0.0) - right.get(key, 0.0)) ** 2 for key in keys))


def chemical_distance_report(
    samples: list[Sample],
    sources: list[str],
    table: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    """Measure whether byte-periodic molecules cluster by concept or primary."""

    signatures = [byte_periodic_signature(source, table, mode=mode) for source in sources]
    vectors = [_signature_vector(signature) for signature in signatures]
    keys = _feature_keys_for(vectors)
    intra: list[float] = []
    inter: list[float] = []
    same_primary_cross_concept: list[float] = []
    same_concept_cross_primary: list[float] = []
    per_concept: dict[str, list[float]] = defaultdict(list)
    nearest: dict[str, Counter[str]] = defaultdict(Counter)

    for left_index, right_index in combinations(range(len(samples)), 2):
        left = samples[left_index]
        right = samples[right_index]
        distance = _l2_features(vectors[left_index], vectors[right_index], keys)
        if left.concept == right.concept:
            intra.append(distance)
            same_concept_cross_primary.append(distance)
            per_concept[left.concept].append(distance)
        else:
            inter.append(distance)
            if left.primary == right.primary:
                same_primary_cross_concept.append(distance)

    for index, sample in enumerate(samples):
        best_distance = math.inf
        best_concept = "UNKNOWN"
        for other_index, other in enumerate(samples):
            if other_index == index:
                continue
            distance = _l2_features(vectors[index], vectors[other_index], keys)
            if distance < best_distance:
                best_distance = distance
                best_concept = other.concept
        nearest[sample.concept][best_concept] += 1

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return {
        "mode": mode,
        "feature_count": len(keys),
        "intra_concept_mean": mean(intra),
        "inter_concept_mean": mean(inter),
        "same_concept_cross_primary_mean": mean(same_concept_cross_primary),
        "same_primary_cross_concept_mean": mean(same_primary_cross_concept),
        "intra_inter_ratio": mean(intra) / mean(inter) if inter else 0.0,
        "per_concept_intra_mean": {concept: mean(values) for concept, values in sorted(per_concept.items())},
        "nearest_neighbor_confusions": {
            concept: dict(counter.most_common(5)) for concept, counter in sorted(nearest.items())
        },
        "source_molecules": [
            {
                "concept": sample.concept,
                "primary": sample.primary,
                "path": str(sample.path),
                "byte_count": signature["byte_count"],
                "atomic_number_mean": signature["atomic_number_mean"],
                "atomic_number_std": signature["atomic_number_std"],
                "electronegativity_mean": signature["electronegativity_mean"],
                "period_mean": signature["period_mean"],
                "group_mean": signature["group_mean"],
                "top_elements": sorted(signature["element_fracs"].items(), key=lambda item: (-item[1], item[0]))[:8],
                "top_categories": sorted(signature["category_fracs"].items(), key=lambda item: (-item[1], item[0]))[:5],
            }
            for sample, signature in zip(samples, signatures)
        ],
    }


def token_atom_trace(
    samples: list[Sample],
    table: list[dict[str, Any]],
    *,
    mode: str,
    hex_lookup: dict[int, dict[str, str]] | None = None,
    concepts: tuple[str, ...] = ("palindrome", "fibonacci", "gcd", "is_prime"),
    primary: str = "KO",
    max_tokens: int = 16,
) -> list[dict[str, Any]]:
    """Capture readable byte->element traces for a small review subset."""

    traces: list[dict[str, Any]] = []
    lookup = hex_lookup or {}
    for sample in samples:
        if sample.primary != primary or sample.concept not in concepts:
            continue
        tokens = TOKEN_PATTERN.findall(sample.source)[:max_tokens]
        token_rows: list[dict[str, Any]] = []
        for token in tokens:
            token_bytes = token.encode("utf-8")
            elements = [_byte_element(byte, table, mode) for byte in token_bytes]
            hex_rows = [binary_hex_row(byte, lookup) for byte in token_bytes]
            token_rows.append(
                {
                    "token": token,
                    "hex": [row["hex"] for row in hex_rows],
                    "binary": [row["binary"] for row in hex_rows],
                    "hex_source_sheets": [row["source_sheet"] for row in hex_rows],
                    "elements": [str(element.get("symbol") or "?") for element in elements],
                    "categories": [str(element.get("category") or "unknown") for element in elements],
                    "atomic_numbers": [_element_number(element) for element in elements],
                }
            )
        traces.append(
            {
                "concept": sample.concept,
                "primary": sample.primary,
                "path": str(sample.path),
                "tokens": token_rows,
            }
        )
    return traces


def workflow_chain_string(
    source: str,
    table: list[dict[str, Any]],
    hex_lookup: dict[int, dict[str, str]],
    *,
    mode: str,
    max_tokens: int = 64,
) -> str:
    """Compact token->element chain for training ingestion."""

    parts: list[str] = []
    for token in TOKEN_PATTERN.findall(source)[:max_tokens]:
        rows = [binary_hex_row(byte, hex_lookup) for byte in token.encode("utf-8")]
        elements = [_byte_element(int(row["hex"], 16), table, mode) for row in rows]
        element_chain = "-".join(str(element.get("symbol") or "?") for element in elements)
        hex_chain = ".".join(row["hex"].removeprefix("0x").upper() for row in rows)
        parts.append(f"{token}[{hex_chain}|{element_chain}]")
    return " -> ".join(parts)


def workflow_training_records(
    samples: list[Sample],
    sources: list[str],
    table: list[dict[str, Any]],
    hex_lookup: dict[int, dict[str, str]],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    """Create dual-lane semantic chemistry records for downstream training."""

    chemistry_feature = make_binary_hex_chemistry_feature(table, hex_lookup, mode=mode)
    semantic_feature = make_atomic_semantic_overlay_feature()
    flow_feature = make_operational_flow_feature()
    geometry_feature = make_layered_geometry_semantic_feature()
    records: list[dict[str, Any]] = []
    for sample, source in zip(samples, sources):
        records.append(
            {
                "schema_version": "semantic_chemistry_workflow_v1",
                "track": "geoseal_semantic_chemistry_workflow",
                "concept": sample.concept,
                "primary": sample.primary,
                "source_path": str(sample.path),
                "source_sha256": _sha256_text(source),
                "lanes": {
                    "chemistry_actual": {
                        "mapping": "byte -> binary_interpretation_matrix.hex -> periodic_element",
                        "feature": chemistry_feature(source),
                    },
                    "semantic_overlay": {
                        "mapping": "source token -> current atomic tokenizer semantic state",
                        "feature": semantic_feature(source),
                    },
                    "flow_reinforcement": {
                        "mapping": "source text -> operational control and syntax shape",
                        "feature": flow_feature(source),
                    },
                    "layered_geometry_semantic": {
                        "mapping": "source token -> stable outer hull family plus packed inner context metrics",
                        "feature": geometry_feature(source),
                    },
                },
                "workflow_chain": workflow_chain_string(source, table, hex_lookup, mode=mode),
            }
        )
    return records


def _feature_keys_for(features: list[dict[str, float]]) -> list[str]:
    keys: set[str] = set()
    for feature in features:
        keys.update(feature)
    return sorted(keys)


def _loo_nearest_with_keys(features: list[dict[str, float]], concepts: list[str], keys: list[str]) -> list[str]:
    sums: dict[str, dict[str, float]] = {}
    counts: dict[str, int] = {}
    for feature, concept in zip(features, concepts):
        if concept not in sums:
            sums[concept] = {key: 0.0 for key in keys}
            counts[concept] = 0
        for key in keys:
            sums[concept][key] += feature.get(key, 0.0)
        counts[concept] += 1
    predictions: list[str] = []
    for feature, concept in zip(features, concepts):
        best = "UNKNOWN"
        best_distance = math.inf
        for candidate in sorted(sums):
            total = sums[candidate]
            if candidate == concept:
                rest_count = counts[candidate] - 1
                if rest_count <= 0:
                    continue
                prototype = {key: (total[key] - feature.get(key, 0.0)) / rest_count for key in keys}
            else:
                rest_count = counts[candidate]
                prototype = {key: total[key] / rest_count for key in keys}
            distance = math.fsum((feature.get(key, 0.0) - prototype[key]) ** 2 for key in keys)
            if distance < best_distance:
                best_distance = distance
                best = candidate
        predictions.append(best)
    return predictions


def _loo_nearest_with_groups(
    features: list[dict[str, float]],
    concepts: list[str],
    groups: list[str],
    keys: list[str],
) -> list[str]:
    """Leave-one-group-out nearest concept observer.

    This is stricter than normal LOO because no sample from the held-out
    primary/language can contribute to any prototype.
    """

    predictions: list[str] = []
    for index, feature in enumerate(features):
        held_out_group = groups[index]
        sums: dict[str, dict[str, float]] = {}
        counts: dict[str, int] = {}
        for train_feature, train_concept, train_group in zip(features, concepts, groups):
            if train_group == held_out_group:
                continue
            if train_concept not in sums:
                sums[train_concept] = {key: 0.0 for key in keys}
                counts[train_concept] = 0
            for key in keys:
                sums[train_concept][key] += train_feature.get(key, 0.0)
            counts[train_concept] += 1
        best = "UNKNOWN"
        best_distance = math.inf
        for candidate in sorted(sums):
            prototype = {key: sums[candidate][key] / counts[candidate] for key in keys}
            distance = math.fsum((feature.get(key, 0.0) - prototype[key]) ** 2 for key in keys)
            if distance < best_distance:
                best_distance = distance
                best = candidate
        predictions.append(best)
    return predictions


def _normalize_features(features: list[dict[str, float]], keys: list[str]) -> list[dict[str, float]]:
    means: dict[str, float] = {}
    stdevs: dict[str, float] = {}
    n = float(len(features) or 1)
    for key in keys:
        mean = sum(feature.get(key, 0.0) for feature in features) / n
        variance = sum((feature.get(key, 0.0) - mean) ** 2 for feature in features) / n
        means[key] = mean
        stdevs[key] = math.sqrt(variance) or 1.0
    return [{key: (feature.get(key, 0.0) - means[key]) / stdevs[key] for key in keys} for feature in features]


SITUATION_PROFILES: dict[str, dict[str, float]] = {
    "recovery_default": {
        "leave_primary_out": 0.55,
        "renamed": 0.20,
        "shuffle_margin": 0.20,
        "geometry_bonus": 0.00,
        "flow_bonus": 0.00,
        "drop_penalty": 0.15,
        "uncontrolled_penalty": 0.12,
    },
    "geometry_context": {
        "leave_primary_out": 0.42,
        "renamed": 0.14,
        "shuffle_margin": 0.18,
        "geometry_bonus": 0.08,
        "flow_bonus": 0.03,
        "drop_penalty": 0.12,
        "uncontrolled_penalty": 0.12,
    },
    "low_resource_route": {
        "leave_primary_out": 0.38,
        "renamed": 0.18,
        "shuffle_margin": 0.18,
        "geometry_bonus": 0.03,
        "flow_bonus": 0.08,
        "drop_penalty": 0.18,
        "uncontrolled_penalty": 0.16,
    },
}


def _situational_lane_selection(
    summary: list[dict[str, Any]],
    leave_primary_out_summary: list[dict[str, Any]],
    label_shuffle_control: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Select a primary lane per situation from measured lane evidence."""

    summary_by_feature = {row["feature"]: row for row in summary}
    lpo_by_feature = {row["feature"]: row for row in leave_primary_out_summary}
    selections: dict[str, Any] = {}
    for profile_name, weights in SITUATION_PROFILES.items():
        scored: list[dict[str, Any]] = []
        for feature, lpo_row in lpo_by_feature.items():
            summary_row = summary_by_feature.get(feature, {})
            control = label_shuffle_control.get(feature)
            observed = float(lpo_row["accuracy"])
            renamed = float(summary_row.get("renamed", 0.0))
            drop = max(0.0, float(lpo_row.get("drop_from_renamed", 0.0)))
            has_control = control is not None
            passes_control = bool(control and control["risk"] == "passes shuffle control")
            null_p95 = float(control.get("null_p95", 0.0)) if control else 0.0
            shuffle_margin = max(0.0, observed - null_p95) if passes_control else 0.0
            geometry_bonus = 1.0 if "geometry" in feature else 0.0
            flow_bonus = 1.0 if "flow" in feature else 0.0
            score = (
                weights["leave_primary_out"] * observed
                + weights["renamed"] * renamed
                + weights["shuffle_margin"] * shuffle_margin
                + weights["geometry_bonus"] * geometry_bonus
                + weights["flow_bonus"] * flow_bonus
                - weights["drop_penalty"] * drop
                - weights["uncontrolled_penalty"] * (0.0 if has_control else 1.0)
            )
            scored.append(
                {
                    "feature": feature,
                    "score": score,
                    "leave_primary_out": observed,
                    "renamed": renamed,
                    "shuffle_margin": shuffle_margin,
                    "passes_shuffle_control": passes_control,
                    "has_shuffle_control": has_control,
                    "drop_from_renamed": drop,
                    "geometry_bonus_applied": bool(geometry_bonus),
                    "flow_bonus_applied": bool(flow_bonus),
                }
            )
        scored.sort(key=lambda row: row["score"], reverse=True)
        selections[profile_name] = {
            "primary_lane": scored[0]["feature"],
            "formula_weights": weights,
            "ranked_lanes": scored,
        }
    return {
        "version": "situational-lane-selection-v1",
        "rule": (
            "primary lane is selected per situation by weighted leave-primary-out recovery, renamed recovery, "
            "shuffle-null margin, situation bonuses, and penalties for drop/uncontrolled lanes"
        ),
        "profiles": selections,
    }


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def _accuracy_histogram(values: list[float], *, bucket_width: float = 0.05) -> dict[str, int]:
    histogram: dict[str, int] = {}
    if bucket_width <= 0:
        raise ValueError("bucket_width must be positive")
    for value in values:
        lower = math.floor(value / bucket_width) * bucket_width
        upper = min(1.0, lower + bucket_width)
        key = f"{lower:.2f}-{upper:.2f}"
        histogram[key] = histogram.get(key, 0) + 1
    return dict(sorted(histogram.items()))


def _label_shuffle_control(
    samples: list[Sample],
    sources: list[str],
    feature_fns: dict[str, Callable[[str], dict[str, float]]],
    observed_leave_primary_out: dict[str, dict[str, Any]],
    *,
    shuffle_runs: int,
    seed: int,
) -> dict[str, Any]:
    """Balanced null control for leave-primary-out recovery.

    The sample features and primary groups stay fixed. For each held-out
    primary, only labels on the training primaries are permuted. Held-out labels
    remain true and are used for scoring. If the observer still scores high
    after this, the result is likely corpus/style leakage rather than concept
    recovery.
    """

    true_concepts = [sample.concept for sample in samples]
    groups = [sample.primary for sample in samples]
    unique_groups = sorted(set(groups))
    rng = random.Random(seed)
    controls: dict[str, Any] = {}
    for name, feature_fn in feature_fns.items():
        features = [feature_fn(source) for source in sources]
        keys = _feature_keys_for(features)
        if name.startswith(("dual_lane_", "reinforced_")):
            features = _normalize_features(features, keys)
        null_accuracies: list[float] = []
        iteration_seeds: list[int] = []
        marginal_count_checks: list[bool] = []
        for _iteration in range(shuffle_runs):
            iteration_seed = rng.randrange(0, 2**32)
            iteration_rng = random.Random(iteration_seed)
            iteration_seeds.append(iteration_seed)
            predictions: list[str] = ["UNKNOWN"] * len(samples)
            for held_out_group in unique_groups:
                train_indices = [index for index, group in enumerate(groups) if group != held_out_group]
                test_indices = [index for index, group in enumerate(groups) if group == held_out_group]
                shuffled_train_labels = [true_concepts[index] for index in train_indices]
                original_train_counts = Counter(shuffled_train_labels)
                iteration_rng.shuffle(shuffled_train_labels)
                marginal_count_checks.append(Counter(shuffled_train_labels) == original_train_counts)
                sums: dict[str, dict[str, float]] = {}
                counts: dict[str, int] = {}
                for train_index, shuffled_label in zip(train_indices, shuffled_train_labels):
                    if shuffled_label not in sums:
                        sums[shuffled_label] = {key: 0.0 for key in keys}
                        counts[shuffled_label] = 0
                    for key in keys:
                        sums[shuffled_label][key] += features[train_index].get(key, 0.0)
                    counts[shuffled_label] += 1
                for test_index in test_indices:
                    best = "UNKNOWN"
                    best_distance = math.inf
                    for candidate in sorted(sums):
                        prototype = {key: sums[candidate][key] / counts[candidate] for key in keys}
                        distance = math.fsum((features[test_index].get(key, 0.0) - prototype[key]) ** 2 for key in keys)
                        if distance < best_distance:
                            best_distance = distance
                            best = candidate
                    predictions[test_index] = best
            null_accuracies.append(_accuracy(true_concepts, predictions)["accuracy"])
        observed = observed_leave_primary_out[name]["overall"]["accuracy"]
        null_ge_observed = sum(1 for accuracy in null_accuracies if accuracy >= observed)
        empirical_p = (null_ge_observed + 1) / (shuffle_runs + 1)
        null_mean = sum(null_accuracies) / len(null_accuracies) if null_accuracies else 0.0
        null_p95 = _percentile(null_accuracies, 0.95)
        if empirical_p <= 0.05 and null_p95 <= 0.25:
            risk = "passes shuffle control"
        elif empirical_p <= 0.10 and null_p95 <= 0.35:
            risk = "borderline shuffle control"
        else:
            risk = "fails or weak shuffle control"
        controls[name] = {
            "feature": name,
            "observed_leave_primary_out": observed,
            "shuffle_runs": shuffle_runs,
            "seed": seed,
            "null_mean": null_mean,
            "null_p95": null_p95,
            "null_max": max(null_accuracies) if null_accuracies else 0.0,
            "distribution": null_accuracies,
            "histogram": _accuracy_histogram(null_accuracies),
            "iteration_seeds": iteration_seeds,
            "marginal_counts_preserved": all(marginal_count_checks),
            "empirical_p": empirical_p,
            "risk": risk,
        }
    return controls


def _evaluate_within_primary_loo(
    samples: list[Sample],
    sources: list[str],
    feature_fn: Callable[[str], dict[str, float]],
    *,
    feature_name: str,
) -> dict[str, Any]:
    concepts = [sample.concept for sample in samples]
    groups = [sample.primary for sample in samples]
    replicate_counts = Counter((sample.primary, sample.concept) for sample in samples)
    if all(count <= 1 for count in replicate_counts.values()):
        return {
            "feature": feature_name,
            "status": "not_applicable_single_sample_per_concept_per_primary",
            "reason": "within-primary LOO needs at least two samples for the same concept inside a primary; this corpus has one",
            "replicate_count_min": min(replicate_counts.values()) if replicate_counts else 0,
            "replicate_count_max": max(replicate_counts.values()) if replicate_counts else 0,
        }
    features = [feature_fn(source) for source in sources]
    keys = _feature_keys_for(features)
    if feature_name.startswith(("dual_lane_", "reinforced_")):
        features = _normalize_features(features, keys)
    predictions: list[str] = ["UNKNOWN"] * len(samples)
    for group in sorted(set(groups)):
        indices = [index for index, item in enumerate(groups) if item == group]
        group_features = [features[index] for index in indices]
        group_concepts = [concepts[index] for index in indices]
        group_predictions = _loo_nearest_with_keys(group_features, group_concepts, keys)
        for index, prediction in zip(indices, group_predictions):
            predictions[index] = prediction
    return {
        "feature": feature_name,
        "overall": _accuracy(concepts, predictions),
        "per_primary": _per_primary_accuracy(samples, predictions),
    }


def _per_primary_accuracy(samples: list[Sample], predictions: list[str]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for sample, pred in zip(samples, predictions):
        buckets[sample.primary].append((sample.concept, pred))
    return {
        primary: _accuracy(
            [concept for concept, _ in pairs],
            [pred for _, pred in pairs],
        )
        for primary, pairs in sorted(buckets.items())
    }


def _unknown_token_collapse(samples: list[Sample]) -> dict[str, Any]:
    tokens: list[str] = []
    for sample in samples:
        tokens.extend(TOKEN_PATTERN.findall(sample.source)[:200])
    unique = sorted(set(tokens))
    states: dict[str, int] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for token in unique:
        state = map_token_to_atomic_state(token, language="en", context_class="operator")
        key = f"{state.semantic_class}/{state.element.symbol}/{state.tau.as_tuple()}"
        states[key] += 1
        if len(examples[key]) < 8:
            examples[key].append(token)
    total = len(unique)
    most_common = states.most_common(8)
    return {
        "unique_token_count": total,
        "state_count": len(states),
        "top_states": [
            {
                "state": key,
                "unique_tokens": count,
                "fraction": count / total if total else 0.0,
                "examples": examples[key],
            }
            for key, count in most_common
        ],
    }


def _evaluate(
    samples: list[Sample],
    sources: list[str],
    feature_fn: Callable[[str], dict[str, float]],
    *,
    feature_name: str,
) -> dict[str, Any]:
    concepts = [sample.concept for sample in samples]
    features = [feature_fn(source) for source in sources]
    if feature_name == "atomic_current":
        predictions = loo_nearest_concept(features, concepts)
    else:
        keys = _feature_keys_for(features)
        if feature_name.startswith(("dual_lane_", "reinforced_")):
            features = _normalize_features(features, keys)
        predictions = _loo_nearest_with_keys(features, concepts, keys)
    return {
        "feature": feature_name,
        "overall": _accuracy(concepts, predictions),
        "per_concept": _per_concept_accuracy(concepts, predictions),
        "per_primary": _per_primary_accuracy(samples, predictions),
        "predictions": [
            {
                "concept": sample.concept,
                "primary": sample.primary,
                "predicted": pred,
            }
            for sample, pred in zip(samples, predictions)
        ],
    }


def _evaluate_leave_primary_out(
    samples: list[Sample],
    sources: list[str],
    feature_fn: Callable[[str], dict[str, float]],
    *,
    feature_name: str,
) -> dict[str, Any]:
    concepts = [sample.concept for sample in samples]
    groups = [sample.primary for sample in samples]
    features = [feature_fn(source) for source in sources]
    keys = _feature_keys_for(features)
    if feature_name.startswith(("dual_lane_", "reinforced_")):
        features = _normalize_features(features, keys)
    predictions = _loo_nearest_with_groups(features, concepts, groups, keys)
    return {
        "feature": feature_name,
        "overall": _accuracy(concepts, predictions),
        "per_concept": _per_concept_accuracy(concepts, predictions),
        "per_primary": _per_primary_accuracy(samples, predictions),
        "predictions": [
            {
                "concept": sample.concept,
                "primary": sample.primary,
                "predicted": pred,
            }
            for sample, pred in zip(samples, predictions)
        ],
    }


def _comparison_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Atomic Tokenizer Rename Benchmark",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Summary",
        "",
        "| Feature | Baseline | Renamed | Drop | Interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    for row in report["summary"]:
        lines.append("| {feature} | {baseline:.1%} | {renamed:.1%} | {drop:.1%} | {interpretation} |".format(**row))
    lines.extend(
        [
            "",
            "## Leakage Guard",
            "",
            "| Feature | Leave-primary-out | Risk |",
            "|---|---:|---|",
        ]
    )
    for row in report["leave_primary_out_summary"]:
        lines.append("| {feature} | {accuracy:.1%} | {risk} |".format(**row))
    lines.extend(
        [
            "",
            "## Label Shuffle Null Control",
            "",
            "Decision rule: a feature head is training-safe only if its real leave-primary-out score exceeds the 95th percentile of shuffled-label scores.",
            "",
            "| Feature | Real LPO | Shuffle Mean | Shuffle p95 | Shuffle Max | Empirical p | Risk |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report["label_shuffle_control_summary"]:
        lines.append(
            "| {feature} | {observed_leave_primary_out:.1%} | {null_mean:.1%} | {null_p95:.1%} | {null_max:.1%} | {empirical_p:.3f} | {risk} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            f"Training promotion status: **{report['workflow_training_records']['status']}**.",
            report["workflow_training_records"]["status_reason"],
            "",
            "## Within-Primary Diagnostic",
            "",
            report["within_primary_diagnostic"]["note"],
            "",
        ]
    )
    lines.extend(
        [
            "",
            "## Lane Model",
            "",
            f"- Chemistry actual: {report['lane_model']['chemistry_actual']}",
            f"- Semantic overlay: {report['lane_model']['semantic_overlay']}",
            f"- Flow reinforcement: {report['lane_model']['flow_reinforcement']}",
            f"- Fallback rule: {report['lane_model']['fallback_rule']}",
            f"- Selected lane: {report['lane_model']['selected_lane']}",
            f"- Training export: `{report['workflow_training_records']['path']}` ({report['workflow_training_records']['record_count']} records)",
        ]
    )
    lines.extend(
        [
            "",
            "## Atomic Collapse Diagnostic",
            "",
            f"Unique tokens inspected: {report['atomic_collapse']['unique_token_count']}",
            f"Distinct atomic states used: {report['atomic_collapse']['state_count']}",
            "",
            "| State | Unique Tokens | Fraction | Examples |",
            "|---|---:|---:|---|",
        ]
    )
    for row in report["atomic_collapse"]["top_states"]:
        lines.append(
            f"| `{row['state']}` | {row['unique_tokens']} | {row['fraction']:.1%} | {', '.join(row['examples'])} |"
        )
    chemical = report["chemical_distance"]
    lines.extend(
        [
            "",
            "## Byte-Periodic Chemical Distance",
            "",
            f"Mapping mode: `{chemical['mode']}`",
            f"Feature count: {chemical['feature_count']}",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Intra-concept mean distance | {chemical['intra_concept_mean']:.4f} |",
            f"| Inter-concept mean distance | {chemical['inter_concept_mean']:.4f} |",
            f"| Intra / inter ratio | {chemical['intra_inter_ratio']:.4f} |",
            f"| Same-concept cross-primary mean | {chemical['same_concept_cross_primary_mean']:.4f} |",
            f"| Same-primary cross-concept mean | {chemical['same_primary_cross_concept_mean']:.4f} |",
            "",
            "Interpretation: a ratio below 1.0 means same-concept molecule signatures are closer than different-concept signatures. A ratio near or above 1.0 means this byte-periodic head is not yet recovering concept structure.",
            "",
            "## Token Atom Trace Examples",
            "",
        ]
    )
    for trace in report["token_atom_traces"]:
        lines.append(f"### {trace['concept']} / {trace['primary']}")
        lines.append("")
        lines.append("| Token | Bytes | Elements |")
        lines.append("|---|---|---|")
        for token in trace["tokens"][:8]:
            lines.append(
                "| `{token}` | `{bytes}` | `{elements}` |".format(
                    token=token["token"],
                    bytes=" ".join(token["hex"]),
                    elements=" ".join(token["elements"]),
                )
            )
        lines.append("")
    lines.extend(["", "## Renamed Concepts", "", "| Concept | Aliases Removed |", "|---|---|"])
    for concept, aliases in sorted(report["renamed_aliases"].items()):
        lines.append(f"| `{concept}` | {', '.join(aliases) if aliases else '(none)'} |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            report["decision"],
            "",
        ]
    )
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    byte_map_mode: str,
    *,
    shuffle_runs: int = DEFAULT_SHUFFLE_RUNS,
    shuffle_seed: int = DEFAULT_SHUFFLE_SEED,
) -> dict[str, Any]:
    samples = _load_samples(input_dir)
    original_sources = [sample.source for sample in samples]
    renamed_sources: list[str] = []
    renamed_aliases: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        renamed, aliases = anonymize_concept_words(sample.source, sample.concept)
        renamed_sources.append(renamed)
        renamed_aliases[sample.concept].update(aliases)

    table = _load_periodic_table(PERIODIC_TABLE)
    hex_lookup = load_binary_hex_lookup()
    byte_feature = make_byte_periodic_feature(table, mode=byte_map_mode)
    chemistry_feature = make_binary_hex_chemistry_feature(table, hex_lookup, mode=byte_map_mode)
    flow_feature = make_operational_flow_feature()
    semantic_overlay_feature = make_atomic_semantic_overlay_feature()
    geometry_feature = make_layered_geometry_semantic_feature()
    dual_lane_feature = combine_feature_heads(
        [
            ("chemistry", chemistry_feature, 1.0),
            ("semantic", semantic_overlay_feature, 0.35),
        ]
    )
    reinforced_feature = combine_feature_heads(
        [
            ("chemistry", chemistry_feature, 1.0),
            ("semantic", semantic_overlay_feature, 0.35),
            ("flow", flow_feature, 0.75),
        ]
    )
    geometry_reinforced_feature = combine_feature_heads(
        [
            ("chemistry", chemistry_feature, 1.0),
            ("semantic", semantic_overlay_feature, 0.35),
            ("flow", flow_feature, 0.75),
            ("geometry", geometry_feature, 0.60),
        ]
    )
    feature_fns: dict[str, Callable[[str], dict[str, float]]] = {
        "atomic_current": _default_atomic_feature,
        f"byte_periodic_{byte_map_mode}": byte_feature,
        f"chemistry_actual_{byte_map_mode}": chemistry_feature,
        "semantic_overlay_current": semantic_overlay_feature,
        "flow_reinforcement": flow_feature,
        "layered_geometry_semantic": geometry_feature,
        f"dual_lane_chemistry_semantic_{byte_map_mode}": dual_lane_feature,
        f"reinforced_chemistry_semantic_flow_{byte_map_mode}": reinforced_feature,
        f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}": geometry_reinforced_feature,
    }

    evaluations = {
        "atomic_current": {
            "baseline": _evaluate(samples, original_sources, _default_atomic_feature, feature_name="atomic_current"),
            "renamed": _evaluate(samples, renamed_sources, _default_atomic_feature, feature_name="atomic_current"),
        },
        f"byte_periodic_{byte_map_mode}": {
            "baseline": _evaluate(
                samples, original_sources, byte_feature, feature_name=f"byte_periodic_{byte_map_mode}"
            ),
            "renamed": _evaluate(samples, renamed_sources, byte_feature, feature_name=f"byte_periodic_{byte_map_mode}"),
        },
        f"chemistry_actual_{byte_map_mode}": {
            "baseline": _evaluate(
                samples, original_sources, chemistry_feature, feature_name=f"chemistry_actual_{byte_map_mode}"
            ),
            "renamed": _evaluate(
                samples, renamed_sources, chemistry_feature, feature_name=f"chemistry_actual_{byte_map_mode}"
            ),
        },
        "semantic_overlay_current": {
            "baseline": _evaluate(
                samples, original_sources, semantic_overlay_feature, feature_name="semantic_overlay_current"
            ),
            "renamed": _evaluate(
                samples, renamed_sources, semantic_overlay_feature, feature_name="semantic_overlay_current"
            ),
        },
        "flow_reinforcement": {
            "baseline": _evaluate(samples, original_sources, flow_feature, feature_name="flow_reinforcement"),
            "renamed": _evaluate(samples, renamed_sources, flow_feature, feature_name="flow_reinforcement"),
        },
        "layered_geometry_semantic": {
            "baseline": _evaluate(
                samples, original_sources, geometry_feature, feature_name="layered_geometry_semantic"
            ),
            "renamed": _evaluate(samples, renamed_sources, geometry_feature, feature_name="layered_geometry_semantic"),
        },
        f"dual_lane_chemistry_semantic_{byte_map_mode}": {
            "baseline": _evaluate(
                samples,
                original_sources,
                dual_lane_feature,
                feature_name=f"dual_lane_chemistry_semantic_{byte_map_mode}",
            ),
            "renamed": _evaluate(
                samples,
                renamed_sources,
                dual_lane_feature,
                feature_name=f"dual_lane_chemistry_semantic_{byte_map_mode}",
            ),
        },
        f"reinforced_chemistry_semantic_flow_{byte_map_mode}": {
            "baseline": _evaluate(
                samples,
                original_sources,
                reinforced_feature,
                feature_name=f"reinforced_chemistry_semantic_flow_{byte_map_mode}",
            ),
            "renamed": _evaluate(
                samples,
                renamed_sources,
                reinforced_feature,
                feature_name=f"reinforced_chemistry_semantic_flow_{byte_map_mode}",
            ),
        },
        f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}": {
            "baseline": _evaluate(
                samples,
                original_sources,
                geometry_reinforced_feature,
                feature_name=f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}",
            ),
            "renamed": _evaluate(
                samples,
                renamed_sources,
                geometry_reinforced_feature,
                feature_name=f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}",
            ),
        },
    }
    leave_primary_out = {
        name: _evaluate_leave_primary_out(
            samples,
            renamed_sources,
            feature_fns[name],
            feature_name=name,
        )
        for name in evaluations
    }
    shuffle_feature_fns = {
        name: feature_fns[name]
        for name in (
            f"chemistry_actual_{byte_map_mode}",
            "layered_geometry_semantic",
            f"dual_lane_chemistry_semantic_{byte_map_mode}",
            f"reinforced_chemistry_semantic_flow_{byte_map_mode}",
            f"reinforced_chemistry_semantic_flow_geometry_{byte_map_mode}",
        )
    }
    label_shuffle_control = _label_shuffle_control(
        samples,
        renamed_sources,
        shuffle_feature_fns,
        leave_primary_out,
        shuffle_runs=shuffle_runs,
        seed=shuffle_seed,
    )
    label_shuffle_control_summary = [
        {key: value for key, value in control.items() if key != "distribution"}
        for control in label_shuffle_control.values()
    ]

    summary = []
    for name, result in evaluations.items():
        baseline = result["baseline"]["overall"]["accuracy"]
        renamed = result["renamed"]["overall"]["accuracy"]
        drop = baseline - renamed
        if name == "atomic_current" and renamed <= (1 / len({s.concept for s in samples}) + 0.03):
            interpretation = "current atomic signal is mostly lexical or override-table leakage"
        elif drop > 0.10:
            interpretation = "rename-sensitive signal"
        else:
            interpretation = "rename-stable under this feature head"
        summary.append(
            {
                "feature": name,
                "baseline": baseline,
                "renamed": renamed,
                "drop": drop,
                "interpretation": interpretation,
            }
        )

    best = max(summary, key=lambda row: row["renamed"])
    leave_primary_out_summary = []
    for name, result in leave_primary_out.items():
        accuracy = result["overall"]["accuracy"]
        renamed_accuracy = evaluations[name]["renamed"]["overall"]["accuracy"]
        drop = renamed_accuracy - accuracy
        if drop > 0.25:
            risk = "high same-primary/style dependence"
        elif drop > 0.10:
            risk = "moderate same-primary/style dependence"
        else:
            risk = "low additional leave-primary-out drop"
        leave_primary_out_summary.append(
            {
                "feature": name,
                "accuracy": accuracy,
                "drop_from_renamed": drop,
                "risk": risk,
            }
        )
    selected_lane = max(
        leave_primary_out_summary,
        key=lambda row: (row["accuracy"], -row["drop_from_renamed"]),
    )
    situational_lane_selection = _situational_lane_selection(
        summary,
        leave_primary_out_summary,
        label_shuffle_control,
    )
    selected_control = label_shuffle_control.get(selected_lane["feature"])
    if selected_control and selected_control["risk"] == "passes shuffle control":
        training_status = "candidate"
        training_status_reason = "Selected lane passed the pre-committed label-shuffle control; export remains a candidate training input, not a promoted dataset."
    else:
        training_status = "hold"
        if selected_control:
            training_status_reason = "Selected lane did not cleanly pass the label-shuffle null control; export is generated for inspection only and must not be promoted to training."
        else:
            training_status_reason = "Selected lane was not included in the shuffle control; export is generated for inspection only and must not be promoted to training."
    within_primary = {
        name: _evaluate_within_primary_loo(
            samples,
            renamed_sources,
            feature_fns[name],
            feature_name=name,
        )
        for name in shuffle_feature_fns
    }
    within_primary_diagnostic = {
        "feature_heads": within_primary,
        "note": "Within-primary LOO is not applicable to the current corpus because each primary has one sample per concept. Use same-primary cross-concept distance and leave-primary-out/null controls for this corpus, or add replicated implementations per concept/primary.",
    }
    decision = (
        "Keep the chemistry lane and semantic lane separate in evidence. The actual chemistry lane is "
        "byte -> workbook hex/binary -> periodic element features; the semantic lane is the current "
        "atomic-tokenizer overlay. Do not force early fusion when it reduces measured recovery; use the "
        "best lane selector first, then add flow or semantic reinforcement only when a task-specific eval "
        f"improves. Best renamed accuracy in this run: {best['feature']} at {best['renamed']:.1%}. "
        f"Best leave-primary-out lane: {selected_lane['feature']} at {selected_lane['accuracy']:.1%}. "
        f"Training export status after shuffle control: {training_status}."
    )

    report = {
        "version": "atomic-tokenizer-rename-benchmark-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "sample_count": len(samples),
        "concept_count": len({sample.concept for sample in samples}),
        "primary_count": len({sample.primary for sample in samples}),
        "byte_map_mode": byte_map_mode,
        "binary_hex_lookup": {
            "source": str(BINARY_MATRIX_SFT),
            "row_count": len(hex_lookup),
            "sheets": sorted({row["source_sheet"] for row in hex_lookup.values()}),
            "coverage": {
                "explicit_min": min(hex_lookup) if hex_lookup else None,
                "explicit_max": max(hex_lookup) if hex_lookup else None,
            },
        },
        "lane_model": {
            "chemistry_actual": "byte -> Binary Interpretation Matrix hex/binary row -> periodic element trace",
            "semantic_overlay": "current atomic tokenizer feature head; kept separate because it collapses most code identifiers",
            "flow_reinforcement": "rename-stable operational syntax and control-flow shape features; only promoted if its own eval improves the task",
            "layered_geometry_semantic": "stable outer token hull plus inner packed context metrics; promoted only if leave-primary-out and shuffle-null controls hold",
            "fallback_rule": "select the best validated lane per task instead of forcing chemistry, semantics, and flow into one vector",
            "selected_lane": selected_lane["feature"],
        },
        "situational_lane_selection": situational_lane_selection,
        "layered_geometry_probe": asdict(geometry_feature.geometry_probe),  # type: ignore[attr-defined]
        "summary": summary,
        "evaluations": evaluations,
        "leave_primary_out": leave_primary_out,
        "leave_primary_out_summary": leave_primary_out_summary,
        "label_shuffle_control": label_shuffle_control,
        "label_shuffle_control_summary": label_shuffle_control_summary,
        "within_primary_diagnostic": within_primary_diagnostic,
        "renamed_aliases": {key: sorted(value) for key, value in renamed_aliases.items()},
        "atomic_collapse": _unknown_token_collapse(samples),
        "chemical_distance": chemical_distance_report(samples, original_sources, table, mode=byte_map_mode),
        "token_atom_traces": token_atom_trace(samples, table, mode=byte_map_mode, hex_lookup=hex_lookup),
        "workflow_training_records": {
            "path": str(output_dir / "semantic_chemistry_workflows.jsonl"),
            "schema_version": "semantic_chemistry_workflow_v1",
            "record_count": len(samples),
            "status": training_status,
            "status_reason": training_status_reason,
        },
        "decision": decision,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rename_benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "comparison.md").write_text(_comparison_markdown(report), encoding="utf-8")
    (output_dir / "renamed_manifest.json").write_text(
        json.dumps(
            {
                "version": "atomic-tokenizer-renamed-corpus-manifest-v1",
                "source": str(input_dir),
                "samples": [
                    {
                        "concept": sample.concept,
                        "primary": sample.primary,
                        "source_sha256": _sha256_text(sample.source),
                        "renamed_sha256": _sha256_text(renamed),
                    }
                    for sample, renamed in zip(samples, renamed_sources)
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    workflow_records = workflow_training_records(samples, original_sources, table, hex_lookup, mode=byte_map_mode)
    with (output_dir / "semantic_chemistry_workflows.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in workflow_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--byte-map-mode",
        choices=["mod", "stride", "hex", "hash"],
        default="hex",
        help="Byte to periodic table index mapping for the experimental byte head.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run(args.input_dir, args.output_dir, args.byte_map_mode)
    if args.json:
        print(json.dumps(report["summary"], indent=2))
    else:
        print((args.output_dir / "comparison.md").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
