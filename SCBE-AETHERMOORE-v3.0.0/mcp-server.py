#!/usr/bin/env python3
"""
SCBE-AETHERMOORE MCP Server
===========================

Exposes the Six Sacred Tongues protocol and GeoSeal operations
via Model Context Protocol (MCP) for integration with Claude Code
and other MCP-compatible clients.

Tools provided:
- tongue_encode: Encode bytes to spell-text in a Sacred Tongue
- tongue_decode: Decode spell-text back to bytes
- tongue_xlate: Cross-translate between tongues with attestation
- tongue_blend: Stripe-blend data across multiple tongues
- geoseal_evaluate: Evaluate intent through GeoSeal access control
- geoseal_encrypt: Encrypt with geometric context binding
- geoseal_decrypt: Decrypt with context verification

Usage:
  python mcp-server.py

Or configure as MCP server in your client:
  {
    "mcpServers": {
      "scbe-aethermoore": {
        "command": "python",
        "args": ["path/to/mcp-server.py"]
      }
    }
  }

Patent Pending: USPTO #63/961,403
Author: Issac Daniel Davis
"""

import asyncio
import base64
import hashlib
import hmac
import json
import math
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# MCP Protocol Implementation (stdio-based)
# -----------------------------------------

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# Tongue metadata
TONGUE_INFO = {
    "KO": {"name": "Kor'aelin", "domain": "Nonce/Flow/Control", "phase": 0, "weight": 1.00},
    "AV": {"name": "Avali", "domain": "AAD/Context/I/O", "phase": 60, "weight": 1.618},
    "RU": {"name": "Runethic", "domain": "Salt/Binding/Policy", "phase": 120, "weight": 2.618},
    "CA": {"name": "Cassisivadan", "domain": "Ciphertext/Compute", "phase": 180, "weight": 4.236},
    "UM": {"name": "Umbroth", "domain": "Redaction/Security", "phase": 240, "weight": 6.854},
    "DR": {"name": "Draumric", "domain": "Auth Tags/Schema", "phase": 300, "weight": 11.090},
}

# Lexicon generation (16x16 = 256 tokens per tongue)
HI_NIBBLES = ["ka", "ke", "ki", "ko", "ku", "sa", "se", "si", "so", "su", "ra", "re", "ri", "ro", "ru", "za"]
LO_NIBBLES = ["na", "ne", "ni", "no", "nu", "la", "le", "li", "lo", "lu", "ta", "te", "ti", "to", "tu", "ma"]


def generate_lexicon(prefix: str) -> Tuple[List[str], Dict[str, int]]:
    """Generate 256 bijective tokens for a tongue."""
    tokens = []
    reverse = {}
    for i in range(256):
        hi = HI_NIBBLES[(i >> 4) & 0x0F]
        lo = LO_NIBBLES[i & 0x0F]
        token = f"{prefix.lower()}{hi}'{lo}"
        tokens.append(token)
        reverse[token] = i
    return tokens, reverse


# Pre-generate all lexicons
LEXICONS = {tg: generate_lexicon(tg) for tg in TONGUES}


def encode_bytes(tongue: str, data: bytes) -> List[str]:
    """Encode bytes to tongue tokens."""
    tokens, _ = LEXICONS[tongue]
    return [tokens[b] for b in data]


def decode_tokens(tongue: str, token_list: List[str]) -> bytes:
    """Decode tongue tokens to bytes."""
    _, reverse = LEXICONS[tongue]
    result = bytearray()
    for tok in token_list:
        tok = tok.strip()
        if not tok:
            continue
        # Handle prefixed tokens (e.g., "ko:kaka'na")
        if ":" in tok:
            _, tok = tok.split(":", 1)
        if tok not in reverse:
            raise ValueError(f"Unknown token '{tok}' for tongue {tongue}")
        result.append(reverse[tok])
    return bytes(result)


