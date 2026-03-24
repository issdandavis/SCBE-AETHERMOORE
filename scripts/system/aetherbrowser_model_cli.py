#!/usr/bin/env python3
"""CLI for running AetherBrowser plans through a chosen model provider.

The goal is to make model choice explicit and log the plan/execution pair so
the run can later be curated into training data.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.aetherbrowser.agents import AgentSquad
from src.aetherbrowser.command_planner import build_command_plan
from src.aetherbrowser.provider_executor import ProviderExecutor
from src.aetherbrowser.router import ModelProvider, OctoArmorRouter
from src.aetherbrowser.ws_feed import WsFeed


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = PROJECT_ROOT / "training-data" / "browser" / "aetherbrowser_model_cli_calls.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_provider(raw: str) -> ModelProvider:
    normalized = raw.strip().lower()
    if normalized == "hf":
        normalized = "huggingface"
    return ModelProvider(normalized)


def load_context_text(context_file: str | None = None, inline_context: str | None = None) -> str:
    if inline_context:
        return inline_context.strip()
    if context_file:
        return Path(context_file).read_text(encoding="utf-8").strip()
    return ""


def render_weighted_context(context_text: str, *, label: str, weight: float) -> str:
    cleaned = context_text.strip()
    if not cleaned:
        return ""
    return f"[weighted-context label={label} weight={weight:.2f}]\n" f"{cleaned}\n" "[/weighted-context]"


def build_logged_input(text: str, context_block: str) -> str:
    if not context_block:
        return text.strip()
    return f"{text.strip()}\n\n{context_block}"


def context_summary(context_text: str, *, label: str, weight: float, store_text: bool) -> dict[str, Any]:
    encoded = context_text.encode("utf-8")
    payload: dict[str, Any] = {
        "label": label,
        "weight": weight,
        "length": len(context_text),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if store_text:
        payload["text"] = context_text
    return payload


def append_jsonl_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


async def execute_request(
    *,
    text: str,
    provider: ModelProvider,
    model_id: str | None = None,
    auto_cascade: bool = True,
    context_text: str = "",
    context_label: str = "operator",
    context_weight: float = 1.0,
    metadata: dict[str, Any] | None = None,
    executor: ProviderExecutor | None = None,
    router: OctoArmorRouter | None = None,
) -> dict[str, Any]:
    weighted_context = render_weighted_context(context_text, label=context_label, weight=context_weight)
    logged_input = build_logged_input(text, weighted_context)
    router = router or OctoArmorRouter()
    squad = AgentSquad(WsFeed())
    routing_preferences = {"KO": provider.value}
    plan = build_command_plan(
        text=logged_input,
        squad=squad,
        router=router,
        routing_preferences=routing_preferences,
        auto_cascade=auto_cascade,
    )
    model_ids = {provider: model_id} if model_id else None
    executor = executor or ProviderExecutor(model_ids=model_ids)
    execution = await executor.execute(plan)
    return {
        "timestamp_utc": utc_now(),
        "record_type": "aetherbrowser_model_cli_v1",
        "requested_provider": provider.value,
        "requested_model_id": model_id or executor._model_ids[provider],
        "text": text,
        "logged_input": logged_input,
        "context": (
            context_summary(
                context_text,
                label=context_label,
                weight=context_weight,
                store_text=False,
            )
            if context_text
            else {}
        ),
        "metadata": metadata or {},
        "plan": plan.to_dict(),
        "execution": execution.to_dict(),
    }


def write_artifact(record: dict[str, Any]) -> Path:
    output_dir = PROJECT_ROOT / "artifacts" / "aetherbrowser_cli" / f"run-{utc_stamp()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "result.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an AetherBrowser command through a chosen model provider.")
    parser.add_argument("text", help="User request to route through the AetherBrowser planner.")
    parser.add_argument(
        "--provider", default="huggingface", help="Model provider (huggingface|hf|local|haiku|sonnet|opus|flash|grok)"
    )
    parser.add_argument("--model-id", default="", help="Optional explicit model ID override for the chosen provider.")
    parser.add_argument("--context-file", default="", help="Optional UTF-8 file with extra operator context.")
    parser.add_argument("--context", default="", help="Optional inline context to weight with the request.")
    parser.add_argument("--context-label", default="operator")
    parser.add_argument("--context-weight", type=float, default=1.0)
    parser.add_argument("--metadata-json", default="", help="Optional JSON object to attach to the training record.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--no-cascade", action="store_true", help="Disable provider fallback chain.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    provider = resolve_provider(args.provider)
    context_text = load_context_text(args.context_file or None, args.context or None)
    metadata = json.loads(args.metadata_json) if args.metadata_json else {}
    record = asyncio.run(
        execute_request(
            text=args.text,
            provider=provider,
            model_id=args.model_id or None,
            auto_cascade=not args.no_cascade,
            context_text=context_text,
            context_label=args.context_label,
            context_weight=args.context_weight,
            metadata=metadata,
        )
    )
    artifact_path = write_artifact(record)
    log_path = Path(args.log_path)
    append_jsonl_record(log_path, {**record, "artifact_path": str(artifact_path)})
    payload = {**record, "artifact_path": str(artifact_path), "log_path": str(log_path)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"AetherBrowser CLI run complete: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
