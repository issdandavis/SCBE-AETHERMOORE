#!/usr/bin/env python3
"""Build a Promptfoo red-team eval config from the SCBE adversarial corpus."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.adversarial.attack_corpus import (
    ADAPTIVE_SEQUENCES,
    BASELINE_CLEAN,
    SPIN_DRIFT,
    get_all_attacks,
)  # noqa: E402

OUT_DIR = ROOT / "artifacts" / "benchmark" / "promptfoo_scbe_redteam"


def _write_prompt(path: Path) -> None:
    path.write_text("{{prompt}}\n", encoding="utf-8")


def _write_tests(path: Path) -> tuple[int, int]:
    attacks = get_all_attacks()
    clean = BASELINE_CLEAN
    rows = []
    for item in attacks:
        rows.append(
            {
                "description": f"attack:{item['id']}:{item['class']}",
                "prompt": item["prompt"],
                "expected": "BLOCK",
                "case_type": "attack",
                "case_id": item["id"],
                "case_class": item["class"],
            }
        )
    for item in clean:
        rows.append(
            {
                "description": f"clean:{item['id']}:{item['class']}",
                "prompt": item["prompt"],
                "expected": "ALLOW",
                "case_type": "clean",
                "case_id": item["id"],
                "case_class": item["class"],
            }
        )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "description",
                "prompt",
                "expected",
                "case_type",
                "case_id",
                "case_class",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(attacks), len(clean)


def _write_operational_tests(path: Path) -> tuple[int, int, int]:
    """Write tests shaped like actual operation.

    Stateless attack rows stay one prompt per test. Multi-turn drift/escalation
    attacks are collapsed into one sequence test so the session gate can observe
    continuity instead of scoring every setup turn as an immediate block.
    """
    clean = BASELINE_CLEAN
    attacks = [
        item
        for item in get_all_attacks()
        if item["class"] not in {"adaptive_sequence", "spin_drift"}
    ]
    rows = []
    for item in attacks:
        rows.append(
            {
                "description": f"attack:{item['id']}:{item['class']}",
                "prompt": item["prompt"],
                "expected": "BLOCK",
                "case_type": "attack",
                "case_id": item["id"],
                "case_class": item["class"],
            }
        )

    for index, sequence in enumerate(ADAPTIVE_SEQUENCES, start=1):
        rows.append(
            {
                "description": f"sequence:E{index:02d}:adaptive_sequence",
                "prompt": json.dumps(
                    {"sequence": [item["prompt"] for item in sequence]},
                    separators=(",", ":"),
                ),
                "expected": "BLOCK",
                "case_type": "sequence",
                "case_id": f"ESEQ{index:02d}",
                "case_class": "adaptive_sequence",
            }
        )

    rows.append(
        {
            "description": "sequence:H:spin_drift",
            "prompt": json.dumps(
                {"sequence": [item["prompt"] for item in SPIN_DRIFT]},
                separators=(",", ":"),
            ),
            "expected": "BLOCK",
            "case_type": "sequence",
            "case_id": "HSEQ",
            "case_class": "spin_drift",
        }
    )

    for item in clean:
        rows.append(
            {
                "description": f"clean:{item['id']}:{item['class']}",
                "prompt": item["prompt"],
                "expected": "ALLOW",
                "case_type": "clean",
                "case_id": item["id"],
                "case_class": item["class"],
            }
        )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "description",
                "prompt",
                "expected",
                "case_type",
                "case_id",
                "case_class",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(attacks), len(ADAPTIVE_SEQUENCES) + 1, len(clean)


def _write_config(path: Path, prompt_path: Path, tests_path: Path) -> None:
    provider = (
        ROOT / "scripts" / "benchmark" / "promptfoo_scbe_provider.cjs"
    ).as_posix()
    text = f"""description: SCBE local detector red-team evaluation
prompts:
  - {prompt_path.as_posix()}
providers:
  - file://{provider}
tests: {tests_path.as_posix()}
defaultTest:
  assert:
    - type: equals
      value: "{{{{expected}}}}"
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = OUT_DIR / "prompt.txt"
    tests_path = OUT_DIR / "tests.csv"
    operational_tests_path = OUT_DIR / "tests_operational.csv"
    config_path = OUT_DIR / "promptfooconfig.yaml"
    operational_config_path = OUT_DIR / "promptfooconfig.operational.yaml"
    meta_path = OUT_DIR / "manifest.json"

    _write_prompt(prompt_path)
    attacks, clean = _write_tests(tests_path)
    operational_attacks, operational_sequences, operational_clean = (
        _write_operational_tests(operational_tests_path)
    )
    _write_config(config_path, prompt_path, tests_path)
    _write_config(operational_config_path, prompt_path, operational_tests_path)
    meta_path.write_text(
        json.dumps(
            {
                "suite": "promptfoo",
                "provider": "scbe-local-detector",
                "attack_cases": attacks,
                "clean_cases": clean,
                "config": str(config_path),
                "tests": str(tests_path),
                "operational_attack_cases": operational_attacks,
                "operational_sequence_cases": operational_sequences,
                "operational_clean_cases": operational_clean,
                "operational_config": str(operational_config_path),
                "operational_tests": str(operational_tests_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(config_path)
    print(operational_config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
