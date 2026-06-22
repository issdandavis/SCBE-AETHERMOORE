#!/usr/bin/env python3
"""Supervised shell-in-shell runner for local AI agent integrations.

This is the first relay-station layer: a parent SCBE process launches a child
agent shell, feeds it a bounded task packet, captures the transcript, and emits a
receipt. It deliberately starts with subprocess pipes so it is portable and easy
to test; the command surface is shaped so a ConPTY/pywinpty backend can replace
the pipe backend later.
"""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_shell"
DEFAULT_MODEL = "qwen2.5-coder:3b"
DEFAULT_TIMEOUT_S = 45

KNOWN_INTEGRATIONS = {
    "claude",
    "codex-app",
    "hermes",
    "openclaw",
    "opencode",
    "codex",
    "copilot",
    "droid",
    "pi",
    "qwen",
}

BANNED_INPUT_MARKERS = (
    "git reset --hard",
    "Remove-Item -Recurse",
    "rm -rf",
    "del /s",
    "format ",
)


@dataclass
class AgentShellReceipt:
    ok: bool
    mode: str
    command: list[str]
    cwd: str
    started_at: str
    duration_s: float
    timeout_s: float
    timed_out: bool
    returncode: int | None
    stdout_tail: str
    stderr_tail: str
    receipt_path: str
    notes: list[str]
    readonly_worktree: bool = False
    worktree_changed: bool = False
    worktree_before: str | None = None
    worktree_after: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ollama_exe() -> str | None:
    found = _which("ollama")
    if found:
        return found
    common = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
    if common.exists():
        return str(common)
    return None


def _which(name: str) -> str | None:
    candidates = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        candidates.append(f"{name}.exe")
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        for candidate in candidates:
            path = Path(directory) / candidate
            if path.exists() and path.is_file():
                return str(path)
    return None


def _tail(text: str, limit: int = 6000) -> str:
    return text[-limit:] if len(text) > limit else text


def _check_task(task: str) -> list[str]:
    lowered = task.casefold()
    notes: list[str] = []
    for marker in BANNED_INPUT_MARKERS:
        if marker.casefold() in lowered:
            notes.append(f"blocked marker in task packet: {marker}")
    return notes


