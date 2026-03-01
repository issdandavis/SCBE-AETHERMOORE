#!/usr/bin/env python3
"""Local SCBE secret store utility.

Stores secrets in a tokenized local file so they are not kept in source code or
printed during normal process runs. Use this to write/read secrets for local
laptop use.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import os
import subprocess
from getpass import getpass
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.security.secret_store import get_secret, list_secret_names, remove_secret, set_secret, store_path


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _shell_quote_ps(value: str) -> str:
    safe = value.replace("'", "''")
    return f"'{safe}'"


def _shell_quote_bash(value: str) -> str:
    safe = value.replace("'", "'\\''")
    return f"'{safe}'"


def _pick_secret_names_from_file(path: str) -> list[str]:
    out: list[str] = []
    if not path:
        return out
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                token = line.strip()
                if token:
                    out.append(token)
    except OSError:
        return []
    return out


def _load_env_overlay(names: list[str] | None = None) -> dict[str, str]:
    secrets = list_secret_names()
    if names:
        selected = [n for n in names if n in secrets]
    else:
        selected = secrets

    env = os.environ.copy()
    for name in selected:
        value = get_secret(name, "")
        if value:
            env[name] = value
    return env


def _read_value_from_stdin(prompt: str) -> str:
    if sys.stdin.isatty():
        return getpass(prompt)
    return sys.stdin.read().strip()


def cmd_list(args: argparse.Namespace) -> int:
    secrets = list_secret_names()
    if args.names_only:
        for name in secrets:
            print(name)
        return 0

    _print_json(
        {
            "store_path": store_path(),
            "count": len(secrets),
            "secrets": secrets,
        }
    )
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    value = get_secret(args.name, "")
    if not value:
        print(f"[SCBE] secret not found: {args.name}", file=sys.stderr)
        return 1
    print(value)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    if not args.name:
        print("[SCBE] --name and --value required", file=sys.stderr)
        return 1
    value = args.value
    if value is None or args.stdin:
        value = _read_value_from_stdin(f"[SCBE] secret value for {args.name}: ")

    if not value:
        print("[SCBE] no secret value provided", file=sys.stderr)
        return 1

    if args.stdin:
        value = value.rstrip("\r\n")

    set_secret(args.name, value, note=args.note or "")
    print(f"[SCBE] stored: {args.name}")
    print(f"[SCBE] store: {store_path()}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    names = _pick_secret_names_from_file(args.names_file)
    secrets = list_secret_names()
    selected = [n for n in secrets if n in names] if names else secrets
    shell = (args.shell or "powershell").lower()

    lines: list[str] = []
    for name in selected:
        value = get_secret(name, "")
        if not value:
            continue
        if shell == "bash":
            lines.append(f"export {name}={_shell_quote_bash(value)}")
        elif shell == "cmd":
            lines.append(f"set {name}={value}")
        else:
            lines.append(f"$env:{name}={_shell_quote_ps(value)}")

    if not lines:
        print("[SCBE] no decodeable secrets found", file=sys.stderr)
        return 1

    if args.format_json:
        payload = {name: get_secret(name, "") for name in selected}
        _print_json(payload)
    else:
        print("\\n".join(lines))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    command = [c for c in args.command if c]
    if not command:
        print("[SCBE] command is required", file=sys.stderr)
        return 1

    env = _load_env_overlay(_pick_secret_names_from_file(args.names_file))
    completed = subprocess.run(
        command,
        env=env,
        cwd=args.cwd or None,
        check=False,
    )
    return int(completed.returncode)


def cmd_remove(args: argparse.Namespace) -> int:
    removed = remove_secret(args.name)
    if not removed:
        print(f"[SCBE] secret not found: {args.name}", file=sys.stderr)
        return 1
    print(f"[SCBE] removed: {args.name}")
    return 0


def cmd_path(_: argparse.Namespace) -> int:
    print(store_path())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage tokenized local SCBE secrets.")
    parser.add_argument("--root", default=str(ROOT), help="Optional repo root override.")
    subs = parser.add_subparsers(dest="command", required=True)

    list_parser = subs.add_parser("list", help="List secret names.")
    list_parser.add_argument("--names-only", action="store_true", dest="names_only")
    list_parser.set_defaults(func=cmd_list)

    get_parser = subs.add_parser("get", help="Read and decode a stored secret.")
    get_parser.add_argument("name")
    get_parser.set_defaults(func=cmd_get)

    set_parser = subs.add_parser("set", help="Tokenize and store a secret.")
    set_parser.add_argument("name")
    set_parser.add_argument("value", nargs="?")
    set_parser.add_argument("--stdin", action="store_true", help="Read value from stdin")
    set_parser.add_argument("--note", default="", help="Optional note for this secret.")
    set_parser.set_defaults(func=cmd_set)

    rm_parser = subs.add_parser("remove", help="Delete a secret record.")
    rm_parser.add_argument("name")
    rm_parser.set_defaults(func=cmd_remove)

    path_parser = subs.add_parser("path", help="Print secret store path.")
    path_parser.set_defaults(func=cmd_path)

    export_parser = subs.add_parser("export", help="Print shell-ready env assignments.")
    export_parser.add_argument(
        "--shell",
        default="powershell",
        choices=["powershell", "bash", "cmd"],
        help="Shell target output",
    )
    export_parser.add_argument(
        "--names-file",
        default="",
        help="Optional file with one secret name per line",
    )
    export_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON map instead of shell lines",
    )
    export_parser.set_defaults(func=cmd_export)

    run_parser = subs.add_parser("run", help="Run command with local secrets injected")
    run_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    run_parser.add_argument("--cwd", default="", help="Working directory for command")
    run_parser.add_argument(
        "--names-file",
        default="",
        help="Optional file with one secret name per line",
    )
    run_parser.set_defaults(func=cmd_run)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    env_root = os.getenv("SCBE_REPO_ROOT", "")
    if env_root:
        override = Path(env_root)
        if override.is_dir() and str(override) not in sys.path:
            sys.path.insert(0, str(override))
    raise SystemExit(main())
