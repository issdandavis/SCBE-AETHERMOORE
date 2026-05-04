#!/usr/bin/env python
from _common import allow, load_payload, pick_first, print_json, write_summary


def main():
    payload = load_payload()
    command = pick_first(
        payload,
        [
            ("command",),
            ("raw_command",),
            ("arguments", "command"),
        ],
    )
    exit_code = pick_first(payload, [("exit_code",), ("result", "exit_code"), ("status",)])
    write_summary(
        "afterShellExecution",
        payload,
        extras={
            "command": command,
            "exit_code": exit_code,
        },
    )
    print_json(allow())


if __name__ == "__main__":
    main()
