#!/usr/bin/env python3
"""Build a consolidated notes dossier from Obsidian + repo notes and ship it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN_ROOT = "training/runs/notes_dossier"
DEFAULT_MAPROOM_NOTE = "docs/map-room/notes_dossier_reference.md"
DEFAULT_REPO_NOTES = ["docs/**/*.md", "training/**/*.md", "notes/**/*.md", "docs/map-room/**/*.md"]
DEFAULT_IGNORE_DIRS = {".git", ".venv", "node_modules", ".ruff_cache", ".mypy_cache", ".pytest_cache", "artifacts", ".obsidian"}
DEFAULT_DROPBOX_HISTORY = 30


@dataclass(frozen=True)
class Vault:
    key: str
    path: Path
    open: bool



def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def resolve_obsidian_config() -> list[Vault]:
    appdata = os.getenv("APPDATA", "")
    if not appdata:
        raise RuntimeError("APPDATA is not available on this machine.")

    cfg = Path(appdata) / "Obsidian" / "obsidian.json"
    if not cfg.exists():
        raise RuntimeError(f"Obsidian config missing: {cfg}")

    payload = json.loads(cfg.read_text(encoding="utf-8"))
    vaults = payload.get("vaults", {})
    if not isinstance(vaults, dict):
        raise RuntimeError("Malformed Obsidian config: expected vaults map.")

    found: list[Vault] = []
    for key, raw in vaults.items():
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("path", "")).strip()
        p = Path(path)
        if path and p.exists():
            found.append(Vault(key=key, path=p, open=bool(raw.get("open", False))))

    if not found:
        raise RuntimeError("No usable Obsidian vault found in config.")
    return found


def discover_vaults(explicit: str = "") -> list[Vault]:
    if explicit.strip():
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Vault not found: {p}")
        return [Vault(key=p.name, path=p, open=True)]
    return resolve_obsidian_config()


def sanitize_slug(value: str, fallback: str = "item") -> str:
    value = re.sub(r"[^A-Za-z0-9._-]", "-", value, flags=re.ASCII)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or fallback


def extract_title(text: str, fallback: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            if line.lower().startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"\'')
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def should_skip(path: Path, root: Path, ignored: Iterable[str]) -> bool:
    rel = path.relative_to(root).parts
    ignore = set(ignored)
    for part in rel[:-1]:
        if part in ignore:
            return True
        if part.startswith(".") and part not in {".."}:
            if part in {".obsidian", ".trash"}:
                return True
    return False


def iter_markdown_files(root: Path, patterns: Sequence[str], ignored: Sequence[str], max_bytes: int | None = None) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        for p in root.glob(pattern):
            if not p.is_file() or p.suffix.lower() != ".md":
                continue
            if should_skip(p, root, ignored):
                continue
            if max_bytes and p.stat().st_size > max_bytes:
                continue
            files.add(p)
    return sorted(files, key=lambda x: str(x).lower())


def normalize_notion_id(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    m = re.search(r"([0-9a-fA-F]{32})", value)
    if m:
        return m.group(1)
    return re.sub(r"[^0-9a-fA-F]", "", value).lower()


def notion_request(url: str, token: str, payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {exc.code}: {detail}") from exc


def notion_rich(text: str) -> dict[str, Any]:
    return {"type": "text", "text": {"content": text[:2000]}}


def notion_paragraph(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "paragraph": {"rich_text": [notion_rich(text)]}}


def notion_heading(text: str, level: int = 3) -> dict[str, Any]:
    key = f"heading_{min(3, max(level, 1))}"
    return {"type": key, key: {"rich_text": [notion_rich(text)]}}


def notion_append_blocks(token: str, page_id: str, blocks: list[dict[str, Any]], batch: int = 95) -> None:
    for i in range(0, len(blocks), batch):
        part = blocks[i : i + batch]
        notion_request(f"https://api.notion.com/v1/blocks/{page_id}/children", token, {"children": part})


def detect_dropbox_sync_dir(explicit: str = "") -> Path | None:
    if explicit.strip():
        p = Path(explicit).expanduser()
        if p.exists():
            return p

    env_path = os.getenv("DROPBOX_SYNC_DIR", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    home = Path.home()
    for candidate in [home / "Dropbox", home / "Dropbox (Personal)", home / "Dropbox (Business)"]:
        if candidate.exists():
            return candidate
    for p in home.glob("Dropbox*"):
        if p.is_dir():
            return p
    return None


def copy_to_cloud_root(run_id: str, run_root: Path, archive: Path, base_root: Path) -> dict[str, Any]:
    target = base_root / "SCBE" / "notes-dossier" / run_id
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    nested_run = target / run_root.name
    if nested_run.exists():
        shutil.rmtree(nested_run)
    shutil.copytree(run_root, nested_run)
    copied.append(str(nested_run))

    shutil.copy2(archive, target / archive.name)
    copied.append(str(target / archive.name))

    return {
        "status": "ok",
        "root": str(base_root),
        "target": str(target),
        "copied": copied,
    }


def copy_to_cloud_root_organized(
    run_id: str,
    run_root: Path,
    archive: Path,
    base_root: Path,
    history_limit: int = DEFAULT_DROPBOX_HISTORY,
) -> dict[str, Any]:
    root = base_root / "SCBE" / "notes-dossier"
    runs_root = root / "runs"
    archives_root = root / "archives"
    manifest_path = root / "index.json"
    latest_txt = root / "LATEST.txt"
    latest_json = root / "LATEST.json"

    runs_root.mkdir(parents=True, exist_ok=True)
    archives_root.mkdir(parents=True, exist_ok=True)

    organized_run = runs_root / run_id
    if organized_run.exists():
        shutil.rmtree(organized_run)
    shutil.copytree(run_root, organized_run)

    shutil.copy2(archive, archives_root / archive.name)

    # Keep a simple machine-readable index that makes the Dropbox namespace easy to browse.
    record = {
        "run_id": run_id,
        "timestamp_utc": utc_now().isoformat(),
        "run_root": f"runs/{run_id}",
        "archive": f"archives/{archive.name}",
        "manifest": f"runs/{run_id}/manifest.json",
    }

    entries: list[dict[str, Any]] = []
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                entries = payload
        except Exception:
            entries = []

    entries = [item for item in entries if str(item.get("run_id", "")).strip()]
    entries.append(record)
    entries_sorted = sorted(entries, key=lambda item: str(item.get("run_id", "")), reverse=True)

    if history_limit > 0:
        keep = entries_sorted[:history_limit]
    else:
        keep = entries_sorted
    entries_map: list[dict[str, Any]] = keep
    manifest_path.write_text(json.dumps(entries_map, indent=2, ensure_ascii=False), encoding="utf-8")

    latest_payload = {
        "run_id": run_id,
        "timestamp_utc": record["timestamp_utc"],
        "run_root": str(organized_run),
        "archive": str(archives_root / archive.name),
        "manifest": str(organized_run / "manifest.json"),
        "total_runs": len(entries_map),
    }
    latest_txt.write_text(run_id + "\n", encoding="utf-8")
    latest_json.write_text(json.dumps(latest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Optional README for human discoverability.
    readme = [
        "# SCBE Notes Dossier (Dropbox)",
        "",
        f"Run: {run_id}",
        f"Generated UTC: {record['timestamp_utc']}",
        "",
        "## Layout",
        "- `runs/<run_id>/` — full dossier bundle",
        "- `archives/` — zip snapshots",
        "- `index.json` — latest runs index",
        "- `LATEST.txt` — current run id",
        "- `LATEST.json` — machine-readable latest payload",
        "",
        "## Latest run",
        f"- Manifest: `runs/{run_id}/manifest.json`",
        f"- Inventory: `runs/{run_id}/inventory.md`",
        f"- Compendium: `runs/{run_id}/dossier_compendium.md`",
    ]
    (root / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    return {
        "status": "ok",
        "root": str(base_root),
        "target": str(root),
        "run_target": str(organized_run),
        "archive_target": str(archives_root / archive.name),
        "index": str(manifest_path),
    }


def push_to_hf(bundle_root: Path, run_id: str, repo_id: str, token: str, repo_type: str, dry_run: bool) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc

    if dry_run:
        return {"status": "dry-run", "repo": repo_id, "target": f"notes-dossier/{run_id}"}

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type=repo_type, private=True, exist_ok=True)
    api.upload_folder(
        folder_path=str(bundle_root),
        path_in_repo=f"notes-dossier/{run_id}",
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=f"notes dossier {run_id}",
    )
    return {"status": "ok", "repo": repo_id, "target": f"notes-dossier/{run_id}"}


def publish_to_notion(
    token: str,
    parent_page_id: str,
    title: str,
    run_id: str,
    manifest: list[dict[str, Any]],
    archive_name: str,
    include_body: bool,
    max_notes: int,
    max_chars_per_note: int,
    note_text_by_dest: dict[str, str],
) -> dict[str, Any]:
    parent = normalize_notion_id(parent_page_id)
    if len(parent) != 32:
        raise ValueError("Notion parent id not valid; provide 32-char id or full Notion URL with id.")

    intro = [
        "## SCBE Notes Dossier",
        f"run_id: {run_id}",
        f"total_notes: {len(manifest)}",
        f"archive: {archive_name}",
    ]
    create_payload = {
        "parent": {"page_id": parent},
        "properties": {
            "title": {
                "title": [
                    {"text": {"content": title}},
                ]
            }
        },
        "children": [
            notion_paragraph("\n".join(intro)),
        ],
    }
    created = notion_request("https://api.notion.com/v1/pages", token, create_payload)
    page_id = created.get("id", "")
    if not page_id:
        raise RuntimeError("Notion did not return a created page id.")

    if include_body and manifest:
        blocks: list[dict[str, Any]] = []
        for i, row in enumerate(manifest[:max_notes]):
            blocks.append(notion_heading(f"{i + 1:04d}. {row['source_kind']}: {row['destination_path']}", 3))
            blocks.append(
                notion_paragraph(f"title: {row['title']}\nsource: {row['source_path']}")
            )
            text = note_text_by_dest.get(row["destination_path"], "")
            chunks = [text[i : i + 1500] for i in range(0, min(len(text), max_chars_per_note), 1500)]
            for chunk in chunks:
                if chunk:
                    blocks.append(notion_paragraph(chunk))
        if blocks:
            notion_append_blocks(token, page_id, blocks)

    return {
        "status": "ok",
        "page_id": page_id,
        "target": f"notion://{page_id}",
        "included_notes": min(len(manifest), max_notes) if include_body else 0,
    }


def build_inventory(mark: list[dict[str, Any]]) -> str:
    lines = ["# SCBE Notes Dossier", "", f"Generated: {utc_now().isoformat()}", f"Total notes: {len(mark)}", "", "## Inventory"]
    for row in mark:
        lines.append(f"- [{row['source_kind']}/{row['source_label']}] {row['destination_path']}")
        lines.append(f"  - title: {row['title']}")
        lines.append(f"  - chars: {row['char_count']} | lines: {row['line_count']}")
    return "\n".join(lines) + "\n"


def build_compendium(mark: list[dict[str, Any]], note_text_by_dest: dict[str, str]) -> str:
    lines = ["# SCBE Notes Dossier", "", f"Generated: {utc_now().isoformat()}", f"Total notes: {len(mark)}", ""]
    for row in mark:
        lines.append(f"## {row['destination_path']}")
        lines.append(f"**title:** {row['title']}")
        lines.append(f"**source:** {row['source_path']}")
        lines.append("")
        lines.append(note_text_by_dest.get(row["destination_path"], ""))
        lines.append("\n----\n")
    return "\n".join(lines)


def write_maproom_reference(note_path: Path, run_id: str, run_root: Path, shipping: dict[str, Any]) -> None:
    note_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Notes Dossier Run {run_id}",
        "",
        f"Generated: {utc_now().isoformat()}",
        f"Run directory: `{run_root}`",
        "",
        "## Shipping status",
        json.dumps(shipping, indent=2),
        "",
        "## How AI systems can discover this",
        "The canonical dossier bundle is always written to:",
        f"- `notes_dossier/{run_id}`",
        "",
        "This file is here for follow-up agents to discover all prior dossier runs quickly.",
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and ship all notes into one dossier.")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--vault", default="", help="Explicit Obsidian vault path (defaults to all discovered)")
    parser.add_argument("--vault-include", default="", help="Comma-separated obsidian vault keys to include")
    parser.add_argument("--repo-glob", action="append", default=[], help="Extra repo markdown globs")
    parser.add_argument("--max-note-bytes", type=int, default=2_000_000)
    parser.add_argument("--no-obsidian", action="store_true")
    parser.add_argument("--no-repo", action="store_true")
    parser.add_argument("--dropbox", action="store_true")
    parser.add_argument("--dropbox-dir", default="")
    parser.add_argument(
        "--dropbox-organized",
        action="store_true",
        help="Copy into a structured notes-dossier layout with runs + archive index",
    )
    parser.add_argument(
        "--dropbox-flat",
        action="store_false",
        dest="dropbox_organized",
        help="Disable structured notes-dossier layout and use legacy flat package folder.",
    )
    parser.add_argument("--dropbox-history", type=int, default=DEFAULT_DROPBOX_HISTORY, help="Number of recent runs to keep in dropbox index")
    parser.add_argument("--hf-repo", default="")
    parser.add_argument("--hf-repo-type", default="dataset", choices=["dataset", "model", "space"])
    parser.add_argument("--notion-parent-page-id", default="")
    parser.add_argument("--notion-title", default="")
    parser.add_argument("--notion-max-notes", type=int, default=25)
    parser.add_argument("--notion-max-chars-per-note", type=int, default=4000)
    parser.add_argument("--notion-exclude-body", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--maproom-note", default=str(REPO_ROOT / DEFAULT_MAPROOM_NOTE))
    parser.set_defaults(dropbox_organized=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or utc_now().strftime("%Y%m%dT%H%M%SZ")
    run_root = REPO_ROOT / args.run_root / run_id
    notes_root = run_root / "notes"
    run_root.mkdir(parents=True, exist_ok=True)

    vault_names = {v.strip() for v in args.vault_include.split(",") if v.strip()}

    manifest: list[dict[str, Any]] = []
    note_text_by_dest: dict[str, str] = {}

    if not args.no_obsidian:
        vaults = discover_vaults(args.vault)
        for vault in vaults:
            if vault_names and vault.key not in vault_names and vault.path.name not in vault_names:
                continue
            label = sanitize_slug(vault.key, fallback=vault.path.name)
            source_tag = f"obsidian/{label}"
            for src in iter_markdown_files(vault.path, ["**/*.md"], DEFAULT_IGNORE_DIRS, max_bytes=args.max_note_bytes):
                text = src.read_text(encoding="utf-8", errors="replace")
                rel = src.relative_to(vault.path).as_posix()
                dst = notes_root / source_tag / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(text, encoding="utf-8")

                row = {
                    "source_kind": "obsidian",
                    "source_label": label,
                    "source_path": str(src),
                    "destination_path": str((Path("notes") / source_tag / rel).as_posix()),
                    "title": extract_title(text, fallback=src.stem or "note"),
                    "sha256": sha256_file(src),
                    "line_count": len(text.splitlines()),
                    "char_count": len(text),
                    "updated_utc": datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).isoformat(),
                }
                manifest.append(row)
                note_text_by_dest[row["destination_path"]] = text

    if not args.no_repo:
        patterns = list(DEFAULT_REPO_NOTES) + list(args.repo_glob)
        for src in iter_markdown_files(REPO_ROOT, patterns, DEFAULT_IGNORE_DIRS, max_bytes=args.max_note_bytes):
            text = src.read_text(encoding="utf-8", errors="replace")
            rel = src.relative_to(REPO_ROOT)
            dst = notes_root / "repo" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")

            row = {
                "source_kind": "repo",
                "source_label": "repo",
                "source_path": str(src),
                "destination_path": str((Path("notes") / "repo" / rel).as_posix()),
                "title": extract_title(text, fallback=src.stem or "note"),
                "sha256": sha256_file(src),
                "line_count": len(text.splitlines()),
                "char_count": len(text),
                "updated_utc": datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
            manifest.append(row)
            note_text_by_dest[row["destination_path"]] = text

    manifest_path = run_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    inventory_path = run_root / "inventory.md"
    inventory_path.write_text(build_inventory(manifest), encoding="utf-8")

    compendium_path = run_root / "dossier_compendium.md"
    compendium_path.write_text(build_compendium(manifest, note_text_by_dest), encoding="utf-8")

    archive_path = run_root.parent / f"{run_id}.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(run_root.rglob("*")):
            if file.is_file():
                zf.write(file, arcname=str(file.relative_to(run_root)))

    shipping: dict[str, Any] = {"dropbox": {"status": "skipped"}, "huggingface": {"status": "skipped"}, "notion": {"status": "skipped"}}

    if args.dropbox:
        root = detect_dropbox_sync_dir(args.dropbox_dir)
        if root is None:
            shipping["dropbox"] = {"status": "failed", "error": "Dropbox sync directory not found"}
        else:
            if args.dry_run:
                shipping["dropbox"] = {"status": "dry-run", "root": str(root)}
            else:
                if args.dropbox_organized:
                    shipping["dropbox"] = copy_to_cloud_root_organized(
                        run_id=run_id,
                        run_root=run_root,
                        archive=archive_path,
                        base_root=root,
                        history_limit=args.dropbox_history,
                    )
                else:
                    shipping["dropbox"] = copy_to_cloud_root(run_id, run_root, archive_path, root)

    if args.hf_repo:
        hf_token = os.getenv("HF_TOKEN", "").strip()
        if not hf_token:
            shipping["huggingface"] = {"status": "failed", "error": "HF_TOKEN not set"}
        else:
            try:
                shipping["huggingface"] = push_to_hf(run_root, run_id, args.hf_repo.strip(), hf_token, args.hf_repo_type, args.dry_run)
            except Exception as exc:  # noqa: BLE001
                shipping["huggingface"] = {"status": "failed", "error": str(exc)}

    if args.notion_parent_page_id:
        notion_token = (os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_MCP_TOKEN") or "").strip()
        if not notion_token:
            shipping["notion"] = {"status": "failed", "error": "NOTION_TOKEN or NOTION_API_KEY is not set"}
        else:
            try:
                include_body = not args.notion_exclude_body
                shipping["notion"] = publish_to_notion(
                    token=notion_token,
                    parent_page_id=args.notion_parent_page_id,
                    title=args.notion_title.strip() or f"SCBE Notes Dossier {run_id}",
                    run_id=run_id,
                    manifest=manifest,
                    archive_name=archive_path.name,
                    include_body=include_body,
                    max_notes=args.notion_max_notes,
                    max_chars_per_note=args.notion_max_chars_per_note,
                    note_text_by_dest=note_text_by_dest,
                )
            except Exception as exc:  # noqa: BLE001
                shipping["notion"] = {"status": "failed", "error": str(exc)}

    run_summary = {
        "run_id": run_id,
        "timestamp_utc": utc_now().isoformat(),
        "total_notes": len(manifest),
        "run_root": str(run_root),
        "manifest_path": str(manifest_path),
        "inventory_path": str(inventory_path),
        "compendium_path": str(compendium_path),
        "archive_path": str(archive_path),
        "shipping": shipping,
    }
    (run_root / "run_bundle.json").write_text(json.dumps(run_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    maproom_path = Path(args.maproom_note)
    write_maproom_reference(maproom_path, run_id, run_root, shipping)

    print(json.dumps({"status": "ok", "run_id": run_id, "run_root": str(run_root), "total_notes": len(manifest), "shipping": shipping}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
