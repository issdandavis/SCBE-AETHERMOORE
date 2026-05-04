#!/usr/bin/env python
from _common import allow, load_payload, pick_first, print_json, write_event


def main():
    payload = load_payload()
    write_event(
        "subagentStop",
        payload,
        extras={
            "subagent_type": pick_first(payload, [("subagent_type",), ("type",), ("agent_type",)]),
            "status": pick_first(payload, [("status",), ("result",)]),
        },
    )
    print_json(allow())


if __name__ == "__main__":
    main()
