#!/usr/bin/env python
from _common import allow, ask, load_payload, pick_first, print_json, write_event
from _policy import HIGH_RISK_SUBAGENT_TYPES, looks_broad_subagent_prompt


def main():
    payload = load_payload()
    subagent_type = pick_first(payload, [("subagent_type",), ("type",), ("agent_type",)])
    prompt = pick_first(payload, [("prompt",), ("task",), ("description",)])
    write_event(
        "subagentStart",
        payload,
        extras={
            "subagent_type": subagent_type,
        },
    )

    if subagent_type in HIGH_RISK_SUBAGENT_TYPES or looks_broad_subagent_prompt(prompt):
        print_json(
            ask(
                "Hook check: subagent request appears high-risk or overly broad. Confirm scope before launch.",
                agent_message=f"subagentStart flagged type='{subagent_type}' prompt='{prompt}'",
            )
        )
        return

    print_json(allow())


if __name__ == "__main__":
    main()
