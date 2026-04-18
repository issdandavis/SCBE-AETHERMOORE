"""
Coding Spine — Shared Semantic IR
=================================

Minimal canonical substrate for dual-strand coding tests.

The transport tokenizer is already bijective. This module gives the coding lane
the same property at the semantic level for a narrow primitive set by lowering
language-specific requests into a shared op-centric IR.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Optional

from src.ca_lexicon import lookup

from .router import RouteResult, route_task


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
        )

    entry = lookup(op_name)
    return SemanticIR(
        family="lexicon_op",
        op=entry.name,
        band=entry.band,
        valence=entry.valence,
        tongue=route.tongue,
        language=route.language,
        signature=f"op:{entry.name}:{entry.band}:v{entry.valence}",
        task=task,
    )


def equivalent_ir(left: SemanticIR, right: SemanticIR) -> bool:
    return left.signature == right.signature