def xlate_tokens(src_tongue: str, dst_tongue: str, tokens: List[str]) -> Tuple[List[str], Dict]:
    """Cross-translate tokens between tongues."""
    # Decode from source
    data = decode_tokens(src_tongue, tokens)
    # Encode to destination
    out_tokens = encode_bytes(dst_tongue, data)

    # Generate attestation
    src_info = TONGUE_INFO[src_tongue]
    dst_info = TONGUE_INFO[dst_tongue]
    phase_delta = (dst_info["phase"] - src_info["phase"]) % 360
    weight_ratio = dst_info["weight"] / src_info["weight"]

    attestation = {
        "src_tongue": src_tongue,
        "dst_tongue": dst_tongue,
        "phase_delta": phase_delta,
        "weight_ratio": round(weight_ratio, 4),
        "timestamp": int(time.time()),
        "data_hash": hashlib.sha256(data).hexdigest()[:16]
    }

    return out_tokens, attestation


def blend_data(pattern: List[str], data: bytes) -> List[Tuple[str, str]]:
    """Stripe-blend data across multiple tongues."""
    result = []
    for i, byte in enumerate(data):
        tongue = pattern[i % len(pattern)]
        tokens, _ = LEXICONS[tongue]
        result.append((tongue, tokens[byte]))
    return result


# GeoSeal Implementation
# ----------------------

def project_to_sphere(ctx: List[float]) -> List[float]:
    """Project context to unit sphere."""
    take = (ctx[:3] if len(ctx) >= 3 else (ctx + [0, 0, 0])[:3])
    # Z-score normalization
    mu = sum(take) / len(take)
    var = sum((x - mu) ** 2 for x in take) / max(1, len(take) - 1)
    sd = math.sqrt(var) if var > 0 else 1.0
    z = [(x - mu) / sd for x in take]
    # Normalize to unit sphere
    norm = math.sqrt(sum(v * v for v in z)) or 1.0
    return [v / norm for v in z]


def project_to_cube(ctx: List[float], m: int = 6) -> List[float]:
    """Project context to unit hypercube."""
    arr = ctx[:m] if len(ctx) >= m else ctx + [0] * (m - len(ctx))
    return [min(1.0, max(0.0, (math.tanh(x / 5) + 1) / 2)) for x in arr]


def compute_potentials(u: List[float], v: List[float]) -> Tuple[float, float]:
    """Compute risk potential and margin."""
    R = sum(abs(x) for x in u) + 0.1 * sum(v)
    T = 0.5 + 0.05 * len([x for x in v if x < 0.2])
    P = 0.7 * R - 0.3 * T
    margin = 0.5 - abs(u[0]) if u else 0.5
    return P, margin


def classify_ring(r: float) -> Dict:
    """Classify position into trust ring."""
    rings = [
        (0.0, 0.3, "core", 5, 0),
        (0.3, 0.5, "inner", 20, 8),
        (0.5, 0.7, "middle", 100, 16),
        (0.7, 0.9, "outer", 500, 24),
        (0.9, 1.0, "edge", 5000, 32),
    ]
    for rmin, rmax, name, latency, pow_bits in rings:
        if rmin <= r < rmax:
            return {
                "ring": name,
                "latency_ms": latency,
                "pow_bits": pow_bits,
                "action": "ALLOW" if name in ["core", "inner"] else "REVIEW" if name == "middle" else "RESTRICT"
            }
    return {"ring": "beyond", "latency_ms": float("inf"), "pow_bits": 64, "action": "DENY"}


def evaluate_intent(intent: str, context: List[float]) -> Dict:
    """Evaluate intent through GeoSeal."""
    # Hash intent to position
    h = hashlib.sha256(intent.encode()).digest()
    intent_pos = [(b / 255.0) * 2 - 1 for b in h[:3]]  # Map to [-1, 1]

    # Project context
    u = project_to_sphere(context)
    v = project_to_cube(context)

    # Compute metrics
    P, margin = compute_potentials(u, v)

    # Compute radial distance (simplified)
    r = math.sqrt(sum(x * x for x in intent_pos))
    r = min(r, 0.99)  # Clamp to ball interior

    # Classify
    ring_info = classify_ring(r)

    # Harmonic wall cost
    d = r
    R = 1.5  # Harmonic base
    harmonic_cost = R ** (d * d) if d < 1 else float("inf")

    return {
        "intent": intent[:50] + "..." if len(intent) > 50 else intent,
        "position": [round(x, 4) for x in intent_pos],
        "radial_distance": round(r, 4),
        "ring": ring_info["ring"],
        "action": ring_info["action"],
        "latency_ms": ring_info["latency_ms"],
        "harmonic_cost": round(harmonic_cost, 4) if harmonic_cost < 1e6 else "∞",
        "potential": round(P, 4),
        "margin": round(margin, 4)
    }


