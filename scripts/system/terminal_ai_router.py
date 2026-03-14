#!/usr/bin/env python3
"""Cheap-first terminal router for OpenAI/Anthropic/xAI with daily spend caps.

Features:
- secret alias sync into canonical env keys
- live provider health checks (openai/anthropic/xai/huggingface)
- cheap -> standard -> premium escalation by prompt complexity
- daily spend caps tracked in local ledger
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "governance" / "terminal_ai_router_profiles.json"
DEFAULT_HEALTH_PATH = REPO_ROOT / "artifacts" / "ai_router" / "terminal_ai_health.json"
DEFAULT_CALL_PATH = REPO_ROOT / "artifacts" / "ai_router" / "terminal_ai_router_last.json"
LEDGER_DIR = REPO_ROOT / "artifacts" / "ai_router"

ALIAS_SYNC_MAP: dict[str, list[str]] = {
    "OPENAI_API_KEY": ["OPENAI_KEY"],
    "ANTHROPIC_API_KEY": ["CLAUDE_API_KEY"],
    "XAI_API_KEY": ["GROK_API_KEY"],
    "HF_TOKEN": ["HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
}

DEFAULT_PROVIDER_KEYS: dict[str, list[str]] = {
    "openai": ["OPENAI_API_KEY", "OPENAI_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
}

DEFAULT_PROVIDER_ORDER = ["openai", "anthropic", "xai"]
DEFAULT_COMPLEXITY_TIERS = {
    "easy": ["cheap"],
    "medium": ["cheap", "standard"],
    "hard": ["cheap", "standard", "premium"],
}
SENSITIVE_METADATA_ITERATIONS = 120_000
DEFAULT_PROVIDER_HOSTS: dict[str, set[str]] = {
    "openai": {"api.openai.com"},
    "anthropic": {"api.anthropic.com"},
    "xai": {"api.x.ai"},
    "huggingface": {"huggingface.co"},
    "hf": {"huggingface.co"},
}


if str(REPO_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(REPO_ROOT))

from src.security.secret_store import get_secret, set_secret  # noqa: E402


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now_utc().isoformat()


def _utc_day() -> str:
    return _now_utc().strftime("%Y-%m-%d")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sanitize_for_report(payload), indent=2), encoding="utf-8")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _response_metadata(text: str | None) -> dict[str, Any]:
    value = str(text or "")
    return {
        "present": bool(value),
        "length": len(value),
        "pbkdf2_sha256": _sensitive_fingerprint(value) if value else "",
    }


def _sensitive_fingerprint(value: str) -> str:
    salt = os.getenv("SCBE_METADATA_HASH_KEY", "scbe-terminal-router-metadata").encode("utf-8")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        value.encode("utf-8"),
        salt,
        SENSITIVE_METADATA_ITERATIONS,
    )
    return derived.hex()


def _safe_body_summary(body: Any) -> dict[str, Any]:
    if isinstance(body, dict):
        return {
            "type": "dict",
            "size": len(body),
            "keys": sorted(str(key) for key in body.keys())[:32],
        }
    if isinstance(body, list):
        return {
            "type": "list",
            "length": len(body),
        }
    if body is None:
        return {"type": "null", "present": False}
    return {
        "type": type(body).__name__,
        "present": True,
        "length": len(str(body)),
    }


def _attach_response_summary(detail: dict[str, Any], body: Any) -> None:
    summary = _safe_body_summary(body)
    if summary.get("present", True) or summary.get("type") != "null":
        detail["response_summary"] = summary


def _resolve_artifact_output(output_path: str) -> Path:
    artifacts_root = (REPO_ROOT / "artifacts").resolve()
    candidate = Path(output_path)
    resolved = (REPO_ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not _is_relative_to(resolved, artifacts_root):
        raise ValueError("Output path must stay under artifacts/")
    return resolved


def _validate_provider_endpoint(endpoint: str, provider: str, provider_cfg: dict[str, Any]) -> str:
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    allow_insecure_local = bool(provider_cfg.get("allow_insecure_local", False))
    if parsed.scheme != "https":
        if not allow_insecure_local or host not in {"localhost", "127.0.0.1"}:
            raise ValueError(f"Provider endpoint for {provider} must use HTTPS unless local override is enabled")
    allow_custom_endpoint = bool(provider_cfg.get("allow_custom_endpoint", False))
    allowed_hosts = DEFAULT_PROVIDER_HOSTS.get(provider, set())
    if allowed_hosts and not allow_custom_endpoint and host not in allowed_hosts:
        raise ValueError(f"Provider endpoint for {provider} must use an approved host")
    return endpoint


def _summarize_mapping(values: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, dict):
            row = {"status": value.get("status")}
            detail = value.get("detail")
            if isinstance(detail, dict):
                if detail.get("http_status") is not None:
                    row["http_status"] = detail.get("http_status")
                if detail.get("reason"):
                    row["reason"] = detail.get("reason")
                if detail.get("error"):
                    row["error"] = detail.get("error")
            summary[key] = row
        else:
            summary[key] = value
    return summary


def _sanitize_for_report(payload: Any) -> Any:
    sensitive_fragments = {
        "api_key",
        "content",
        "prompt",
        "token",
        "secret",
        "authorization",
        "x-api-key",
        "stdout",
        "stderr",
        "response",
        "response_excerpt",
        "raw",
    }
    if isinstance(payload, dict):
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key).lower()
            if any(fragment in key_text for fragment in sensitive_fragments) and not (
                key_text.endswith("_metadata") or key_text.endswith("_summary")
            ):
                clean[key] = "[redacted]"
                continue
            clean[key] = _sanitize_for_report(value)
        return clean
    if isinstance(payload, list):
        return [_sanitize_for_report(item) for item in payload]
    return payload


def _request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> tuple[int | None, dict[str, Any], str]:
    request_headers = dict(headers or {})
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, headers=request_headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return int(resp.status), {}, ""
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            return int(resp.status), parsed, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return int(exc.code), parsed, f"http_error_{exc.code}"
    except urllib.error.URLError as exc:
        return None, {"error": str(getattr(exc, "reason", exc))}, "url_error"
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}, "exception"


def _pick_secret_value(keys: list[str]) -> tuple[str, str, str]:
    for key in keys:
        env_val = os.getenv(key, "").strip()
        if env_val:
            return key, env_val, "env"
        secret_val = get_secret(key, "").strip()
        if secret_val:
            return key, secret_val, "secret_store"
    return "", "", ""


def _sync_secret_aliases() -> dict[str, Any]:
    results: dict[str, Any] = {}
    for canonical, aliases in ALIAS_SYNC_MAP.items():
        canonical_env = os.getenv(canonical, "").strip()
        canonical_secret = get_secret(canonical, "").strip()
        if canonical_env or canonical_secret:
            source = "env" if canonical_env else canonical
            results[canonical] = {"status": "set", "source": source}
            continue

        alias_key, alias_value, alias_source = _pick_secret_value(aliases)
        if alias_value:
            set_secret(canonical, alias_value, note=f"synced from {alias_key}")
            os.environ[canonical] = alias_value
            results[canonical] = {
                "status": "synced",
                "source": alias_key,
                "source_type": alias_source,
            }
        else:
            results[canonical] = {"status": "missing", "source": None}
    return results


def _provider_env_keys(provider: str, provider_cfg: dict[str, Any]) -> list[str]:
    from_cfg = provider_cfg.get("env_keys")
    if isinstance(from_cfg, list) and from_cfg:
        return [str(x).strip() for x in from_cfg if str(x).strip()]
    return DEFAULT_PROVIDER_KEYS.get(provider, [])


def _status_from_http(http_status: int | None) -> str:
    if http_status == 200:
        return "ok"
    if http_status in {401, 403}:
        return "requires_auth"
    if http_status is None:
        return "down"
    return "degraded"


def _health_openai(provider_cfg: dict[str, Any]) -> dict[str, Any]:
    env_keys = _provider_env_keys("openai", provider_cfg)
    key_name, key_value, key_source = _pick_secret_value(env_keys)
    if not key_value:
        return {"status": "requires_auth", "detail": {"reason": "missing_key", "accepted_keys": env_keys}}

    url = _validate_provider_endpoint(
        str(provider_cfg.get("health_endpoint") or "https://api.openai.com/v1/models").strip(),
        "openai",
        provider_cfg,
    )
    status, body, error = _request_json(url, headers={"Authorization": f"Bearer {key_value}"}, timeout=20)
    detail = {
        "http_status": status,
        "key_name": key_name,
        "key_source": key_source,
        "error": error,
    }
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            detail["sample_models"] = [str(item.get("id", "")) for item in data[:8] if isinstance(item, dict)]
        else:
            _attach_response_summary(detail, body)
    else:
        _attach_response_summary(detail, body)
    return {"status": _status_from_http(status), "detail": detail}


def _health_anthropic(provider_cfg: dict[str, Any]) -> dict[str, Any]:
    env_keys = _provider_env_keys("anthropic", provider_cfg)
    key_name, key_value, key_source = _pick_secret_value(env_keys)
    if not key_value:
        return {"status": "requires_auth", "detail": {"reason": "missing_key", "accepted_keys": env_keys}}

    url = _validate_provider_endpoint(
        str(provider_cfg.get("health_endpoint") or "https://api.anthropic.com/v1/models").strip(),
        "anthropic",
        provider_cfg,
    )
    headers = {
        "x-api-key": key_value,
        "anthropic-version": "2023-06-01",
    }
    status, body, error = _request_json(url, headers=headers, timeout=20)
    detail = {
        "http_status": status,
        "key_name": key_name,
        "key_source": key_source,
        "error": error,
    }
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            detail["sample_models"] = [str(item.get("id", "")) for item in data[:8] if isinstance(item, dict)]
        else:
            _attach_response_summary(detail, body)
    else:
        _attach_response_summary(detail, body)
    return {"status": _status_from_http(status), "detail": detail}


def _health_xai(provider_cfg: dict[str, Any]) -> dict[str, Any]:
    env_keys = _provider_env_keys("xai", provider_cfg)
    key_name, key_value, key_source = _pick_secret_value(env_keys)
    if not key_value:
        return {"status": "requires_auth", "detail": {"reason": "missing_key", "accepted_keys": env_keys}}

    url = _validate_provider_endpoint(
        str(provider_cfg.get("health_endpoint") or "https://api.x.ai/v1/models").strip(),
        "xai",
        provider_cfg,
    )
    status, body, error = _request_json(url, headers={"Authorization": f"Bearer {key_value}"}, timeout=20)
    detail = {
        "http_status": status,
        "key_name": key_name,
        "key_source": key_source,
        "error": error,
    }
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            detail["sample_models"] = [str(item.get("id", "")) for item in data[:8] if isinstance(item, dict)]
        else:
            _attach_response_summary(detail, body)
    else:
        _attach_response_summary(detail, body)
    return {"status": _status_from_http(status), "detail": detail}


def _health_hf(provider_cfg: dict[str, Any]) -> dict[str, Any]:
    env_keys = _provider_env_keys("huggingface", provider_cfg)
    key_name, key_value, key_source = _pick_secret_value(env_keys)
    if not key_value:
        return {"status": "requires_auth", "detail": {"reason": "missing_key", "accepted_keys": env_keys}}

    url = _validate_provider_endpoint(
        str(provider_cfg.get("health_endpoint") or "https://huggingface.co/api/whoami-v2").strip(),
        "huggingface",
        provider_cfg,
    )
    status, body, error = _request_json(url, headers={"Authorization": f"Bearer {key_value}"}, timeout=20)
    detail = {
        "http_status": status,
        "key_name": key_name,
        "key_source": key_source,
        "error": error,
    }
    if isinstance(body, dict):
        detail["user"] = body.get("name") or body.get("fullname")
    else:
        _attach_response_summary(detail, body)
    return {"status": _status_from_http(status), "detail": detail}


def _load_config(path: Path) -> dict[str, Any]:
    cfg = _read_json(path, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault("provider_order", DEFAULT_PROVIDER_ORDER)
    cfg.setdefault("complexity_tiers", DEFAULT_COMPLEXITY_TIERS)
    cfg.setdefault("providers", {})
    cfg.setdefault(
        "default_system_prompt",
        "You are an SCBE terminal assistant. Keep answers short, practical, and evidence-aware.",
    )
    return cfg


def run_health(args: argparse.Namespace) -> int:
    config = _load_config(Path(args.config))
    providers_cfg = config.get("providers", {})
    checks = [item.strip().lower() for item in str(args.checks).split(",") if item.strip()]

    alias_sync = _sync_secret_aliases() if args.sync_aliases else {}

    status_map: dict[str, dict[str, Any]] = {}
    for provider in checks:
        provider_cfg = providers_cfg.get(provider, {})
        if provider == "openai":
            status_map[provider] = _health_openai(provider_cfg)
        elif provider == "anthropic":
            status_map[provider] = _health_anthropic(provider_cfg)
        elif provider == "xai":
            status_map[provider] = _health_xai(provider_cfg)
        elif provider in {"huggingface", "hf"}:
            status_map["huggingface"] = _health_hf(provider_cfg)
        else:
            status_map[provider] = {
                "status": "degraded",
                "detail": {"reason": f"unsupported_health_provider:{provider}"},
            }

    payload = {
        "generated_at_utc": _iso_now(),
        "config_path": str(Path(args.config).resolve()),
        "checks": checks,
        "alias_sync": alias_sync,
        "status": status_map,
    }
    output_path = _resolve_artifact_output(args.output)
    _write_json(output_path, payload)
    stdout_payload = {
        "generated_at_utc": payload["generated_at_utc"],
        "config_path": payload["config_path"],
        "checks": checks,
        "output_path": str(output_path),
        "alias_sync": _summarize_mapping(alias_sync),
        "status": _summarize_mapping(status_map),
    }
    print(json.dumps(stdout_payload, indent=2))

    if args.strict:
        failing = [name for name, val in status_map.items() if val.get("status") != "ok"]
        return 1 if failing else 0
    hard_fail = [name for name, val in status_map.items() if val.get("status") in {"down", "degraded"}]
    return 1 if hard_fail else 0


def _load_ledger() -> tuple[Path, dict[str, Any]]:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    path = LEDGER_DIR / f"spend_ledger_{_utc_day()}.json"
    payload = _read_json(path, default={})
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("date_utc", _utc_day())
    payload.setdefault("providers", {})
    payload.setdefault("events", [])
    return path, payload


def _provider_spend_cents(ledger: dict[str, Any], provider: str) -> float:
    providers = ledger.get("providers", {})
    row = providers.get(provider, {})
    try:
        return float(row.get("spent_cents_estimate", 0.0))
    except Exception:
        return 0.0


def _record_spend(
    ledger: dict[str, Any],
    provider: str,
    *,
    model: str,
    tier: str,
    estimated_cents: float,
    response_ok: bool,
) -> None:
    providers = ledger.setdefault("providers", {})
    row = providers.setdefault(provider, {"spent_cents_estimate": 0.0, "calls": 0, "successful_calls": 0})
    row["calls"] = int(row.get("calls", 0)) + 1
    row["spent_cents_estimate"] = round(float(row.get("spent_cents_estimate", 0.0)) + float(estimated_cents), 4)
    if response_ok:
        row["successful_calls"] = int(row.get("successful_calls", 0)) + 1
    ledger.setdefault("events", []).append(
        {
            "time_utc": _iso_now(),
            "provider": provider,
            "model": model,
            "tier": tier,
            "estimated_cents": float(estimated_cents),
            "ok": bool(response_ok),
        }
    )


def _classify_complexity(prompt: str) -> str:
    text = prompt.lower()
    tokens = len(prompt.split())
    hard_terms = [
        "proof",
        "formal",
        "architecture",
        "threat model",
        "tradeoff",
        "benchmark",
        "governance",
        "multi-step",
        "deep research",
    ]
    medium_terms = [
        "plan",
        "summarize",
        "compare",
        "analyze",
        "design",
        "evaluate",
    ]
    hard_hits = sum(1 for term in hard_terms if term in text)
    medium_hits = sum(1 for term in medium_terms if term in text)
    if tokens >= 360 or hard_hits >= 2:
        return "hard"
    if tokens >= 140 or medium_hits >= 1:
        return "medium"
    return "easy"


def _extract_openai_text(body: dict[str, Any]) -> str:
    choices = body.get("choices", []) if isinstance(body, dict) else []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message", {}) if isinstance(first, dict) else {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
        return "\n".join(chunks).strip()
    return str(content or "")


def _extract_anthropic_text(body: dict[str, Any]) -> str:
    content = body.get("content", []) if isinstance(body, dict) else []
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
        return "\n".join(chunks).strip()
    if isinstance(content, str):
        return content
    return ""


def _call_openai_like(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_sec: int,
) -> tuple[bool, str, int | None, dict[str, Any], str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    status, body, error = _request_json(
        endpoint,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        body=payload,
        timeout=timeout_sec,
    )
    text = _extract_openai_text(body)
    ok = bool(status == 200 and text.strip())
    return ok, text, status, body, error


def _call_anthropic(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_sec: int,
) -> tuple[bool, str, int | None, dict[str, Any], str]:
    payload = {
        "model": model,
        "system": system_prompt,
        "max_tokens": max_output_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }
    status, body, error = _request_json(
        endpoint,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        body=payload,
        timeout=timeout_sec,
    )
    text = _extract_anthropic_text(body)
    ok = bool(status == 200 and text.strip())
    return ok, text, status, body, error


def run_call(args: argparse.Namespace) -> int:
    config = _load_config(Path(args.config))
    providers_cfg: dict[str, Any] = config.get("providers", {})
    provider_order = [item.strip().lower() for item in str(args.providers).split(",") if item.strip()]
    if not provider_order:
        provider_order = [str(x).strip().lower() for x in config.get("provider_order", DEFAULT_PROVIDER_ORDER)]
    provider_order = [x for x in provider_order if x]

    if args.sync_aliases:
        _sync_secret_aliases()

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    prompt = str(prompt or "").strip()
    if not prompt:
        print("prompt is required (use --prompt or --prompt-file)")
        return 2

    complexity = args.complexity
    if complexity == "auto":
        complexity = _classify_complexity(prompt)

    tiers_map = config.get("complexity_tiers", DEFAULT_COMPLEXITY_TIERS)
    tiers = tiers_map.get(complexity, tiers_map.get("medium", ["cheap", "standard"]))
    if not isinstance(tiers, list) or not tiers:
        tiers = ["cheap", "standard"]
    tiers = [str(t).strip().lower() for t in tiers if str(t).strip()]

    ledger_path, ledger = _load_ledger()
    system_prompt = str(config.get("default_system_prompt", "")).strip() or (
        "You are an SCBE terminal assistant. Keep answers short, practical, and evidence-aware."
    )

    attempts: list[dict[str, Any]] = []
    final_text = ""
    selected: dict[str, Any] | None = None

    for tier in tiers:
        for provider in provider_order:
            cfg = providers_cfg.get(provider, {})
            if not isinstance(cfg, dict):
                attempts.append({"provider": provider, "tier": tier, "status": "skipped", "reason": "missing_config"})
                continue
            if not bool(cfg.get("enabled", True)):
                attempts.append({"provider": provider, "tier": tier, "status": "skipped", "reason": "disabled"})
                continue

            tier_cfg = cfg.get("tiers", {}).get(tier, {})
            if not isinstance(tier_cfg, dict):
                attempts.append({"provider": provider, "tier": tier, "status": "skipped", "reason": "tier_not_configured"})
                continue

            model = str(tier_cfg.get("model", "")).strip()
            if not model:
                attempts.append({"provider": provider, "tier": tier, "status": "skipped", "reason": "empty_model"})
                continue

            key_candidates = _provider_env_keys(provider, cfg)
            key_name, api_key, key_source = _pick_secret_value(key_candidates)
            if not api_key:
                attempts.append(
                    {
                        "provider": provider,
                        "tier": tier,
                        "model": model,
                        "status": "skipped",
                        "reason": "missing_api_key",
                        "accepted_keys": key_candidates,
                    }
                )
                continue

            est_cents = float(tier_cfg.get("estimated_cents", 1.0))
            cap_cents = float(cfg.get("daily_cap_usd", 5.0)) * 100.0
            spent = _provider_spend_cents(ledger, provider)
            remaining = cap_cents - spent
            if est_cents > remaining:
                attempts.append(
                    {
                        "provider": provider,
                        "tier": tier,
                        "model": model,
                        "status": "skipped",
                        "reason": "daily_cap_reached",
                        "remaining_cents": round(remaining, 4),
                        "needed_cents": est_cents,
                    }
                )
                continue

            timeout_sec = int(cfg.get("timeout_sec", 45))
            endpoint = str(cfg.get("chat_endpoint", "")).strip()
            if not endpoint:
                attempts.append(
                    {
                        "provider": provider,
                        "tier": tier,
                        "model": model,
                        "status": "skipped",
                        "reason": "missing_chat_endpoint",
                    }
                )
                continue

            try:
                endpoint = _validate_provider_endpoint(endpoint, provider, cfg)
            except ValueError as exc:
                attempts.append(
                    {
                        "provider": provider,
                        "tier": tier,
                        "model": model,
                        "status": "skipped",
                        "reason": str(exc),
                    }
                )
                continue

            if provider in {"openai", "xai"}:
                ok, text, http_status, body, error = _call_openai_like(
                    endpoint=endpoint,
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    timeout_sec=timeout_sec,
                )
            elif provider == "anthropic":
                ok, text, http_status, body, error = _call_anthropic(
                    endpoint=endpoint,
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    prompt=prompt,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                    timeout_sec=timeout_sec,
                )
            else:
                attempts.append(
                    {
                        "provider": provider,
                        "tier": tier,
                        "model": model,
                        "status": "skipped",
                        "reason": "unsupported_provider_for_call",
                    }
                )
                continue

            attempts.append(
                {
                    "provider": provider,
                    "tier": tier,
                    "model": model,
                    "key_name": key_name,
                    "key_source": key_source,
                    "status": "ok" if ok else "failed",
                    "http_status": http_status,
                    "error": error,
                }
            )

            _record_spend(
                ledger,
                provider,
                model=model,
                tier=tier,
                estimated_cents=est_cents,
                response_ok=ok,
            )

            if ok:
                selected = {
                    "provider": provider,
                    "tier": tier,
                    "model": model,
                    "http_status": http_status,
                    "estimated_cents": est_cents,
                }
                final_text = text.strip()
                break

            attempts[-1]["response_summary"] = _safe_body_summary(body)
        if selected:
            break

    _write_json(ledger_path, ledger)
    output_path = _resolve_artifact_output(args.output)

    result = {
        "generated_at_utc": _iso_now(),
        "config_path": str(Path(args.config).resolve()),
        "complexity_requested": args.complexity,
        "complexity_used": complexity,
        "provider_order": provider_order,
        "tiers_tried": tiers,
        "selected": selected,
        "attempts": attempts,
        "response_metadata": _response_metadata(final_text),
        "ledger_path": str(ledger_path.resolve()),
    }
    _write_json(output_path, result)
    print(json.dumps(_sanitize_for_report({**result, "output_path": str(output_path)}), indent=2))

    if args.print_response and final_text:
        print("")
        print(json.dumps({"response_metadata": _response_metadata(final_text)}, indent=2))

    return 0 if selected else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCBE terminal AI router with cheap-first escalation and caps.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Router profile config JSON path.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health", help="Run provider health checks.")
    health.add_argument(
        "--checks",
        default="openai,anthropic,xai,huggingface",
        help="Comma-separated checks.",
    )
    health.add_argument(
        "--output",
        default=str(DEFAULT_HEALTH_PATH),
        help="Health report output path.",
    )
    health.add_argument("--sync-aliases", action="store_true", help="Sync alias keys into canonical names first.")
    health.add_argument("--strict", action="store_true", help="Exit non-zero unless every requested check is ok.")
    health.set_defaults(func=run_health)

    call = sub.add_parser("call", help="Route a prompt through cheap-first provider escalation.")
    call.add_argument("--prompt", default="", help="Prompt text.")
    call.add_argument("--prompt-file", default="", help="Path to prompt text file.")
    call.add_argument(
        "--complexity",
        choices=["auto", "easy", "medium", "hard"],
        default="auto",
        help="Routing complexity tier.",
    )
    call.add_argument(
        "--providers",
        default="",
        help="Optional comma-separated provider override order.",
    )
    call.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    call.add_argument("--max-output-tokens", type=int, default=420, help="Max output tokens.")
    call.add_argument(
        "--output",
        default=str(DEFAULT_CALL_PATH),
        help="Call report output path.",
    )
    call.add_argument("--sync-aliases", action="store_true", help="Sync alias keys into canonical names first.")
    call.add_argument("--print-response", action="store_true", help="Print final response text to stdout.")
    call.set_defaults(func=run_call)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
