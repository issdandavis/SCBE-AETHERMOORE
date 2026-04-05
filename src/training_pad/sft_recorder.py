"""SFT Recorder — converts cell histories into oriented training records.

Every cell session becomes multi-turn SFT data showing the process
of coding: write, fail, get feedback, fix, pass. Not just the answer.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from training.auto_marker import orient_record, write_oriented_jsonl, OrientedRecord
from .cell import Cell, CellEvent, EventType


def cell_event_to_instruction(event: CellEvent, cell: Cell) -> tuple[str, str] | None:
    """Convert a single cell event to an instruction/response pair."""

    if event.event_type == EventType.WRITE:
        instruction = f"Write {cell.language} code for a {cell.tongue} task."
        response = event.code_snapshot
        return instruction, response

    elif event.event_type == EventType.RUN:
        instruction = f"Run this {cell.language} code and show the output."
        response = f"```{cell.language}\n{event.code_snapshot}\n```\n\nOutput:\n```\n{event.stdout}\n```"
        if event.stderr:
            response += f"\n\nStderr:\n```\n{event.stderr}\n```"
        return instruction, response

    elif event.event_type == EventType.FAIL:
        instruction = f"This {cell.language} code failed. What went wrong?"
        response = f"```{cell.language}\n{event.code_snapshot}\n```\n\nError:\n```\n{event.error}\n```"
        if event.stderr:
            response += f"\n\nStderr:\n```\n{event.stderr}\n```"
        return instruction, response

    elif event.event_type == EventType.FIX:
        instruction = f"Fix the failing {cell.language} code."
        response = f"Fixed code:\n```{cell.language}\n{event.code_snapshot}\n```"
        return instruction, response

    elif event.event_type == EventType.FEEDBACK:
        if not event.feedback_notes:
            return None
        instruction = f"Review this {cell.language} code for issues."
        notes_text = "\n".join(
            f"- [{n.get('severity', 'info')}] {n.get('message', '')}"
            + (f"\n  Suggestion: {n['suggestion']}" if n.get('suggestion') else "")
            for n in event.feedback_notes
        )
        response = f"```{cell.language}\n{event.code_snapshot}\n```\n\nFindings:\n{notes_text}"
        return instruction, response

    return None


def cell_to_sft_records(cell: Cell) -> list[OrientedRecord]:
    """Convert a cell's full history into oriented SFT records."""
    records = []

    for event in cell.history:
        pair = cell_event_to_instruction(event, cell)
        if pair is None:
            continue
        instruction, response = pair

        if len(response.strip()) < 10:
            continue

        record = orient_record(
            instruction=instruction,
            response=response,
            source=f"training_pad/{cell.cell_id}",
            source_type="training_pad",
            extra_metadata={
                "cell_id": cell.cell_id,
                "cell_tongue": cell.tongue,
                "cell_language": cell.language,
                "cell_status": cell.status.value,
                "event_type": event.event_type.value,
            },
        )
        records.append(record)

    # Multi-turn: full session as a single record (write → fail → feedback → fix → pass)
    if len(cell.history) >= 3:
        session_instruction = f"Complete {cell.language} coding session ({cell.tongue} intent): write, test, debug, and fix code."
        turns = []
        for event in cell.history:
            pair = cell_event_to_instruction(event, cell)
            if pair:
                _, resp = pair
                turns.append(f"[{event.event_type.value}]\n{resp}")

        session_response = "\n\n---\n\n".join(turns)
        if len(session_response) > 50:
            record = orient_record(
                instruction=session_instruction,
                response=session_response,
                source=f"training_pad/{cell.cell_id}",
                source_type="training_pad_session",
                extra_metadata={
                    "cell_id": cell.cell_id,
                    "cell_tongue": cell.tongue,
                    "cell_language": cell.language,
                    "cell_status": cell.status.value,
                    "event_count": len(cell.history),
                    "multi_turn": True,
                },
            )
            records.append(record)

    return records


def export_pad_session(cells: list[Cell], output_path: str | Path, append: bool = True) -> int:
    """Export all cells from a training pad session to JSONL."""
    all_records = []
    for cell in cells:
        all_records.extend(cell_to_sft_records(cell))

    if not all_records:
        return 0

    return write_oriented_jsonl(all_records, output_path, append=append)
