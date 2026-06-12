#!/usr/bin/env python3
"""scbe store — unified storage across rclone remotes (gdrive, onedrive, ...).

Safe by default: list / read / pull / copy-up only. This tool NEVER deletes,
purges, or mirrors-with-delete — `rclone copy` is additive, so nothing on either
side is removed (honors the save-first, never-delete data policy). For agents this
is the storage hand: one verb surface over every connected provider, governed.

Subcommands (all accept --json):
  remotes                         list configured remotes
  ls     <remote:path>            list files at a remote path
  pull   <remote:path> <local>    copy DOWN from remote to local (additive)
  push   <local> <remote:path>    copy UP from local to remote (additive)
  check  <local> <remote:path>    verify local vs remote match (read-only)

Run: python scripts/tools/scbe_store.py <subcommand> [args] [--json]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

SCHEMA = "scbe_store_v1"


def _rclone() -> str | None:
    return shutil.which("rclone")


def _run(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _emit(payload: dict, as_json: bool, human_lines: list[str]) -> int:
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        for line in human_lines:
            print(line)
    return 0 if payload.get("ok") else 1


def _need_rclone(as_json: bool) -> dict | None:
    if _rclone():
        return None
    payload = {
        "schema_version": SCHEMA,
        "ok": False,
        "error": "rclone not found on PATH",
        "hint": "Install rclone (https://rclone.org/install) and configure remotes with `rclone config`.",
    }
    _emit(payload, as_json, [f"error: {payload['error']}", f"hint: {payload['hint']}"])
    return payload


def cmd_remotes(args: argparse.Namespace) -> int:
    if _need_rclone(args.json):
        return 1
    rc, out, err = _run([_rclone(), "listremotes"])
    remotes = [r.strip() for r in out.splitlines() if r.strip()]
    payload = {"schema_version": SCHEMA, "ok": rc == 0, "subcommand": "remotes", "remotes": remotes}
    if rc != 0:
        payload["error"] = err.strip()
    return _emit(payload, args.json, [f"remotes ({len(remotes)}):", *[f"  {r}" for r in remotes]])


def cmd_ls(args: argparse.Namespace) -> int:
    if _need_rclone(args.json):
        return 1
    rc, out, err = _run([_rclone(), "lsf", args.remote_path])
    entries = [e.strip() for e in out.splitlines() if e.strip()]
    payload = {
        "schema_version": SCHEMA,
        "ok": rc == 0,
        "subcommand": "ls",
        "remote_path": args.remote_path,
        "entries": entries,
        "count": len(entries),
    }
    if rc != 0:
        payload["error"] = err.strip()
    lines = [f"{args.remote_path} ({len(entries)} entries):", *[f"  {e}" for e in entries[:200]]]
    return _emit(payload, args.json, lines if rc == 0 else [f"error: {err.strip()}"])


def _copy(direction: str, src: str, dst: str, as_json: bool) -> int:
    if _need_rclone(as_json):
        return 1
    # `copy` is additive: it never deletes on the destination.
    rc, out, err = _run([_rclone(), "copy", src, dst, "--stats-one-line", "-v"], timeout=600)
    payload = {
        "schema_version": SCHEMA,
        "ok": rc == 0,
        "subcommand": direction,
        "source": src,
        "dest": dst,
        "mode": "additive_copy_no_delete",
        "log_tail": "\n".join((err or out).strip().splitlines()[-6:]),
    }
    if rc != 0:
        payload["error"] = (err or out).strip()[-400:]
    verdict = "ok" if rc == 0 else "failed"
    return _emit(payload, as_json, [f"{direction} {src} -> {dst}: {verdict}", payload["log_tail"]])


def cmd_pull(args: argparse.Namespace) -> int:
    return _copy("pull", args.remote_path, args.local, args.json)


def cmd_push(args: argparse.Namespace) -> int:
    return _copy("push", args.local, args.remote_path, args.json)


def cmd_check(args: argparse.Namespace) -> int:
    if _need_rclone(args.json):
        return 1
    rc, out, err = _run([_rclone(), "check", args.local, args.remote_path], timeout=300)
    payload = {
        "schema_version": SCHEMA,
        "ok": rc == 0,
        "subcommand": "check",
        "local": args.local,
        "remote_path": args.remote_path,
        "matched": rc == 0,
        "log_tail": "\n".join((err or out).strip().splitlines()[-6:]),
    }
    return _emit(
        payload,
        args.json,
        [f"check {args.local} vs {args.remote_path}: {'match' if rc == 0 else 'differs'}", payload["log_tail"]],
    )


def build_parser() -> argparse.ArgumentParser:
    # Shared parent so --json works in BOTH positions (before or after the subcommand).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    ap = argparse.ArgumentParser(
        prog="scbe store",
        description="Unified governed storage over rclone remotes.",
        parents=[common],
    )
    sub = ap.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("remotes", help="list configured remotes", parents=[common]).set_defaults(func=cmd_remotes)

    p_ls = sub.add_parser("ls", help="list files at a remote path", parents=[common])
    p_ls.add_argument("remote_path")
    p_ls.set_defaults(func=cmd_ls)

    p_pull = sub.add_parser("pull", help="copy DOWN from remote to local (additive)", parents=[common])
    p_pull.add_argument("remote_path")
    p_pull.add_argument("local")
    p_pull.set_defaults(func=cmd_pull)

    p_push = sub.add_parser("push", help="copy UP from local to remote (additive)", parents=[common])
    p_push.add_argument("local")
    p_push.add_argument("remote_path")
    p_push.set_defaults(func=cmd_push)

    p_check = sub.add_parser("check", help="verify local vs remote match (read-only)", parents=[common])
    p_check.add_argument("local")
    p_check.add_argument("remote_path")
    p_check.set_defaults(func=cmd_check)
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except subprocess.TimeoutExpired:
        payload = {"schema_version": SCHEMA, "ok": False, "error": "rclone timed out"}
        return _emit(payload, getattr(args, "json", False), ["error: rclone timed out"])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
