"""Load a custom Encounter from JSON so the engine can run any cast, not just the demo.

stdlib-only (json + dataclasses), to match the rest of the package. The loader is
deliberately strict: a hand- or LLM-authored encounter file fails with a path-pointing
message ("encounter.fighters[0].concealed: ...") instead of a deep stack trace from the
Director. The validated invariants are exactly the ones the Director silently assumes.
"""

from __future__ import annotations

import dataclasses
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .models import Encounter, Feature, Fighter, PlannedGoal, Technique, Terrain

# The path orders in Director._chosen_features index features by these kinds.
REQUIRED_FEATURE_KINDS = ("safe_zone", "treasure", "monster")


class EncounterSpecError(ValueError):
    """Raised when an encounter JSON file is missing or malformed, with a field path."""


# --- small typed extractors (each reports the dotted path of the offending field) ---


def _as_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EncounterSpecError(f"{path}: expected an object, got {type(value).__name__}")
    return value


def _as_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise EncounterSpecError(f"{path}: expected a list, got {type(value).__name__}")
    return value


def _req(data: dict[str, Any], key: str, path: str) -> Any:
    if key not in data:
        raise EncounterSpecError(f"{path}.{key}: required field is missing")
    return data[key]


def _req_str(data: dict[str, Any], key: str, path: str) -> str:
    value = _req(data, key, path)
    if not isinstance(value, str):
        raise EncounterSpecError(f"{path}.{key}: expected a string, got {type(value).__name__}")
    return value


def _req_int(data: dict[str, Any], key: str, path: str) -> int:
    value = _req(data, key, path)
    if isinstance(value, bool) or not isinstance(value, int):
        raise EncounterSpecError(f"{path}.{key}: expected an integer, got {type(value).__name__}")
    return value


def _str_list(value: Any, path: str) -> list[str]:
    items = _as_list(value, path)
    for idx, item in enumerate(items):
        if not isinstance(item, str):
            raise EncounterSpecError(f"{path}[{idx}]: expected a string, got {type(item).__name__}")
    return list(items)


def _int_map(value: Any, path: str) -> dict[str, int]:
    mapping = _as_dict(value, path)
    for key, val in mapping.items():
        if isinstance(val, bool) or not isinstance(val, int):
            raise EncounterSpecError(f"{path}.{key}: expected an integer, got {type(val).__name__}")
    return dict(mapping)


# --- per-dataclass builders ---


def _fighter_from_dict(value: Any, path: str) -> Fighter:
    data = _as_dict(value, path)
    return Fighter(
        name=_req_str(data, "name", path),
        tier=_req_str(data, "tier", path),
        stats=_int_map(_req(data, "stats", path), f"{path}.stats"),
        temperament=_str_list(_req(data, "temperament", path), f"{path}.temperament"),
        techniques=_str_list(_req(data, "techniques", path), f"{path}.techniques"),
        concealed=_str_list(data.get("concealed", []), f"{path}.concealed"),
        resources=_int_map(data.get("resources", {}), f"{path}.resources"),
        injuries=_str_list(data.get("injuries", []), f"{path}.injuries"),
        momentum=int(data.get("momentum", 0)),
        morale=float(data.get("morale", 1.0)),
        goal=str(data.get("goal", "win")),
    )


def _technique_from_dict(value: Any, path: str) -> Technique:
    data = _as_dict(value, path)
    return Technique(
        technique_id=_req_str(data, "technique_id", path),
        name=_req_str(data, "name", path),
        type=_req_str(data, "type", path),
        cost=_req_int(data, "cost", path),
        range=_req_str(data, "range", path),
        grade=_req_str(data, "grade", path),
        hidden=bool(data.get("hidden", False)),
        effect=dict(_as_dict(data.get("effect", {}), f"{path}.effect")),
        narrative_tags=_str_list(data.get("narrative_tags", []), f"{path}.narrative_tags"),
    )


def _terrain_from_dict(value: Any, path: str) -> Terrain:
    data = _as_dict(value, path)
    return Terrain(
        name=_req_str(data, "name", path),
        constraints=_str_list(data.get("constraints", []), f"{path}.constraints"),
        modifiers=_int_map(data.get("modifiers", {}), f"{path}.modifiers"),
        narrative_tags=_str_list(data.get("narrative_tags", []), f"{path}.narrative_tags"),
    )


