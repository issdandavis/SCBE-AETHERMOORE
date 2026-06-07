"""Code cell-division lane.

Treat source code as a parent organism and lexical segments as child cells. Each
child keeps enough span/text data to reconstruct the parent exactly, while
non-whitespace cells also carry atomic tokenizer state and optional CA-prime
identity when the token names a known opcode.

This is a coding-agent lane, not a biological claim:

    parent code organism -> child token cells -> atomic state/fusion -> exact recomposition
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .atomic_tokenization import AtomicTokenState, map_token_to_atomic_state
from .chemical_fusion import FusionResult, fuse_atomic_states
from .prime_ir import prime_for_op_name
from .reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
    sha256_value,
)

_CELL_RE = re.compile(
    r"\s+|[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|==|!=|<=|>=|->|=>|::|[^\s]",
    re.UNICODE,
)


@dataclass(frozen=True)
class CodeCell:
    """One child cell produced by dividing a code organism."""

    cell_id: str
    parent_id: str
    generation: int
    text: str
    start: int
    end: int
    kind: str
    atomic_state: AtomicTokenState | None
    ca_prime: int | None

    def to_dict(self) -> dict[str, Any]:
        state = self.atomic_state
        return {
            "cell_id": self.cell_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "kind": self.kind,
            "ca_prime": self.ca_prime,
            "atomic": (
                None
                if state is None
                else {
                    "semantic_class": state.semantic_class,
                    "element": state.element.symbol,
                    "tau": state.tau.as_dict(),
                    "negative_state": state.negative_state,
                    "trust_baseline": state.trust_baseline,
                }
            ),
        }


@dataclass(frozen=True)
class CodeOrganismDivision:
    """Result of dividing source code into exact child cells."""

    parent_id: str
    language: str
    source_sha256: str
    cells: tuple[CodeCell, ...]
    fusion: FusionResult | None
    reaction_packet: ReactionStatePacket

    @property
    def reconstructed_source(self) -> str:
        return "".join(cell.text for cell in self.cells)

    @property
    def identity_preserved(self) -> bool:
        return (
            self.reaction_packet.classification == "BIJECTIVE"
            and self.reaction_packet.verify_hash()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scbe_code_cell_division_v1",
            "parent_id": self.parent_id,
            "language": self.language,
            "source_sha256": self.source_sha256,
            "cell_count": len(self.cells),
            "cells": [cell.to_dict() for cell in self.cells],
            "fusion": (
                None
                if self.fusion is None
                else {
                    "tau_hat": self.fusion.tau_hat,
                    "reconstruction_votes": self.fusion.reconstruction_votes,
                    "signed_edge_tension": self.fusion.signed_edge_tension,
                    "coherence_penalty": self.fusion.coherence_penalty,
                    "valence_pressure": self.fusion.valence_pressure,
                }
            ),
            "reaction_packet": self.reaction_packet.to_dict(),
        }


def divide_code_organism(
    source: str, *, language: str = "python", parent_id: str = "code:root"
) -> CodeOrganismDivision:
    """Divide source into exact lexical cells and attach atomic/prime metadata."""
    cells: list[CodeCell] = []
    atomic_states: list[AtomicTokenState] = []

    pos = 0
    for index, match in enumerate(_CELL_RE.finditer(source)):
        if match.start() != pos:
            raise ValueError("tokenizer skipped source bytes")
        text = match.group(0)
        kind = _classify_cell(text)
        atomic_state = None
        ca_prime = None
        if kind != "whitespace":
            atomic_state = map_token_to_atomic_state(
                text, language=language, context_class="operator"
            )
            atomic_states.append(atomic_state)
            ca_prime = _maybe_ca_prime(text)
        cells.append(
            CodeCell(
                cell_id=f"{parent_id}:g1:{index}",
                parent_id=parent_id,
                generation=1,
                text=text,
                start=match.start(),
                end=match.end(),
                kind=kind,
                atomic_state=atomic_state,
                ca_prime=ca_prime,
            )
        )
        pos = match.end()
    if pos != len(source):
        raise ValueError("tokenizer did not consume the full source")

    reconstructed = "".join(cell.text for cell in cells)
    identity_ok = reconstructed == source
    fusion = fuse_atomic_states(atomic_states) if atomic_states else None
    packet = build_reaction_state_packet(
        domain="code",
        step=1,
        bounded_operation="cell_division",
        source=ReactionEndpoint(
            identity=parent_id,
            representation="source_text",
            language=language,
            payload_sha256=sha256_value(source),
        ),
        target=ReactionEndpoint(
            identity=f"{parent_id}:cell_lineage",
            representation="code_cell_lineage",
            language=language,
            payload_sha256=sha256_value([cell.to_dict() for cell in cells]),
            metadata={"cell_count": len(cells)},
        ),
        semantic_engravings=["source text divided into exact child cells"],
        loss_notes=[] if identity_ok else ["source text did not reconstruct exactly"],
        recalculation=ReactionRecalculation(
            identity_ok=identity_ok, extra={"cell_count": len(cells)}
        ),
        identity_preserved=identity_ok,
        claim_boundary=[
            "cell division is a coding-agent representation lane",
            "biological analogy is operational, not biological evidence",
        ],
    )
    return CodeOrganismDivision(
        parent_id=parent_id,
        language=language,
        source_sha256=sha256_value(source),
        cells=tuple(cells),
        fusion=fusion,
        reaction_packet=packet,
    )


def _classify_cell(text: str) -> str:
    if text.isspace():
        return "whitespace"
    if text.isidentifier():
        return "identifier"
    if text.replace(".", "", 1).isdigit():
        return "number"
    if text in {"(", ")", "{", "}", "[", "]", ",", ":", ";"}:
        return "boundary"
    return "operator"


def _maybe_ca_prime(text: str) -> int | None:
    try:
        return prime_for_op_name(text)
    except ValueError:
        return None
