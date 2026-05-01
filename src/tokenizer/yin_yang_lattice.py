from __future__ import annotations

import hashlib
import math
from typing import Any

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

FRAME_TONGUES = {
    0: {"figure": "KO", "ground": "DR", "rotation_degrees": 0},
    1: {"figure": "DR", "ground": "KO", "rotation_degrees": 180},
}


def _transport_tongue(tongue: str) -> str:
    return tongue.strip().lower()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encode_channel(text: str, tongue: str) -> dict[str, Any]:
    transport = _transport_tongue(tongue)
    raw = text.encode("utf-8")
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, raw)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens).decode("utf-8")
    joined = " ".join(tokens)
    return {
        "tongue": tongue.upper(),
        "text_sha256": _sha256_text(text),
        "byte_count": len(raw),
        "token_count": len(tokens),
        "token_sha256": _sha256_text(joined),
        "roundtrip_ok": decoded == text,
        "tokens": tokens,
    }


def _s_curve_side(x: int, y: int, size: int) -> str:
    center = (size - 1) / 2.0
    nx = (x - center) / max(center, 1.0)
    ny = (y - center) / max(center, 1.0)
    # An S-curve threshold gives the two lobes a deterministic yin-yang split.
    threshold = 0.48 * math.sin(math.pi * ny)
    return "KO" if nx < threshold else "DR"


def _build_surface(size: int) -> list[list[str]]:
    return [[_s_curve_side(x, y, size) for x in range(size)] for y in range(size)]


def _rotate_180(surface: list[list[str]]) -> list[list[str]]:
    return [list(reversed(row)) for row in reversed(surface)]


def _surface_rows(surface: list[list[str]], *, frame: int) -> list[str]:
    figure = FRAME_TONGUES[frame]["figure"]
    ground = FRAME_TONGUES[frame]["ground"]
    figure_char = "K" if figure == "KO" else "D"
    ground_char = "." if ground == "DR" else ","
    return ["".join(figure_char if cell == figure else ground_char for cell in row) for row in surface]


def _complementarity(surface: list[list[str]]) -> dict[str, Any]:
    rotated = _rotate_180(surface)
    total = 0
    flipped = 0
    center = len(surface) // 2
    for y, row in enumerate(surface):
        for x, cell in enumerate(row):
            if len(surface) % 2 == 1 and x == center and y == center:
                continue
            total += 1
            if rotated[y][x] != cell:
                flipped += 1
    return {
        "rotational_antisymmetry_score": round(flipped / max(total, 1), 6),
        "cell_count": total,
        "flipped_cell_count": flipped,
        "passes": flipped == total,
    }


def _frame_projection(surface: list[list[str]], frame: int) -> dict[str, Any]:
    figure = FRAME_TONGUES[frame]["figure"]
    ground = FRAME_TONGUES[frame]["ground"]
    figure_cells = sum(1 for row in surface for cell in row if cell == figure)
    ground_cells = sum(1 for row in surface for cell in row if cell == ground)
    return {
        "frame": frame,
        "rotation_degrees": FRAME_TONGUES[frame]["rotation_degrees"],
        "figure_tongue": figure,
        "ground_tongue": ground,
        "figure_cells": figure_cells,
        "ground_cells": ground_cells,
        "figure_ground_balance": round(figure_cells / max(figure_cells + ground_cells, 1), 6),
        "surface_preview": _surface_rows(surface, frame=frame),
    }


