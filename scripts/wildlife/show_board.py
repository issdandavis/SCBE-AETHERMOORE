"""Render the Wildlife Board as a Go-style ASCII view, grouped by pack.

Reads `.scbe/wildlife/board.json` (or path given by --board) and prints:

  - Totals row (each pack with current count, breeding flag if applicable)
  - Per-pack grids with each animal as a stone:
        ●  = trapped (0 liberties - must tame or it dies)
        ◐  = pressed (1-2 liberties)
        ○  = breathing (3+ liberties)
  - Tame command for the most-urgent animal in each pack

Usage:
    python scripts/wildlife/show_board.py
    python scripts/wildlife/show_board.py --pack wolves
    python scripts/wildlife/show_board.py --board /tmp/board.json --max 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.wildlife.packs import PACKS, severity_order  # noqa: E402

DEFAULT_BOARD = ROOT / ".scbe" / "wildlife" / "board.json"


USE_UNICODE = False  # set in main() based on --unicode flag


def stone(liberties: int) -> str:
    if USE_UNICODE:
        if liberties <= 0:
            return "●"  # trapped
        if liberties <= 2:
            return "◐"  # pressed
        return "○"  # breathing
    if liberties <= 0:
        return "X"  # trapped
    if liberties <= 2:
        return "o"  # pressed
    return "."  # breathing


def format_grid(animals: list[dict], width: int = 24) -> list[str]:
    """Lay out stones in a grid, max `width` per line. Each stone is 1 char + 1 space."""
    cells = [stone(a.get("liberties", 0)) for a in animals]
    lines: list[str] = []
    for i in range(0, len(cells), width):
        row = " ".join(cells[i : i + width])
        lines.append(row)
    return lines


def render(board: dict, only_pack: str | None, max_per_pack: int) -> str:
    out_lines: list[str] = []
    out_lines.append(f"Wildlife Board - harvested {board.get('harvested_at','?')}")
    out_lines.append("=" * 64)

    totals = board.get("totals", {})
    breeding = board.get("breeding_now", {})
    total_animals = sum(totals.values())
    out_lines.append(f"  Total animals on board: {total_animals}")

    summary_parts = []
    for pname in severity_order():
        plural = PACKS[pname].plural
        n = totals.get(plural, 0)
        if n == 0:
            continue
        marker = "!" if plural in breeding else " "
        summary_parts.append(f"{marker}{plural}={n}")
    out_lines.append("  " + "  ".join(summary_parts))

    if breeding:
        out_lines.append("")
        out_lines.append("  BREEDING NOW:")
        for plural, info in breeding.items():
            out_lines.append(f"    {plural} ({info['count']} > {info['threshold']}): {info['rule']}")

    out_lines.append("")
    if USE_UNICODE:
        out_lines.append("  Stone legend:  ● trapped   ◐ pressed   ○ breathing")
    else:
        out_lines.append("  Stone legend:  X trapped   o pressed   . breathing")
    out_lines.append("")

    packs_section = board.get("packs", {})
    for pname in severity_order():
        pack = PACKS[pname]
        if only_pack and only_pack.lower() not in (pack.plural.lower(), pack.animal.lower()):
            continue
        animals = packs_section.get(pack.plural, [])
        if not animals:
            continue

        out_lines.append("-" * 64)
        marker = " [BREEDING]" if pack.plural in breeding else ""
        out_lines.append(f"  {pack.plural.upper()} ({len(animals)}) - skill: {pack.skill}{marker}")
        if pack.breeding_threshold is not None:
            out_lines.append(f"    breeding threshold: {pack.breeding_threshold} - {pack.breeding_rule}")
        out_lines.append(f"    tame hint: {pack.tame_hint}")
        out_lines.append("")

        for line in format_grid(animals):
            out_lines.append("    " + line)

        out_lines.append("")
        # Show top-N most urgent (lowest liberties)
        urgent = animals[:max_per_pack]
        for a in urgent:
            url = a.get("url") or a.get("path") or ""
            out_lines.append(f"    {stone(a.get('liberties',0))} {a.get('id','?'):<32s} {a.get('title','')[:80]}")
            if url:
                out_lines.append(f"        {url}")
        if len(animals) > max_per_pack:
            out_lines.append(f"    ... +{len(animals)-max_per_pack} more (run with --max {len(animals)} to see all)")

        # Show bus command for the most urgent
        if urgent:
            out_lines.append("")
            out_lines.append(f"    next move (most urgent):")
            out_lines.append(f"      $ {urgent[0].get('tame_command','')}")
        out_lines.append("")

    return "\n".join(out_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--board", default=str(DEFAULT_BOARD), help="path to board.json")
    parser.add_argument("--pack", default=None, help="restrict to one pack (e.g. wolves, sheep, dragons)")
    parser.add_argument("--max", type=int, default=5, dest="max_per_pack", help="max detail rows per pack")
    parser.add_argument(
        "--unicode",
        action="store_true",
        help="use ●◐○ stone glyphs (UTF-8 terminal required; Windows cmd usually breaks)",
    )
    args = parser.parse_args()
    global USE_UNICODE
    USE_UNICODE = bool(args.unicode)

    board_path = Path(args.board)
    if not board_path.exists():
        print(
            f"[wildlife] no board at {board_path} - run " f"`python scripts/wildlife/harvest_packs.py` first.",
            file=sys.stderr,
        )
        return 1

    board = json.loads(board_path.read_text(encoding="utf-8"))
    print(render(board, args.pack, args.max_per_pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
