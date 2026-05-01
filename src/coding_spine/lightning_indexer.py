"""Lightning-style sparse selector for agent harness candidates.

This is the SCBE-scale version of a sparse-attention indexer: score many
candidate blocks cheaply, keep only the small set an agent should inspect, and
return deterministic evidence for training/replay.
"""

from __future__ import annotations

import hashlib
import heapq
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "scbe_lightning_indexer_v1"


@dataclass(frozen=True)
class SparseCandidate:
    candidate_id: str
    text: str
    kind: str = "general"
    lane: str = "workspace"
    priority: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", (text or "").lower())
        if token not in {"the", "and", "for", "with", "from", "this", "that", "into", "onto"}
    }


def _candidate_from_raw(raw: dict[str, Any], index: int) -> SparseCandidate:
    text = str(raw.get("text") or raw.get("summary") or raw.get("content") or raw.get("path") or "")
    candidate_id = str(raw.get("candidate_id") or raw.get("id") or raw.get("path") or f"candidate-{index}")
    return SparseCandidate(
        candidate_id=candidate_id,
        text=text,
        kind=str(raw.get("kind") or raw.get("type") or "general"),
        lane=str(raw.get("lane") or raw.get("route") or "workspace"),
        priority=float(raw.get("priority") or raw.get("score_hint") or 0.0),
        metadata={k: v for k, v in raw.items() if k not in {"candidate_id", "id", "text", "summary", "content"}},
    )


def normalize_candidates(raw_candidates: list[dict[str, Any]]) -> list[SparseCandidate]:
    return [_candidate_from_raw(row, idx) for idx, row in enumerate(raw_candidates) if isinstance(row, dict)]


