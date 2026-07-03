"""CLI/demo entry point for the consolidated SCBE Instrument Computer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.instrument_computer import (  # noqa: E402
    consonance_report,
    demo_receipt,
    holophonor_receipt,
    key_bijection_proof,
    note_role,
    prove_any_instrument,
    reel_tape_demo,
    shell_demo,
)


def _emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCBE Instrument Computer")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("demo", help="run the full consolidated demo receipt")

    holo = sub.add_parser("holophonor", help="play one note phrase into code/result/color/voice")
    holo.add_argument("--song", default="C E")
    holo.add_argument("--mode", default="coding")
    holo.add_argument("--args", default="2,3,4", help="comma-separated numeric args")
    holo.add_argument("--speak", action="store_true", help="write a Windows SAPI voice WAV")
    holo.add_argument("--wav", default=None, help="optional output WAV path")

    role = sub.add_parser("role", help="show a note's role in a key")
    role.add_argument("note")
    role.add_argument("root")
    role.add_argument("mode", choices=["major", "minor"])

    cons = sub.add_parser("consonance", help="check interval/key fit for notes")
    cons.add_argument("notes", nargs="+")

    sub.add_parser("bijection", help="prove key-independent degree program rendering")
    sub.add_parser("any-instrument", help="prove alphabet independence across instruments")
    sub.add_parser("shell", help="run the persistent Holophonor shell demo")
    sub.add_parser("reel", help="run the old movie-reel tape mechanism demo")

    args = parser.parse_args(argv)
    cmd = args.cmd or "demo"
    if cmd == "demo":
        _emit(demo_receipt())
    elif cmd == "holophonor":
        values = tuple(float(part.strip()) for part in args.args.split(",") if part.strip())
        _emit(
            holophonor_receipt(
                args.song,
                mode=args.mode,
                args=values,
                speak=args.speak,
                wav_path=args.wav,
            )
        )
    elif cmd == "role":
        _emit(note_role(args.note, args.root, args.mode))
    elif cmd == "consonance":
        _emit(consonance_report(args.notes))
    elif cmd == "bijection":
        _emit(key_bijection_proof())
    elif cmd == "any-instrument":
        _emit(prove_any_instrument())
    elif cmd == "shell":
        _emit(shell_demo())
    elif cmd == "reel":
        _emit(reel_tape_demo())
    else:
        parser.error(f"unknown command {cmd!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
