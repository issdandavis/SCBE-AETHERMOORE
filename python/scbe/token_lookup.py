"""Token lookup table rows for SCBE's semantic chemistry/tokenizer layer.

The goal is the tokenizer equivalent of an atomic lookup table: a compact,
deterministic record that tells an agent what a token is, how it is encoded, how
it behaves in the semantic-periodic lattice, and whether it is also a real
chemical element/formula with a dimensional ledger.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .atomic_tokenization import chemical_element, map_token_to_atomic_state
from .chemistry_dimensions import ChemistryDimensionError, analyze_formula, element_dimension


TOKEN_LOOKUP_CLAIM_BOUNDARY = [
    "token lookup is deterministic representation metadata",
    "semantic element rows are SCBE tokenizer classes, not physical atoms",
    "material chemistry dimensions appear only when the token is a known element or formula",
    "not wet-lab synthesis, kinetics, toxicity, dosing, or bioactivity advice",
]


def _byte_signature(token: str) -> dict[str, Any]:
    data = token.encode("utf-8")
    return {
        "byte_count": len(data),
        "bit_count": len(data) * 8,
        "hex": [f"0x{byte:02X}" for byte in data],
        "popcount": [byte.bit_count() for byte in data],
        "bit_density": (
            round(sum(byte.bit_count() for byte in data) / float(len(data) * 8), 6)
            if data
            else 0.0
        ),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _state_row(state: Any) -> dict[str, Any]:
    element = state.element
    return {
        "semantic_class": state.semantic_class,
        "semantic_element": {
            "symbol": element.symbol,
            "Z": element.Z,
            "group": element.group,
            "period": element.period,
            "valence": element.valence,
            "electronegativity": round(float(element.electronegativity), 6),
            "witness_stable": element.witness_stable,
        },
        "tau": state.tau.as_dict(),
        "negative_state": state.negative_state,
        "dual_state": state.dual_state,
        "band_flag": state.band_flag,
        "witness_state": state.witness_state,
        "resilience": round(float(state.resilience), 6),
        "adaptivity": round(float(state.adaptivity), 6),
        "trust_baseline": round(float(state.trust_baseline), 6),
    }


def _material_row(token: str) -> dict[str, Any] | None:
    element = chemical_element(token)
    if element is not None:
        try:
            physical = element_dimension(element.symbol)
        except ChemistryDimensionError:
            return {
                "kind": "element",
                "symbol": element.symbol,
                "periodic_semantic": {
                    "Z": element.Z,
                    "group": element.group,
                    "period": element.period,
                    "valence": element.valence,
                    "electronegativity": element.electronegativity,
                },
                "dimensions": None,
            }
        dimensions = analyze_formula(element.symbol)
        return {
            "kind": "element",
            "symbol": element.symbol,
            "atomic_number": physical.atomic_number,
            "mass_number_common_isotope": physical.mass_number,
            "common_neutrons": physical.common_neutrons,
            "atomic_weight": physical.atomic_weight,
            "dimensions": dimensions,
        }
    try:
        dimensions = analyze_formula(token)
    except (ChemistryDimensionError, ValueError):
        return None
    return {
        "kind": "formula",
        "formula": token,
        "dimensions": dimensions,
    }


def lookup_token(
    token: str,
    *,
    language: str | None = None,
    context_class: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic atomic-style lookup row for one token."""

    state = map_token_to_atomic_state(token, language=language, context_class=context_class)
    material = _material_row(token)
    workflow_unit = None
    try:
        from src.tokenizer.atomic_workflow_units import build_atomic_workflow_unit

        workflow_unit = build_atomic_workflow_unit(token)
    except Exception:
        workflow_unit = None
    return {
        "schema_version": "scbe_token_lookup_v1",
        "token": token,
        "language": language,
        "context_class": context_class,
        "byte_signature": _byte_signature(token),
        "semantic": _state_row(state),
        "workflow_unit": workflow_unit,
        "material": material,
        "lookup_axes": [
            "bytes",
            "semantic_class",
            "semantic_element",
            "tau",
            "workflow_band",
            "material_dimensions",
        ],
        "claim_boundary": list(TOKEN_LOOKUP_CLAIM_BOUNDARY),
    }


def lookup_tokens(
    tokens: list[str],
    *,
    language: str | None = None,
    context_class: str | None = None,
) -> dict[str, Any]:
    """Return lookup rows for several tokens."""

    return {
        "schema_version": "scbe_token_lookup_batch_v1",
        "tokens": tokens,
        "rows": [
            lookup_token(token, language=language, context_class=context_class)
            for token in tokens
        ],
        "claim_boundary": list(TOKEN_LOOKUP_CLAIM_BOUNDARY),
    }
