#!/usr/bin/env python
from _common import allow, ask, compact_payload, load_payload, print_json
from _policy import SECRET_PATTERNS, first_match


def main():
    payload = load_payload()
    prompt_text = compact_payload(payload, max_chars=7000)
    secret_reason = first_match(prompt_text, SECRET_PATTERNS)
    if secret_reason:
        print_json(
            ask(
                f"Hook check: possible secret found in prompt ({secret_reason}). Confirm before sending.",
                agent_message="beforeSubmitPrompt secret heuristic matched.",
            )
        )
        return
    print_json(allow())


if __name__ == "__main__":
    main()
