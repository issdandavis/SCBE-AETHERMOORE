#!/usr/bin/env python3
"""Sync live World Anvil content to local JSON exports for lore RAG."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pywaclient.api import BoromirApiClient
from pywaclient.exceptions import (
    AccessForbidden,
    ConnectionException,
    FailedRequest,
    ResourceNotFound,
    UnauthorizedRequest,
    UnprocessableDataProvided,
    WorldAnvilClientException,
    WorldAnvilServerException,
)


DEFAULT_REPO_ROOT = "C:/Users/issda/SCBE-AETHERMOORE"
DEFAULT_SKILL_DIR = "C:/Users/issda/.codex/skills/scbe-world-anvil-lore-rag-7th-tongue"
DEFAULT_MIRROR_SCRIPT = "C:/Users/issda/.codex/skills/scbe-api-key-local-mirror/scripts/key_mirror.py"
DEFAULT_VAULT_DIR = str(Path.home() / ".scbe_keys")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sanitize_for_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value).strip("-_") or "world"


def resolve_path(repo_root: Path, maybe_rel: str) -> Path:
    p = Path(maybe_rel)
    return p if p.is_absolute() else repo_root / p


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_json(payload: dict[str, Any], *, indent: int | None = 2) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync live World Anvil content to local JSON export files.")
    parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT)
    parser.add_argument("--output-dir", default="", help="Default: exports/world_anvil/live_sync_<timestamp>")
    parser.add_argument("--world-id", default="", help="Specific world id to sync. Auto-detect if omitted.")
    parser.add_argument(
        "--endpoints",
        default="articles,categories,timelines,maps,manuscripts,chronicles,secrets,histories,images",
        help="Comma-separated world endpoints to sync.",
    )
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-items-per-endpoint", type=int, default=200)
    parser.add_argument("--granularity", type=int, default=2, choices=[1, 2], help="Detail fetch granularity.")
    parser.add_argument("--no-details", action="store_true", help="Skip per-item detail fetch calls.")
    parser.add_argument("--dry-run", action="store_true", help="Preflight auth/config only; do not fetch content.")
    parser.add_argument("--mock", action="store_true", help="Write mock World Anvil-like export files without API auth.")
    parser.add_argument("--self-test", action="store_true", help="Run identity/world discovery test and exit.")
    parser.add_argument("--app-key-env", default="WORLD_ANVIL_APP_KEY")
    parser.add_argument("--token-env", default="WORLD_ANVIL_USER_TOKEN")
    parser.add_argument("--script-name", default="SCBE-AETHERMOORE")
    parser.add_argument("--script-version", default="1.0.0")
    parser.add_argument("--script-url", default="https://github.com/issdandavis/SCBE-AETHERMOORE")
    parser.add_argument("--key-mirror-script", default=DEFAULT_MIRROR_SCRIPT)
    parser.add_argument("--vault-dir", default=DEFAULT_VAULT_DIR)
    parser.add_argument(
        "--mirror-service-app",
        default="world_anvil_app_key,world_anvil_api_key,world_anvil_app",
        help="Comma-separated mirror service names for app key fallback.",
    )
    parser.add_argument(
        "--mirror-service-token",
        default="world_anvil_user_token,world_anvil_token,world_anvil_auth_token",
        help="Comma-separated mirror service names for token fallback.",
    )
    return parser.parse_args()


def read_mirror_key(
    mirror_script: Path,
    vault_dir: Path,
    service_candidates: list[str],
) -> tuple[str, str]:
    if not mirror_script.exists():
        return "", ""

    for service in service_candidates:
        cmd = [
            sys.executable,
            str(mirror_script),
            "resolve",
            "--service",
            service,
            "--raw",
            "--vault-dir",
            str(vault_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            value = proc.stdout.strip()
            if value:
                return value, service
    return "", ""


def load_credentials(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, str]]:
    app_key = os.getenv(args.app_key_env, "").strip()
    token = os.getenv(args.token_env, "").strip()
    source = {"app_key": "", "token": ""}

    if app_key:
        source["app_key"] = f"env:{args.app_key_env}"
    if token:
        source["token"] = f"env:{args.token_env}"

    mirror_script = Path(args.key_mirror_script)
    vault_dir = Path(args.vault_dir)

    if not app_key:
        app_key, service = read_mirror_key(
            mirror_script,
            vault_dir,
            [s.strip() for s in args.mirror_service_app.split(",") if s.strip()],
        )
        if app_key:
            source["app_key"] = f"mirror:{service}"

    if not token:
        token, service = read_mirror_key(
            mirror_script,
            vault_dir,
            [s.strip() for s in args.mirror_service_token.split(",") if s.strip()],
        )
        if token:
            source["token"] = f"mirror:{service}"

    return {"app_key": app_key, "token": token}, source


def extract_identifier(record: dict[str, Any]) -> str:
    for key in ("id", "identifier", "_id", "entityid", "slug"):
        value = record.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text
    return ""


def fetch_collection(
    list_fn: Callable[..., Any],
    detail_fn: Callable[..., Any] | None,
    world_id: str,
    page_size: int,
    max_items: int,
    granularity: int,
    fetch_details: bool,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    offset = 0

    while len(items) < max_items:
        limit = min(page_size, max_items - len(items))
        try:
            batch = list(list_fn(world_id, True, limit, offset))
        except Exception as exc:  # noqa: BLE001
            errors.append({"stage": "list", "offset": offset, "error": str(exc)})
            break

        if not batch:
            break
        items.extend(batch)
        offset += len(batch)
        if len(batch) < limit:
            break

    if fetch_details and detail_fn is not None:
        for row in items:
            identifier = extract_identifier(row)
            if not identifier:
                continue
            try:
                detail = detail_fn(identifier, granularity)
                detail_rows.append(detail)
            except Exception as exc:  # noqa: BLE001
                errors.append({"stage": "detail", "id": identifier, "error": str(exc)})

    return {
        "count": len(items),
        "items": items,
        "details_count": len(detail_rows),
        "details": detail_rows,
        "errors": errors,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_world_id(client: BoromirApiClient, requested_world_id: str) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    identity = client.user.identity()
    user_id = str(identity.get("id") or identity.get("identifier") or "").strip()
    if not user_id:
        raise FailedRequest("Could not resolve user id from World Anvil identity response.")

    worlds = list(client.user.worlds(user_id))
    if requested_world_id:
        return requested_world_id, identity, worlds

    if not worlds:
        raise ResourceNotFound("No worlds found for authenticated user.")

    first_world_id = extract_identifier(worlds[0])
    if not first_world_id:
        raise FailedRequest("Could not resolve world id from first world record.")
    return first_world_id, identity, worlds


def summarize_counts(sync_payload: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for endpoint, payload in sync_payload.items():
        out[endpoint] = int(payload.get("count", 0))
    return out


def build_mock_sync_payload(endpoints: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    identity = {"id": "mock-user-1", "username": "scbe-mock", "displayName": "SCBE Mock User"}
    worlds = [{"id": "mock-world-aethermoor", "title": "Aethermoor", "slug": "aethermoor"}]
    world_meta = {
        "id": "mock-world-aethermoor",
        "title": "Aethermoor",
        "description": "Mock World Anvil world for local sync and lore RAG validation.",
    }

    seed_records = {
        "articles": [
            {
                "id": "art-kael-future",
                "title": "Kael of the Future Thread",
                "content": "A future-thread Kael appears with the Seventh Tongue to challenge canon continuity.",
                "tags": ["kael", "future", "seventh-tongue"],
                "category": "character",
            },
            {
                "id": "art-marcus-protocol",
                "title": "Marcus and the Protocol",
                "content": "Marcus stabilizes the six tongues and seats the 7th overseer as audit witness.",
                "tags": ["marcus", "protocol", "audit"],
                "category": "lore",
            },
        ],
        "categories": [
            {"id": "cat-lore", "title": "Lore Canon", "description": "Primary canon category."},
            {"id": "cat-timelines", "title": "Timeline Branches", "description": "Future/past branch records."},
        ],
        "timelines": [
            {"id": "tl-luminal", "title": "Luminal Awakening", "description": "Origin timeline anchor."},
            {"id": "tl-kael-future", "title": "Kael Future Branch", "description": "Speculative future continuity."},
        ],
        "maps": [
            {"id": "map-archives", "title": "Archive Complex", "description": "Vault chambers and protocol halls."}
        ],
        "manuscripts": [
            {"id": "ms-7th", "title": "The Seventh Tongue Codex", "content": "EL/LU oversight tongue manuscript."}
        ],
        "chronicles": [
            {"id": "chr-incursion", "title": "First Incursion Log", "content": "Kael signature propagation event log."}
        ],
        "secrets": [
            {"id": "sec-void-seed", "title": "Void Seed Containment", "content": "Containment chain specs and guard lanes."}
        ],
        "histories": [
            {"id": "hist-protocol", "title": "Protocol Formation", "content": "Distributed consensus replaced central authority."}
        ],
        "images": [{"id": "img-polypad", "title": "Polly Pad Diagram", "description": "Fleet formation reference image"}],
    }

    payload: dict[str, Any] = {}
    for endpoint in endpoints:
        rows = seed_records.get(endpoint, [])
        payload[endpoint] = {
            "count": len(rows),
            "items": rows,
            "details_count": len(rows),
            "details": rows,
            "errors": [],
        }

    return identity, worlds, world_meta, payload


def main() -> int:
    configure_stdout()
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = (
        resolve_path(repo_root, args.output_dir)
        if args.output_dir
        else repo_root / "exports" / "world_anvil" / f"live_sync_{utc_stamp()}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    creds, source = load_credentials(args)
    preflight = {
        "ok": True,
        "time": utc_now(),
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "auth_source": source,
        "has_app_key": bool(creds["app_key"]),
        "has_token": bool(creds["token"]),
    }

    if args.dry_run:
        print_json({"ok": True, "mode": "dry_run", **preflight})
        return 0

    requested = [e.strip().lower() for e in args.endpoints.split(",") if e.strip()]

    if args.mock:
        identity, worlds, world_meta, sync_payload = build_mock_sync_payload(requested)
        world_id = "mock-world-aethermoor"
        write_json(output_dir / "identity.json", identity)
        write_json(output_dir / "worlds.json", worlds)
        write_json(output_dir / f"world_{sanitize_for_filename(world_id)}_meta.json", world_meta)
        for endpoint, data in sync_payload.items():
            write_json(output_dir / f"{endpoint}_list.json", data["items"])
            write_json(output_dir / f"{endpoint}_detail.json", data["details"])
        report = {
            "ok": True,
            "mode": "mock",
            "time": utc_now(),
            "world_id": world_id,
            "output_dir": str(output_dir),
            "endpoint_counts": summarize_counts(sync_payload),
            "requested_endpoints": requested,
        }
        write_json(output_dir / "sync_report.json", report)
        print_json(report)
        return 0

    if not creds["app_key"] or not creds["token"]:
        print_json(
            {
                "ok": False,
                "error": "Missing World Anvil credentials.",
                "expected_env": [args.app_key_env, args.token_env],
                "mirror_script": args.key_mirror_script,
                "preflight": preflight,
                "hint": "Set env vars or store keys in DPAPI mirror services and rerun.",
            }
        )
        return 1

    try:
        client = BoromirApiClient(
            args.script_name,
            args.script_url,
            args.script_version,
            creds["app_key"],
            creds["token"],
        )

        world_id, identity, worlds = choose_world_id(client, args.world_id)
        if args.self_test:
            print_json(
                {
                    "ok": True,
                    "mode": "self_test",
                    "preflight": preflight,
                    "identity_keys": sorted(identity.keys()),
                    "world_count": len(worlds),
                    "selected_world_id": world_id,
                }
            )
            return 0

        world_meta = client.world.get(world_id, args.granularity)
        write_json(output_dir / "identity.json", identity)
        write_json(output_dir / "worlds.json", worlds)
        write_json(output_dir / f"world_{sanitize_for_filename(world_id)}_meta.json", world_meta)

        endpoint_map: dict[str, tuple[Callable[..., Any], Callable[..., Any] | None]] = {
            "articles": (client.world.articles, client.article.get),
            "categories": (client.world.categories, client.category.get),
            "timelines": (client.world.timelines, client.timeline.get),
            "maps": (client.world.maps, client.map.get),
            "manuscripts": (client.world.manuscripts, client.manuscript.get),
            "chronicles": (client.world.chronicles, client.chronicle.get),
            "secrets": (client.world.secrets, client.secret.get),
            "histories": (client.world.histories, client.history.get),
            "images": (client.world.images, client.image.get),
        }

        unknown = [e for e in requested if e not in endpoint_map]
        if unknown:
            print_json({"ok": False, "error": "Unknown endpoints requested", "unknown": unknown})
            return 1

        sync_payload: dict[str, Any] = {}
        for endpoint in requested:
            list_fn, detail_fn = endpoint_map[endpoint]
            data = fetch_collection(
                list_fn=list_fn,
                detail_fn=detail_fn,
                world_id=world_id,
                page_size=args.page_size,
                max_items=args.max_items_per_endpoint,
                granularity=args.granularity,
                fetch_details=not args.no_details,
            )
            sync_payload[endpoint] = data
            write_json(output_dir / f"{endpoint}_list.json", data["items"])
            if not args.no_details:
                write_json(output_dir / f"{endpoint}_detail.json", data["details"])
            if data["errors"]:
                write_json(output_dir / f"{endpoint}_errors.json", data["errors"])

        report = {
            "ok": True,
            "time": utc_now(),
            "world_id": world_id,
            "output_dir": str(output_dir),
            "endpoint_counts": summarize_counts(sync_payload),
            "detail_mode": (not args.no_details),
            "max_items_per_endpoint": args.max_items_per_endpoint,
            "granularity": args.granularity,
            "auth_source": source,
            "requested_endpoints": requested,
        }
        write_json(output_dir / "sync_report.json", report)
        print_json(report)
        return 0

    except (
        UnauthorizedRequest,
        AccessForbidden,
        ResourceNotFound,
        UnprocessableDataProvided,
        ConnectionException,
        FailedRequest,
        WorldAnvilClientException,
        WorldAnvilServerException,
    ) as exc:
        print_json({"ok": False, "error": str(exc), "type": exc.__class__.__name__, "preflight": preflight})
        return 1
    except Exception as exc:  # noqa: BLE001
        print_json({"ok": False, "error": str(exc), "type": exc.__class__.__name__, "preflight": preflight})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
