#!/usr/bin/env python3
"""Build a golden-helix curriculum schedule over local SCBE training rows.

The output is a metadata schedule, not a duplicated corpus. Each scheduled row
points back to its source JSONL row by file, row index, and SHA-256. This lets
training jobs interleave coding, chemistry, governance, research, motion, and
tokenizer rows without flattening their domain identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "curriculum" / "golden_helix_curriculum_v1"
DEFAULT_LANES = ("coding", "chemistry", "governance", "research", "motion", "tokenizer")
DEFAULT_GLOBS = ("training-data/**/*.jsonl",)
DEFAULT_SKIP_SUBSTRINGS = (
    "/evals/",
    "/holdout",
    "_holdout",
    "_test.",
    "_eval.",
    "/intake/",
    "/curriculum/",
)
PHI = (1.0 + math.sqrt(5.0)) / 2.0
TAU = 2.0 * math.pi
GOLDEN_ANGLE_RAD = TAU / (PHI * PHI)
GOLDEN_ANGLE_DEG = 360.0 / (PHI * PHI)

LANE_KEYWORDS = {
    "chemistry": {
        "chemistry",
        "chemical",
        "smiles",
        "rdkit",
        "valence",
        "molecule",
        "organic",
        "aromatic",
        "heterocycle",
        "ionic",
        "acid",
        "drug",
    },
    "motion": {
        "motion",
        "mechanical",
        "trajectory",
        "drone",
        "mars",
        "robot",
        "assembly",
        "embodiment",
        "thrust",
        "dynamics",
    },
    "tokenizer": {
        "tokenizer",
        "tokenization",
        "binary",
        "hex",
        "byte",
        "bijective",
        "sacred",
        "tongue",
        "tongues",
        "ss1",
        "transport",
    },
    "coding": {
        "coding",
        "polyglot",
        "coder",
        "copilot",
        "python",
        "javascript",
        "typescript",
        "rust",
        "haskell",
        "mathematica",
        "stage6",
        "boss",
        "command_lattice",
        "command-lattice",
        "command_harmony",
        "command-harmony",
        "agentic",
        "scbe_instructions",
        "bijective_dsl",
        "aethercode",
        "instruction_tuning",
    },
    "governance": {
        "governance",
        "geoseal",
        "hydra",
        "security",
        "boundary",
        "allow",
        "deny",
        "quarantine",
        "audit",
        "policy",
    },
    "research": {
        "research",
        "proposal",
        "proposals",
        "darpa",
        "mathbac",
        "arxiv",
        "source",
        "evidence",
        "roadmap",
        "architecture",
    },
}


@dataclass(frozen=True)
class Candidate:
    source_path: str
    row_index: int
    row_sha256: str
    primary_lane: str
    bond_lanes: tuple[str, ...]
    labels: tuple[str, ...]
    difficulty: float


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _add_label(labels: set[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _add_label(labels, item)
        return
    text = str(value).strip().lower()
    if not text:
        return
    normalized = text.replace("\\", "/")
    labels.add(text)
    labels.add(normalized)
    stem = Path(normalized).stem.lower()
    if stem:
        labels.add(stem)
    splitter = normalized.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ")
    for token in splitter.split():
        token = "".join(ch for ch in token if ch.isalnum())
        if token:
            labels.add(token)


def record_labels(row: dict[str, Any], source_path: str) -> set[str]:
    """Build label set from STRUCTURAL metadata + path only.

    Free-text content fields (prompt/completion/text/etc.) are intentionally
    excluded so prose tokens like 'function' or 'api' don't dominate
    classification. Explicit structural signals (smiles, motion_assembly,
    semantic_token_bridge) still emit lane-direct labels.
    """
    labels: set[str] = set()
    for key in (
        "categories",
        "tags",
        "source",
        "source_type",
        "track",
        "name",
        "id",
        "domain",
        "record_type",
        "lane",
        "primary_lane",
    ):
        _add_label(labels, row.get(key))
    _add_label(labels, source_path)

    if row.get("smiles") or row.get("expected_family") or row.get("manual_valence_check"):
        labels.add("chemistry")
    if row.get("motion_assembly") or row.get("embodiment_passport"):
        labels.add("motion")
    if row.get("tokenizer") or row.get("binary") or row.get("semantic_token_bridge"):
        labels.add("tokenizer")
    if row.get("governance_decision") or row.get("policy") or row.get("audit_trail"):
        labels.add("governance")

    return labels


def classify_lane(labels: set[str], lanes: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    scores = Counter()
    for lane in lanes:
        keywords = LANE_KEYWORDS.get(lane, {lane})
        scores[lane] = len(labels.intersection(keywords))
    if not any(scores.values()):
        scores["research"] = 1

    best_score = max(scores.values())
    primary = sorted([lane for lane, score in scores.items() if score == best_score])[0]
    bonded = tuple(lane for lane, score in sorted(scores.items()) if score > 0)
    return primary, bonded


def difficulty_score(row: dict[str, Any], labels: set[str]) -> float:
    raw = row.get("difficulty", row.get("curriculum_difficulty", row.get("difficulty_score")))
    if isinstance(raw, (int, float)):
        if raw > 1:
            return min(1.0, float(raw) / 5.0)
        return max(0.0, min(1.0, float(raw)))

    payload = _stable_json(row)
    length_score = min(1.0, len(payload) / 4000.0)
    label_score = min(1.0, len(labels) / 32.0)
    return round(0.65 * length_score + 0.35 * label_score, 4)


def iter_jsonl_files(
    root: Path,
    include_globs: Iterable[str],
    skip_substrings: Iterable[str] = DEFAULT_SKIP_SUBSTRINGS,
) -> list[Path]:
    files: set[Path] = set()
    skip_lower = tuple(s.lower() for s in skip_substrings)
    for pattern in include_globs:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            posix_lower = path.as_posix().lower()
            if any(sub in posix_lower for sub in skip_lower):
                continue
            files.add(path)
    return sorted(files)


def source_stream_for_path(rel_path: str) -> str:
    """Derive a stable, lane-friendly stream label from a relative source path."""
    cleaned = rel_path.replace("\\", "/")
    if cleaned.endswith(".jsonl"):
        cleaned = cleaned[: -len(".jsonl")]
    cleaned = cleaned.replace(".sft", "")
    parts = [p for p in cleaned.split("/") if p]
    parts = [p.replace("-", "_").replace(" ", "_") for p in parts]
    return "_".join(parts).strip("_") or "unknown"


def load_candidates(
    root: Path,
    include_globs: Iterable[str],
    lanes: tuple[str, ...],
    skip_substrings: Iterable[str] = DEFAULT_SKIP_SUBSTRINGS,
    cap_per_file: int = 0,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in iter_jsonl_files(root, include_globs, skip_substrings):
        rel_path = path.relative_to(root).as_posix()
        kept = 0
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
            raw = line.strip()
            if not raw or raw.startswith("version https://git-lfs.github.com") or raw.startswith("oid sha256"):
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            labels = record_labels(row, rel_path)
            primary, bonds = classify_lane(labels, lanes)
            candidates.append(
                Candidate(
                    source_path=rel_path,
                    row_index=idx,
                    row_sha256=_sha256_text(_stable_json(row)),
                    primary_lane=primary,
                    bond_lanes=bonds,
                    labels=tuple(sorted(labels)[:64]),
                    difficulty=difficulty_score(row, labels),
                )
            )
            kept += 1
            if cap_per_file and kept >= cap_per_file:
                break
    return sorted(candidates, key=lambda item: (item.primary_lane, item.difficulty, item.source_path, item.row_index))


def golden_target_lane(index: int, lanes: tuple[str, ...]) -> tuple[str, float, float]:
    theta = (index * GOLDEN_ANGLE_RAD) % TAU
    lane_width = TAU / len(lanes)
    lane_index = int(theta / lane_width) % len(lanes)
    radius = PHI**lane_index
    return lanes[lane_index], math.degrees(theta), radius


def schedule_candidates(
    candidates: list[Candidate],
    lanes: tuple[str, ...],
    limit: int = 0,
    cap_per_lane: int = 0,
) -> list[dict[str, Any]]:
    queues = {lane: deque([candidate for candidate in candidates if candidate.primary_lane == lane]) for lane in lanes}
    if cap_per_lane > 0:
        for lane in lanes:
            while len(queues[lane]) > cap_per_lane:
                queues[lane].pop()
    total = sum(len(queue) for queue in queues.values())
    if limit > 0:
        total = min(total, limit)

    rows: list[dict[str, Any]] = []
    for index in range(total):
        target_lane, theta_deg, radius = golden_target_lane(index, lanes)
        lane = target_lane if queues[target_lane] else max(lanes, key=lambda item: len(queues[item]))
        candidate = queues[lane].popleft()
        rows.append(
            {
                **asdict(candidate),
                "curriculum_index": index,
                "helix_angle_deg": round(theta_deg, 6),
                "helix_radius": round(radius, 6),
                "helix_depth": index // len(lanes),
                "helix_lane": lane,
                "source_stream": source_stream_for_path(candidate.source_path),
                "target_lane": target_lane,
                "scheduled_lane": lane,
                "lane_match": target_lane == lane,
                "previous_row_sha256": "",
                "next_row_sha256": "",
            }
        )

    for index, row in enumerate(rows):
        if index:
            row["previous_row_sha256"] = rows[index - 1]["row_sha256"]
        if index + 1 < len(rows):
            row["next_row_sha256"] = rows[index + 1]["row_sha256"]
    return rows


def write_outputs(
    out_dir: Path, schedule: list[dict[str, Any]], lanes: tuple[str, ...], include_globs: tuple[str, ...]
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    schedule_path = out_dir / "schedule.jsonl"
    schedule_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in schedule) + "\n", encoding="utf-8")

    lane_counts = Counter(row["scheduled_lane"] for row in schedule)
    target_counts = Counter(row["target_lane"] for row in schedule)
    source_counts = Counter(row["source_path"] for row in schedule)
    stream_counts = Counter(row["source_stream"] for row in schedule)
    n_match = sum(1 for row in schedule if row["lane_match"])
    lane_match_rate = round(n_match / len(schedule), 4) if schedule else 0.0
    manifest = {
        "schema_version": "scbe_golden_helix_curriculum_v1",
        "description": "Deterministic golden-angle curriculum schedule over local SCBE training rows.",
        "phi": PHI,
        "golden_angle_deg": GOLDEN_ANGLE_DEG,
        "lanes": list(lanes),
        "include_globs": list(include_globs),
        "row_count": len(schedule),
        "lane_match_rate": lane_match_rate,
        "lane_counts": dict(sorted(lane_counts.items())),
        "target_lane_counts": dict(sorted(target_counts.items())),
        "source_file_count": len(source_counts),
        "source_stream_count": len(stream_counts),
        "top_sources": dict(source_counts.most_common(12)),
        "top_streams": dict(stream_counts.most_common(12)),
        "schedule_path": (
            schedule_path.relative_to(REPO_ROOT).as_posix() if out_dir.is_relative_to(REPO_ROOT) else str(schedule_path)
        ),
        "schedule_sha256": _sha256_text(schedule_path.read_text(encoding="utf-8")),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Golden Helix Curriculum v1",
                "",
                "This bundle schedules local SCBE training rows with a golden-angle helix.",
                "It stores metadata pointers only; source rows remain in their original JSONL files.",
                "",
                f"- row count: {manifest['row_count']}",
                f"- golden angle: {GOLDEN_ANGLE_DEG:.6f} degrees",
                f"- lanes: {', '.join(lanes)}",
                "",
                "Each row carries previous/next SHA-256 pointers so adjacent curriculum bonds can be audited.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build golden-helix local curriculum schedule")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to schedule; 0 means all rows")
    parser.add_argument(
        "--cap-per-file",
        type=int,
        default=0,
        help="Per-file row cap so one giant merged file does not dominate; 0 = no cap",
    )
    parser.add_argument(
        "--cap-per-lane",
        type=int,
        default=0,
        help="Per-lane row cap to force hard balance (matches helix intent); 0 = no cap",
    )
    parser.add_argument("--lane", action="append", dest="lanes", help="Lane name; repeat to override defaults")
    parser.add_argument("--include-glob", action="append", dest="include_globs", help="Repo-root-relative JSONL glob")
    parser.add_argument(
        "--skip-substring",
        action="append",
        dest="skip_substrings",
        help="Path substring to skip (lowercase, repeatable)",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    lanes = tuple(args.lanes or DEFAULT_LANES)
    include_globs = tuple(args.include_globs or DEFAULT_GLOBS)
    skip_substrings = tuple(args.skip_substrings or DEFAULT_SKIP_SUBSTRINGS)
    candidates = load_candidates(
        root, include_globs, lanes, skip_substrings=skip_substrings, cap_per_file=args.cap_per_file
    )
    schedule = schedule_candidates(candidates, lanes, limit=args.limit, cap_per_lane=args.cap_per_lane)
    manifest = write_outputs(out_dir, schedule, lanes, include_globs)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"golden helix curriculum: rows={manifest['row_count']} out={out_dir}")
    return 0


# Public alias so callers can import the implementation rule under its
# canonical name without depending on the private `schedule_candidates` symbol.
golden_helix_curriculum_order = schedule_candidates


if __name__ == "__main__":
    raise SystemExit(main())
