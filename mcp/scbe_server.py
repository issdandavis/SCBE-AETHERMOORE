#!/usr/bin/env python3
"""SCBE Cryptographic Toolkit MCP Server

Exposes Sacred Tongues, GeoSeal, Sacred Eggs, and Identity Cubes
as MCP tools for any AI client.

Usage:
    python mcp/scbe_server.py          # starts stdio MCP server
"""

import base64
import dataclasses
import json
import os
import sys

# Ensure project root is on sys.path for src.* imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from mcp.server.fastmcp import FastMCP

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    TONGUES,
    ConcentricRingPolicy,
    CrossTokenizer,
    Lexicons,
    TongueTokenizer,
    geoseal_decrypt,
    geoseal_encrypt,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEgg,
    SacredEggIntegrator,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_registry import (
    SacredEggRegistry,
)
from src.symphonic_cipher.scbe_aethermoore.genesis_protocol import (
    GenesisProtocol,
    IdentityCube,
    mint_identity_cube,
)

# ---------------------------------------------------------------------------
# Shared instances (initialized once at import time)
# ---------------------------------------------------------------------------

_lex = Lexicons()
_tok = TongueTokenizer(_lex)
_xt = CrossTokenizer(_tok)
_ring_policy = ConcentricRingPolicy()
_integrator = SacredEggIntegrator(_xt)
_genesis = GenesisProtocol(_integrator)

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "scbe",
    instructions="SCBE-AETHERMOORE Cryptographic Toolkit — Sacred Tongues, GeoSeal, Sacred Eggs, Identity Cubes",
)


# ── Resources ──────────────────────────────────────────────────────────────


@mcp.resource("scbe://tongues")
def resource_tongues() -> str:
    """List all 6 Sacred Tongues with their phi-weights and phases."""
    info = []
    for tg in TONGUES:
        canon = Lexicons._CANON[tg]
        info.append({
            "code": tg,
            "name": canon["name"],
            "domain": canon["domain"],
            "phase": CrossTokenizer.PHASE[tg],
            "weight_phdm": CrossTokenizer.WEIGHT_PHDM[tg],
            "weight_lws": CrossTokenizer.WEIGHT_LWS[tg],
        })
    return json.dumps(info, indent=2)


@mcp.resource("scbe://rings")
def resource_rings() -> str:
    """Concentric Ring Policy — 5 trust rings from core to edge."""
    rings = []
    for rmin, rmax, name, lat, sigs, powb, decay in ConcentricRingPolicy.RINGS:
        rings.append({
            "ring": name,
            "radius_range": [rmin, rmax],
            "max_latency_ms": lat,
            "required_signatures": sigs,
            "pow_bits": powb,
            "trust_decay_rate": decay,
        })
    return json.dumps(rings, indent=2)


# ── Tongue Tools ───────────────────────────────────────────────────────────


@mcp.tool()
def tongue_encode(tongue: str, data_b64: str) -> str:
    """Encode base64 bytes into Sacred Tongue tokens.

    Args:
        tongue: Sacred Tongue code (KO, AV, RU, CA, UM, DR)
        data_b64: Base64-encoded input bytes
    """
    if tongue not in TONGUES:
        return json.dumps({"error": f"Unknown tongue: {tongue}. Valid: {TONGUES}"})
    data = base64.b64decode(data_b64)
    tokens = _tok.encode_bytes(tongue, data)
    return json.dumps({"tongue": tongue, "tokens": tokens, "token_count": len(tokens)})


@mcp.tool()
def tongue_decode(tongue: str, tokens_text: str) -> str:
    """Decode Sacred Tongue tokens back to bytes (returned as base64).

    Args:
        tongue: Sacred Tongue code (KO, AV, RU, CA, UM, DR)
        tokens_text: Space-separated Sacred Tongue tokens
    """
    if tongue not in TONGUES:
        return json.dumps({"error": f"Unknown tongue: {tongue}. Valid: {TONGUES}"})
    tokens = _tok.normalize_token_stream(tokens_text)
    data = _tok.decode_tokens(tongue, tokens)
    return json.dumps({"tongue": tongue, "data_b64": base64.b64encode(data).decode(), "byte_count": len(data)})


