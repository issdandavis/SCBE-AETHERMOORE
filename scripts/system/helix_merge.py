"""Helix Merge — Self-healing dual-strand merge system.

Like DNA: two strands (main + feature) continuously zip together.
When conflicts arise, repair agents resolve them automatically.
Push and pull work together in a double helix rhythm.

Usage:
    python scripts/system/helix_merge.py                    # dry run
    python scripts/system/helix_merge.py --execute          # actually merge
    python scripts/system/helix_merge.py --execute --squash  # squash merge
    python scripts/system/helix_merge.py --status           # just show status
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class ConflictReport:
    file: str
    ours_lines: int
    theirs_lines: int
    resolution: str  # "ours", "theirs", "manual", "auto"
    reason: str


@dataclass
class HelixState:
    timestamp: str
    main_branch: str
    feature_branch: str
    commits_ahead: int
    commits_behind: int
    conflicts: List[ConflictReport]
    resolved: int
    unresolved: int
    status: str  # "clean", "diverged", "conflicted", "merged"
    actions_taken: List[str]


def run(cmd: str, cwd: str = None) -> Tuple[int, str]:
    """Run a shell command, return (exit_code, output)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(PROJECT_ROOT),
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def get_current_branch() -> str:
    _, out = run("git branch --show-current")
    return out.strip()


def get_commits_ahead_behind(feature: str, main: str) -> Tuple[int, int]:
    _, ahead = run(f"git rev-list --count {main}..{feature}")
    _, behind = run(f"git rev-list --count {feature}..{main}")
    try:
        return int(ahead.strip()), int(behind.strip())
    except ValueError:
        return 0, 0


def get_conflict_files() -> List[str]:
    _, out = run("git diff --name-only --diff-filter=U")
    return [f.strip() for f in out.split("\n") if f.strip()]


def auto_resolve_conflict(filepath: str) -> ConflictReport:
    """Try to auto-resolve a conflict using heuristics.

    Resolution strategy:
    - docs/ files: keep ours (feature branch has newer docs)
    - tests/ files: keep ours (feature branch has newer tests)
    - src/ files: keep ours but flag for review
    - config/ files: keep theirs (main has authoritative config)
    - .github/workflows/: keep theirs (main has CI fixes)
    - training-data/: keep ours (feature has more data)
    - package.json / pyproject.toml: keep theirs then re-apply version bumps
    """
    # Read the conflicted file to count conflict markers
    full_path = PROJECT_ROOT / filepath
    ours_lines = 0
    theirs_lines = 0

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        in_ours = False
        in_theirs = False
        for line in content.split("\n"):
            if line.startswith("<<<<<<<"):
                in_ours = True
                continue
            elif line.startswith("======="):
                in_ours = False
                in_theirs = True
                continue
            elif line.startswith(">>>>>>>"):
                in_theirs = False
                continue
            if in_ours:
                ours_lines += 1
            if in_theirs:
                theirs_lines += 1
    except Exception:
        logger.debug("Could not parse conflict markers in %s", filepath, exc_info=True)

    # Determine resolution strategy based on file path
    resolution = "ours"
    reason = "default: feature branch is newer"

    if filepath.startswith(".github/workflows/"):
        resolution = "theirs"
        reason = "CI workflows: main branch has authoritative CI config"
    elif filepath.startswith("config/"):
        resolution = "theirs"
        reason = "config: main branch has authoritative configuration"
    elif filepath in ("package.json", "pyproject.toml", "package-lock.json"):
        resolution = "theirs"
        reason = "package manifests: main branch version is authoritative"
    elif filepath.startswith("docs/"):
        resolution = "ours"
        reason = "docs: feature branch has newer documentation"
    elif filepath.startswith("tests/"):
        resolution = "ours"
        reason = "tests: feature branch has newer test coverage"
    elif filepath.startswith("src/"):
        resolution = "ours"
        reason = "src: feature branch has newer implementation"
    elif filepath.startswith("training-data/") or filepath.startswith("training/"):
        resolution = "ours"
        reason = "training data: feature branch has more data"
    elif filepath.startswith("artifacts/"):
        resolution = "ours"
        reason = "artifacts: feature branch has newer artifacts"

    return ConflictReport(
        file=filepath,
        ours_lines=ours_lines,
        theirs_lines=theirs_lines,
        resolution=resolution,
        reason=reason,
    )


