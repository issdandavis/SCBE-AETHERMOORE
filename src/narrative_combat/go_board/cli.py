from __future__ import annotations

import argparse
import json
from pathlib import Path

from .director import GoDirector
from .fixtures import boss_board_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Go-board narrative fight packet.")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--translator",
        choices=["template", "llm"],
        default="template",
        help="template = deterministic (default); llm = prose via Ollama, falls back to template",
    )
    parser.add_argument("--style", default=None, help="override prose style for the llm translator")
    parser.add_argument("--model", default="glm-5.1:cloud", help="Ollama model for the llm translator")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    encounter = boss_board_demo(seed=args.seed)
    translator = None
    if args.translator == "llm":
        from .translator import GoLLMTranslator

        translator = GoLLMTranslator(
            model=args.model,
            host=args.ollama_host,
            style=args.style or encounter.style,
        )

    packet = GoDirector(encounter, translator=translator).run()
    payload = json.dumps(packet, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
