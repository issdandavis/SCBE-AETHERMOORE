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
from hashlib import sha256
from typing import Any, Optional

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


@dataclass(frozen=True)
class RouteIR:
    """Canonical replayable execution contract for code and task lanes."""

    schema_version: str
    semantic: dict[str, Any]
    source: dict[str, Any]
    route: dict[str, Any]
    backend: dict[str, Any]
    execution_policy: dict[str, Any]
    hashes: dict[str, str]
    replay: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
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


def build_route_ir(
    *,
    task: str,
    source_text: str,
    source_language: str,
    source_name: str,
    force_tongue: Optional[str] = None,
    selected_backend: Optional[str] = None,
    available_backends: Optional[list[str]] = None,
    timeout_seconds: float = 10.0,
) -> RouteIR:
    """Build a canonical execution contract used by explain/history/replay."""
    semantic = infer_semantic_ir(task, force_tongue=force_tongue)
    canonical_task = task.strip()
    canonical_source = source_text.replace("\r\n", "\n")
    task_hash = sha256(canonical_task.encode("utf-8")).hexdigest()
    source_hash = sha256(canonical_source.encode("utf-8")).hexdigest()
    plan_key = sha256(
        f"{semantic.signature}|{source_hash}|{source_language.lower()}".encode("utf-8")
    ).hexdigest()
    backend = selected_backend or (
        available_backends[0] if available_backends else "none"
    )
    return RouteIR(
        schema_version="scbe_route_ir_v1",
        semantic=semantic.to_dict(),
        source={
            "name": source_name,
            "language": source_language.lower(),
            "byte_length": len(canonical_source.encode("utf-8")),
        },
        route={
            "tongue": semantic.tongue,
            "language": semantic.language.lower(),
            "signature": semantic.signature,
        },
        backend={
            "selected": backend,
            "candidates": list(available_backends or []),
        },
        execution_policy={
            "timeout_seconds": timeout_seconds,
            "deterministic": True,
            "sandbox_mode": "bounded-subprocess",
        },
        hashes={
            "task_sha256": task_hash,
            "source_sha256": source_hash,
            "plan_sha256": plan_key,
        },
        replay={
            "strategy": "plan+source+route",
            "replay_key": plan_key,
        },
    )
