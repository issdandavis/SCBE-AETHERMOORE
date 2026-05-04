"""Poly-embedded tile/JEPA/LLM nodal mapping.

This is a deterministic test harness for the method, not a neural model. It
checks whether one concept can be embedded through synchronized tile, graph,
latent, token, Sacred Tongue, and binary-packet surfaces without breaking shared
invariants.

This lives under ``python/scbe`` on purpose because it composes the Python
``tile_lang`` and production training primitives before any canonical M6/Mesh
Foundry service wiring depends on it.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterable

from .atomic_tokenization import TONGUES
from .tile_lang import lang_at_tile, tile_key, tile_to_voxel6

PHI = (1.0 + math.sqrt(5.0)) / 2.0
SCHEMA_VERSION = "scbe_poly_embedded_jepa_v1"


@dataclass(frozen=True)
class TileNode:
    row: int
    col: int
    tongue: str
    tile: str
    voxel6: tuple[int, int, int, int, int, int]
    phi_weight: float


@dataclass(frozen=True)
class CodingSystem:
    system_id: str
    purpose: str
    surface: str
    production_ready: bool
    evidence: str


@dataclass(frozen=True)
class PolyEmbedding:
    schema_version: str
    concept: str
    masked_tile: str
    masked_tiles: tuple[str, ...]
    mask_ratio: float
    residual_lambda: float
    tile_node: TileNode
    graph_neighbors: tuple[str, ...]
    jepa_latent: tuple[float, ...]
    jepa_prediction: tuple[float, ...]
    llm_token_surface: tuple[str, ...]
    sacred_tongue_surface: str
    coding_systems: tuple[CodingSystem, ...]
    binary_packet_sha256: str
    invariants: tuple[str, ...]


CODING_SYSTEMS: tuple[CodingSystem, ...] = (
    CodingSystem(
        system_id="tile_lang",
        purpose="map tile coordinates to Sacred Tongue lanes and 6D voxels",
        surface="python/scbe/tile_lang.py",
        production_ready=True,
        evidence="tests/test_tile_lang.py",
    ),
    CodingSystem(
        system_id="sacred_tongue_syntax_alignment",
        purpose="align one coding concept across all six coding primaries",
        surface="scripts/training_data/build_sacred_tongue_syntax_alignment_sft.py",
        production_ready=False,
        evidence="experimental eval-only generator; not in production training profile",
    ),
    CodingSystem(
        system_id="bijective_reasoning_code_packet",
        purpose="packetize intent, route, code views, transport, verification, and merge geometry",
        surface="src/coding_spine/bijective_reasoning_code_packet.py",
        production_ready=True,
        evidence="tests/coding_spine/test_bijective_reasoning_code_packet.py",
    ),
    CodingSystem(
        system_id="geoshell_pair_agent",
        purpose="train Builder and Navigator separation with GeoSeal apply gates",
        surface="scripts/training_data/build_geoshell_pair_agent_sft.py",
        production_ready=True,
        evidence="tests/training/test_geoshell_pair_agent_sft.py",
    ),
    CodingSystem(
        system_id="code_prism",
        purpose="cross-language lookup and coding-spine interoperability",
        surface="config/code_prism/interoperability_matrix.json",
        production_ready=True,
        evidence="repo configuration surface used by code-prism scripts",
    ),
    CodingSystem(
        system_id="cassisivadan_opcode_table",
        purpose="Cassisivadan symbolic opcode facts and deterministic math lane",
        surface="python/scbe/ca_opcode_table.py",
        production_ready=True,
        evidence="CA opcode facts consumed by GeoShell gate-repair records",
    ),
    CodingSystem(
        system_id="agent_call_switchboard",
        purpose="reserve multi-agent tool/apply lanes before work starts",
        surface="src/coding_spine/agent_call_switchboard.py",
        production_ready=True,
        evidence="used by GeoShell pair-agent SFT builder",
    ),
    CodingSystem(
        system_id="lsp_diagnostic",
        purpose="machine-readable editor diagnostics for repair routing",
        surface="Language Server Protocol diagnostic packet",
        production_ready=False,
        evidence="concept block only; promote after concrete LSP adapter exists",
    ),
    CodingSystem(
        system_id="vim_operator_motion",
        purpose="compact operator/motion edit intent for tool use",
        surface="Vim-style edit packet",
        production_ready=False,
        evidence="concept block only; promote after concrete editor adapter exists",
    ),
    CodingSystem(
        system_id="binary_wave_tool_packet",
        purpose="byte-level transport receipt after semantic intent is validated",
        surface="SCBE binary-wave transport packet",
        production_ready=False,
        evidence="concept block only; promote after transport encoder/verifier exists",
    ),
)


@lru_cache(maxsize=1)
def tongue_phi_weights() -> dict[str, float]:
    """Return phi^n weights for the canonical Sacred Tongue order."""

    return {tongue: PHI**index for index, tongue in enumerate(TONGUES)}


@lru_cache(maxsize=1)
def normalized_tongue_weights() -> dict[str, float]:
    weights = tongue_phi_weights()
    total = sum(weights.values())
    return {tongue: weight / total for tongue, weight in weights.items()}


@lru_cache(maxsize=256)
def _node(row: int, col: int, layer: int = 0) -> TileNode:
    tongue = lang_at_tile(row, col)
    return TileNode(
        row=row,
        col=col,
        tongue=tongue,
        tile=tile_key(row, col),
        voxel6=tile_to_voxel6(row, col, layer),
        phi_weight=tongue_phi_weights()[tongue],
    )


@lru_cache(maxsize=256)
def nodal_neighbors(row: int, col: int, size: int = 6) -> tuple[TileNode, ...]:
    """Return local, same-tongue, and phi-spiral neighbors for a tile."""

    candidates = [
        ((row - 1) % size, col % size),
        ((row + 1) % size, col % size),
        (row % size, (col - 1) % size),
        (row % size, (col + 1) % size),
        ((row + 1) % size, (col + 5) % size),  # same diagonal tongue stripe
        ((row + 1) % size, (col + 2) % size),  # phi-spiral cross-lane edge
    ]
    return tuple(_node(r, c) for r, c in candidates)


def deterministic_masked_tiles(concept: str, mask_ratio: float, size: int = 6) -> tuple[str, ...]:
    """Derive a stable mask set from the concept and mask ratio."""

    if not 0.0 < mask_ratio <= 0.5:
        raise ValueError("mask_ratio must be in (0, 0.5] for this first stability gate")
    node_count = size * size
    mask_count = max(1, math.floor(node_count * mask_ratio))
    ranked = []
    for row in range(size):
        for col in range(size):
            tile = tile_key(row, col)
            digest = hashlib.sha256(f"{concept}|{mask_ratio:.6f}|{tile}".encode("utf-8")).hexdigest()
            ranked.append((digest, tile))
    return tuple(tile for _, tile in sorted(ranked)[:mask_count])


@lru_cache(maxsize=1)
def edge_weights() -> tuple[float, ...]:
    return (1.0, 1.0, 1.0, 1.0, 1.0 / (PHI**2), 1.0 / (PHI**3))


@lru_cache(maxsize=1)
def row_normalized_edge_weights() -> tuple[float, ...]:
    weights = edge_weights()
    total = sum(weights)
    return tuple(weight / total for weight in weights)


def safe_unnormalized_residual_lambda() -> float:
    """Conservative contraction bound for the 6-neighbor unnormalized update."""

    return 1.0 / sum(edge_weights())


def _hash_to_unit_interval(text: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}|{text}".encode("utf-8")).digest()
    integer = int.from_bytes(digest[:8], "big")
    return integer / float(2**64 - 1)


@lru_cache(maxsize=8192)
def semantic_latent(concept: str, node: TileNode, dims: int = 6) -> tuple[float, ...]:
    """Deterministically embed a concept at a tile node into a bounded latent."""

    tongue_weight = normalized_tongue_weights()[node.tongue]
    values = []
    for axis in range(dims):
        base = _hash_to_unit_interval(concept, f"{node.tile}|{node.tongue}|{axis}")
        centered = (base * 2.0) - 1.0
        values.append(round(centered * (1.0 + tongue_weight), 8))
    return tuple(values)


def predict_masked_latent(
    concept: str,
    masked_row: int,
    masked_col: int,
    *,
    residual_lambda: float = 0.25,
) -> tuple[float, ...]:
    """Predict a masked tile latent from row-normalized nodal neighbors."""

    if not 0.0 <= residual_lambda <= 1.0:
        raise ValueError("residual_lambda must stay in [0, 1] for normalized graph updates")
    neighbors = nodal_neighbors(masked_row, masked_col)
    weights = row_normalized_edge_weights()
    neighbor_latents = [semantic_latent(concept, neighbor) for neighbor in neighbors]
    dims = len(neighbor_latents[0])
    averaged = []
    for dim in range(dims):
        averaged.append(sum(weight * latent[dim] for weight, latent in zip(weights, neighbor_latents, strict=True)))
    current = semantic_latent(concept, _node(masked_row, masked_col))
    return tuple(round((1.0 - residual_lambda) * current[i] + residual_lambda * averaged[i], 8) for i in range(dims))


def predict_masked_latent_unnormalized(
    concept: str,
    masked_row: int,
    masked_col: int,
    *,
    residual_lambda: float | None = None,
) -> tuple[float, ...]:
    """Predict with raw edge weights; lambda is bounded by the exposed safe value."""

    max_lambda = safe_unnormalized_residual_lambda()
    if residual_lambda is None:
        residual_lambda = max_lambda * 0.95
    if not 0.0 <= residual_lambda <= max_lambda:
        raise ValueError("residual_lambda exceeds the safe unnormalized contraction bound")
    neighbors = nodal_neighbors(masked_row, masked_col)
    weights = edge_weights()
    neighbor_latents = [semantic_latent(concept, neighbor) for neighbor in neighbors]
    dims = len(neighbor_latents[0])
    raw = []
    for dim in range(dims):
        raw.append(sum(weight * latent[dim] for weight, latent in zip(weights, neighbor_latents, strict=True)))
    current = semantic_latent(concept, _node(masked_row, masked_col))
    return tuple(round((1.0 - residual_lambda) * current[i] + residual_lambda * raw[i], 8) for i in range(dims))


def _tokens_for_concept(concept: str) -> tuple[str, ...]:
    tokens = [token.lower() for token in concept.replace("-", " ").replace("_", " ").split() if token.strip()]
    return tuple(tokens[:12] or ("concept",))


def _packet_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def coding_system_ids(systems: tuple[CodingSystem, ...] = CODING_SYSTEMS) -> tuple[str, ...]:
    return tuple(system.system_id for system in systems)


def _coerce_coding_systems(rows: object) -> tuple[CodingSystem, ...]:
    systems = []
    if not isinstance(rows, (list, tuple)):
        return ()
    for row in rows:
        if isinstance(row, CodingSystem):
            systems.append(row)
        elif isinstance(row, dict):
            systems.append(
                CodingSystem(
                    system_id=str(row.get("system_id", "")),
                    purpose=str(row.get("purpose", "")),
                    surface=str(row.get("surface", "")),
                    production_ready=bool(row.get("production_ready", False)),
                    evidence=str(row.get("evidence", "")),
                )
            )
    return tuple(systems)


@lru_cache(maxsize=1)
def production_ready_coding_systems() -> tuple[CodingSystem, ...]:
    return tuple(system for system in CODING_SYSTEMS if system.production_ready)


def build_poly_embedding(
    concept: str,
    *,
    masked_row: int = 0,
    masked_col: int = 0,
    mask_ratio: float = 0.4,
    residual_lambda: float = 0.25,
    coding_systems: tuple[CodingSystem, ...] | None = None,
) -> PolyEmbedding:
    """Build one poly-embedded state for a concept and masked tile."""

    if not concept.strip():
        raise ValueError("concept is required")
    masked_tiles = deterministic_masked_tiles(concept, mask_ratio)
    if coding_systems is None:
        coding_systems = production_ready_coding_systems()
    if any(not system.production_ready for system in coding_systems):
        raise ValueError("training/eval packet cannot include non-production-ready coding systems by default")
    node = _node(masked_row, masked_col)
    latent = semantic_latent(concept, node)
    # TODO(jepa): replace this deterministic graph smoother with a learned
    # latent predictor after we have production-ready masked-tile training data.
    prediction = predict_masked_latent(
        concept,
        masked_row,
        masked_col,
        residual_lambda=residual_lambda,
    )
    neighbors = nodal_neighbors(masked_row, masked_col)
    payload = {
        "concept": concept,
        "tile": node.tile,
        "masked_tiles": masked_tiles,
        "tongue": node.tongue,
        "coding_system_ids": coding_system_ids(coding_systems),
        "latent": latent,
        "prediction": prediction,
        "mask_ratio": mask_ratio,
        "residual_lambda": residual_lambda,
    }
    return PolyEmbedding(
        schema_version=SCHEMA_VERSION,
        concept=concept,
        masked_tile=node.tile,
        masked_tiles=masked_tiles,
        mask_ratio=mask_ratio,
        residual_lambda=residual_lambda,
        tile_node=node,
        graph_neighbors=tuple(neighbor.tile for neighbor in neighbors),
        jepa_latent=latent,
        jepa_prediction=prediction,
        llm_token_surface=_tokens_for_concept(concept),
        sacred_tongue_surface=f"{node.tongue}:{concept}",
        coding_systems=coding_systems,
        binary_packet_sha256=_packet_hash(payload),
        invariants=(
            "tile_tongue_matches_grid",
            "latent_dimension_is_6",
            "prediction_dimension_matches_latent",
            "mask_ratio_lte_half",
            "masked_tiles_match_budget",
            "coding_systems_cover_core_surfaces",
            "binary_packet_matches_surfaces",
        ),
    )


def verify_poly_embedding(embedding: PolyEmbedding | dict[str, object]) -> dict[str, object]:
    """Verify that all embedding surfaces still agree."""

    if isinstance(embedding, PolyEmbedding):
        payload = asdict(embedding)
    else:
        payload = dict(embedding)
    node_raw = payload["tile_node"]
    node = TileNode(**node_raw) if isinstance(node_raw, dict) else node_raw
    expected_tongue = lang_at_tile(node.row, node.col)
    system_rows = payload.get("coding_systems") or ()
    coerced_systems = _coerce_coding_systems(system_rows)
    reconstruction_systems = coerced_systems or production_ready_coding_systems()
    try:
        reconstructed = build_poly_embedding(
            str(payload["concept"]),
            masked_row=node.row,
            masked_col=node.col,
            mask_ratio=float(payload.get("mask_ratio", 0.4)),
            residual_lambda=float(payload.get("residual_lambda", 0.25)),
            coding_systems=reconstruction_systems,
        )
        reconstruction_ok = True
    except ValueError:
        reconstructed = None
        reconstruction_ok = False
    system_ids = {
        row.get("system_id") if isinstance(row, dict) else getattr(row, "system_id", "") for row in system_rows
    }
    required_system_ids = {
        "tile_lang",
        "bijective_reasoning_code_packet",
        "geoshell_pair_agent",
        "code_prism",
        "cassisivadan_opcode_table",
        "agent_call_switchboard",
    }
    checks = {
        "tile_tongue_matches_grid": node.tongue == expected_tongue,
        "latent_dimension_is_6": len(payload["jepa_latent"]) == 6,
        "prediction_dimension_matches_latent": len(payload["jepa_prediction"]) == len(payload["jepa_latent"]),
        "coding_systems_are_production_ready": reconstruction_ok,
        "mask_ratio_lte_half": 0.0 < float(payload.get("mask_ratio", 0.0)) <= 0.5,
        "masked_tiles_match_budget": reconstruction_ok
        and tuple(payload.get("masked_tiles", ())) == reconstructed.masked_tiles,
        "coding_systems_cover_core_surfaces": required_system_ids.issubset(system_ids),
        "binary_packet_matches_surfaces": reconstruction_ok
        and payload["binary_packet_sha256"] == reconstructed.binary_packet_sha256,
        "sacred_tongue_surface_matches": str(payload["sacred_tongue_surface"]).startswith(f"{node.tongue}:"),
    }
    return {
        "ok": all(checks.values()),
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "failed": [name for name, ok in checks.items() if not ok],
    }


def jepa_llm_loss_mix(training_progress: float) -> dict[str, float]:
    """Latent-heavy early schedule; balanced by the end of a run."""

    if not 0.0 <= training_progress <= 1.0:
        raise ValueError("training_progress must be in [0, 1]")
    jepa = 0.75 - (0.25 * training_progress)
    return {
        "jepa_latent_weight": round(jepa, 6),
        "llm_decode_weight": round(1.0 - jepa, 6),
    }


def batch_verify(embeddings: Iterable[PolyEmbedding]) -> dict[str, object]:
    reports = [verify_poly_embedding(embedding) for embedding in embeddings]
    return {
        "ok": all(report["ok"] for report in reports),
        "count": len(reports),
        "failed_count": sum(1 for report in reports if not report["ok"]),
        "reports": reports,
    }
