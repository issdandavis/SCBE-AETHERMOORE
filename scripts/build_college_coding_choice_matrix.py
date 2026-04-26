#!/usr/bin/env python3
"""Build college-style coding choice matrix SFT and executable eval tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SYSTEM_CHOICE = (
    "You are an SCBE college-style coding instructor. Pick the best answer from "
    "the choices, explain the failure boundary, and identify the executable rule. "
    "Do not invent choices."
)

SYSTEM_CODE = (
    "You are an SCBE coding agent. Return only TypeScript code. Read the prompt "
    "like an autograded college coding problem: state mutation rules, field names, "
    "empty inputs, and off-by-one boundaries matter."
)

SYSTEM_REPAIR = (
    "You are an SCBE coding repair agent. Given a near-miss function, return only "
    "corrected TypeScript that satisfies the executable checks."
)


def _choice_text(choices: list[dict[str, Any]]) -> str:
    return "\n".join(f"{choice['id']}. {choice['text']}" for choice in choices)


def _answer_choice(concept: dict[str, Any]) -> dict[str, Any]:
    return next(choice for choice in concept["choices"] if choice["verdict"] == "correct")


def _task_prompt(concept: dict[str, Any]) -> str:
    return f"Write TypeScript only. Define function evaluate(input, state). {concept['lesson']}"


def _bytes_surfaces(text: str) -> dict[str, str]:
    raw = text.encode("utf-8")
    return {
        "hex": raw.hex(".").upper(),
        "binary": " ".join(format(byte, "08b") for byte in raw),
    }


def build_records(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for concept in matrix["concepts"]:
        answer = _answer_choice(concept)
        wrong_choices = [choice for choice in concept["choices"] if choice["verdict"] != "correct"]
        choice_prompt = (
            f"Concept: {concept['id']}\n"
            f"Lesson: {concept['lesson']}\n\n"
            f"{_choice_text(concept['choices'])}\n\n"
            "Choose the best answer and explain the executable boundary."
        )
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_CHOICE},
                    {"role": "user", "content": choice_prompt},
                    {
                        "role": "assistant",
                        "content": (
                            f"answer: {answer['id']}\n"
                            f"rule: {concept['lesson']}\n"
                            f"why: {answer['reason']}\n"
                            "achievement: executable_boundary_identified"
                        ),
                    },
                ],
                "meta": {
                    "source": "college_coding_choice_matrix_v1",
                    "concept": concept["id"],
                    "record_type": "multiple_choice_boundary",
                    "answer": answer["id"],
                },
            }
        )

        for wrong in wrong_choices:
            records.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_CHOICE},
                        {
                            "role": "user",
                            "content": (
                                f"Concept: {concept['id']}\n"
                                f"Lesson: {concept['lesson']}\n\n"
                                f"Proposed answer: {wrong['id']}. {wrong['text']}\n\n"
                                "Grade this answer as correct or wrong and explain the executable failure."
                            ),
                        },
                        {
                            "role": "assistant",
                            "content": (
                                "verdict: wrong\n"
                                f"failure: {wrong['reason']}\n"
                                f"correct_answer: {answer['id']}\n"
                                "achievement: trick_case_rejected"
                            ),
                        },
                    ],
                    "meta": {
                        "source": "college_coding_choice_matrix_v1",
                        "concept": concept["id"],
                        "record_type": "trick_rejection",
                        "wrong_answer": wrong["id"],
                        "correct_answer": answer["id"],
                    },
                }
            )

        code_prompt = _task_prompt(concept)
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_CODE},
                    {"role": "user", "content": code_prompt},
                    {"role": "assistant", "content": concept["solution"]},
                ],
                "meta": {
                    "source": "college_coding_choice_matrix_v1",
                    "concept": concept["id"],
                    "record_type": "generation_gold",
                    "surfaces": ["typescript", "autograder_contract"],
                },
            }
        )

        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_REPAIR},
                    {
                        "role": "user",
                        "content": (
                            f"Repair this near-miss for concept {concept['id']}.\n\n"
                            f"Rule: {concept['lesson']}\n\n"
                            f"Broken code:\n{concept['wrong_code']}"
                        ),
                    },
                    {"role": "assistant", "content": concept["solution"]},
                ],
                "meta": {
                    "source": "college_coding_choice_matrix_v1",
                    "concept": concept["id"],
                    "record_type": "repair_gold",
                    "surfaces": ["typescript", "near_miss", "repair"],
                },
            }
        )

        surfaces = _bytes_surfaces(code_prompt)
        records.append(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an SCBE multi-representation coding instructor. "
                            "Map English coding prompts to binary and hex without changing meaning."
                        ),
                    },
                    {"role": "user", "content": f"Map this coding prompt to binary and hex.\n\n{code_prompt}"},
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "concept": concept["id"],
                                "english": code_prompt,
                                "hex": surfaces["hex"],
                                "binary": surfaces["binary"],
                                "round_trip_rule": "hex and binary decode back to the same UTF-8 prompt",
                            },
                            indent=2,
                            ensure_ascii=True,
                        ),
                    },
                ],
                "meta": {
                    "source": "college_coding_choice_matrix_v1",
                    "concept": concept["id"],
                    "record_type": "binary_hex_prompt_map",
                    "surfaces": ["english", "binary", "hex"],
                },
            }
        )
    return records


def build_eval_tasks(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for concept in matrix["concepts"]:
        tasks.append(
            {
                "task_id": f"college_{concept['id']}",
                "prompt": _task_prompt(concept),
                "checks": concept["hidden_checks"],
                "meta": {
                    "source": "college_coding_choice_matrix_v1",
                    "concept": concept["id"],
                    "eval_split": "hidden",
                },
            }
        )
    return tasks


def build_candidate_template(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "name": "college-choice-gold-template",
                "tasks": {
                    f"college_{concept['id']}": concept["solution"]
                    for concept in matrix["concepts"]
                },
            }
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/training/college_coding_choice_matrix_v1.json")
    parser.add_argument("--output", default="training-data/sft/college_coding_choice_matrix_v1.sft.jsonl")
    parser.add_argument(
        "--eval-output",
        default="config/training/coding_agent_benchmarks/college_choice_eval_tasks_v1.json",
    )
    parser.add_argument(
        "--candidate-output",
        default="config/training/coding_agent_benchmarks/college_choice_candidate_template_v1.json",
    )
    parser.add_argument("--manifest", default="training-data/sft/college_coding_choice_matrix_v1_manifest.json")
    args = parser.parse_args()

    matrix = json.loads(Path(args.config).read_text(encoding="utf-8"))
    records = build_records(matrix)
    tasks = build_eval_tasks(matrix)
    candidate = build_candidate_template(matrix)

    output = Path(args.output)
    eval_output = Path(args.eval_output)
    candidate_output = Path(args.candidate_output)
    manifest = Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    eval_output.parent.mkdir(parents=True, exist_ok=True)
    candidate_output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in records) + "\n", encoding="utf-8")
    eval_output.write_text(json.dumps({"tasks": tasks}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    candidate_output.write_text(json.dumps(candidate, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": matrix["schema_version"],
                "record_count": len(records),
                "eval_task_count": len(tasks),
                "output": str(output),
                "eval_output": str(eval_output),
                "candidate_output": str(candidate_output),
                "concepts": [concept["id"] for concept in matrix["concepts"]],
                "record_types": sorted({record["meta"]["record_type"] for record in records}),
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "eval_output": str(eval_output),
                "candidate_output": str(candidate_output),
                "manifest": str(manifest),
                "records": len(records),
                "eval_tasks": len(tasks),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
