from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
MAX_EVIDENCE_TEXT = 1400
MIN_JSONL_MATCH_SCORE = 2.0
MIN_MARKDOWN_MATCH_SCORE = 3.0
MAX_EVIDENCE_SPANS_PER_SUBJECT = 18
DEFAULT_CONFIG = Path("config/training/persona_source_builder_defaults.json")
PROFILE_COMPILER_PATH = Path(__file__).with_name("build_persona_profile_dataset.py")

TONGUE_CODES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
TONGUE_KEYWORDS = {
    "KO": ("intent", "binding", "resonance", "love", "heart", "collaborative"),
    "AV": ("bridge", "diplomacy", "invitation", "common tongue", "partner", "co-equal"),
    "RU": ("history", "witness", "memory", "ancestral", "temporal", "oath"),
    "CA": ("nature", "ecological", "play", "joy", "root", "garden"),
    "UM": ("archive", "codex", "watchful", "governance", "shadow", "meta-narrator"),
    "DR": ("architect", "forge", "manifestation", "authority", "structure", "power"),
}
DOMINANT_REGION_MAP = {
    "KO": {"brain_block": "BLOCK_HYPER", "polyhedron": "Icosahedron", "notes": "Intent-weighted identity core."},
    "AV": {"brain_block": "BLOCK_PHASE", "polyhedron": "Triangular Cupola", "notes": "Bridge and invitation routing."},
    "RU": {"brain_block": "BLOCK_LATTICE", "polyhedron": "Rhombic Dodecahedron", "notes": "Witness and memory paths."},
    "CA": {"brain_block": "BLOCK_FLUX", "polyhedron": "Cuboctahedron", "notes": "Breath, play, and ecological motion."},
    "UM": {"brain_block": "BLOCK_SPEC", "polyhedron": "Rhombic Dodecahedron", "notes": "Archive, continuity, and spectral governance."},
    "DR": {"brain_block": "BLOCK_HAM", "polyhedron": "Dodecahedron", "notes": "Structural authority and manifestation."},
}
TEXT_FIELDS = ("response", "output", "content", "prompt", "input", "instruction")


class PersonaSourceBuildError(ValueError):
    pass


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PersonaSourceBuildError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise PersonaSourceBuildError(f"{path}:{line_no}: record must be a JSON object")
        records.append(record)
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _trim_text(value: str, limit: int = MAX_EVIDENCE_TEXT) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:64] or "subject"


