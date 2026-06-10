#!/usr/bin/env python3
"""Build a cross-representation coding-language lens matrix for SCBE.

The output treats each concept as one frame and each code language / tongue as
a lens over that same frame. It preserves semantic, code, music, tokenizer,
binary transport, and workflow lanes instead of flattening them into prose.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = [
    REPO_ROOT / "training-data" / "sft" / "coding_system_full_v1_train.sft.jsonl",
    REPO_ROOT / "training-data" / "sft" / "coding_system_full_v1_holdout.sft.jsonl",
]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "representation_kaleidoscope"
EXPECTED_LANGUAGES = {"python", "typescript", "rust", "c", "julia", "haskell"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_payloads(paths: list[Path]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row.get("messages") or []
            if not messages:
                continue
            try:
                payload = json.loads(messages[-1]["content"])
            except (KeyError, json.JSONDecodeError, TypeError):
                continue
            if payload.get("schema_version") == "scbe_full_coding_system_answer_v1":
                payloads.append(payload)
    return payloads


def _lens_entry(payload: dict[str, Any]) -> dict[str, Any]:
    primary = payload.get("coding_primary") or {}
    music = payload.get("music_theory") or {}
    atomic = payload.get("atomic_tokenizer") or {}
    binary = payload.get("binary_transport") or {}
    contract = payload.get("code_lane_contract") or {}
    workflow = payload.get("workflow_composition") or {}
    return {
        "tongue": primary.get("tongue", ""),
        "tongue_name": primary.get("full_name", ""),
        "language": primary.get("language", ""),
        "domain": primary.get("domain", ""),
        "foundation_role": primary.get("foundation_role", ""),
        "mode": primary.get("mode", music.get("mode", "")),
        "phase_degrees": primary.get("phase_degrees"),
        "mirror_pair": primary.get("mirror_pair", ""),
        "sample_code": primary.get("sample_code", ""),
        "lexical_tokens": atomic.get("lexical_tokens", [])[:16],
        "stisa_field_names": atomic.get("stisa_field_names", []),
        "binary": {
            "byte_count": binary.get("byte_count", 0),
            "first_16_hex": binary.get("first_16_hex", []),
            "source_sha256": binary.get("source_sha256", ""),
            "token_sha256": binary.get("token_sha256", ""),
            "transport_tongue": binary.get("transport_tongue", ""),
        },
        "workflow": {
            "quarks": workflow.get("quarks", []),
            "resource_axes": workflow.get("resource_axes", []),
            "fallback_rule": workflow.get("fallback_rule", ""),
        },
        "contract": {
            "active_profile": contract.get("active_profile", ""),
            "reference_profile": contract.get("reference_profile", ""),
            "degradation_score": contract.get("degradation_score"),
            "mismatch_lanes": contract.get("mismatch_lanes", []),
            "operational_failure_risk": contract.get("operational_failure_risk", ""),
        },
    }


def _autosearch_pack(
    concept_id: str, intent: str, languages: list[str]
) -> dict[str, Any]:
    language_list = ", ".join(languages)
    return {
        "purpose": "auto_search_when_lens_drift_or_missing_evidence",
        "local_queries": [
            f"{concept_id} {intent} coding system",
            f"{concept_id} language lens {language_list}",
            f"{concept_id} semantic drift source_sha256 token_sha256",
        ],
        "web_queries": [
            f"Andrej Karpathy software 2.0 coding agents representation search {concept_id}",
            f"cross-language code representation benchmark {concept_id}",
            f"semantic equivalence across programming languages {concept_id}",
        ],
        "trigger_rules": [
            "Run local search when any expected language lens is missing.",
            "Run local search when source hashes change without matching test evidence.",
            "Run web search only for research context; do not treat web results as repo truth.",
        ],
    }


def build_kaleidoscope(paths: list[Path]) -> dict[str, Any]:
    payloads = _read_payloads(paths)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in payloads:
        concept = payload.get("concept") or {}
        grouped[str(concept.get("concept_id", "unknown"))].append(payload)

    frames: list[dict[str, Any]] = []
    for concept_id, items in sorted(grouped.items()):
        items = sorted(
            items,
            key=lambda item: (item.get("coding_primary") or {}).get("language", ""),
        )
        concept = items[0].get("concept") or {}
        lenses = [_lens_entry(item) for item in items]
        languages = sorted({lens["language"] for lens in lenses if lens["language"]})
        tongues = sorted({lens["tongue"] for lens in lenses if lens["tongue"]})
        intents = sorted(
            {str((item.get("concept") or {}).get("intent", "")) for item in items}
        )
        missing_languages = sorted(EXPECTED_LANGUAGES - set(languages))
        drift_flags = [
            {
                "language": lens["language"],
                "tongue": lens["tongue"],
                "mismatch_lanes": lens["contract"]["mismatch_lanes"],
                "risk": lens["contract"]["operational_failure_risk"],
            }
            for lens in lenses
            if lens["contract"]["mismatch_lanes"]
            or lens["contract"]["operational_failure_risk"] == "HIGH"
        ]
        frame = {
            "concept_id": concept_id,
            "command_key": concept.get("command_key", concept_id),
            "intent": concept.get("intent", ""),
            "phase_operation": concept.get("phase_operation", ""),
            "semantic_invariant_ok": len(intents) == 1 and not missing_languages,
            "languages": languages,
            "tongues": tongues,
            "missing_languages": missing_languages,
            "representation_axes": [
                "plain_english_intent",
                "code_language_lens",
                "sacred_tongue_metric_lane",
                "music_theory_mode",
                "atomic_tokenizer_rows",
                "binary_hex_transport",
                "workflow_composition",
                "autosearch_research_loop",
            ],
            "lenses": lenses,
            "drift_flags": drift_flags,
            "autosearch": _autosearch_pack(
                concept_id, str(concept.get("intent", "")), languages
            ),
        }
        frames.append(frame)

    coverage = {
        "concept_count": len(frames),
        "lens_count": sum(len(frame["lenses"]) for frame in frames),
        "complete_language_frames": sum(
            1 for frame in frames if not frame["missing_languages"]
        ),
        "expected_languages": sorted(EXPECTED_LANGUAGES),
    }
    return {
        "schema_version": "scbe_representation_kaleidoscope_v1",
        "created_at": _utc_now(),
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in paths],
        "coverage": coverage,
        "frames": frames,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Representation Kaleidoscope",
        "",
        "Each frame is one concept. Each lens is a code language plus Sacred Tongue, music, tokenizer, binary transport, and workflow view over the same concept.",
        "",
        "## Coverage",
        "",
        f"- Concepts: `{report['coverage']['concept_count']}`",
        f"- Lenses: `{report['coverage']['lens_count']}`",
        f"- Complete language frames: `{report['coverage']['complete_language_frames']}`",
        f"- Expected languages: `{', '.join(report['coverage']['expected_languages'])}`",
        "",
        "## Frames",
        "",
    ]
    for frame in report["frames"]:
        status = (
            "complete"
            if not frame["missing_languages"]
            else "missing " + ", ".join(frame["missing_languages"])
        )
        lines.extend(
            [
                f"### {frame['concept_id']}",
                "",
                f"- Intent: {frame['intent']}",
                f"- Phase operation: `{frame['phase_operation']}`",
                f"- Languages: `{', '.join(frame['languages'])}`",
                f"- Status: `{status}`",
                f"- Autosearch trigger: `{frame['autosearch']['purpose']}`",
                "",
                "| Lens | Language | Mode | Phase | SHA-256 | Code preview |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for lens in frame["lenses"]:
            preview = " ".join(str(lens["sample_code"]).strip().split())[:80].replace(
                "|", "\\|"
            )
            source_hash = str(lens["binary"]["source_sha256"])[:12]
            lines.append(
                f"| {lens['tongue']} / {lens['tongue_name']} | {lens['language']} | {lens['mode']} | "
                f"{lens['phase_degrees']} | `{source_hash}` | `{preview}` |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the SCBE representation kaleidoscope matrix."
    )
    parser.add_argument(
        "--input", action="append", default=[], help="JSONL input file. Repeatable."
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    inputs = [Path(item) for item in args.input] if args.input else DEFAULT_INPUTS
    inputs = [
        (REPO_ROOT / path).resolve() if not path.is_absolute() else path
        for path in inputs
    ]
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report = build_kaleidoscope(inputs)
    json_path = out_dir / "representation_kaleidoscope_latest.json"
    md_path = out_dir / "representation_kaleidoscope_latest.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(
        json.dumps(
            {
                "ok": True,
                "json": str(json_path),
                "markdown": str(md_path),
                "coverage": report["coverage"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