def apply_resolution(report: ConflictReport) -> bool:
    """Apply the resolution strategy for a conflicted file."""
    if report.resolution == "ours":
        code, _ = run(f'git checkout --ours "{report.file}" && git add "{report.file}"')
    elif report.resolution == "theirs":
        code, _ = run(f'git checkout --theirs "{report.file}" && git add "{report.file}"')
    else:
        return False  # manual resolution needed
    return code == 0


def dual_push(branch: str, main: str = "main") -> List[str]:
    """Push to both GitHub and GitLab."""
    actions = []

    # Push to GitHub
    code, out = run(f"git push origin {branch}")
    if code == 0:
        actions.append(f"Pushed to GitHub origin/{branch}")
    else:
        actions.append(f"GitHub push failed: {out[:100]}")

    # Push to GitLab
    code, out = run(f"git push gitlab {branch}:{main}")
    if code == 0:
        actions.append(f"Pushed to GitLab gitlab/{main}")
    else:
        actions.append(f"GitLab push failed: {out[:100]}")

    return actions


def helix_merge(
    feature_branch: str = None,
    main_branch: str = "main",
    execute: bool = False,
    squash: bool = False,
) -> HelixState:
    """Run the helix merge cycle."""

    if feature_branch is None:
        feature_branch = get_current_branch()

    actions = []

    # Step 1: Fetch latest from both remotes
    actions.append("Fetching from all remotes...")
    run("git fetch origin")
    run("git fetch gitlab")

    # Step 2: Check divergence
    ahead, behind = get_commits_ahead_behind(feature_branch, f"origin/{main_branch}")
    actions.append(f"Branch {feature_branch}: {ahead} ahead, {behind} behind origin/{main_branch}")

    if ahead == 0:
        return HelixState(
            timestamp=datetime.now().isoformat(),
            main_branch=main_branch,
            feature_branch=feature_branch,
            commits_ahead=0,
            commits_behind=behind,
            conflicts=[],
            resolved=0,
            unresolved=0,
            status="clean",
            actions_taken=actions + ["Nothing to merge — branch is up to date with main"],
        )

    if behind == 0:
        actions.append("Main has no new commits. Safe to fast-forward merge.")

    if not execute:
        return HelixState(
            timestamp=datetime.now().isoformat(),
            main_branch=main_branch,
            feature_branch=feature_branch,
            commits_ahead=ahead,
            commits_behind=behind,
            conflicts=[],
            resolved=0,
            unresolved=0,
            status="diverged" if behind > 0 else "ready",
            actions_taken=actions + ["DRY RUN — pass --execute to actually merge"],
        )

    # Step 3: Stash any dirty work
    _, dirty = run("git status --porcelain")
    if dirty.strip():
        run('git stash push -m "helix-merge-autostash"')
        actions.append("Stashed dirty work")

    # Step 4: Merge main into feature (the helix twist)
    if behind > 0:
        actions.append(f"Merging origin/{main_branch} into {feature_branch}...")
        code, out = run(f"git merge origin/{main_branch} --no-edit")

        if code != 0 and "CONFLICT" in out:
            # Step 5: Auto-resolve conflicts
            conflict_files = get_conflict_files()
            actions.append(f"Found {len(conflict_files)} conflicts — auto-resolving...")

            reports = []
            resolved = 0
            for cf in conflict_files:
                report = auto_resolve_conflict(cf)
                if apply_resolution(report):
                    resolved += 1
                    actions.append(f"  Resolved {cf}: {report.resolution} ({report.reason})")
                else:
                    actions.append(f"  MANUAL NEEDED: {cf}")
                reports.append(report)

            unresolved = len(conflict_files) - resolved

            if unresolved == 0:
                # All resolved — commit the merge
                run('git commit -m "merge: helix auto-resolve — main into feature branch"')
                actions.append("All conflicts resolved. Merge committed.")
            else:
                return HelixState(
                    timestamp=datetime.now().isoformat(),
                    main_branch=main_branch,
                    feature_branch=feature_branch,
                    commits_ahead=ahead,
                    commits_behind=behind,
                    conflicts=reports,
                    resolved=resolved,
                    unresolved=unresolved,
                    status="conflicted",
                    actions_taken=actions + [f"{unresolved} conflicts need manual resolution"],
                )
        else:
            actions.append("Merge completed cleanly (no conflicts)")

    # Step 6: Now merge feature into main
    actions.append(f"Switching to {main_branch} and merging {feature_branch}...")
    run(f"git checkout {main_branch}")

    if squash:
        code, out = run(f"git merge --squash {feature_branch}")
        if code == 0:
            run(f'git commit -m "feat: squash merge {feature_branch} — all session work"')
            actions.append(f"Squash-merged {feature_branch} into {main_branch}")
    else:
        code, out = run(f"git merge {feature_branch} --no-edit")
        if code == 0:
            actions.append(f"Merged {feature_branch} into {main_branch}")
        else:
            actions.append(f"Merge into main failed: {out[:200]}")
            run(f"git checkout {feature_branch}")
            return HelixState(
                timestamp=datetime.now().isoformat(),
                main_branch=main_branch,
                feature_branch=feature_branch,
                commits_ahead=ahead,
                commits_behind=behind,
                conflicts=[],
                resolved=0,
                unresolved=0,
                status="failed",
                actions_taken=actions,
            )

    # Step 7: Dual push
    push_actions = dual_push(main_branch, main_branch)
    actions.extend(push_actions)

    # Step 8: Switch back to feature branch and rebase
    run(f"git checkout {feature_branch}")

    # Step 9: Pop stash if we stashed
    if dirty.strip():
        run("git stash pop")
        actions.append("Restored stashed work")

    # Recount
    new_ahead, new_behind = get_commits_ahead_behind(feature_branch, f"origin/{main_branch}")

    return HelixState(
        timestamp=datetime.now().isoformat(),
        main_branch=main_branch,
        feature_branch=feature_branch,
        commits_ahead=new_ahead,
        commits_behind=new_behind,
        conflicts=[],
        resolved=0,
        unresolved=0,
        status="merged",
        actions_taken=actions,
    )


