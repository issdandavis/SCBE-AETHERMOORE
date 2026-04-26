from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable

SEMANTIC_ROLES = {
    "observe": {"phase": 0.10, "reactivity": 0.20, "valence": 2, "stability": 0.90},
    "measure": {"phase": 0.15, "reactivity": 0.25, "valence": 2, "stability": 0.88},
    "gate": {"phase": 0.30, "reactivity": 0.50, "valence": 3, "stability": 0.72},
    "move": {"phase": 0.45, "reactivity": 0.70, "valence": 2, "stability": 0.55},
    "compute": {"phase": 0.55, "reactivity": 0.65, "valence": 4, "stability": 0.62},
    "transmit": {"phase": 0.70, "reactivity": 0.80, "valence": 2, "stability": 0.48},
    "repair": {"phase": 0.82, "reactivity": 0.45, "valence": 3, "stability": 0.78},
    "report": {"phase": 0.92, "reactivity": 0.20, "valence": 1, "stability": 0.92},
    "hold": {"phase": 0.02, "reactivity": 0.05, "valence": 1, "stability": 0.98},
}

ROLE_ALIASES = {
    "scan": "observe",
    "sense": "observe",
    "read": "observe",
    "sample": "measure",
    "check": "measure",
    "if": "gate",
    "switch": "gate",
    "route": "gate",
    "drive": "move",
    "fly": "move",
    "turn": "move",
    "run": "compute",
    "plan": "compute",
    "classify": "compute",
    "send": "transmit",
    "uplink": "transmit",
    "downlink": "transmit",
    "fix": "repair",
    "heal": "repair",
    "stabilize": "repair",
    "emit": "report",
    "log": "report",
    "wait": "hold",
    "idle": "hold",
    "noop": "hold",
    "dampen": "hold",
    "cancel": "hold",
}

RESOURCE_KEYS = ("power", "compute", "time", "comms", "wear")
ROLE_RESOURCE_COSTS = {
    "observe": {"power": 0.06, "compute": 0.08, "time": 0.08, "comms": 0.01, "wear": 0.02},
    "measure": {"power": 0.10, "compute": 0.12, "time": 0.10, "comms": 0.02, "wear": 0.03},
    "gate": {"power": 0.05, "compute": 0.18, "time": 0.06, "comms": 0.01, "wear": 0.01},
    "move": {"power": 0.28, "compute": 0.08, "time": 0.16, "comms": 0.02, "wear": 0.22},
    "compute": {"power": 0.16, "compute": 0.32, "time": 0.18, "comms": 0.01, "wear": 0.03},
    "transmit": {"power": 0.18, "compute": 0.10, "time": 0.12, "comms": 0.38, "wear": 0.02},
    "repair": {"power": 0.22, "compute": 0.16, "time": 0.25, "comms": 0.03, "wear": 0.18},
    "report": {"power": 0.04, "compute": 0.06, "time": 0.05, "comms": 0.12, "wear": 0.01},
    "hold": {"power": 0.01, "compute": 0.01, "time": 0.04, "comms": 0.0, "wear": 0.0},
}

ELEMENT_SYMBOLS = {
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Fe",
    "Cu",
    "Zn",
    "Ag",
    "Au",
    "Hg",
    "Pb",
    "U",
}


@dataclass(frozen=True)
class ResourceBudget:
    power: float = 1.0
    compute: float = 1.0
    time: float = 1.0
    comms: float = 1.0
    wear: float = 1.0

    def at(self, tick: int, total_ticks: int, *, floor: float = 0.05) -> "ResourceBudget":
        if total_ticks <= 1:
            fraction = 1.0
        else:
            fraction = max(floor, 1.0 - (tick / float(total_ticks - 1)) * (1.0 - floor))
        return ResourceBudget(
            power=self.power * fraction,
            compute=self.compute * fraction,
            time=self.time * fraction,
            comms=self.comms * fraction,
            wear=self.wear * fraction,
        )

    def as_dict(self) -> dict[str, float]:
        return {key: float(getattr(self, key)) for key in RESOURCE_KEYS}


def _role_for_token(token: str) -> str:
    lowered = token.lower().strip()
    if lowered in SEMANTIC_ROLES:
        return lowered
    if lowered in ROLE_ALIASES:
        return ROLE_ALIASES[lowered]
    if any(part in lowered for part in ("scan", "sense", "read", "observe")):
        return "observe"
    if any(part in lowered for part in ("send", "transmit", "uplink", "downlink")):
        return "transmit"
    if any(part in lowered for part in ("move", "drive", "fly", "turn", "nav")):
        return "move"
    if any(part in lowered for part in ("repair", "heal", "stabilize")):
        return "repair"
    if any(part in lowered for part in ("measure", "sample", "check")):
        return "measure"
    if any(part in lowered for part in ("report", "emit", "log")):
        return "report"
    if any(part in lowered for part in ("gate", "if", "route", "guard")):
        return "gate"
    if any(part in lowered for part in ("compute", "plan", "classify", "infer")):
        return "compute"
    return "compute"


