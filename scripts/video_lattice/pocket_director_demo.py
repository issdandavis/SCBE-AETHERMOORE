#!/usr/bin/env python3
"""Run a pocket-dimension director step.

Default mode is local/stubbed so the demo is deterministic and free. Use
`--live` to call OpenAI through WorldDirector when OPENAI_API_KEY is available.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "video_lattice" / "pocket_director"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import RoundTableDirector, WorldCommand, WorldDelta, WorldDirector, demo_world  # noqa: E402


class StubDirector(WorldDirector):
    """Deterministic no-network director for local testing."""

    def __init__(self, model: str, dx: int, dy: int, narrative: str) -> None:
        self.model = model
        self.dx = dx
        self.dy = dy
        self.narrative = narrative

    def step(self, world, director_note: str = "") -> WorldDelta:
        return WorldDelta(
            commands=[
                WorldCommand(
                    type="move",
                    data={"entity_id": "hero", "dx": self.dx, "dy": self.dy},
                )
            ],
            narrative=self.narrative,
            model=self.model,
            raw_response=json.dumps({"stub": True, "director_note": director_note}),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note", nargs="?", default="the hero cautiously approaches the water")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--live", action="store_true", help="Use live OpenAI calls through WorldDirector")
    parser.add_argument("--roundtable", action="store_true", help="Run two directors and choose lowest drift")
    parser.add_argument("--model", default="gpt-4.1")
    parser.add_argument("--second-model", default="gpt-4o-mini")
    args = parser.parse_args()

    world = demo_world()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.live:
        directors = [WorldDirector(model=args.model)]
        if args.roundtable:
            directors.append(WorldDirector(model=args.second_model))
    else:
        directors = [
            StubDirector("stub.cautious", dx=1, dy=0, narrative="The hero steps closer to the water."),
            StubDirector("stub.chaotic", dx=5, dy=2, narrative="The hero suddenly lunges across the pocket world."),
        ]

    if args.roundtable or not args.live:
        table = RoundTableDirector(directors)
        delta, report = table.step(world, args.note)
        report_text = report.summary()
    else:
        director = directors[0]
        delta = director.step(world, args.note)
        drift = director.score_delta(world, delta)
        report_text = f"winner: {director.model} (drift={drift:.4f})\n  {director.model}: drift={drift:.4f}  '{delta.narrative}'"

    skipped = directors[0].apply_delta(world, delta)
    json_path = world.save_json(args.out_dir / "directed_world.json")
    svg_path = world.save_svg(args.out_dir / "directed_world.svg", cell=48)
    text_path = args.out_dir / "directed_world.txt"
    report_path = args.out_dir / "roundtable_report.txt"
    delta_path = args.out_dir / "winning_delta.json"

    text_path.write_text("\n".join(world.to_symbol_grid()) + "\n", encoding="utf-8")
    report_path.write_text(report_text + "\n", encoding="utf-8")
    delta_path.write_text(json.dumps(delta.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    print(report_text)
    if skipped:
        print("skipped:")
        for item in skipped:
            print(f"  {item}")
    print(f"wrote {json_path}")
    print(f"wrote {svg_path}")
    print(f"wrote {text_path}")
    print(f"wrote {delta_path}")
    print(f"wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
