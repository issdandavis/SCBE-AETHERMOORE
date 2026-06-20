"""Provider health matrix — Lane 41 of the 100-lane improvement map.

Checks each AI provider tier for:
  - env var presence (key configured)
  - SDK package installed
  - reachability (lightweight HEAD / list-models call, 5s timeout)

Outputs a JSON health matrix so bench lanes and the free-first router
know exactly which providers are available before making API calls.

Usage:
    python scripts/benchmark/provider_health_matrix.py [--json] [--out-dir DIR]
    scbe bench providers [--json]

Free-first policy: Ollama (local) > Cerebras/Groq (free-tier) > HuggingFace >
OpenAI/Anthropic/XAI (paid). A "READY" provider at the free tier should be
tried before escalating to paid routes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------


@dataclass
class ProviderSpec:
    name: str
    tier: str  # "local" | "free" | "paid"
    env_vars: list[str]
    sdk_package: str
    probe_fn: str  # name of the probe function
    base_url: Optional[str] = None
    default_model: Optional[str] = None


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="ollama",
        tier="local",
        env_vars=[],
        sdk_package="ollama",
        probe_fn="_probe_ollama",
        base_url="http://localhost:11434",
        default_model="llama3.2",
    ),
    ProviderSpec(
        name="cerebras",
        tier="free",
        env_vars=["CEREBRAS_API_KEY"],
        sdk_package="cerebras",
        probe_fn="_probe_openai_compat",
        base_url="https://api.cerebras.ai/v1",
        default_model="gpt-oss-120b",
    ),
    ProviderSpec(
        name="groq",
        tier="free",
        env_vars=["GROQ_API_KEY"],
        sdk_package="groq",
        probe_fn="_probe_openai_compat",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
    ),
    ProviderSpec(
        name="huggingface",
        tier="free",
        env_vars=["HUGGINGFACE_API_KEY", "HF_TOKEN"],
        sdk_package="huggingface_hub",
        probe_fn="_probe_huggingface",
        base_url="https://huggingface.co",
    ),
    ProviderSpec(
        name="openai",
        tier="paid",
        env_vars=["OPENAI_API_KEY"],
        sdk_package="openai",
        probe_fn="_probe_openai_compat",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    ProviderSpec(
        name="anthropic",
        tier="paid",
        env_vars=["ANTHROPIC_API_KEY"],
        sdk_package="anthropic",
        probe_fn="_probe_anthropic",
        base_url="https://api.anthropic.com",
        default_model="claude-haiku-4-5-20251001",
    ),
    ProviderSpec(
        name="xai",
        tier="paid",
        env_vars=["XAI_API_KEY"],
        sdk_package="openai",
        probe_fn="_probe_openai_compat",
        base_url="https://api.x.ai/v1",
        default_model="grok-3-mini",
    ),
]


# ---------------------------------------------------------------------------
# Health result
# ---------------------------------------------------------------------------


@dataclass
class ProviderHealth:
    name: str
    tier: str
    key_configured: bool
    sdk_installed: bool
    reachable: Optional[bool] = None  # None = not checked (no key / no sdk)
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    status: str = "UNKNOWN"  # READY | KEY_MISSING | SDK_MISSING | UNREACHABLE | ERROR
    free_first_rank: int = 0  # lower = try first; 0 = local, 1-2 = free, 3+ = paid


def _env_key(spec: ProviderSpec) -> Optional[str]:
    for var in spec.env_vars:
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return None


def _sdk_installed(package: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(package) is not None


# ---------------------------------------------------------------------------
# Probe functions — each returns (reachable, latency_ms, error)
# ---------------------------------------------------------------------------


def _probe_ollama(spec: ProviderSpec) -> tuple[bool, Optional[int], Optional[str]]:
    try:
        import urllib.request

        t0 = time.monotonic()
        req = urllib.request.Request(f"{spec.base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True, int((time.monotonic() - t0) * 1000), None
    except Exception as exc:
        return False, None, str(exc)[:120]


def _probe_openai_compat(spec: ProviderSpec) -> tuple[bool, Optional[int], Optional[str]]:
    key = _env_key(spec)
    if not key:
        return False, None, "no API key"
    try:
        import urllib.request

        t0 = time.monotonic()
        req = urllib.request.Request(
            f"{spec.base_url}/models",
            headers={"Authorization": f"Bearer {key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True, int((time.monotonic() - t0) * 1000), None
    except Exception as exc:
        msg = str(exc)[:120]
        # 401 = key invalid but endpoint reachable
        if "401" in msg or "403" in msg:
            return True, None, f"auth_error: {msg}"
        return False, None, msg


def _probe_huggingface(spec: ProviderSpec) -> tuple[bool, Optional[int], Optional[str]]:
    key = _env_key(spec)
    try:
        import urllib.request

        t0 = time.monotonic()
        headers = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(
            "https://huggingface.co/api/whoami-v2",
            headers=headers,
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True, int((time.monotonic() - t0) * 1000), None
    except Exception as exc:
        msg = str(exc)[:120]
        if "401" in msg:
            return True, None, f"auth_error (no key or invalid): {msg}"
        return False, None, msg


def _probe_anthropic(spec: ProviderSpec) -> tuple[bool, Optional[int], Optional[str]]:
    key = _env_key(spec)
    if not key:
        return False, None, "no API key"
    try:
        import urllib.request

        t0 = time.monotonic()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            data=b'{"model":"claude-haiku-4-5-20251001","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}',
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True, int((time.monotonic() - t0) * 1000), None
    except Exception as exc:
        msg = str(exc)[:120]
        if "401" in msg or "403" in msg:
            return True, None, f"auth_error: {msg}"
        # 400 = bad request but endpoint reachable (e.g. model not found)
        if "400" in msg or "HTTP Error 400" in msg:
            return True, None, None
        return False, None, msg


_PROBE_MAP = {
    "_probe_ollama": _probe_ollama,
    "_probe_openai_compat": _probe_openai_compat,
    "_probe_huggingface": _probe_huggingface,
    "_probe_anthropic": _probe_anthropic,
}

_FREE_FIRST_RANK = {
    "local": 0,
    "free": 1,
    "paid": 10,
}


def check_provider(spec: ProviderSpec, probe: bool = True) -> ProviderHealth:
    key_configured = bool(_env_key(spec)) if spec.env_vars else True
    sdk_installed = _sdk_installed(spec.sdk_package)

    health = ProviderHealth(
        name=spec.name,
        tier=spec.tier,
        key_configured=key_configured,
        sdk_installed=sdk_installed,
        free_first_rank=_FREE_FIRST_RANK.get(spec.tier, 99),
    )

    if not key_configured and spec.env_vars:
        health.status = "KEY_MISSING"
        return health

    if not probe:
        health.status = "KEY_OK" if key_configured else "NO_KEY"
        return health

    probe_fn = _PROBE_MAP.get(spec.probe_fn)
    if not probe_fn:
        health.status = "ERROR"
        health.error = f"unknown probe: {spec.probe_fn}"
        return health

    try:
        reachable, latency_ms, error = probe_fn(spec)
        health.reachable = reachable
        health.latency_ms = latency_ms
        health.error = error
        if reachable:
            health.status = "READY"
        else:
            health.status = "UNREACHABLE"
    except Exception as exc:
        health.reachable = False
        health.error = str(exc)[:120]
        health.status = "ERROR"

    return health


def build_matrix(probe: bool = True) -> dict:
    results = [check_provider(spec, probe=probe) for spec in PROVIDERS]
    ready = [r for r in results if r.status == "READY"]
    free_ready = [r for r in ready if r.tier in ("local", "free")]

    # Free-first recommendation: cheapest ready provider for ops triage
    recommended = sorted(free_ready, key=lambda r: (r.free_first_rank, r.latency_ms or 9999))
    recommended_name = recommended[0].name if recommended else (ready[0].name if ready else None)

    return {
        "schema_version": "scbe_provider_health_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "free_first_policy": "local > free > paid; escalate only when local/free unavailable or task requires it",
        "recommended_provider": recommended_name,
        "ready_count": len(ready),
        "total_count": len(results),
        "providers": [asdict(r) for r in results],
    }


def render_text(matrix: dict) -> str:
    lines = [
        f"Provider health matrix  ({matrix['ready_count']}/{matrix['total_count']} ready)",
        f"free-first recommended: {matrix['recommended_provider'] or 'none'}",
        "",
    ]
    for p in sorted(matrix["providers"], key=lambda x: x["free_first_rank"]):
        tier_tag = f"[{p['tier']}]"
        status = p["status"]
        latency = f"  {p['latency_ms']}ms" if p.get("latency_ms") else ""
        err = f"  ({p['error']})" if p.get("error") else ""
        lines.append(f"  {p['name']:<14} {tier_tag:<8} {status}{latency}{err}")
    return "\n".join(lines)


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    no_probe = "--no-probe" in args
    out_dir = None
    if "--out-dir" in args:
        idx = args.index("--out-dir")
        out_dir = args[idx + 1] if idx + 1 < len(args) else None

    matrix = build_matrix(probe=not no_probe)

    if out_dir:
        p = Path(out_dir)
        p.mkdir(parents=True, exist_ok=True)
        (p / "latest_report.json").write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    if as_json:
        print(json.dumps(matrix, indent=2))
    else:
        print(render_text(matrix))

    ready = sum(1 for p in matrix["providers"] if p["status"] == "READY")
    sys.exit(0 if ready > 0 else 1)


if __name__ == "__main__":
    main()
