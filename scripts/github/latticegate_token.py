#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.github_app.client import GitHubAppApiClient, GitHubAppConfig


def _resolve_installation_id(explicit: str | None) -> int:
    raw = (
        explicit
        or os.getenv("GITHUB_APP_INSTALLATION_ID", "").strip()
        or os.getenv("LATTICEGATE_INSTALLATION_ID", "").strip()
    )
    if not raw:
        raise SystemExit(
            "Missing installation id. Set GITHUB_APP_INSTALLATION_ID or pass --installation-id."
        )
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"Invalid installation id: {raw}") from exc


def _validate_config(config: GitHubAppConfig) -> None:
    missing: list[str] = []
    if not config.app_id:
        missing.append("GITHUB_APP_ID")
    if not config.private_key_pem:
        missing.append("GITHUB_APP_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH")
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing GitHub App configuration: {joined}")


async def _mint_token(config: GitHubAppConfig, installation_id: int) -> str:
    client = GitHubAppApiClient(config)
    return await client.create_installation_token(installation_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint a GitHub App installation token for LatticeGate.")
    parser.add_argument("--installation-id", help="Override GITHUB_APP_INSTALLATION_ID for this call.")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of the raw token.")
    args = parser.parse_args()

    config = GitHubAppConfig.from_env()
    _validate_config(config)
    installation_id = _resolve_installation_id(args.installation_id)
    token = asyncio.run(_mint_token(config, installation_id))

    if args.json:
        payload = {
            "app_id": config.app_id,
            "installation_id": installation_id,
            "token": token,
        }
        print(json.dumps(payload))
    else:
        print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
