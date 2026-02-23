"""Automatic byproduct note logging for Obsidian vaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class ByproductLogger:
    vault_root: Path

    def log(self, title: str, summary: str, files: Iterable[str] = (), next_steps: Iterable[str] = ()) -> Path:
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        ts = now.strftime("%H%M%S")

        folder = self.vault_root / "SCBE-Hub" / "Worklog" / day
        folder.mkdir(parents=True, exist_ok=True)

        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in title).strip("-")
        if not safe:
            safe = "work-note"

        path = folder / f"{ts}-{safe}.md"

        lines = [
            f"# {title}",
            "",
            f"- timestamp_utc: {now.isoformat()}",
            "",
            "## Summary",
            summary,
            "",
            "## Files",
        ]

        files_list = list(files)
        if files_list:
            for f in files_list:
                lines.append(f"- `{f}`")
        else:
            lines.append("- (none listed)")

        lines.append("")
        lines.append("## Next Steps")
        next_list = list(next_steps)
        if next_list:
            for step in next_list:
                lines.append(f"- {step}")
        else:
            lines.append("- (none)")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
