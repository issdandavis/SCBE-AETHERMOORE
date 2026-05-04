#!/usr/bin/env python
from _common import allow, load_payload, pick_first, print_json, write_summary


def build_hint(path: str) -> str:
    if path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
        return "Edited code file detected. Consider running focused tests and formatter checks."
    if path.endswith((".json", ".yaml", ".yml", ".toml")):
        return "Edited config file detected. Consider validating schema or parser compatibility."
    return "Edit recorded. Consider running the smallest relevant validation command."


def main():
    payload = load_payload()
    path = pick_first(
        payload,
        [
            ("path",),
            ("file_path",),
            ("target_file",),
            ("arguments", "path"),
        ],
    )
    write_summary("afterFileEdit", payload, extras={"path": path})
    # additional_context is only used by events that support it.
    print_json(allow(extra={"additional_context": build_hint(path)}))


if __name__ == "__main__":
    main()
