#!/usr/bin/env python
from _common import allow, load_payload, pick_first, print_json, tool_name, write_summary


def main():
    payload = load_payload()
    status = pick_first(payload, [("status",), ("result", "status"), ("success",)])
    write_summary(
        "afterMCPExecution",
        payload,
        extras={
            "tool": tool_name(payload),
            "status": status,
        },
    )
    print_json(allow())


if __name__ == "__main__":
    main()
