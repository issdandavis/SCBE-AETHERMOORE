#!/usr/bin/env python3
"""Biomorphic control plane for octopus tentacles + raven monitor.

Value-first contract:
- Security gates remain active.
- Routing optimizes for useful outcomes under budget.
- Execution mode is selected per task: api_first, browser_assist, full_browser.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "governance" / "biomorphic_portal_registry.example.json"
DEFAULT_VALUE_PROFILE = REPO_ROOT / "config" / "governance" / "value_execution_profiles.json"

BIOMORPHIC_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "biomorphic"
STATE_VECTOR_LOG = BIOMORPHIC_ROOT / "state_vectors.jsonl"
DECISION_LOG = BIOMORPHIC_ROOT / "decision_records.jsonl"
PORTAL_EVENT_LOG = BIOMORPHIC_ROOT / "portal_events.jsonl"

CROSS_TALK_LOG = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"

FALLBACK_VALUE_PROFILE: dict[str, Any] = {
    "intent_value_weights": {
        "lead_generation": 0.92,
        "publish_content": 0.84,
        "release_ops": 0.78,
        "research_intel": 0.70,
        "maintenance": 0.55,
        "generic": 0.50,
    },
    "execution_modes": {
        "api_first": {"estimated_cost_cents": 2.0, "quality": 0.70, "speed": 0.92},
        "browser_assist": {"estimated_cost_cents": 7.0, "quality": 0.85, "speed": 0.78},
        "full_browser": {"estimated_cost_cents": 20.0, "quality": 0.93, "speed": 0.58},
    },
    "risk_mode_caps": {
        "low": ["api_first", "browser_assist", "full_browser"],
        "medium": ["api_first", "browser_assist", "full_browser"],
        "high": ["api_first", "browser_assist"],
    },
    "default_budget_cents": {"low": 20, "medium": 12, "high": 8},
}


@dataclass
class ValuePlan:
    value_intent: str
    objective_value: float
    execution_mode: str
    estimated_cost_cents: float
    budget_cents: int
    utility_score: float
    roi_score: float
    over_budget: bool
    rationale: str


@dataclass
class StateVector:
    state_id: str
    created_at: str
    objective: str
    event_type: str
    domain: str
    lane: str
    tentacle_id: str
    portal_id: str
    risk: str
    threat_score: float
    confidence: float
    coordinates: dict[str, float]
    tags: list[str]
    value_intent: str
    execution_mode: str
    budget_cents: int
    estimated_cost_cents: float
    utility_score: float
    roi_score: float


@dataclass
class DecisionRecord:
    decision_id: str
    state_id: str
    action: str
    signature: str
    timestamp: str
    reason: str
    confidence: float
    lane: str
    tentacle_id: str
    portal_id: str
    next_steps: list[str]
    pending_integrations: list[str]
    value_intent: str
    execution_mode: str
    estimated_cost_cents: float
    roi_score: float


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def load_json_or_default(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def extract_domain(domain: str, goal: str) -> str:
    raw = (domain or "").strip()
    if not raw:
        url_match = re.search(r"https?://[^\s]+", goal)
        raw = url_match.group(0) if url_match else ""
    if not raw:
        return "unknown"
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.netloc or parsed.path
    return host.lower().strip()


def deterministic_coordinates(seed: str) -> dict[str, float]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    values = []
    for i in range(0, 6, 2):
        n = int.from_bytes(digest[i : i + 2], "big")
        values.append(round((n / 65535.0) * 2.0 - 1.0, 6))
    return {"x": values[0], "y": values[1], "z": values[2]}


def classify_lane(goal: str, event_type: str, risk: str) -> str:
    text = f"{event_type} {goal}".lower()
    if any(k in text for k in ["codespace", "devcontainer", "integration test", "e2e", "workflow", "ci", "build"]):
        return "codespaces_lane"
    if any(k in text for k in ["webhook", "publish", "post", "social", "shopify", "gumroad", "reddit", "linkedin", "x "]):
        return "webhook_lane"
    if any(k in text for k in ["merge", "rebase", "branch", "commit", "release", "pypi", "twine", "git", "gh "]):
        return "cli_lane"
    if risk == "high":
        return "cli_lane"
    return "webhook_lane"


def threat_score(goal: str, domain: str, threat_words: list[str]) -> float:
    text = f"{goal} {domain}".lower()
    hits = sum(1 for word in threat_words if word in text)
    return round(min(1.0, hits / 4.0), 3)


def choose_tentacle(goal: str, lane: str, profiles: list[dict[str, Any]]) -> tuple[str, float]:
    text = goal.lower()
    best_id = "UNASSIGNED"
    best_score = -1.0
    for profile in profiles:
        score = 0.0
        if profile.get("lane") == lane:
            score += 2.0
        for keyword in profile.get("focus_keywords", []):
            if keyword.lower() in text:
                score += 1.0
        if score > best_score:
            best_score = score
            best_id = str(profile.get("tentacle_id", "UNASSIGNED"))
    confidence = round(min(1.0, max(0.2, (best_score + 1.0) / 6.0)), 3)
    return best_id, confidence


def _domain_match(domain: str, candidate: str) -> bool:
    d = domain.lower()
    c = candidate.lower()
    return d == c or d.endswith(f".{c}") or c in d


def choose_portal(goal: str, domain: str, lane: str, portals: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    text = goal.lower()
    best: dict[str, Any] | None = None
    best_score = -1.0
    for portal in portals:
        score = 0.0
        if portal.get("lane") == lane:
            score += 1.0
        candidate_domain = str(portal.get("domain", "")).strip()
        if candidate_domain and _domain_match(domain, candidate_domain):
            score += 3.0
        portal_id = str(portal.get("portal_id", ""))
        if portal_id and portal_id.replace("-", " ") in text:
            score += 2.0
        if score > best_score:
            best = portal
            best_score = score
    if best_score < 3.0:
        return None, 0.2
    confidence = round(min(1.0, max(0.2, (best_score + 1.0) / 6.0)), 3)
    return best, confidence


def infer_value_intent(goal: str, intent: str, event_type: str) -> str:
    text = f"{goal} {intent} {event_type}".lower()
    if any(k in text for k in ["lead", "prospect", "outreach", "dm", "client", "sales"]):
        return "lead_generation"
    if any(k in text for k in ["publish", "post", "article", "blog", "content"]):
        return "publish_content"
    if any(k in text for k in ["release", "deploy", "ship", "tag", "package", "pypi"]):
        return "release_ops"
    if any(k in text for k in ["research", "scan", "intel", "analyze", "paper", "source"]):
        return "research_intel"
    if any(k in text for k in ["fix", "test", "workflow", "ci", "maintenance", "refactor"]):
        return "maintenance"
    return "generic"


def effective_budget_cents(
    provided_budget_cents: int,
    risk: str,
    profile: dict[str, Any],
) -> int:
    if provided_budget_cents > 0:
        return provided_budget_cents
    defaults = profile.get("default_budget_cents", {})
    value = defaults.get(risk, defaults.get("medium", 12))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 12


def build_value_plan(
    *,
    goal: str,
    intent: str,
    event_type: str,
    risk: str,
    budget_cents: int,
    profile: dict[str, Any],
    portal_available: bool,
) -> ValuePlan:
    intent_key = infer_value_intent(goal, intent, event_type)
    objective_value = float(profile.get("intent_value_weights", {}).get(intent_key, 0.5))
    modes = profile.get("execution_modes", {})
    allowed = set(profile.get("risk_mode_caps", {}).get(risk, list(modes.keys())))
    effective_budget = effective_budget_cents(budget_cents, risk, profile)

    candidates: list[dict[str, Any]] = []
    for mode_name, mode_cfg in modes.items():
        if mode_name not in allowed:
            continue
        if mode_name == "api_first" and not portal_available:
            continue

        cost = float(mode_cfg.get("estimated_cost_cents", 99.0))
        quality = float(mode_cfg.get("quality", 0.5))
        speed = float(mode_cfg.get("speed", 0.5))

        # Weight outcome first, then responsiveness.
        utility = objective_value * 0.68 + quality * 0.20 + speed * 0.12
        over_budget = cost > effective_budget

        # Cost-aware utility bonus/penalty keeps expenses controlled.
        utility_adjusted = utility + (0.08 if not over_budget else -0.22)
        roi = (utility_adjusted * 100.0) / max(0.1, cost)
        selection_score = utility_adjusted + min(0.25, roi / 20.0)

        candidates.append(
            {
                "mode": mode_name,
                "cost": round(cost, 3),
                "utility": round(max(0.01, utility_adjusted), 3),
                "roi": round(roi, 3),
                "score": round(selection_score, 3),
                "over_budget": over_budget,
            }
        )

    if not candidates:
        return ValuePlan(
            value_intent=intent_key,
            objective_value=round(objective_value, 3),
            execution_mode="browser_assist",
            estimated_cost_cents=7.0,
            budget_cents=effective_budget,
            utility_score=0.35,
            roi_score=5.0,
            over_budget=7.0 > effective_budget,
            rationale="No eligible mode matched profile constraints; fallback=browser_assist.",
        )

    affordable = [c for c in candidates if not c["over_budget"]]
    pool = affordable if affordable else candidates
    best = sorted(pool, key=lambda c: (c["score"], -c["cost"]), reverse=True)[0]

    return ValuePlan(
        value_intent=intent_key,
        objective_value=round(objective_value, 3),
        execution_mode=str(best["mode"]),
        estimated_cost_cents=float(best["cost"]),
        budget_cents=effective_budget,
        utility_score=float(best["utility"]),
        roi_score=float(best["roi"]),
        over_budget=bool(best["over_budget"]),
        rationale=f"Selected {best['mode']} from {len(candidates)} candidates (budget={effective_budget}c).",
    )


def build_signature(state_id: str, action: str) -> str:
    payload = f"{state_id}|{action}|{utc_now()}"
    return "rwp2-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def build_packets(
    *,
    goal: str,
    domain: str,
    event_type: str,
    risk: str,
    sender: str,
    intent: str,
    registry: dict[str, Any],
    value_profile: dict[str, Any],
    budget_cents: int,
) -> tuple[StateVector, DecisionRecord, dict[str, Any]]:
    lane = classify_lane(goal, event_type, risk)
    tentacle_id, tentacle_conf = choose_tentacle(goal, lane, registry.get("tentacle_profiles", []))
    portal, portal_conf = choose_portal(goal, domain, lane, registry.get("portals", []))

    monitor_cfg = registry.get("raven_monitor", {})
    threat_words = monitor_cfg.get("threat_keywords", [])
    score = threat_score(goal, domain, threat_words)

    plan = build_value_plan(
        goal=goal,
        intent=intent,
        event_type=event_type,
        risk=risk,
        budget_cents=budget_cents,
        profile=value_profile,
        portal_available=portal is not None,
    )

    confidence = round(
        max(
            0.05,
            min(
                0.99,
                (tentacle_conf + portal_conf) / 2.0 + (plan.utility_score * 0.15) - (score * 0.18),
            ),
        ),
        3,
    )

    state_id = f"sv-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    coords = deterministic_coordinates(f"{goal}|{domain}|{event_type}")
    portal_id = str((portal or {}).get("portal_id", "unresolved"))
    tags = sorted({lane, tentacle_id.lower(), risk, "biomorphic", plan.execution_mode})

    state = StateVector(
        state_id=state_id,
        created_at=utc_now(),
        objective=goal,
        event_type=event_type,
        domain=domain,
        lane=lane,
        tentacle_id=tentacle_id,
        portal_id=portal_id,
        risk=risk,
        threat_score=score,
        confidence=confidence,
        coordinates=coords,
        tags=tags,
        value_intent=plan.value_intent,
        execution_mode=plan.execution_mode,
        budget_cents=plan.budget_cents,
        estimated_cost_cents=plan.estimated_cost_cents,
        utility_score=plan.utility_score,
        roi_score=plan.roi_score,
    )

    pending: list[str] = []
    if not portal:
        pending.append(f"Add portal mapping for lane={lane} domain={domain}.")
    else:
        auth_ref = str(portal.get("auth_ref", ""))
        if auth_ref.startswith("env:"):
            env_key = auth_ref.split(":", 1)[1]
            if not os.environ.get(env_key):
                pending.append(f"Set environment variable {env_key} for portal {portal_id}.")
    if plan.over_budget:
        pending.append(f"Task mode estimate {plan.estimated_cost_cents}c exceeds budget {plan.budget_cents}c.")

    next_steps = [
        f"Dispatch {tentacle_id} on {lane}.",
        f"Run mode={plan.execution_mode} for intent={plan.value_intent}.",
        f"Execute intent={intent} through portal={portal_id}.",
        "Write completion ack packet to cross_talk.jsonl.",
    ]

    reason = (
        f"lane={lane}; tentacle={tentacle_id}; portal={portal_id}; "
        f"mode={plan.execution_mode}; utility={plan.utility_score}; roi={plan.roi_score}; "
        f"threat_score={score}; confidence={confidence}"
    )

    action = f"route:{intent}"
    decision = DecisionRecord(
        decision_id=f"dr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        state_id=state.state_id,
        action=action,
        signature=build_signature(state.state_id, action),
        timestamp=utc_now(),
        reason=reason,
        confidence=confidence,
        lane=lane,
        tentacle_id=tentacle_id,
        portal_id=portal_id,
        next_steps=next_steps,
        pending_integrations=pending,
        value_intent=plan.value_intent,
        execution_mode=plan.execution_mode,
        estimated_cost_cents=plan.estimated_cost_cents,
        roi_score=plan.roi_score,
    )

    portal_event = {
        "created_at": utc_now(),
        "event_id": f"pe-{uuid.uuid4().hex[:10]}",
        "sender": sender,
        "state_id": state.state_id,
        "lane": lane,
        "portal_id": portal_id,
        "domain": domain,
        "auth_ref": (portal or {}).get("auth_ref", "unresolved"),
        "risk": risk,
        "execution_mode": plan.execution_mode,
        "estimated_cost_cents": plan.estimated_cost_cents,
    }
    return state, decision, portal_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Biomorphic octopus+corvid control-plane router.")
    parser.add_argument("--goal", required=True, help="Goal text to route.")
    parser.add_argument("--domain", default="", help="Target domain or URL.")
    parser.add_argument("--event-type", default="manual", help="Synthetic or webhook event type.")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"], help="Risk label.")
    parser.add_argument("--sender", default="raven.monitor", help="Packet sender id.")
    parser.add_argument("--intent", default="execute_goal", help="Intent label for routed action.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to biomorphic portal registry JSON.")
    parser.add_argument(
        "--value-profile",
        default=str(DEFAULT_VALUE_PROFILE),
        help="Path to value_execution_profiles.json.",
    )
    parser.add_argument(
        "--budget-cents",
        type=int,
        default=-1,
        help="Per-task budget in cents. If omitted, use risk defaults from value profile.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not append logs; print payload only.")
    args = parser.parse_args()

    registry_path = Path(args.registry).expanduser().resolve()
    value_path = Path(args.value_profile).expanduser().resolve()
    registry = load_json_or_default(registry_path, {"raven_monitor": {}, "tentacle_profiles": [], "portals": []})
    value_profile = load_json_or_default(value_path, FALLBACK_VALUE_PROFILE)

    domain = extract_domain(args.domain, args.goal)
    state, decision, portal_event = build_packets(
        goal=args.goal,
        domain=domain,
        event_type=args.event_type,
        risk=args.risk,
        sender=args.sender,
        intent=args.intent,
        registry=registry,
        value_profile=value_profile,
        budget_cents=args.budget_cents,
    )

    state_payload = asdict(state)
    decision_payload = asdict(decision)

    cross_talk_packet = {
        "created_at": utc_now(),
        "packet_id": f"bio-{uuid.uuid4().hex[:8]}",
        "from": args.sender,
        "to": state.lane,
        "event_type": args.event_type,
        "task": args.goal,
        "status": "queued",
        "risk": args.risk,
        "state_id": state.state_id,
        "decision_id": decision.decision_id,
        "portal_id": state.portal_id,
        "execution_mode": state.execution_mode,
        "estimated_cost_cents": state.estimated_cost_cents,
    }

    if not args.dry_run:
        append_jsonl(STATE_VECTOR_LOG, state_payload)
        append_jsonl(DECISION_LOG, decision_payload)
        append_jsonl(PORTAL_EVENT_LOG, portal_event)
        append_jsonl(CROSS_TALK_LOG, cross_talk_packet)

    print(
        json.dumps(
            {
                "ok": True,
                "dry_run": args.dry_run,
                "state_vector": state_payload,
                "decision_record": decision_payload,
                "portal_event": portal_event,
                "cross_talk_path": str(CROSS_TALK_LOG),
                "state_vector_path": str(STATE_VECTOR_LOG),
                "decision_record_path": str(DECISION_LOG),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