@mcp.tool()
def cross_tokenize(src_tongue: str, dst_tongue: str, tokens_text: str) -> str:
    """Cross-encode tokens from one Sacred Tongue to another with HMAC attestation.

    Args:
        src_tongue: Source tongue code
        dst_tongue: Destination tongue code
        tokens_text: Space-separated tokens in the source tongue
    """
    if src_tongue not in TONGUES or dst_tongue not in TONGUES:
        return json.dumps({"error": f"Unknown tongue. Valid: {TONGUES}"})
    out_tokens, attest = _xt.retokenize(src_tongue, dst_tongue, tokens_text)
    return json.dumps({
        "src": src_tongue,
        "dst": dst_tongue,
        "tokens": out_tokens,
        "attestation": dataclasses.asdict(attest),
    })


# ── GeoSeal Tools ─────────────────────────────────────────────────────────


@mcp.tool()
def geoseal_seal(plaintext_b64: str, context: list[float], pk_kem_b64: str, sk_dsa_b64: str) -> str:
    """GeoSeal encrypt data with a context vector and PQC keys.

    Args:
        plaintext_b64: Base64-encoded plaintext
        context: List of floats (6D+ context vector)
        pk_kem_b64: Base64-encoded KEM public key
        sk_dsa_b64: Base64-encoded DSA signing key
    """
    env = geoseal_encrypt(plaintext_b64, context, pk_kem_b64, sk_dsa_b64)
    return json.dumps(env)


@mcp.tool()
def geoseal_unseal(envelope_json: str, context: list[float], sk_kem_b64: str, pk_dsa_b64: str) -> str:
    """GeoSeal decrypt a sealed envelope.

    Args:
        envelope_json: JSON string of the GeoSeal envelope (from geoseal_seal)
        context: List of floats (must match encryption context)
        sk_kem_b64: Base64-encoded KEM secret key
        pk_dsa_b64: Base64-encoded DSA verification key
    """
    env = json.loads(envelope_json)
    ok, pt = geoseal_decrypt(env, context, sk_kem_b64, pk_dsa_b64)
    if not ok or pt is None:
        return json.dumps({"success": False, "error": "Decryption failed or signature invalid"})
    return json.dumps({"success": True, "plaintext_b64": base64.b64encode(pt).decode()})


# ── Ring Classification ────────────────────────────────────────────────────


@mcp.tool()
def ring_classify(radius: float) -> str:
    """Classify a radius value into a concentric trust ring (core/inner/middle/outer/edge).

    Args:
        radius: Float in [0, 1) representing distance from core
    """
    result = _ring_policy.classify(radius)
    return json.dumps(result)


# ── Sacred Egg Tools ───────────────────────────────────────────────────────


@mcp.tool()
def egg_create(
    payload_b64: str,
    primary_tongue: str,
    glyph: str,
    hatch_condition_json: str,
    context: list[float],
    pk_kem_b64: str,
    sk_dsa_b64: str,
) -> str:
    """Create a Sacred Egg — GeoSeal-encrypted payload with ritual access conditions.

    Args:
        payload_b64: Base64-encoded payload bytes
        primary_tongue: Tongue identity bound to egg (KO/AV/RU/CA/UM/DR)
        glyph: Visual symbol for the egg
        hatch_condition_json: JSON dict of ritual requirements (ring, path, min_tongues, min_weight)
        context: 6D+ float context vector for GeoSeal binding
        pk_kem_b64: Base64-encoded KEM public key
        sk_dsa_b64: Base64-encoded DSA signing key
    """
    payload = base64.b64decode(payload_b64)
    hatch_condition = json.loads(hatch_condition_json)
    egg = _integrator.create_egg(payload, primary_tongue, glyph, hatch_condition, context, pk_kem_b64, sk_dsa_b64)
    return _integrator.to_json(egg)


@mcp.tool()
def egg_hatch(
    egg_json: str,
    context: list[float],
    agent_tongue: str,
    sk_kem_b64: str,
    pk_dsa_b64: str,
    ritual_mode: str = "solitary",
) -> str:
    """Hatch a Sacred Egg — attempt to decrypt under ritual conditions.

    Args:
        egg_json: JSON string of the Sacred Egg (from egg_create)
        context: Current 6D+ context vector
        agent_tongue: Agent's active Sacred Tongue
        sk_kem_b64: Base64-encoded KEM secret key
        pk_dsa_b64: Base64-encoded DSA verification key
        ritual_mode: "solitary", "triadic", or "ring_descent"
    """
    egg = _integrator.from_json(egg_json)
    result = _integrator.hatch_egg(egg, context, agent_tongue, sk_kem_b64, pk_dsa_b64, ritual_mode=ritual_mode)
    return json.dumps({
        "success": result.success,
        "reason": result.reason,
        "tokens": result.tokens,
        "attestation": result.attestation,
    })


