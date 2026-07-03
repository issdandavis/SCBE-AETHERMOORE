#!/usr/bin/env python3
"""Local worktree garden tracker.

This is a small, receipt-first registry for local code "plots". A plot can be a
git worktree/repo or a storage lane. Agents attach by taking a lease with a TTL;
the lease does not execute code, it only declares local intent so multiple agents
can avoid stepping on the same workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "system" / "worktree_garden.json"
DEFAULT_STATE = REPO_ROOT / "artifacts" / "worktree_garden" / "state.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs" / "ops" / "WORKTREE_GARDEN.md"
DEFAULT_RECEIPTS = REPO_ROOT / "artifacts" / "worktree_garden" / "receipts"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


def safe_slug(value: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value.strip())[:80].strip("-")
    return out or "agent"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def expand_path(raw: str) -> Path:
    text = str(raw)
    for key, value in os.environ.items():
        text = text.replace("${" + key + "}", value)
    return Path(os.path.expandvars(os.path.expanduser(text))).resolve()


def run(cmd: list[str], cwd: Path, timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False, timeout=timeout)


def is_git_repo(path: Path) -> bool:
    if not path.exists():
        return False
    result = run(["git", "rev-parse", "--show-toplevel"], path)
    return result.returncode == 0


def git_info(path: Path) -> dict[str, Any]:
    if not is_git_repo(path):
        return {"is_git": False}

    top = run(["git", "rev-parse", "--show-toplevel"], path).stdout.strip()
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path).stdout.strip()
    head = run(["git", "rev-parse", "--short", "HEAD"], path).stdout.strip()
    status = run(["git", "status", "--short"], path, timeout=15).stdout.splitlines()
    worktree_raw = run(["git", "worktree", "list", "--porcelain"], path).stdout

    statuses = Counter()
    for line in status:
        if len(line) >= 2:
            statuses[line[:2].strip() or "modified"] += 1

    return {
        "is_git": True,
        "repo_root": top,
        "branch": branch,
        "head": head,
        "dirty_count": len(status),
        "status_counts": dict(sorted(statuses.items())),
        "worktrees": parse_git_worktrees(worktree_raw),
    }


def parse_git_worktrees(raw: str) -> list[dict[str, Any]]:
    blocks = [block for block in raw.strip().split("\n\n") if block.strip()]
    rows: list[dict[str, Any]] = []
    for block in blocks:
        row: dict[str, Any] = {"path": "", "head": "", "branch": None, "detached": False, "locked": False}
        for line in block.splitlines():
            if line.startswith("worktree "):
                row["path"] = line.removeprefix("worktree ").strip()
            elif line.startswith("HEAD "):
                row["head"] = line.removeprefix("HEAD ").strip()
            elif line.startswith("branch "):
                row["branch"] = line.removeprefix("branch ").strip()
            elif line == "detached":
                row["detached"] = True
            elif line.startswith("locked"):
                row["locked"] = True
                reason = line.removeprefix("locked").strip()
                row["locked_reason"] = reason or None
        rows.append(row)
    return rows


def storage_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    files = 0
    dirs = 0
    top_bytes = 0
    try:
        children = sorted(path.iterdir(), key=lambda item: item.name.lower())
    except OSError as exc:
        return {"exists": True, "scan_error": str(exc)}

    for child in children[:200]:
        try:
            stat = child.stat()
        except OSError:
            continue
        if child.is_dir():
            dirs += 1
        else:
            files += 1
            top_bytes += stat.st_size

    return {
        "exists": True,
        "top_level_dirs": dirs,
        "top_level_files": files,
        "top_level_file_bytes": top_bytes,
        "cloud_backed": "onedrive" in str(path).lower(),
        "scan_note": "top-level probe only",
    }


def active_leases(state: dict[str, Any]) -> list[dict[str, Any]]:
    now = utc_now()
    leases = []
    for lease in state.get("leases", []):
        expires = parse_dt(lease.get("expires_at"))
        if expires and expires < now:
            continue
        if lease.get("status") == "released":
            continue
        leases.append(lease)
    return leases


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_plot(seed: dict[str, Any], leases: list[dict[str, Any]]) -> dict[str, Any]:
    path = expand_path(seed["path"])
    plot_leases = [lease for lease in leases if lease.get("plot_id") == seed["id"]]
    kind = seed.get("kind", "git")
    git = git_info(path) if kind == "git" or is_git_repo(path) else {"is_git": False}
    storage = storage_info(path) if kind == "storage" else None
    exists = path.exists()
    health = classify_health(seed, exists, git, storage, plot_leases)
    return {
        "id": seed["id"],
        "zone": seed["zone"],
        "kind": kind,
        "role": seed.get("role", ""),
        "path": str(path),
        "exists": exists,
        "max_agents": int(seed.get("max_agents", 1)),
        "active_agents": len(plot_leases),
        "health": health,
        "notes": seed.get("notes", ""),
        "git": git,
        "storage": storage,
        "leases": plot_leases,
    }


def classify_health(
    seed: dict[str, Any],
    exists: bool,
    git: dict[str, Any],
    storage: dict[str, Any] | None,
    leases: list[dict[str, Any]],
) -> str:
    if not exists:
        return "missing"
    if len(leases) >= int(seed.get("max_agents", 1)):
        return "occupied"
    if git.get("is_git") and int(git.get("dirty_count", 0)) > 0:
        return "growing-dirty"
    if storage and storage.get("cloud_backed"):
        return "cloud-storage"
    if leases:
        return "tended"
    return "ready"


def build_state(config: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = previous or {}
    leases = active_leases(previous)
    plots = [build_plot(seed, leases) for seed in config.get("plot_seeds", [])]
    zone_counts = Counter(plot["zone"] for plot in plots)
    zone_payload = {}
    for zone_id, zone in config.get("zones", {}).items():
        zone_payload[zone_id] = {
            **zone,
            "plot_count": zone_counts.get(zone_id, 0),
            "over_capacity": zone_counts.get(zone_id, 0) > int(zone.get("max_plots", 0)),
        }

    max_plots = int(config.get("max_plots", len(plots)))
    state = {
        "schema": "scbe_worktree_garden_state_v1",
        "garden_name": config.get("garden_name", "SCBE Worktree Garden"),
        "generated_at": utc_text(),
        "source": "scripts/system/worktree_garden.py",
        "max_plots": max_plots,
        "zones": zone_payload,
        "plots": plots,
        "leases": leases,
    }
    state["summary"] = summarize_state(state)
    state["garden_digest"] = garden_digest(state)
    return state


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    plots = state.get("plots", [])
    health = Counter(plot.get("health", "unknown") for plot in plots)
    return {
        "plots": len(plots),
        "max_plots": state.get("max_plots"),
        "free_plots": sum(
            1
            for plot in plots
            if plot.get("exists") and int(plot.get("active_agents", 0)) < int(plot.get("max_agents", 1))
        ),
        "leased_plots": sum(1 for plot in plots if plot.get("active_agents", 0) > 0),
        "active_leases": len(state.get("leases", [])),
        "missing_plots": sum(1 for plot in plots if not plot.get("exists")),
        "over_plot_capacity": len(plots) > int(state.get("max_plots", 0)),
        "health": dict(sorted(health.items())),
        "zones": {
            zone_id: {
                "plot_count": zone.get("plot_count", 0),
                "max_plots": zone.get("max_plots", 0),
                "over_capacity": zone.get("over_capacity", False),
            }
            for zone_id, zone in state.get("zones", {}).items()
        },
    }


def garden_digest(state: dict[str, Any]) -> str:
    stable = {
        "max_plots": state.get("max_plots"),
        "plots": [
            {
                "id": plot["id"],
                "path": plot["path"],
                "health": plot["health"],
                "dirty": plot.get("git", {}).get("dirty_count"),
                "agents": sorted(lease.get("agent") for lease in plot.get("leases", [])),
            }
            for plot in state.get("plots", [])
        ],
    }
    raw = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def render_markdown(state: dict[str, Any]) -> str:
    lines = [
        f"# {state['garden_name']}",
        "",
        f"Generated: `{state['generated_at']}`",
        f"Digest: `{state['garden_digest']}`",
        "",
        "This is the local worktree garden map. Plots are workspaces or storage lanes. Agents attach by lease.",
        "",
        "## Capacity",
        "",
        f"- Plots: `{state['summary']['plots']}/{state['summary']['max_plots']}`",
        f"- Active leases: `{state['summary']['active_leases']}`",
        f"- Missing plots: `{state['summary']['missing_plots']}`",
        f"- Over plot capacity: `{state['summary']['over_plot_capacity']}`",
        "",
        "## Zones",
        "",
        "| Zone | Label | Plots | Max | Purpose |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for zone_id, zone in state.get("zones", {}).items():
        lines.append(
            f"| `{zone_id}` | {zone.get('label', zone_id)} | {zone.get('plot_count', 0)} | "
            f"{zone.get('max_plots', 0)} | {zone.get('purpose', '')} |"
        )

    lines.extend(["", "## Plots", "", "| Plot | Zone | Health | Agents | Branch | Dirty | Path |", "| --- | --- | --- | ---: | --- | ---: | --- |"])
    for plot in state.get("plots", []):
        git = plot.get("git", {})
        branch = git.get("branch") or ""
        dirty = git.get("dirty_count", "")
        lines.append(
            f"| `{plot['id']}` | `{plot['zone']}` | `{plot['health']}` | {plot['active_agents']} | "
            f"`{branch}` | {dirty} | `{plot['path']}` |"
        )

    lines.extend(["", "## Active Agent Leases", ""])
    leases = state.get("leases", [])
    if leases:
        for lease in leases:
            lines.append(
                f"- `{lease['agent']}` on `{lease['plot_id']}` as `{lease['mode']}` until `{lease['expires_at']}`: "
                f"{lease.get('task', '')}"
            )
    else:
        lines.append("- No active leases.")

    lines.extend(
        [
            "",
            "## Agent Commands",
            "",
            "```powershell",
            "npm run worktree:garden -- status",
            "npm run worktree:garden -- attach --agent codex --plot house-scbe --task \"describe work\"",
            "npm run worktree:garden -- release --agent codex --plot house-scbe",
            "```",
            "",
            "## Safety Notes",
            "",
            "- Attachment is metadata only; it does not run a shell command or start a background worker.",
            "- Cloud-backed storage plots should be verify-first before move/delete work.",
            "- A dirty git plot is treated as growing work, not trash.",
            "",
        ]
    )
    return "\n".join(lines)


def write_state_and_markdown(state: dict[str, Any], state_path: Path, markdown_path: Path) -> None:
    write_json(state_path, state)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(state), encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    return read_json(path, {})


def lease_id(agent: str, plot_id: str, task: str) -> str:
    seed = f"{utc_text()}::{agent}::{plot_id}::{task}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def attach_agent(config: dict[str, Any], state: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    plot_id = args.plot
    agent = safe_slug(args.agent)
    task = args.task or ""
    mode = args.mode
    ttl = float(args.ttl_hours or config.get("default_lease_hours", 12))
    state = build_state(config, state)
    plots = {plot["id"]: plot for plot in state.get("plots", [])}
    if plot_id not in plots:
        raise SystemExit(f"unknown plot: {plot_id}")
    plot = plots[plot_id]
    if not plot.get("exists"):
        raise SystemExit(f"plot is missing: {plot_id} -> {plot.get('path')}")
    if plot.get("active_agents", 0) >= int(plot.get("max_agents", 1)):
        raise SystemExit(f"plot is full: {plot_id}")
    if mode == "work" and any(lease.get("mode") == "work" for lease in plot.get("leases", [])):
        raise SystemExit(f"plot already has a work lease: {plot_id}")

    now = utc_now()
    lease = {
        "lease_id": lease_id(agent, plot_id, task),
        "agent": agent,
        "plot_id": plot_id,
        "mode": mode,
        "task": task,
        "attached_at": utc_text(now),
        "expires_at": utc_text(now + timedelta(hours=ttl)),
        "status": "active",
    }
    state.setdefault("leases", []).append(lease)
    return build_state(config, state)


def release_agent(config: dict[str, Any], state: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    agent = safe_slug(args.agent) if args.agent else None
    lease_id_filter = args.lease_id
    plot_filter = args.plot
    released = []
    kept = []
    for lease in active_leases(state):
        matches = True
        if agent and lease.get("agent") != agent:
            matches = False
        if lease_id_filter and lease.get("lease_id") != lease_id_filter:
            matches = False
        if plot_filter and lease.get("plot_id") != plot_filter:
            matches = False
        if matches:
            lease = {**lease, "status": "released", "released_at": utc_text()}
            released.append(lease)
        else:
            kept.append(lease)
    state["leases"] = kept
    next_state = build_state(config, state)
    next_state["released"] = released
    return next_state


def write_receipt(receipts_dir: Path, action: str, state: dict[str, Any]) -> Path:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    path = receipts_dir / f"{stamp}-{safe_slug(action)}.json"
    write_json(
        path,
        {
            "schema": "scbe_worktree_garden_receipt_v1",
            "action": action,
            "created_at": utc_text(),
            "garden_digest": state.get("garden_digest"),
            "summary": state.get("summary"),
        },
    )
    return path


def print_result(payload: dict[str, Any], print_json: bool) -> None:
    if print_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    summary = payload.get("summary", {})
    print(f"garden={payload.get('garden_name')}")
    print(f"digest={payload.get('garden_digest')}")
    print(f"plots={summary.get('plots')}/{summary.get('max_plots')} active_leases={summary.get('active_leases')}")
    print(f"health={json.dumps(summary.get('health', {}), sort_keys=True)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track local worktree garden plots and agent leases.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--markdown", default=str(DEFAULT_MARKDOWN))
    parser.add_argument("--receipts-dir", default=str(DEFAULT_RECEIPTS))
    parser.add_argument("--json", action="store_true", dest="print_json")
    sub = parser.add_subparsers(dest="command")

    def allow_trailing_json(command_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        command_parser.add_argument("--json", action="store_true", dest="print_json", default=argparse.SUPPRESS)
        return command_parser

    allow_trailing_json(sub.add_parser("scan", help="Scan plots and write state/map."))
    allow_trailing_json(sub.add_parser("status", help="Print current garden status."))
    allow_trailing_json(sub.add_parser("plots", help="List plot details."))

    attach = allow_trailing_json(sub.add_parser("attach", help="Attach an AI agent to a local plot by lease."))
    attach.add_argument("--agent", required=True)
    attach.add_argument("--plot", required=True)
    attach.add_argument("--task", default="")
    attach.add_argument("--mode", choices=["observe", "work", "review"], default="work")
    attach.add_argument("--ttl-hours", type=float, default=None)

    release = allow_trailing_json(sub.add_parser("release", help="Release matching agent leases."))
    release.add_argument("--agent", default="")
    release.add_argument("--plot", default="")
    release.add_argument("--lease-id", default="")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.command = args.command or "status"
    config_path = Path(args.config).resolve()
    state_path = Path(args.state).resolve()
    markdown_path = Path(args.markdown).resolve()
    receipts_dir = Path(args.receipts_dir).resolve()
    config = load_config(config_path)
    previous = read_json(state_path, {})

    if args.command in {"scan", "status", "plots"}:
        state = build_state(config, previous)
    elif args.command == "attach":
        state = attach_agent(config, previous, args)
    elif args.command == "release":
        state = release_agent(config, previous, args)
    else:
        raise SystemExit(f"unknown command: {args.command}")

    write_state_and_markdown(state, state_path, markdown_path)
    receipt = write_receipt(receipts_dir, args.command, state)
    state["receipt_path"] = str(receipt)

    if args.command == "plots" and not args.print_json:
        for plot in state.get("plots", []):
            print(f"{plot['id']:24} {plot['zone']:18} {plot['health']:14} {plot['active_agents']} {plot['path']}")
    else:
        print_result(state, args.print_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
