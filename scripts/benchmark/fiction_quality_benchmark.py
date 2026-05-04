#!/usr/bin/env python3
"""Deterministic bootstrap benchmark for AI-generated fiction quality.

This is a local scoring harness, not a claim that heuristic judging replaces
human taste. Its job is to catch common AI-fiction failure modes and create
course-shaped feedback rows before a Kaggle/public benchmark is launched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "eval" / "fiction_quality_benchmark.v1.json"
DEFAULT_INPUT = REPO_ROOT / "training-data" / "evals" / "fiction_quality_seed.jsonl"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality"
SCHEMA_VERSION = "scbe_fiction_quality_benchmark_report_v1"

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")

GENERIC_AI_PHRASES = [
    "tapestry",
    "symphony of",
    "testament to",
    "whispers of",
    "dance of",
    "endless galaxies",
    "world would never be the same",
    "little did",
    "fate had chosen",
    "ancient prophecy",
    "magical and mysterious",
]

VAGUE_FILLER = {
    "thing",
    "things",
    "stuff",
    "somehow",
    "mysterious",
    "indescribable",
    "unimaginable",
    "everything",
    "something",
}

CONCRETE_ANCHORS = {
    "door",
    "floor",
    "glass",
    "rain",
    "clock",
    "station",
    "paper",
    "cup",
    "handle",
    "screen",
    "file",
    "desk",
    "lamp",
    "archive",
    "shelf",
    "ink",
    "breath",
    "window",
    "train",
}

PROGRESSION_MARKERS = {
    "then",
    "before",
    "after",
    "because",
    "but",
    "so",
    "therefore",
    "until",
    "when",
    "while",
}

EMOTIONAL_MARKERS = {
    "afraid",
    "relieved",
    "tired",
    "angry",
    "quiet",
    "tense",
    "warm",
    "cold",
    "laughed",
    "gasped",
    "understood",
    "missed",
    "mattered",
}

THOUGHT_TRACKS = {
    "emotional": EMOTIONAL_MARKERS,
    "sensory": {"cold", "warm", "wet", "rain", "glass", "breath", "dark", "sound", "light", "silent"},
    "action": {"stepped", "reached", "deleted", "typed", "leaned", "opened", "shut", "changed", "wrote", "listened"},
    "memory": {"old", "again", "before", "remembered", "arrival", "memory", "first", "third"},
    "decision": {"understood", "decided", "chose", "will", "never", "must", "here", "good", "stopped"},
}

TRACK_INSTRUMENTS = {
    "emotional": "strings",
    "sensory": "woodwinds",
    "action": "percussion",
    "memory": "piano",
    "decision": "brass",
}

NULL_SPACE_MARKERS = {
    "commitment": {"promise", "rule", "contract", "must", "will", "changed", "responsibility", "condition"},
    "witness": {"saw", "heard", "record", "proof", "evidence", "watched", "listened", "highlighted"},
    "boundary": {"door", "handle", "threshold", "locked", "safe", "closed", "opened", "window", "wall"},
    "pause_audit": {"stopped", "paused", "waited", "before", "again", "checked", "audit", "listened"},
    "invitation_choice": {"ask", "typed", "chose", "choice", "let", "allowed", "reached", "opened"},
}

AI_DETECTION_MARKERS = {
    "cliche_generation": set(GENERIC_AI_PHRASES),
    "assistant_disclaimer": {
        "as an ai",
        "i cannot",
        "i'm sorry",
        "it is important to",
        "in conclusion",
        "overall",
    },
    "synthetic_fiction_pressure": {
        "destiny",
        "chosen",
        "prophecy",
        "ancient",
        "mysterious",
        "galaxies",
        "secrets",
        "courage",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path = DEFAULT_INPUT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no} row must be an object")
        rows.append(obj)
    return rows


def _words(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in SENTENCE_RE.findall(text) if item.strip()]


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 3)


def _presence_ratio(needles: list[str], haystack: str) -> float:
    if not needles:
        return 1.0
    lowered = haystack.casefold()
    return sum(1 for item in needles if str(item).casefold() in lowered) / len(needles)


def _length_score(word_count: int, constraints: dict[str, Any]) -> float:
    min_words = int(constraints.get("min_words", 80) or 80)
    max_words = int(constraints.get("max_words", 300) or 300)
    if min_words <= word_count <= max_words:
        return 10.0
    if word_count < min_words:
        return 10.0 * max(0.0, word_count / max(1, min_words))
    over = word_count - max_words
    return max(0.0, 10.0 - (over / max(1, max_words)) * 10.0)


def _repetition_penalty(words: list[str]) -> float:
    if not words:
        return 5.0
    counts = Counter(word for word in words if len(word) > 3)
    repeated = sum(count - 1 for count in counts.values() if count > 2)
    return min(4.0, repeated * 0.35)


def _generic_phrase_penalty(text: str) -> float:
    lowered = text.casefold()
    return min(5.0, sum(1.0 for phrase in GENERIC_AI_PHRASES if phrase in lowered))


def _alliteration_stats(words: list[str]) -> dict[str, Any]:
    initials = [word[0] for word in words if word and word[0].isalpha() and len(word) > 2]
    if not initials:
        return {"runs": 0, "max_run": 0, "score": 5.0}
    runs = 0
    max_run = 1
    current = 1
    for prev, cur in zip(initials, initials[1:]):
        if cur == prev:
            current += 1
            if current == 2:
                runs += 1
            max_run = max(max_run, current)
        else:
            current = 1
    density = runs / max(1, len(initials))
    if max_run >= 5 or density > 0.18:
        score = 4.5
    elif runs == 0:
        score = 7.0
    elif density <= 0.10:
        score = 9.0
    else:
        score = 7.0
    return {"runs": runs, "max_run": max_run, "density": round(density, 4), "score": score}


def _thought_track_sheet(sentences: list[str]) -> dict[str, Any]:
    phrases: list[dict[str, Any]] = []
    durations: list[int] = []
    active_track_counts: list[int] = []
    track_totals = {name: 0 for name in THOUGHT_TRACKS}
    previous_tracks: set[str] = set()
    transitions = 0
    unresolved_dissonance = 0

    for index, sentence in enumerate(sentences, 1):
        words = set(_words(sentence))
        duration = max(1, len(words))
        active = {
            track: sorted(markers & words)
            for track, markers in THOUGHT_TRACKS.items()
            if markers & words
        }
        active_names = set(active)
        if previous_tracks and active_names != previous_tracks:
            transitions += 1
        previous_tracks = active_names
        for track in active:
            track_totals[track] += len(active[track])
        active_track_counts.append(len(active))
        durations.append(duration)
        chord = "+".join(TRACK_INSTRUMENTS[track] for track in active) or "rest"
        if "rest" == chord and duration > 12:
            unresolved_dissonance += 1
        phrases.append(
            {
                "phrase": index,
                "duration_words": duration,
                "active_tracks": active,
                "chord": chord,
            }
        )

    track_coverage = sum(1 for total in track_totals.values() if total > 0)
    avg_tracks = sum(active_track_counts) / len(active_track_counts) if active_track_counts else 0.0
    duration_variance = 0.0
    if durations:
        mean = sum(durations) / len(durations)
        duration_variance = sum((duration - mean) ** 2 for duration in durations) / len(durations)
    resolution_tracks = set(phrases[-1]["active_tracks"]) if phrases else set()
    has_resolution = bool({"decision", "action", "emotional"} & resolution_tracks)
    composition_score = _clamp_score(
        3.0
        + track_coverage * 0.9
        + min(1.2, avg_tracks * 0.45)
        + (1.0 if transitions >= 2 else 0.0)
        + (1.0 if has_resolution else 0.0)
        - min(2.0, unresolved_dissonance * 0.75)
        - (0.6 if duration_variance > 120 else 0.0)
    )
    return {
        "track_totals": track_totals,
        "track_coverage": track_coverage,
        "average_tracks_per_phrase": round(avg_tracks, 3),
        "transitions": transitions,
        "duration_variance": round(duration_variance, 3),
        "has_resolution": has_resolution,
        "unresolved_dissonance": unresolved_dissonance,
        "composition_score": composition_score,
        "phrases": phrases,
    }


def _sentence_length_variance(sentences: list[str]) -> float:
    lengths = [len(_words(sentence)) for sentence in sentences if sentence.strip()]
    if not lengths:
        return 0.0
    mean = sum(lengths) / len(lengths)
    return sum((length - mean) ** 2 for length in lengths) / len(lengths)


def _ai_likelihood_report(
    *,
    text: str,
    words: list[str],
    sentences: list[str],
    dimension_scores: dict[str, float],
    generic_penalty: float,
    vague_count: int,
    null_family_count: int,
    thought_track_sheet: dict[str, Any],
    alliteration: dict[str, Any],
) -> dict[str, Any]:
    """Local AI-likelihood signal.

    This is not a forensic AI detector. It is a transparent, GLTR-inspired
    stylometric lane that flags common generated-fiction artifacts and records
    false-positive risk on known human passages.
    """

    lowered = text.casefold()
    word_count = max(1, len(words))
    unique_ratio = len(set(words)) / word_count
    sentence_variance = _sentence_length_variance(sentences)

    marker_hits = {
        family: sorted(marker for marker in markers if marker in lowered)
        for family, markers in AI_DETECTION_MARKERS.items()
    }
    marker_count = sum(len(hits) for hits in marker_hits.values())

    cliche_signal = min(28.0, generic_penalty * 10.0 + len(marker_hits["cliche_generation"]) * 4.0)
    disclaimer_signal = min(20.0, len(marker_hits["assistant_disclaimer"]) * 10.0)
    synthetic_pressure = min(16.0, len(marker_hits["synthetic_fiction_pressure"]) * 2.2)
    vague_signal = min(14.0, (vague_count / word_count) * 240.0)
    low_specificity = max(0.0, 7.0 - float(dimension_scores["specificity_vs_ai_weirdness"])) * 2.2
    weak_anchor = max(0.0, 2 - null_family_count) * 5.0
    flat_track = max(0.0, 3 - int(thought_track_sheet["track_coverage"])) * 3.0
    over_smooth = 0.0
    if len(sentences) >= 4 and 8.0 <= sentence_variance <= 24.0 and 0.45 <= unique_ratio <= 0.72:
        over_smooth = 7.0
    rhythm_pressure = 4.0 if float(alliteration.get("density", 0.0)) > 0.14 else 0.0

    human_complexity_offset = 0.0
    if unique_ratio > 0.72:
        human_complexity_offset += 5.0
    if sentence_variance > 80:
        human_complexity_offset += 5.0
    if marker_count == 0 and generic_penalty == 0:
        human_complexity_offset += 4.0

    score = max(
        0.0,
        min(
            100.0,
            18.0
            + cliche_signal
            + disclaimer_signal
            + synthetic_pressure
            + vague_signal
            + low_specificity
            + weak_anchor
            + flat_track
            + over_smooth
            + rhythm_pressure
            - human_complexity_offset,
        ),
    )
    score = round(score, 3)
    if score >= 70:
        label = "likely_ai_generated"
    elif score >= 55:
        label = "mixed_or_uncertain"
    else:
        label = "likely_human_or_human_edited"

    return {
        "schema_version": "scbe_local_ai_likelihood_v1",
        "detector_family": "transparent_stylometric_gltr_inspired",
        "claim_boundary": (
            "Local heuristic signal only; use as a comparison lane and false-positive probe, "
            "not as proof of authorship."
        ),
        "ai_likelihood_score": score,
        "label": label,
        "signals": {
            "marker_hits": marker_hits,
            "generic_phrase_penalty": generic_penalty,
            "vague_filler_count": vague_count,
            "unique_word_ratio": round(unique_ratio, 4),
            "sentence_length_variance": round(sentence_variance, 3),
            "null_space_family_count": null_family_count,
            "thought_track_coverage": thought_track_sheet["track_coverage"],
            "over_smooth_signal": over_smooth,
            "human_complexity_offset": human_complexity_offset,
        },
    }


def score_row(row: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    prompt = str(row.get("prompt", ""))
    response = str(row.get("response", ""))
    constraints = row.get("constraints") if isinstance(row.get("constraints"), dict) else {}
    words = _words(response)
    sentences = _sentences(response)
    word_count = len(words)
    lowered = response.casefold()

    required_terms = [str(item) for item in constraints.get("required_terms", [])]
    forbidden_patterns = [str(item) for item in constraints.get("forbidden_patterns", [])]
    characters = [str(item) for item in constraints.get("characters", [])]

    required_ratio = _presence_ratio(required_terms, response)
    forbidden_hits = [item for item in forbidden_patterns if item.casefold() in lowered]
    character_ratio = _presence_ratio(characters, response)
    length_score = _length_score(word_count, constraints)

    prompt_adherence = _clamp_score((required_ratio * 6.0) + (length_score * 0.4) - len(forbidden_hits) * 2.0)

    progression = sum(1 for word in words if word in PROGRESSION_MARKERS)
    sentence_count = max(1, len(sentences))
    avg_sentence_len = word_count / sentence_count
    coherence_base = 5.5 + min(2.0, progression * 0.35)
    if 8 <= avg_sentence_len <= 28:
        coherence_base += 1.0
    if "somehow" in words or "for no reason" in lowered:
        coherence_base -= 1.5
    story_coherence = _clamp_score(coherence_base)

    character_continuity = _clamp_score(4.0 + character_ratio * 5.0 + min(1.0, len(characters) * 0.2))

    concrete_count = sum(1 for word in words if word in CONCRETE_ANCHORS)
    sensory_count = sum(1 for word in words if word in {"cold", "warm", "wet", "rain", "glass", "breath", "dark"})
    scene_grounding = _clamp_score(4.0 + min(3.0, concrete_count * 0.55) + min(2.0, sensory_count * 0.5))

    repetition_penalty = _repetition_penalty(words)
    generic_penalty = _generic_phrase_penalty(response)
    prose_naturalness = _clamp_score(8.5 - repetition_penalty - generic_penalty * 0.8)

    alliteration = _alliteration_stats(words)
    rhythm = _clamp_score(float(alliteration["score"]) + (1.0 if 10 <= avg_sentence_len <= 24 else -0.5))
    thought_track_sheet = _thought_track_sheet(sentences)
    thought_track_composition = float(thought_track_sheet["composition_score"])

    vague_count = sum(1 for word in words if word in VAGUE_FILLER)
    specificity = _clamp_score(7.0 + min(2.0, concrete_count * 0.3) - vague_count * 0.65 - generic_penalty)

    null_hits = {
        family: sorted(marker for marker in markers if marker in words)
        for family, markers in NULL_SPACE_MARKERS.items()
    }
    null_family_count = sum(1 for hits in null_hits.values() if hits)
    null_space_structure = _clamp_score(3.5 + null_family_count * 1.25 + min(1.0, progression * 0.15))

    emotion_count = sum(1 for word in words if word in EMOTIONAL_MARKERS)
    emotional_progression = _clamp_score(4.5 + min(3.0, emotion_count * 0.55) + min(1.5, progression * 0.25))

    ending = sentences[-1].lower() if sentences else ""
    ending_or_transition = _clamp_score(
        5.0
        + (2.0 if any(marker in ending for marker in ("understood", "changed", "opened", "typed", "reached")) else 0.0)
        + (1.0 if len(ending.split()) >= 6 else 0.0)
        - (2.0 if ending.endswith("same.") or "never be the same" in ending else 0.0)
    )

    dimension_scores = {
        "prompt_adherence": prompt_adherence,
        "story_coherence": story_coherence,
        "character_continuity": character_continuity,
        "scene_grounding": scene_grounding,
        "prose_naturalness": prose_naturalness,
        "rhythm_and_sound_control": rhythm,
        "thought_track_composition": thought_track_composition,
        "specificity_vs_ai_weirdness": specificity,
        "null_space_structure": null_space_structure,
        "emotional_progression": emotional_progression,
        "ending_or_transition": ending_or_transition,
    }
    ai_likelihood = _ai_likelihood_report(
        text=response,
        words=words,
        sentences=sentences,
        dimension_scores=dimension_scores,
        generic_penalty=generic_penalty,
        vague_count=vague_count,
        null_family_count=null_family_count,
        thought_track_sheet=thought_track_sheet,
        alliteration=alliteration,
    )
    rubric = config["rubric"]
    weighted = 0.0
    weight_total = 0.0
    for key, score in dimension_scores.items():
        weight = float(rubric[key]["weight"])
        weighted += score * weight
        weight_total += weight
    score_100 = round((weighted / weight_total) * 10.0, 3) if weight_total else 0.0
    min_pass = float(config.get("minimum_pass_score", 72.0))
    portfolio = float(config.get("portfolio_ready_score", 85.0))
    if score_100 >= portfolio:
        tier = "portfolio_ready"
        decision = "PASS"
    elif score_100 >= min_pass:
        tier = "course_ready"
        decision = "PASS"
    elif score_100 >= 55:
        tier = "revise"
        decision = "HOLD"
    else:
        tier = "do_not_train_without_revision"
        decision = "HOLD"

    feedback = []
    if forbidden_hits:
        feedback.append(f"Remove forbidden or generic prompt violations: {', '.join(forbidden_hits)}.")
    if generic_penalty:
        feedback.append("Replace generic AI-fiction phrases with concrete scene action.")
    if vague_count:
        feedback.append("Trade vague filler for specific objects, choices, and sensory anchors.")
    if alliteration["max_run"] >= 5:
        feedback.append("Reduce alliteration density so sound supports the scene instead of dominating it.")
    if thought_track_sheet["track_coverage"] < 3:
        feedback.append("Add another thought track so the passage has a fuller emotional, sensory, action, memory, or decision chord.")
    if null_family_count < 2:
        feedback.append("Add missing structure: commitment, witness, boundary, pause/audit, or invitation/choice.")
    if not feedback:
        feedback.append("Keep as a positive course example; ask for a targeted revision to preserve the strengths.")

    return {
        "id": str(row.get("id", "")),
        "decision": decision,
        "tier": tier,
        "score": score_100,
        "dimension_scores": dimension_scores,
        "ai_detection": ai_likelihood,
        "diagnostics": {
            "word_count": word_count,
            "sentence_count": len(sentences),
            "avg_sentence_len": round(avg_sentence_len, 3),
            "required_ratio": round(required_ratio, 3),
            "character_ratio": round(character_ratio, 3),
            "forbidden_hits": forbidden_hits,
            "generic_phrase_penalty": generic_penalty,
            "vague_filler_count": vague_count,
            "alliteration": alliteration,
            "thought_track_sheet": thought_track_sheet,
            "null_space_marker_hits": null_hits,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        },
        "course_feedback": feedback,
    }


def run_benchmark(
    *,
    input_path: Path = DEFAULT_INPUT,
    config_path: Path = DEFAULT_CONFIG,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    config = load_config(config_path)
    rows = load_jsonl(input_path)
    results = [score_row(row, config) for row in rows]
    average = round(sum(item["score"] for item in results) / len(results), 3) if results else 0.0
    pass_count = sum(1 for item in results if item["decision"] == "PASS")
    payload_core = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "benchmark_id": config["benchmark_id"],
        "claim_boundary": config["claim_boundary"],
        "input_path": str(input_path),
        "config_path": str(config_path),
        "row_count": len(rows),
        "average_score": average,
        "pass_count": pass_count,
        "hold_count": len(results) - pass_count,
        "minimum_pass_score": config["minimum_pass_score"],
        "portfolio_ready_score": config["portfolio_ready_score"],
        "results": results,
        "kaggle_shape": config["kaggle_shape"],
        "course_signal": config["course_signal"],
    }
    payload = {**payload_core, "report_hash": _sha256_json(payload_core)}
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "fiction_quality_benchmark_latest.json"
    md_path = output_root / "fiction_quality_benchmark_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AI Fiction Quality Benchmark",
        "",
        f"- benchmark: `{payload['benchmark_id']}`",
        f"- rows: `{payload['row_count']}`",
        f"- average score: `{payload['average_score']}`",
        f"- pass count: `{payload['pass_count']}`",
        f"- hold count: `{payload['hold_count']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        "",
        "## Rows",
        "",
    ]
    for row in payload["results"]:
        weak = sorted(row["dimension_scores"].items(), key=lambda item: item[1])[:3]
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- decision: `{row['decision']}`",
                f"- tier: `{row['tier']}`",
                f"- score: `{row['score']}`",
                f"- weakest dimensions: `{json.dumps(dict(weak), sort_keys=True)}`",
                f"- feedback: {' '.join(row['course_feedback'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Kaggle Shape",
            "",
            f"- task: {payload['kaggle_shape']['task']}",
            f"- public metric: {payload['kaggle_shape']['public_metric']}",
            f"- local metric: {payload['kaggle_shape']['local_metric']}",
            "",
            "## Course Signal",
            "",
            f"- lesson unit: {payload['course_signal']['lesson_unit']}",
            f"- promotion rule: {payload['course_signal']['promotion_rule']}",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_benchmark(input_path=args.input, config_path=args.config, output_root=args.output_root)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if payload["row_count"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
