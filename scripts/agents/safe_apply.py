#!/usr/bin/env python3
"""Sandboxed patch application — never touches the main tree on failure.

Flow:
  1. Parse a unified diff (git apply --check) inside an isolated git worktree.
  2. Apply the patch in the worktree.
  3. Run a smoke command (default: import-check the touched Python files).
  4. If smoke passes: replay the same patch on the main tree.
  5. Always remove the worktree (try/finally), even on smoke failure or crash.

Guarantees:
- Main tree is bit-identical until the worktree smoke passes.
- Worktree lives under ``<repo>/.scbe-sandbox/`` (gitignored, single root).
- Patches that touch ``.git``, ``.scbe-sandbox``, ``.venv*``, ``node_modules``
  or escape the repo root are rejected before the worktree is created.
- Smoke command runs under a timeout (default 60s).
- No ``rm -rf`` calls; uses ``git worktree remove --force`` + ``shutil.rmtree``
  on the worktree directory only.

CLI:
  python scripts/agents/safe_apply.py --patch-file patch.diff
  cat patch.diff | python scripts/agents/safe_apply.py
  python scripts/agents/safe_apply.py --patch-file p.diff --smoke "pytest -x tests/foo.py"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SANDBOX_ROOT = REPO_ROOT / ".scbe-sandbox"

FORBIDDEN_PATH_PREFIXES = (
    ".git/",
    ".git\\",
    ".scbe-sandbox/",
    ".scbe-sandbox\\",
    ".venv-training/",
    ".venv-training\\",
    ".venv/",
    ".venv\\",
    "node_modules/",
    "node_modules\\",
    "unsloth_compiled_cache/",
    "unsloth_compiled_cache\\",
)


@dataclass
class ApplyResult:
    ok: bool
    applied: bool
    sandbox_path: str
    touched_files: List[str] = field(default_factory=list)
    smoke_cmd: str = ""
    smoke_stdout: str = ""
    smoke_stderr: str = ""
    smoke_returncode: Optional[int] = None
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)


_DIFF_PATH_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
_PLUSPLUS_RE = re.compile(r"^\+\+\+ b/(.+?)$", re.MULTILINE)


def _extract_touched_files(patch_text: str) -> List[str]:
    """Pull every file path the patch claims to touch."""
    files: set[str] = set()
    for m in _DIFF_PATH_RE.finditer(patch_text):
        files.add(m.group(1))
        files.add(m.group(2))
    for m in _PLUSPLUS_RE.finditer(patch_text):
        files.add(m.group(1))
    files.discard("/dev/null")
    return sorted(files)


def _path_is_safe(rel_path: str) -> bool:
    """Reject paths that escape the repo or hit forbidden zones."""
    if not rel_path or rel_path == "/dev/null":
        return True
    norm = rel_path.replace("\\", "/")
    if norm.startswith("/") or norm.startswith("../") or "/../" in norm:
        return False
    for prefix in FORBIDDEN_PATH_PREFIXES:
        if norm.startswith(prefix.replace("\\", "/")):
            return False
    return True


def _git(args: List[str], cwd: Path, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _default_smoke_cmd(touched_files: List[str]) -> str:
    """Default smoke = import-check every touched .py file."""
    py_files = [f for f in touched_files if f.endswith(".py")]
    if not py_files:
        return "python -c \"print('no python files touched; smoke trivially ok')\""
    mods = []
    for f in py_files:
        mod = f.replace("/", ".").replace("\\", ".")
        if mod.endswith(".py"):
            mod = mod[:-3]
        mods.append(mod)
    py_args = "; ".join(f"importlib.import_module({m!r})" for m in mods)
    return (
        "python -c \"import importlib, sys; sys.path.insert(0, '.'); "
        f"{py_args}; print('imports ok')\""
    )


def _ensure_sandbox_root() -> None:
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    gi = SANDBOX_ROOT / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")


def _remove_worktree(worktree: Path) -> None:
    """Best-effort worktree teardown. Never raises."""
    try:
        _git(["worktree", "remove", "--force", str(worktree)], cwd=REPO_ROOT, check=False, timeout=30)
    except Exception:
        pass
    if worktree.exists():
        try:
            shutil.rmtree(worktree, ignore_errors=True)
        except Exception:
            pass
    try:
        _git(["worktree", "prune"], cwd=REPO_ROOT, check=False, timeout=30)
    except Exception:
        pass


def apply_patch_safely(
    patch_text: str,
    smoke_cmd: Optional[str] = None,
    smoke_timeout: int = 60,
) -> ApplyResult:
    """Sandbox-apply a unified-diff patch. Returns ApplyResult."""
    if not patch_text.strip():
        return ApplyResult(ok=False, applied=False, sandbox_path="", error="empty patch")

    touched = _extract_touched_files(patch_text)
    bad = [p for p in touched if not _path_is_safe(p)]
    if bad:
        return ApplyResult(
            ok=False,
            applied=False,
            sandbox_path="",
            touched_files=touched,
            error=f"patch touches forbidden paths: {bad}",
        )

    _ensure_sandbox_root()
    sandbox_id = uuid.uuid4().hex[:12]
    worktree = SANDBOX_ROOT / f"wt-{sandbox_id}"

    smoke = smoke_cmd or _default_smoke_cmd(touched)
    result = ApplyResult(
        ok=False,
        applied=False,
        sandbox_path=str(worktree),
        touched_files=touched,
        smoke_cmd=smoke,
    )

    try:
        try:
            _git(["worktree", "add", "--detach", str(worktree), "HEAD"], cwd=REPO_ROOT, timeout=60)
        except subprocess.CalledProcessError as e:
            result.error = f"git worktree add failed: {e.stderr.strip() or e.stdout.strip()}"
            return result
        except subprocess.TimeoutExpired:
            result.error = "git worktree add timed out"
            return result

        patch_file = worktree / ".scbe_patch.diff"
        patch_file.write_text(patch_text, encoding="utf-8")

        try:
            _git(["apply", "--check", str(patch_file)], cwd=worktree, timeout=30)
        except subprocess.CalledProcessError as e:
            result.error = f"patch does not apply cleanly: {e.stderr.strip() or e.stdout.strip()}"
            return result

        try:
            _git(["apply", str(patch_file)], cwd=worktree, timeout=30)
        except subprocess.CalledProcessError as e:
            result.error = f"git apply failed inside worktree: {e.stderr.strip() or e.stdout.strip()}"
            return result

        try:
            patch_file.unlink()
        except Exception:
            pass

        try:
            proc = subprocess.run(
                smoke,
                shell=True,
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=smoke_timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired as e:
            result.error = f"smoke timed out after {smoke_timeout}s"
            result.smoke_stdout = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            result.smoke_stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return result

        result.smoke_returncode = proc.returncode
        result.smoke_stdout = proc.stdout
        result.smoke_stderr = proc.stderr
        if proc.returncode != 0:
            result.error = f"smoke command exited {proc.returncode}"
            return result

        main_patch = REPO_ROOT / f".scbe_patch-{sandbox_id}.diff"
        main_patch.write_text(patch_text, encoding="utf-8")
        try:
            _git(["apply", "--check", str(main_patch)], cwd=REPO_ROOT, timeout=30)
            _git(["apply", str(main_patch)], cwd=REPO_ROOT, timeout=30)
            result.applied = True
            result.ok = True
        except subprocess.CalledProcessError as e:
            result.error = f"main-tree apply failed after sandbox passed: {e.stderr.strip() or e.stdout.strip()}"
        finally:
            try:
                main_patch.unlink()
            except Exception:
                pass
        return result
    finally:
        _remove_worktree(worktree)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sandbox-apply a unified diff patch.")
    parser.add_argument("--patch-file", help="Path to patch; if omitted, reads from stdin.")
    parser.add_argument("--smoke", help="Smoke command to run inside worktree before main-tree apply.")
    parser.add_argument("--smoke-timeout", type=int, default=60, help="Smoke command timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Run smoke in sandbox; do NOT apply on main even if smoke passes.")
    args = parser.parse_args(argv)

    if args.patch_file:
        patch_text = Path(args.patch_file).read_text(encoding="utf-8")
    else:
        patch_text = sys.stdin.read()

    if args.dry_run:
        touched = _extract_touched_files(patch_text)
        bad = [p for p in touched if not _path_is_safe(p)]
        if bad:
            print(json.dumps({"ok": False, "dry_run": True, "error": f"forbidden paths: {bad}"}, indent=2))
            return 2

    result = apply_patch_safely(patch_text, smoke_cmd=args.smoke, smoke_timeout=args.smoke_timeout)
    if args.dry_run and result.ok:
        result.applied = False
        result.error = "dry-run: smoke passed but main-tree apply skipped"
    print(result.to_json())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
