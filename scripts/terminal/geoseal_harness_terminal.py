#!/usr/bin/env python3
"""Terminal dashboard for the GeoSeal AI-to-AI harness.

This is intentionally dependency-free so it works from the npm `geoseal`
passthrough, a bare Python checkout, or a CI terminal. The richer browser
console can still handle interactive REPL work; this surface is for quick
operator checks and model-lane routing decisions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark.harness_provider_matrix import DEFAULT_MODEL_REFS, build_provider_matrix  # noqa: E402
from scripts.benchmark.harness_research_matrix import build_research_matrix  # noqa: E402
from scripts.ci.harness_release_readiness import TEST_COMMANDS  # noqa: E402
from scripts.terminal.analog_action_primitives import build_default_action_deck  # noqa: E402

DEFAULT_BRIDGE_URL = "http://127.0.0.1:8766"


def parse_model_refs(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_MODEL_REFS)
    return [item.strip() for item in raw.split(",") if item.strip()]


def probe_bridge_health(base_url: str, *, timeout: float = 1.5) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/health"
    req = urlrequest.Request(url=url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else {}
            return {
                "ok": 200 <= int(resp.status) < 300,
                "url": url,
                "status_code": int(resp.status),
                "payload": payload,
                "error": "",
            }
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return {
            "ok": False,
            "url": url,
            "status_code": int(exc.code),
            "payload": {},
            "error": detail[:240] or str(exc),
        }
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "url": url,
            "status_code": None,
            "payload": {},
            "error": str(exc),
        }


def build_terminal_state(
    *,
    model_refs: list[str],
    bridge_url: str = DEFAULT_BRIDGE_URL,
    probe_health: bool = True,
    timeout: float = 1.5,
) -> dict[str, Any]:
    matrix = build_provider_matrix(model_refs)
    pairs = matrix["pairs"]
    signal_required = [pair for pair in pairs if pair["signal_required"]]
    blocked_without_signal = [pair for pair in pairs if not pair["ok_without_signal"]]
    local_models = [model for model in matrix["models"] if model["local"]]
    remote_models = [model for model in matrix["models"] if not model["local"]]
    action_deck = build_default_action_deck()
    research_matrix = build_research_matrix()
    bridge = probe_bridge_health(bridge_url, timeout=timeout) if probe_health else {
        "ok": None,
        "url": f"{bridge_url.rstrip('/')}/health",
        "status_code": None,
        "payload": {},
        "error": "not_probed",
    }

    return {
        "schema_version": "scbe_geoseal_harness_terminal_v1",
        "title": "GeoSeal Harness Terminal",
        "bridge": bridge,
        "matrix": matrix,
        "analog_actions": [action.to_dict() for action in action_deck],
        "research_benchmarks": research_matrix,
        "summary": {
            "models": len(matrix["models"]),
            "providers": matrix["provider_count"],
            "pairs": len(pairs),
            "local_models": len(local_models),
            "remote_models": len(remote_models),
            "signal_required_pairs": len(signal_required),
            "blocked_without_signal_pairs": len(blocked_without_signal),
            "analog_actions": len(action_deck),
            "research_lanes": research_matrix["lane_count"],
        },
        "controls": {
            "pair_endpoint": f"{bridge_url.rstrip('/')}/harness/pair",
            "packet_endpoint": f"{bridge_url.rstrip('/')}/harness/packet",
            "signal_format": "provider-pair:<left-provider>-><right-provider>:<reason>",
            "cli_examples": [
                "geoseal harness-terminal --no-health",
                "python scripts/benchmark/harness_provider_matrix.py --json",
                "python scripts/benchmark/harness_live_smoke.py --json",
                "python scripts/ci/harness_release_readiness.py --json",
                "python scripts/serve_geoseal_harness.py",
            ],
            "release_gate_commands": list(TEST_COMMANDS),
        },
    }


def _short(text: Any, limit: int = 34) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return f"{value[: max(0, limit - 3)]}..."


def render_terminal_text(state: dict[str, Any]) -> str:
    matrix = state["matrix"]
    summary = state["summary"]
    bridge = state["bridge"]
    lines = [
        "GeoSeal Harness Terminal",
        "=" * 28,
        f"Bridge: {bridge['url']} -> {('online' if bridge['ok'] else 'offline' if bridge['ok'] is False else 'not probed')}",
        f"Models: {summary['models']} ({summary['local_models']} local / {summary['remote_models']} remote)",
        f"Providers: {summary['providers']} | Pairs: {summary['pairs']} | Signal-required: {summary['signal_required_pairs']}",
        "",
        "Provider Lanes",
        "-" * 28,
    ]
    for model in matrix["models"]:
        available = "ready" if model["available"] else "needs-key"
        locality = "local" if model["local"] else "remote"
        pricing = model.get("pricing_tier", "unknown")
        lines.append(
            f"- {_short(model['ref'], 42):42} {model['provider']:11} {locality:6} "
            f"{available:9} {pricing:18} adapter={model['tool_adapter']}"
        )

    lines.extend(["", "Lane Switches", "-" * 28])
    if matrix["pairs"]:
        for pair in matrix["pairs"]:
            left, right = pair["models"]
            signal = pair["recommended_signal"] or "same-lane"
            state_label = "ok" if pair["ok_without_signal"] else "signal"
            lines.append(
                f"- {_short(left, 24):24} -> {_short(right, 24):24} "
                f"cost={pair['cost']} {state_label:6} {signal}"
            )
    else:
        lines.append("- no provider pairs in current selection")

    lines.extend(["", "Operator Controls", "-" * 28])
    controls = state["controls"]
    lines.append(f"- pair:   {controls['pair_endpoint']}")
    lines.append(f"- packet: {controls['packet_endpoint']}")
    lines.append(f"- signal: {controls['signal_format']}")
    lines.extend(["", "Release Gates", "-" * 28])
    for command in controls.get("release_gate_commands", []):
        lines.append(f"- {command}")
    lines.extend(["", "Analog Actions", "-" * 28])
    for action in state.get("analog_actions", []):
        lines.append(
            f"- {action['symbol']} {action['action_id']:17} {action['command_shape']} -> {action['expected_effect']}"
        )

    research = state.get("research_benchmarks") or {}
    lines.extend(["", "Research Benchmarks", "-" * 28])
    for lane in research.get("lanes", []):
        lines.append(
            f"- {lane['lane_id']:24} {lane['family']:22} cost={lane['cost']} "
            f"parity={lane['parity_claim']}"
        )
        lines.append(f"  gate: {lane['promotion_gate']}")
    lines.append("")
    lines.append("This terminal panel is read-only. It verifies lane readiness and turn-signal rules before model fan-out.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_REFS), help="Comma-separated provider:model refs")
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL, help="GeoSeal harness bridge URL")
    parser.add_argument("--timeout", type=float, default=1.5, help="Bridge health timeout in seconds")
    parser.add_argument("--no-health", action="store_true", help="Skip bridge health probe")
    parser.add_argument("--json", action="store_true", help="Print machine-readable terminal state")
    args = parser.parse_args(argv)

    state = build_terminal_state(
        model_refs=parse_model_refs(args.models),
        bridge_url=args.bridge_url,
        probe_health=not args.no_health,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True))
    else:
        print(render_terminal_text(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