def _stable_noise(goal: str, candidate_id: str) -> float:
    digest = hashlib.sha256(f"{goal}\0{candidate_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF / 1000.0


def _hash_coord(seed: str, axis: str) -> float:
    digest = hashlib.sha256(f"{seed}\0{axis}".encode("utf-8")).hexdigest()
    unit = int(digest[:8], 16) / 0xFFFFFFFF
    return round((unit * 1.8) - 0.9, 6)


def _coerce_coords(value: Any) -> list[float] | None:
    if isinstance(value, str):
        try:
            value = [float(part.strip()) for part in value.split(",")]
        except ValueError:
            return None
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    coords: list[float] = []
    for item in value[:3]:
        try:
            coords.append(max(-0.99, min(0.99, float(item))))
        except (TypeError, ValueError):
            return None
    return coords


def _candidate_coords(candidate: SparseCandidate) -> list[float]:
    for key in ("spatial_coords", "octree_point", "coords", "embedding3d"):
        coords = _coerce_coords(candidate.metadata.get(key))
        if coords is not None:
            return coords
    seed = f"{candidate.lane}\0{candidate.kind}\0{candidate.text}\0{candidate.candidate_id}"
    return [_hash_coord(seed, "x"), _hash_coord(seed, "y"), _hash_coord(seed, "z")]


def _distance_3d(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def score_candidate(goal: str, candidate: SparseCandidate) -> dict[str, Any]:
    """Return a deterministic sparse-selection score with component evidence."""

    goal_tokens = _tokenize(goal)
    text_tokens = _tokenize(candidate.text)
    metadata_tokens = _tokenize(" ".join(str(v) for v in candidate.metadata.values() if isinstance(v, (str, int, float))))
    all_tokens = text_tokens | metadata_tokens
    overlap = goal_tokens & all_tokens
    coverage = len(overlap) / max(len(goal_tokens), 1)
    density = len(overlap) / max(math.sqrt(len(all_tokens) or 1), 1.0)
    priority = max(min(candidate.priority, 10.0), -10.0) / 20.0
    kind_boost = 0.08 if candidate.kind.lower() in {"tool", "route", "test", "code", "skill"} else 0.0
    lane_boost = 0.06 if any(token in candidate.lane.lower() for token in goal_tokens) else 0.0
    score = (coverage * 1.8) + (density * 0.6) + priority + kind_boost + lane_boost + _stable_noise(goal, candidate.candidate_id)
    return {
        "candidate_id": candidate.candidate_id,
        "score": round(score, 6),
        "components": {
            "coverage": round(coverage, 6),
            "density": round(density, 6),
            "priority": round(priority, 6),
            "kind_boost": round(kind_boost, 6),
            "lane_boost": round(lane_boost, 6),
        },
        "matched_tokens": sorted(overlap),
    }


def _blocks(candidates: list[SparseCandidate], block_size: int) -> list[list[SparseCandidate]]:
    size = max(int(block_size), 1)
    return [candidates[i : i + size] for i in range(0, len(candidates), size)]


def _ranked_candidate_row(candidate: SparseCandidate, scored: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        **scored,
        "candidate": asdict(candidate),
    }


def _channel_rows(
    goal: str,
    candidates: list[SparseCandidate],
    score_by_id: dict[str, dict[str, Any]],
    *,
    channel_budget: int,
) -> dict[str, list[dict[str, Any]]]:
    budget = max(int(channel_budget), 1)

    local = candidates[-budget:]
    global_anchors = heapq.nlargest(
        min(budget, len(candidates)),
        candidates,
        key=lambda candidate: (candidate.priority, len(_tokenize(candidate.text)), candidate.candidate_id),
    )
    semantic = heapq.nlargest(
        min(budget, len(candidates)),
        candidates,
        key=lambda candidate: (score_by_id[candidate.candidate_id]["score"], candidate.priority, candidate.candidate_id),
    )

    def rows(selected: list[SparseCandidate]) -> list[dict[str, Any]]:
        return [_ranked_candidate_row(candidate, score_by_id[candidate.candidate_id], idx) for idx, candidate in enumerate(selected, start=1)]

    return {
        "local_window": rows(local),
        "sparse_semantic": rows(semantic),
        "global_anchor": rows(global_anchors),
    }


def _multiview_projection(selected_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_lane: dict[str, list[str]] = {}
    by_kind: dict[str, list[str]] = {}
    by_token: dict[str, list[str]] = {}
    for row in selected_rows:
        candidate = row["candidate"]
        candidate_id = row["candidate_id"]
        by_lane.setdefault(candidate["lane"], []).append(candidate_id)
        by_kind.setdefault(candidate["kind"], []).append(candidate_id)
        for token in row.get("matched_tokens", []):
            by_token.setdefault(token, []).append(candidate_id)
    return {
        "schema_version": "scbe_sparse_multiview_projection_v1",
        "views": {
            "lane": by_lane,
            "kind": by_kind,
            "matched_token": by_token,
        },
    }


def _hybrid_attention_plan(
    channels: dict[str, list[dict[str, Any]]],
    octree_rows: list[dict[str, Any]],
    *,
    top_k: int,
    block_size: int,
    channel_budget: int,
) -> dict[str, Any]:
    """Describe how the selected rows should be packed into an agent context.

    This is an agent-harness analogue of hybrid long-context attention: keep a
    small dense recency window, retrieve sparse semantic matches, and pin a few
    global anchors that should not be lost during compaction.
    """

    dense_ids = [row["candidate_id"] for row in channels.get("local_window", [])]
    sparse_ids = [row["candidate_id"] for row in channels.get("sparse_semantic", [])]
    anchor_ids = [row["candidate_id"] for row in channels.get("global_anchor", [])]
    octree_ids = [row["candidate_id"] for row in octree_rows]
    ordered: list[str] = []
    for candidate_id in [*dense_ids, *sparse_ids, *octree_ids, *anchor_ids]:
        if candidate_id not in ordered:
            ordered.append(candidate_id)

    return {
        "schema_version": "scbe_hybrid_attention_plan_v1",
        "analogue": {
            "dense_local_attention": "local_window",
            "compressed_sparse_attention": "sparse_semantic",
            "heavily_compressed_attention": "global_anchor",
            "spatial_sparse_index": "octree_retrieval",
        },
        "budgets": {
            "top_k": max(int(top_k), 1),
            "block_size": max(int(block_size), 1),
            "channel_budget": max(int(channel_budget), 1),
        },
        "pack_order": ordered,
        "compaction_policy": [
            "keep local_window rows verbatim while the task is active",
            "summarize sparse_semantic rows by matched_tokens and score components",
            "use octree_retrieval rows for structural neighbors and non-nested nesting across lanes",
            "pin global_anchor rows across rolling compaction unless superseded by a higher-priority anchor",
        ],
    }


def _octree_retrieval_rows(
    goal: str,
    candidates: list[SparseCandidate],
    score_by_id: dict[str, dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Return nearest candidates in a deterministic sparse-octree analogue.

    Candidate metadata may provide ``spatial_coords``, ``octree_point``,
    ``coords``, or ``embedding3d``. If not present, a stable hash projection is
    used so the retrieval shape is still reproducible and trainable.
    """

    target = [
        _hash_coord(goal or "scbe-goal", "x"),
        _hash_coord(goal or "scbe-goal", "y"),
        _hash_coord(goal or "scbe-goal", "z"),
    ]
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        coords = _candidate_coords(candidate)
        distance = _distance_3d(target, coords)
        scored = score_by_id[candidate.candidate_id]
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "octree_point": coords,
                "target_point": target,
                "distance": round(distance, 6),
                "score": scored["score"],
                "candidate": asdict(candidate),
            }
        )
    rows.sort(key=lambda row: (row["distance"], -row["score"], row["candidate_id"]))
    return rows[: max(int(top_k), 1)]


def select_sparse_candidates(
    goal: str,
    raw_candidates: list[dict[str, Any]],
    *,
    top_k: int = 8,
    block_size: int = 16,
    block_multiplier: int = 3,
    channel_budget: int = 3,
) -> dict[str, Any]:
    """Select top candidates through a block-first sparse indexer.

    The implementation intentionally avoids sorting the whole candidate pool.
    It scores all candidates once, keeps top blocks via ``heapq.nlargest``, then
    keeps top candidates from those surviving blocks.
    """

    candidates = normalize_candidates(raw_candidates)
    k = max(int(top_k), 1)
    blocks = _blocks(candidates, block_size=max(block_size, 1))
    scored_blocks: list[dict[str, Any]] = []
    score_by_id: dict[str, dict[str, Any]] = {}

    for block_index, block in enumerate(blocks):
        scored = [score_candidate(goal, candidate) for candidate in block]
        for row in scored:
            score_by_id[row["candidate_id"]] = row
        block_score = max((row["score"] for row in scored), default=0.0)
        scored_blocks.append(
            {
                "block_id": f"block-{block_index}",
                "block_index": block_index,
                "candidate_count": len(block),
                "score": round(block_score, 6),
                "candidate_ids": [candidate.candidate_id for candidate in block],
            }
        )

    keep_blocks = min(len(scored_blocks), max(1, k * max(int(block_multiplier), 1)))
    selected_blocks = heapq.nlargest(keep_blocks, scored_blocks, key=lambda row: (row["score"], -row["block_index"]))
    selected_ids = {candidate_id for block in selected_blocks for candidate_id in block["candidate_ids"]}
    survivor_candidates = [candidate for candidate in candidates if candidate.candidate_id in selected_ids]
    selected = heapq.nlargest(
        min(k, len(survivor_candidates)),
        survivor_candidates,
        key=lambda candidate: (score_by_id[candidate.candidate_id]["score"], candidate.priority, candidate.candidate_id),
    )

    rows = []
    for rank, candidate in enumerate(selected, start=1):
        scored = score_by_id[candidate.candidate_id]
        rows.append(_ranked_candidate_row(candidate, scored, rank))

    channels = _channel_rows(goal, candidates, score_by_id, channel_budget=channel_budget)
    octree_rows = _octree_retrieval_rows(goal, candidates, score_by_id, top_k=min(k, max(channel_budget, 1)))
    return {
        "schema_version": SCHEMA_VERSION,
        "goal": goal,
        "candidate_count": len(candidates),
        "top_k": k,
        "block_size": max(int(block_size), 1),
        "selected_block_count": len(selected_blocks),
        "selected": rows,
        "selected_blocks": sorted(selected_blocks, key=lambda row: row["block_index"]),
        "context_channels": channels,
        "octree_retrieval": {
            "schema_version": "scbe_sparse_octree_retrieval_v1",
            "rows": octree_rows,
        },
        "hybrid_attention_plan": _hybrid_attention_plan(
            channels,
            octree_rows,
            top_k=k,
            block_size=max(int(block_size), 1),
            channel_budget=channel_budget,
        ),
        "multiview_projection": _multiview_projection(rows),
    }
