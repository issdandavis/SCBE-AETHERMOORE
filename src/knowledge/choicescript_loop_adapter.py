"""ChoiceScript Loop Adapter for SCBE Library Wing.

Repurposes game session JSONL events into deterministic training episodes
without depending on proprietary ChoiceScript runtime internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import json


@dataclass
class ChoiceEpisode:
    episode_id: str
    session_file: str
    event_type: str
    prompt: str
    response: str
    metadata: dict[str, Any]


class ChoiceScriptLoopAdapter:
    """Reads branch events and emits model-training-ready episodes."""

    def __init__(self, sessions_root: Path):
        self.sessions_root = Path(sessions_root)

    def session_files(self, limit: int = 50) -> list[Path]:
        files = sorted(self.sessions_root.glob("*.jsonl"))
        return files[: max(0, limit)]

    def iter_episodes(self, file_limit: int = 25) -> Iterable[ChoiceEpisode]:
        for path in self.session_files(limit=file_limit):
            with path.open("r", encoding="utf-8") as fh:
                for idx, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield ChoiceEpisode(
                        episode_id=f"{path.stem}:{idx}",
                        session_file=str(path),
                        event_type=str(row.get("event_type", "unknown")),
                        prompt=str(row.get("prompt", "")),
                        response=str(row.get("response", "")),
                        metadata=row.get("metadata", {}),
                    )

    def export_sft_jsonl(self, output_path: Path, file_limit: int = 25) -> int:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output_path.open("w", encoding="utf-8") as out:
            for ep in self.iter_episodes(file_limit=file_limit):
                rec = {
                    "id": ep.episode_id,
                    "prompt": ep.prompt,
                    "response": ep.response,
                    "metadata": {
                        "event_type": ep.event_type,
                        "session_file": ep.session_file,
                        **(ep.metadata or {}),
                    },
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                count += 1
        return count

    @staticmethod
    def episode_to_note(ep: ChoiceEpisode) -> str:
        """Compact note line for round-table lane synthesis."""
        tongue = ""
        if isinstance(ep.metadata, dict):
            tongue = str(ep.metadata.get("tongue", "")).strip()
        prefix = f"[{ep.event_type.upper()}]"
        if tongue:
            prefix += f"[{tongue}]"
        return f"{prefix} {ep.prompt[:140]} -> {ep.response[:140]}"

    def export_notes(self, output_path: Path, max_notes: int = 200, file_limit: int = 25) -> int:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with output_path.open("w", encoding="utf-8") as out:
            for ep in self.iter_episodes(file_limit=file_limit):
                out.write(self.episode_to_note(ep) + "\n")
                written += 1
                if written >= max_notes:
                    break
        return written
