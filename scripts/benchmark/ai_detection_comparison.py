#!/usr/bin/env python3
"""Compare AI-likelihood detector lanes across book benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "fiction_quality"
DEFAULT_BOOK_SWEEP = DEFAULT_OUTPUT_ROOT / "book_quality_sweep_latest.json"
DEFAULT_REFERENCE_SWEEP = (
    DEFAULT_OUTPUT_ROOT / "reference_books" / "frankenstein" / "sweep" / "book_quality_sweep_latest.json"
)
DEFAULT_BLIND_ROUND = DEFAULT_OUTPUT_ROOT / "fiction_quality_blind_round_latest.json"
SCHEMA_VERSION = "scbe_ai_detection_comparison_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _label_from_score(score: float) -> str:
    if score >= 70:
        return "likely_ai_generated"
    if score >= 40:
        return "mixed_or_uncertain"
    return "likely_human_or_human_edited"


def _summarize_rows(rows: list[dict[str, Any]], *, source_name: str) -> dict[str, Any]:
    labels = Counter(str(row.get("ai_detection_label", _label_from_score(row["ai_likelihood_score"]))) for row in rows)
    scores = [float(row["ai_likelihood_score"]) for row in rows]
    quality_scores = [float(row["score"]) for row in rows]
    return {
        "source_name": source_name,
        "sample_count": len(rows),
        "average_ai_likelihood": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "max_ai_likelihood": round(max(scores), 3) if scores else 0.0,
        "min_ai_likelihood": round(min(scores), 3) if scores else 0.0,
        "average_quality": round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0,
        "label_counts": dict(sorted(labels.items())),
        "highest_ai_likelihood_samples": [
            {
                "id": row["id"],
                "score": row["score"],
                "ai_likelihood_score": row["ai_likelihood_score"],
                "label": row.get("ai_detection_label", _label_from_score(row["ai_likelihood_score"])),
                "chapter_path": row.get("chapter_path", ""),
            }
            for row in sorted(rows, key=lambda item: item["ai_likelihood_score"], reverse=True)[:8]
        ],
    }


def _superannotate_detect(text: str, endpoint: str, timeout: int) -> dict[str, Any]:
    payload = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    generated_score = float(data.get("generated_score", 0.0))
    author = str(data.get("author", "Not sure"))
    return {
        "ai_likelihood_score": round(generated_score * 100.0, 3),
        "label": {
            "LLM Generated": "likely_ai_generated",
            "Probably LLM Generated": "likely_ai_generated",
            "Not sure": "mixed_or_uncertain",
            "Probably human written": "likely_human_or_human_edited",
            "Human": "likely_human_or_human_edited",
        }.get(author, "mixed_or_uncertain"),
        "raw": data,
    }


def _run_superannotate_sample(
    rows: list[dict[str, Any]],
    *,
    source_name: str,
    endpoint: str,
    timeout: int,
    max_samples: int,
) -> dict[str, Any]:
    detected: list[dict[str, Any]] = []
    for row in rows[:max_samples]:
        detection = _superannotate_detect(str(row.get("passage", "")), endpoint, timeout)
        detected.append(
            {
                "id": row["id"],
                "score": row["score"],
                "ai_likelihood_score": detection["ai_likelihood_score"],
                "ai_detection_label": detection["label"],
                "chapter_path": row.get("chapter_path", ""),
                "external_raw": detection["raw"],
            }
        )
    return _summarize_rows(detected, source_name=source_name)


def compare_detection(
    *,
    own_path: Path = DEFAULT_BOOK_SWEEP,
    reference_path: Path = DEFAULT_REFERENCE_SWEEP,
    blind_round_path: Path = DEFAULT_BLIND_ROUND,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    detector: str = "local",
    endpoint: str = "http://127.0.0.1:8080/detect",
    timeout: int = 20,
    max_external_samples: int = 12,
) -> dict[str, Any]:
    own = _load_json(own_path)
    reference = _load_json(reference_path)
    own_rows = list(own.get("rows", []))
    reference_rows = list(reference.get("rows", []))

    detector_status = {"ok": True, "error": None}
    if detector == "local":
        summaries = {
            "own_book": _summarize_rows(own_rows, source_name="The Six Tongues Protocol"),
            "reference_book": _summarize_rows(reference_rows, source_name="Frankenstein; or, the Modern Prometheus"),
        }
    elif detector == "superannotate-http":
        try:
            summaries = {
                "own_book": _run_superannotate_sample(
                    own_rows,
                    source_name="The Six Tongues Protocol",
                    endpoint=endpoint,
                    timeout=timeout,
                    max_samples=max_external_samples,
                ),
                "reference_book": _run_superannotate_sample(
                    reference_rows,
                    source_name="Frankenstein; or, the Modern Prometheus",
                    endpoint=endpoint,
                    timeout=timeout,
                    max_samples=max_external_samples,
                ),
            }
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            detector_status = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            summaries = {}
    else:
        raise ValueError(f"Unsupported detector: {detector}")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "detector": detector,
        "detector_status": detector_status,
        "detector_contract": {
            "local": "transparent stylometric GLTR-inspired heuristic already embedded in book sweeps",
            "superannotate-http": "expects a local SuperAnnotate generated_text_detector service with POST /detect",
        },
        "source_artifacts": {
            "own_book": str(own_path),
            "reference_book": str(reference_path),
            "blind_round": str(blind_round_path),
        },
        "summaries": summaries,
    }
    if detector == "local" and blind_round_path.exists():
        blind = _load_json(blind_round_path)
        known_ai = blind.get("groups", {}).get("known_ai_writing", {})
        public_domain = blind.get("groups", {}).get("public_domain", {})
        false_negatives = int(known_ai.get("false_negative_count", 0) or 0)
        public_false_positives = int(public_domain.get("false_positive_or_uncertain_count", 0) or 0)
        payload["calibration_gate"] = {
            "status": "UNDER_SENSITIVE" if false_negatives else "CALIBRATED_FOR_CURRENT_CONTROLS",
            "known_ai_false_negative_count": false_negatives,
            "public_domain_false_positive_or_uncertain_count": public_false_positives,
            "known_ai_average_ai_likelihood": known_ai.get("ai_likelihood_average"),
            "public_domain_average_ai_likelihood": public_domain.get("ai_likelihood_average"),
            "verdict": (
                (
                    "Local detector catches generic generated text but misses grounded or edited AI. "
                    "Do not use it as proof of authorship."
                )
                if false_negatives
                else "Local detector passed the current tiny control set; still requires external validation."
            ),
        }
    if summaries:
        own_avg = summaries["own_book"]["average_ai_likelihood"]
        ref_avg = summaries["reference_book"]["average_ai_likelihood"]
        payload["comparison"] = {
            "own_minus_reference_ai_likelihood": round(own_avg - ref_avg, 3),
            "interpretation": "negative means own book looks less AI-like than the reference under this detector",
        }

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / f"ai_detection_comparison_{detector.replace('-', '_')}_latest.json"
    md_path = output_root / f"ai_detection_comparison_{detector.replace('-', '_')}_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AI Detection Comparison",
        "",
        f"- detector: `{payload['detector']}`",
        f"- detector ok: `{payload['detector_status']['ok']}`",
    ]
    if payload["detector_status"]["error"]:
        lines.append(f"- detector error: `{payload['detector_status']['error']}`")
    if "comparison" in payload:
        lines.append(
            f"- own minus reference AI-likelihood: `{payload['comparison']['own_minus_reference_ai_likelihood']}`"
        )
    if "calibration_gate" in payload:
        gate = payload["calibration_gate"]
        lines.extend(
            [
                f"- calibration status: `{gate['status']}`",
                f"- known AI false negatives: `{gate['known_ai_false_negative_count']}`",
                f"- verdict: {gate['verdict']}",
            ]
        )
    lines.extend(["", "## Summaries", ""])
    for summary in payload.get("summaries", {}).values():
        lines.extend(
            [
                f"### {summary['source_name']}",
                "",
                f"- samples: `{summary['sample_count']}`",
                f"- average quality: `{summary['average_quality']}`",
                f"- average AI-likelihood: `{summary['average_ai_likelihood']}`",
                f"- max AI-likelihood: `{summary['max_ai_likelihood']}`",
                f"- label counts: `{json.dumps(summary['label_counts'], sort_keys=True)}`",
                "",
            ]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--own-path", type=Path, default=DEFAULT_BOOK_SWEEP)
    parser.add_argument("--reference-path", type=Path, default=DEFAULT_REFERENCE_SWEEP)
    parser.add_argument("--blind-round-path", type=Path, default=DEFAULT_BLIND_ROUND)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--detector", choices=["local", "superannotate-http"], default="local")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/detect")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-external-samples", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = compare_detection(
        own_path=args.own_path,
        reference_path=args.reference_path,
        blind_round_path=args.blind_round_path,
        output_root=args.output_root,
        detector=args.detector,
        endpoint=args.endpoint,
        timeout=args.timeout,
        max_external_samples=args.max_external_samples,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if payload["detector_status"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
