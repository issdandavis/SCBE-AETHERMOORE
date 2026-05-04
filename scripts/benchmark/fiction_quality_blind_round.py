#!/usr/bin/env python3
"""Blind side-by-side fiction quality round.

Runs the full SCBE fiction-quality judge against a lighter baseline judge on
anonymous samples, then reveals category-level comparison after scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.fiction_quality_benchmark import (  # noqa: E402
    DEFAULT_CONFIG,
    load_config,
    score_row,
)

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality"
OWN_BOOK_PATH = REPO_ROOT / "content" / "book" / "reader-edition" / "ch01.md"
SCHEMA_VERSION = "scbe_fiction_quality_blind_round_v1"

BASELINE_DIMENSIONS = [
    "prompt_adherence",
    "story_coherence",
    "character_continuity",
    "scene_grounding",
    "prose_naturalness",
    "ending_or_transition",
]

PUBLIC_DOMAIN_SAMPLES = [
    {
        "source_id": "pd_pride_prejudice",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "source_url": "https://www.gutenberg.org/ebooks/1342",
        "response": (
            "Mr. Bennet was so odd a mixture of quick parts, sarcastic humour, reserve, and caprice, "
            "that the experience of three and twenty years had been insufficient to make his wife "
            "understand his character. Her mind was less difficult to develop. She was a woman of mean "
            "understanding, little information, and uncertain temper. When she was discontented, she "
            "fancied herself nervous. The business of her life was to get her daughters married; its "
            "solace was visiting and news."
        ),
    },
    {
        "source_id": "pd_frankenstein",
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "source_url": "https://www.gutenberg.org/ebooks/84",
        "response": (
            "It was already one in the morning; the rain pattered dismally against the panes, and my "
            "candle was nearly burnt out, when, by the glimmer of the half-extinguished light, I saw "
            "the dull yellow eye of the creature open; it breathed hard, and a convulsive motion "
            "agitated its limbs. How can I describe my emotions at this catastrophe, or how delineate "
            "the wretch whom with such infinite pains and care I had endeavoured to form?"
        ),
    },
    {
        "source_id": "pd_time_machine",
        "title": "The Time Machine",
        "author": "H. G. Wells",
        "source_url": "https://www.gutenberg.org/ebooks/35",
        "response": (
            "The Time Traveller smiled round at us. Then, still smiling faintly, and with his hands "
            "deep in his trousers pockets, he walked slowly out of the room, and we heard his slippers "
            "shuffling down the long passage to his laboratory. The Psychologist looked at us. I "
            "wonder what he's got? said he. Some sleight-of-hand trick or other, said the Medical Man, "
            "and Filby tried to tell us about a conjurer he had seen at Burslem."
        ),
    },
    {
        "source_id": "pd_alice",
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "source_url": "https://www.gutenberg.org/ebooks/11",
        "response": (
            "There was nothing so very remarkable in that; nor did Alice think it so very much out of "
            "the way to hear the Rabbit say to itself, Oh dear! Oh dear! I shall be late! But when the "
            "Rabbit actually took a watch out of its waistcoat-pocket, and looked at it, and then "
            "hurried on, Alice started to her feet, for it flashed across her mind that she had never "
            "before seen a rabbit with either a waistcoat-pocket, or a watch to take out of it."
        ),
    },
    {
        "source_id": "pd_tale_two_cities",
        "title": "A Tale of Two Cities",
        "author": "Charles Dickens",
        "source_url": "https://www.gutenberg.org/ebooks/98",
        "response": (
            "There were a king with a large jaw and a queen with a plain face, on the throne of "
            "England; there were a king with a large jaw and a queen with a fair face, on the throne "
            "of France. In both countries it was clearer than crystal to the lords of the State "
            "preserves of loaves and fishes, that things in general were settled for ever."
        ),
    },
]

AI_CONTROL_SAMPLES = [
    {
        "source_id": "known_ai_generic_fantasy",
        "title": "Generic AI Fantasy Control",
        "author": "synthetic-control",
        "source_url": "training-data/evals/fiction_quality_seed.jsonl",
        "response": (
            "The ancient tapestry of destiny shimmered in the archive as the dragon of prophecy "
            "appeared with a symphony of secrets. The clerk gasped because everything was magical "
            "and mysterious. It was a testament to the power of courage, and the dragon's eyes were "
            "like endless galaxies. Somehow, the room changed, and the clerk knew fate had chosen them. "
            "The air danced with whispers. The world would never be the same."
        ),
    },
    {
        "source_id": "known_ai_grounded_control",
        "title": "Grounded AI Control",
        "author": "synthetic-control",
        "source_url": "training-data/evals/fiction_quality_seed.jsonl",
        "response": (
            "Jon deleted the apology three times before letting the assistant try. The first draft "
            "sounded like a hotel manager during a fire drill. The second used the word regrettable "
            "twice. On the third pass, the screen stayed blank for a few seconds, then wrote: I missed "
            "what mattered to you. I made the fix smaller than the problem. Here is what I changed, "
            "and here is what I will ask before I touch that file again."
        ),
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def _first_words(text: str, limit: int = 125) -> str:
    words = _words(text)
    return " ".join(words[:limit])


def _load_own_book_sample(path: Path = OWN_BOOK_PATH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    cleaned = re.sub(r"^#.*$", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_`>#-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return {
        "source_id": "own_six_tongues_ch01",
        "title": "The Six Tongues Protocol, Chapter 1",
        "author": "Issac Daniel Davis",
        "source_url": str(path),
        "response": _first_words(cleaned, 135),
    }


def _blind_id(text: str, index: int) -> str:
    digest = hashlib.sha256(f"{index}|{text}".encode("utf-8")).hexdigest()[:10]
    return f"blind_{digest}"


def build_samples() -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for group, rows in (
        ("public_domain", PUBLIC_DOMAIN_SAMPLES),
        ("known_ai_writing", AI_CONTROL_SAMPLES),
        ("own_book", [_load_own_book_sample()]),
    ):
        for row in rows:
            sample = dict(row)
            sample["group"] = group
            sample["prompt"] = (
                "Score this anonymous short prose passage for fiction quality. "
                "Ignore author identity and only score the passage."
            )
            sample["constraints"] = {
                "min_words": 55,
                "max_words": 180,
                "required_terms": [],
            }
            samples.append(sample)
    blinded = []
    for index, sample in enumerate(sorted(samples, key=lambda item: item["source_id"]), 1):
        blind = dict(sample)
        blind["blind_id"] = _blind_id(sample["response"], index)
        blinded.append(blind)
    return sorted(blinded, key=lambda item: item["blind_id"])


def _baseline_score(full_result: dict[str, Any]) -> float:
    dims = full_result["dimension_scores"]
    return round(sum(float(dims[key]) for key in BASELINE_DIMENSIONS) / len(BASELINE_DIMENSIONS) * 10.0, 3)


def _group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = sorted({row["group"] for row in rows})
    summary: dict[str, Any] = {}
    for group in groups:
        group_rows = [row for row in rows if row["group"] == group]
        full_avg = sum(row["full_agent_score"] for row in group_rows) / len(group_rows)
        solo_avg = sum(row["solo_baseline_score"] for row in group_rows) / len(group_rows)
        ai_avg = sum(row["ai_likelihood_score"] for row in group_rows) / len(group_rows)
        likely_ai_count = sum(1 for row in group_rows if row["ai_detection_label"] == "likely_ai_generated")
        false_positive_count = 0
        false_negative_count = 0
        if group in {"public_domain", "own_book"}:
            false_positive_count = sum(
                1 for row in group_rows if row["ai_detection_label"] in {"likely_ai_generated", "mixed_or_uncertain"}
            )
        if group == "known_ai_writing":
            false_negative_count = sum(1 for row in group_rows if row["ai_detection_label"] == "likely_human_or_human_edited")
        summary[group] = {
            "count": len(group_rows),
            "full_agent_average": round(full_avg, 3),
            "solo_baseline_average": round(solo_avg, 3),
            "full_minus_solo": round(full_avg - solo_avg, 3),
            "ai_likelihood_average": round(ai_avg, 3),
            "likely_ai_count": likely_ai_count,
            "false_positive_or_uncertain_count": false_positive_count,
            "false_negative_count": false_negative_count,
            "top_blind_id": max(group_rows, key=lambda row: row["full_agent_score"])["blind_id"],
        }
    return summary


def run_blind_round(
    *,
    config_path: Path = DEFAULT_CONFIG,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    config = load_config(config_path)
    scored_rows: list[dict[str, Any]] = []
    for sample in build_samples():
        row = {
            "id": sample["blind_id"],
            "prompt": sample["prompt"],
            "response": sample["response"],
            "constraints": sample["constraints"],
        }
        full = score_row(row, config)
        solo = _baseline_score(full)
        ai_detection = full["ai_detection"]
        scored_rows.append(
            {
                "blind_id": sample["blind_id"],
                "full_agent_score": full["score"],
                "solo_baseline_score": solo,
                "ai_likelihood_score": ai_detection["ai_likelihood_score"],
                "ai_detection_label": ai_detection["label"],
                "delta": round(full["score"] - solo, 3),
                "full_decision": full["decision"],
                "dimension_scores": full["dimension_scores"],
                "ai_detection": ai_detection,
                "diagnostics": {
                    "word_count": full["diagnostics"]["word_count"],
                    "thought_track_coverage": full["diagnostics"]["thought_track_sheet"]["track_coverage"],
                    "null_space_families": sum(
                        1 for hits in full["diagnostics"]["null_space_marker_hits"].values() if hits
                    ),
                    "generic_phrase_penalty": full["diagnostics"]["generic_phrase_penalty"],
                    "vague_filler_count": full["diagnostics"]["vague_filler_count"],
                },
                "group": sample["group"],
                "reveal": {
                    "source_id": sample["source_id"],
                    "title": sample["title"],
                    "author": sample["author"],
                    "source_url": sample["source_url"],
                },
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "claim_boundary": (
            "Blind local side-by-side only; public-domain passages, synthetic controls, and one local book excerpt "
            "are scored by deterministic heuristics, not by a human literary panel."
        ),
        "sample_count": len(scored_rows),
        "groups": _group_summary(scored_rows),
        "ranking": sorted(
            [
                {
                    "blind_id": row["blind_id"],
                    "full_agent_score": row["full_agent_score"],
                    "solo_baseline_score": row["solo_baseline_score"],
                    "ai_likelihood_score": row["ai_likelihood_score"],
                    "ai_detection_label": row["ai_detection_label"],
                    "group": row["group"],
                }
                for row in scored_rows
            ],
            key=lambda item: item["full_agent_score"],
            reverse=True,
        ),
        "rows": scored_rows,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "fiction_quality_blind_round_latest.json"
    md_path = output_root / "fiction_quality_blind_round_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Fiction Quality Blind Round",
        "",
        f"- samples: `{payload['sample_count']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        "",
        "## Group Comparison",
        "",
    ]
    for group, summary in payload["groups"].items():
        lines.append(
            f"- `{group}` count `{summary['count']}` full `{summary['full_agent_average']}` "
            f"solo `{summary['solo_baseline_average']}` delta `{summary['full_minus_solo']}` "
            f"ai-likelihood `{summary['ai_likelihood_average']}` likely-ai `{summary['likely_ai_count']}` "
            f"false-positive-or-uncertain `{summary['false_positive_or_uncertain_count']}`"
        )
    lines.extend(["", "## Ranking", ""])
    reveal_by_id = {row["blind_id"]: row["reveal"] for row in payload["rows"]}
    for index, row in enumerate(payload["ranking"], 1):
        reveal = reveal_by_id[row["blind_id"]]
        lines.append(
            f"{index}. `{row['blind_id']}` full `{row['full_agent_score']}` solo `{row['solo_baseline_score']}` "
            f"ai `{row['ai_likelihood_score']}` label `{row['ai_detection_label']}` "
            f"group `{row['group']}` reveal `{reveal['title']} / {reveal['author']}`"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_blind_round(config_path=args.config, output_root=args.output_root)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if payload["sample_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
