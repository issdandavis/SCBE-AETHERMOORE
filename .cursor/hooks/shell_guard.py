#!/usr/bin/env python
from _common import ask, deny, load_payload, pick_first, print_json
from _policy import (
    DESTRUCTIVE_SHELL_RULES,
    NETWORK_EXFIL_RULES,
    first_match,
)


HARD_DENY_MARKERS = ("format ", " shutdown /", "shutdown /")


def extract_command(payload):
    return pick_first(
        payload,
        [
            ("command",),
            ("raw_command",),
            ("input",),
            ("arguments", "command"),
            ("arguments", "raw_command"),
        ],
    )


def main():
    payload = load_payload()
    command = extract_command(payload)
    lowered = command.lower()
    if any(marker in lowered for marker in HARD_DENY_MARKERS):
        print_json(
            deny(
                "Hook blocked this shell command because it can cause immediate host or disk damage.",
                agent_message=f"Blocked shell command: {command}",
            )
        )
        return

    destructive_reason = first_match(command, DESTRUCTIVE_SHELL_RULES)
    if destructive_reason:
        print_json(
            ask(
                f"Hook check: shell command may be destructive ({destructive_reason}). Confirm before running.",
                agent_message=f"Destructive shell pattern matched: {command}",
            )
        )
        return

    exfil_reason = first_match(command, NETWORK_EXFIL_RULES)
    if exfil_reason:
        print_json(
            ask(
                f"Hook check: potential network exfil risk ({exfil_reason}). Confirm destination and scope.",
                agent_message=f"Network-aware shell pattern matched: {command}",
            )
        )
        return

    print_json({"permission": "allow"})


if __name__ == "__main__":
    main()
