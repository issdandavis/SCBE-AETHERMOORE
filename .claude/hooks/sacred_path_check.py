"""PostToolUse hook: detect edits to sacred paths and inject dry-run-specialist context."""
import json
import re
import sys

SACRED_PATTERN = re.compile(r"src/(harmonic|symphonic_cipher|ca_lexicon|geoseal_cli)")

try:
    data = json.load(sys.stdin)
except Exception:
    print("{}")
    sys.exit(0)

file_path = (
    data.get("tool_input", {}).get("file_path", "")
    or data.get("tool_response", {}).get("filePath", "")
)
normalized = file_path.replace("\\", "/")

if SACRED_PATTERN.search(normalized):
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"Sacred-path file edited: {file_path}. "
                "Consider invoking the dry-run-specialist agent to verify "
                "cross-tongue parity via geoseal_cli swarm dispatch."
            ),
        }
    }
    print(json.dumps(result))
else:
    print("{}")
