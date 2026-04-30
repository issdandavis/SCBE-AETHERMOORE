"""Aligned-foundations cross-lane concept-preservation primitives.

Implements the canonical promotion gate for the ``aligned_foundations`` bucket
of ``config/model_training/scbe_dataset_regularization_v1.json``:

  eval_gate     = "cross-lane concept preservation and packet compliance"
  promotion_rule= "Promote only if a concept survives representation transfer
                   without collapsing lane boundaries."
  merge_strategy= "paired_multirepresentation_records"

Two metrics, both at the (map, kind, value) concept level:

1. ``packet_compliance`` — does a single model output match the canonical
   envelope (header pattern, KV keys, schema markers) for its (map, kind)?
2. ``cross_lane_invariance`` — for multi-tongue concepts, do the per-tongue
   outputs share the structural signature (lane boundary preserved across
   the representation transfer)?

Single-tongue concepts (20 of 49 in v5 holdout) only contribute to (1);
multi-tongue concepts (29 of 49) contribute to both.

Body content is NOT part of the signature: surface code, equation samples,
and prose continuations vary per tongue by canonical design. The signature
captures envelope only.

Unmapped-kind policy is fail-closed: if a (map, kind) tuple has no extractor
mapping, the concept verdict returns ``ok=False, error="not_implemented"``
rather than silently passing. New kinds must be added to ``KIND_EXTRACTORS``.

Drift-guard: ``tests/governance/test_aligned_foundations_cross_lane.py`` runs
every extractor against ``training-data/sft/drill_langues_full_train.sft.jsonl``
and asserts canonical training targets pass invariance. If they don't, the
extractor (not the model) is wrong.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Signature extractors per (map, kind)
# ---------------------------------------------------------------------------

_BRACKET_HEADER_RE = re.compile(r"^\[([^\]\n]+)\]")
# Match ``key=`` at line-start OR following whitespace (canonical bracket
# packets pack several ``key=val`` pairs onto one line).
_KV_LINE_RE = re.compile(r"(?:^|\s)([a-zA-Z_][a-zA-Z0-9_]*)\s*=", re.MULTILINE)
_KV_COLON_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s", re.MULTILINE)


def _extract_bracket_packet(text: str) -> Dict[str, Any]:
    """Extract envelope for ``[bracket_header]\\nKV pairs\\nsurface=...`` packets.

    Used by runtime_emission/*, spirit_narrative/*, paradigm_isomorphism/*,
    opcode_runtime/*, cartography_state/*, convergence_action/packet.

    Signature fields:
      - header_label: the bracket label (invariant: same map name across tongues)
      - kv_keys: frozenset of `key=value` keys present in the body
      - has_surface: bool (every canonical packet has a `surface=` line)
    """
    body = text or ""
    first_line = body.lstrip().split("\n", 1)[0]
    m = _BRACKET_HEADER_RE.match(first_line)
    header_label = m.group(1).strip() if m else ""
    kv_keys = frozenset(_KV_LINE_RE.findall(body))
    return {
        "type": "bracket_packet",
        "header_label": header_label,
        "kv_keys": kv_keys,
        "has_surface": "surface=" in body,
    }


_TRANSPORT_HEADER_RE = re.compile(
    r"^\[([A-Za-z'’ ]+)/([A-Za-z0-9_+\-]+)\]\s+(.+?)\s*\.\s*$",
    re.MULTILINE,
)


def _extract_transport_atomic_packet(text: str) -> Dict[str, Any]:
    """Extract envelope for transport_atomic chemistry reaction packets.

    Format::

        [<Tongue>/<lang>] <verb phrase>.
        reactants: ...
        reaction_class: ...
        stability: ...
        products: ...

    Signature fields:
      - verb_phrase: the action verb sentence (invariant across tongues)
      - kv_keys: frozenset of `key:` field labels in the body
    """
    body = text or ""
    first_line = body.lstrip().split("\n", 1)[0]
    m = _TRANSPORT_HEADER_RE.match(first_line)
    verb_phrase = m.group(3).strip().lower() if m else ""
    kv_keys = frozenset(_KV_COLON_RE.findall(body))
    return {
        "type": "transport_atomic_packet",
        "verb_phrase": verb_phrase,
        "kv_keys": kv_keys,
    }


_TRANSPORT_TEMPLATE_HEADER_RE = re.compile(
    r"^\[([A-Za-z'’ ]+)/([A-Za-z0-9_+\-]+)\]\s+transport_atomic reaction:",
    re.MULTILINE,
)


def _extract_transport_atomic_template(text: str) -> Dict[str, Any]:
    """Extract envelope for transport_atomic/reaction_template packets.

    These have a fuller schema than reaction_predict / reaction_stability:
    they include atoms_conserved, metaphor, code blocks. The header is
    ``[<Tongue>/<lang>] transport_atomic reaction: <name>``.
    """
    body = text or ""
    has_template_header = bool(_TRANSPORT_TEMPLATE_HEADER_RE.search(body))
    kv_keys = frozenset(_KV_COLON_RE.findall(body))
    return {
        "type": "transport_atomic_template",
        "has_template_header": has_template_header,
        "kv_keys": kv_keys,
    }


_CROSS_BRAID_PAIR_HEADER_RE = re.compile(
    r"^Cross-braid\s+(\S.*?)\s*->\s*(\S.*?)\s*\(.*?\):",
    re.MULTILINE,
)


def _extract_cross_braid_pair(text: str) -> Dict[str, Any]:
    """Extract envelope for cross_braid_code/pair packets.

    Format::

        Cross-braid <T1> -> <T2> (phase_delta=..., weight_ratio=...):
        [<T1>]
        <code>
        [<T2>]
        <code>

    Signature: header presence + bracket count (must be exactly 2).
    """
    body = text or ""
    has_header = bool(_CROSS_BRAID_PAIR_HEADER_RE.search(body))
    bracket_count = len(re.findall(r"^\[[^\]\n]+\]", body, flags=re.MULTILINE))
    return {
        "type": "cross_braid_pair",
        "has_header": has_header,
        "bracket_count": bracket_count,
    }


def _extract_bracketed_code_only(text: str) -> Dict[str, Any]:
    """Extract envelope for cross_braid_code/{anchor_code, witness_code}.

    Format::

        [<Tongue>]
        <single code surface>
    """
    body = text or ""
    first_line = body.lstrip().split("\n", 1)[0]
    m = _BRACKET_HEADER_RE.match(first_line)
    has_bracket_header = m is not None
    line_count = len([line for line in body.splitlines() if line.strip()])
    return {
        "type": "bracketed_code_only",
        "has_bracket_header": has_bracket_header,
        "line_count": line_count,
    }


def _extract_cross_braid_rationale(text: str) -> Dict[str, Any]:
    """Extract envelope for cross_braid_code/rationale free-prose packets.

    Canonical phrasing references the bijective pair, phase delta, and
    weight ratio. Signature: presence of the three concept anchors.
    """
    body = (text or "").lower()
    return {
        "type": "cross_braid_rationale",
        "mentions_bijective": "bijective" in body,
        "mentions_phase_delta": "phase delta" in body or "phase_delta" in body,
        "mentions_weight_ratio": "weight ratio" in body or "weight_ratio" in body,
    }


def _extract_atomic_semantic_rationale(text: str) -> Dict[str, Any]:
    """Extract envelope for atomic_semantic/rationale free-prose packets.

    Canonical phrasing names the tongue, the value, and references the
    semantic-lattice / invariant projection. Signature: presence of the
    invariant-anchor markers.
    """
    body = (text or "").lower()
    return {
        "type": "atomic_semantic_rationale",
        "mentions_invariant": "invariant" in body,
        "mentions_lattice_or_projection": "lattice" in body or "projection" in body,
    }


def _extract_atomic_semantic_state(text: str) -> Dict[str, Any]:
    """Extract envelope for atomic_semantic/state KV-string packets.

    Format::

        filter:class=...,element=...,tau=KO:1/AV:1/...,... | positive:class=...
    """
    body = text or ""
    sections = [s.strip() for s in body.split("|") if s.strip()]
    section_labels = frozenset(s.split(":", 1)[0] for s in sections if ":" in s)
    return {
        "type": "atomic_semantic_state",
        "section_labels": section_labels,
        "mentions_tau_axis": "tau=" in body,
    }


def _extract_convergence_action_anchor(text: str) -> Dict[str, Any]:
    """Extract envelope for convergence_action/anchor single-line packets.

    Format::

        <Tongue> convergence anchor: voice=... motif=... cadence=... runtime=... spirit=...
    """
    body = text or ""
    kv_keys = frozenset(_KV_LINE_RE.findall(body))
    return {
        "type": "convergence_anchor",
        "kv_keys": kv_keys,
        "has_anchor_marker": "convergence anchor" in body,
    }


def _extract_qa_invariance(text: str) -> Dict[str, Any]:
    """Extract envelope for qa_invariance/* formula-restatement packets.

    QA invariance kinds are tongue-independent (the formula is the same
    regardless of which tongue 'speaks' it). Signature: presence of the
    formula header anchors per kind. These are single-concept rows in
    practice (the (map,kind,value) triple is the formula identifier),
    so cross_lane_invariance is rarely meaningful here.
    """
    body = text or ""
    kv_keys = frozenset(_KV_COLON_RE.findall(body))
    return {
        "type": "qa_invariance",
        "kv_keys": kv_keys,
        "has_equals": "=" in body,
    }


# Map of (map, kind) -> extractor callable. Fail-closed: anything not in
# this dict returns ok=False with error="not_implemented".
KIND_EXTRACTORS: Dict[Tuple[str, str], Callable[[str], Dict[str, Any]]] = {
    # transport_atomic family (chemistry packets) — 72% of v5 holdout
    ("transport_atomic", "reaction_predict"): _extract_transport_atomic_packet,
    ("transport_atomic", "reaction_stability"): _extract_transport_atomic_packet,
    ("transport_atomic", "reaction_template"): _extract_transport_atomic_template,
    ("transport_atomic", "rationale"): _extract_atomic_semantic_rationale,
    ("transport_atomic", "transport"): _extract_atomic_semantic_state,
    # cross_braid_code family
    ("cross_braid_code", "anchor_code"): _extract_bracketed_code_only,
    ("cross_braid_code", "witness_code"): _extract_bracketed_code_only,
    ("cross_braid_code", "pair"): _extract_cross_braid_pair,
    ("cross_braid_code", "rationale"): _extract_cross_braid_rationale,
    # bracket-packet family (cartography_state, convergence_action, etc.)
    ("cartography_state", "packet"): _extract_bracket_packet,
    ("cartography_state", "route"): _extract_bracket_packet,
    ("convergence_action", "packet"): _extract_bracket_packet,
    ("convergence_action", "anchor"): _extract_convergence_action_anchor,
    # runtime_emission, spirit_narrative, paradigm_isomorphism, opcode_runtime
    # share the bracket-packet envelope; templates are short prose lines.
    ("runtime_emission", "code"): _extract_bracket_packet,
    ("runtime_emission", "packet"): _extract_bracket_packet,
    ("runtime_emission", "rationale"): _extract_bracket_packet,
    ("runtime_emission", "template"): _extract_atomic_semantic_rationale,
    ("spirit_narrative", "code"): _extract_bracket_packet,
    ("spirit_narrative", "packet"): _extract_bracket_packet,
    ("spirit_narrative", "rationale"): _extract_bracket_packet,
    ("spirit_narrative", "template"): _extract_atomic_semantic_rationale,
    ("paradigm_isomorphism", "code"): _extract_bracket_packet,
    ("paradigm_isomorphism", "packet"): _extract_bracket_packet,
    ("paradigm_isomorphism", "rationale"): _extract_bracket_packet,
    ("paradigm_isomorphism", "template"): _extract_atomic_semantic_rationale,
    ("opcode_runtime", "anchor"): _extract_bracket_packet,
    ("opcode_runtime", "packet"): _extract_bracket_packet,
    ("opcode_runtime", "rationale"): _extract_bracket_packet,
    ("opcode_runtime", "template"): _extract_atomic_semantic_rationale,
    # atomic_semantic family
    ("atomic_semantic", "rationale"): _extract_atomic_semantic_rationale,
    ("atomic_semantic", "state"): _extract_atomic_semantic_state,
    # qa_invariance family — formula restatements (tongue-independent)
    ("qa_invariance", "comma_drift"): _extract_qa_invariance,
    ("qa_invariance", "harmonic_wall"): _extract_qa_invariance,
    ("qa_invariance", "hyperbolic_distance"): _extract_qa_invariance,
    ("qa_invariance", "phase_delta"): _extract_qa_invariance,
    ("qa_invariance", "phi_ladder"): _extract_qa_invariance,
}


# Per-(map, kind), the subset of signature fields that must be identical
# across tongues for the same (map, kind, value) concept. Fields not listed
# are allowed to vary per tongue.
INVARIANT_FIELDS: Dict[Tuple[str, str], Tuple[str, ...]] = {
    ("transport_atomic", "reaction_predict"): ("verb_phrase", "kv_keys"),
    ("transport_atomic", "reaction_stability"): ("verb_phrase", "kv_keys"),
    ("transport_atomic", "reaction_template"): ("has_template_header", "kv_keys"),
    ("transport_atomic", "rationale"): ("mentions_invariant",),
    ("transport_atomic", "transport"): ("mentions_tau_axis",),
    ("cross_braid_code", "anchor_code"): ("has_bracket_header",),
    ("cross_braid_code", "witness_code"): ("has_bracket_header",),
    ("cross_braid_code", "pair"): ("has_header", "bracket_count"),
    ("cross_braid_code", "rationale"): (
        "mentions_bijective",
        "mentions_phase_delta",
        "mentions_weight_ratio",
    ),
    ("cartography_state", "packet"): ("header_label", "has_surface"),
    ("cartography_state", "route"): ("header_label", "has_surface"),
    ("convergence_action", "packet"): ("header_label", "has_surface"),
    ("convergence_action", "anchor"): ("has_anchor_marker",),
    ("runtime_emission", "code"): ("header_label", "has_surface"),
    ("runtime_emission", "packet"): ("header_label", "has_surface"),
    ("runtime_emission", "rationale"): ("header_label", "has_surface"),
    ("runtime_emission", "template"): (),
    ("spirit_narrative", "code"): ("header_label", "has_surface"),
    ("spirit_narrative", "packet"): ("header_label", "has_surface"),
    ("spirit_narrative", "rationale"): ("header_label", "has_surface"),
    ("spirit_narrative", "template"): (),
    ("paradigm_isomorphism", "code"): ("header_label", "has_surface"),
    ("paradigm_isomorphism", "packet"): ("header_label", "has_surface"),
    ("paradigm_isomorphism", "rationale"): ("header_label", "has_surface"),
    ("paradigm_isomorphism", "template"): (),
    ("opcode_runtime", "anchor"): ("header_label", "has_surface"),
    ("opcode_runtime", "packet"): ("header_label", "has_surface"),
    ("opcode_runtime", "rationale"): ("header_label", "has_surface"),
    ("opcode_runtime", "template"): (),
    ("atomic_semantic", "rationale"): ("mentions_invariant",),
    ("atomic_semantic", "state"): ("section_labels", "mentions_tau_axis"),
    ("qa_invariance", "comma_drift"): ("kv_keys", "has_equals"),
    ("qa_invariance", "harmonic_wall"): ("kv_keys", "has_equals"),
    ("qa_invariance", "hyperbolic_distance"): ("kv_keys", "has_equals"),
    ("qa_invariance", "phase_delta"): ("kv_keys", "has_equals"),
    ("qa_invariance", "phi_ladder"): ("kv_keys", "has_equals"),
}


# ---------------------------------------------------------------------------
# Public scoring API
# ---------------------------------------------------------------------------


def extract_packet_signature(map_name: str, kind: str, response: str) -> Dict[str, Any]:
    """Run the (map, kind) extractor; raise KeyError if unmapped (caller decides)."""
    extractor = KIND_EXTRACTORS[(map_name, kind)]
    return extractor(response)


def score_packet_compliance(map_name: str, kind: str, response: str, reference: str) -> Dict[str, Any]:
    """Score a single response against the canonical envelope.

    Compliance = the response's signature matches the canonical reference
    signature on every invariant field for the kind. The reference signature
    is computed by running the same extractor on the canonical training
    target (passed as ``reference``).
    """
    if (map_name, kind) not in KIND_EXTRACTORS:
        return {
            "ok": False,
            "error": "not_implemented",
            "map": map_name,
            "kind": kind,
        }
    actual = extract_packet_signature(map_name, kind, response)
    expected = extract_packet_signature(map_name, kind, reference)
    invariant_fields = INVARIANT_FIELDS.get((map_name, kind), ())
    diffs: Dict[str, Tuple[Any, Any]] = {}
    for field in invariant_fields:
        if actual.get(field) != expected.get(field):
            diffs[field] = (expected.get(field), actual.get(field))
    return {
        "ok": not diffs,
        "map": map_name,
        "kind": kind,
        "diffs": diffs,
        "actual_signature": actual,
        "expected_signature": expected,
    }


def score_cross_lane_invariance(
    map_name: str,
    kind: str,
    per_tongue_responses: Dict[str, str],
) -> Dict[str, Any]:
    """Score whether per-tongue responses share the structural envelope.

    Multi-tongue concepts (29 of 49 in v5 holdout) drop here. A concept is
    invariant if every per-tongue signature matches every other on all
    invariant fields. Pairwise mismatches are reported per field.
    """
    if (map_name, kind) not in KIND_EXTRACTORS:
        return {
            "ok": False,
            "error": "not_implemented",
            "map": map_name,
            "kind": kind,
        }
    if len(per_tongue_responses) < 2:
        return {
            "ok": True,
            "map": map_name,
            "kind": kind,
            "n_tongues": len(per_tongue_responses),
            "skipped_reason": "single_tongue_concept",
        }
    invariant_fields = INVARIANT_FIELDS.get((map_name, kind), ())
    sigs = {tongue: extract_packet_signature(map_name, kind, resp) for tongue, resp in per_tongue_responses.items()}
    tongues = sorted(sigs)
    mismatches: List[Dict[str, Any]] = []
    for i, t_a in enumerate(tongues):
        for t_b in tongues[i + 1 :]:
            for field in invariant_fields:
                if sigs[t_a].get(field) != sigs[t_b].get(field):
                    mismatches.append(
                        {
                            "tongue_a": t_a,
                            "tongue_b": t_b,
                            "field": field,
                            "value_a": sigs[t_a].get(field),
                            "value_b": sigs[t_b].get(field),
                        }
                    )
    return {
        "ok": not mismatches,
        "map": map_name,
        "kind": kind,
        "n_tongues": len(per_tongue_responses),
        "tongues": tongues,
        "mismatches": mismatches,
        "per_tongue_signatures": sigs,
    }


def aligned_foundations_concept_verdict(
    map_name: str,
    kind: str,
    value: str,
    per_tongue_responses: Dict[str, str],
    per_tongue_references: Dict[str, str],
) -> Dict[str, Any]:
    """Composite per-concept verdict combining packet compliance + invariance.

    A concept (single (map, kind, value) group) passes iff:
      - every per-tongue response is packet-compliant against its reference, AND
      - if multi-tongue: every per-tongue signature matches every other on
        invariant fields.

    Fail-closed for unmapped (map, kind).
    """
    if (map_name, kind) not in KIND_EXTRACTORS:
        return {
            "ok": False,
            "error": "not_implemented",
            "map": map_name,
            "kind": kind,
            "value": value,
        }
    compliance: Dict[str, Dict[str, Any]] = {}
    for tongue, response in per_tongue_responses.items():
        reference = per_tongue_references.get(tongue, "")
        compliance[tongue] = score_packet_compliance(map_name, kind, response, reference)
    all_compliant = all(c["ok"] for c in compliance.values())
    invariance = score_cross_lane_invariance(map_name, kind, per_tongue_responses)
    return {
        "ok": all_compliant and invariance["ok"],
        "map": map_name,
        "kind": kind,
        "value": value,
        "n_tongues": len(per_tongue_responses),
        "all_compliant": all_compliant,
        "invariance_ok": invariance["ok"],
        "per_tongue_compliance": compliance,
        "invariance": invariance,
    }


# ---------------------------------------------------------------------------
# Helpers for grouping holdout records by concept
# ---------------------------------------------------------------------------


def group_records_by_concept(
    records: List[Dict[str, Any]],
) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    """Group SFT records by (map, kind, value) concept identifier.

    Each input record is expected to be a row from drill_langues_full
    SFT JSONL: ``{"messages": [...], "meta": {"map", "kind", "tongue", "value"}}``.
    """
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        meta = rec.get("meta") or {}
        key = (str(meta.get("map", "")), str(meta.get("kind", "")), str(meta.get("value", "")))
        groups[key].append(rec)
    return dict(groups)


def reference_assistant_text(record: Dict[str, Any]) -> str:
    """Return the canonical assistant turn text from an SFT record."""
    msgs = record.get("messages") or []
    for msg in reversed(msgs):
        if msg.get("role") == "assistant":
            return str(msg.get("content", ""))
    return ""


def user_prompt_text(record: Dict[str, Any]) -> str:
    """Return the user turn text (the prompt the model will be evaluated on)."""
    msgs = record.get("messages") or []
    for msg in msgs:
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def system_prompt_text(record: Dict[str, Any]) -> Optional[str]:
    """Return the system turn text if present (for chat-template construction)."""
    msgs = record.get("messages") or []
    for msg in msgs:
        if msg.get("role") == "system":
            return str(msg.get("content", ""))
    return None


__all__ = [
    "KIND_EXTRACTORS",
    "INVARIANT_FIELDS",
    "extract_packet_signature",
    "score_packet_compliance",
    "score_cross_lane_invariance",
    "aligned_foundations_concept_verdict",
    "group_records_by_concept",
    "reference_assistant_text",
    "user_prompt_text",
    "system_prompt_text",
]
