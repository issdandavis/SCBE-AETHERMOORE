#!/usr/bin/env python3
"""SCBE-AETHERMOORE Unified MCP Orchestrator

Single server combining:
  - SCBE Cryptographic Toolkit (Sacred Tongues, GeoSeal, Sacred Eggs, Identity Cubes)
  - HYDRA Swarm Browser (6-agent Sacred Tongue browser control)
  - SFT Training Collector (every tool call becomes a training record)

Every tool call is automatically logged as an SFT training record so your
AI workforce gets smarter as a byproduct of normal work.

Usage:
    python mcp/orchestrator.py                    # stdio (Claude Code)
    python mcp/orchestrator.py --transport sse    # HTTP/SSE (Claude.ai connector)
    python mcp/orchestrator.py --transport sse --port 8100
"""

import base64
import dataclasses
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
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
)
from hydra.swarm_browser import SwarmBrowser, AGENTS
from src.symphonic_cipher.scbe_aethermoore.rosetta import (
    RosettaStone,
    LCDAProjector,
    DualEntropicDefenseEngine,
)

# ---------------------------------------------------------------------------
# Shared instances
# ---------------------------------------------------------------------------

_lex = Lexicons()
_tok = TongueTokenizer(_lex)
_xt = CrossTokenizer(_tok)
_ring_policy = ConcentricRingPolicy()
_integrator = SacredEggIntegrator(_xt)
_genesis = GenesisProtocol(_integrator)

# Rosetta-LCDA singletons
_rosetta = RosettaStone()
_lcda = LCDAProjector()
_dede = DualEntropicDefenseEngine()

# Swarm singleton
_swarm: Optional[SwarmBrowser] = None

