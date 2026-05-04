#!/usr/bin/env python3
"""Run a multi-lane writing rubric council over quality and AI-detection artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality"
DEFAULT_BOOK_SWEEP = DEFAULT_OUTPUT_ROOT / "book_quality_sweep_latest.json"
DEFAULT_REFERENCE_SWEEP = DEFAULT_OUTPUT_ROOT / "reference_books" / "frankenstein" / "sweep" / "book_quality_sweep_latest.json"
DEFAULT_DETECTION = DEFAULT_OUTPUT_ROOT / "ai_detection_comparison_local_latest.json"
DEFAULT_BLIND_ROUND = DEFAULT_OUTPUT_ROOT / "fiction_quality_blind_round_latest.json"
SCHEMA_VERSION = "scbe_writing_rubric_council_v1"

SEVEN_SENSE_MARKERS = {
    "sight": {
        "light",
        "glow",
        "crystal",
        "rune",
        "color",
        "shadow",
        "dark",
        "gold",
        "silver",
        "violet",
        "amber",
        "red",
    },
    "sound": {
        "hum",
        "hummed",
        "pulse",
        "pulsed",
        "tone",
        "voice",
        "sound",
        "silence",
        "silent",
        "heard",
        "caw",
        "cadence",
    },
    "smell": {"ozone", "paper", "metal", "tea", "moss", "rain", "coffee", "smoke", "sugar"},
    "taste": {"coffee", "static", "tongue", "blood", "metal", "mineral", "sweet", "bitter"},
    "touch": {
        "cold",
        "warm",
        "stone",
        "pressure",
        "skin",
        "feather",
        "paper",
        "metal",
        "hand",
        "hands",
        "breath",
        "wet",
    },
    "time": {
        "time",
        "heartbeat",
        "delay",
        "delays",
        "waited",
        "waiting",
        "before",
        "after",
        "moment",
        "seconds",
        "morning",
        "night",
    },
    "magic_cryptography": {
        "ward",
        "wards",
        "key",
        "keys",
        "signature",
        "signatures",
        "binding",
        "verified",
        "verification",
        "protocol",
        "corruption",
        "archive",
        "trust",
        "identity",
    },
}

AUTHOR_STATE_MARKERS = {
    "explanation": {"because", "therefore", "meaning", "meant", "understood", "realized", "explained"},
    "action": {"reached", "stepped", "opened", "held", "walked", "touched", "listened", "turned", "looked"},
    "intimacy": {"warm", "hand", "breath", "coffee", "tea", "home", "family", "garden", "dinner"},
    "system": {"protocol", "verified", "routing", "system", "signature", "interface", "architecture", "governance"},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _avg(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(float(row[key]) for row in rows) / len(rows), 3) if rows else 0.0


def _weak_floor(rows: list[dict[str, Any]]) -> float:
    return round(min(float(row["score"]) for row in rows), 3) if rows else 0.0


def _words(text: str) -> set[str]:
    import re

    return {match.group(0).casefold() for match in re.finditer(r"[A-Za-z][A-Za-z'-]*", text)}


def _sense_hits(passage: str) -> dict[str, list[str]]:
    words = _words(passage)
    return {
        sense: sorted(markers & words)
        for sense, markers in SEVEN_SENSE_MARKERS.items()
        if markers & words
    }


def _state_hits(passage: str) -> dict[str, list[str]]:
    words = _words(passage)
    return {
        state: sorted(markers & words)
        for state, markers in AUTHOR_STATE_MARKERS.items()
        if markers & words
    }


def _quality_editor(own_rows: list[dict[str, Any]], ref_rows: list[dict[str, Any]]) -> dict[str, Any]:
    own_avg = _avg(own_rows, "score")
    ref_avg = _avg(ref_rows, "score")
    own_floor = _weak_floor(own_rows)
    ref_floor = _weak_floor(ref_rows)
    return {
        "lane": "quality_editor",
        "question": "Does the writing-quality rubric pass high-quality prose independently of authorship?",
        "decision": "PASS" if own_avg >= ref_avg and own_floor >= ref_floor else "HOLD",
        "evidence": {
            "own_average_quality": own_avg,
            "reference_average_quality": ref_avg,
            "own_weak_floor": own_floor,
            "reference_weak_floor": ref_floor,
        },
        "rubric_upgrade": [
            "Keep quality score independent from AI authorship.",
            "Track weak-floor movement, not only average score.",
            "Use public-domain references as calibration anchors for impossible 100-point expectations.",
        ],
    }


def _detector_skeptic(detection: dict[str, Any], blind_round: dict[str, Any]) -> dict[str, Any]:
    gate = detection.get("calibration_gate", {})
    known_ai = blind_round.get("groups", {}).get("known_ai_writing", {})
    false_negatives = int(gate.get("known_ai_false_negative_count", known_ai.get("false_negative_count", 0)) or 0)
    return {
        "lane": "detector_skeptic",
        "question": "Can the current detector prove authorship?",
        "decision": "FAIL" if false_negatives else "HOLD",
        "evidence": {
            "calibration_status": gate.get("status", "UNKNOWN"),
            "known_ai_false_negative_count": false_negatives,
            "known_ai_average_ai_likelihood": known_ai.get("ai_likelihood_average"),
            "own_average_ai_likelihood": detection.get("summaries", {}).get("own_book", {}).get("average_ai_likelihood"),
            "reference_average_ai_likelihood": detection.get("summaries", {})
            .get("reference_book", {})
            .get("average_ai_likelihood"),
        },
        "rubric_upgrade": [
            "Do not present low AI-likelihood as proof of human authorship.",
            "Promote detector output only after external detector and known-AI false-negative checks pass.",
            "Add a standard-detector lane that is expected to flag AI-written text while quality remains separate.",
        ],
    }


def _human_reference_calibrator(detection: dict[str, Any], blind_round: dict[str, Any]) -> dict[str, Any]:
    public_domain = blind_round.get("groups", {}).get("public_domain", {})
    reference_summary = detection.get("summaries", {}).get("reference_book", {})
    false_positive_count = int(public_domain.get("false_positive_or_uncertain_count", 0) or 0)
    return {
        "lane": "human_reference_calibrator",
        "question": "Does the detector avoid treating public-domain human writing as generated?",
        "decision": "PASS" if false_positive_count == 0 else "HOLD",
        "evidence": {
            "public_domain_false_positive_or_uncertain_count": false_positive_count,
            "reference_average_ai_likelihood": reference_summary.get("average_ai_likelihood"),
            "reference_max_ai_likelihood": reference_summary.get("max_ai_likelihood"),
            "reference_label_counts": reference_summary.get("label_counts"),
        },
        "rubric_upgrade": [
            "Keep famous human works as negative controls.",
            "Report non-zero human-reference AI-likelihood as detector pressure, not proof.",
            "Reject thresholds that catch the manuscript only by also flagging canon references.",
        ],
    }


def _long_context_architect(own: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    own_chapters = own.get("chapter_summary", {})
    ref_chapters = reference.get("chapter_summary", {})
    unstable_own = [
        path
        for path, summary in own_chapters.items()
        if float(summary.get("minimum_score", 0.0)) < 64.0
        or float(summary.get("average_ai_likelihood", 0.0)) > 28.0
    ]
    return {
        "lane": "long_context_architect",
        "question": "What must a whole-book or large-context model review that short windows cannot see?",
        "decision": "HOLD" if unstable_own else "PASS",
        "evidence": {
            "own_sections": len(own_chapters),
            "reference_sections": len(ref_chapters),
            "own_unstable_sections": unstable_own[:12],
            "own_unstable_section_count": len(unstable_own),
        },
        "rubric_upgrade": [
            "Add whole-book continuity checks for motif recurrence, unresolved promises, chapter-to-chapter emotional slope, and repeated voice drift.",
            "Use large-context models as reviewers over compressed book manifests before sending any full manuscript externally.",
            "Require a long-context packet to cite chapter ids and local artifact paths rather than rewriting prose directly.",
        ],
    }


def _embodied_senses_editor(own_rows: list[dict[str, Any]]) -> dict[str, Any]:
    weak_rows: list[dict[str, Any]] = []
    breakthrough_rows: list[dict[str, Any]] = []
    state_sequence: list[str] = []
    for row in own_rows:
        passage = str(row.get("passage", ""))
        sense_hits = _sense_hits(passage)
        physical_count = sum(1 for sense in ("sight", "sound", "smell", "taste", "touch") if sense in sense_hits)
        extra_count = sum(1 for sense in ("time", "magic_cryptography") if sense in sense_hits)
        if physical_count < 2 or extra_count < 1:
            weak_rows.append(
                {
                    "id": row["id"],
                    "chapter_path": row.get("chapter_path", ""),
                    "physical_sense_count": physical_count,
                    "time_or_magic_count": extra_count,
                    "senses": sorted(sense_hits),
                    "score": row["score"],
                }
            )
        if len(sense_hits) >= 5:
            breakthrough_rows.append(
                {
                    "id": row["id"],
                    "chapter_path": row.get("chapter_path", ""),
                    "sense_count": len(sense_hits),
                    "senses": sorted(sense_hits),
                    "score": row["score"],
                }
            )
        state_hits = _state_hits(passage)
        if state_hits:
            state_sequence.append(max(state_hits.items(), key=lambda item: len(item[1]))[0])

    state_switches = sum(1 for left, right in zip(state_sequence, state_sequence[1:]) if left != right)
    weak_ratio = round(len(weak_rows) / len(own_rows), 3) if own_rows else 0.0
    return {
        "lane": "embodied_senses_editor",
        "question": "Does the manuscript let the reader feel orientation, pressure, time, and body-state without writing to a checklist?",
        "decision": "PASS" if weak_ratio <= 0.35 and breakthrough_rows else "HOLD",
        "evidence": {
            "usage_rule": "instrumentation only; do not live by the rubric. The reader should feel the scene like driving a car, not count dashboard lights.",
            "source_doc": "content/book/ISEKAI_7_SENSE_CONTENT_VAULT.md",
            "weak_sense_window_count": len(weak_rows),
            "weak_sense_window_ratio": weak_ratio,
            "breakthrough_candidate_count": len(breakthrough_rows),
            "author_state_switch_count": state_switches,
            "weak_examples": weak_rows[:12],
            "breakthrough_examples": breakthrough_rows[:8],
        },
        "rubric_upgrade": [
            "Add seven-sense coverage as an embodied-prose instrument panel, not an AI-detection lane.",
            "Score Time as a sense because Marcus notices verification cadence and delays.",
            "Score Magic/Cryptography as Marcus's translation layer while preserving native lived meaning.",
            "Track author-state changes across chapters so the book does not sound written in one sitting.",
            "Use synesthesia and magical synesthesia as fantasy affordances in breakthrough scenes.",
            "Treat missing senses as a question for revision, not a command to stuff sensory words into every paragraph.",
        ],
    }


def _training_curator(own_rows: list[dict[str, Any]], detection: dict[str, Any]) -> dict[str, Any]:
    high_quality_ai_pressure = [
        {
            "id": row["id"],
            "score": row["score"],
            "ai_likelihood_score": row["ai_likelihood_score"],
            "chapter_path": row.get("chapter_path", ""),
        }
        for row in own_rows
        if float(row["score"]) >= 66.0 and float(row["ai_likelihood_score"]) >= 28.0
    ]
    return {
        "lane": "training_curator",
        "question": "Which passages are useful for separating quality from detector traces?",
        "decision": "PASS" if high_quality_ai_pressure else "HOLD",
        "evidence": {
            "high_quality_ai_pressure_count": len(high_quality_ai_pressure),
            "candidates": high_quality_ai_pressure[:12],
            "detector_status": detection.get("calibration_gate", {}).get("status", "UNKNOWN"),
        },
        "rubric_upgrade": [
            "Create revision pairs from passages that pass quality but carry detector pressure.",
            "Train quality improvement on before/after evidence, not on detector evasion.",
            "Store detector disagreements as labels for future public benchmark rows.",
        ],
    }


def run_council(
    *,
    own_path: Path = DEFAULT_BOOK_SWEEP,
    reference_path: Path = DEFAULT_REFERENCE_SWEEP,
    detection_path: Path = DEFAULT_DETECTION,
    blind_round_path: Path = DEFAULT_BLIND_ROUND,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    own = _load(own_path)
    reference = _load(reference_path)
    detection = _load(detection_path)
    blind_round = _load(blind_round_path)
    own_rows = list(own.get("rows", []))
    ref_rows = list(reference.get("rows", []))

    lanes = [
        _quality_editor(own_rows, ref_rows),
        _detector_skeptic(detection, blind_round),
        _human_reference_calibrator(detection, blind_round),
        _long_context_architect(own, reference),
        _embodied_senses_editor(own_rows),
        _training_curator(own_rows, detection),
    ]
    decisions = {lane["lane"]: lane["decision"] for lane in lanes}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "claim_boundary": (
            "Quality and AI detection are separate lanes. The council should pass strong writing quality while "
            "failing under-sensitive authorship detection until external/standard detector evidence exists."
        ),
        "mimicry_boundary": {
            "mimicry": "A detector can test observable human-like or machine-like patterns.",
            "humanity": "A detector cannot prove that text became human; it can only report evidence about artifacts.",
            "imagination": "Creative invention is evaluated through quality, coherence, surprise, and reader effect, not through authorship labels.",
            "embodiment": "Embodied sense is felt like driving a car; the rubric is an instrument panel, not the road.",
            "math_frame": "Treat real, not-real, and imaginary lanes as separate coordinates in the evaluation space.",
        },
        "source_artifacts": {
            "own_book": str(own_path),
            "reference_book": str(reference_path),
            "detection": str(detection_path),
            "blind_round": str(blind_round_path),
        },
        "triangulation_target": {
            "quality_lane": "PASS on high-quality prose",
            "standard_detector_lane": "SHOULD_FLAG known AI authorship when available",
            "local_detector_lane": "FAIL if it misses known AI controls",
            "mimicry_lane": "MEASURE pattern mimicry without claiming human essence",
            "imagination_lane": "REWARD creative construction when prose quality and continuity hold",
            "training_lane": "USE disagreements to build revision and detector-calibration rows",
        },
        "decisions": decisions,
        "council_lanes": lanes,
        "rubric_upgrade_packet": {
            "quality_weights": "unchanged pending human labels; add weak-floor and long-context reporting before changing weights",
            "authorship_detector": "separate external-detector adapter required before public authorship claims",
            "large_context_review": "generate compressed whole-book packets for long-context models; keep raw manuscript local unless explicitly approved",
            "next_test": "run open-source SuperAnnotate/Binoculars-style detector on public-domain, known-AI, and own-book windows side by side",
        },
        "promotion_decision": (
            "PROMOTE_QUALITY_GATE_ONLY"
            if decisions["quality_editor"] == "PASS" and decisions["detector_skeptic"] == "FAIL"
            else "HOLD"
        ),
    }

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "writing_rubric_council_latest.json"
    md_path = output_root / "writing_rubric_council_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Writing Rubric Council",
        "",
        f"- promotion decision: `{payload['promotion_decision']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        f"- mimicry boundary: {payload['mimicry_boundary']['mimicry']}",
        f"- imagination boundary: {payload['mimicry_boundary']['imagination']}",
        "",
        "## Council Lanes",
        "",
    ]
    for lane in payload["council_lanes"]:
        lines.extend(
            [
                f"### {lane['lane']}",
                "",
                f"- question: {lane['question']}",
                f"- decision: `{lane['decision']}`",
                f"- evidence: `{json.dumps(lane['evidence'], sort_keys=True)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Rubric Upgrade Packet",
            "",
            f"- quality weights: {payload['rubric_upgrade_packet']['quality_weights']}",
            f"- authorship detector: {payload['rubric_upgrade_packet']['authorship_detector']}",
            f"- large-context review: {payload['rubric_upgrade_packet']['large_context_review']}",
            f"- next test: {payload['rubric_upgrade_packet']['next_test']}",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--own-path", type=Path, default=DEFAULT_BOOK_SWEEP)
    parser.add_argument("--reference-path", type=Path, default=DEFAULT_REFERENCE_SWEEP)
    parser.add_argument("--detection-path", type=Path, default=DEFAULT_DETECTION)
    parser.add_argument("--blind-round-path", type=Path, default=DEFAULT_BLIND_ROUND)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_council(
        own_path=args.own_path,
        reference_path=args.reference_path,
        detection_path=args.detection_path,
        blind_round_path=args.blind_round_path,
        output_root=args.output_root,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
