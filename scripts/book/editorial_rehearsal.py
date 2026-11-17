"""Validate the staged Six Tongues reader/writer/continuity rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = REPO_ROOT / "content" / "book" / "editorial" / "rehearsal-plan.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_plan(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def receipt_path(repo_root: Path, cycle: str, role: str, block_id: str) -> Path:
    return repo_root / "content" / "book" / "editorial" / cycle / role / f"{block_id}.md"


def validate_plan(plan: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    bounds = plan.get("chapter_bounds", {})
    minimum = int(bounds.get("minimum", 2))
    maximum = int(bounds.get("maximum", 3))
    seen_chapters: set[int] = set()
    seen_ids: set[str] = set()

    if plan.get("role_order") != ["fresh-reader", "writer", "continuity"]:
        errors.append("role_order must be fresh-reader -> writer -> continuity")

    for block in plan.get("blocks", []):
        block_id = str(block.get("id", ""))
        chapters = [int(chapter) for chapter in block.get("chapters", [])]
        if not block_id or block_id in seen_ids:
            errors.append(f"duplicate or empty block id: {block_id!r}")
        seen_ids.add(block_id)

        if not minimum <= len(chapters) <= maximum:
            errors.append(f"{block_id}: expected {minimum}-{maximum} chapters, got {len(chapters)}")
        overlap = seen_chapters.intersection(chapters)
        if overlap:
            errors.append(f"{block_id}: overlaps chapters {sorted(overlap)}")
        seen_chapters.update(chapters)

        if block.get("reader_actor") != block.get("writer_actor"):
            errors.append(f"{block_id}: the fresh reader must graduate into writer for the same block")
        if block.get("continuity_actor") == block.get("writer_actor"):
            errors.append(f"{block_id}: continuity keeper must be independent from the writer")

        sources = block.get("sources", [])
        if len(sources) != len(chapters):
            errors.append(f"{block_id}: expected one pinned source per chapter")
        for source in sources:
            relative = Path(str(source.get("path", "")))
            expected = str(source.get("sha256", "")).lower()
            absolute = repo_root / relative
            if not absolute.is_file():
                errors.append(f"{block_id}: missing source {relative.as_posix()}")
                continue
            actual = sha256(absolute)
            if actual != expected:
                errors.append(f"{block_id}: source drift {relative.as_posix()} expected {expected} got {actual}")
    return errors


def verify_receipt_chain(
    plan: dict[str, Any], repo_root: Path, require_complete: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    statuses: list[dict[str, Any]] = []
    errors: list[str] = []
    cycle = str(plan["cycle"])

    for block in plan["blocks"]:
        block_id = str(block["id"])
        reader = receipt_path(repo_root, cycle, "fresh-reader", block_id)
        writer = receipt_path(repo_root, cycle, "writer", block_id)
        continuity = receipt_path(repo_root, cycle, "continuity", block_id)
        state = "UNREAD"

        if reader.is_file():
            state = "FRESH_READER"
        if writer.is_file():
            if not reader.is_file():
                errors.append(f"{block_id}: writer receipt exists without a fresh-reader receipt")
            else:
                reader_hash = sha256(reader)
                writer_text = writer.read_text(encoding="utf-8").lower()
                if reader_hash not in writer_text:
                    errors.append(f"{block_id}: writer receipt does not bind fresh-reader hash {reader_hash}")
                state = "WRITER"
        if continuity.is_file():
            if not writer.is_file():
                errors.append(f"{block_id}: continuity receipt exists without a writer receipt")
            else:
                writer_hash = sha256(writer)
                continuity_text = continuity.read_text(encoding="utf-8").lower()
                if writer_hash not in continuity_text:
                    errors.append(f"{block_id}: continuity receipt does not bind writer hash {writer_hash}")
                state = "CONTINUITY_REVIEWED"

        if require_complete and state != "CONTINUITY_REVIEWED":
            errors.append(f"{block_id}: incomplete receipt chain (current state {state})")

        statuses.append(
            {
                "block": block_id,
                "chapters": block["chapters"],
                "state": state,
                "reader": block["reader_actor"],
                "writer": block["writer_actor"],
                "continuity_keeper": block["continuity_actor"],
            }
        )
    return statuses, errors


def run(command: str, plan_path: Path) -> int:
    plan_path = plan_path.resolve()
    repo_root = plan_path.parents[3]
    plan = load_plan(plan_path)
    errors = validate_plan(plan, repo_root)
    statuses, receipt_errors = verify_receipt_chain(plan, repo_root, require_complete=command == "verify")
    errors.extend(receipt_errors)

    if command in {"status", "verify"}:
        print(
            json.dumps(
                {
                    "cycle": plan["cycle"],
                    "authority": plan["authority"],
                    "blocks": statuses,
                },
                indent=2,
            )
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {len(plan['blocks'])} blocks; source hashes and role invariants hold")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "status", "verify"))
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()
    return run(args.command, args.plan)


if __name__ == "__main__":
    raise SystemExit(main())
