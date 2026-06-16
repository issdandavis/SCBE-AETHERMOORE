"""Mechanical ELIZA support router CLI.

Use this as a secondary support system for chatbots and command agents:

    python scripts/system/mechanical_eliza_support.py "run tests but don't break anything"
    python scripts/system/mechanical_eliza_support.py --text-file request.txt --pretty
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.mechanical_eliza import route_dialogue, route_support


def _read_text(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.text:
        chunks.extend(args.text)
    if args.text_file:
        chunks.append(Path(args.text_file).read_text(encoding="utf-8"))
    if args.stdin:
        chunks.append(sys.stdin.read())
    return "\n".join(chunk for chunk in chunks if chunk is not None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="*", help="Support request text.")
    parser.add_argument(
        "--text-file", help="Read support request text from a UTF-8 file."
    )
    parser.add_argument(
        "--history-file",
        help="Read prior dialogue turns from a UTF-8 file, one turn per line. The request text is appended as the latest turn.",
    )
    parser.add_argument(
        "--stdin", action="store_true", help="Read support request text from stdin."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output."
    )
    parser.add_argument(
        "--response-only",
        action="store_true",
        help="Print only the ELIZA-style support response.",
    )
    args = parser.parse_args(argv)

    text = _read_text(args)
    if args.history_file:
        history = [
            line.strip()
            for line in Path(args.history_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        packet = route_dialogue(history + ([text] if text else []))
    else:
        packet = route_support(text)
    if args.response_only:
        print(packet.response)
        return 0

    indent = 2 if args.pretty else None
    print(json.dumps(packet.as_dict(), indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
