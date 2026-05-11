#!/usr/bin/env python3
"""SCBE bridge to Kaggle CLI / Python API.

Wraps the quirks documented in `reference_kaggle_cli_quirks.md`:

  - Auth env var rename: `KAGGLE_API_TOKEN` (project convention) -> `KAGGLE_KEY`
    (what the kaggle library actually reads). Bridged automatically.
  - License slugs are constrained to {all, cc, gpl, odb, other}. We
    validate before sending so callers get a clean error instead of
    a Kaggle 400.
  - Keywords must be single-word slugs from Kaggle's controlled
    vocabulary. Multi-word phrases get rejected. We strip + warn.
  - Title cap 6-50 chars, subtitle cap 20-80 chars. Validated.
  - `kaggle datasets create -p .` defaults to PRIVATE; we expose an
    `is_public` flag and forward it to `--public`.
  - For existing datasets, the Python `dataset_metadata_update` is
    the only working path to flip visibility (no CLI flag exists).

CLI:

    python scripts/kaggle/scbe_kaggle.py list
    python scripts/kaggle/scbe_kaggle.py pull <owner/slug> [<dest_dir>]
    python scripts/kaggle/scbe_kaggle.py push <folder> [--message NOTE] [--public]
    python scripts/kaggle/scbe_kaggle.py update-metadata <folder>
    python scripts/kaggle/scbe_kaggle.py info <owner/slug>

Library:

    from scripts.kaggle.scbe_kaggle import (
        KaggleBridge, validate_metadata, ensure_auth_env,
    )
    bridge = KaggleBridge()
    info = bridge.info("issacizrealdavis/scbe-dense-bundle-sft-v1")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

VALID_LICENSE_SLUGS: tuple[str, ...] = ("all", "cc", "gpl", "odb", "other")
TITLE_MIN, TITLE_MAX = 6, 50
SUBTITLE_MIN, SUBTITLE_MAX = 20, 80
SCBE_KAGGLE_USERNAME_ENV = "KAGGLE_USERNAME"
SCBE_KAGGLE_TOKEN_ENV = "KAGGLE_API_TOKEN"
KAGGLE_KEY_ENV = "KAGGLE_KEY"


@dataclass
class MetadataValidation:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def ensure_auth_env() -> None:
    """Bridge the project's `KAGGLE_API_TOKEN` to the lib's `KAGGLE_KEY`.

    Idempotent. If `KAGGLE_KEY` is already set, leave it alone. If
    `KAGGLE_API_TOKEN` exists but `KAGGLE_KEY` doesn't, copy across.
    Raises `RuntimeError` if neither is set so the caller fails loud.
    """
    if os.environ.get(KAGGLE_KEY_ENV):
        return
    fallback = os.environ.get(SCBE_KAGGLE_TOKEN_ENV)
    if fallback:
        os.environ[KAGGLE_KEY_ENV] = fallback
        return
    raise RuntimeError(
        "Kaggle auth missing. Set KAGGLE_KEY (or KAGGLE_API_TOKEN, "
        "which we'll alias). KAGGLE_USERNAME also required."
    )


def validate_metadata(meta: dict) -> MetadataValidation:
    """Validate a dataset-metadata.json dict before we ship it."""
    errors: list[str] = []
    warnings: list[str] = []

    title = meta.get("title", "")
    if not isinstance(title, str) or not (TITLE_MIN <= len(title) <= TITLE_MAX):
        errors.append(f"title must be {TITLE_MIN}-{TITLE_MAX} chars (got {len(title)})")

    subtitle = meta.get("subtitle", "")
    if subtitle and not (SUBTITLE_MIN <= len(subtitle) <= SUBTITLE_MAX):
        errors.append(f"subtitle must be {SUBTITLE_MIN}-{SUBTITLE_MAX} chars (got {len(subtitle)})")

    licenses = meta.get("licenses") or []
    if not isinstance(licenses, list) or len(licenses) != 1:
        errors.append("licenses must be an array with exactly one entry")
    else:
        lic_name = (licenses[0] or {}).get("name") if isinstance(licenses[0], dict) else None
        if lic_name not in VALID_LICENSE_SLUGS:
            errors.append(f"license name {lic_name!r} is not in valid set {VALID_LICENSE_SLUGS}")

    keywords = meta.get("keywords") or []
    if isinstance(keywords, list):
        for kw in keywords:
            if not isinstance(kw, str):
                errors.append(f"keyword {kw!r} must be a string")
                continue
            if " " in kw or "_" in kw:
                warnings.append(
                    f"keyword {kw!r} contains spaces/underscores — Kaggle will likely reject; "
                    "prefer single-word slugs (e.g. 'chemistry', 'education')"
                )

    if "id" not in meta or not isinstance(meta["id"], str) or "/" not in meta["id"]:
        errors.append("id must be 'owner/slug'")

    return MetadataValidation(ok=not errors, errors=errors, warnings=warnings)


def filter_invalid_keywords(keywords: Iterable[str]) -> tuple[list[str], list[str]]:
    """Return (kept, dropped). Drops anything with whitespace/underscores."""
    kept: list[str] = []
    dropped: list[str] = []
    for kw in keywords:
        if not isinstance(kw, str):
            dropped.append(str(kw))
            continue
        if " " in kw or "_" in kw or "\t" in kw:
            dropped.append(kw)
        else:
            kept.append(kw)
    return kept, dropped


@dataclass
class KaggleBridge:
    """Thin wrapper over the Python KaggleApi.

    Lazy-imports `kaggle` so the module is importable in environments
    where the lib isn't installed (tests can stub things out).
    """

    _api: object | None = None

    def _get_api(self):
        if self._api is not None:
            return self._api
        ensure_auth_env()
        from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402

        api = KaggleApi()
        api.authenticate()
        self._api = api
        return api

    def list_my_datasets(self, limit: int = 50) -> list[dict]:
        api = self._get_api()
        # The CLI surface returns Dataset objects; convert to dicts.
        raw = api.dataset_list(mine=True, page_size=limit)
        out: list[dict] = []
        for ds in raw[:limit]:
            out.append(
                {
                    "ref": getattr(ds, "ref", str(ds)),
                    "title": getattr(ds, "title", ""),
                    "size": getattr(ds, "totalBytes", 0),
                    "last_updated": str(getattr(ds, "lastUpdated", "")),
                    "is_private": bool(getattr(ds, "isPrivate", False)),
                }
            )
        return out

    def info(self, ref: str) -> dict:
        """Pull the dataset's `dataset-metadata.json` and return it as a dict.

        `KaggleApi` doesn't expose a direct "view" method; the working
        path is `dataset_metadata(ref, path)` which writes the metadata
        file to disk. We tee it to a tempdir, parse, return.
        """
        import tempfile

        api = self._get_api()
        with tempfile.TemporaryDirectory() as tmp:
            api.dataset_metadata(ref, tmp)
            meta_path = Path(tmp) / "dataset-metadata.json"
            if not meta_path.exists():
                # Some kaggle versions write the older filename.
                alt = Path(tmp) / "datapackage.json"
                meta_path = alt if alt.exists() else meta_path
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        return {
            "ref": data.get("id", ref),
            "title": data.get("title", ""),
            "subtitle": data.get("subtitle", ""),
            "license": (data.get("licenses") or [{}])[0].get("name", ""),
            "keywords": data.get("keywords", []),
            "is_private": bool(data.get("isPrivate", False)),
        }

    def pull(self, ref: str, dest: Path, force: bool = False, unzip: bool = True) -> Path:
        api = self._get_api()
        owner, slug = ref.split("/", 1)
        dest.mkdir(parents=True, exist_ok=True)
        api.dataset_download_files(f"{owner}/{slug}", path=str(dest), force=force, unzip=unzip)
        return dest

    def push_create(self, folder: Path, is_public: bool = False) -> str:
        """Create a NEW dataset from `folder` (must contain dataset-metadata.json)."""
        meta_path = folder / "dataset-metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"missing {meta_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        validation = validate_metadata(meta)
        if not validation.ok:
            raise ValueError("metadata invalid: " + "; ".join(validation.errors))

        # Drop bad keywords on the way in so Kaggle doesn't reject the whole upload.
        kept, dropped = filter_invalid_keywords(meta.get("keywords") or [])
        if dropped:
            print(f"[scbe-kaggle] dropping invalid keywords: {dropped}", file=sys.stderr)
            meta["keywords"] = kept
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        api = self._get_api()
        api.dataset_create_new(
            folder=str(folder),
            public=is_public,
            quiet=False,
            convert_to_csv=False,
            dir_mode="zip",
        )
        return meta["id"]

    def push_version(self, folder: Path, message: str, delete_old: bool = False) -> str:
        meta_path = folder / "dataset-metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        api = self._get_api()
        api.dataset_create_version(
            folder=str(folder),
            version_notes=message,
            quiet=False,
            convert_to_csv=False,
            delete_old_versions=delete_old,
            dir_mode="zip",
        )
        return meta["id"]

    def update_metadata(self, folder: Path) -> str:
        """Update metadata-only on an existing dataset (also flips visibility)."""
        meta_path = folder / "dataset-metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        api = self._get_api()
        api.dataset_metadata_update(meta["id"], str(folder))
        return meta["id"]


SCBE_KAGGLE_CONTEXT_SLUGS_ENV = "SCBE_KAGGLE_CONTEXT_SLUGS"


def format_kaggle_context_hint(bridge: "KaggleBridge | None" = None) -> str:
    """Build a hint block listing Kaggle datasets the bus should treat as context.

    Reads `SCBE_KAGGLE_CONTEXT_SLUGS` env var (comma-separated owner/slug
    list). For each slug, fetches the metadata stub and returns a
    multi-line block suitable for inclusion in a swarm-bus lane prompt.

    Returns "" when the env var is unset OR when fetching fails — the
    bus must work without Kaggle, so this is a zero-cost noop in the
    common case.
    """
    raw = os.environ.get(SCBE_KAGGLE_CONTEXT_SLUGS_ENV, "").strip()
    if not raw:
        return ""
    slugs = [s.strip() for s in raw.split(",") if s.strip()]
    if not slugs:
        return ""
    if bridge is None:
        # If auth isn't present at all, skip silently — the bus must work
        # without Kaggle. A partial-failure-per-slug path runs only when
        # auth IS present but a specific dataset is unreachable.
        try:
            ensure_auth_env()
        except RuntimeError:
            return ""
        try:
            bridge = KaggleBridge()
        except RuntimeError:
            return ""
    lines = ["Kaggle context datasets (pull with `npm run kaggle:pull <ref>`):"]
    for slug in slugs:
        try:
            info = bridge.info(slug)
        except Exception as err:  # noqa: BLE001 — best-effort
            lines.append(f"- {slug} (fetch failed: {err})")
            continue
        title = info.get("title") or info.get("ref", slug)
        license_name = info.get("license", "?")
        is_private = info.get("is_private", False)
        visibility = "private" if is_private else "public"
        lines.append(f"- {slug} — {title} (license={license_name}, {visibility})")
    return "\n".join(lines)


def _cmd_list(args: argparse.Namespace) -> int:
    bridge = KaggleBridge()
    rows = bridge.list_my_datasets(limit=args.limit)
    print(json.dumps(rows, indent=2))
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    bridge = KaggleBridge()
    print(json.dumps(bridge.info(args.ref), indent=2))
    return 0


def _cmd_pull(args: argparse.Namespace) -> int:
    bridge = KaggleBridge()
    dest = Path(args.dest) if args.dest else Path("./") / args.ref.split("/")[-1]
    out = bridge.pull(args.ref, dest, force=args.force, unzip=not args.no_unzip)
    print(f"[ok] pulled {args.ref} -> {out}")
    return 0


def _cmd_push(args: argparse.Namespace) -> int:
    bridge = KaggleBridge()
    folder = Path(args.folder)
    if args.new:
        ref = bridge.push_create(folder, is_public=args.public)
        print(f"[ok] created {ref} (public={args.public})")
    else:
        ref = bridge.push_version(folder, message=args.message, delete_old=args.delete_old)
        print(f"[ok] new version of {ref}: {args.message}")
    return 0


def _cmd_update_metadata(args: argparse.Namespace) -> int:
    bridge = KaggleBridge()
    ref = bridge.update_metadata(Path(args.folder))
    print(f"[ok] metadata updated for {ref}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCBE Kaggle bridge.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List my datasets")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=_cmd_list)

    p_info = sub.add_parser("info", help="Inspect a dataset by ref")
    p_info.add_argument("ref", help="owner/slug")
    p_info.set_defaults(func=_cmd_info)

    p_pull = sub.add_parser("pull", help="Download a dataset")
    p_pull.add_argument("ref", help="owner/slug")
    p_pull.add_argument("dest", nargs="?", default=None)
    p_pull.add_argument("--force", action="store_true")
    p_pull.add_argument("--no-unzip", action="store_true")
    p_pull.set_defaults(func=_cmd_pull)

    p_push = sub.add_parser("push", help="Upload a folder as new dataset or new version")
    p_push.add_argument("folder", help="Folder containing dataset-metadata.json")
    p_push.add_argument("--new", action="store_true", help="Create a new dataset (default: new version)")
    p_push.add_argument("--public", action="store_true", help="Public on create (only with --new)")
    p_push.add_argument("--message", "-m", default="version bump", help="Version notes (only without --new)")
    p_push.add_argument("--delete-old", action="store_true")
    p_push.set_defaults(func=_cmd_push)

    p_meta = sub.add_parser("update-metadata", help="Push metadata-only update")
    p_meta.add_argument("folder")
    p_meta.set_defaults(func=_cmd_update_metadata)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except RuntimeError as err:
        print(f"[error] {err}", file=sys.stderr)
        return 2
    except FileNotFoundError as err:
        print(f"[error] {err}", file=sys.stderr)
        return 2
    except ValueError as err:
        print(f"[error] {err}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
