#!/usr/bin/env python
from _common import allow, load_payload, print_json, tool_name, write_event


def main():
    payload = load_payload()
    write_event(
        "postToolUseFailure",
        payload,
        extras={
            "tool": tool_name(payload),
            "outcome": "failure",
        },
    )
    print_json(allow())


if __name__ == "__main__":
    main()