def _byte_signature(token: str) -> dict[str, Any]:
    data = token.encode("utf-8")
    if not data:
        return {
            "byte_count": 0,
            "bit_density": 0.0,
            "hex": [],
            "popcount": [],
            "byte_sha256": hashlib.sha256(data).hexdigest(),
        }
    return {
        "byte_count": len(data),
        "bit_density": sum(byte.bit_count() for byte in data) / (len(data) * 8.0),
        "hex": [f"0x{byte:02X}" for byte in data],
        "popcount": [byte.bit_count() for byte in data],
        "byte_sha256": hashlib.sha256(data).hexdigest(),
    }


def _material_elements(token: str) -> list[str]:
    # This is deliberately conservative: only direct element symbols are treated
    # as material chemistry. Code tokens still get the structural chemistry lane.
    return [match.group(0) for match in re.finditer(r"[A-Z][a-z]?", token) if match.group(0) in ELEMENT_SYMBOLS]


def build_atomic_workflow_unit(token: str, *, explicit_role: str | None = None) -> dict[str, Any]:
    role = _role_for_token(explicit_role or token)
    role_frame = SEMANTIC_ROLES[role]
    byte_frame = _byte_signature(token)
    bit_density = float(byte_frame["bit_density"])
    cost = ROLE_RESOURCE_COSTS[role].copy()
    byte_pressure = 1.0 + (math.log1p(byte_frame["byte_count"]) * 0.08)
    for key in cost:
        cost[key] = round(cost[key] * byte_pressure, 6)
    semantic_lane = {
        "role": role,
        "phase": role_frame["phase"],
        "reactivity": role_frame["reactivity"],
        "valence_slots": role_frame["valence"],
        "stability": role_frame["stability"],
    }
    chemistry_lane = {
        "mode": "material" if _material_elements(token) else "structural_template",
        "material_elements": _material_elements(token),
        "byte_signature": byte_frame,
        "phase_shift": round((bit_density - 0.5) * 0.25, 6),
        "bond_capacity": max(1, int(role_frame["valence"] + round(bit_density * 2))),
        "reactivity_bias": round(role_frame["reactivity"] + (bit_density - 0.5) * 0.2, 6),
    }
    unit_id = hashlib.sha256(
        jsonish({"token": token, "role": role, "hex": byte_frame["hex"]}).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "unit_id": unit_id,
        "token": token,
        "semantic_lane": semantic_lane,
        "chemistry_lane": chemistry_lane,
        "resource_cost": cost,
    }