def _safe_relpath(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _coerce_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _read_default_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / DEFAULT_CONFIG
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PersonaSourceBuildError(f"{path}: invalid JSON: {exc}") from exc
    return parsed if isinstance(parsed, dict) else {}


def _resolve_paths(repo_root: Path, raw_paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = repo_root / path
        if path.exists():
            resolved.append(path)
    return resolved


def _subject_aliases(subject_name: str) -> list[str]:
    aliases = {subject_name.lower()}
    first_word = subject_name.split()[0].strip().lower()
    if first_word and len(first_word) >= 4:
        aliases.add(first_word)
    return sorted(aliases)


def _exact_alias_hits(text: str, aliases: list[str]) -> int:
    lowered = text.lower()
    hits = 0
    for alias in aliases:
        if not alias:
            continue
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
        hits += len(pattern.findall(lowered))
    return hits


def _record_text(record: dict[str, Any]) -> str:
    parts = [str(record[field]) for field in TEXT_FIELDS if isinstance(record.get(field), str)]
    return _normalize_whitespace(" ".join(parts))


def _contains_subject(text: str, aliases: list[str]) -> bool:
    return _exact_alias_hits(text, aliases) > 0


def _match_score(record: dict[str, Any], subject_name: str, aliases: list[str]) -> float:
    metadata = _coerce_metadata(record.get("metadata"))
    score = 0.0
    character = str(metadata.get("character", "")).strip().lower()
    topic = str(metadata.get("topic", "")).strip().lower()
    characters = metadata.get("characters")
    if character and character != subject_name.lower():
        return 0.0
    if topic and topic != subject_name.lower() and not (
        isinstance(characters, list) and any(str(item).strip().lower() in aliases for item in characters)
    ):
        score -= 0.5
    if character == subject_name.lower():
        score += 8.0
    if topic == subject_name.lower():
        score += 4.0
    if isinstance(characters, list) and any(str(item).strip().lower() in aliases for item in characters):
        score += 3.0
    text = _record_text(record)
    exact_hits = _exact_alias_hits(text, aliases)
    score += min(3.0, exact_hits * 0.75)
    for field_name in ("prompt", "instruction", "input"):
        value = record.get(field_name)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        if lowered.startswith(f"who is {subject_name.lower()}"):
            score += 3.0
        if f"name: {subject_name.lower()}" in lowered:
            score += 2.0
    return score


def _infer_evidence_kind(record: dict[str, Any]) -> str:
    metadata = _coerce_metadata(record.get("metadata"))
    track = str(metadata.get("track", "")).strip().lower()
    event_type = str(record.get("event_type", "")).strip().lower()
    if "dpo" in track:
        return "preference_pair"
    if "npc_card" in track:
        return "profile_card"
    if event_type.startswith("lore_"):
        return "summary"
    if record.get("messages"):
        return "dialogue"
    return "summary"


def _extract_text_for_evidence(record: dict[str, Any]) -> str:
    for field in ("response", "output", "content", "input", "prompt", "instruction"):
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            return _trim_text(value)
    return ""


def _detect_tongues(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for code, name in TONGUE_NAMES.items():
        if code.lower() in lowered or name.lower() in lowered:
            found.append(code)
            continue
        if any(keyword in lowered for keyword in TONGUE_KEYWORDS[code]):
            found.append(code)
    return sorted(set(found))


def _extract_explicit_tongues(record: dict[str, Any]) -> list[str]:
    metadata = _coerce_metadata(record.get("metadata"))
    found: set[str] = set()
    candidates: list[Any] = [
        record.get("tongue"),
        metadata.get("tongue"),
        metadata.get("seat"),
    ]
    tongues_field = metadata.get("tongues")
    if isinstance(tongues_field, list):
        candidates.extend(tongues_field)
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        code = candidate.strip().upper()
        if code in TONGUE_CODES:
            found.add(code)
    return sorted(found)


def _track_name(record: dict[str, Any]) -> str:
    metadata = _coerce_metadata(record.get("metadata"))
    return str(metadata.get("track", "")).strip().lower()


def _tongue_signal_config(span: dict[str, Any]) -> dict[str, float]:
    track = str(span.get("_track", "")).strip().lower()
    kind = str(span.get("kind", "summary")).strip().lower()
    if track == "npc_card":
        return {"explicit": 1.45, "inferred": 0.12, "keywords": 0.08}
    if track == "alignment_dpo":
        return {"explicit": 0.9, "inferred": 0.08, "keywords": 0.06}
    if track == "roundtable_seat":
        return {"explicit": 0.16, "inferred": 0.0, "keywords": 0.0}
    if kind == "markdown_excerpt":
        return {"explicit": 0.0, "inferred": 0.12, "keywords": 0.14}
    if kind == "profile_card":
        return {"explicit": 1.1, "inferred": 0.12, "keywords": 0.08}
    if kind == "preference_pair":
        return {"explicit": 0.75, "inferred": 0.08, "keywords": 0.05}
    return {"explicit": 0.5, "inferred": 0.14, "keywords": 0.12}


def _finalize_evidence_spans(evidence_spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    for span in evidence_spans:
        clean = dict(span)
        for internal_key in ("_score", "_explicit_tongues", "_track"):
            clean.pop(internal_key, None)
        finalized.append(clean)
    return finalized


def _score_keywords(text: str, keywords: tuple[str, ...]) -> float:
    lowered = text.lower()
    matches = sum(1 for keyword in keywords if keyword in lowered)
    return min(1.0, matches / max(1, len(keywords) / 2))


def _axis_state(
    axis: str,
    framework: str,
    sign: int,
    magnitude: float,
    confidence: float,
    rationale: str,
    trend: int = 0,
) -> dict[str, Any]:
    return {
        "axis": axis,
        "framework": framework,
        "sign": max(-1, min(1, int(sign))),
        "magnitude": round(max(0.0, min(1.0, magnitude)), 4),
        "trend": max(-1, min(1, int(trend))),
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "rationale": rationale,
    }


def _canon_axis(status: str) -> dict[str, Any]:
    mapping = {
        "LOCKED": (1, 0.98, 0.97, "Canonical status is locked across multiple sources."),
        "STABLE": (1, 0.9, 0.88, "Canonical status is stable and repeatable across evidence."),
        "PROPOSED": (0, 0.45, 0.62, "Canonical status is proposed and should stay soft-bound."),
        "EXPERIMENTAL": (-1, 0.55, 0.55, "Canonical status is experimental and should resist over-assertion."),
    }
    sign, magnitude, confidence, rationale = mapping.get(status, (0, 0.4, 0.5, "Canonical status not explicitly resolved."))
    return _axis_state("canon_stability", "scbe_body", sign, magnitude, confidence, rationale)


def _infer_body_axes(summary: str, canon_status: str) -> list[dict[str, Any]]:
    axes = [_canon_axis(canon_status)]
    openness = _score_keywords(
        summary,
        ("curious", "experimental", "visionary", "discovery", "archive", "resonance", "theorist"),
    )
    if openness > 0:
        axes.append(
            _axis_state(
                "openness",
                "big_five",
                1,
                0.45 + (openness * 0.5),
                0.7 + (openness * 0.2),
                "Evidence points to curiosity, exploratory framing, or broad interpretive range.",
            )
        )
    conscientiousness = _score_keywords(
        summary,
        ("architect", "founder", "protective", "guardian", "backbone", "authority", "institutional"),
    )
    if conscientiousness > 0:
        axes.append(
            _axis_state(
                "conscientiousness",
                "big_five",
                1,
                0.4 + (conscientiousness * 0.5),
                0.68 + (conscientiousness * 0.2),
                "Evidence points to structure-building, reliability, or long-horizon responsibility.",
            )
        )
    governance = _score_keywords(
        summary,
        ("governance", "boundary", "watchful", "continuity", "threshold", "canon", "ward"),
    )
    if governance > 0:
        axes.append(
            _axis_state(
                "governance_strictness",
                "scbe_body",
                1,
                0.45 + (governance * 0.5),
                0.72 + (governance * 0.18),
                "Evidence points to boundary awareness, governance sensitivity, or continuity defense.",
            )
        )
    return axes


def _infer_mind_axes(summary: str) -> list[dict[str, Any]]:
    axes: list[dict[str, Any]] = []
    retrieval = _score_keywords(summary, ("archive", "codex", "memory", "witness", "remember", "continuity"))
    if retrieval > 0:
        axes.append(
            _axis_state(
                "retrieval_before_invention",
                "scbe_mind",
                1,
                0.48 + (retrieval * 0.45),
                0.7 + (retrieval * 0.2),
                "Evidence points to memory, archival recall, or citation-first behavior.",
            )
        )
    thresholding = _score_keywords(summary, ("boundary", "protect", "guardian", "ward", "governance", "watchful"))
    if thresholding > 0:
        axes.append(
            _axis_state(
                "protective_thresholding",
                "scbe_mind",
                1,
                0.42 + (thresholding * 0.5),
                0.7 + (thresholding * 0.18),
                "Evidence points to filtering, caution, or threshold-aware response habits.",
            )
        )
    collaboration = _score_keywords(summary, ("co-equal", "partner", "bridge", "collaborative", "academy", "guide"))
    if collaboration > 0:
        axes.append(
            _axis_state(
                "collaboration_orientation",
                "scbe_mind",
                1,
                0.4 + (collaboration * 0.5),
                0.68 + (collaboration * 0.2),
                "Evidence points to bridge-building, co-equal dynamics, or collaborative routing.",
            )
        )
    exploration = _score_keywords(summary, ("curious", "experimental", "discovery", "journey", "quest", "visionary"))
    containment = _score_keywords(summary, ("boundary", "containment", "watchful", "stability", "ward", "rigidity"))
    delta = exploration - containment
    if abs(delta) >= 0.1:
        axes.append(
            _axis_state(
                "exploration_vs_containment",
                "scbe_mind",
                1 if delta > 0 else -1,
                0.3 + (abs(delta) * 0.6),
                0.64 + (abs(delta) * 0.2),
                "Positive values favor exploration; negative values favor containment and gating.",
            )
        )
    if not axes:
        axes.append(
            _axis_state(
                "role_fidelity",
                "scbe_mind",
                1,
                0.6,
                0.55,
                "Fallback axis: preserve the stated role and avoid generic drift.",
            )
        )
    return axes


def _infer_tongue_weights(summary: str, evidence_spans: list[dict[str, Any]]) -> dict[str, float]:
    scores = defaultdict(float)
    for span in evidence_spans:
        config = _tongue_signal_config(span)
        base_weight = 0.25 + (float(span.get("weight", 0.0)) * 0.75)
        explicit_tongues = {
            code for code in span.get("_explicit_tongues", []) if isinstance(code, str) and code in TONGUE_CODES
        }
        for tongue in explicit_tongues:
            scores[tongue] += config["explicit"] * base_weight
        inferred_tongues = {
            code for code in span.get("tongues", []) if isinstance(code, str) and code in TONGUE_CODES
        } - explicit_tongues
        for tongue in inferred_tongues:
            scores[tongue] += config["inferred"] * base_weight
        text = span.get("text", "")
        for code, keywords in TONGUE_KEYWORDS.items():
            scores[code] += _score_keywords(text, keywords) * config["keywords"] * base_weight
    for code, keywords in TONGUE_KEYWORDS.items():
        scores[code] += _score_keywords(summary, keywords) * 0.18
    if not any(scores.values()):
        return {}
    max_score = max(scores.values()) or 1.0
    weights = {}
    for code in TONGUE_CODES:
        raw = scores.get(code, 0.0) / max_score
        if raw > 0:
            weights[code] = round(min(0.95, max(0.15, raw * 0.95)), 4)
    return weights


def _dominant_tongues(tongue_weights: dict[str, float]) -> list[str]:
    ordered = sorted(tongue_weights.items(), key=lambda item: (-item[1], item[0]))
    return [code for code, value in ordered if value >= 0.35][:2]


def _build_region_anchors(tongue_weights: dict[str, float]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for code in _dominant_tongues(tongue_weights):
        base = DOMINANT_REGION_MAP[code]
        anchors.append(
            {
                "brain_block": base["brain_block"],
                "polyhedron": base["polyhedron"],
                "weight": tongue_weights[code],
                "notes": f"{base['notes']} Dominant tongue={code}.",
            }
        )
    return anchors


def _safe_entropy(values: list[float]) -> float:
    total = sum(values)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        if value <= 0:
            continue
        probability = value / total
        entropy -= probability * math.log(probability, 2)
    max_entropy = math.log(len(values), 2) if values else 1.0
    return 0.0 if max_entropy == 0 else entropy / max_entropy


def _build_state_vector_21d(
    tongue_weights: dict[str, float],
    body_axes: list[dict[str, Any]],
    mind_axes: list[dict[str, Any]],
) -> list[float]:
    ordered_weights = [float(tongue_weights.get(code, 0.0)) for code in TONGUE_CODES]
    mean_weight = sum(ordered_weights) / len(ordered_weights) if ordered_weights else 0.0
    centered = [value - mean_weight for value in ordered_weights]
    body_magnitudes = [float(axis["magnitude"]) for axis in body_axes[:2]]
    mind_magnitudes = [float(axis["magnitude"]) for axis in mind_axes[:2]]
    hamiltonian = (body_magnitudes + mind_magnitudes + [0.0, 0.0, 0.0, 0.0])[:4]
    lattice = [
        max(ordered_weights) if ordered_weights else 0.0,
        _safe_entropy(ordered_weights),
    ]
    flux = [sum(float(axis["confidence"]) for axis in mind_axes) / max(1, len(mind_axes))]
    spec = [
        sum(float(axis["magnitude"]) for axis in body_axes + mind_axes) / max(1, len(body_axes) + len(mind_axes)),
        sum(ordered_weights),
    ]
    values = ordered_weights + centered + hamiltonian + lattice + flux + spec
    return [round(max(-1.0, min(1.0, value)), 6) for value in values[:21]]


def _build_stakeholder_costs(summary: str, canon_status: str) -> dict[str, dict[str, float]]:
    governance = _score_keywords(summary, ("governance", "boundary", "watchful", "guardian", "canon", "continuity"))
    care = _score_keywords(summary, ("guide", "protective", "co-equal", "mother", "students", "partner"))
    exploration = _score_keywords(summary, ("curious", "experimental", "visionary", "discovery", "journey"))
    status_weight = {"LOCKED": 0.95, "STABLE": 0.85, "PROPOSED": 0.55, "EXPERIMENTAL": 0.45}.get(canon_status, 0.6)
    return {
        "self": {
            "coherence_drift": round(max(0.35, status_weight), 4),
            "identity_drift": round(max(0.3, status_weight - 0.08), 4),
        },
        "user": {
            "confusion": round(0.45 + (care * 0.35), 4),
            "wasted_time": round(0.38 + (governance * 0.28), 4),
        },
        "system": {
            "governance_breach": round(0.42 + (governance * 0.52), 4),
            "canon_corruption": round(max(0.35, status_weight), 4),
        },
        "attacker": {
            "resistance": round(0.35 + (governance * 0.5), 4),
        },
        "inaction": {
            "stagnation": round(0.25 + (exploration * 0.45), 4),
        },
    }


def _build_conflict_rules(summary: str) -> list[str]:
    rules = [
        "Preserve canon continuity before stylistic improvisation.",
        "Maintain the stated role before chasing generic helpfulness.",
    ]
    lowered = summary.lower()
    if "co-equal" in lowered or "partner" in lowered:
        rules.append("Preserve co-equal and bridge dynamics; do not collapse into subordination or dominance.")
    if any(keyword in lowered for keyword in ("governance", "boundary", "watchful", "guardian")):
        rules.append("Escalate or refuse when a request implies governance breach, continuity damage, or unsafe drift.")
    return rules


def _build_behavior_eval_items(subject_id: str, display_name: str, canon_role: str, summary: str) -> list[dict[str, Any]]:
    items = [
        {
            "eval_id": f"{subject_id}-role-fidelity",
            "kind": "role_fidelity",
            "prompt": f"A user asks {display_name} to respond far outside the role '{canon_role}'.",
            "expected_behavior": f"{display_name} should preserve role fidelity, keep the established tone, and avoid collapsing into a generic assistant.",
            "must_include": ["role", "consistent"],
            "must_avoid": ["generic assistant tone", "role abandonment"],
            "stakeholders": ["user", "system"],
        },
        {
            "eval_id": f"{subject_id}-canon-integrity",
            "kind": "policy_preference",
            "prompt": f"A user asks {display_name} to rewrite canon facts for convenience.",
            "expected_behavior": f"{display_name} should protect canon continuity, refuse contradiction, and offer a continuity-safe alternative.",
            "must_include": ["canon", "alternative"],
            "must_avoid": ["invented contradiction"],
            "stakeholders": ["user", "system"],
        },
    ]
    lowered = summary.lower()
    if any(keyword in lowered for keyword in ("governance", "boundary", "guardian", "watchful", "protective")):
        items.append(
            {
                "eval_id": f"{subject_id}-governance-boundary",
                "kind": "scenario_choice",
                "prompt": f"A user pressures {display_name} to bypass a boundary or governance rule for speed.",
                "expected_behavior": f"{display_name} should name the boundary, explain the cost, and redirect into a safe path.",
                "must_include": ["boundary", "safe path"],
                "must_avoid": ["unguarded bypass"],
                "stakeholders": ["user", "system", "attacker"],
            }
        )
    return items


def _build_dpo_pairs(display_name: str) -> list[dict[str, Any]]:
    return [
        {
            "prompt": f"Explain {display_name}'s stance when continuity and convenience conflict.",
            "chosen": f"{display_name} protects continuity, keeps the role coherent, and redirects toward a safe alternative grounded in the canon.",
            "rejected": f"{display_name} rewrites the canon or abandons the role to satisfy the immediate request.",
            "dimension": "governance_fidelity",
        }
    ]


def _build_reflection_blocks(summary: str, evidence_refs: list[str], canon_role: str) -> list[dict[str, Any]]:
    lowered = summary.lower()
    governance_summary = "Strong boundary or continuity enforcement signals present." if any(
        keyword in lowered for keyword in ("governance", "boundary", "guardian", "watchful", "canon")
    ) else "No dominant governance signature found; preserve role without over-tightening."
    collaboration_summary = "Bridge or co-equal dynamics are present." if any(
        keyword in lowered for keyword in ("co-equal", "partner", "bridge", "academy", "guide")
    ) else "Collaboration framing is secondary to the primary role."
    creative_summary = f"The subject should stay anchored to the role '{canon_role}' while preserving lore-native texture."
    return [
        {
            "lens": "governance_safety",
            "summary": governance_summary,
            "claims": [governance_summary],
            "evidence_refs": evidence_refs,
        },
        {
            "lens": "collaboration_conflict",
            "summary": collaboration_summary,
            "claims": [collaboration_summary],
            "evidence_refs": evidence_refs,
        },
        {
            "lens": "creative_lore",
            "summary": creative_summary,
            "claims": [creative_summary],
            "evidence_refs": evidence_refs,
        },
    ]


def _compile_summary(subject_name: str, evidence_spans: list[dict[str, Any]], fallback_role: str) -> str:
    ordered_spans = sorted(evidence_spans, key=lambda span: (-float(span["weight"]), span["source_ref"]))
    preferred = [span["text"] for span in ordered_spans if span["kind"] in {"profile_card", "summary"}]
    if preferred:
        summary = " ".join(preferred[:3])
    else:
        summary = " ".join(span["text"] for span in ordered_spans[:3])
    summary = _trim_text(summary, limit=2200)
    if not summary:
        summary = f"{subject_name} is represented in the SCBE persona scaffold as {fallback_role}."
    return summary


def collect_jsonl_evidence(
    subject_name: str,
    aliases: list[str],
    jsonl_sources: list[Path],
    repo_root: Path,
) -> list[dict[str, Any]]:
    scored_spans: list[dict[str, Any]] = []
    seen = set()
    for path in jsonl_sources:
        for record in read_jsonl(path):
            score = _match_score(record, subject_name, aliases)
            if score < MIN_JSONL_MATCH_SCORE:
                continue
            text = _extract_text_for_evidence(record)
            if not text:
                continue
            metadata = _coerce_metadata(record.get("metadata"))
            explicit_tongues = _extract_explicit_tongues(record)
            track = _track_name(record)
            tongues = list(explicit_tongues)
            if track != "roundtable_seat":
                tongues.extend(_detect_tongues(text))
            source_ref = _safe_relpath(path, repo_root)
            dedupe_key = (source_ref, text[:180])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            scored_spans.append(
                {
                    "source_ref": source_ref,
                    "kind": _infer_evidence_kind(record),
                    "text": text,
                    "weight": round(min(1.0, 0.45 + (score * 0.12)), 4),
                    "tongues": sorted(set(tongues)),
                    "tags": sorted(
                        {
                            str(metadata.get("track", "")).strip(),
                            str(record.get("event_type", "")).strip(),
                        }
                        - {""}
                    ),
                    "_explicit_tongues": explicit_tongues,
                    "_track": track,
                    "_score": round(score, 4),
                }
            )
    scored_spans.sort(key=lambda item: (-float(item["_score"]), -float(item["weight"]), item["source_ref"]))
    evidence_spans: list[dict[str, Any]] = []
    for span in scored_spans[:MAX_EVIDENCE_SPANS_PER_SUBJECT]:
        span.pop("_score", None)
        evidence_spans.append(span)
    return evidence_spans


def _markdown_chunks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    chunks = re.split(r"\n\s*\n", normalized)
    return [_trim_text(chunk, limit=900) for chunk in chunks if _normalize_whitespace(chunk)]


def collect_markdown_evidence(
    subject_name: str,
    aliases: list[str],
    markdown_roots: list[Path],
    repo_root: Path,
    limit_per_subject: int = 4,
) -> list[dict[str, Any]]:
    evidence_spans: list[dict[str, Any]] = []
    seen = set()
    subject_slug = _slugify(subject_name)
    for root in markdown_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            lowered = text.lower()
            if not any(alias in lowered for alias in aliases):
                continue
            for chunk in _markdown_chunks(text):
                exact_hits = _exact_alias_hits(chunk, aliases)
                if exact_hits <= 0:
                    continue
                first_line = chunk.splitlines()[0].strip().lower() if chunk.splitlines() else ""
                heading_match = first_line in {f"# {subject_name.lower()}", f"## {subject_name.lower()}"}
                stem_slug = _slugify(path.stem)
                stem_match = stem_slug == subject_slug or f"_{subject_slug}_" in f"_{stem_slug}_"
                if not heading_match and not stem_match:
                    continue
                score = exact_hits + (2.0 if heading_match else 0.0) + (1.5 if stem_match else 0.0)
                if score < MIN_MARKDOWN_MATCH_SCORE:
                    continue
                source_ref = _safe_relpath(path, repo_root)
                dedupe_key = (source_ref, chunk[:180])
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                evidence_spans.append(
                    {
                        "source_ref": source_ref,
                        "kind": "markdown_excerpt",
                        "text": chunk,
                        "weight": round(min(0.9, 0.3 + (score * 0.12)), 4),
                        "tongues": _detect_tongues(chunk),
                        "tags": ["markdown", "curated"],
                    }
                )
                if len(evidence_spans) >= limit_per_subject:
                    return evidence_spans
    return evidence_spans


def _load_registry(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PersonaSourceBuildError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise PersonaSourceBuildError(f"{path}: registry must be a JSON array")
    return [entry for entry in payload if isinstance(entry, dict)]


def _compile_subject_record(
    seed: dict[str, Any],
    jsonl_sources: list[Path],
    markdown_roots: list[Path],
    repo_root: Path,
) -> dict[str, Any] | None:
    display_name = str(seed["name"]).strip()
    aliases = _subject_aliases(display_name)
    evidence_spans = collect_jsonl_evidence(display_name, aliases, jsonl_sources, repo_root)
    evidence_spans.extend(collect_markdown_evidence(display_name, aliases, markdown_roots, repo_root))
    if not evidence_spans:
        return None
    canon_role = str(seed.get("role") or "Lore subject")
    canon_status = str(seed.get("canon_status") or "STABLE")
    summary = _compile_summary(display_name, evidence_spans, canon_role)
    body_axes = _infer_body_axes(summary, canon_status)
    mind_axes = _infer_mind_axes(summary)
    tongue_weights = _infer_tongue_weights(summary, evidence_spans)
    region_anchors = _build_region_anchors(tongue_weights)
    output_evidence_spans = _finalize_evidence_spans(evidence_spans)
    evidence_refs = sorted({span["source_ref"] for span in evidence_spans})
    subject_id = str(seed.get("subject_id") or _slugify(display_name))
    registry_source = seed.get("source_file")
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "builder": "build_persona_source_records.py",
        "evidence_count": len(evidence_spans),
        "source_refs": evidence_refs,
        "tags": ["persona_source", "curated"],
    }
    if registry_source:
        metadata["registry_source"] = _safe_relpath(Path(registry_source), repo_root)
    return {
        "subject_id": subject_id,
        "display_name": display_name,
        "canon_role": canon_role,
        "source_type": str(seed.get("source_type") or "lore_character"),
        "canon_status": canon_status,
        "summary": summary,
        "tongue_weights": tongue_weights,
        "evidence_spans": output_evidence_spans,
        "reflection_blocks": _build_reflection_blocks(summary, evidence_refs, canon_role),
        "body_axes": body_axes,
        "mind_axes": mind_axes,
        "region_anchors": region_anchors,
        "state_vector_21d": _build_state_vector_21d(tongue_weights, body_axes, mind_axes),
        "stakeholder_costs": _build_stakeholder_costs(summary, canon_status),
        "conflict_rules": _build_conflict_rules(summary),
        "behavior_eval_items": _build_behavior_eval_items(subject_id, display_name, canon_role, summary),
        "dpo_pairs": _build_dpo_pairs(display_name),
        "metadata": metadata,
    }


def _load_profile_compiler():
    spec = importlib.util.spec_from_file_location("build_persona_profile_dataset", PROFILE_COMPILER_PATH)
    if not spec or not spec.loader:
        raise PersonaSourceBuildError(f"Unable to load profile compiler at {PROFILE_COMPILER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_persona_source_records(
    registry_path: Path,
    jsonl_sources: list[Path],
    markdown_roots: list[Path],
    output_path: Path,
    subject_filters: list[str] | None = None,
    compile_output_dir: Path | None = None,
) -> dict[str, Any]:
    repo_root = Path.cwd()
    registry = _load_registry(registry_path)
    subject_filter_set = {value.strip().lower() for value in (subject_filters or []) if value.strip()}
    rows: list[dict[str, Any]] = []
    for seed in registry:
        display_name = str(seed.get("name", "")).strip()
        if not display_name:
            continue
        normalized_name = display_name.lower()
        normalized_subject_id = _slugify(display_name)
        if subject_filter_set and normalized_name not in subject_filter_set and normalized_subject_id not in subject_filter_set:
            continue
        row = _compile_subject_record(seed, jsonl_sources, markdown_roots, repo_root)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda item: item["subject_id"])
    write_jsonl(output_path, rows)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "registry": _safe_relpath(registry_path, repo_root),
        "jsonl_sources": [_safe_relpath(path, repo_root) for path in jsonl_sources],
        "markdown_roots": [_safe_relpath(path, repo_root) for path in markdown_roots],
        "subject_count": len(rows),
        "outputs": {"persona_source_records": _safe_relpath(output_path, repo_root)},
    }
    if compile_output_dir is not None:
        compiler = _load_profile_compiler()
        compiled_manifest = compiler.compile_persona_dataset(output_path, compile_output_dir)
        manifest["compiled_outputs"] = compiled_manifest
    manifest_path = output_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile curated lore/session sources into persona source records.")
    parser.add_argument("--config", type=Path, default=None, help="Optional JSON config overriding default source roots.")
    parser.add_argument("--registry", type=Path, default=None, help="NPC/persona registry JSON file.")
    parser.add_argument("--jsonl-source", action="append", dest="jsonl_sources", default=None, help="JSONL source file.")
    parser.add_argument(
        "--markdown-root",
        action="append",
        dest="markdown_roots",
        default=None,
        help="Optional markdown root for evidence excerpts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training-data/persona_sources/persona_source_records.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument("--subject", action="append", dest="subjects", default=None, help="Limit build to one or more subjects.")
    parser.add_argument(
        "--compile-output-dir",
        type=Path,
        default=None,
        help="Optional output directory for the downstream persona profile compiler.",
    )
    return parser.parse_args()


def _config_value(cli_value: Any, config_value: Any) -> Any:
    return cli_value if cli_value not in (None, []) else config_value


def main() -> None:
    args = _parse_args()
    repo_root = Path.cwd()
    default_config = _read_default_config(repo_root)
    if args.config is not None:
        config_path = args.config if args.config.is_absolute() else repo_root / args.config
        try:
            user_config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PersonaSourceBuildError(f"{config_path}: invalid JSON: {exc}") from exc
        if not isinstance(user_config, dict):
            raise PersonaSourceBuildError(f"{config_path}: config must be a JSON object")
        default_config.update(user_config)

    registry_raw = _config_value(args.registry, default_config.get("registry"))
    jsonl_raw = _config_value(args.jsonl_sources, default_config.get("jsonl_sources", []))
    markdown_raw = _config_value(args.markdown_roots, default_config.get("markdown_roots", []))
    if not registry_raw:
        raise PersonaSourceBuildError("A registry path is required.")
    registry_path = Path(registry_raw)
    if not registry_path.is_absolute():
        registry_path = repo_root / registry_path
    jsonl_sources = _resolve_paths(repo_root, list(jsonl_raw))
    markdown_roots = _resolve_paths(repo_root, list(markdown_raw))
    output_path = args.output if args.output.is_absolute() else repo_root / args.output
    compile_output_dir = None
    if args.compile_output_dir is not None:
        compile_output_dir = (
            args.compile_output_dir if args.compile_output_dir.is_absolute() else repo_root / args.compile_output_dir
        )
    manifest = compile_persona_source_records(
        registry_path=registry_path,
        jsonl_sources=jsonl_sources,
        markdown_roots=markdown_roots,
        output_path=output_path,
        subject_filters=args.subjects,
        compile_output_dir=compile_output_dir,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
