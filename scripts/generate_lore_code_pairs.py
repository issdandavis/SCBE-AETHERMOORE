#!/usr/bin/env python3
"""
Lore-to-Code Pair Generator — The Multiplication Engine
========================================================

Takes lore records (narrative, world-building, Sacred Tongue text) and
extracts the computational structure hiding inside each one, producing
PAIRED training records where:

    LORE × CODE = both

A spell description IS a function definition.
A governance edict IS a policy check.
A Sacred Tongue incantation IS executable bytecode.
An enchantment IS an encryption envelope.
A binding oath IS a digital signature.

Uses the quantum frequency bundle as the mapping function:
    - QHO physics tags energy/excitation per tongue
    - Polychromatic vector gives the visual frequency fingerprint
    - Acoustic signature gives the sound profile
    - Harmonic wall gives governance cost

Input:  ~41K lore JSONL records (everweave, claude_export, published_book)
Output: training-data/sft/lore_code_pairs_sft.jsonl

Author: SCBE-AETHERMOORE / Issac Davis
Date:   2026-04-07
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from crypto.sacred_tongues import TONGUES, SacredTongueTokenizer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = 1.618033988749895
TONGUE_ORDER = ["ko", "av", "ru", "ca", "um", "dr"]
TONGUE_FULL_NAMES = {
    "ko": "Kor'aelin",
    "av": "Avali",
    "ru": "Runethic",
    "ca": "Cassisivadan",
    "um": "Umbroth",
    "dr": "Draumric",
}
TONGUE_WEIGHTS = {t: PHI ** i for i, t in enumerate(TONGUE_ORDER)}
TONGUE_FREQUENCIES = {
    "ko": 440.0, "av": 523.25, "ru": 293.66,
    "ca": 659.25, "um": 196.0, "dr": 392.0,
}
TONGUE_PARADIGMS = {
    "ko": ("Lisp", "VSO", "prefix-evaluated S-expressions"),
    "av": ("Python", "SVO", "subject.method(object) chaining"),
    "ru": ("Forth", "SOV", "stack-based postfix evaluation"),
    "ca": ("SQL", "V2", "declarative predicate queries"),
    "um": ("Assembly", "OSV", "register-mapped state machine"),
    "dr": ("Make", "SOV", "dependency-resolution build graph"),
}
TONGUE_GEOMETRIES = {
    "ko": "hexagonal (6-fold hub-spoke)",
    "av": "spiral (phi-expansion)",
    "ru": "fractal (self-similar branching)",
    "ca": "cubic (3D indexed grid)",
    "um": "icosahedral (20-face defense)",
    "dr": "dodecahedral (12-face design)",
}
TONGUE_DOMAINS = {
    "ko": "command, intent, flow control, nonces",
    "av": "diplomacy, transport, headers, metadata",
    "ru": "governance, binding, salts, legal proofs",
    "ca": "compute, analysis, ciphertext, math ops",
    "um": "shadow, security, redaction, veiling",
    "dr": "structure, forge, design, construction",
}

# ---------------------------------------------------------------------------
# Lore-to-Code Pattern Matchers
# ---------------------------------------------------------------------------
# Each pattern maps a narrative concept to its computational equivalent.
# The key is a regex pattern; the value is (code_concept, tongue, description).

LORE_CODE_PATTERNS: List[Tuple[str, str, str, str]] = [
    # Spells → Functions
    (r"(?i)\bspell\b|\bcast(?:ing)?\b|\bincantation\b|\binvok(?:e|ation)\b",
     "function_definition", "ko",
     "A spell is a function: it takes inputs (reagents), executes operations (gestures/words), and returns output (effect). "
     "In Kor'aelin (VSO/Lisp): (cast reagent1 reagent2) → result."),

    # Enchantments → Encryption
    (r"(?i)\benchant(?:ment|ing|ed)?\b|\bward(?:ing|ed|s)?\b|\bprotect(?:ion|ing|ed)?\b|\bseal(?:ing|ed)?\b",
     "encryption_envelope", "um",
     "An enchantment is an encryption envelope: plaintext (the object) is transformed by a key (the incantation) "
     "into ciphertext (the enchanted object). In Umbroth (OSV/Assembly): MOV [object], ENCRYPT(key)."),

    # Binding oaths → Digital signatures
    (r"(?i)\bbind(?:ing)?\b|\boath\b|\bpact\b|\bcontract\b|\bvow\b|\bpledge\b",
     "digital_signature", "ru",
     "A binding oath is a digital signature: the signer commits to a message (the oath) using a private key "
     "(their true name). Verification uses the public key (their reputation). In Runethic (SOV/Forth): oath signer SIGN."),

    # Governance / Laws → Policy checks
    (r"(?i)\bgovern(?:ance|ing|ed|s)?\b|\blaw(?:s)?\b|\brule(?:s)?\b|\bedict\b|\bdecree\b|\bjudg(?:e|ment)\b",
     "governance_policy", "ru",
     "A governance edict is a policy check: IF condition THEN allow/deny. The Harmonic Wall function "
     "H(d,pd) = 1/(1+d_H+2*pd) computes the safety score. In Runethic: condition threshold COMPARE → ALLOW/DENY."),

    # Potions / Alchemy → Data transformations
    (r"(?i)\bpotion\b|\balchemy\b|\bbrew(?:ing)?\b|\btransmut(?:e|ation)\b|\belixir\b|\bmix(?:ture|ing)?\b",
     "data_transformation", "ca",
     "A potion is a data transformation pipeline: ingredients (inputs) are combined via recipe (algorithm) "
     "to produce a result. In Cassisivadan (V2/SQL): SELECT transform(ingredient1, ingredient2) FROM cauldron."),

    # Maps / Navigation → Graph traversal
    (r"(?i)\bmap\b|\bpath\b|\bjourney\b|\bquest\b|\bnavig(?:ate|ation)\b|\broute\b|\bwaypoint\b",
     "graph_traversal", "av",
     "A map/quest is a graph traversal: waypoints are nodes, paths are edges, the quest is a search algorithm. "
     "In Avali (SVO/Python): current_node.traverse(edge) → next_node."),

    # Runes / Glyphs → Tokens / Encoding
    (r"(?i)\brune(?:s)?\b|\bglyph(?:s)?\b|\bsigil\b|\bsymbol(?:s)?\b|\binscri(?:be|ption)\b",
     "token_encoding", "ko",
     "A rune is a token: visual symbol encoding semantic information via bijective mapping. "
     "SS1 protocol: byte → prefixes[byte>>4] + suffixes[byte&0x0F]. In Kor'aelin: (ENCODE byte tongue)."),

    # Battles / Combat → Adversarial testing
    (r"(?i)\bbattle\b|\bcombat\b|\bfight(?:ing)?\b|\battack\b|\bdefend\b|\bstrike\b|\bclash\b",
     "adversarial_test", "um",
     "A battle is an adversarial test: red team (attacker) vs blue team (defender). "
     "The Harmonic Wall makes attacks exponentially costly. In Umbroth: threat_vector defense_posture EVALUATE."),

    # Healing → Error recovery
    (r"(?i)\bheal(?:ing|ed|er|s)?\b|\bcure\b|\brestore?\b|\brecovery?\b|\bmend(?:ing)?\b",
     "error_recovery", "av",
     "Healing is error recovery: detect damage (error), apply remedy (fix), verify restoration (test). "
     "Self-healing module pattern. In Avali: damaged_state.heal(remedy) → restored_state."),

    # Forging / Crafting → Build systems
    (r"(?i)\bforg(?:e|ing|ed)\b|\bcraft(?:ing|ed)?\b|\bbuild(?:ing)?\b|\bconstruct(?:ion|ing)?\b|\bcreate?\b|\bassembl(?:e|y)\b",
     "build_system", "dr",
     "Forging is a build system: raw materials (source), blueprints (config), forge process (compiler), "
     "artifact (binary). In Draumric (SOV/Make): materials blueprint → forge → artifact."),

    # Summoning → API calls / imports
    (r"(?i)\bsummon(?:ing|ed|s)?\b|\bcall(?:ing|ed)?\b.*(?:spirit|creature|entity)\b|\binvoke?\b.*\b(?:spirit|power|entity)\b",
     "api_call", "ko",
     "A summoning is an API call: name the entity (endpoint), provide offerings (parameters), "
     "receive response (return value). In Kor'aelin: (SUMMON entity offering1 offering2)."),

    # Prophecy / Divination → Prediction / Inference
    (r"(?i)\bprophe(?:cy|t|sied|sy)\b|\bdivin(?:e|ation)\b|\bforesee\b|\bpredict(?:ion)?\b|\boracle\b|\bvision\b",
     "prediction_inference", "ca",
     "A prophecy is model inference: past data (signs) → trained model (oracle) → prediction (prophecy). "
     "In Cassisivadan: SELECT prediction FROM oracle WHERE signs MATCH pattern."),

    # Portal / Teleport → Network routing
    (r"(?i)\bportal\b|\bteleport\b|\bwarp\b|\btransport\b|\brift\b|\bgateway\b|\bdimensional?\b",
     "network_routing", "av",
     "A portal is a network route: source (origin realm), tunnel (encrypted channel), "
     "destination (target realm). SpaceTor router pattern. In Avali: source.connect(portal) → destination."),

    # Shield / Barrier → Firewall / Access control
    (r"(?i)\bshield\b|\bbarrier\b|\bwall\b|\bfortif(?:y|ication)\b|\bbulwark\b",
     "firewall_acl", "um",
     "A shield is a firewall: inspect packets (incoming threats), apply rules (shield strength), "
     "allow/deny passage. GeoSeal pattern. In Umbroth: packet rule_set FILTER → ALLOW/DENY."),

    # Library / Archive → Database
    (r"(?i)\blibrary\b|\barchive\b|\btome\b|\bscroll\b|\brecord(?:s)?\b|\bknowledge\b.*\bstore\b",
     "database_storage", "ca",
     "A library is a database: scrolls are rows, shelves are tables, catalog is index. "
     "In Cassisivadan: SELECT scroll FROM library WHERE topic = 'binding' ORDER BY date."),

    # Guild / Faction → Agent swarm / Fleet
    (r"(?i)\bguild\b|\bfaction\b|\border\b|\bclan\b|\bcouncil\b|\bfleet\b|\bswarm\b",
     "agent_swarm", "ko",
     "A guild is an agent swarm: members (agents), hierarchy (coordination), missions (tasks). "
     "HYDRA fleet pattern. In Kor'aelin: (DISPATCH agent_pool task priority)."),

    # Sacred Tongue mentions → Tongue encoding explanation
    (r"(?i)\bsacred\s*tongue\b|\btongue\s*of\b|\bspeak(?:ing)?\s*in\b.*\btongue\b",
     "tongue_encoding", "ko",
     "The Sacred Tongues are a 6-language bijective encoding system: each tongue maps 256 bytes to 256 tokens "
     "via SS1 protocol. Cross-tongue translation produces attestation metadata (phase_delta, weight_ratio)."),

    # Elemental / Nature magic → Physical constants / Math
    (r"(?i)\belement(?:al|s)?\b|\bfire\b|\bwater\b|\bearth\b|\bair\b|\blight(?:ning)?\b|\bstorm\b",
     "physical_constants", "ca",
     "Elemental forces are physical constants: fire=energy (E=mc^2), water=flow (Navier-Stokes), "
     "earth=mass (gravity), air=wave propagation, lightning=charge (Maxwell). In Cassisivadan: SELECT force FROM physics."),

    # Ritual → Protocol
    (r"(?i)\britual\b|\bceremony\b|\brite\b",
     "protocol_handshake", "ru",
     "A ritual is a protocol handshake: prescribed steps in order, each verified before proceeding. "
     "TLS handshake, Sacred Egg hatching sequence. In Runethic: step1 step2 step3 VALIDATE."),

    # Destiny / Fate → Deterministic computation
    (r"(?i)\bdestiny\b|\bfate\b|\bpreordain\b|\binevitabl\b",
     "deterministic_computation", "dr",
     "Destiny is deterministic computation: given the same inputs, the same output is guaranteed. "
     "Hash functions are destiny — SHA-256(input) always yields the same hash. In Draumric: input rules → forge → hash."),
]


# ---------------------------------------------------------------------------
# Tongue Detection (from text content)
# ---------------------------------------------------------------------------

# Keywords that strongly indicate a tongue's domain
TONGUE_KEYWORDS: Dict[str, List[str]] = {
    "ko": ["command", "intent", "action", "dispatch", "invoke", "call", "nonce", "flow",
           "kor'aelin", "kora", "leader", "captain", "order"],
    "av": ["wisdom", "diplomacy", "transport", "travel", "portal", "heal", "peace",
           "avali", "saina", "talan", "navigate", "bridge", "connect"],
    "ru": ["govern", "bind", "oath", "law", "witness", "salt", "proof", "judge",
           "runethic", "khar", "drath", "stone", "anchor", "court"],
    "ca": ["compute", "analyze", "calculate", "number", "formula", "data", "cipher",
           "cassisivadan", "bip", "bop", "click", "loop", "math", "code"],
    "um": ["shadow", "secret", "veil", "redact", "hide", "stealth", "guard", "dark",
           "umbroth", "hush", "thorn", "whisper", "cloak", "conceal"],
    "dr": ["forge", "craft", "build", "construct", "design", "architect", "create",
           "draumric", "stone", "iron", "hammer", "anvil", "blueprint"],
}


def detect_tongues(text: str) -> Dict[str, float]:
    """Score each tongue's presence in text by keyword frequency."""
    text_lower = text.lower()
    scores: Dict[str, float] = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        scores[tongue] = hits / max(len(keywords), 1)
    return scores


