"""Convert Claude Code session logs to SFT training pairs for Polly.

Reads .jsonl session logs from ~/.claude/projects/*, extracts user->assistant
message pairs, filters for quality, and outputs SCBE-formatted SFT records.
"""
import json
import os
from pathlib import Path


SESSION_DIR = Path(os.path.expanduser("~")) / ".claude" / "projects" / "C--Users-issda-SCBE-AETHERMOORE"
OUTPUT = Path("training-data/sft/claude_sessions_sft.jsonl")

# Skip messages shorter than this (low signal)
MIN_USER_LEN = 10
MIN_ASSISTANT_LEN = 50
# Skip messages longer than this (too much noise / tool output)
MAX_ASSISTANT_LEN = 4000


def extract_text(content):
    """Extract plain text from message content (string or content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def process_session(session_file):
    """Extract user->assistant pairs from a session log."""
    pairs = []
    entries = []

    with open(session_file, "r", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("type") in ("user", "assistant"):
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    # Pair consecutive user->assistant messages
    i = 0
    while i < len(entries) - 1:
        if entries[i].get("type") == "user" and entries[i + 1].get("type") == "assistant":
            user_msg = extract_text(entries[i].get("message", {}).get("content", ""))
            asst_msg = extract_text(entries[i + 1].get("message", {}).get("content", ""))

            # Quality filters
            if len(user_msg) >= MIN_USER_LEN and MIN_ASSISTANT_LEN <= len(asst_msg) <= MAX_ASSISTANT_LEN:
                # Skip if mostly tool calls / code output
                if not asst_msg.startswith("{") and "tool_use" not in asst_msg[:100]:
                    pairs.append({
                        "messages": [
                            {"role": "system", "content": "You are Polly, the SCBE-AETHERMOORE AI assistant. You help users understand and work with the SCBE AI safety and governance framework."},
                            {"role": "user", "content": user_msg.strip()},
                            {"role": "assistant", "content": asst_msg.strip()},
                        ],
                        "source": f"claude_session_{session_file.stem[:8]}",
                        "timestamp": entries[i].get("timestamp", ""),
                    })
            i += 2
        else:
            i += 1

    return pairs


def main():
    sessions = sorted(SESSION_DIR.glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    print(f"Found {len(sessions)} session logs in {SESSION_DIR}")

    all_pairs = []
    for s in sessions:
        size_mb = s.stat().st_size / 1024 / 1024
        pairs = process_session(s)
        print(f"  {s.name[:12]}... ({size_mb:.1f} MB) -> {len(pairs)} pairs")
        all_pairs.extend(pairs)

    # Deduplicate by user message content
    seen = set()
    unique_pairs = []
    for p in all_pairs:
        key = p["messages"][1]["content"][:200]
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for p in unique_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_pairs)} pairs -> {len(unique_pairs)} unique")
    print(f"Saved to {OUTPUT}")

    # Also show stats on existing training data
    existing = Path("training-data/sft/polly_combined_sft.jsonl")
    if existing.exists():
        with open(existing) as f:
            existing_count = sum(1 for _ in f)
        print(f"Existing Polly SFT: {existing_count} records")
        print(f"New from sessions: {len(unique_pairs)} records")
        print(f"Combined potential: {existing_count + len(unique_pairs)} records")


if __name__ == "__main__":
    main()
