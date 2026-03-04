#!/usr/bin/env python3
"""Google AI Studio (Gemini) smoke test for SCBE.

Reads API key from one of:
- GOOGLE_API_KEY
- GOOGLE_AI_API_KEY
- GEMINI_API_KEY

Usage:
  python scripts/system/google_ai_studio_smoke.py
  python scripts/system/google_ai_studio_smoke.py --model gemini-2.0-flash
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _resolve_key() -> tuple[str | None, str | None]:
    candidates = ["GOOGLE_API_KEY", "GOOGLE_AI_API_KEY", "GEMINI_API_KEY"]
    for name in candidates:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    # Fallback: load from local .env if present.
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k in candidates and v:
                return v, f"{k}(.env)"
    return None, None


def _masked(v: str) -> str:
    if len(v) < 10:
        return "***"
    return f"{v[:6]}...{v[-4:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test Google AI Studio connectivity.")
    parser.add_argument("--model", default=os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--prompt", default="Reply with: SCBE Google link OK")
    args = parser.parse_args()

    key, key_name = _resolve_key()
    if not key:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "missing_api_key",
                    "accepted_env_vars": ["GOOGLE_API_KEY", "GOOGLE_AI_API_KEY", "GEMINI_API_KEY"],
                }
            )
        )
        return 1

    base = "https://generativelanguage.googleapis.com/v1beta"
    endpoint = f"{base}/models/{args.model}:generateContent"
    query = urllib.parse.urlencode({"key": key})
    url = f"{endpoint}?{query}"

    body = {
        "contents": [
            {"role": "user", "parts": [{"text": args.prompt}]},
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 80,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        usage = payload.get("usageMetadata", {})
        print(
            json.dumps(
                {
                    "ok": True,
                    "model": args.model,
                    "api_key_env": key_name,
                    "api_key_masked": _masked(key),
                    "reply_preview": text[:160],
                    "usage": usage,
                }
            )
        )
        return 0
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "ok": False,
                    "model": args.model,
                    "api_key_env": key_name,
                    "api_key_masked": _masked(key),
                    "http_status": exc.code,
                    "error": details[:500],
                }
            )
        )
        return 2
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "ok": False,
                    "model": args.model,
                    "api_key_env": key_name,
                    "api_key_masked": _masked(key),
                    "error": str(exc),
                }
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
