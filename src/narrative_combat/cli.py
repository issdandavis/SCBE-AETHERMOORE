from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .director import Director
from .fixtures import boss_duel_demo


def _emit(payload: str, out: Path | None) -> None:
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a narrative combat fight packet.")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed override (default 1337 for the demo, or the file's own seed when --encounter is given)",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--encounter",
        type=Path,
        default=None,
        help="path to a custom encounter JSON (default: built-in boss_duel_demo)",
    )
    source.add_argument(
        "--dump-template",
        action="store_true",
        help="emit the built-in demo as a fillable encounter JSON template and exit",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--translator",
        choices=["template", "llm"],
        default="template",
        help="template = deterministic (default); llm = glm-5.1 prose via Ollama, falls back to template",
    )
    parser.add_argument("--style", default=None, help="override prose style for the llm translator")
    parser.add_argument("--model", default="glm-5.1:cloud", help="Ollama model for the llm translator")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    if args.dump_template:
        from .loader import encounter_to_dict

        _emit(json.dumps(encounter_to_dict(boss_duel_demo()), indent=2, sort_keys=True), args.out)
        return 0

    if args.encounter is not None:
        from .loader import EncounterSpecError, load_encounter

        try:
            encounter = load_encounter(args.encounter, seed_override=args.seed)
        except EncounterSpecError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        encounter = boss_duel_demo(seed=args.seed if args.seed is not None else 1337)

    translator = None
    if args.translator == "llm":
        from .translator import LLMTranslator

        translator = LLMTranslator(
            model=args.model,
            host=args.ollama_host,
            style=args.style or encounter.style,
        )

    packet = Director(encounter, translator=translator).run()
    _emit(json.dumps(packet, indent=2, sort_keys=True), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
