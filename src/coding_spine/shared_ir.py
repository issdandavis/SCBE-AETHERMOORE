"""
Coding Spine — Shared Semantic IR
=================================

Canonical substrate for cross-language coding alignment.

The transport tokenizer is already bijective. This module gives the coding lane
the same property at the semantic level by lowering language-specific requests
into a shared op-centric IR, then attaching a first-class operator family
record: invariant, witnesses, blockers, and substitute routes.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Optional

from src.ca_lexicon import lookup

from .router import RouteResult, TONGUE_FULL_NAME, TONGUE_LANGUAGE, route_task

_OP_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("add", (" add ", "sum", "plus", "combine")),
    ("sub", ("subtract", "minus", "difference")),
    ("mul", ("multiply", "product", "times")),
    ("div", ("divide", "quotient")),
    ("mod", ("modulo", "remainder")),
    ("pow", ("power", "exponent", "raised to")),
    ("sqrt", ("square root", "sqrt")),
    ("min", ("minimum", "smallest", "lower bound")),
    ("max", ("maximum", "largest", "upper bound")),
    ("sum", ("aggregate sum", "total", "sum over")),
    ("product", ("aggregate product",)),
    ("mean", ("mean", "average")),
    ("variance", ("variance",)),
    ("stdev", ("standard deviation", "stddev", "stdev")),
    ("reduce", ("reduce", "fold left")),
    ("fold", ("fold",)),
    ("scan", ("scan", "prefix sum")),
    ("filter", ("filter", "keep only", "select only")),
    ("map", ("map", "transform each")),
    ("zip", ("zip", "pairwise combine")),
    ("unzip", ("unzip", "split pairs")),
    ("sort", ("sort", "ordered", "ordering")),
    ("unique", ("unique", "deduplicate", "distinct")),
    ("count", ("count", "frequency")),
    ("clamp", ("clamp", "bound between")),
)

_BAND_DEFAULTS: dict[str, dict[str, object]] = {
    "ARITHMETIC": {
        "input_shape": "numeric_scalars_or_sequences",
        "output_shape": "numeric_scalar_or_sequence",
        "reversible": False,
        "conservation_rule": "preserve operand slots and arithmetic intent",
    },
    "COMPARISON": {
        "input_shape": "comparable_values",
        "output_shape": "boolean_or_selection_mask",
        "reversible": False,
        "conservation_rule": "preserve compared fields and predicate semantics",
    },
    "LOGIC": {
        "input_shape": "boolean_or_predicate_inputs",
        "output_shape": "boolean_or_branch_decision",
        "reversible": False,
        "conservation_rule": "preserve truth-condition semantics under translation",
    },
    "AGGREGATION": {
        "input_shape": "iterable_or_stream",
        "output_shape": "reduced_or_transformed_collection",
        "reversible": False,
        "conservation_rule": "preserve slot alignment, ordering contract, and reduction target",
    },
}

_OPERATOR_OVERRIDES: dict[str, dict[str, object]] = {
    "map": {
        "input_shape": "sequence_plus_transform",
        "output_shape": "sequence_same_arity",
        "conservation_rule": "preserve sequence cardinality and per-slot transform intent",
        "equivalence_group": "map_transform",
        "fallback_ops": ["reduce"],
    },
    "filter": {
        "input_shape": "sequence_plus_predicate",
        "output_shape": "sequence_subset",
        "conservation_rule": "preserve order of retained slots and predicate meaning",
        "equivalence_group": "filter_select",
        "fallback_ops": ["reduce"],
    },
    "reduce": {
        "input_shape": "sequence_plus_accumulator",
        "output_shape": "single_accumulated_value",
        "conservation_rule": "preserve accumulator identity and fold order contract",
        "equivalence_group": "reduce_fold",
        "fallback_ops": ["fold", "scan"],
    },
    "fold": {
        "input_shape": "sequence_plus_accumulator",
        "output_shape": "single_accumulated_value",
        "conservation_rule": "preserve fold direction and accumulator semantics",
        "equivalence_group": "reduce_fold",
        "fallback_ops": ["reduce", "scan"],
    },
    "scan": {
        "input_shape": "sequence_plus_accumulator",
        "output_shape": "prefix_sequence",
        "conservation_rule": "preserve prefix accumulation semantics",
        "equivalence_group": "reduce_fold",
        "fallback_ops": ["reduce", "fold"],
    },
    "zip": {
        "input_shape": "two_sequences",
        "output_shape": "paired_sequence",
        "reversible": True,
        "conservation_rule": "preserve left/right slot pairing",
        "equivalence_group": "zip_pair",
        "fallback_ops": ["map"],
    },
    "unzip": {
        "input_shape": "paired_sequence",
        "output_shape": "two_sequences",
        "reversible": True,
        "conservation_rule": "preserve pair decomposition into original slots",
        "equivalence_group": "zip_pair",
        "fallback_ops": ["map"],
    },
    "sort": {
        "input_shape": "sequence_plus_ordering",
        "output_shape": "ordered_sequence",
        "conservation_rule": "preserve elements while changing only order",
        "equivalence_group": "sort_order",
        "fallback_ops": ["unique"],
    },
    "unique": {
        "input_shape": "sequence",
        "output_shape": "deduplicated_sequence",
        "conservation_rule": "preserve first-class values while removing duplicate witnesses",
        "equivalence_group": "sort_order",
        "fallback_ops": ["sort", "count"],
    },
    "count": {
        "input_shape": "sequence",
        "output_shape": "frequency_table_or_scalar",
        "conservation_rule": "preserve frequency semantics of repeated values",
        "equivalence_group": "count_frequency",
        "fallback_ops": ["reduce"],
    },
}

_DEFAULT_BLOCKERS: tuple[dict[str, str], ...] = (
    {
        "id": "runtime_unavailable",
        "condition": "requested runtime not installed or disabled",
        "substitute_rule": "route to a witness lane with a live runtime or emit-only path",
    },
    {
        "id": "syntax_path_blocked",
        "condition": "primary language fails syntax or compiler checks",
        "substitute_rule": "retry in an equivalent operator witness with simpler syntax surface",
    },
    {
        "id": "latency_budget_exceeded",
        "condition": "provider or toolchain exceeds current time budget",
        "substitute_rule": "route to a cheaper witness lane or accumulator-style fallback",
    },
)


def _normalize_text(task: str) -> str:
    text = " " + re.sub(r"\s+", " ", task.strip().lower()) + " "
    return text


def _infer_op(task: str) -> Optional[str]:
    text = _normalize_text(task)
    for op_name, hints in _OP_PATTERNS:
        if any(hint in text for hint in hints):
            return op_name
    return None


@dataclass(frozen=True)
class SemanticIR:
    family: str
    op: Optional[str]
    band: Optional[str]
    valence: Optional[int]
    tongue: str
    language: str
    signature: str
    task: str
    operator_family: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def infer_semantic_ir(task: str, *, force_tongue: Optional[str] = None) -> SemanticIR:
    route: RouteResult = route_task(task, force_tongue=force_tongue)
    op_name = _infer_op(task)

    if op_name is None:
        return SemanticIR(
            family="freeform",
            op=None,
            band=None,
            valence=None,
            tongue=route.tongue,
            language=route.language,
            signature=f"freeform:{route.tongue}:{route.language.lower()}",
            task=task,
            operator_family={},
        )

    entry = lookup(op_name)
    operator_family = build_operator_family_record(
        entry.name,
        primary_tongue=route.tongue,
        primary_language=route.language,
    )
    return SemanticIR(
        family="lexicon_op",
        op=entry.name,
        band=entry.band,
        valence=entry.valence,
        tongue=route.tongue,
        language=route.language,
        signature=f"op:{entry.name}:{entry.band}:v{entry.valence}",
        task=task,
        operator_family=operator_family,
    )


def equivalent_ir(left: SemanticIR, right: SemanticIR) -> bool:
    return left.signature == right.signature


def build_operator_family_record(
    op_name: str,
    *,
    primary_tongue: str,
    primary_language: str,
) -> dict:
    """Return the canonical operator-family record for a shared coding command."""
    entry = lookup(op_name)
    base = dict(_BAND_DEFAULTS.get(entry.band, {}))
    base.update(_OPERATOR_OVERRIDES.get(entry.name, {}))
    equivalence_group = str(base.get("equivalence_group", entry.name))
    witnesses = []
    for tongue, language in TONGUE_LANGUAGE.items():
        witness_kind = "primary" if tongue == primary_tongue else "equivalent"
        witnesses.append(
            {
                "tongue": tongue,
                "tongue_name": TONGUE_FULL_NAME[tongue],
                "language": language,
                "witness_kind": witness_kind,
                "equivalence_group": equivalence_group,
                "preferred": tongue == primary_tongue,
            }
        )
    fallback_ops = [str(item) for item in base.get("fallback_ops", [])]
    fallback_routes = []
    for fallback in fallback_ops:
        for tongue, language in TONGUE_LANGUAGE.items():
            fallback_routes.append(
                {
                    "op": fallback,
                    "tongue": tongue,
                    "language": language,
                    "reason": f"use {fallback} witness when {entry.name} is blocked or expensive",
                }
            )
    return {
        "op": entry.name,
        "band": entry.band,
        "valence": entry.valence,
        "equivalence_group": equivalence_group,
        "primary_route": {
            "tongue": primary_tongue,
            "language": primary_language,
        },
        "input_shape": base.get("input_shape", "unknown"),
        "output_shape": base.get("output_shape", "unknown"),
        "reversible": bool(base.get("reversible", False)),
        "conservation_rule": base.get("conservation_rule", "preserve semantic intent"),
        "witnesses": witnesses,
        "blockers": list(_DEFAULT_BLOCKERS),
        "fallback_routes": fallback_routes,
    }