def _git_status(cwd: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def build_launch_command(
    integration: str,
    *,
    model: str = DEFAULT_MODEL,
    extra_args: Sequence[str] = (),
) -> list[str]:
    if integration not in KNOWN_INTEGRATIONS:
        raise ValueError(f"unknown integration {integration!r}; expected one of {sorted(KNOWN_INTEGRATIONS)}")
    exe = _ollama_exe()
    if not exe:
        raise FileNotFoundError("Ollama executable not found")
    command = [exe, "launch", integration]
    if model:
        command += ["--model", model]
    if extra_args:
        command += ["--", *extra_args]
    return command


def run_supervised(
    command: Sequence[str],
    *,
    task: str,
    cwd: Path = REPO_ROOT,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    mode: str = "command",
    readonly_worktree: bool = False,
) -> AgentShellReceipt:
    started_at = _utc_now()
    notes = _check_task(task)
    output_root.mkdir(parents=True, exist_ok=True)
    receipt_path = output_root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{mode}.json"

    if notes:
        receipt = AgentShellReceipt(
            ok=False,
            mode=mode,
            command=list(command),
            cwd=str(cwd),
            started_at=started_at,
            duration_s=0.0,
            timeout_s=timeout_s,
            timed_out=False,
            returncode=None,
            stdout_tail="",
            stderr_tail="",
            receipt_path=str(receipt_path),
            notes=notes,
            readonly_worktree=readonly_worktree,
        )
        receipt_path.write_text(json.dumps(asdict(receipt), indent=2), encoding="utf-8")
        return receipt

    worktree_before = _git_status(cwd) if readonly_worktree else None
    started = time.monotonic()
    proc = subprocess.Popen(
        list(command),
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdin is not None
    proc.stdin.write(task)
    if not task.endswith("\n"):
        proc.stdin.write("\n")
    proc.stdin.flush()
    proc.stdin.close()

    stdout, stderr, timed_out = _communicate_with_timeout(proc, timeout_s)
    duration_s = round(time.monotonic() - started, 3)
    worktree_after = _git_status(cwd) if readonly_worktree else None
    worktree_changed = (
        readonly_worktree
        and worktree_before is not None
        and worktree_after is not None
        and worktree_after != worktree_before
    )
    ok = proc.returncode == 0 and not timed_out
    if timed_out:
        notes.append("child process timed out and was terminated")
    if worktree_changed:
        ok = False
        notes.append("readonly worktree guard detected file changes")

    receipt = AgentShellReceipt(
        ok=ok,
        mode=mode,
        command=list(command),
        cwd=str(cwd),
        started_at=started_at,
        duration_s=duration_s,
        timeout_s=timeout_s,
        timed_out=timed_out,
        returncode=proc.returncode,
        stdout_tail=_tail(stdout),
        stderr_tail=_tail(stderr),
        receipt_path=str(receipt_path),
        notes=notes,
        readonly_worktree=readonly_worktree,
        worktree_changed=bool(worktree_changed),
        worktree_before=worktree_before,
        worktree_after=worktree_after,
    )
    receipt_path.write_text(json.dumps(asdict(receipt), indent=2), encoding="utf-8")
    return receipt


def _communicate_with_timeout(proc: subprocess.Popen[str], timeout_s: float) -> tuple[str, str, bool]:
    if os.name == "nt":
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
            return stdout, stderr, False
        except subprocess.TimeoutExpired:
            _terminate_tree(proc)
            stdout, stderr = proc.communicate(timeout=5)
            return stdout, stderr, True

    selector = selectors.DefaultSelector()
    assert proc.stdout is not None and proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ)
    selector.register(proc.stderr, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout_s
    chunks = {"stdout": [], "stderr": []}
    stream_names = {proc.stdout: "stdout", proc.stderr: "stderr"}
    timed_out = False
    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            _terminate_tree(proc)
            break
        for key, _event in selector.select(timeout=min(0.2, remaining)):
            data = key.fileobj.readline()
            if data:
                chunks[stream_names[key.fileobj]].append(data)
            else:
                selector.unregister(key.fileobj)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_tree(proc)
    return "".join(chunks["stdout"]), "".join(chunks["stderr"]), timed_out


def _terminate_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, text=True, check=False)
    else:
        proc.kill()


def _json_print(receipt: AgentShellReceipt) -> None:
    print(json.dumps(asdict(receipt), indent=2, ensure_ascii=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=str(REPO_ROOT), help="child working directory")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="show available supervisor configuration")
    probe.add_argument("--model", default=DEFAULT_MODEL)

    run = sub.add_parser("run", help="launch an Ollama integration under supervision")
    run.add_argument("integration", choices=sorted(KNOWN_INTEGRATIONS))
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--task", required=True)
    run.add_argument("--timeout", type=float, default=None, dest="sub_timeout", help="override the global timeout")
    run.add_argument("--readonly-worktree", action="store_true", help="fail the receipt if git status changes")
    run.add_argument("--extra", nargs="*", default=())

    cmd = sub.add_parser("command", help="run an arbitrary child command under the same supervisor")
    cmd.add_argument("--task", required=True)
    cmd.add_argument("--timeout", type=float, default=None, dest="sub_timeout", help="override the global timeout")
    cmd.add_argument("--readonly-worktree", action="store_true", help="fail the receipt if git status changes")
    cmd.add_argument("child_command", nargs=argparse.REMAINDER)

    args = parser.parse_args(list(argv) if argv is not None else None)
    cwd = Path(args.cwd).resolve()
    output_root = Path(args.output_root).resolve()

    if args.command == "probe":
        data = {
            "ok": True,
            "ollama_exe": _ollama_exe(),
            "default_model": args.model,
            "known_integrations": sorted(KNOWN_INTEGRATIONS),
            "output_root": str(output_root),
        }
        print(json.dumps(data, indent=2, ensure_ascii=True))
        return 0

    timeout_s = args.sub_timeout if getattr(args, "sub_timeout", None) is not None else args.timeout

    if args.command == "run":
        command = build_launch_command(args.integration, model=args.model, extra_args=args.extra)
        receipt = run_supervised(
            command,
            task=args.task,
            cwd=cwd,
            timeout_s=timeout_s,
            output_root=output_root,
            mode=f"ollama-{args.integration}",
            readonly_worktree=args.readonly_worktree,
        )
    elif args.command == "command":
        if not args.child_command:
            raise SystemExit("child command is required after 'command'")
        child_command = args.child_command
        if child_command and child_command[0] == "--":
            child_command = child_command[1:]
        receipt = run_supervised(
            child_command,
            task=args.task,
            cwd=cwd,
            timeout_s=timeout_s,
            output_root=output_root,
            mode="command",
            readonly_worktree=args.readonly_worktree,
        )
    else:  # pragma: no cover
        raise SystemExit(f"unknown command {args.command}")

    if args.json:
        _json_print(receipt)
    else:
        status = "OK" if receipt.ok else "FAIL"
        print(f"[{status}] agent-shell {receipt.mode} duration={receipt.duration_s}s receipt={receipt.receipt_path}")
        if receipt.notes:
            print("notes:")
            for note in receipt.notes:
                print(f"- {note}")
        if receipt.stdout_tail:
            print("stdout tail:")
            print(receipt.stdout_tail)
        if receipt.stderr_tail:
            print("stderr tail:")
            print(receipt.stderr_tail)
    return 0 if receipt.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