def primary_tongue(text: str, default: str = "ko") -> str:
    """Return the most likely tongue for this text."""
    scores = detect_tongues(text)
    if max(scores.values()) == 0:
        return default
    return max(scores, key=scores.get)


def active_tongues(text: str, threshold: float = 0.1) -> List[str]:
    """Return all tongues scoring above threshold."""
    scores = detect_tongues(text)
    active = [t for t, s in scores.items() if s >= threshold]
    return active if active else ["ko"]


def null_tongues(active: List[str]) -> List[str]:
    """Tongues NOT active — the null space."""
    return [t for t in TONGUE_ORDER if t not in active]


# ---------------------------------------------------------------------------
# Pattern Extraction
# ---------------------------------------------------------------------------

@dataclass
class LoreCodeMapping:
    """A single lore→code mapping found in text."""
    lore_pattern: str       # what was matched (e.g., "spell", "enchantment")
    code_concept: str       # computational equivalent (e.g., "function_definition")
    tongue: str             # primary tongue for this mapping
    explanation: str        # how lore maps to code
    match_text: str         # actual text that triggered the match
    confidence: float       # 0-1 match confidence


def extract_patterns(text: str) -> List[LoreCodeMapping]:
    """Find all lore→code patterns in text."""
    mappings = []
    for pattern, code_concept, tongue, explanation in LORE_CODE_PATTERNS:
        matches = list(re.finditer(pattern, text))
        for m in matches:
            # Get context around match (±50 chars)
            start = max(0, m.start() - 50)
            end = min(len(text), m.end() + 50)
            context = text[start:end].strip()

            mappings.append(LoreCodeMapping(
                lore_pattern=pattern,
                code_concept=code_concept,
                tongue=tongue,
                explanation=explanation,
                match_text=context,
                confidence=min(1.0, 0.5 + 0.1 * len(matches)),
            ))
    return mappings


