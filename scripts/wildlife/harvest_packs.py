"""Harvest real work signals from the repo and classify them by pack.

Signals collected:
- Open GitHub issues (via `gh issue list --json`)
- Open GitHub PRs needing attention (via `gh pr list`)
- TODO / FIXME / XXX / HACK comments in source
- Recently failed workflow runs
- Stale branches (>30 days, not merged)
- Untracked work surfaced from docs/specs/*.md headers (pending dragons)

Output: `.scbe/wildlife/board.json` (or path given by --out).

Usage:
    python scripts/wildlife/harvest_packs.py
    python scripts/wildlife/harvest_packs.py --out /tmp/board.json --no-github
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.wildlife.packs import PACKS, classify  # noqa: E402

DEFAULT_OUT = ROOT / ".scbe" / "wildlife" / "board.json"

TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b\s*:?\s*(.{0,140})", re.IGNORECASE)
SOURCE_GLOBS = ("**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.rs")
SKIP_DIRS = (
    "node_modules",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "external",
    ".home",
    ".scbe",
    # vendored / cached / generated content — TODOs in here aren't ours
    # to triage and flooded the crow pack with 195 third-party comments
    "artifacts",
    "training-data",
    "training_data",
    "training",
    ".cache",
    ".next",
    "site-packages",
    "rust/scbe_core/target",
    "scbe-visual-system/node_modules",
    "kindle-app/node_modules",
    # vendored repos
    "unsloth",
    "_external",
    "vendored",
    "third_party",
    "third-party",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _gh(args: list[str]) -> list[dict]:
    """Run `gh` with --json output, return parsed list. Empty list on error."""
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False, timeout=30)
        if result.returncode != 0:
            return []
        return json.loads(result.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return []


def _bus_command(task: str, task_type: str, series_id: str) -> str:
    safe_task = task.replace("'", "'\\''")
    return (
        f"scbe-system agentbus run --task '{safe_task}' --task-type {task_type} "
        f"--series-id {series_id} --privacy local_only"
    )


def harvest_issues(limit: int) -> list[dict]:
    """Open GitHub issues."""
    raw = _gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,labels,author,createdAt,url",
        ]
    )
    out = []
    for r in raw:
        labels = [l.get("name", "") for l in r.get("labels", [])]
        out.append(
            {
                "id": f"issue-{r.get('number')}",
                "title": r.get("title", "")[:200],
                "body": "",
                "labels": labels,
                "author": (r.get("author") or {}).get("login", ""),
                "source": "github-issue",
                "url": r.get("url", ""),
                "first_seen": (r.get("createdAt") or "")[:10],
            }
        )
    return out


def harvest_prs(limit: int) -> list[dict]:
    """Open PRs that aren't yours-and-merging — anything still needing a decision."""
    raw = _gh(
        [
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,author,createdAt,labels,isDraft,url",
        ]
    )
    out = []
    for r in raw:
        labels = [l.get("name", "") for l in r.get("labels", [])]
        out.append(
            {
                "id": f"pr-{r.get('number')}",
                "title": r.get("title", "")[:200],
                "body": "",
                "labels": labels + (["draft"] if r.get("isDraft") else []),
                "author": (r.get("author") or {}).get("login", ""),
                "source": "github-pr",
                "url": r.get("url", ""),
                "first_seen": (r.get("createdAt") or "")[:10],
            }
        )
    return out


def harvest_failing_workflows(limit: int) -> list[dict]:
    """Recently-failed workflow runs are wolves OR bees depending on context."""
    raw = _gh(
        [
            "run",
            "list",
            "--limit",
            str(limit),
            "--status",
            "failure",
            "--json",
            "name,workflowName,databaseId,createdAt,url,event,conclusion",
        ]
    )
    out = []
    for r in raw:
        name = r.get("workflowName") or r.get("name", "")
        out.append(
            {
                "id": f"run-{r.get('databaseId')}",
                "title": f"workflow failed: {name}",
                "body": f"event={r.get('event','')}",
                "labels": [],
                "source": "workflow-failure",
                "url": r.get("url", ""),
                "first_seen": (r.get("createdAt") or "")[:10],
            }
        )
    return out


_SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs"}


def _walk_source_files(root: Path) -> list[Path]:
    """os.walk with topdown pruning so SKIP_DIRS get cut early.

    A naive `root.glob('**/*.py')` walks every directory including
    node_modules and external/ before filtering, which is many seconds on
    this repo. Match SKIP_DIRS by exact name OR prefix so e.g.
    `unsloth_compiled_cache/` is pruned by the `unsloth` entry.
    """
    out: list[Path] = []
    skip = tuple(SKIP_DIRS)

    def _pruned(d: str) -> bool:
        if d.startswith(".") or d.startswith("_"):
            return True
        return any(d == s or d.startswith(s + "_") or d.startswith(s + "-") for s in skip)

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune in place — must mutate dirnames so os.walk skips them
        dirnames[:] = [d for d in dirnames if not _pruned(d)]
        for name in filenames:
            ext = os.path.splitext(name)[1]
            if ext not in _SOURCE_EXTS:
                continue
            p = Path(dirpath) / name
            try:
                if p.stat().st_size > 500_000:
                    continue
            except OSError:
                continue
            out.append(p)
    return out