# MCP Server Protocol
# -------------------

class MCPServer:
    """MCP Server implementing SCBE-AETHERMOORE tools."""

    def __init__(self):
        self.tools = {
            "tongue_encode": self.tool_tongue_encode,
            "tongue_decode": self.tool_tongue_decode,
            "tongue_xlate": self.tool_tongue_xlate,
            "tongue_blend": self.tool_tongue_blend,
            "tongue_info": self.tool_tongue_info,
            "geoseal_evaluate": self.tool_geoseal_evaluate,
        }

    async def tool_tongue_encode(self, params: Dict) -> Dict:
        """Encode data to Sacred Tongue spell-text."""
        tongue = params.get("tongue", "KO").upper()
        data_b64 = params.get("data_base64", "")
        data_text = params.get("data_text", "")
        include_prefix = params.get("include_prefix", True)

        if tongue not in TONGUES:
            return {"error": f"Invalid tongue. Must be one of: {TONGUES}"}

        if data_b64:
            data = base64.b64decode(data_b64)
        elif data_text:
            data = data_text.encode("utf-8")
        else:
            return {"error": "Provide either data_base64 or data_text"}

        tokens = encode_bytes(tongue, data)
        if include_prefix:
            tokens = [f"{tongue.lower()}:{t}" for t in tokens]

        return {
            "tongue": tongue,
            "tongue_name": TONGUE_INFO[tongue]["name"],
            "tokens": tokens,
            "spell_text": " ".join(tokens),
            "byte_count": len(data)
        }

    async def tool_tongue_decode(self, params: Dict) -> Dict:
        """Decode Sacred Tongue spell-text to data."""
        tongue = params.get("tongue", "KO").upper()
        spell_text = params.get("spell_text", "")

        if tongue not in TONGUES:
            return {"error": f"Invalid tongue. Must be one of: {TONGUES}"}

        tokens = spell_text.strip().split()
        try:
            data = decode_tokens(tongue, tokens)
            return {
                "tongue": tongue,
                "data_base64": base64.b64encode(data).decode(),
                "data_text": data.decode("utf-8", errors="replace"),
                "byte_count": len(data)
            }
        except Exception as e:
            return {"error": str(e)}

    async def tool_tongue_xlate(self, params: Dict) -> Dict:
        """Cross-translate spell-text between tongues."""
        src = params.get("src_tongue", "KO").upper()
        dst = params.get("dst_tongue", "CA").upper()
        spell_text = params.get("spell_text", "")

        if src not in TONGUES or dst not in TONGUES:
            return {"error": f"Invalid tongue. Must be one of: {TONGUES}"}

        tokens = spell_text.strip().split()
        try:
            out_tokens, attestation = xlate_tokens(src, dst, tokens)
            prefixed = [f"{dst.lower()}:{t}" for t in out_tokens]
            return {
                "src_tongue": src,
                "dst_tongue": dst,
                "translated_tokens": prefixed,
                "spell_text": " ".join(prefixed),
                "attestation": attestation
            }
        except Exception as e:
            return {"error": str(e)}

    async def tool_tongue_blend(self, params: Dict) -> Dict:
        """Stripe-blend data across multiple tongues."""
        pattern = params.get("pattern", ["KO", "AV", "RU"])
        data_b64 = params.get("data_base64", "")
        data_text = params.get("data_text", "")

        pattern = [t.upper() for t in pattern]
        for t in pattern:
            if t not in TONGUES:
                return {"error": f"Invalid tongue in pattern: {t}"}

        if data_b64:
            data = base64.b64decode(data_b64)
        elif data_text:
            data = data_text.encode("utf-8")
        else:
            return {"error": "Provide either data_base64 or data_text"}

        pairs = blend_data(pattern, data)
        tokens = [f"{tg.lower()}:{tok}" for tg, tok in pairs]

        return {
            "pattern": pattern,
            "blended_pairs": pairs,
            "spell_text": " ".join(tokens),
            "byte_count": len(data)
        }

    async def tool_tongue_info(self, params: Dict) -> Dict:
        """Get information about Sacred Tongues."""
        tongue = params.get("tongue")

        if tongue:
            tongue = tongue.upper()
            if tongue not in TONGUES:
                return {"error": f"Invalid tongue. Must be one of: {TONGUES}"}
            info = TONGUE_INFO[tongue]
            return {
                "tongue": tongue,
                "name": info["name"],
                "domain": info["domain"],
                "phase_degrees": info["phase"],
                "weight": info["weight"],
                "vocabulary_size": 256
            }
        else:
            return {
                "tongues": [
                    {
                        "code": tg,
                        "name": TONGUE_INFO[tg]["name"],
                        "domain": TONGUE_INFO[tg]["domain"],
                        "phase": TONGUE_INFO[tg]["phase"],
                        "weight": TONGUE_INFO[tg]["weight"]
                    }
                    for tg in TONGUES
                ]
            }

    async def tool_geoseal_evaluate(self, params: Dict) -> Dict:
        """Evaluate intent through GeoSeal geometric access control."""
        intent = params.get("intent", "")
        context = params.get("context", [0.0, 0.0, 0.0])

        if not intent:
            return {"error": "Intent string required"}

        if not isinstance(context, list):
            context = [0.0, 0.0, 0.0]

        return evaluate_intent(intent, context)

    async def handle_request(self, request: Dict) -> Dict:
        """Handle an MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "scbe-aethermoore",
                        "version": "3.1.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "tongue_encode",
                            "description": "Encode data to Sacred Tongue spell-text (bijective byte→token mapping)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tongue": {"type": "string", "enum": TONGUES, "description": "Sacred Tongue to use"},
                                    "data_text": {"type": "string", "description": "UTF-8 text to encode"},
                                    "data_base64": {"type": "string", "description": "Base64-encoded binary data"},
                                    "include_prefix": {"type": "boolean", "default": True}
                                }
                            }
                        },
                        {
                            "name": "tongue_decode",
                            "description": "Decode Sacred Tongue spell-text back to data",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tongue": {"type": "string", "enum": TONGUES},
                                    "spell_text": {"type": "string", "description": "Space-separated tokens"}
                                },
                                "required": ["spell_text"]
                            }
                        },
                        {
                            "name": "tongue_xlate",
                            "description": "Cross-translate spell-text between Sacred Tongues with attestation",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "src_tongue": {"type": "string", "enum": TONGUES},
                                    "dst_tongue": {"type": "string", "enum": TONGUES},
                                    "spell_text": {"type": "string"}
                                },
                                "required": ["spell_text"]
                            }
                        },
                        {
                            "name": "tongue_blend",
                            "description": "Stripe-blend data across multiple tongues for semantic segmentation",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pattern": {"type": "array", "items": {"type": "string", "enum": TONGUES}},
                                    "data_text": {"type": "string"},
                                    "data_base64": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "tongue_info",
                            "description": "Get information about Sacred Tongues (names, domains, phases, weights)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tongue": {"type": "string", "enum": TONGUES, "description": "Specific tongue, or omit for all"}
                                }
                            }
                        },
                        {
                            "name": "geoseal_evaluate",
                            "description": "Evaluate intent through GeoSeal geometric access control (trust rings, harmonic wall)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "intent": {"type": "string", "description": "The intent/query to evaluate"},
                                    "context": {"type": "array", "items": {"type": "number"}, "description": "Context vector (e.g., [lat, lon, time])"}
                                },
                                "required": ["intent"]
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

            try:
                result = await self.tools[tool_name](tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)}
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            }

    async def run(self):
        """Run the MCP server on stdio."""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break

                request = json.loads(line)
                response = await self.handle_request(request)

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()


async def main():
    """Main entry point."""
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
