#!/usr/bin/env python3
"""Build full GeoSeal coding-system SFT records.

This lane teaches the coding agent to keep the core SCBE coding surfaces
separate but aligned: code primary, music theory, atomic tokenizer, binary
transport, lane contract, and workflow composition.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tokenizer.chemistry_command_stack import build_chemistry_command_stack  # noqa: E402
from src.tokenizer.code_weight_packets import build_code_weight_packet  # noqa: E402


SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "coding_system_full_v1_train.sft.jsonl"
HOLDOUT_OUT = SFT_ROOT / "coding_system_full_v1_holdout.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "coding_system_full_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE GeoSeal coding agent. Treat coding as the primary build target. "
    "Keep code-primary semantics, music-theory harmony, atomic tokenizer rows, binary/hex transport, "
    "and workflow-composition evidence in separate lanes, then align them for deterministic code work. "
    "Structural chemistry is a composition template; material chemistry is only claimed for real chemistry input."
)


PRIMARY_MAP: dict[str, dict[str, Any]] = {
    "KO": {
        "full_name": "Kor'aelin",
        "language": "python",
        "domain": "intent_command",
        "phase_degrees": 0,
        "mode": "Ionian",
        "interval_pattern": "W-W-H-W-W-W-H",
        "anchor_pitch": "C",
        "mirror_pair": "DR",
        "foundation_role": "intent and executable command lane",
    },
    "AV": {
        "full_name": "Avali",
        "language": "typescript",
        "domain": "wisdom_knowledge",
        "phase_degrees": 60,
        "mode": "Lydian",
        "interval_pattern": "W-W-W-H-W-W-H",
        "anchor_pitch": "F",
        "mirror_pair": "CA",
        "foundation_role": "typed interface and browser/tool lane",
    },
    "RU": {
        "full_name": "Runethic",
        "language": "rust",
        "domain": "governance_entropy",
        "phase_degrees": 120,
        "mode": "Dorian",
        "interval_pattern": "W-H-W-W-W-H-W",
        "anchor_pitch": "D",
        "mirror_pair": "UM",
        "foundation_role": "ownership, guardrail, and deterministic systems lane",
    },
    "CA": {
        "full_name": "Cassisivadan",
        "language": "c",
        "domain": "compute_logic",
        "phase_degrees": 180,
        "mode": "Mixolydian",
        "interval_pattern": "W-W-H-W-W-H-W",
        "anchor_pitch": "G",
        "mirror_pair": "AV",
        "foundation_role": "low-level compute, memory, and ABI lane",
    },
    "UM": {
        "full_name": "Umbroth",
        "language": "julia",
        "domain": "security_defense",
        "phase_degrees": 240,
        "mode": "Aeolian",
        "interval_pattern": "W-H-W-W-H-W-W",
        "anchor_pitch": "A",
        "mirror_pair": "RU",
        "foundation_role": "numerical defense, analysis, and optimization lane",
    },
    "DR": {
        "full_name": "Draumric",
        "language": "haskell",
        "domain": "structure_architecture",
        "phase_degrees": 300,
        "mode": "Phrygian",
        "interval_pattern": "H-W-W-W-H-W-W",
        "anchor_pitch": "E",
        "mirror_pair": "KO",
        "foundation_role": "type-shape, architecture, and proof lane",
    },
}


@dataclass(frozen=True)
class Concept:
    concept_id: str
    intent: str
    phase_operation: str
    command_key: str
    resource_axes: tuple[str, ...]
    samples: dict[str, str]


CONCEPTS: tuple[Concept, ...] = (
    Concept(
        "add",
        "combine two numeric slots and return the result",
        "fuse",
        "add",
        ("compute", "time"),
        {
            "KO": "def add(a, b):\n    return a + b\n",
            "AV": "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
            "RU": "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
            "CA": "int add(int a, int b) {\n    return a + b;\n}\n",
            "UM": "function add(a, b)\n    return a + b\nend\n",
            "DR": "add :: Int -> Int -> Int\nadd a b = a + b\n",
        },
    ),
    Concept(
        "guard_divide",
        "block divide-by-zero before runtime launch",
        "gate",
        "guard_divide",
        ("risk", "compute"),
        {
            "KO": "def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n",
            "AV": "export function safeDivide(a: number, b: number): number | null {\n  if (b === 0) return null;\n  return a / b;\n}\n",
            "RU": "fn safe_divide(a: f64, b: f64) -> Option<f64> {\n    if b == 0.0 { None } else { Some(a / b) }\n}\n",
            "CA": "double safe_divide(double a, double b, int *ok) {\n    if (b == 0.0) { *ok = 0; return 0.0; }\n    *ok = 1; return a / b;\n}\n",
            "UM": "function safe_divide(a, b)\n    b == 0 && return nothing\n    return a / b\nend\n",
            "DR": "safeDivide :: Double -> Double -> Maybe Double\nsafeDivide _ 0 = Nothing\nsafeDivide a b = Just (a / b)\n",
        },
    ),
    Concept(
        "map_square",
        "apply one deterministic transform over a sequence",
        "replicate",
        "map_square",
        ("compute", "memory"),
        {
            "KO": "def map_square(xs):\n    return [x * x for x in xs]\n",
            "AV": "export const mapSquare = (xs: number[]) => xs.map((x) => x * x);\n",
            "RU": "fn map_square(xs: &[i32]) -> Vec<i32> {\n    xs.iter().map(|x| x * x).collect()\n}\n",
            "CA": "void map_square(const int *xs, int *out, int n) {\n    for (int i = 0; i < n; i++) out[i] = xs[i] * xs[i];\n}\n",
            "UM": "map_square(xs) = map(x -> x * x, xs)\n",
            "DR": "mapSquare :: [Int] -> [Int]\nmapSquare xs = map (\\x -> x * x) xs\n",
        },
    ),
    Concept(
        "retry_packet",
        "retry a packet route only inside a bounded attempt window",
        "propagate",
        "retry_packet",
        ("comms", "time"),
        {
            "KO": "def retry_packet(send, payload, limit):\n    for attempt in range(limit):\n        if send(payload):\n            return True\n    return False\n",
            "AV": "export function retryPacket(send: (p: string) => boolean, payload: string, limit: number): boolean {\n  for (let attempt = 0; attempt < limit; attempt++) if (send(payload)) return true;\n  return false;\n}\n",
            "RU": "fn retry_packet<F: Fn(&str) -> bool>(send: F, payload: &str, limit: usize) -> bool {\n    (0..limit).any(|_| send(payload))\n}\n",
            "CA": "int retry_packet(int (*send)(const char *), const char *payload, int limit) {\n    for (int attempt = 0; attempt < limit; attempt++) if (send(payload)) return 1;\n    return 0;\n}\n",
            "UM": "function retry_packet(send, payload, limit)\n    any(_ -> send(payload), 1:limit)\nend\n",
            "DR": "retryPacket :: (String -> Bool) -> String -> Int -> Bool\nretryPacket send payload limit = any (\\_ -> send payload) [1..limit]\n",
        },
    ),
    Concept(
        "budget_fallback",
        "hold an action when projected cost exceeds available resources",
        "stabilize",
        "budget_fallback",
        ("power", "compute", "time", "comms", "wear"),
        {
            "KO": "def route_or_hold(cost, budget):\n    if cost > budget:\n        return \"hold\"\n    return \"launch\"\n",
            "AV": "export function routeOrHold(cost: number, budget: number): \"hold\" | \"launch\" {\n  return cost > budget ? \"hold\" : \"launch\";\n}\n",
            "RU": "fn route_or_hold(cost: f32, budget: f32) -> &'static str {\n    if cost > budget { \"hold\" } else { \"launch\" }\n}\n",
            "CA": "const char *route_or_hold(float cost, float budget) {\n    return cost > budget ? \"hold\" : \"launch\";\n}\n",
            "UM": "route_or_hold(cost, budget) = cost > budget ? \"hold\" : \"launch\"\n",
            "DR": "routeOrHold :: Float -> Float -> String\nrouteOrHold cost budget = if cost > budget then \"hold\" else \"launch\"\n",
        },
    ),
    Concept(
        "hash_route",
        "derive a deterministic route slot from source bytes",
        "measure",
        "hash_route",
        ("audit", "compute"),
        {
            "KO": "import hashlib\n\ndef hash_route(text):\n    return hashlib.sha256(text.encode()).hexdigest()\n",
            "AV": "export async function hashRoute(text: string): Promise<string> {\n  const data = new TextEncoder().encode(text);\n  const digest = await crypto.subtle.digest(\"SHA-256\", data);\n  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, \"0\")).join(\"\");\n}\n",
            "RU": "fn hash_route(bytes: &[u8]) -> u64 {\n    bytes.iter().fold(0u64, |acc, b| acc.wrapping_mul(131).wrapping_add(*b as u64))\n}\n",
            "CA": "unsigned long hash_route(const unsigned char *bytes, int n) {\n    unsigned long acc = 0;\n    for (int i = 0; i < n; i++) acc = acc * 131u + bytes[i];\n    return acc;\n}\n",
            "UM": "hash_route(bytes) = foldl((acc, b) -> acc * UInt(131) + UInt(b), bytes; init=UInt(0))\n",
            "DR": "hashRoute :: [Int] -> Int\nhashRoute bytes = foldl (\\acc b -> acc * 131 + b) 0 bytes\n",
        },
    ),
    Concept(
        "parse_flag",
        "extract a command-line flag without changing payload semantics",
        "cleave",
        "parse_flag",
        ("interface", "risk"),
        {
            "KO": "def parse_flag(args, flag):\n    return flag in args\n",
            "AV": "export function parseFlag(args: string[], flag: string): boolean {\n  return args.includes(flag);\n}\n",
            "RU": "fn parse_flag(args: &[String], flag: &str) -> bool {\n    args.iter().any(|arg| arg == flag)\n}\n",
            "CA": "int parse_flag(int argc, char **argv, const char *flag) {\n    for (int i = 0; i < argc; i++) if (strcmp(argv[i], flag) == 0) return 1;\n    return 0;\n}\n",
            "UM": "parse_flag(args, flag) = flag in args\n",
            "DR": "parseFlag :: [String] -> String -> Bool\nparseFlag args flag = flag `elem` args\n",
        },
    ),
    Concept(
        "test_assert",
        "prove expected behavior with a small deterministic assertion",
        "bind",
        "test_assert",
        ("proof", "compute"),
        {
            "KO": "def test_add():\n    assert add(2, 3) == 5\n",
            "AV": "export function testAdd(): void {\n  if (add(2, 3) !== 5) throw new Error(\"add failed\");\n}\n",
            "RU": "#[test]\nfn test_add() {\n    assert_eq!(add(2, 3), 5);\n}\n",
            "CA": "void test_add(void) {\n    assert(add(2, 3) == 5);\n}\n",
            "UM": "function test_add()\n    @assert add(2, 3) == 5\nend\n",
            "DR": "testAdd :: Bool\ntestAdd = add 2 3 == 5\n",
        },
    ),
)


PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _pitch_for(concept_index: int, primary: str) -> dict[str, Any]:
    primary_index = list(PRIMARY_MAP).index(primary)
    pitch_class = (concept_index * 3 + primary_index * 2) % len(PITCHES)
    anchor_pitch = PRIMARY_MAP[primary]["anchor_pitch"]
    anchor_index = PITCHES.index(anchor_pitch)
    interval = (pitch_class - anchor_index) % len(PITCHES)
    return {
        "anchor_pitch": anchor_pitch,
        "pitch_class": pitch_class,
        "pitch_name": PITCHES[pitch_class],
        "interval_from_anchor": interval,
        "harmony_role": "convergent" if interval in {0, 5, 7} else "tension_to_resolve",
    }


def _token_hex(token: str) -> str:
    return ".".join(f"{byte:02X}" for byte in token.encode("utf-8"))


def _packet_summary(packet: dict[str, Any]) -> dict[str, Any]:
    token_rows = ((packet.get("stisa") or {}).get("token_rows") or [])[:8]
    atomic_states = (packet.get("atomic_states") or [])[:8]
    return {
        "lexical_tokens": (packet.get("lexical_tokens") or [])[:12],
        "atomic_rows": [
            {
                "token": row.get("token"),
                "semantic_class": row.get("semantic_class"),
                "feature_vector": row.get("feature_vector"),
                "element": (atomic_states[idx].get("element") if idx < len(atomic_states) else {}),
            }
            for idx, row in enumerate(token_rows)
        ],
        "stisa_field_names": [
            item.get("name") for item in ((packet.get("stisa") or {}).get("field_definitions") or [])[:8]
        ],
    }


def _binary_summary(packet: dict[str, Any], source: str) -> dict[str, Any]:
    source_bytes = source.encode("utf-8")
    return {
        "byte_count": len(source_bytes),
        "first_16_hex": [f"{byte:02X}" for byte in source_bytes[:16]],
        "first_16_bits": (packet.get("binary") or {}).get("bits", [])[:16],
        "transport_tongue": (packet.get("transport") or {}).get("tongue"),
        "transport_tokens": (packet.get("transport") or {}).get("tokens", [])[:16],
        "source_sha256": (packet.get("transport") or {}).get("source_sha256"),
        "token_sha256": (packet.get("transport") or {}).get("token_sha256"),
    }


def _topology(concept: Concept, primary: str) -> dict[str, Any]:
    return {
        "operative_command": {
            "command_key": concept.command_key,
            "phase_operation": concept.phase_operation,
            "binary_input": _token_hex(concept.command_key),
            "key_slot": primary,
        }
    }


def _build_single_record(concept: Concept, concept_index: int, primary: str) -> dict[str, Any]:
    primary_cfg = PRIMARY_MAP[primary]
    source = concept.samples[primary]
    packet = build_code_weight_packet(
        source,
        language=primary_cfg["language"],
        source_name=f"{concept.concept_id}.{primary_cfg['language']}",
    )
    stack = build_chemistry_command_stack(packet, _topology(concept, primary))
    music = {
        "mode": primary_cfg["mode"],
        "interval_pattern": primary_cfg["interval_pattern"],
        **_pitch_for(concept_index, primary),
        "pseudo_harmony": (
            "stable_primary" if primary in {"KO", "AV", "RU"} else "mirror_resolution"
        ),
    }
    assistant_payload = {
        "schema_version": "scbe_full_coding_system_answer_v1",
        "concept": {
            "concept_id": concept.concept_id,
            "intent": concept.intent,
            "command_key": concept.command_key,
            "phase_operation": concept.phase_operation,
        },
        "coding_primary": {
            "tongue": primary,
            **primary_cfg,
            "sample_code": source,
        },
        "music_theory": music,
        "atomic_tokenizer": _packet_summary(packet),
        "binary_transport": _binary_summary(packet, source),
        "code_lane_contract": packet.get("lane_alignment"),
        "workflow_composition": {
            "resource_axes": list(concept.resource_axes),
            "quarks": (packet.get("semantic_expression") or {}).get("quarks", []),
            "semantic_compound_commands": stack.get("semantic_compound_commands", [])[:6],
            "validation": stack.get("validation"),
            "fallback_rule": (
                "If projected cost exceeds budget, hold in steady-state, damp launch momentum, "
                "preserve token-to-binary evidence, then re-advance from a cheaper route."
            ),
        },
        "boundary": {
            "semantic_vs_transport": "Semantic meaning, metric payload, and SS1/SS2 transport packet stay distinct.",
            "chemistry_scope": (
                "The chemistry lane is a structural composition template for workflow units. "
                "Material chemistry is only asserted for real chemical input."
            ),
        },
    }
    prompt = (
        f"Map `{concept.concept_id}` in {primary}/{primary_cfg['language']} through the full GeoSeal coding system. "
        "Keep code primary, music theory, atomic tokenizer, binary transport, lane contract, and workflow composition separate."
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": _json_dumps(assistant_payload)},
        ],
        "meta": {
            "stage": "full_coding_system_v1",
            "kind": "single_primary_lane",
            "concept_id": concept.concept_id,
            "primary": primary,
            "language": primary_cfg["language"],
            "source": "coding_system_master_reference_plus_live_code_weight_packet",
        },
    }


def _build_roundabout_record(concept: Concept, concept_index: int) -> dict[str, Any]:
    lanes: list[dict[str, Any]] = []
    for primary, primary_cfg in PRIMARY_MAP.items():
        source = concept.samples[primary]
        packet = build_code_weight_packet(
            source,
            language=primary_cfg["language"],
            source_name=f"{concept.concept_id}.{primary_cfg['language']}",
        )
        lanes.append(
            {
                "tongue": primary,
                "language": primary_cfg["language"],
                "mode": primary_cfg["mode"],
                "phase_degrees": primary_cfg["phase_degrees"],
                "pitch": _pitch_for(concept_index, primary),
                "tokens": (packet.get("lexical_tokens") or [])[:10],
                "first_8_hex": [f"{byte:02X}" for byte in source.encode("utf-8")[:8]],
                "route_tongue": (packet.get("route") or {}).get("tongue"),
                "source_sha256": packet.get("source_sha256"),
                "lane_alignment": packet.get("lane_alignment"),
            }
        )
    assistant_payload = {
        "schema_version": "scbe_full_coding_system_roundabout_v1",
        "concept_id": concept.concept_id,
        "intent": concept.intent,
        "roundabout_rule": (
            "The concept is fixed at the center. Each vehicle is a code primary. "
            "The road is the shared byte/binary transport plus aligned operation contract."
        ),
        "lanes": lanes,
        "mirror_pairs": {"KO": "DR", "AV": "CA", "RU": "UM"},
        "foundation_triangle": ["KO/Python", "AV/TypeScript", "RU/Rust"],
        "music_theory_use": (
            "Modes and intervals mark convergence, tension, and mirror resolution. "
            "They do not replace runtime tests; they provide routeable structure for command recall."
        ),
        "training_rule": (
            "Train the coding agent to preserve slots and action intent across primaries, "
            "then use binary/hex/token evidence as the audit trail."
        ),
    }
    prompt = (
        f"Show how `{concept.concept_id}` stays fixed while all six code primaries move through the same "
        "GeoSeal roundabout. Include music theory and binary/token audit evidence."
    )
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": _json_dumps(assistant_payload)},
        ],
        "meta": {
            "stage": "full_coding_system_v1",
            "kind": "cross_primary_roundabout",
            "concept_id": concept.concept_id,
            "source": "coding_system_master_reference_plus_live_code_weight_packet",
        },
    }


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for concept_index, concept in enumerate(CONCEPTS):
        for primary in PRIMARY_MAP:
            rows.append(_build_single_record(concept, concept_index, primary))
        rows.append(_build_roundabout_record(concept, concept_index))

    train_rows = [row for idx, row in enumerate(rows) if idx % 7 != 0]
    holdout_rows = [row for idx, row in enumerate(rows) if idx % 7 == 0]

    for path, payload in ((TRAIN_OUT, train_rows), (HOLDOUT_OUT, holdout_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in payload:
                handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "coding_system_full_v1_manifest",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outputs": {"train": str(TRAIN_OUT), "holdout": str(HOLDOUT_OUT)},
        "counts": {"train": len(train_rows), "holdout": len(holdout_rows), "total": len(rows)},
        "concepts": [concept.concept_id for concept in CONCEPTS],
        "primaries": {
            key: {
                "full_name": value["full_name"],
                "language": value["language"],
                "mode": value["mode"],
                "domain": value["domain"],
            }
            for key, value in PRIMARY_MAP.items()
        },
        "boundary": (
            "Coding is the primary training target. Music theory, atomic tokenization, binary transport, "
            "and structural chemistry workflow evidence are separate aligned lanes."
        ),
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, ensure_ascii=True))
