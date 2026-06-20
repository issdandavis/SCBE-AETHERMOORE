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

from python.scbe.mechanical_eliza import (
    build_choicescript_navigation,
    build_free_llm_dispatch_request,
    build_semantic_navigation,
    route_dialogue,
    route_support,
)


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
    parser.add_argument("--text-file", help="Read support request text from a UTF-8 file.")
    parser.add_argument(
        "--history-file",
        help=(
            "Read prior dialogue turns from a UTF-8 file, one turn per line. "
            "The request text is appended as the latest turn."
        ),
    )
    parser.add_argument("--stdin", action="store_true", help="Read support request text from stdin.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument(
        "--response-only",
        action="store_true",
        help="Print only the ELIZA-style support response.",
    )
    parser.add_argument(
        "--choicescript",
        action="store_true",
        help="Print a ChoiceScript-style navigation scene.",
    )
    parser.add_argument(
        "--semantic-map",
        action="store_true",
        help="Print the semantic navigation array.",
    )
    parser.add_argument(
        "--free-llm-request",
        action="store_true",
        help="Include a Free LLM dispatch request in the JSON.",
    )
    parser.add_argument(
        "--dispatch-free-llm",
        action="store_true",
        help="Call the repo's Free LLM dispatcher after ELIZA routes.",
    )
    parser.add_argument(
        "--provider",
        default="offline",
        help="Free LLM provider id for request/dispatch.",
    )
    parser.add_argument("--model", default=None, help="Optional model override for Free LLM routing.")
    parser.add_argument(
        "--live-model",
        action="store_true",
        help="Actually call the selected provider. Without this, dispatch uses dry-run.",
    )
    args = parser.parse_args(argv)

    text = _read_text(args)
    if args.history_file:
        history = [
            line.strip() for line in Path(args.history_file).read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        packet = route_dialogue(history + ([text] if text else []))
    else:
        packet = route_support(text)
    if args.response_only:
        print(packet.response)
        return 0
    if args.choicescript:
        print(build_choicescript_navigation(packet))
        return 0
    if args.semantic_map:
        print(
            json.dumps(
                build_semantic_navigation(packet),
                indent=2 if args.pretty else None,
                sort_keys=True,
            )
        )
        return 0

    indent = 2 if args.pretty else None
    payload = packet.as_dict()
    if args.free_llm_request or args.dispatch_free_llm:
        payload["free_llm_bridge"] = build_free_llm_dispatch_request(
            packet,
            provider=args.provider,
            model=args.model,
            dry_run=not args.live_model,
        )
    if args.dispatch_free_llm:
        from src.api import free_llm_routes

        dispatch = payload["free_llm_bridge"]["dispatch"]
        payload["free_llm_result"] = free_llm_routes.dispatch_free_llm_request(
            free_llm_routes.FreeLLMDispatchRequest(**dispatch),
            user="mechanical-eliza",
            origin="inside",
        )
    print(json.dumps(payload, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
