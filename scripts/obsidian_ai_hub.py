#!/usr/bin/env python3
"""
Obsidian AI Workspace utility.

Features:
- Discover configured Obsidian vaults.
- Initialize an "AI Workspace" folder structure.
- Post task notes into the workspace.
- Read latest context/session notes for cross-agent handoff.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass
class VaultInfo:
    key: str
    path: str
    open: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _obsidian_config_path() -> Path:
    appdata = os.getenv("APPDATA", "")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot locate Obsidian config.")
    return Path(appdata) / "Obsidian" / "obsidian.json"


def discover_vaults() -> List[VaultInfo]:
    cfg = _obsidian_config_path()
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Obsidian config JSON: {cfg}") from exc

    vaults = data.get("vaults", {})
    if not isinstance(vaults, dict):
        return []

    out: List[VaultInfo] = []
    for key, meta in vaults.items():
        if not isinstance(meta, dict):
            continue
        path = str(meta.get("path", "")).strip()
        if not path:
            continue
        out.append(
            VaultInfo(
                key=str(key),
                path=path,
                open=bool(meta.get("open", False)),
            )
        )
    return out


def resolve_vault_path(explicit_path: str = "") -> Path:
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"Vault path does not exist: {p}")
        return p

    vaults = discover_vaults()
    if not vaults:
        raise RuntimeError("No Obsidian vaults discovered. Set --vault explicitly.")

    opened = [v for v in vaults if v.open]
    selected = opened[0] if opened else vaults[0]
    p = Path(selected.path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Discovered vault path does not exist: {p}")
    return p


def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text)
    return text[:80].strip("-") or "task"


def workspace_root(vault_path: Path) -> Path:
    return vault_path / "AI Workspace"


def init_workspace(vault_path: Path) -> List[Path]:
    root = workspace_root(vault_path)
    dirs = [
        root,
        root / "Tasks",
        root / "Context",
        root / "Sessions",
        root / "Inbox",
        root / "Artifacts",
    ]
    created: List[Path] = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    "# AI Workspace",
                    "",
                    "Cross-agent collaboration workspace for task handoff and shared context.",
                    "",
                    "## Folders",
                    "- `Tasks`: task tickets and execution notes",
                    "- `Context`: short shared context notes",
                    "- `Sessions`: per-session handoff/context files",
                    "- `Inbox`: incoming raw prompts and ideas",
                    "- `Artifacts`: generated outputs and evidence",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        created.append(readme)

    return created


def post_task(
    vault_path: Path,
    title: str,
    body: str,
    owner: str = "unassigned",
    priority: str = "P2",
    status: str = "todo",
    tags: Sequence[str] = (),
) -> Path:
    init_workspace(vault_path)
    tasks_dir = workspace_root(vault_path) / "Tasks"
    ts = _utc_now().strftime("%Y%m%d-%H%M%S")
    safe = _slug(title)
    target = tasks_dir / f"{ts}-{safe}.md"

    fm_tags = [t.strip() for t in tags if t.strip()]
    lines = [
        "---",
        f"title: {title}",
        f"owner: {owner}",
        f"priority: {priority}",
        f"status: {status}",
        f"created_utc: {_utc_now().isoformat()}",
        f"tags: [{', '.join(fm_tags)}]",
        "---",
        "",
        f"# {title}",
        "",
        "## Task",
        body.strip() or "(empty)",
        "",
        "## Notes",
        "-",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def post_context(vault_path: Path, title: str, body: str, folder: str = "Sessions") -> Path:
    init_workspace(vault_path)
    target_dir = workspace_root(vault_path) / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    ts = _utc_now().strftime("%Y%m%d-%H%M%S")
    safe = _slug(title)
    target = target_dir / f"{ts}-{safe}.md"
    payload = "\n".join(
        [
            f"# {title}",
            "",
            f"- created_utc: {_utc_now().isoformat()}",
            "",
            body.strip() or "(empty)",
            "",
        ]
    )
    target.write_text(payload, encoding="utf-8")
    return target


def _iter_context_files(vault_path: Path, include_folders: Sequence[str]) -> Iterable[Path]:
    root = workspace_root(vault_path)
    for folder in include_folders:
        d = root / folder
        if d.exists():
            yield from d.rglob("*.md")


def read_context(
    vault_path: Path,
    session_query: str = "",
    include_folders: Sequence[str] = ("Sessions", "Context"),
    latest: bool = True,
    max_chars: int = 6000,
) -> Dict[str, str]:
    files = [p for p in _iter_context_files(vault_path, include_folders)]
    if not files:
        raise FileNotFoundError("No context/session markdown files found in AI Workspace.")

    if session_query:
        sq = session_query.lower()
        files = [p for p in files if sq in p.stem.lower() or sq in str(p).lower()]
        if not files:
            raise FileNotFoundError(f"No context file matched query: {session_query}")

    chosen = max(files, key=lambda p: p.stat().st_mtime) if latest else sorted(files)[0]
    content = chosen.read_text(encoding="utf-8", errors="replace")
    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars] + "\n\n...[truncated]..."

    return {"path": str(chosen), "content": content}


def verify_workspace(vault_path: Path) -> Dict[str, object]:
    root = workspace_root(vault_path)
    expected = ["Tasks", "Context", "Sessions", "Inbox", "Artifacts"]
    status = {name: (root / name).exists() for name in expected}
    tasks_count = len(list((root / "Tasks").glob("*.md"))) if (root / "Tasks").exists() else 0
    return {"workspace": str(root), "exists": root.exists(), "folders": status, "tasks_count": tasks_count}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Obsidian AI Workspace helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-vaults", help="List vaults from Obsidian config")
    p_list.add_argument("--json", action="store_true", help="Emit JSON output")

    p_init = sub.add_parser("init-workspace", help="Create AI Workspace folder structure")
    p_init.add_argument("--vault", default="", help="Vault path (default: auto-detect open vault)")

    p_verify = sub.add_parser("verify-workspace", help="Check AI Workspace structure")
    p_verify.add_argument("--vault", default="", help="Vault path (default: auto-detect open vault)")

    p_post = sub.add_parser("post-task", help="Create a task note in AI Workspace/Tasks")
    p_post.add_argument("--vault", default="", help="Vault path (default: auto-detect open vault)")
    p_post.add_argument("--title", required=True, help="Task title")
    p_post.add_argument("--body", default="", help="Task body markdown")
    p_post.add_argument("--owner", default="unassigned", help="Task owner")
    p_post.add_argument("--priority", default="P2", help="Priority label")
    p_post.add_argument("--status", default="todo", help="Task status")
    p_post.add_argument("--tags", default="", help="Comma-separated tags")

    p_ctx = sub.add_parser("post-context", help="Write a context/session note")
    p_ctx.add_argument("--vault", default="", help="Vault path (default: auto-detect open vault)")
    p_ctx.add_argument("--title", required=True, help="Context note title")
    p_ctx.add_argument("--body", default="", help="Context markdown body")
    p_ctx.add_argument(
        "--folder",
        default="Sessions",
        choices=["Sessions", "Context"],
        help="Destination folder under AI Workspace",
    )

    p_read = sub.add_parser("read-context", help="Read latest context/session note")
    p_read.add_argument("--vault", default="", help="Vault path (default: auto-detect open vault)")
    p_read.add_argument("--session", default="", help="Filter by session name fragment")
    p_read.add_argument("--oldest", action="store_true", help="Read oldest matching file")
    p_read.add_argument("--folders", default="Sessions,Context", help="Comma-separated folders under AI Workspace")
    p_read.add_argument("--max-chars", type=int, default=6000, help="Max characters to print")

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.command == "list-vaults":
        vaults = discover_vaults()
        if getattr(args, "json", False):
            print(json.dumps([asdict(v) for v in vaults], indent=2))
        else:
            if not vaults:
                print("No vaults found.")
            for v in vaults:
                marker = "*" if v.open else "-"
                print(f"{marker} {v.path}")
        return 0

    vault = resolve_vault_path(getattr(args, "vault", ""))

    if args.command == "init-workspace":
        created = init_workspace(vault)
        print(f"Vault: {vault}")
        print(f"Workspace: {workspace_root(vault)}")
        print(f"Created entries: {len(created)}")
        for item in created:
            print(f"- {item}")
        return 0

    if args.command == "verify-workspace":
        report = verify_workspace(vault)
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "post-task":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        target = post_task(
            vault_path=vault,
            title=args.title,
            body=args.body,
            owner=args.owner,
            priority=args.priority,
            status=args.status,
            tags=tags,
        )
        print(str(target))
        return 0

    if args.command == "post-context":
        target = post_context(
            vault_path=vault,
            title=args.title,
            body=args.body,
            folder=args.folder,
        )
        print(str(target))
        return 0

    if args.command == "read-context":
        folders = [f.strip() for f in args.folders.split(",") if f.strip()]
        record = read_context(
            vault_path=vault,
            session_query=args.session,
            include_folders=folders,
            latest=not args.oldest,
            max_chars=args.max_chars,
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
