#!/usr/bin/env python3
"""Dry-run or execute compact live smoke calls for harness providers."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark.harness_provider_matrix import DEFAULT_MODEL_REFS  # noqa: E402
from src.agent_comms import compact_system_prompt, resolve_provider_model  # noqa: E402

SMOKE_USER_PROMPT = (
    'Return exactly this JSON shape with no prose: {"ok":true,"role":"harness-smoke","tokens_saved":true}'
)


def parse_model_refs(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_MODEL_REFS[:3])
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_chat_payload(provider_id: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [
            {
                "role": "system",
                "content": compact_system_prompt(
                    phase="smoke",
                    tongue="KO",
                    domain="agentic_harness",
                    expected_output="json",
                    adapter=provider_id,
                ),
            },
            {"role": "user", "content": SMOKE_USER_PROMPT},
        ],
    }


def call_chat_completion(
    *,
    provider_ref: str,
    timeout: float = 20.0,
    opener: Callable[..., Any] = urlrequest.urlopen,
) -> dict[str, Any]:
    provider, model = resolve_provider_model(provider_ref)
    token = provider.token()
    if not token:
        return {
            "ref": provider_ref,
            "provider": provider.provider,
            "model": model,
            "status": "skipped",
            "reason": "missing_token_or_local_server",
            "latency_ms": None,
            "content": "",
            "json_ok": False,
        }

    payload = build_chat_payload(provider.provider, model)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token != "local-no-auth":
        headers["Authorization"] = f"Bearer {token}"

    req = urlrequest.Request(
        provider.chat_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            latency_ms = int((time.perf_counter() - started) * 1000)
            body = json.loads(raw)
            content = _extract_message_text(body)
            return {
                "ref": provider_ref,
                "provider": provider.provider,
                "model": model,
                "status": "passed" if _content_is_jsonish(content) else "failed",
                "reason": "",
                "latency_ms": latency_ms,
                "content": content[:500],
                "json_ok": _content_is_jsonish(content),
            }
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return _failure(provider_ref, provider.provider, model, "http_error", str(exc.code), detail)
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return _failure(provider_ref, provider.provider, model, "error", str(exc), "")


def _extract_message_text(body: dict[str, Any]) -> str:
    """Return content text while tolerating reasoning-only model responses.

    Some NVIDIA-hosted reasoning models emit ``content: null`` until enough
    tokens have been generated, while placing partial text in
    ``reasoning_content`` or ``reasoning``. Smoke tests should report that
    text instead of crashing on a non-string content value.
    """

    choices = body.get("choices") or [{}]
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    for key in ("content", "reasoning_content", "reasoning"):
        value = message.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _content_is_jsonish(content: str) -> bool:
    text = content.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    return parsed.get("ok") is True and parsed.get("role") == "harness-smoke"


def _failure(ref: str, provider: str, model: str, status: str, reason: str, detail: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "provider": provider,
        "model": model,
        "status": status,
        "reason": (reason or detail)[:240],
        "latency_ms": None,
        "content": detail[:500],
        "json_ok": False,
    }


def build_smoke_report(model_refs: list[str], *, execute: bool = False, timeout: float = 20.0) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for ref in model_refs:
        provider, model = resolve_provider_model(ref)
        if execute:
            results.append(call_chat_completion(provider_ref=ref, timeout=timeout))
        else:
            results.append(
                {
                    "ref": ref,
                    "provider": provider.provider,
                    "model": model,
                    "status": "planned",
                    "reason": "dry_run_use_execute_to_call_provider",
                    "latency_ms": None,
                    "content": "",
                    "json_ok": False,
                    "available": provider.status()["available"],
                    "chat_url": provider.chat_url,
                    "tool_adapter": provider.tool_adapter,
                }
            )

    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {
        "schema_version": "scbe_harness_live_smoke_v1",
        "mode": "execute" if execute else "dry_run",
        "model_count": len(model_refs),
        "summary": counts,
        "results": results,
        "prompt": SMOKE_USER_PROMPT,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODEL_REFS[:3]), help="Comma-separated provider:model refs")
    parser.add_argument("--execute", action="store_true", help="Actually call providers. Default is dry-run.")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_smoke_report(parse_model_refs(args.models), execute=args.execute, timeout=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("GeoSeal Harness Live Smoke")
        print("=" * 30)
        print(f"mode={report['mode']} models={report['model_count']} summary={report['summary']}")
        for result in report["results"]:
            print(f"- {result['ref']}: {result['status']} {result['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
