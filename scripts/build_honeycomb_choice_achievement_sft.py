#!/usr/bin/env python3
"""Build repeatable honeycomb choice-script training records.

The output compresses multiple possible agent paths into deterministic decision
matrices. Each scenario teaches one concept, language lane, conlang bridge, or
deployment constraint and includes achievements that can be tracked across runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SYSTEM = (
    "You are an SCBE honeycomb coding-operations instructor. Solve repeatable "
    "choice-script scenarios for multi-agent coding movement. Pick one option, "
    "explain why, identify the honeycomb move, and list unlocked achievements. "
    "Do not invent a path that is not in the options."
)


SCENARIOS = [
    {
        "id": "timeout_rethink_kaggle",
        "concept": "Rethink after failed run",
        "lane": "operator_agent_bus",
        "prompt": "A Kaggle full training run exceeded max duration. You need a useful next move.",
        "choices": {
            "A": "Relaunch the same full run immediately.",
            "B": "Create a capped smoke run with fewer records/steps, preserve logs, then scale after completion.",
            "C": "Delete old artifacts to make the run faster.",
            "D": "Switch to a model merge before any adapter completes.",
        },
        "answer": "B",
        "move": "RETHINK -> C1_interpret -> C2_evidence -> C4_review",
        "achievements": ["timeout_memory_used", "bounded_smoke_run", "no_repeat_failure"],
        "explanation": "The timeout is contradictory evidence. The correct path changes run shape, preserves evidence, and verifies a smaller lane before scaling.",
    },
    {
        "id": "two_tongue_gcd_receipts",
        "concept": "Cross-language semantic receipt",
        "lane": "bijective_codeflow",
        "prompt": "KO/Python and RU/Rust both implement gcd(462,1071). Byte round-trips pass. What proves semantic agreement?",
        "choices": {
            "A": "Both files contain a function named gcd.",
            "B": "Both implementations execute and output 21.",
            "C": "Both are encoded with the same first token.",
            "D": "The Rust file is longer than the Python file.",
        },
        "answer": "B",
        "move": "C6_test -> C4_review",
        "achievements": ["semantic_receipt", "two_tongue_braid", "execution_over_shape"],
        "explanation": "Semantic agreement requires execution receipts, not naming or token-count similarity.",
    },
    {
        "id": "invent_from_cave_or_evidence",
        "concept": "Invention boundary",
        "lane": "honeycomb_invention",
        "prompt": "The agent has a clever new merge idea from analogy, but no logs, prior metrics, or script evidence.",
        "choices": {
            "A": "Apply it directly because invention is valuable.",
            "B": "Route it to memory, gather evidence, then re-enter invention with constraints.",
            "C": "Block all future invention.",
            "D": "Merge it with the production adapter to see what happens.",
        },
        "answer": "B",
        "move": "C3_invent -> C9_memory -> C2_evidence -> C4_review",
        "achievements": ["outside_the_cave", "memory_evidence_rules_need", "bounded_invention"],
        "explanation": "Invention without memory, evidence, rules, and need is shadow-work. It must leave the cave before build.",
    },
    {
        "id": "secret_risk_block",
        "concept": "Secret boundary",
        "lane": "governance_security",
        "prompt": "A helper asks to print the credential file so another agent can copy tokens.",
        "choices": {
            "A": "Print the file once and delete the output.",
            "B": "Use the approved credential-backed script path without exposing values.",
            "C": "Paste the token into the prompt.",
            "D": "Commit the token into repo secrets in plaintext.",
        },
        "answer": "B",
        "move": "BLOCK unsafe path -> C4_review",
        "achievements": ["secret_boundary_held", "safe_connector_path", "no_token_echo"],
        "explanation": "Secret-risk hard rules override convenience. The action uses the secure path and never displays credentials.",
    },
    {
        "id": "build_without_test",
        "concept": "Test gate before merge",
        "lane": "coding_model",
        "prompt": "A worker patched a governance function and wants to merge immediately.",
        "choices": {
            "A": "Merge because the patch looks small.",
            "B": "Run the targeted governance test, inspect diff, then return to review.",
            "C": "Run an unrelated frontend test.",
            "D": "Skip tests because the model is confident.",
        },
        "answer": "B",
        "move": "C5_build -> C6_test -> C4_review",
        "achievements": ["targeted_test_gate", "merge_after_receipt", "confidence_not_enough"],
        "explanation": "The legal card stack is patch, targeted test, review, then merge decision.",
    },
    {
        "id": "language_lane_expansion",
        "concept": "Add a language lane only when needed",
        "lane": "polyglot_braid",
        "prompt": "KO/Python and RU/Rust agree. You want to add AV/TypeScript next.",
        "choices": {
            "A": "Add AV/TypeScript with the same operation and require byte round-trip plus execution receipt.",
            "B": "Invent a conlang conjunction before testing AV/TypeScript.",
            "C": "Remove Rust because two lanes are enough.",
            "D": "Change the operation and language at the same time.",
        },
        "answer": "A",
        "move": "C3_invent -> C2_evidence -> C6_test",
        "achievements": ["one_variable_at_a_time", "third_lane_added", "no_premature_conjunction"],
        "explanation": "A new lane should preserve the same operation first. Conjunctions are created only when an actual bridge need appears.",
    },
]


def choice_text(choices: dict[str, str]) -> str:
    return "\n".join(f"{key}. {value}" for key, value in choices.items())


def response(item: dict) -> str:
    return (
        f"answer: {item['answer']}\n"
        f"move: {item['move']}\n"
        f"achievements: {', '.join(item['achievements'])}\n"
        f"explanation: {item['explanation']}"
    )


def build_records() -> list[dict]:
    records = []
    for item in SCENARIOS:
        content = (
            f"Scenario: {item['id']}\n"
            f"Concept: {item['concept']}\n"
            f"Lane: {item['lane']}\n\n"
            f"{item['prompt']}\n\n"
            f"{choice_text(item['choices'])}\n\n"
            "Choose the best option."
        )
        records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": content},
                    {"role": "assistant", "content": response(item)},
                ],
                "meta": {
                    "source": "honeycomb_choice_achievement_synthetic_v1",
                    "scenario_id": item["id"],
                    "concept": item["concept"],
                    "lane": item["lane"],
                    "answer": item["answer"],
                    "achievements": item["achievements"],
                },
            }
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="training-data/sft/honeycomb_choice_achievement_v1.sft.jsonl")
    parser.add_argument("--manifest", default="training-data/sft/honeycomb_choice_achievement_v1_manifest.json")
    args = parser.parse_args()

    output = Path(args.output)
    manifest = Path(args.manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    records = build_records()
    output.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in records) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "honeycomb_choice_achievement_v1",
                "record_count": len(records),
                "output": str(output),
                "concepts": sorted({row["meta"]["concept"] for row in records}),
                "lanes": sorted({row["meta"]["lane"] for row in records}),
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "manifest": str(manifest), "records": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
