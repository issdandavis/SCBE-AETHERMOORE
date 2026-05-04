#!/usr/bin/env python
from _common import allow, ask, compact_payload, load_payload, print_json, tool_name
from _policy import HIGH_RISK_MCP_NAME, SECRET_PATTERNS, first_match


def main():
    payload = load_payload()
    name = tool_name(payload)
    if name and HIGH_RISK_MCP_NAME.search(name):
        print_json(
            ask(
                f"Hook check: MCP tool '{name}' appears high risk. Confirm intent before execution.",
                agent_message=f"High-risk MCP name matched: {name}",
            )
        )
        return

    payload_text = compact_payload(payload, max_chars=3000)
    secret_reason = first_match(payload_text, SECRET_PATTERNS)
    if secret_reason:
        print_json(
            ask(
                f"Hook check: possible secret exposure detected ({secret_reason}). Confirm safe handling.",
                agent_message="Secret-like value found in MCP request payload.",
            )
        )
        return

    print_json(allow())


if __name__ == "__main__":
    main()