def jsonish(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(f"{key}:{jsonish(value[key])}" for key in sorted(value)) + "}"
    if isinstance(value, list):
        return "[" + ",".join(jsonish(item) for item in value) + "]"
    return str(value)


def _compatible(left: dict[str, Any], right: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    left_sem = left["semantic_lane"]
    right_sem = right["semantic_lane"]
    left_chem = left["chemistry_lane"]
    right_chem = right["chemistry_lane"]
    phase_gap = abs(float(right_sem["phase"]) - float(left_sem["phase"]))
    if phase_gap > 0.72:
        reasons.append(f"phase_gap_too_large:{phase_gap:.3f}")
    if left_chem["bond_capacity"] <= 0:
        reasons.append("left_has_no_bond_capacity")
    if left_sem["role"] == "report" and right_sem["role"] not in {"hold", "transmit"}:
        reasons.append("report_should_terminate_or_transmit")
    if left_sem["role"] == "transmit" and right_sem["role"] == "move":
        reasons.append("avoid_move_immediately_after_transmit")
    return not reasons, reasons


def _cost_pressure(cost: dict[str, float], available: dict[str, float], spent: dict[str, float]) -> float:
    pressure = 0.0
    for key in RESOURCE_KEYS:
        remaining = max(0.0, float(available[key]) - float(spent[key]))
        if remaining <= 0.0:
            pressure = max(pressure, float("inf"))
        else:
            pressure = max(pressure, float(cost[key]) / remaining)
    return pressure


def _scale_cost(cost: dict[str, float], factor: float) -> dict[str, float]:
    return {key: round(float(value) * factor, 6) for key, value in cost.items()}


def _can_afford(cost: dict[str, float], available: dict[str, float], spent: dict[str, float]) -> list[str]:
    return [key for key in RESOURCE_KEYS if spent[key] + float(cost[key]) > float(available[key])]


def _steady_state_fallback_unit(original_unit: dict[str, Any], *, momentum: float) -> dict[str, Any]:
    fallback = build_atomic_workflow_unit("hold", explicit_role="hold")
    return {
        **fallback,
        "fallback_kind": "steady_state_cancel",
        "momentum_before": round(momentum, 6),
        "momentum_after": round(momentum * 0.35, 6),
        "original_unit": original_unit,
    }


def _readvance_unit(original_unit: dict[str, Any], *, momentum: float) -> dict[str, Any]:
    role = original_unit["semantic_lane"]["role"]
    if role in {"move", "transmit", "repair"}:
        token = "stabilize_readvance"
        explicit_role = "repair"
        cost_factor = 0.45
    elif role == "compute":
        token = "route_readvance"
        explicit_role = "gate"
        cost_factor = 0.55
    else:
        token = "measure_readvance"
        explicit_role = "measure"
        cost_factor = 0.65
    unit = build_atomic_workflow_unit(token, explicit_role=explicit_role)
    unit["resource_cost"] = _scale_cost(unit["resource_cost"], max(0.25, cost_factor * (1.0 - min(momentum, 0.9) * 0.25)))
    unit["fallback_kind"] = "readvance_from_better_footing"
    unit["original_unit"] = original_unit
    unit["momentum_inherited"] = round(momentum, 6)
    return unit


def compose_workflow(
    tokens: Iterable[str],
    *,
    budget: ResourceBudget | None = None,
    decay_floor: float = 0.05,
) -> dict[str, Any]:
    units = [build_atomic_workflow_unit(token) for token in tokens]
    mission_budget = budget or ResourceBudget()
    total_ticks = max(1, len(units))
    ledger: list[dict[str, Any]] = []
    spent = {key: 0.0 for key in RESOURCE_KEYS}
    feasible = True
    degradation_events: list[dict[str, Any]] = []
    readvance_attempts: list[dict[str, Any]] = []
    composition_errors: list[dict[str, Any]] = []
    momentum = 0.0
    for index, unit in enumerate(units):
        available = mission_budget.at(index, total_ticks, floor=decay_floor).as_dict()
        cost = unit["resource_cost"]
        pressure = _cost_pressure(cost, available, spent)
        blocked_resources = _can_afford(cost, available, spent)
        if blocked_resources:
            feasible = False
            momentum = min(1.0, max(momentum, pressure if math.isfinite(pressure) else 1.0))
            fallback = _steady_state_fallback_unit(unit, momentum=momentum)
            degradation_events.append(
                {
                    "index": index,
                    "unit_id": unit["unit_id"],
                    "token": unit["token"],
                    "mode": "steady_state_fallback",
                    "reason": "predicted_budget_overrun_before_commit",
                    "blocked_resources": blocked_resources,
                    "available": available,
                    "spent_before": spent.copy(),
                    "cost": cost,
                    "pressure": pressure,
                    "momentum_before": fallback["momentum_before"],
                    "momentum_after": fallback["momentum_after"],
                    "fallback": "hold",
                }
            )
            fallback_cost = fallback["resource_cost"]
            if not _can_afford(fallback_cost, available, spent):
                fallback["resource_cost"] = _scale_cost(fallback_cost, 0.25)
            for key in RESOURCE_KEYS:
                spent[key] += float(fallback["resource_cost"][key])
            readvance = _readvance_unit(unit, momentum=fallback["momentum_after"])
            readvance_blocked = _can_afford(readvance["resource_cost"], available, spent)
            if readvance_blocked:
                readvance_attempts.append(
                    {
                        "index": index,
                        "status": "held",
                        "token": readvance["token"],
                        "blocked_resources": readvance_blocked,
                        "available": available,
                        "spent_before": spent.copy(),
                        "cost": readvance["resource_cost"],
                    }
                )
                unit = fallback
                cost = {key: 0.0 for key in RESOURCE_KEYS}
                momentum = fallback["momentum_after"]
            else:
                readvance_attempts.append(
                    {
                        "index": index,
                        "status": "accepted",
                        "token": readvance["token"],
                        "available": available,
                        "spent_before": spent.copy(),
                        "cost": readvance["resource_cost"],
                    }
                )
                unit = readvance
                cost = readvance["resource_cost"]
                momentum = max(0.0, fallback["momentum_after"] - 0.2)
        for key in RESOURCE_KEYS:
            spent[key] += float(cost[key])
        if index > 0:
            ok, reasons = _compatible(ledger[-1]["unit"], unit)
            if not ok:
                feasible = False
                composition_errors.append(
                    {
                        "left": ledger[-1]["unit"]["token"],
                        "right": unit["token"],
                        "reasons": reasons,
                    }
                )
        ledger.append(
            {
                "index": index,
                "unit": unit,
                "spent_after": {key: round(value, 6) for key, value in spent.items()},
                "available": available,
                "momentum": round(momentum, 6),
            }
        )
    return {
        "version": "atomic-workflow-composition-v1",
        "unit_count": len(units),
        "feasible": feasible,
        "budget": mission_budget.as_dict(),
        "decay_floor": decay_floor,
        "spent": {key: round(value, 6) for key, value in spent.items()},
        "ledger": ledger,
        "degradation_events": degradation_events,
        "readvance_attempts": readvance_attempts,
        "composition_errors": composition_errors,
        "decision": "execute" if feasible else "degrade_or_replan",
    }
