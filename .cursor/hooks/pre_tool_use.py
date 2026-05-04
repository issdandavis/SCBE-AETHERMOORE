#!/usr/bin/env python
from _common import allow, ask, compact_payload, load_payload, print_json, tool_name
from _policy import HIGH_RISK_MCP_NAME, SECRET_PATTERNS, first_match


def main():
    payload = load_payload()
    name = tool_name(payload).lower()
    payload_text = compact_payload(payload, max_chars=4000)

    secret_reason = first_match(payload_text, SECRET_PATTERNS)
    if secret_reason:
        print_json(
            ask(
                f"Hook check: potential secret leak detected in tool input ({secret_reason}). Confirm before continuing.",
                agent_message="Secret-like content found in preToolUse payload.",
            )
        )
        return

    if name and HIGH_RISK_MCP_NAME.search(name):
        print_json(
            ask(
                f"Hook check: tool '{name}' looks high impact. Confirm this call should proceed.",
                agent_message=f"High-impact tool pattern matched for: {name}",
            )
        )
        return

    print_json(allow())


if __name__ == "__main__":
    main()
