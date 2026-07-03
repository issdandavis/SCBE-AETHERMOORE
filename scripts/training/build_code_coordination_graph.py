#!/usr/bin/env python
"""Build a binary + harmonic coordination graph for all SCBE code languages.

This is the "coordination graph" layer on top of the language systems atlas:

  language examples -> canonical code payload
                    -> binary signatures
                    -> harmonic coordinates
                    -> graph nodes/edges

Honest scope:
  * The graph is deterministic and executable.
  * "Harmonic" here means a reproducible phase/frequency coordinate derived
    from code bytes and the six SCBE tongue phases. It is a coordination
    geometry, not a physical acoustics proof.
  * Edges are similarity/routing edges, not proof that languages are equivalent.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_language_systems_atlas import BINARY_MODES, LANGUAGES as ATLAS_LANGUAGES, binary_views, code_example as atlas_code_example


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "language_systems_atlas"
GRAPH_PATH = OUT_DIR / "code_coordination_graph.json"
ROWS_PATH = OUT_DIR / "code_coordination_graph_training_rows.jsonl"
RECEIPT_PATH = OUT_DIR / "code_coordination_graph_receipt.json"

PHI = (1 + 5**0.5) / 2
TONGUE_PHASES = [
    ("KO", 0),
    ("AV", 60),
    ("RU", 120),
    ("CA", 180),
    ("UM", 240),
    ("DR", 300),
]
CONSTRUCTS = ("hello", "function", "branch_loop")

EXTRA_LANGUAGES: list[dict[str, Any]] = [
    {
        "id": "brainfuck",
        "aliases": ["mindfuck", "bf"],
        "name": "Brainfuck",
        "family": "esolang",
        "docs": "https://esolangs.org/wiki/Brainfuck",
        "tutorial": "https://esolangs.org/wiki/Brainfuck#Commands",
        "troubleshooting": "https://esolangs.org/wiki/Brainfuck_algorithms",
    }
]

LANGUAGES: list[dict[str, Any]] = [*ATLAS_LANGUAGES, *EXTRA_LANGUAGES]


def code_example(lang: dict[str, Any], construct: str) -> str:
    if lang["id"] == "brainfuck":
        if construct == "hello":
            return "+++++."
        if construct == "function":
            return "++>+++[<+>-]<."
        if construct == "branch_loop":
            return "+++[>++<-]>."
    return atlas_code_example(lang, construct)


def sha_bytes(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).digest()


def bitstring(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in data)


def bit_hamming(a: bytes, b: bytes) -> int:
    return sum((x ^ y).bit_count() for x, y in zip(a, b))


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((count / n) * math.log2(count / n) for count in counts.values())


def byte_hist_vector(data: bytes) -> list[float]:
    counts = Counter(data)
    total = max(1, len(data))
    return [counts.get(i, 0) / total for i in range(256)]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def nearest_tongue(phase_deg: float) -> tuple[str, int, float]:
    best = None
    for name, phase in TONGUE_PHASES:
        diff = abs(((phase_deg - phase + 180) % 360) - 180)
        if best is None or diff < best[2]:
            best = (name, phase, diff)
    assert best is not None
    return best


def harmonic_coordinate(payload: str, family_index: int) -> dict[str, Any]:
    digest = sha_bytes(payload)
    phase_raw = int.from_bytes(digest[:2], "big") / 65535
    phase_deg = phase_raw * 360
    tongue, tongue_phase, phase_error = nearest_tongue(phase_deg)
    entropy = byte_entropy(payload.encode("utf-8", errors="replace"))
    radius = min(0.95, 0.18 + entropy / 10)
    octave = 2 + (digest[2] % 5)
    family_lift = 1 + (family_index % 12) / 24
    frequency_hz = 55.0 * (2**octave) * (PHI ** ((phase_deg / 60) % 6 / 6)) * family_lift
    radians = math.radians(phase_deg)
    return {
        "phase_deg": round(phase_deg, 6),
        "nearest_tongue": tongue,
        "tongue_phase_deg": tongue_phase,
        "phase_error_deg": round(phase_error, 6),
        "radius": round(radius, 6),
        "frequency_hz": round(frequency_hz, 6),
        "coordinate": [
            round(radius * math.cos(radians), 6),
            round(radius * math.sin(radians), 6),
            round((entropy / 8) * 2 - 1, 6),
        ],
    }


def compact_binary_signature(payload: str) -> dict[str, Any]:
    data = payload.encode("utf-8", errors="replace")
    digest = hashlib.sha256(data).hexdigest()
    views = binary_views(payload)
    return {
        "sha256": digest,
        "byte_len": len(data),
        "entropy_bits_per_byte": round(byte_entropy(data), 6),
        "utf8_preview": views["utf8"],
        "hex_prefix": views["hex"][:96],
        "bits_prefix": views["bits"][:128],
        "base64_prefix": views["base64"][:96],
        "ascii85_prefix": views["ascii85"][:96],
        "byte_hist_nonzero": len(views["byte_hist"]),
    }


def mode_payload(mode: str, payload: str, signature: dict[str, Any]) -> str:
    data = payload.encode("utf-8", errors="replace")
    if mode == "utf8":
        return payload
    if mode == "utf16le":
        return data.decode("utf-8", errors="replace").encode("utf-16le").hex()
    if mode == "utf32le":
        return data.decode("utf-8", errors="replace").encode("utf-32le").hex()
    if mode == "bytes":
        return ",".join(str(byte) for byte in data)
    if mode == "hex":
        return data.hex()
    if mode == "bits":
        return bitstring(data)
    if mode == "nibbles":
        return " ".join(f"{byte >> 4:x}{byte & 15:x}" for byte in data)
    if mode == "base64":
        return base64.b64encode(data).decode("ascii")
    if mode == "base64url":
        return base64.urlsafe_b64encode(data).decode("ascii")
    if mode == "ascii85":
        return base64.a85encode(data).decode("ascii", errors="replace")
    if mode == "byte_hist":
        return json.dumps(signature, sort_keys=True)
    if mode == "sha256":
        return signature["sha256"]
    return payload


def build_graph() -> dict[str, Any]:
    families = {family: i for i, family in enumerate(sorted({lang["family"] for lang in LANGUAGES}))}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    language_payloads: dict[str, str] = {}
    language_digests: dict[str, bytes] = {}
    language_hist: dict[str, list[float]] = {}

    for mode in BINARY_MODES:
        nodes.append({"id": f"binary:{mode}", "kind": "binary_mode", "label": mode})

    for family, idx in families.items():
        phase = (idx * 360 / max(1, len(families))) % 360
        nodes.append(
            {
                "id": f"family:{family}",
                "kind": "language_family",
                "label": family,
                "harmonic": {
                    "phase_deg": round(phase, 6),
                    "frequency_hz": round(110 * (PHI ** (idx / max(1, len(families)))), 6),
                },
            }
        )

    for lang in LANGUAGES:
        payload = "\n\n".join(f"## {construct}\n{code_example(lang, construct)}" for construct in CONSTRUCTS)
        language_payloads[lang["id"]] = payload
        data = payload.encode("utf-8", errors="replace")
        digest = sha_bytes(payload)
        language_digests[lang["id"]] = digest
        language_hist[lang["id"]] = byte_hist_vector(data)
        signature = compact_binary_signature(payload)
        harmonic = harmonic_coordinate(payload, families[lang["family"]])
        node_id = f"language:{lang['id']}"

        nodes.append(
            {
                "id": node_id,
                "kind": "language",
                "label": lang["name"],
                "language": lang,
                "constructs": list(CONSTRUCTS),
                "binary_signature": signature,
                "harmonic": harmonic,
            }
        )
        edges.append(
            {
                "source": node_id,
                "target": f"family:{lang['family']}",
                "kind": "belongs_to_family",
                "weight": 1.0,
            }
        )
        for construct in CONSTRUCTS:
            code = code_example(lang, construct)
            code_signature = compact_binary_signature(code)
            code_harmonic = harmonic_coordinate(code, families[lang["family"]])
            code_node_id = f"code:{lang['id']}:{construct}"
            nodes.append(
                {
                    "id": code_node_id,
                    "kind": "code_payload",
                    "label": f"{lang['name']} {construct}",
                    "language_id": lang["id"],
                    "construct": construct,
                    "code": code,
                    "binary_signature": code_signature,
                    "binary_views": binary_views(code),
                    "harmonic": code_harmonic,
                    "aliases": lang.get("aliases", []),
                }
            )
            edges.append(
                {
                    "source": node_id,
                    "target": code_node_id,
                    "kind": "has_code_payload",
                    "weight": 1.0,
                }
            )
            for mode in BINARY_MODES:
                encoded = mode_payload(mode, code, code_signature)
                mode_digest = hashlib.sha256(encoded.encode("utf-8", errors="replace")).hexdigest()
                edges.append(
                    {
                        "source": code_node_id,
                        "target": f"binary:{mode}",
                        "kind": "code_payload_has_binary_view",
                        "weight": 1.0,
                        "digest": mode_digest,
                        "encoded_len": len(encoded.encode("utf-8", errors="replace")),
                    }
                )
            rows.append(
                {
                    "id": f"coordination-code:{lang['id']}:{construct}:{code_signature['sha256'][:12]}",
                    "lane": "coordination_graph",
                    "task": "code_payload_to_binary_harmonic_views",
                    "prompt": f"Map the {construct} construct in {lang['name']} into binary multi-view and harmonic coordination form.",
                    "response": json.dumps(
                        {
                            "code_node": code_node_id,
                            "language": lang["id"],
                            "construct": construct,
                            "sha256": code_signature["sha256"],
                            "nearest_tongue": code_harmonic["nearest_tongue"],
                            "coordinate": code_harmonic["coordinate"],
                            "hex_prefix": code_signature["hex_prefix"],
                            "bits_prefix": code_signature["bits_prefix"],
                        },
                        sort_keys=True,
                    ),
                    "views": {
                        "language": lang,
                        "construct": construct,
                        "code": code,
                        "binary_signature": code_signature,
                        "binary_views": binary_views(code),
                        "harmonic": code_harmonic,
                        "binary_modes": list(BINARY_MODES),
                    },
                    "metadata": {"validated": True, "graph_artifact": str(GRAPH_PATH)},
                }
            )
        for mode in BINARY_MODES:
            encoded = mode_payload(mode, payload, signature)
            mode_digest = hashlib.sha256(encoded.encode("utf-8", errors="replace")).hexdigest()
            edges.append(
                {
                    "source": node_id,
                    "target": f"binary:{mode}",
                    "kind": "has_binary_view",
                    "weight": 1.0,
                    "digest": mode_digest,
                    "encoded_len": len(encoded.encode("utf-8", errors="replace")),
                }
            )

        rows.append(
            {
                "id": f"coordination:{lang['id']}:{signature['sha256'][:12]}",
                "lane": "coordination_graph",
                "task": "language_to_binary_harmonic_node",
                "prompt": f"Map {lang['name']} into binary signatures and harmonic coordination coordinates.",
                "response": json.dumps(
                    {
                        "node": node_id,
                        "sha256": signature["sha256"],
                        "nearest_tongue": harmonic["nearest_tongue"],
                        "coordinate": harmonic["coordinate"],
                    },
                    sort_keys=True,
                ),
                "views": {
                    "language": lang,
                    "binary_signature": signature,
                    "harmonic": harmonic,
                    "binary_modes": list(BINARY_MODES),
                },
                "metadata": {"validated": True, "graph_artifact": str(GRAPH_PATH)},
            }
        )

    # Similarity/routing edges: connect each language to its strongest byte-neighborhood peers.
    top_k = 4
    for lang in LANGUAGES:
        scored = []
        for other in LANGUAGES:
            if other["id"] == lang["id"]:
                continue
            hamming = bit_hamming(language_digests[lang["id"]], language_digests[other["id"]])
            hist_sim = cosine(language_hist[lang["id"]], language_hist[other["id"]])
            same_family = 1.0 if lang["family"] == other["family"] else 0.0
            score = (1 - hamming / 256) * 0.45 + hist_sim * 0.40 + same_family * 0.15
            scored.append((score, hamming, hist_sim, other))
        for score, hamming, hist_sim, other in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]:
            edges.append(
                {
                    "source": f"language:{lang['id']}",
                    "target": f"language:{other['id']}",
                    "kind": "binary_harmonic_neighbor",
                    "weight": round(score, 6),
                    "sha256_hamming_bits": hamming,
                    "byte_hist_cosine": round(hist_sim, 6),
                    "same_family": lang["family"] == other["family"],
                }
            )

    degree = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    graph = {
        "kind": "code_language_binary_harmonic_coordination_graph",
        "honest_scope": "Deterministic coordination graph from code bytes, binary encodings, language families, and SCBE six-phase harmonic coordinates.",
        "counts": {
            "languages": len(LANGUAGES),
            "families": len(families),
            "binary_modes": len(BINARY_MODES),
            "nodes": len(nodes),
            "edges": len(edges),
            "training_rows": len(rows),
        },
        "binary_modes": list(BINARY_MODES),
        "tongue_phases": [{"tongue": name, "phase_deg": phase} for name, phase in TONGUE_PHASES],
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "max_degree": max(degree.values()) if degree else 0,
            "min_degree": min(degree.values()) if degree else 0,
            "avg_degree": round(sum(degree.values()) / max(1, len(degree)), 6),
        },
    }
    return graph, rows


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph, rows = build_graph()
    GRAPH_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    with ROWS_PATH.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    receipt = {
        "ok": True,
        "kind": "code_language_binary_harmonic_coordination_graph",
        "counts": graph["counts"],
        "metrics": graph["metrics"],
        "artifacts": {
            "graph": str(GRAPH_PATH),
            "training_rows": str(ROWS_PATH),
        },
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("CODE_COORDINATION_GRAPH_DONE")
    print(f"languages: {graph['counts']['languages']} binary_modes: {graph['counts']['binary_modes']} nodes: {graph['counts']['nodes']} edges: {graph['counts']['edges']}")
    print(f"training_rows: {graph['counts']['training_rows']} avg_degree: {graph['metrics']['avg_degree']}")
    print(f"receipt: {RECEIPT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