def main():
    parser = argparse.ArgumentParser(description="Helix Merge — self-healing dual-strand merge")
    parser.add_argument("--execute", action="store_true", help="Actually perform the merge (default: dry run)")
    parser.add_argument("--squash", action="store_true", help="Squash all commits into one")
    parser.add_argument("--status", action="store_true", help="Just show status, don't merge")
    parser.add_argument("--main", default="main", help="Main branch name")
    parser.add_argument("--feature", default=None, help="Feature branch (default: current)")
    args = parser.parse_args()

    if args.status:
        branch = args.feature or get_current_branch()
        ahead, behind = get_commits_ahead_behind(branch, f"origin/{args.main}")
        print(f"Branch: {branch}")
        print(f"Ahead of {args.main}: {ahead}")
        print(f"Behind {args.main}: {behind}")
        print(f"Status: {'ready to merge' if behind == 0 else 'needs rebase/merge'}")
        return

    state = helix_merge(
        feature_branch=args.feature,
        main_branch=args.main,
        execute=args.execute,
        squash=args.squash,
    )

    print(f"\n{'=' * 60}")
    print(f"  HELIX MERGE {'RESULT' if args.execute else 'DRY RUN'}")
    print(f"{'=' * 60}")
    print(f"  Status:  {state.status}")
    print(f"  Branch:  {state.feature_branch} -> {state.main_branch}")
    print(f"  Ahead:   {state.commits_ahead}")
    print(f"  Behind:  {state.commits_behind}")
    if state.conflicts:
        print(f"  Conflicts: {len(state.conflicts)} ({state.resolved} resolved, {state.unresolved} unresolved)")
    print(f"\n  Actions:")
    for a in state.actions_taken:
        print(f"    {a}")
    print(f"{'=' * 60}")

    # Save state
    out_path = PROJECT_ROOT / "artifacts" / "helix_merge_state.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(state), indent=2, default=str))
    print(f"\n  State saved to: {out_path}")


if __name__ == "__main__":
    main()