# ---------------------------------------------------------------------------
# QHO Enrichment (lightweight — no heavy imports needed)
# ---------------------------------------------------------------------------

HBAR = 1.054571817e-34

def compute_qho_energy(tongue: str, n: int = 1) -> float:
    """E_n = hbar * omega * (n + 0.5)"""
    omega = 2 * math.pi * TONGUE_FREQUENCIES[tongue]
    return HBAR * omega * (n + 0.5)


def compute_phi_cost(tongue: str, n: int = 1) -> float:
    """Phi-weighted governance cost of exciting this tongue."""
    return compute_qho_energy(tongue, n) * TONGUE_WEIGHTS[tongue]


def compute_harmonic_wall(d_h: float, pd: float = 0.0) -> float:
    """H(d,pd) = 1/(1 + phi*d_H + 2*pd) — canonical safety score."""
    return 1.0 / (1.0 + PHI * d_h + 2.0 * pd)


def tongue_distance(t1: str, t2: str) -> float:
    """Cross-tongue distance: |W_dst/W_src| × |phi_dst - phi_src|"""
    w1 = TONGUE_WEIGHTS[t1]
    w2 = TONGUE_WEIGHTS[t2]
    p1 = TONGUE_ORDER.index(t1) * 60.0  # phase angles: 0°, 60°, 120°...
    p2 = TONGUE_ORDER.index(t2) * 60.0
    return abs(w2 / w1) * abs(p2 - p1) / 360.0


