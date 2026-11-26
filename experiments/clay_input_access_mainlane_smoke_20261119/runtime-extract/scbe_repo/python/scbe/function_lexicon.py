"""Typed speech senses and exact perspective mixtures above a fixed byte codec.

This is an authored semantic inventory and deterministic composition interface,
not an automatic parser, a truth detector, or learned model weights.
"""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Mapping, Sequence

SCHEMA = "scbe.function-primitives.v1"
BINDING_SCHEMA = "scbe.function-word-bindings.v1"
ROLES = ("speaker", "addressee", "hearer", "listener", "bystander", "nonparticipant", "omniscient_narrator")
STANCES = ("negative", "neutral", "positive")
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "lexicons" / "function_primitives.json"


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def rational(value) -> Fraction:
    """Accept finite nonnegative ratios; decimal strings preserve decimal intent."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Fraction)):
        raise ValueError("Ratio must be a number or a rational/decimal string")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Ratio must be finite")
    if len(str(value)) > 256:
        raise ValueError("Ratio precision exceeds the input bound")
    try:
        answer = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid ratio") from exc
    if answer < 0:
        raise ValueError("Negative emphasis belongs in the negative stance channel")
    return answer


def normalize_ratios(values: Mapping, allowed: Sequence[str]) -> dict[str, str]:
    if not isinstance(values, Mapping) or not values or set(values) - set(allowed):
        raise ValueError("Supply a nonempty mapping of known channels")
    raw = {key: rational(value) for key, value in values.items()}
    total = sum(raw.values(), Fraction(0))
    if total <= 0:
        raise ValueError("At least one ratio must be positive")
    return {key: str(raw.get(key, Fraction(0)) / total) for key in allowed}


class FunctionLexicon:
    def __init__(self, path=DEFAULT_REGISTRY):
        self.path = Path(path).resolve()
        self.document = read_json(self.path)
        if self.document.get("schema") != SCHEMA or self.document.get("version") != 1:
            raise ValueError("Unknown semantic registry version")
        if set(self.document.get("role_definitions", {})) != set(ROLES):
            raise ValueError("Perspective roles changed")
        if set(self.document.get("stance_definitions", {})) != set(STANCES):
            raise ValueError("Stance channels changed")
        self.entries = {}
        self.by_form = {}
        for entry in self.document["entries"]:
            required = {"id", "kind", "family", "upos", "forms", "definition", "features"}
            if set(entry) != required or not re.fullmatch(r"[a-z][a-z0-9_.]*", entry["id"]):
                raise ValueError("Invalid primitive record")
            if entry["id"] in self.entries or entry["kind"] not in ("content", "function", "context"):
                raise ValueError("Duplicate primitive or unknown kind")
            if not entry["forms"] or any(not isinstance(s, str) or not s.strip() for s in entry["forms"]):
                raise ValueError("Primitive needs nonempty example forms")
            if any(not isinstance(v, str) or not v for v in entry["features"].values()):
                raise ValueError("Feature values must be explicit strings")
            self.entries[entry["id"]] = entry
            for form in entry["forms"]:
                self.by_form.setdefault(form.casefold(), []).append(entry["id"])
        self.registry_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.bindings = {}

    def entry(self, primitive_id):
        try:
            return deepcopy(self.entries[primitive_id])
        except (KeyError, TypeError) as exc:
            raise ValueError("Unknown primitive ID") from exc

    def lookup(self, surface, *, kind=None, family=None):
        """Return ALL candidate senses. The caller supplies syntax and context."""
        if not isinstance(surface, str):
            raise ValueError("Surface must be text")
        return [
            self.entry(key)
            for key in self.by_form.get(surface.strip().casefold(), ())
            if (kind is None or self.entries[key]["kind"] == kind)
            and (family is None or self.entries[key]["family"] == family)
        ]

    def bind_conlang(self, document):
        tongue = document.get("tongue")
        spec = document.get("function_words", {})
        if tongue not in TONGUES or spec.get("schema") != BINDING_SCHEMA:
            raise ValueError("Unknown conlang function binding")
        if spec.get("registry") != self.path.name or spec.get("coverage") != "shared_registry_v1":
            raise ValueError("Conlang registry reference changed")
        if spec.get("encoding") != "stista_framed_sequence":
            raise ValueError("Only derived, framed codec words are declared")
        vocabulary = {word for section in ("words", "particles", "roots") for word in document.get(section, {})}
        native = spec.get("native_bindings", {})
        if not isinstance(native, dict):
            raise ValueError("Native bindings must be explicit")
        for word, senses in native.items():
            if word not in vocabulary or not senses or len(senses) != len(set(senses)):
                raise ValueError("Native binding must name an existing word and distinct senses")
            for sense in senses:
                self.entry(sense)
        if tongue in self.bindings and self.bindings[tongue] != spec:
            raise ValueError("Conflicting registry binding for tongue")
        self.bindings[tongue] = deepcopy(spec)

    def wordlist(self, tongue):
        """Semantic words usable in a named lane; actual tokens come from STISTA."""
        if tongue not in self.bindings:
            raise ValueError("Conlang lane has not been bound")
        native = self.bindings[tongue]["native_bindings"]
        return [
            {
                **self.entry(key),
                "tongue": tongue,
                "native_forms": [w for w, ids in native.items() if key in ids],
                "codec_payload": "scbe.fn.v1/" + key,
                "representation": "derived_codec_sequence_not_native_translation",
            }
            for key in sorted(self.entries)
        ]

    def compose(self, occurrences, *, perspective=None, stance=None, topic=None):
        """Share explicitly named scopes only when hard features and referents fit.

        The caller selects senses and attachment scopes. This does not infer
        syntactic attachments or evaluate logical negation from raw prose.
        """
        if not isinstance(occurrences, list) or not 1 <= len(occurrences) <= 1024:
            raise ValueError("Expected 1..1024 scoped occurrences")
        cells = {}
        for ordinal, occurrence in enumerate(occurrences):
            if not isinstance(occurrence, dict) or set(occurrence) - {"id", "scope", "weight", "referent"}:
                raise ValueError("Unknown occurrence fields")
            entry = self.entry(occurrence.get("id"))
            scope = occurrence.get("scope")
            if not isinstance(scope, str) or not 1 <= len(scope) <= 200:
                raise ValueError("Every primitive needs an explicit bounded scope")
            ref = occurrence.get("referent")
            if ref is not None and (not isinstance(ref, str) or not ref):
                raise ValueError("Referent must be an explicit identity")
            cell = cells.setdefault(scope, {"features": {}, "referent": None, "occurrences": []})
            if ref is not None and cell["referent"] not in (None, ref):
                raise ValueError("Conflicting referents require separate scopes")
            if ref is not None:
                cell["referent"] = ref
            for key, value in entry["features"].items():
                if key in cell["features"] and cell["features"][key] != value:
                    raise ValueError(f"Conflicting {key} in {scope}; choose a sense or split the scope")
                cell["features"][key] = value
            cell["occurrences"].append(
                {"ordinal": ordinal, "id": entry["id"], "mass": str(rational(occurrence.get("weight", 1)))}
            )
        for cell in cells.values():
            members = cell["occurrences"]
            weights = {str(m["ordinal"]): m["mass"] for m in members}
            norm = normalize_ratios(weights, tuple(weights))
            for member in members:
                member["ratio"] = norm[str(member["ordinal"])]
        if stance is not None and (not isinstance(topic, str) or not topic.strip()):
            raise ValueError("Stance requires its target topic")
        return {
            "schema": "scbe.scoped-function-space.v1",
            "registry_sha256": self.registry_hash,
            "cells": cells,
            "perspective": None if perspective is None else normalize_ratios(perspective, ROLES),
            "stance": None if stance is None else {"topic": topic, "ratios": normalize_ratios(stance, STANCES)},
            "knowledge_inferred": False,
        }


def _identities(value):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError("Participant identities must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError("Duplicate participant identity")
    return value


def resolve_reference(entry, context):
    """Bind an explicitly selected sense in this utterance frame; unknown stays []."""
    reference = entry["features"].get("Reference")
    speaker = context.get("speaker")
    if speaker is not None and (not isinstance(speaker, str) or not speaker):
        raise ValueError("Invalid speaker")
    addressees = _identities(context.get("addressees", []))
    if reference == "speaker":
        return [speaker] if speaker else []
    if reference == "addressee":
        return list(addressees)
    if reference == "group":
        group = _identities(context.get("group_members", []))
        if entry["features"].get("Person") == "1":
            if not speaker or not group:
                return []
            if speaker not in group:
                raise ValueError("First-person group must include speaker")
        clusivity = entry["features"].get("Clusivity")
        if clusivity and not addressees:
            return []
        if clusivity == "In" and not set(addressees) <= set(group):
            raise ValueError("Inclusive group must include the addressees")
        if clusivity == "Ex" and set(addressees) & set(group):
            raise ValueError("Exclusive group contains an addressee")
        return list(group)
    if reference in ("bound", "antecedent"):
        return list(_identities(context.get(reference, [])))
    return []


def perspective_views(facts, role_entities, ratios):
    """Keep each view separate; emphasis cannot grant a character narrator access.

    known_by is supplied story metadata, not a claim that hearing implies knowing.
    Even the omniscient narrator only sees the facts explicitly supplied here.
    """
    mix = normalize_ratios(ratios, ROLES)
    if not isinstance(role_entities, dict) or set(role_entities) - set(ROLES):
        raise ValueError("Unknown participant role")
    entities = {role: _identities(ids) for role, ids in role_entities.items()}
    if not isinstance(facts, list) or len(facts) > 4096:
        raise ValueError("Expected a bounded fact list")
    ids = set()
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {"id", "text", "known_by", "status"}:
            raise ValueError("Fact needs identity, text, knowledge owners and evidence status")
        if not isinstance(fact["id"], str) or not fact["id"] or fact["id"] in ids:
            raise ValueError("Invalid or duplicate fact ID")
        if not isinstance(fact["text"], str) or not fact["text"]:
            raise ValueError("Fact text missing")
        if fact["status"] not in ("observed", "reported", "hypothetical", "fictional"):
            raise ValueError("Unknown evidence status")
        _identities(fact["known_by"])
        ids.add(fact["id"])
    result = []
    for role, ratio in mix.items():
        if Fraction(ratio) == 0:
            continue
        if role == "omniscient_narrator":
            result.append({"role": role, "entity": None, "ratio": ratio, "facts": deepcopy(facts)})
            continue
        for entity in entities.get(role, []):
            result.append(
                {
                    "role": role,
                    "entity": entity,
                    "ratio": str(Fraction(ratio) / len(entities[role])),
                    "facts": [deepcopy(f) for f in facts if entity in f["known_by"]],
                }
            )
        if not entities.get(role):
            result.append({"role": role, "entity": None, "ratio": ratio, "facts": [], "status": "UNBOUND"})
    return result
