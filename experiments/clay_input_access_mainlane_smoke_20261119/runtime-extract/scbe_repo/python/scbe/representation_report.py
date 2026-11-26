"""Combined chemistry/tokenizer representation reports.

This is the next layer above one-token lookup: take an input string, tokenize it,
look up each token, and summarize the representation across semantic atoms,
material chemistry dimensions, trit/tau totals, and workflow resource costs.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .token_lookup import TOKEN_LOOKUP_CLAIM_BOUNDARY, lookup_tokens

REPRESENTATION_REPORT_CLAIM_BOUNDARY = [
    "representation report combines tokenizer metadata with formula-level chemistry dimensions",
    "semantic atoms are SCBE representation classes, not physical atoms",
    "material totals include only tokens recognized as element symbols or formulas",
    "not wet-lab synthesis, kinetics, toxicity, dosing, or bioactivity advice",
]


def representation_tokens(text: str) -> list[str]:
    """Tokenize text for chemistry/tokenizer representation lookup."""

    return re.findall(r"[A-Za-z0-9_^+\-()']+|[^\s]", text or "")


def _empty_material_totals() -> dict[str, float | int]:
    return {
        "atoms": 0,
        "protons": 0,
        "neutrons_common_isotope": 0,
        "electrons": 0,
        "mass_number_common_isotope": 0,
        "molar_mass_g_mol": 0.0,
        "charge": 0,
    }


def _add_totals(left: dict[str, Any], right: dict[str, Any]) -> None:
    for key in left:
        left[key] += right[key]
    left["molar_mass_g_mol"] = round(float(left["molar_mass_g_mol"]), 6)


def _resource_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in rows:
        unit = row.get("workflow_unit") or {}
        for key, value in (unit.get("resource_cost") or {}).items():
            totals[key] = round(totals.get(key, 0.0) + float(value), 6)
    return totals


def build_representation_report(
    text: str,
    *,
    language: str | None = None,
    context_class: str | None = None,
) -> dict[str, Any]:
    """Build a compact report connecting token lookup and material dimensions."""

    tokens = representation_tokens(text)
    lookup = lookup_tokens(tokens, language=language, context_class=context_class)
    rows = lookup["rows"]
    semantic_counts = Counter(row["semantic"]["semantic_class"] for row in rows)
    semantic_elements = Counter(row["semantic"]["semantic_element"]["symbol"] for row in rows)
    tau_totals: dict[str, int] = {}
    material_hits: list[dict[str, Any]] = []
    material_totals = _empty_material_totals()
    for row in rows:
        for tongue, value in row["semantic"]["tau"].items():
            tau_totals[tongue] = tau_totals.get(tongue, 0) + int(value)
        material = row.get("material")
        if material and material.get("dimensions"):
            dimensions = material["dimensions"]
            material_hits.append(
                {
                    "token": row["token"],
                    "kind": material["kind"],
                    "formula": dimensions["formula"],
                    "totals": dimensions["totals"],
                }
            )
            _add_totals(material_totals, dimensions["totals"])
    return {
        "schema_version": "scbe_representation_report_v1",
        "text": text,
        "tokens": tokens,
        "token_count": len(tokens),
        "lookup_units": rows,
        "summary": {
            "semantic_class_counts": dict(sorted(semantic_counts.items())),
            "semantic_element_counts": dict(sorted(semantic_elements.items())),
            "tau_totals": dict(sorted(tau_totals.items())),
            "workflow_resource_totals": _resource_totals(rows),
            "material_hit_count": len(material_hits),
            "material_hits": material_hits,
            "material_totals": material_totals,
        },
        "claim_boundary": [
            *REPRESENTATION_REPORT_CLAIM_BOUNDARY,
            *TOKEN_LOOKUP_CLAIM_BOUNDARY,
        ],
    }