def harvest_todos(root: Path, max_per_file: int = 5, max_total: int = 200) -> list[dict]:
    """Sweep TODO/FIXME/XXX/HACK comments. These are crows."""
    out: list[dict] = []
    for path in _walk_source_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        per_file = 0
        for i, line in enumerate(text.splitlines(), start=1):
            m = TODO_RE.search(line)
            if not m:
                continue
            kind = m.group(1).upper()
            note = (m.group(2) or "").strip().rstrip(":,;-")
            out.append(
                {
                    "id": f"todo-{rel.replace('/', '_')}-{i}",
                    "title": f"{kind}: {note[:120] or '(no note)'}",
                    "body": f"{rel}:{i}",
                    "labels": [kind.lower()],
                    "source": "todo-comment",
                    "url": "",
                    "path": rel,
                    "first_seen": _now_iso()[:10],
                }
            )
            per_file += 1
            if per_file >= max_per_file:
                break
            if len(out) >= max_total:
                return out
        if len(out) >= max_total:
            break
    return out


def harvest_dragons_from_specs(root: Path) -> list[dict]:
    """Spec docs named like proposals or major-architecture become dragons."""
    out: list[dict] = []
    spec_dir = root / "docs" / "specs"
    if not spec_dir.exists():
        return out
    for spec in sorted(spec_dir.glob("*.md")):
        name = spec.stem.lower()
        if any(
            k in name
            for k in (
                "darpa",
                "mathbac",
                "clara",
                "proposal",
                "federal",
                "sam_gov",
                "wildlife_board",
            )
        ):
            try:
                first_line = spec.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
            except OSError:
                first_line = spec.stem
            title = first_line.lstrip("# ").strip()[:200] or spec.stem
            out.append(
                {
                    "id": f"spec-{spec.stem}",
                    "title": f"spec: {title}",
                    "body": f"docs/specs/{spec.name}",
                    "labels": ["spec"],
                    "source": "spec-doc",
                    "url": "",
                    "path": f"docs/specs/{spec.name}",
                    "first_seen": _now_iso()[:10],
                }
            )
    return out


def liberties_for(signal: dict) -> int:
    """Estimate open dependencies. Heuristic: more labels + draft = fewer liberties.

    Range 0-4. 0 = trapped, 4 = wide open.
    """
    labels = [str(l).lower() for l in signal.get("labels", [])]
    if any(l in ("blocked", "needs-info", "needs-decision", "draft") for l in labels):
        return 0
    if signal.get("source") in {"workflow-failure", "broken-deploy"}:
        return 1
    if signal.get("source") == "todo-comment":
        return 4
    return 3


def build_board(signals: list[dict]) -> dict:
    by_pack: dict[str, list[dict]] = {p: [] for p in PACKS}
    for sig in signals:
        pack = classify(sig)
        sig_out = {
            "id": sig["id"],
            "title": sig["title"],
            "source": sig["source"],
            "url": sig.get("url", ""),
            "path": sig.get("path", ""),
            "labels": sig.get("labels", []),
            "first_seen": sig.get("first_seen", ""),
            "liberties": liberties_for(sig),
            "tame_command": _bus_command(
                f"tame {pack.lower()}: {sig['title'][:80]}",
                PACKS[pack].bus_task_type,
                sig["id"],
            ),
        }
        by_pack[pack].append(sig_out)

    # Sort each pack: lowest liberties first (most urgent)
    for pack in by_pack:
        by_pack[pack].sort(key=lambda s: (s["liberties"], s["id"]))

    totals = {PACKS[p].plural: len(by_pack[p]) for p in by_pack}
    breeding = {}
    for pname, plist in by_pack.items():
        threshold = PACKS[pname].breeding_threshold
        if threshold is not None and len(plist) >= threshold:
            breeding[PACKS[pname].plural] = {
                "count": len(plist),
                "threshold": threshold,
                "rule": PACKS[pname].breeding_rule,
            }

    return {
        "schema": "wildlife-board-v1",
        "harvested_at": _now_iso(),
        "totals": totals,
        "breeding_now": breeding,
        "packs": {PACKS[p].plural: by_pack[p] for p in by_pack},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output board.json path")
    parser.add_argument("--no-github", action="store_true", help="skip GitHub API calls (offline mode)")
    parser.add_argument("--issues-limit", type=int, default=100, help="max GH issues to fetch")
    parser.add_argument("--prs-limit", type=int, default=50, help="max GH PRs to fetch")
    parser.add_argument("--runs-limit", type=int, default=20, help="max recent failed runs to fetch")
    parser.add_argument("--todos-limit", type=int, default=200, help="max TODO comments to harvest")
    args = parser.parse_args()

    signals: list[dict] = []
    if not args.no_github:
        signals.extend(harvest_issues(args.issues_limit))
        signals.extend(harvest_prs(args.prs_limit))
        signals.extend(harvest_failing_workflows(args.runs_limit))
    signals.extend(harvest_todos(ROOT, max_total=args.todos_limit))
    signals.extend(harvest_dragons_from_specs(ROOT))

    board = build_board(signals)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[wildlife] harvested {sum(board['totals'].values())} signals -> {out_path}")
    for plural, count in sorted(board["totals"].items(), key=lambda kv: -kv[1]):
        if count == 0:
            continue
        print(f"  {plural:<10s} {count}")
    if board["breeding_now"]:
        print()
        print("BREEDING NOW:")
        for plural, info in board["breeding_now"].items():
            print(f"  {plural} count={info['count']} threshold={info['threshold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