@mcp.tool()
def egg_paint(egg_json: str, glyph: str = "", hatch_condition_json: str = "") -> str:
    """Paint an egg — change the shell (glyph/conditions) while keeping the yolk intact.

    Args:
        egg_json: JSON string of the Sacred Egg
        glyph: New visual symbol (empty = keep current)
        hatch_condition_json: New hatch condition JSON (empty = keep current)
    """
    egg = _integrator.from_json(egg_json)
    new_glyph = glyph if glyph else None
    new_cond = json.loads(hatch_condition_json) if hatch_condition_json else None
    painted = _integrator.paint_egg(egg, glyph=new_glyph, hatch_condition=new_cond)
    return _integrator.to_json(painted)


@mcp.tool()
def egg_register(egg_json: str, ttl_seconds: int = 0, db_path: str = "") -> str:
    """Register a Sacred Egg in the persistent SQLite registry.

    Args:
        egg_json: JSON string of the Sacred Egg
        ttl_seconds: Time-to-live in seconds (0 = no expiry)
        db_path: Custom DB path (empty = default ~/.scbe/sacred_eggs.db)
    """
    egg = _integrator.from_json(egg_json)
    registry = SacredEggRegistry(db_path=db_path or None)
    try:
        egg_id = registry.register(egg, ttl_seconds=ttl_seconds)
        return json.dumps({"egg_id": egg_id, "status": "SEALED", "ttl_seconds": ttl_seconds})
    finally:
        registry.close()


# ── Identity Cube Tools ───────────────────────────────────────────────────


@mcp.tool()
def cube_mint(
    payloads_b64: list[str],
    tongue: str,
    context: list[float],
    pk_kem_b64: str,
    sk_dsa_b64: str,
    sk_kem_b64: str,
    pk_dsa_b64: str,
    glyph: str = "hatchling",
) -> str:
    """Mint Identity Cubes for a batch of AIs via the Genesis Protocol.

    Creates Sacred Eggs from each payload, hatches them, and mints cubes.

    Args:
        payloads_b64: List of base64-encoded payloads (one per AI)
        tongue: Primary Sacred Tongue for the batch
        context: 6D+ context vector
        pk_kem_b64: KEM public key (for egg creation)
        sk_dsa_b64: DSA signing key (for egg creation)
        sk_kem_b64: KEM secret key (for hatching)
        pk_dsa_b64: DSA verification key (for hatching)
        glyph: Visual symbol for the batch
    """
    payloads = [base64.b64decode(p) for p in payloads_b64]
    batch_id, eggs = _genesis.create_batch(payloads, tongue, context, pk_kem_b64, sk_dsa_b64, glyph=glyph)
    cubes = _genesis.hatch_batch(batch_id, eggs, context, tongue, sk_kem_b64, pk_dsa_b64)
    results = []
    for cube in cubes:
        if cube is not None:
            results.append(dataclasses.asdict(cube))
        else:
            results.append(None)
    return json.dumps({"batch_id": batch_id, "cubes": results, "total": len(results)})


@mcp.tool()
def cube_verify(cube_json: str) -> str:
    """Verify an Identity Cube's hash integrity.

    Args:
        cube_json: JSON string of an IdentityCube (from cube_mint)
    """
    data = json.loads(cube_json)
    cube = IdentityCube(
        cube_id=data["cube_id"],
        tongue_affinity=data["tongue_affinity"],
        cube_vector=tuple(data["cube_vector"]),
        batch_id=data["batch_id"],
        batch_index=data["batch_index"],
        healpix_cell=data["healpix_cell"],
        morton_cell=data["morton_cell"],
        egg_id=data["egg_id"],
        born_at=data["born_at"],
    )
    valid = _genesis.verify_cube(cube)
    return json.dumps({"cube_id": cube.cube_id, "valid": valid})


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