def build_yin_yang_dual_packet(
    *,
    ko_text: str,
    dr_text: str,
    size: int = 9,
    active_frame: int = 0,
) -> dict[str, Any]:
    if active_frame not in FRAME_TONGUES:
        raise ValueError("active_frame must be 0 or 1")
    if size < 5 or size % 2 == 0:
        raise ValueError("size must be an odd integer >= 5")

    channels = {
        "KO": _encode_channel(ko_text, "KO"),
        "DR": _encode_channel(dr_text, "DR"),
    }
    surface = _build_surface(size)
    active = FRAME_TONGUES[active_frame]["figure"]
    inactive = FRAME_TONGUES[active_frame]["ground"]
    payload_material = "|".join(
        [
            "scbe-yin-yang-dual-token-v1",
            channels["KO"]["text_sha256"],
            channels["DR"]["text_sha256"],
            str(size),
            str(active_frame),
        ]
    )
    packet_sha256 = _sha256_text(payload_material)
    packet_id = f"yy1-{packet_sha256[:16]}"
    route_cost = round((channels["KO"]["byte_count"] + channels["DR"]["byte_count"]) / max(size * size * 2.0, 1.0), 6)
    return {
        "schema_version": "scbe-yin-yang-dual-token-v1",
        "identity": {
            "packet_id": packet_id,
            "profile": "industry-sample",
            "producer": "SCBE-AETHERMOORE GeoSeal CLI",
            "mission_id": "local-prototype",
            "asset_id": "space-agent-sim-001",
            "environment": "digital-simulation",
        },
        "role": "view_dependent_semantic_execution_lattice",
        "boundary": {
            "tokenizer_role": "semantic transport and reversible cross-domain mapping",
            "not_security_boundary": True,
            "security_layers": [
                "governance gates",
                "crypto/sealing",
                "capability controls",
                "execution policy",
                "verification layers",
            ],
        },
        "active_frame": active_frame,
        "active_tongue": active,
        "inactive_tongue": inactive,
        "conjugate_pair": {
            "figure_frame_0": "KO",
            "figure_frame_1": "DR",
            "interpretation": "KO intent/control-flow and DR structure/transform share one complementary surface.",
        },
        "channels": channels,
        "surface": {
            "model": "yin_yang_s_curve_complementary_mask",
            "size": size,
            "cell_encoding": {"KO": "control_flow_lobe", "DR": "structure_transform_lobe"},
            "frames": [_frame_projection(surface, 0), _frame_projection(surface, 1)],
            "complementarity": _complementarity(surface),
        },
        "microstructure": {
            "version": 1,
            "ridge_model": "digital_sideband_fields",
            "route_cost": route_cost,
            "confidence": 0.82,
            "terrain_risk": 0.18,
            "retry_count": 0,
            "map_tile_id": "sim://mars/jezero/ridge-0001",
            "home_vector": {"frame": "local_ned", "x_m": -14.2, "y_m": 3.6, "z_m": 0.0},
            "checksum_sha256": packet_sha256,
        },
        "routing": {
            "planner_view": "KO",
            "verifier_view": "DR",
            "allowed_consumers": ["planner", "verifier", "governance", "training"],
            "delivery_mode": "store-and-forward-compatible",
        },
        "governance": {
            "risk_tier": "LOW",
            "policy_mode": "observe",
            "requires_human_ack": False,
            "action_boundary": "semantic_packet_only",
            "promotion_requirements": [
                "all channels roundtrip",
                "rotational antisymmetry score equals 1.0",
                "external GeoSeal policy permits execution",
            ],
        },
        "crypto_envelope": {
            "payload_state": "plaintext_sample",
            "production_expectation": "encrypt sensitive channel payloads and sign canonical packet bytes",
            "payload_hashes": {
                "KO": channels["KO"]["text_sha256"],
                "DR": channels["DR"]["text_sha256"],
            },
            "signature": {
                "algorithm": "not-applied-in-sample",
                "key_id": "sample-only",
                "signature_b64": "",
            },
        },
        "telemetry": {
            "bandwidth_class": "low",
            "latency_tolerance": "delayed",
            "audit_replay": True,
            "operator_notes": "Sample packet shows digital side-band structure; it is not a physical optical medium.",
        },
        "training_hooks": {
            "use_as": [
                "paired KO/DR route record",
                "frame-conditioned tokenizer example",
                "bijective reconstruction check",
            ],
            "promotion_gate": "both channels roundtrip and rotational antisymmetry score is 1.0",
        },
        "packet_sha256": packet_sha256,
    }


__all__ = ["build_yin_yang_dual_packet"]
