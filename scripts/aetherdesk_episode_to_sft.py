"""Convert AetherDesk trace events into computer-use SFT rows.

Input: JSONL exported by AetherDesk's local trace recorder.
Output: JSONL rows using messages + metadata, suitable for later curation.

This script does not train, upload, or publish anything.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ACTION_TYPES = {
    "desktop.open_app",
    "skill.open",
    "browser.tool_post",
    "terminal.submit",
    "powershell.run",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
      for line_no, line in enumerate(handle, 1):
          line = line.strip()
          if not line:
              continue
          try:
              rows.append(json.loads(line))
          except json.JSONDecodeError as exc:
              raise SystemExit(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
    return rows


def compact(value: Any, limit: int = 1600) -> str:
    text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def rows_to_sft(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_episode[event.get("episode_id") or "unknown"].append(event)

    out: list[dict[str, Any]] = []
    for episode_id, episode_events in by_episode.items():
        episode_events.sort(key=lambda item: item.get("timestamp", ""))
        prior: list[dict[str, Any]] = []
        for event in episode_events:
            event_type = event.get("type", "")
            payload = event.get("payload", {})
            if event_type not in ACTION_TYPES:
                prior.append(event)
                continue

            observation = {
                "recent_events": prior[-5:],
                "current_event_type": event_type,
                "current_payload": payload,
            }
            answer = {
                "schema": "aetherdesk.action.training.v1",
                "type": event_type,
                "action": payload,
                "stop_rules": [
                    "no-secret-exposure",
                    "no-delete-without-approval",
                    "no-publish-without-approval",
                    "no-paid-job-without-approval",
                ],
            }
            out.append({
                "messages": [
                    {
                        "role": "system",
                        "content": "You are the AetherDesk computer-use agent. Output only safe JSON action packets grounded in the observed desktop state.",
                    },
                    {
                        "role": "user",
                        "content": "Choose the next safe AetherDesk action from this observation:\n" + compact(observation),
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(answer, ensure_ascii=True, sort_keys=True),
                    },
                ],
                "metadata": {
                    "source_type": "aetherdesk_trace",
                    "episode_id": episode_id,
                    "event_type": event_type,
                    "provenance": "human_or_agent_demo",
                    "validated": False,
                    "requires_curation": True,
                },
            })
            prior.append(event)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="AetherDesk trace JSONL export")
    parser.add_argument("-o", "--output", type=Path, default=Path("training-data/sft/aetherdesk_computer_use_from_traces.sft.jsonl"))
    args = parser.parse_args()

    events = load_jsonl(args.input)
    rows = rows_to_sft(events)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    print(json.dumps({"events": len(events), "sft_rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