# SFT training log directory
_SFT_DIR = os.path.join(_PROJECT_ROOT, "training", "sft_records")
os.makedirs(_SFT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# SFT Training Recorder
# ---------------------------------------------------------------------------

def _record_sft(tool_name: str, inputs: dict, output: str, success: bool = True):
    """Append an SFT training record. Every tool call becomes training data."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "inputs": inputs,
        "output_preview": output[:500] if len(output) > 500 else output,
        "output_length": len(output),
        "success": success,
    }
    # Daily log file
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = os.path.join(_SFT_DIR, f"sft_{date_str}.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "scbe-orchestrator",
    instructions=(
        "SCBE-AETHERMOORE Unified Orchestrator — Sacred Tongues, GeoSeal, "
        "Sacred Eggs, Identity Cubes, HYDRA Swarm Browser, and SFT Training. "
        "Every tool call is automatically logged as training data."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════
# SCBE CRYPTOGRAPHIC TOOLS
# ═══════════════════════════════════════════════════════════════════════════


@mcp.resource("scbe://tongues")
def resource_tongues() -> str:
    """List all 6 Sacred Tongues with phi-weights and phases."""
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
            "ring": name, "radius_range": [rmin, rmax],
            "max_latency_ms": lat, "required_signatures": sigs,
            "pow_bits": powb, "trust_decay_rate": decay,
        })
    return json.dumps(rings, indent=2)


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
    result = json.dumps({"tongue": tongue, "tokens": tokens, "token_count": len(tokens)})
    _record_sft("tongue_encode", {"tongue": tongue, "byte_count": len(data)}, result)
    return result


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
    result = json.dumps({"tongue": tongue, "data_b64": base64.b64encode(data).decode(), "byte_count": len(data)})
    _record_sft("tongue_decode", {"tongue": tongue, "token_count": len(tokens)}, result)
    return result


@mcp.tool()
def cross_tokenize(src_tongue: str, dst_tongue: str, tokens_text: str) -> str:
    """Cross-encode tokens between two Sacred Tongues with HMAC attestation.

    Args:
        src_tongue: Source tongue code
        dst_tongue: Destination tongue code
        tokens_text: Space-separated tokens in the source tongue
    """
    if src_tongue not in TONGUES or dst_tongue not in TONGUES:
        return json.dumps({"error": f"Unknown tongue. Valid: {TONGUES}"})
    out_tokens, attest = _xt.retokenize(src_tongue, dst_tongue, tokens_text)
    result = json.dumps({
        "src": src_tongue, "dst": dst_tongue,
        "tokens": out_tokens, "attestation": dataclasses.asdict(attest),
    })
    _record_sft("cross_tokenize", {"src": src_tongue, "dst": dst_tongue}, result)
    return result


@mcp.tool()
def geoseal_seal(plaintext_b64: str, context: list[float], pk_kem_b64: str, sk_dsa_b64: str) -> str:
    """GeoSeal encrypt data with context vector and PQC keys.

    Args:
        plaintext_b64: Base64-encoded plaintext
        context: List of floats (6D+ context vector)
        pk_kem_b64: Base64-encoded KEM public key
        sk_dsa_b64: Base64-encoded DSA signing key
    """
    env = geoseal_encrypt(plaintext_b64, context, pk_kem_b64, sk_dsa_b64)
    result = json.dumps(env)
    _record_sft("geoseal_seal", {"context_dim": len(context)}, result)
    return result


@mcp.tool()
def geoseal_unseal(envelope_json: str, context: list[float], sk_kem_b64: str, pk_dsa_b64: str) -> str:
    """GeoSeal decrypt a sealed envelope.

    Args:
        envelope_json: JSON string of the GeoSeal envelope
        context: List of floats (must match encryption context)
        sk_kem_b64: Base64-encoded KEM secret key
        pk_dsa_b64: Base64-encoded DSA verification key
    """
    env = json.loads(envelope_json)
    ok, pt = geoseal_decrypt(env, context, sk_kem_b64, pk_dsa_b64)
    if not ok or pt is None:
        result = json.dumps({"success": False, "error": "Decryption failed"})
        _record_sft("geoseal_unseal", {"context_dim": len(context)}, result, success=False)
        return result
    result = json.dumps({"success": True, "plaintext_b64": base64.b64encode(pt).decode()})
    _record_sft("geoseal_unseal", {"context_dim": len(context)}, result)
    return result


@mcp.tool()
def ring_classify(radius: float) -> str:
    """Classify a radius into a concentric trust ring (core/inner/middle/outer/edge).

    Args:
        radius: Float in [0, 1) representing distance from core
    """
    result = json.dumps(_ring_policy.classify(radius))
    _record_sft("ring_classify", {"radius": radius}, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SACRED EGG TOOLS
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def scbe_sacred_egg_create(
    payload_b64: str, primary_tongue: str, glyph: str,
    hatch_condition_json: str, context: list[float],
    pk_kem_b64: str, sk_dsa_b64: str,
) -> str:
    """Create a Sacred Egg — GeoSeal-encrypted payload with ritual access conditions.

    Args:
        payload_b64: Base64-encoded payload bytes
        primary_tongue: Tongue identity (KO/AV/RU/CA/UM/DR)
        glyph: Visual symbol for the egg
        hatch_condition_json: JSON dict of ritual requirements
        context: 6D+ float context vector
        pk_kem_b64: Base64 KEM public key
        sk_dsa_b64: Base64 DSA signing key
    """
    payload = base64.b64decode(payload_b64)
    hatch_condition = json.loads(hatch_condition_json)
    egg = _integrator.create_egg(payload, primary_tongue, glyph, hatch_condition, context, pk_kem_b64, sk_dsa_b64)
    result = _integrator.to_json(egg)
    _record_sft("scbe_sacred_egg_create", {
        "tongue": primary_tongue, "glyph": glyph, "payload_bytes": len(payload),
    }, result)
    return result


@mcp.tool()
def scbe_sacred_egg_hatch(
    egg_json: str, context: list[float], agent_tongue: str,
    sk_kem_b64: str, pk_dsa_b64: str, ritual_mode: str = "solitary",
) -> str:
    """Hatch a Sacred Egg — decrypt under ritual conditions.

    Args:
        egg_json: JSON string of the Sacred Egg
        context: Current 6D+ context vector
        agent_tongue: Agent's active Sacred Tongue
        sk_kem_b64: Base64 KEM secret key
        pk_dsa_b64: Base64 DSA verification key
        ritual_mode: "solitary", "triadic", or "ring_descent"
    """
    egg = _integrator.from_json(egg_json)
    hr = _integrator.hatch_egg(egg, context, agent_tongue, sk_kem_b64, pk_dsa_b64, ritual_mode=ritual_mode)
    result = json.dumps({
        "success": hr.success, "reason": hr.reason,
        "tokens": hr.tokens, "attestation": hr.attestation,
    })
    _record_sft("scbe_sacred_egg_hatch", {
        "egg_id": egg.egg_id, "tongue": agent_tongue, "ritual_mode": ritual_mode,
    }, result, success=hr.success)
    return result


@mcp.tool()
def egg_paint(egg_json: str, glyph: str = "", hatch_condition_json: str = "") -> str:
    """Paint an egg — change shell while keeping yolk intact.

    Args:
        egg_json: JSON string of the Sacred Egg
        glyph: New visual symbol (empty = keep current)
        hatch_condition_json: New hatch condition JSON (empty = keep current)
    """
    egg = _integrator.from_json(egg_json)
    new_glyph = glyph if glyph else None
    new_cond = json.loads(hatch_condition_json) if hatch_condition_json else None
    painted = _integrator.paint_egg(egg, glyph=new_glyph, hatch_condition=new_cond)
    result = _integrator.to_json(painted)
    _record_sft("egg_paint", {"egg_id": egg.egg_id}, result)
    return result


@mcp.tool()
def egg_register(egg_json: str, ttl_seconds: int = 0, db_path: str = "") -> str:
    """Register a Sacred Egg in the persistent SQLite registry.

    Args:
        egg_json: JSON string of the Sacred Egg
        ttl_seconds: Time-to-live (0 = no expiry)
        db_path: Custom DB path (empty = default)
    """
    egg = _integrator.from_json(egg_json)
    registry = SacredEggRegistry(db_path=db_path or None)
    try:
        egg_id = registry.register(egg, ttl_seconds=ttl_seconds)
        result = json.dumps({"egg_id": egg_id, "status": "SEALED", "ttl_seconds": ttl_seconds})
        _record_sft("egg_register", {"egg_id": egg_id, "ttl": ttl_seconds}, result)
        return result
    finally:
        registry.close()


@mcp.tool()
def cube_mint(
    payloads_b64: list[str], tongue: str, context: list[float],
    pk_kem_b64: str, sk_dsa_b64: str, sk_kem_b64: str, pk_dsa_b64: str,
    glyph: str = "hatchling",
) -> str:
    """Mint Identity Cubes for a batch of AIs via Genesis Protocol.

    Args:
        payloads_b64: List of base64-encoded payloads (one per AI)
        tongue: Primary Sacred Tongue for the batch
        context: 6D+ context vector
        pk_kem_b64: KEM public key
        sk_dsa_b64: DSA signing key
        sk_kem_b64: KEM secret key (for hatching)
        pk_dsa_b64: DSA verification key (for hatching)
        glyph: Visual symbol for the batch
    """
    payloads = [base64.b64decode(p) for p in payloads_b64]
    batch_id, eggs = _genesis.create_batch(payloads, tongue, context, pk_kem_b64, sk_dsa_b64, glyph=glyph)
    cubes = _genesis.hatch_batch(batch_id, eggs, context, tongue, sk_kem_b64, pk_dsa_b64)
    results = [dataclasses.asdict(c) if c else None for c in cubes]
    result = json.dumps({"batch_id": batch_id, "cubes": results, "total": len(results)})
    _record_sft("cube_mint", {"batch_size": len(payloads), "tongue": tongue}, result)
    return result


@mcp.tool()
def cube_verify(cube_json: str) -> str:
    """Verify an Identity Cube's hash integrity.

    Args:
        cube_json: JSON string of an IdentityCube
    """
    data = json.loads(cube_json)
    cube = IdentityCube(
        cube_id=data["cube_id"], tongue_affinity=data["tongue_affinity"],
        cube_vector=tuple(data["cube_vector"]), batch_id=data["batch_id"],
        batch_index=data["batch_index"], healpix_cell=data["healpix_cell"],
        morton_cell=data["morton_cell"], egg_id=data["egg_id"], born_at=data["born_at"],
    )
    valid = _genesis.verify_cube(cube)
    result = json.dumps({"cube_id": cube.cube_id, "valid": valid})
    _record_sft("cube_verify", {"cube_id": cube.cube_id}, result)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# HYDRA SWARM BROWSER TOOLS
# ═══════════════════════════════════════════════════════════════════════════


async def _ensure_swarm() -> SwarmBrowser:
    global _swarm
    if _swarm is None:
        dry_run = os.environ.get("SWARM_DRY_RUN", "1") == "1"
        _swarm = SwarmBrowser(
            provider_type=os.environ.get("SWARM_PROVIDER", "local"),
            model=os.environ.get("SWARM_MODEL", "local-model"),
            dry_run=dry_run,
        )
    if not _swarm._launched:
        await _swarm.launch()
    return _swarm


@mcp.tool()
async def hydra_swarm_launch(dry_run: bool = True) -> str:
    """Launch the 6-agent Sacred Tongue browser swarm.

    Args:
        dry_run: If True, no real browser (safe for testing)
    """
    global _swarm
    _swarm = SwarmBrowser(
        provider_type=os.environ.get("SWARM_PROVIDER", "local"),
        model=os.environ.get("SWARM_MODEL", "local-model"),
        dry_run=dry_run,
    )
    await _swarm.launch()
    result = json.dumps({"launched": True, "agents": list(AGENTS.keys()), "dry_run": dry_run})
    _record_sft("hydra_swarm_launch", {"dry_run": dry_run}, result)
    return result


@mcp.tool()
async def hydra_swarm_run_task(task_description: str) -> str:
    """Execute a web task via the full 6-agent swarm pipeline.

    KO (scout) plans, actions dispatch to specialized tongue agents.
    Roundtable consensus required for sensitive operations.

    Args:
        task_description: Natural language description of the web task
    """
    swarm = await _ensure_swarm()
    task_result = await swarm.execute_task(task_description)
    result = json.dumps(task_result, default=str)
    _record_sft("hydra_swarm_run_task", {"task": task_description}, result, success=task_result.get("success", False))
    return result


@mcp.tool()
async def hydra_swarm_navigate(url: str) -> str:
    """Navigate to URL via KO (scout) agent.

    Args:
        url: Target URL
    """
    swarm = await _ensure_swarm()
    nav_result = await swarm.navigate(url)
    result = json.dumps(nav_result, default=str)
    _record_sft("hydra_swarm_navigate", {"url": url}, result)
    return result


@mcp.tool()
async def hydra_swarm_screenshot() -> str:
    """Take screenshot via AV (vision) agent."""
    swarm = await _ensure_swarm()
    result = json.dumps(await swarm.screenshot(), default=str)
    _record_sft("hydra_swarm_screenshot", {}, result)
    return result


@mcp.tool()
async def hydra_swarm_get_content() -> str:
    """Extract page content via RU (reader) agent."""
    swarm = await _ensure_swarm()
    result = json.dumps(await swarm.get_content(), default=str)
    _record_sft("hydra_swarm_get_content", {}, result)
    return result


@mcp.tool()
async def hydra_swarm_click(selector: str) -> str:
    """Click element via CA (clicker) with Roundtable consensus.

    Args:
        selector: CSS selector or element description
    """
    swarm = await _ensure_swarm()
    result = json.dumps(await swarm.click(selector), default=str)
    _record_sft("hydra_swarm_click", {"selector": selector}, result)
    return result


@mcp.tool()
async def hydra_swarm_type(selector: str, text: str) -> str:
    """Type text via UM (typer) with Roundtable consensus.

    Args:
        selector: CSS selector or element description
        text: Text to type
    """
    swarm = await _ensure_swarm()
    result = json.dumps(await swarm.type_text(selector, text), default=str)
    _record_sft("hydra_swarm_type", {"selector": selector, "text_len": len(text)}, result)
    return result


@mcp.tool()
async def hydra_swarm_status() -> str:
    """Get swarm status — agents, tabs, governance."""
    if _swarm is None:
        return json.dumps({"launched": False})
    result = json.dumps(_swarm.get_status(), default=str)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SFT TRAINING TOOLS
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def training_append_sft_record(tool_name: str, instruction: str, response: str, score: float = 1.0) -> str:
    """Manually append an SFT training record.

    Use this to record high-quality instruction/response pairs from your
    work sessions for fine-tuning.

    Args:
        tool_name: Which tool or capability this trains
        instruction: The instruction/prompt (what was asked)
        response: The ideal response (what was produced)
        score: Quality score 0.0-1.0 (default 1.0)
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "instruction": instruction,
        "response": response[:2000],
        "score": max(0.0, min(1.0, score)),
        "source": "manual",
    }
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = os.path.join(_SFT_DIR, f"sft_{date_str}.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    result = json.dumps({"recorded": True, "file": log_path, "tool": tool_name})
    return result


@mcp.tool()
def training_daily_summary() -> str:
    """Get today's SFT training summary — how many records collected, by tool."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = os.path.join(_SFT_DIR, f"sft_{date_str}.jsonl")
    if not os.path.exists(log_path):
        return json.dumps({"date": date_str, "total_records": 0, "by_tool": {}})
    by_tool: dict[str, int] = {}
    total = 0
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                tool = rec.get("tool", "unknown")
                by_tool[tool] = by_tool.get(tool, 0) + 1
                total += 1
            except json.JSONDecodeError:
                continue
    return json.dumps({"date": date_str, "total_records": total, "by_tool": by_tool, "file": log_path})


@mcp.tool()
def training_list_waves() -> str:
    """List all SFT training log files (daily waves)."""
    files = sorted(Path(_SFT_DIR).glob("sft_*.jsonl"))
    waves = []
    for f in files:
        stat = f.stat()
        waves.append({
            "file": f.name,
            "date": f.stem.replace("sft_", ""),
            "size_kb": round(stat.st_size / 1024, 1),
        })
    return json.dumps({"wave_count": len(waves), "waves": waves, "directory": _SFT_DIR})


@mcp.tool()
def training_export_dataset(format: str = "jsonl") -> str:
    """Export all SFT records as a combined dataset for fine-tuning.

    Args:
        format: Output format ("jsonl" or "json")
    """
    all_records = []
    for f in sorted(Path(_SFT_DIR).glob("sft_*.jsonl")):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        all_records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    export_path = os.path.join(_SFT_DIR, f"sft_combined.{format}")
    with open(export_path, "w", encoding="utf-8") as fh:
        if format == "json":
            json.dump(all_records, fh, indent=2, ensure_ascii=False)
        else:
            for rec in all_records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return json.dumps({
        "exported": True, "total_records": len(all_records),
        "file": export_path, "format": format,
    })


# ═══════════════════════════════════════════════════════════════════════════
# ROSETTA-LCDA TOOLS
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
def rosetta_lookup(concept_id: str, lang_code: str) -> str:
    """Look up a concept's surface forms in a specific language.

    Args:
        concept_id: NSM prime name (e.g., "GOOD", "DANGER", "MOVE")
        lang_code: Language code (EN, ZH, JA, KO, TOKIPONA, ESPERANTO, LOJBAN, KO_ST, etc.)
    """
    forms = _rosetta.lookup(concept_id.upper(), lang_code.upper())
    result = json.dumps({"concept_id": concept_id.upper(), "lang": lang_code.upper(), "forms": forms})
    _record_sft("rosetta_lookup", {"concept_id": concept_id, "lang": lang_code}, result)
    return result


@mcp.tool()
def rosetta_translate(concept_id: str, src_lang: str, dst_lang: str) -> str:
    """Translate a concept between two languages with drift score.

    Args:
        concept_id: NSM prime name (e.g., "TRUST", "DANGER")
        src_lang: Source language code
        dst_lang: Destination language code
    """
    translation = _rosetta.translate(concept_id.upper(), src_lang.upper(), dst_lang.upper())
    result = json.dumps(translation, ensure_ascii=False)
    _record_sft("rosetta_translate", {"concept": concept_id, "src": src_lang, "dst": dst_lang}, result)
    return result


@mcp.tool()
def rosetta_add_mapping(concept_id: str, lang_code: str, forms_json: str) -> str:
    """Add a new concept-surface mapping (auto-logged as SFT).

    Args:
        concept_id: NSM prime name
        lang_code: Language code
        forms_json: JSON array of surface forms (e.g., '["hello", "hi"]')
    """
    forms = json.loads(forms_json)
    ok = _rosetta.add_mapping(concept_id.upper(), lang_code.upper(), forms)
    result = json.dumps({"concept_id": concept_id.upper(), "lang": lang_code.upper(), "forms": forms, "added": ok})
    _record_sft("rosetta_add_mapping", {"concept": concept_id, "lang": lang_code, "forms": forms}, result)
    return result


@mcp.tool()
def rosetta_lcda_project(context_text: str) -> str:
    """Project context text onto SCBE governance dimensions.

    Returns scores (0-1) for: boundary_risk, agent_authority,
    data_sensitivity, jurisdictional_scope, temporal_urgency.

    Args:
        context_text: The text to analyze for governance dimensions
    """
    scores = _lcda.project(context_text)
    composite = _lcda.composite_risk(context_text)
    result = json.dumps({"scores": scores, "composite_risk": composite})
    _record_sft("rosetta_lcda_project", {"text_length": len(context_text)}, result)
    # Also feed DEDE behavioral channel
    _dede.observe_action("lcda_project", scores)
    return result


@mcp.tool()
def rosetta_dede_signal() -> str:
    """Get current dual entropy defense signal.

    Returns behavioral entropy, governance entropy, regime classification,
    and recommended action (allow/sandbox/escalate/block).
    """
    signal = _dede.compute_signal()
    result = json.dumps(signal.to_dict())
    _record_sft("rosetta_dede_signal", {}, result)
    return result


@mcp.tool()
def rosetta_export(format: str = "jsonl") -> str:
    """Export full Rosetta concept + dimension database as SFT training data.

    Args:
        format: Output format ("jsonl" or "json")
    """
    sft_data = _rosetta.export_sft(format=format)
    export_path = os.path.join(_SFT_DIR, f"rosetta_export.{format}")
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(sft_data)
    result = json.dumps({
        "exported": True, "file": export_path, "format": format,
        "concept_count": len(_rosetta.list_concepts()),
    })
    _record_sft("rosetta_export", {"format": format}, result)
    return result


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SCBE-AETHERMOORE Unified MCP Orchestrator")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                        help="Transport mode: stdio (Claude Code) or sse (Claude.ai connector)")
    parser.add_argument("--port", type=int, default=8100, help="Port for SSE transport")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)