def _feature_from_dict(value: Any, path: str) -> Feature:
    data = _as_dict(value, path)
    return Feature(
        feature_id=_req_str(data, "feature_id", path),
        kind=_req_str(data, "kind", path),  # type: ignore[arg-type]
        label=_req_str(data, "label", path),
        innate_test=_req_str(data, "innate_test", path),
        consequence=_req_str(data, "consequence", path),
    )


def _planned_goal_from_dict(value: Any, path: str) -> PlannedGoal:
    data = _as_dict(value, path)
    return PlannedGoal(
        winner=_req_str(data, "winner", path),
        price=_req_str(data, "price", path),
        aftermath=_str_list(data.get("aftermath", []), f"{path}.aftermath"),
    )


def _validate_director_invariants(encounter: Encounter) -> None:
    """Reject encounters the Director would crash or misbehave on, with helpful messages."""
    technique_ids = {technique.technique_id for technique in encounter.techniques}
    attacker = encounter.fighters[0]

    visible = [tid for tid in attacker.techniques if tid in technique_ids]
    if not visible:
        raise EncounterSpecError(
            "encounter.fighters[0].techniques: at least one id must match a defined technique "
            f"(known ids: {sorted(technique_ids)})"
        )

    if not attacker.concealed:
        raise EncounterSpecError(
            "encounter.fighters[0].concealed: needs at least one concealed technique id "
            "(the Director reveals it at the price beat)"
        )
    unknown = [tid for tid in attacker.concealed if tid not in technique_ids]
    if unknown:
        raise EncounterSpecError(
            f"encounter.fighters[0].concealed: unknown technique id(s) {unknown} "
            f"(known ids: {sorted(technique_ids)})"
        )

    kind_counts = Counter(feature.kind for feature in encounter.features)
    missing = [kind for kind in REQUIRED_FEATURE_KINDS if kind_counts[kind] == 0]
    if missing:
        raise EncounterSpecError(
            f"encounter.features: must include one feature of each kind {list(REQUIRED_FEATURE_KINDS)}; "
            f"missing {missing}"
        )
    duplicated = [kind for kind in REQUIRED_FEATURE_KINDS if kind_counts[kind] > 1]
    if duplicated:
        raise EncounterSpecError(
            f"encounter.features: kind(s) {duplicated} appear more than once; the Director picks exactly "
            "one feature per required kind, so duplicates would be silently dropped"
        )


def encounter_from_dict(data: Any, *, seed_override: int | None = None) -> Encounter:
    """Build (and validate) an Encounter from a parsed JSON object."""
    payload = _as_dict(data, "encounter")
    fighters_raw = _as_list(_req(payload, "fighters", "encounter"), "encounter.fighters")
    if len(fighters_raw) < 2:
        raise EncounterSpecError("encounter.fighters: need at least 2 fighters (attacker, then defender)")

    encounter = Encounter(
        encounter_id=_req_str(payload, "encounter_id", "encounter"),
        seed=seed_override if seed_override is not None else _req_int(payload, "seed", "encounter"),
        style=_req_str(payload, "style", "encounter"),
        objective=_req_str(payload, "objective", "encounter"),
        fighters=[_fighter_from_dict(f, f"encounter.fighters[{i}]") for i, f in enumerate(fighters_raw)],
        techniques=[
            _technique_from_dict(t, f"encounter.techniques[{i}]")
            for i, t in enumerate(_as_list(_req(payload, "techniques", "encounter"), "encounter.techniques"))
        ],
        terrain=_terrain_from_dict(_req(payload, "terrain", "encounter"), "encounter.terrain"),
        features=[
            _feature_from_dict(f, f"encounter.features[{i}]")
            for i, f in enumerate(_as_list(_req(payload, "features", "encounter"), "encounter.features"))
        ],
        planned_goal=_planned_goal_from_dict(_req(payload, "planned_goal", "encounter"), "encounter.planned_goal"),
    )
    _validate_director_invariants(encounter)
    return encounter


def load_encounter(path: str | Path, *, seed_override: int | None = None) -> Encounter:
    """Read and validate an encounter JSON file."""
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EncounterSpecError(f"{file_path}: could not read encounter file: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EncounterSpecError(f"{file_path}: invalid JSON: {exc}") from exc
    return encounter_from_dict(data, seed_override=seed_override)


def encounter_to_dict(encounter: Encounter) -> dict[str, Any]:
    """Serialize an Encounter back to a plain dict (every field shown, for use as a template)."""
    return dataclasses.asdict(encounter)