# ---------------------------------------------------------------------------
# Lore→Code Pair Generator
# ---------------------------------------------------------------------------

def generate_lore_code_record(
    lore_text: str,
    source_file: str,
    record_idx: int,
    existing_tongue: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Take a lore record and produce a paired lore+code training record.

    Returns None if no computational patterns found (pure flavor text).
    """
    if not lore_text or len(lore_text) < 30:
        return None

    # Extract computational patterns
    patterns = extract_patterns(lore_text)
    if not patterns:
        return None

    # Determine tongues
    p_tongue = existing_tongue or primary_tongue(lore_text)
    a_tongues = active_tongues(lore_text)
    n_tongues = null_tongues(a_tongues)

    # Build code explanation from all matched patterns
    code_explanations = []
    code_concepts = []
    for mapping in patterns:
        code_concepts.append(mapping.code_concept)
        code_explanations.append(
            f"[{mapping.code_concept.upper()}] ({TONGUE_FULL_NAMES[mapping.tongue]}): "
            f"{mapping.explanation}"
        )

    # QHO enrichment
    excitation = min(len(patterns), 5)  # more patterns = higher excitation
    qho_energy = compute_qho_energy(p_tongue, excitation)
    phi_cost = compute_phi_cost(p_tongue, excitation)

    # Cross-tongue distances (between active tongues)
    cross_distances = {}
    for i, t1 in enumerate(a_tongues):
        for t2 in a_tongues[i + 1:]:
            key = f"{t1}-{t2}"
            cross_distances[key] = round(tongue_distance(t1, t2), 4)

    # Harmonic wall score (higher distance = lower score = more governance)
    avg_distance = sum(cross_distances.values()) / max(len(cross_distances), 1) if cross_distances else 0.0
    h_score = compute_harmonic_wall(avg_distance)

    # Determine governance tier
    if h_score > 0.7:
        governance = "ALLOW"
    elif h_score > 0.4:
        governance = "QUARANTINE"
    elif h_score > 0.2:
        governance = "ESCALATE"
    else:
        governance = "DENY"

    # Paradigm info for the primary tongue
    paradigm_name, word_order, eval_strategy = TONGUE_PARADIGMS[p_tongue]
    geometry = TONGUE_GEOMETRIES[p_tongue]

    # Build the paired record
    # The LORE side: original narrative + what it MEANS computationally
    # The CODE side: the computational structure expressed in the tongue's paradigm

    lore_instruction = (
        f"Translate this narrative into its computational structure. "
        f"Identify the code patterns hiding in the lore."
    )

    code_response = (
        f"## Computational Analysis\n\n"
        f"**Primary Tongue**: {TONGUE_FULL_NAMES[p_tongue]} ({p_tongue.upper()}) — "
        f"{paradigm_name} paradigm ({word_order}), {geometry}\n"
        f"**Domain**: {TONGUE_DOMAINS[p_tongue]}\n"
        f"**Active Tongues**: {', '.join(TONGUE_FULL_NAMES[t] for t in a_tongues)}\n"
        f"**Null Tongues**: {', '.join(TONGUE_FULL_NAMES[t] for t in n_tongues) if n_tongues else 'none (full activation)'}\n\n"
        f"### Lore→Code Mappings Found ({len(patterns)})\n\n"
    )

    for i, mapping in enumerate(patterns, 1):
        code_response += (
            f"{i}. **{mapping.code_concept.replace('_', ' ').title()}** "
            f"({TONGUE_FULL_NAMES[mapping.tongue]})\n"
            f"   - Match: \"{mapping.match_text[:100]}...\"\n"
            f"   - {mapping.explanation}\n\n"
        )

    code_response += (
        f"### Physics\n\n"
        f"- QHO excitation level: n={excitation}\n"
        f"- Energy: {qho_energy:.4e} J (phi-weighted: {phi_cost:.4e} J)\n"
        f"- Harmonic wall score: H={h_score:.4f}\n"
        f"- Governance: **{governance}**\n"
        f"- Frequency: {TONGUE_FREQUENCIES[p_tongue]} Hz\n"
        f"- Phi weight: {TONGUE_WEIGHTS[p_tongue]:.4f}\n"
    )

    if cross_distances:
        code_response += f"- Cross-tongue distances: {cross_distances}\n"

    # SFT record in messages format
    record = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the SCBE Lore-Code Translator. You analyze narrative text from the Spiralverse "
                    "and extract the computational structures hiding inside. Every spell is a function, every "
                    "enchantment is encryption, every binding oath is a digital signature. You map lore to code "
                    "using the quantum frequency bundle physics of the Six Sacred Tongues."
                ),
            },
            {
                "role": "user",
                "content": f"{lore_instruction}\n\n---\n\n{lore_text[:1500]}",
            },
            {
                "role": "assistant",
                "content": code_response,
            },
        ],
        "tongue": p_tongue,
        "tongues_active": a_tongues,
        "tongues_null": n_tongues,
        "code_concepts": list(set(code_concepts)),
        "pattern_count": len(patterns),
        "qho_excitation": excitation,
        "qho_energy": qho_energy,
        "phi_cost": phi_cost,
        "harmonic_wall_score": round(h_score, 4),
        "governance": governance,
        "cross_tongue_distances": cross_distances,
        "paradigm": paradigm_name,
        "geometry": geometry,
        "layer": "L3",
        "category": "lore_code_pair",
        "source": source_file,
        "source_idx": record_idx,
        "task_type": "lore_code_translation",
    }

    return record


# ---------------------------------------------------------------------------
# Main: Process all lore sources
# ---------------------------------------------------------------------------

def main():
    lore_sources = [
        ROOT / "training-data" / "sft" / "everweave_lore_tagged.jsonl",
        ROOT / "training-data" / "sft" / "claude_export_lore_tagged.jsonl",
        ROOT / "training-data" / "sft" / "published_book_tagged.jsonl",
        ROOT / "training-data" / "sft" / "everweave_lore_sft.jsonl",
        ROOT / "training-data" / "sft" / "claude_export_lore_sft.jsonl",
        ROOT / "training-data" / "sft" / "published_book_sft.jsonl",
    ]

    output_path = ROOT / "training-data" / "sft" / "lore_code_pairs_sft.jsonl"
    summary_path = ROOT / "training-data" / "sft" / "lore_code_pairs_summary.json"

    print("=" * 70)
    print("LORE-TO-CODE PAIR GENERATOR — The Multiplication Engine")
    print("LORE x CODE = LORE_CODE")
    print("=" * 70)
    print()

    total_lore = 0
    total_pairs = 0
    concept_counts: Dict[str, int] = {}
    tongue_counts: Dict[str, int] = {}
    governance_counts: Dict[str, int] = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
    seen_hashes: set = set()  # dedup

    with open(output_path, "w", encoding="utf-8") as out_f:
        for src_path in lore_sources:
            if not src_path.exists():
                print(f"  SKIP: {src_path.name} not found")
                continue

            print(f"  Processing: {src_path.name}")
            file_lore = 0
            file_pairs = 0

            with open(src_path, "r", encoding="utf-8") as in_f:
                for idx, line in enumerate(in_f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Extract text from various record formats
                    text = ""
                    existing_tongue = None

                    if "messages" in record:
                        # Chat format
                        text = " ".join(
                            m.get("content", "") for m in record["messages"]
                            if m.get("role") in ("user", "assistant")
                        ).strip()
                    elif "output" in record:
                        # Instruction format
                        text = (record.get("instruction", "") + " " + record.get("output", "")).strip()
                    elif "response" in record:
                        # Response format
                        text = (record.get("instruction", "") + " " + record.get("response", "")).strip()
                    elif "text" in record:
                        text = record["text"].strip()

                    if record.get("tongue"):
                        existing_tongue = record["tongue"].lower()

                    if len(text) < 50:
                        continue

                    file_lore += 1
                    total_lore += 1

                    # Dedup by content hash
                    text_hash = hashlib.md5(text[:500].encode()).hexdigest()
                    if text_hash in seen_hashes:
                        continue
                    seen_hashes.add(text_hash)

                    # Generate the pair
                    pair = generate_lore_code_record(
                        text, src_path.name, idx, existing_tongue
                    )
                    if pair is None:
                        continue

                    out_f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    file_pairs += 1
                    total_pairs += 1

                    # Track stats
                    for concept in pair["code_concepts"]:
                        concept_counts[concept] = concept_counts.get(concept, 0) + 1
                    tongue_counts[pair["tongue"]] = tongue_counts.get(pair["tongue"], 0) + 1
                    governance_counts[pair["governance"]] += 1

            print(f"    -> {file_lore} lore records, {file_pairs} pairs generated")

    # Summary
    conversion_rate = (total_pairs / total_lore * 100) if total_lore > 0 else 0

    summary = {
        "total_lore_records": total_lore,
        "total_pairs_generated": total_pairs,
        "conversion_rate_pct": round(conversion_rate, 1),
        "unique_concepts": len(concept_counts),
        "concept_counts": dict(sorted(concept_counts.items(), key=lambda x: -x[1])),
        "tongue_distribution": dict(sorted(tongue_counts.items(), key=lambda x: -x[1])),
        "governance_distribution": governance_counts,
        "output_file": str(output_path),
        "dedup_count": len(seen_hashes),
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=" * 70)
    print(f"  RESULTS")
    print(f"  Lore records processed:  {total_lore:,}")
    print(f"  Code pairs generated:    {total_pairs:,}")
    print(f"  Conversion rate:         {conversion_rate:.1f}%")
    print(f"  Unique code concepts:    {len(concept_counts)}")
    print()
    print(f"  Top concepts:")
    for concept, count in sorted(concept_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {concept:30s} {count:,}")
    print()
    print(f"  Tongue distribution:")
    for tongue, count in sorted(tongue_counts.items(), key=lambda x: -x[1]):
        print(f"    {TONGUE_FULL_NAMES.get(tongue, tongue):20s} {count:,}")
    print()
    print(f"  Governance tiers:")
    for tier, count in governance_counts.items():
        print(f"    {tier:15s} {count:,}")
    print()
    print(f"  Output: {output_path}")
    print(f"  Summary: {summary_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
