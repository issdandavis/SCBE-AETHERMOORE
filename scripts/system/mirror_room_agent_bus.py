#!/usr/bin/env python3
"""Mirror-room scheduler for multi-provider agent workflows.

Providers are treated as players in a match series. A task is one game in that
series. The scheduler decides who plays, who watches, and who rests based on
privacy, cost, capability, and previous turns, then writes compact reflection
state without storing raw prompts or recursively amplifying outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUTER_CONFIG = (
    REPO_ROOT / "config" / "governance" / "terminal_ai_router_profiles.json"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_bus" / "mirror_room"

ProviderRole = Literal["play", "watch", "rest"]
PrivacyMode = Literal["local_only", "remote_ok"]
TaskType = Literal["coding", "review", "research", "governance", "training", "general"]


@dataclass(frozen=True)
class ProviderPlayer:
    provider: str
    family: str
    privacy: Literal["local", "remote"]
    available: bool
    estimated_cents: float
    strengths: tuple[str, ...]
    command_surface: str
    reason: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")
            )
            + "\n"
        )


def _env_present(keys: list[str]) -> bool:
    return any(bool(os.getenv(key, "").strip()) for key in keys)


def _provider_strengths(provider: str, family: str) -> tuple[str, ...]:
    if provider in {"ollama", "offline"} or family == "local":
        return ("coding", "review", "governance", "general")
    if provider == "huggingface":
        return ("training", "coding", "research", "review")
    if provider == "openai":
        return ("coding", "review", "research", "governance", "general")
    if provider in {"anthropic", "claude"}:
        return ("review", "research", "governance", "coding", "general")
    if provider in {"xai", "grok"}:
        return ("research", "review", "general")
    return ("general",)


def _command_surface(provider: str) -> str:
    if provider == "offline":
        return "src.api.free_llm_routes.dispatch_free_llm_request(provider='offline')"
    if provider == "ollama":
        return "POST /hydra/free-llm/dispatch provider=ollama or local Ollama chat API"
    if provider == "huggingface":
        return "Hugging Face Jobs/Router via HF_TOKEN"
    if provider in {"openai", "anthropic", "xai"}:
        return "scripts/system/terminal_ai_router.py call"
    return "custom OpenAI-compatible endpoint or local adapter"


def discover_players(config_path: Path = DEFAULT_ROUTER_CONFIG) -> list[ProviderPlayer]:
    config = _load_json(config_path, {})
    providers_cfg = config.get("providers") if isinstance(config, dict) else {}
    providers_cfg = providers_cfg if isinstance(providers_cfg, dict) else {}
    players: list[ProviderPlayer] = [
        ProviderPlayer(
            provider="offline",
            family="offline",
            privacy="local",
            available=True,
            estimated_cents=0.0,
            strengths=_provider_strengths("offline", "offline"),
            command_surface=_command_surface("offline"),
            reason="deterministic fallback",
        ),
        ProviderPlayer(
            provider="ollama",
            family="local",
            privacy="local",
            available=True,
            estimated_cents=0.0,
            strengths=_provider_strengths("ollama", "local"),
            command_surface=_command_surface("ollama"),
            reason="local model runtime; runtime health checked at dispatch",
        ),
    ]

    provider_aliases = {
        "anthropic": "anthropic",
        "xai": "xai",
        "openai": "openai",
        "huggingface": "huggingface",
    }
    for provider, family in provider_aliases.items():
        cfg = (
            providers_cfg.get(provider, {})
            if isinstance(providers_cfg.get(provider, {}), dict)
            else {}
        )
        env_keys = (
            [str(key) for key in cfg.get("env_keys", [])]
            if isinstance(cfg.get("env_keys"), list)
            else []
        )
        tiers = cfg.get("tiers", {}) if isinstance(cfg.get("tiers", {}), dict) else {}
        cheap = (
            tiers.get("cheap", {}) if isinstance(tiers.get("cheap", {}), dict) else {}
        )
        est = float(
            cheap.get("estimated_cents", 0.25 if provider == "huggingface" else 1.0)
        )
        players.append(
            ProviderPlayer(
                provider=provider,
                family=family,
                privacy="remote",
                available=bool(cfg.get("enabled", True))
                and (_env_present(env_keys) if env_keys else provider == "huggingface"),
                estimated_cents=est,
                strengths=_provider_strengths(provider, family),
                command_surface=_command_surface(provider),
                reason="configured in terminal router",
            )
        )

    custom_raw = os.getenv("SCBE_FREE_LLM_PROVIDERS", "").strip()
    if custom_raw:
        try:
            custom_cfg = json.loads(custom_raw)
        except json.JSONDecodeError:
            custom_cfg = {}
        if isinstance(custom_cfg, dict):
            for provider, cfg in custom_cfg.items():
                if not isinstance(provider, str) or not isinstance(cfg, dict):
                    continue
                endpoint = str(cfg.get("endpoint", ""))
                privacy = (
                    "local"
                    if "localhost" in endpoint or "127.0.0.1" in endpoint
                    else "remote"
                )
                players.append(
                    ProviderPlayer(
                        provider=provider,
                        family="custom",
                        privacy=privacy,  # type: ignore[arg-type]
                        available=bool(cfg.get("enabled", True)),
                        estimated_cents=float(
                            cfg.get(
                                "estimated_cents", 0.0 if privacy == "local" else 1.0
                            )
                        ),
                        strengths=tuple(cfg.get("strengths", ["general"])),
                        command_surface=_command_surface("custom"),
                        reason="SCBE_FREE_LLM_PROVIDERS",
                    )
                )
    return players


def _load_series_history(output_root: Path, series_id: str) -> list[dict[str, Any]]:
    path = output_root / series_id / "mirror_room.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _recent_play_count(
    history: list[dict[str, Any]], provider: str, window: int = 4
) -> int:
    return sum(
        1 for row in history[-window:] if row.get("selected_provider") == provider
    )


def _score_player(
    player: ProviderPlayer,
    task_type: TaskType,
    privacy: PrivacyMode,
    budget_cents: float,
    history: list[dict[str, Any]],
) -> tuple[float, str]:
    if privacy == "local_only" and player.privacy != "local":
        return (-1000.0, "remote blocked by local_only privacy")
    if not player.available:
        return (-500.0, "provider unavailable or missing key")
    if player.estimated_cents > budget_cents:
        return (-250.0, "provider exceeds per-round budget")

    score = 0.0
    reasons: list[str] = []
    if task_type in player.strengths:
        score += 4.0
        reasons.append("task strength match")
    if player.privacy == "local":
        score += 2.0
        reasons.append("local/private")
    if player.estimated_cents == 0:
        score += 2.0
        reasons.append("zero estimated cost")
    else:
        score += max(0.0, 2.0 - player.estimated_cents)
        reasons.append("within budget")

    fatigue = _recent_play_count(history, player.provider)
    if fatigue:
        score -= fatigue * 1.25
        reasons.append(f"conserve after {fatigue} recent play(s)")
    return (score, "; ".join(reasons) or "neutral")


def schedule_match_round(
    *,
    task: str,
    task_type: TaskType = "general",
    series_id: str = "default",
    round_index: int = 1,
    privacy: PrivacyMode = "remote_ok",
    budget_cents: float = 2.0,
    max_players: int = 1,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    config_path: Path = DEFAULT_ROUTER_CONFIG,
) -> dict[str, Any]:
    players = discover_players(config_path)
    history = _load_series_history(output_root, series_id)
    scored = []
    for player in players:
        score, reason = _score_player(player, task_type, privacy, budget_cents, history)
        scored.append((score, reason, player))
    scored.sort(key=lambda item: (-item[0], item[2].estimated_cents, item[2].provider))

    active = [item for item in scored if item[0] > -100.0][: max(1, max_players)]
    active_providers = {item[2].provider for item in active}
    watchers = [
        item
        for item in scored
        if item[2].provider not in active_providers
        and item[0] > -100.0
        and item[2].available
    ][:3]
    rested = [
        item
        for item in scored
        if item[2].provider not in active_providers and item not in watchers
    ]
    selected = active[0][2]

    reflection = {
        "version": "mirror-room-agent-bus-round-v1",
        "series_id": series_id,
        "round_index": round_index,
        "created_at_utc": _utc_now(),
        "task": {"sha256": _sha256_text(task), "chars": len(task), "type": task_type},
        "selected_provider": selected.provider,
        "primary_bus": [
            {
                "provider": item[2].provider,
                "role": "play",
                "score": round(item[0], 4),
                "reason": item[1],
                "command_surface": item[2].command_surface,
            }
            for item in active
        ],
        "secondary_bus": [
            {
                "provider": item[2].provider,
                "role": "watch",
                "score": round(item[0], 4),
                "reason": item[1],
                "watch_policy": "observe compact reflection only",
            }
            for item in watchers
        ],
        "tertiary_bus": [
            {
                "provider": item[2].provider,
                "role": "rest",
                "score": round(item[0], 4),
                "reason": item[1],
                "rest_policy": "do not call unless primary fails or next round needs this strength",
            }
            for item in rested
        ],
        "mirror_room": {
            "state_policy": "hashes, scores, provider ids, and next actions only; no raw prompt/output text",
            "anti_amplification": "watchers do not respond unless promoted to play in a later round",
            "history_events": len(history),
        },
        "budget": {
            "per_round_cents": budget_cents,
            "selected_estimated_cents": selected.estimated_cents,
        },
    }
    run_dir = output_root / series_id
    _append_jsonl(run_dir / "mirror_room.jsonl", reflection)
    _write_json(run_dir / "latest_round.json", reflection)
    return reflection


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Schedule a mirror-room multi-provider agent-bus round"
    )
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--task-type",
        choices=["coding", "review", "research", "governance", "training", "general"],
        default="general",
    )
    parser.add_argument("--series-id", default="default")
    parser.add_argument("--round-index", type=int, default=1)
    parser.add_argument(
        "--privacy", choices=["local_only", "remote_ok"], default="remote_ok"
    )
    parser.add_argument("--budget-cents", type=float, default=2.0)
    parser.add_argument("--max-players", type=int, default=1)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--config", default=str(DEFAULT_ROUTER_CONFIG))
    args = parser.parse_args()
    result = schedule_match_round(
        task=args.task,
        task_type=args.task_type,
        series_id=args.series_id,
        round_index=args.round_index,
        privacy=args.privacy,
        budget_cents=args.budget_cents,
        max_players=args.max_players,
        output_root=Path(args.output_root),
        config_path=Path(args.config),
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
