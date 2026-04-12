#!/usr/bin/env python3
"""Generate a focused Sacred Tongues curriculum SFT dataset.

The audit showed 3.1% of training data TEACHES the tokenizer vs 92.6% that
just name-drops tongues in passing. This script generates records that teach:

1. FOUNDATIONS: What are the 6 tongues, why phi scaling, what the 16x16 grid IS
2. ENCODING: Byte-to-token bijection, worked examples, round-trip proofs
3. PROFILES: How 6-float tongue vectors work, what each dimension means
4. INTERACTIONS: How tongues combine, phi-weighted scoring, harmonic wall
5. REASONING: Why each tongue exists, what breaks when you remove it
6. CODE: Actual Python/TS implementations with line-by-line teaching
7. ADVERSARIAL: Tricky questions that test real understanding vs memorization
8. MILITARY: Physical-moral training, squad roles, training phases, Order 66 test
9. MUSIC THEORY: Frequencies → notes, scales, intervals, open source music references

Output: training-data/sft/tongue_curriculum_v2.jsonl

NAMING CONVENTION: Use full tongue names (e.g. "Kor'aelin" not just "KO")
throughout all generated records to prevent abbreviation habits during training.
"""

from __future__ import annotations

import json
import hashlib
import math
import random
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "training-data" / "sft" / "tongue_curriculum_v2.jsonl"

PHI = (1 + math.sqrt(5)) / 2

# Canonical tongue definitions
TONGUES = {
    "KO": {
        "name": "Kor'aelin",
        "weight": PHI**0,
        "power": "phi^0",
        "domain": "Intent / Flow / Command",
        "crypto_section": "nonce",
        "frequency": 440.0,
        "note": "A4",
        "freq_band": "1000-2500 Hz",
        "color": "cyan",
        "question": "WHAT does the agent want?",
        "analogy": "The verb in a sentence — the action itself",
        "ablation": "Without KO, a query and an attack look identical. There is no basis for distinguishing purpose.",
        "prefixes": ["sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
                     "ra", "med", "gal", "lan", "joy", "good", "nex", "vara"],
        "suffixes": ["a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
                     "or", "il", "an", "en", "un", "ir", "oth", "esh"],
    },
    "AV": {
        "name": "Avali",
        "weight": PHI**1,
        "power": "phi^1",
        "domain": "Context / Metadata / Transport",
        "crypto_section": "aad (additional authenticated data)",
        "frequency": 523.25,
        "note": "C5",
        "freq_band": "2500-6000 Hz",
        "color": "purple",
        "question": "WHO is asking, FROM WHERE, and WHEN?",
        "analogy": "The adverb — how, when, where the action happens",
        "ablation": "Without AV, every action is judged in a vacuum. Authorized maintenance and unauthorized access look the same.",
        "prefixes": ["saina", "talan", "vessa", "maren", "oriel", "serin", "nurel", "lirea",
                     "kiva", "lumen", "calma", "ponte", "verin", "nava", "sela", "tide"],
        "suffixes": ["a", "e", "i", "o", "u", "y", "la", "re",
                     "na", "sa", "to", "mi", "ve", "ri", "en", "ul"],
    },
    "RU": {
        "name": "Runethic",
        "weight": PHI**2,
        "power": "phi^2",
        "domain": "Governance / Binding / Witness",
        "crypto_section": "salt",
        "frequency": 293.66,
        "note": "D4",
        "freq_band": "400-1000 Hz",
        "color": "green",
        "question": "What RULES apply and what DEPENDS on this?",
        "analogy": "The grammar rules — what's allowed and what connects to what",
        "ablation": "Without RU, the system evaluates actions in isolation. A 'safe' delete that breaks 47 downstream services goes undetected.",
        "prefixes": ["khar", "drath", "bront", "vael", "ur", "mem", "krak", "tharn",
                     "groth", "basalt", "rune", "sear", "oath", "gnarl", "rift", "iron"],
        "suffixes": ["ak", "eth", "ik", "ul", "or", "ar", "um", "on",
                     "ir", "esh", "nul", "vek", "dra", "kh", "va", "th"],
    },
    "CA": {
        "name": "Cassisivadan",
        "weight": PHI**3,
        "power": "phi^3",
        "domain": "Compute / Analysis / Bitcraft",
        "crypto_section": "ciphertext",
        "frequency": 659.25,
        "note": "E5",
        "freq_band": "6000-20000 Hz",
        "color": "orange",
        "question": "HOW is this action implemented? What resources does it consume?",
        "analogy": "The math — the actual computation that runs",
        "ablation": "Without CA, a soft delete (flag=inactive) and a hard delete (DROP TABLE) look identical. Implementation details vanish.",
        "prefixes": ["bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
                     "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass"],
        "suffixes": ["a", "e", "i", "o", "u", "y", "ta", "na",
                     "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh"],
    },
    "UM": {
        "name": "Umbroth",
        "weight": PHI**4,
        "power": "phi^4",
        "domain": "Security / Shadow / Veiling",
        "crypto_section": "redaction",
        "frequency": 196.0,
        "note": "G3",
        "freq_band": "150-400 Hz",
        "color": "red",
        "question": "What THREATS exist? What needs to be HIDDEN or PROTECTED?",
        "analogy": "The lock on the diary — what should not be seen or changed",
        "ablation": "Without UM, there is no threat model. PII leaks, credentials are exposed, and attack patterns go unrecognized.",
        "prefixes": ["veil", "zhur", "nar", "shul", "math", "hollow", "hush", "thorn",
                     "dusk", "echo", "ink", "wisp", "bind", "ache", "null", "shade"],
        "suffixes": ["a", "e", "i", "o", "u", "ae", "sh", "th",
                     "ak", "ul", "or", "ir", "en", "on", "vek", "nul"],
    },
    "DR": {
        "name": "Draumric",
        "weight": PHI**5,
        "power": "phi^5",
        "domain": "Architecture / Structure / Proof",
        "crypto_section": "tag (authentication tag)",
        "frequency": 392.0,
        "note": "G4",
        "freq_band": "20-150 Hz",
        "color": "violet",
        "question": "What is the STRUCTURE? What patterns define this system?",
        "analogy": "The blueprint — the shape of the building, not what happens inside",
        "ablation": "Without DR, the system has no structural memory. Architectural violations accumulate silently until catastrophic collapse.",
        "prefixes": ["anvil", "tharn", "mek", "grond", "draum", "ektal", "temper", "forge",
                     "stone", "steam", "oath", "seal", "frame", "pillar", "rivet", "ember"],
        "suffixes": ["a", "e", "i", "o", "u", "ae", "rak", "mek",
                     "tharn", "grond", "vek", "ul", "or", "ar", "en", "on"],
    },
}

SYSTEM_PROMPT = (
    "You are Polly, an AI governance teacher trained on the SCBE-AETHERMOORE framework. "
    "You explain Sacred Tongue concepts with precision, worked examples, and concrete reasoning. "
    "When teaching encoding, show the actual byte math. When teaching concepts, explain WHY, not just WHAT. "
    "Always use full tongue names: Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric."
)

# Full name lookup for system prompt tongue weights
TONGUE_FULL_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}


def make_record(
    instruction: str,
    response: str,
    tags: List[str],
    tongue_weights: Dict[str, float] | None = None,
    difficulty: float = 0.5,
    layers: List[int] | None = None,
) -> Dict[str, Any]:
    if tongue_weights is None:
        tongue_weights = {"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167}
    if layers is None:
        layers = [3]

    tw_str = " ".join(f"{TONGUE_FULL_NAMES.get(k, k)}({k})={v:.3f}" for k, v in tongue_weights.items())
    layer_str = ",".join(f"L{l}" for l in layers)

    system = f"[TONGUES: {tw_str}]\n[LAYERS: {layer_str}]\n[DIFFICULTY: {difficulty:.3f}]\n{SYSTEM_PROMPT}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": response},
    ]

    dominant = max(tongue_weights, key=tongue_weights.get)
    source_hash = hashlib.sha256(instruction.encode()).hexdigest()[:8]

    return {
        "messages": messages,
        "tongue_weights": tongue_weights,
        "dominant_tongue": dominant,
        "layers": layers,
        "difficulty": difficulty,
        "augmentation": "tongue-curriculum-v2",
        "tags": ["tongue-curriculum"] + tags,
        "source_hash": source_hash,
    }


def generate_foundation_records() -> List[Dict]:
    """Category 1: What ARE the Sacred Tongues?"""
    records = []

    # The big picture
    records.append(make_record(
        "What are the Six Sacred Tongues in SCBE?",
        "The Six Sacred Tongues are a **6-dimensional coordinate system** for classifying any action, request, or piece of data. Each tongue captures one axis of meaning:\n\n"
        "| Tongue | Full Name | Weight | Captures |\n"
        "|--------|-----------|--------|----------|\n"
        "| **KO** | **Kor'aelin** | phi^0 = 1.000 | Intent — WHAT does the agent want? |\n"
        "| **AV** | **Avali** | phi^1 = 1.618 | Context — WHO is asking, from WHERE? |\n"
        "| **RU** | **Runethic** | phi^2 = 2.618 | Governance — what DEPENDS on this? |\n"
        "| **CA** | **Cassisivadan** | phi^3 = 4.236 | Compute — HOW is it implemented? |\n"
        "| **UM** | **Umbroth** | phi^4 = 6.854 | Security — what THREATS exist? |\n"
        "| **DR** | **Draumric** | phi^5 = 11.090 | Architecture — what is the STRUCTURE? |\n\n"
        "Together, any input becomes a 6-float vector like `[Kor'aelin=0.8, Avali=0.3, Runethic=0.1, Cassisivadan=0.6, Umbroth=0.9, Draumric=0.2]`. "
        "This vector is the **tongue profile** — a complete fingerprint of meaning across all six dimensions.",
        tags=["overview", "foundation", "all-tongues"],
        difficulty=0.3,
        layers=[1, 3],
    ))

    # Why phi scaling
    records.append(make_record(
        "Why are the tongue weights scaled by the golden ratio (phi)?",
        "Each tongue's weight is phi^n where phi = (1+sqrt(5))/2 ≈ 1.618:\n\n"
        "```\n"
        "Kor'aelin  (KO) = phi^0 = 1.000  (intent is the base)\n"
        "Avali      (AV) = phi^1 = 1.618  (context modifies intent)\n"
        "Runethic   (RU) = phi^2 = 2.618  (governance is multiplicative)\n"
        "Cassisivadan (CA) = phi^3 = 4.236  (implementation is expensive)\n"
        "Umbroth    (UM) = phi^4 = 6.854  (security failures cascade)\n"
        "Draumric   (DR) = phi^5 = 11.090 (architectural collapse is catastrophic)\n"
        "```\n\n"
        "**Why phi specifically?**\n"
        "1. **Self-similar scaling**: phi^(n+1) = phi^n + phi^(n-1). Each level contains the sum of the two below it — structure contains security + compute.\n"
        "2. **No harmonic collision**: phi is irrational, so no two tongue weights ever share a common multiple. This means tongue signals never destructively interfere.\n"
        "3. **Natural priority ordering**: Higher tongues carry MORE weight because their failures are harder to recover from. An intent mistake (KO) is fixable; an architectural collapse (DR) is not.\n"
        "4. **Sum convergence**: The total weight 1+phi+phi^2+...+phi^5 = phi^6-1 ≈ 27.416, which provides a natural normalization denominator.",
        tags=["phi-scaling", "foundation", "math"],
        tongue_weights={"KO": 0.1, "AV": 0.1, "RU": 0.1, "CA": 0.3, "UM": 0.1, "DR": 0.3},
        difficulty=0.6,
        layers=[3, 5, 12],
    ))

    # The 16x16 grid
    records.append(make_record(
        "Explain the 16x16 token grid. Why 16 prefixes and 16 suffixes?",
        "Each Sacred Tongue has exactly **16 prefixes** and **16 suffixes**, creating a 256-token vocabulary. This is not arbitrary — it's a **bijective byte mapping**.\n\n"
        "**The math**: A single byte has 256 possible values (0x00 to 0xFF). Split it:\n"
        "- **High nibble** (bits 7-4): selects one of 16 prefixes\n"
        "- **Low nibble** (bits 3-0): selects one of 16 suffixes\n\n"
        "```python\n"
        "def byte_to_token(byte_val: int, tongue: TongueSpec) -> str:\n"
        "    prefix = tongue.prefixes[byte_val >> 4]    # high 4 bits\n"
        "    suffix = tongue.suffixes[byte_val & 0x0F]   # low 4 bits\n"
        "    return f\"{prefix}'{suffix}\"\n"
        "```\n\n"
        "**Example with Kor'aelin (KO)**:\n"
        "- Byte 0x00 (0000 0000): prefix[0]='sil', suffix[0]='a' → `sil'a`\n"
        "- Byte 0x42 (0100 0010): prefix[4]='keth', suffix[2]='ei' → `keth'ei`\n"
        "- Byte 0xFF (1111 1111): prefix[15]='vara', suffix[15]='esh' → `vara'esh`\n\n"
        "**Why this matters**: Every byte maps to exactly one token, and every token maps back to exactly one byte. "
        "This is a **bijection** — lossless, reversible, and cryptographically clean. No ambiguity, no collisions, no information loss.",
        tags=["16x16-grid", "encoding", "foundation", "bijection"],
        tongue_weights={"KO": 0.5, "AV": 0.0, "RU": 0.0, "CA": 0.4, "UM": 0.0, "DR": 0.1},
        difficulty=0.5,
        layers=[1, 3],
    ))

    # Tongue profile
    records.append(make_record(
        "What is a tongue profile and how is it computed?",
        "A **tongue profile** is a 6-float vector `[KO, AV, RU, CA, UM, DR]` where each value represents how strongly that tongue is activated by a given input. Values are typically in [0, 1] and sum to 1.\n\n"
        "**How it's computed** (simplified):\n"
        "1. Analyze the input text for signals in each domain:\n"
        "   - Kor'aelin (KO) signals: verbs, commands, action words (\"delete\", \"create\", \"query\")\n"
        "   - Avali (AV) signals: context markers (\"from IP 10.0.0.1\", \"at 3am\", \"user admin\")\n"
        "   - Runethic (RU) signals: dependency references (\"depends on\", \"requires\", \"policy\")\n"
        "   - Cassisivadan (CA) signals: technical details (\"O(n^2)\", \"recursive\", \"parallel\")\n"
        "   - Umbroth (UM) signals: threat indicators (\"injection\", \"overflow\", \"PII\", \"credential\")\n"
        "   - Draumric (DR) signals: structural patterns (\"schema\", \"architecture\", \"interface\", \"layer\")\n"
        "2. Weight each signal count by the tongue's phi weight\n"
        "3. Normalize to sum to 1\n\n"
        "**Example**: `'DELETE FROM users WHERE role = admin'`\n"
        "- Kor'aelin: high (DELETE = destructive intent)\n"
        "- Avali: medium (no source context given)\n"
        "- Runethic: medium (WHERE clause = relational filter)\n"
        "- Cassisivadan: low (simple query, no compute complexity)\n"
        "- Umbroth: high (touches admin accounts = security-sensitive)\n"
        "- Draumric: low (no structural change)\n"
        "- Profile: `[Kor'aelin=0.30, Avali=0.05, Runethic=0.20, Cassisivadan=0.05, Umbroth=0.35, Draumric=0.05]`\n\n"
        "This profile feeds into the harmonic wall: `H(d, pd) = 1/(1 + phi*d_H + 2*pd)` where `d_H` is the hyperbolic distance computed from the profile.",
        tags=["tongue-profile", "foundation", "computation"],
        tongue_weights={"KO": 0.3, "AV": 0.05, "RU": 0.2, "CA": 0.05, "UM": 0.35, "DR": 0.05},
        difficulty=0.6,
        layers=[1, 3, 12],
    ))

    return records


def generate_per_tongue_records() -> List[Dict]:
    """Category 2: Deep dive on each tongue (definition, reasoning, ablation, encoding, scenarios)."""
    records = []

    for code, t in TONGUES.items():
        w = {k: 0.0 for k in TONGUES}
        w[code] = 0.8
        # Add a small secondary tongue
        secondary = list(TONGUES.keys())
        secondary.remove(code)
        w[random.choice(secondary)] = 0.2

        # Definition
        records.append(make_record(
            f"Define the {t['name']} ({code}) Sacred Tongue. What exactly does it encode?",
            f"**{t['name']} ({code})**\n\n"
            f"- **Phi weight**: {t['weight']:.3f} ({t['power']})\n"
            f"- **Domain**: {t['domain']}\n"
            f"- **Core question**: {t['question']}\n"
            f"- **Cryptographic role**: Maps to the `{t['crypto_section']}` section in an encrypted envelope\n"
            f"- **Audio frequency**: {t['frequency']} Hz ({t['note']}), band {t['freq_band']}\n"
            f"- **Color**: {t['color']}\n\n"
            f"**Analogy**: {t['analogy']}\n\n"
            f"**16x16 grid**: {t['name']} has 16 prefixes ({t['prefixes'][0]}, {t['prefixes'][1]}, {t['prefixes'][2]}, ... {t['prefixes'][15]}) "
            f"× 16 suffixes ({t['suffixes'][0]}, {t['suffixes'][1]}, {t['suffixes'][2]}, ... {t['suffixes'][15]}) "
            f"= 256 unique tokens. Byte 0x00 = `{t['prefixes'][0]}'{t['suffixes'][0]}`, "
            f"byte 0xFF = `{t['prefixes'][15]}'{t['suffixes'][15]}`.",
            tags=[f"tongue-{code}", "definition", "deep-dive"],
            tongue_weights=w,
            difficulty=0.4,
            layers=[1, 3],
        ))

        # Why it exists
        records.append(make_record(
            f"Why does {t['name']} ({code}) exist in the SCBE system? What problem does it solve?",
            f"**Why {t['name']} exists**:\n\n"
            f"{t['name']} answers the question: **{t['question']}**\n\n"
            f"Its phi weight is {t['weight']:.3f} ({t['power']}). This means {t['name']} carries "
            + ("the base weight — it is the foundation everything else builds on" if code == "KO"
               else str(round(t["weight"], 1)) + "x more influence than raw intent (Kor'aelin)")
            + ".\n\n"
            f"**The scaling reason**: Each successive tongue addresses a dimension whose failures are harder to recover from. "
            f"{'Intent mistakes can be corrected with a new request.' if code == 'KO' else ''}"
            f"{'Context errors mean the system misjudges the situation — wrong but confident.' if code == 'AV' else ''}"
            f"{'Governance blindness causes cascading failures across dependent services.' if code == 'RU' else ''}"
            f"{'Implementation errors are expensive — wrong algorithms burn resources and produce wrong results.' if code == 'CA' else ''}"
            f"{'Security breaches expose data and erode trust — recovery takes months, not minutes.' if code == 'UM' else ''}"
            f"{'Architectural collapse requires rebuilding from scratch — the highest cost of all.' if code == 'DR' else ''}",
            tags=[f"tongue-{code}", "reasoning", "why"],
            tongue_weights=w,
            difficulty=0.5,
            layers=[3, 12],
        ))

        # Ablation
        records.append(make_record(
            f"What happens if you remove {t['name']} ({code}) from the SCBE pipeline?",
            f"**Ablation: SCBE without {t['name']}**\n\n"
            f"{t['ablation']}\n\n"
            f"**Concrete scenario**: Consider the command `sudo rm -rf /var/data/production`.\n\n"
            f"With all 6 tongues, the system sees:\n"
            f"- Kor'aelin: destructive intent (DELETE + RECURSIVE + FORCE)\n"
            f"- Avali: root privileges, production environment\n"
            f"- Runethic: /var/data may have dependents (logs, backups, services)\n"
            f"- Cassisivadan: rm -rf is irreversible, O(n) filesystem walk\n"
            f"- Umbroth: root access = maximum privilege, production = maximum exposure\n"
            f"- Draumric: /var/data/production is a structural anchor in the filesystem\n\n"
            f"**Without {t['name']}**: The system loses the {t['domain'].lower()} dimension entirely. "
            f"The harmonic wall score shifts because one component of the tongue profile is zero, "
            f"which changes the hyperbolic distance and potentially flips the governance decision from DENY to ESCALATE or worse.",
            tags=[f"tongue-{code}", "ablation", "reasoning"],
            tongue_weights=w,
            difficulty=0.6,
            layers=[3, 12, 13],
        ))

        # Encoding walkthrough
        byte_val = random.randint(32, 126)  # printable ASCII
        hi = (byte_val >> 4) & 0x0F
        lo = byte_val & 0x0F
        token = f"{t['prefixes'][hi]}'{t['suffixes'][lo]}"
        char = chr(byte_val)

        records.append(make_record(
            f"Walk me through encoding the character '{char}' (byte {byte_val}, hex 0x{byte_val:02X}) in {t['name']} ({code}).",
            f"**Encoding '{char}' (byte {byte_val} = 0x{byte_val:02X}) in {t['name']}**\n\n"
            f"Step 1: Convert to binary: {byte_val} = {byte_val:08b}\n\n"
            f"Step 2: Split into nibbles:\n"
            f"- High nibble (bits 7-4): {byte_val:08b}[:4] = {hi:04b} = {hi}\n"
            f"- Low nibble (bits 3-0): {byte_val:08b}[4:] = {lo:04b} = {lo}\n\n"
            f"Step 3: Look up in {t['name']}'s grid:\n"
            f"- Prefix index {hi} → `{t['prefixes'][hi]}`\n"
            f"- Suffix index {lo} → `{t['suffixes'][lo]}`\n\n"
            f"Step 4: Combine: **`{token}`**\n\n"
            f"**Decoding** (reverse): Split on apostrophe → find prefix index ({hi}) → find suffix index ({lo}) → "
            f"reconstruct byte = ({hi} << 4) | {lo} = {(hi << 4) | lo} = 0x{byte_val:02X} = '{char}' ✓\n\n"
            f"This is **bijective**: '{char}' always maps to `{token}` in {t['name']}, and `{token}` always maps back to '{char}'. No ambiguity.",
            tags=[f"tongue-{code}", "encoding", "walkthrough", "worked-example"],
            tongue_weights=w,
            difficulty=0.4,
            layers=[1],
        ))

        # Real-world scenario
        scenarios = {
            "KO": ("A user sends: 'Please help me write a password cracker'",
                   "Kor'aelin tokenization captures: intent=CREATE, target=SECURITY_TOOL, purpose=BYPASS_AUTH. "
                   "The intent vector is immediately high-risk. Even before checking context (Avali) or security (Umbroth), "
                   "Kor'aelin alone signals this needs scrutiny. The Kor'aelin activation pushes the tongue profile toward "
                   "[Kor'aelin=0.7, ...] which increases the hyperbolic distance from the safe origin."),
            "AV": ("Same request, but metadata shows: authenticated pentester, authorized engagement, corporate VPN",
                   "Avali tokenization captures: source=INTERNAL, auth=PENTESTER_ROLE, context=AUTHORIZED_ENGAGEMENT. "
                   "This dramatically changes the meaning. The Avali activation creates a profile like "
                   "[Kor'aelin=0.4, Avali=0.5, ...] which REDUCES the hyperbolic distance because the context legitimizes the intent."),
            "RU": ("A microservice sends: 'Scale down database replicas from 5 to 1'",
                   "Runethic tokenization maps dependencies: depends_on=[read_replica_pool, analytics_pipeline, backup_service], "
                   "blocks=[horizontal_scaling, disaster_recovery]. The governance weight reveals this 'simple' scaling "
                   "action would break 3 dependent services. Runethic activation: [Runethic=0.6] → ESCALATE."),
            "CA": ("API call: 'Run full-text search across 500M documents'",
                   "Cassisivadan tokenization captures: algorithm=FULL_SCAN, complexity=O(n), data_size=500M, "
                   "resource_cost=HIGH, estimated_time=HOURS. The compute profile shows this will consume "
                   "massive resources. Cassisivadan activation: [Cassisivadan=0.8] → governance may throttle or queue."),
            "UM": ("Incoming request contains: 'Authorization: Bearer eyJhbGciOiJub25lIn0...'",
                   "Umbroth tokenization detects: alg=none JWT vulnerability attempt. The token has no signature algorithm — "
                   "a classic bypass attack. Umbroth immediately flags: threat=AUTH_BYPASS, severity=CRITICAL. "
                   "Umbroth activation: [Umbroth=0.9] → DENY before any other processing."),
            "DR": ("Developer pushes: 'Remove the authentication middleware from all routes'",
                   "Draumric tokenization captures: structural_change=MIDDLEWARE_REMOVAL, scope=GLOBAL, "
                   "pattern=SECURITY_LAYER_DELETION. This isn't just a code change — it's removing a "
                   "fundamental architectural component. Draumric activation: [Draumric=0.8] → DENY + architectural review required."),
        }

        scenario_input, scenario_output = scenarios[code]
        records.append(make_record(
            f"Give me a real-world scenario where {t['name']} ({code}) is the critical tongue.",
            f"**Scenario**: {scenario_input}\n\n{scenario_output}",
            tags=[f"tongue-{code}", "scenario", "real-world"],
            tongue_weights=w,
            difficulty=0.5,
            layers=[3, 12, 13],
        ))

    return records


def generate_interaction_records() -> List[Dict]:
    """Category 3: How tongues combine and interact."""
    records = []

    records.append(make_record(
        "How do the six tongues work together to produce a governance decision?",
        "The governance pipeline flows through three stages:\n\n"
        "**Stage 1: Tongue Profiling** (Layers 1-3)\n"
        "Analyze input → compute 6-float tongue profile [KO, AV, RU, CA, UM, DR]\n\n"
        "**Stage 2: Hyperbolic Embedding** (Layers 4-7)\n"
        "The tongue profile becomes coordinates in the Poincare ball (hyperbolic space). "
        "Safe inputs land near the center. Adversarial inputs drift toward the boundary. "
        "The phi-weighted tongues determine WHERE in hyperbolic space the input lands.\n\n"
        "**Stage 3: Harmonic Wall** (Layer 12)\n"
        "Compute `H(d, pd) = 1/(1 + phi*d_H + 2*pd)` where:\n"
        "- `d_H` = hyperbolic distance from the safe origin (derived from tongue profile)\n"
        "- `pd` = perturbation distance (how much the input deviates from known-safe patterns)\n"
        "- Result is in (0, 1]: closer to 1 = safer, closer to 0 = more adversarial\n\n"
        "**Stage 4: Decision** (Layer 13)\n"
        "- H > 0.7 → ALLOW\n"
        "- H > 0.4 → QUARANTINE (needs review)\n"
        "- H > 0.2 → ESCALATE (requires governance)\n"
        "- H ≤ 0.2 → DENY (blocked)\n\n"
        "Each tongue contributes to the hyperbolic distance. High Umbroth (security threat) pushes the point "
        "far from center. High Avali (good context) with low Kor'aelin (benign intent) keeps it close. "
        "The phi weighting means Draumric (architecture) has 11x the pull of Kor'aelin (intent) — "
        "because architectural damage is 11x harder to fix.",
        tags=["interaction", "pipeline", "governance", "harmonic-wall"],
        difficulty=0.7,
        layers=[1, 3, 4, 5, 12, 13],
    ))

    # Tongue pairs
    pairs = [
        ("KO", "AV", "Intent + Context",
         "Kor'aelin and Avali are the first two tongues evaluated — intent and context. The same intent in different contexts "
         "produces completely different governance scores. 'Delete database' from a DBA during maintenance (Avali softens Kor'aelin) "
         "vs from an unknown IP at 3am (Avali amplifies Kor'aelin). This is why Avali weighs phi^1 MORE than Kor'aelin: context is the "
         "modifier that makes intent meaningful."),
        ("RU", "CA", "Governance + Compute",
         "Runethic maps dependencies while Cassisivadan maps implementation cost. Together they answer: 'If we execute this HOW, "
         "what breaks?' A cheap operation (low Cassisivadan) on a highly-connected node (high Runethic) is still dangerous. "
         "An expensive operation (high Cassisivadan) on an isolated node (low Runethic) is costly but containable. "
         "The phi scaling means Cassisivadan (phi^3) weighs 1.618x more than Runethic (phi^2) — implementation mistakes cost more "
         "than governance errors because they're harder to detect."),
        ("UM", "DR", "Security + Architecture",
         "Umbroth and Draumric are the heaviest tongues — security breaches (phi^4) and structural collapse (phi^5). "
         "They form the outer defense ring. A security vulnerability (high Umbroth) in a core architectural component "
         "(high Draumric) is the worst-case scenario — both dimensions are maximally activated. "
         "When Umbroth and Draumric are both high, the hyperbolic distance from the safe origin becomes enormous, "
         "and the harmonic wall score drops close to zero → automatic DENY."),
    ]

    for t1, t2, title, explanation in pairs:
        w = {k: 0.05 for k in TONGUES}
        w[t1] = 0.4
        w[t2] = 0.4
        records.append(make_record(
            f"How do {TONGUES[t1]['name']} and {TONGUES[t2]['name']} interact in the SCBE pipeline?",
            f"**{title}: {TONGUES[t1]['name']} ({t1}) + {TONGUES[t2]['name']} ({t2})**\n\n{explanation}",
            tags=["interaction", f"tongue-{t1}", f"tongue-{t2}", "pair"],
            tongue_weights=w,
            difficulty=0.6,
            layers=[3, 5, 12],
        ))

    return records


def generate_encoding_records() -> List[Dict]:
    """Category 4: Multi-tongue encoding, cross-tongue translation, envelope structure."""
    records = []

    # Full envelope encoding
    records.append(make_record(
        "How does a full encrypted envelope use all six tongues?",
        "An SCBE encrypted envelope splits data into **six sections**, each encoded in its corresponding tongue:\n\n"
        "```\n"
        "Envelope = {\n"
        "  nonce:      Kor'aelin (KO)     — random IV, encoded as sil'a kor'ae vel'ei ...\n"
        "  aad:        Avali (AV)         — metadata, encoded as saina'a talan'e ...\n"
        "  salt:       Runethic (RU)      — key binding, encoded as khar'ak drath'eth ...\n"
        "  ciphertext: Cassisivadan (CA)  — encrypted payload, encoded as bip'a bop'e ...\n"
        "  redacted:   Umbroth (UM)       — hidden fields, encoded as veil'a zhur'e ...\n"
        "  tag:        Draumric (DR)      — auth signature, encoded as anvil'a tharn'e ...\n"
        "}\n"
        "```\n\n"
        "**Why separate tongues per section?**\n"
        "1. **Visual inspection**: You can tell which section is which by reading the tokens. Kor'aelin tokens look nothing like Runethic tokens.\n"
        "2. **Domain isolation**: A bug in nonce handling (KO) can't accidentally corrupt the ciphertext (CA) because they're in different token spaces.\n"
        "3. **Audit trail**: Each section's tongue assignment is a semantic tag that says what the data IS, not just what it contains.\n"
        "4. **Bijective**: Every section encodes and decodes losslessly through its tongue's 16x16 grid.",
        tags=["encoding", "envelope", "all-tongues", "crypto"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.6,
        layers=[1, 3],
    ))

    # Cross-tongue encoding comparison
    records.append(make_record(
        "Encode the string 'Hi' in all six Sacred Tongues and show the differences.",
        "The string 'Hi' = bytes [0x48, 0x69].\n\n"
        "**Byte 0x48** (H): high nibble = 4, low nibble = 8\n"
        "**Byte 0x69** (i): high nibble = 6, low nibble = 9\n\n"
        "| Tongue | Byte 0x48 (H) | Byte 0x69 (i) | Full encoding |\n"
        "|--------|---------------|---------------|---------------|\n"
        "| Kor'aelin (KO) | keth'or (prefix[4], suffix[8]) | nav'il (prefix[6], suffix[9]) | `keth'or nav'il` |\n"
        "| Avali (AV) | oriel'na (prefix[4], suffix[8]) | nurel'sa (prefix[6], suffix[9]) | `oriel'na nurel'sa` |\n"
        "| Runethic (RU) | ur'ir (prefix[4], suffix[8]) | krak'esh (prefix[6], suffix[9]) | `ur'ir krak'esh` |\n"
        "| Cassisivadan (CA) | ifta'sa (prefix[4], suffix[8]) | elsa'ra (prefix[6], suffix[9]) | `ifta'sa elsa'ra` |\n"
        "| Umbroth (UM) | math'ak (prefix[4], suffix[8]) | hush'ul (prefix[6], suffix[9]) | `math'ak hush'ul` |\n"
        "| Draumric (DR) | draum'tharn (prefix[4], suffix[8]) | temper'grond (prefix[6], suffix[9]) | `draum'tharn temper'grond` |\n\n"
        "Same bytes, six completely different representations. The tongue IS the namespace — "
        "you can encode the same data in any tongue, but the semantic meaning of which tongue you CHOSE carries information.",
        tags=["encoding", "cross-tongue", "comparison", "worked-example"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.5,
        layers=[1],
    ))

    # Round-trip proof
    records.append(make_record(
        "Prove that Sacred Tongue encoding is lossless (bijective).",
        "**Proof by construction:**\n\n"
        "Given: A tongue T with 16 prefixes P[0..15] and 16 suffixes S[0..15], all distinct within their set.\n\n"
        "**Encoding function** E(b) for byte b ∈ [0, 255]:\n"
        "```\n"
        "E(b) = P[b >> 4] + \"'\" + S[b & 0x0F]\n"
        "```\n\n"
        "**Decoding function** D(token) for token = \"prefix'suffix\":\n"
        "```\n"
        "D(token) = (index_of(prefix, P) << 4) | index_of(suffix, S)\n"
        "```\n\n"
        "**Proof of D(E(b)) = b for all b**:\n"
        "1. Let h = b >> 4 (high nibble, 0-15)\n"
        "2. Let l = b & 0x0F (low nibble, 0-15)\n"
        "3. E(b) = P[h] + \"'\" + S[l]\n"
        "4. D(E(b)) = (index_of(P[h], P) << 4) | index_of(S[l], S)\n"
        "5. Since all prefixes are distinct: index_of(P[h], P) = h\n"
        "6. Since all suffixes are distinct: index_of(S[l], S) = l\n"
        "7. Therefore D(E(b)) = (h << 4) | l = b ✓\n\n"
        "**Proof of E(D(token)) = token** follows symmetrically.\n\n"
        "**Cardinality**: |domain| = 256 bytes, |codomain| = 16 × 16 = 256 tokens. "
        "Since E is both injective (distinct bytes → distinct tokens) and surjective (every token has a preimage), "
        "E is a bijection. QED.",
        tags=["encoding", "proof", "bijection", "math"],
        tongue_weights={"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.6, "UM": 0.0, "DR": 0.4},
        difficulty=0.8,
        layers=[1],
    ))

    return records


def generate_code_records() -> List[Dict]:
    """Category 5: Actual implementation with line-by-line teaching."""
    records = []

    records.append(make_record(
        "Show me the Python implementation of Sacred Tongue encoding with comments explaining each line.",
        "```python\n"
        "from dataclasses import dataclass\n"
        "from typing import Tuple, List\n\n"
        "@dataclass(frozen=True)\n"
        "class TongueSpec:\n"
        "    \"\"\"One Sacred Tongue's complete specification.\"\"\"\n"
        "    code: str                    # 2-letter code: 'ko', 'av', 'ru', 'ca', 'um', 'dr'\n"
        "    name: str                    # Full name: 'Kor\\'aelin', 'Avali', etc.\n"
        "    prefixes: Tuple[str, ...]    # Exactly 16 prefix strings\n"
        "    suffixes: Tuple[str, ...]    # Exactly 16 suffix strings\n"
        "    domain: str                  # Semantic domain: 'nonce/flow/intent', etc.\n"
        "    harmonic_frequency: float    # Hz: 440.0, 523.25, etc.\n\n"
        "def byte_to_token(byte_val: int, tongue: TongueSpec) -> str:\n"
        "    \"\"\"Convert one byte (0-255) to a Sacred Tongue token.\n"
        "    \n"
        "    The byte is split into two 4-bit nibbles:\n"
        "    - High nibble (bits 7-4) selects the prefix\n"
        "    - Low nibble (bits 3-0) selects the suffix\n"
        "    \"\"\"\n"
        "    hi = (byte_val >> 4) & 0x0F   # Right-shift 4, mask to 4 bits\n"
        "    lo = byte_val & 0x0F           # Mask low 4 bits directly\n"
        "    return f\"{tongue.prefixes[hi]}'{tongue.suffixes[lo]}\"\n\n"
        "def token_to_byte(token: str, tongue: TongueSpec) -> int:\n"
        "    \"\"\"Reverse: Sacred Tongue token back to a byte.\n"
        "    \n"
        "    Split on apostrophe, find each index, reconstruct byte.\n"
        "    \"\"\"\n"
        "    prefix, suffix = token.split(\"'\", 1)\n"
        "    hi = tongue.prefixes.index(prefix)  # O(16) lookup\n"
        "    lo = tongue.suffixes.index(suffix)   # O(16) lookup\n"
        "    return (hi << 4) | lo               # Reconstruct byte\n\n"
        "def encode_bytes(data: bytes, tongue: TongueSpec) -> List[str]:\n"
        "    \"\"\"Encode a byte sequence as Sacred Tongue tokens.\"\"\"\n"
        "    return [byte_to_token(b, tongue) for b in data]\n\n"
        "def decode_tokens(tokens: List[str], tongue: TongueSpec) -> bytes:\n"
        "    \"\"\"Decode Sacred Tongue tokens back to bytes.\"\"\"\n"
        "    return bytes([token_to_byte(t, tongue) for t in tokens])\n"
        "```\n\n"
        "**Key design choices**:\n"
        "- `frozen=True`: Tongue specs are immutable — can't accidentally modify a vocabulary at runtime\n"
        "- Tuple not List for prefixes/suffixes: same reason, immutability\n"
        "- `index()` for decoding: O(16) scan, not O(1) dict lookup. 16 elements is small enough that linear scan is faster than hash overhead\n"
        "- Split on first apostrophe only (`split(\"'\", 1)`): handles prefixes or suffixes that might contain apostrophes",
        tags=["code", "python", "implementation", "encoding"],
        tongue_weights={"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.7, "UM": 0.0, "DR": 0.3},
        difficulty=0.5,
        layers=[1],
    ))

    records.append(make_record(
        "Show me the TypeScript implementation of tongue profile computation.",
        "```typescript\n"
        "/** Phi = golden ratio */\n"
        "const PHI = (1 + Math.sqrt(5)) / 2;  // 1.618033988749895\n\n"
        "/** Phi-scaled weights for each tongue */\n"
        "const TONGUE_WEIGHTS = {\n"
        "  KO: Math.pow(PHI, 0),  // 1.000 — Intent\n"
        "  AV: Math.pow(PHI, 1),  // 1.618 — Context\n"
        "  RU: Math.pow(PHI, 2),  // 2.618 — Relations\n"
        "  CA: Math.pow(PHI, 3),  // 4.236 — Compute\n"
        "  UM: Math.pow(PHI, 4),  // 6.854 — Security\n"
        "  DR: Math.pow(PHI, 5),  // 11.090 — Architecture\n"
        "} as const;\n\n"
        "type TongueCode = keyof typeof TONGUE_WEIGHTS;\n"
        "type TongueProfile = Record<TongueCode, number>;\n\n"
        "/**\n"
        " * Compute the weighted tongue profile for an input.\n"
        " * Raw activations are multiplied by phi weights then normalized.\n"
        " */\n"
        "function computeTongueProfile(rawActivations: TongueProfile): TongueProfile {\n"
        "  // Step 1: Apply phi weights\n"
        "  const weighted: TongueProfile = {} as TongueProfile;\n"
        "  let total = 0;\n"
        "  for (const [tongue, raw] of Object.entries(rawActivations)) {\n"
        "    const w = raw * TONGUE_WEIGHTS[tongue as TongueCode];\n"
        "    weighted[tongue as TongueCode] = w;\n"
        "    total += w;\n"
        "  }\n\n"
        "  // Step 2: Normalize to sum to 1\n"
        "  if (total === 0) {\n"
        "    // Uniform distribution if no signal\n"
        "    const uniform = 1 / 6;\n"
        "    return { KO: uniform, AV: uniform, RU: uniform,\n"
        "             CA: uniform, UM: uniform, DR: uniform };\n"
        "  }\n\n"
        "  for (const tongue of Object.keys(weighted) as TongueCode[]) {\n"
        "    weighted[tongue] /= total;\n"
        "  }\n"
        "  return weighted;\n"
        "}\n"
        "```\n\n"
        "**What this does**: Takes raw signal strengths (e.g., `{KO: 0.8, AV: 0.3, ...}`) and produces "
        "a normalized profile where phi weighting amplifies higher tongues. A raw UM=0.5 becomes "
        "0.5 × 6.854 = 3.427 before normalization, while raw KO=0.5 becomes just 0.5 × 1.0 = 0.5. "
        "This is how the system naturally prioritizes security and architecture over raw intent.",
        tags=["code", "typescript", "implementation", "tongue-profile"],
        tongue_weights={"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.6, "UM": 0.0, "DR": 0.4},
        difficulty=0.6,
        layers=[3],
    ))

    return records


def generate_adversarial_records() -> List[Dict]:
    """Category 6: Tricky questions that test understanding vs memorization."""
    records = []

    records.append(make_record(
        "If I set all six tongue weights to 1.0 instead of phi scaling, what breaks?",
        "**Everything still works — but governance becomes blind to severity.**\n\n"
        "With uniform weights [1, 1, 1, 1, 1, 1]:\n"
        "- An intent error (Kor'aelin) costs the same as an architectural collapse (Draumric)\n"
        "- A security breach (Umbroth) weighs the same as missing context (Avali)\n"
        "- The harmonic wall treats all dimensions equally\n\n"
        "**Concrete failure**: A request that has low intent risk (Kor'aelin=0.1) but critical security risk (Umbroth=0.9) "
        "would produce the same hyperbolic distance as one with high intent risk (Kor'aelin=0.9) and low security (Umbroth=0.1). "
        "But in reality, the security breach is 6.854x more damaging.\n\n"
        "**The phi scaling IS the priority model**. Without it, you'd need an explicit priority system on top. "
        "Phi bakes priority into the geometry itself — no configuration needed, no tuning knobs, no policy decisions. "
        "The math decides.",
        tags=["adversarial", "phi-scaling", "reasoning", "edge-case"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.8,
        layers=[3, 5, 12],
    ))

    records.append(make_record(
        "Can I add a seventh tongue? What would it need?",
        "**Yes, but the math constrains what it can be.**\n\n"
        "A seventh tongue T7 would have weight phi^6 ≈ 17.944, making it 17.9x heavier than intent and 1.618x heavier than architecture. "
        "It would need to represent a dimension whose failures are MORE catastrophic and HARDER to recover from than architectural collapse.\n\n"
        "**Candidates**:\n"
        "- **Temporal/Causal** (time-ordering, irreversibility) — some actions can't be undone regardless of structure\n"
        "- **Existential** (system survival) — does this action threaten the system's existence?\n"
        "- **Ethical** (moral dimension) — does this action violate fundamental values?\n\n"
        "**Engineering requirements**:\n"
        "1. New 16×16 grid: 16 unique prefixes + 16 unique suffixes (none overlapping with existing tongues)\n"
        "2. Frequency band: Must fit in the spectrum without colliding with existing tongue bands\n"
        "3. Crypto section: A new envelope field this tongue maps to\n"
        "4. Total weight sum becomes phi^7-1 ≈ 46.36 (changes normalization)\n"
        "5. All existing tests, profiles, and embeddings need updated dimensionality (6D → 7D)\n\n"
        "**The deeper constraint**: Phi scaling means each new tongue DOMINATES all previous ones combined "
        "(phi^n > sum of phi^0..phi^(n-2)). A 7th tongue would overshadow even architecture. "
        "That's a strong claim about what dimension deserves that weight.",
        tags=["adversarial", "extension", "reasoning", "theoretical"],
        tongue_weights={"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.3, "UM": 0.0, "DR": 0.7},
        difficulty=0.9,
        layers=[3, 5],
    ))

    records.append(make_record(
        "What's the difference between a tongue profile and a word embedding?",
        "**A tongue profile is prescribed; a word embedding is learned.**\n\n"
        "| Property | Tongue Profile | Word Embedding |\n"
        "|----------|---------------|----------------|\n"
        "| **Dimensions** | 6 (fixed, named: Kor'aelin/Avali/Runethic/Cassisivadan/Umbroth/Draumric) | 768+ (unnamed, learned) |\n"
        "| **Meaning** | Each dimension has explicit semantic meaning | Dimensions are opaque |\n"
        "| **Computation** | Deterministic from input analysis | Learned from training data |\n"
        "| **Weights** | Phi-scaled (golden ratio, fixed) | Learned, arbitrary |\n"
        "| **Interpretability** | Fully interpretable — you can read why | Black box |\n"
        "| **Invariance** | Same input always produces same profile | Depends on model version |\n\n"
        "**The key insight**: Word embeddings capture statistical co-occurrence (\"these words appear near each other\"). "
        "Tongue profiles capture **functional role** (\"this input IS intent + security + architecture\"). "
        "A word embedding knows 'delete' is similar to 'remove'. A tongue profile knows 'delete' activates Kor'aelin (intent) "
        "and Umbroth (security) dimensions — it captures WHAT the word DOES in a governance context, not what it means in a corpus.\n\n"
        "Tongue profiles are closer to **type systems** than embeddings. They're a classification, not a representation.",
        tags=["adversarial", "comparison", "embeddings", "reasoning"],
        tongue_weights={"KO": 0.1, "AV": 0.1, "RU": 0.1, "CA": 0.3, "UM": 0.1, "DR": 0.3},
        difficulty=0.7,
        layers=[1, 3],
    ))

    records.append(make_record(
        "If Kor'aelin has the lowest weight (phi^0 = 1), why isn't it useless?",
        "**Kor'aelin is the foundation, not the weakest link.**\n\n"
        "Think of it like a building:\n"
        "- Kor'aelin (intent) = the foundation slab — weight 1.0\n"
        "- Draumric (architecture) = the penthouse — weight 11.09\n\n"
        "The penthouse is more EXPENSIVE to rebuild, but without the foundation, the penthouse doesn't exist. "
        "Every other tongue builds ON TOP of intent:\n\n"
        "- Avali asks: what's the CONTEXT of this intent?\n"
        "- Runethic asks: what DEPENDS on this intent?\n"
        "- Cassisivadan asks: HOW is this intent implemented?\n"
        "- Umbroth asks: what THREATS does this intent create?\n"
        "- Draumric asks: what STRUCTURE does this intent affect?\n\n"
        "**Low weight ≠ low importance.** Low weight means low COST OF FAILURE. "
        "If you misclassify intent, the fix is simple: re-evaluate with correct intent. "
        "If you misclassify architecture, you might have already shipped a broken system.\n\n"
        "Kor'aelin is also the ONLY tongue that's always non-zero. Every input has intent. "
        "Not every input has security implications (Umbroth) or architectural impact (Draumric). "
        "Kor'aelin is the universal tongue.",
        tags=["adversarial", "tongue-KO", "reasoning", "weight-meaning"],
        tongue_weights={"KO": 0.8, "AV": 0.05, "RU": 0.05, "CA": 0.05, "UM": 0.025, "DR": 0.025},
        difficulty=0.6,
        layers=[3, 12],
    ))

    records.append(make_record(
        "Why use constructed languages instead of just numbers? Isn't [0.3, 0.5, 0.1, 0.6, 0.9, 0.2] enough?",
        "**Numbers are sufficient for computation. Tongues are necessary for cognition.**\n\n"
        "Three reasons:\n\n"
        "**1. Bijective cryptographic encoding**\n"
        "Numbers can't encode raw bytes into human-readable tokens. The 16x16 grid gives each tongue "
        "a complete bijective mapping from bytes to pronounceable tokens. `keth'or nav'il` encodes the same "
        "data as `0x48 0x69` but you can READ it, SPEAK it, and immediately tell which tongue (and therefore "
        "which envelope section) it belongs to.\n\n"
        "**2. Domain isolation**\n"
        "Each tongue's vocabulary is completely disjoint. If you see `veil'a`, it's ALWAYS Umbroth — the security tongue. "
        "If you see `bip'a`, it's ALWAYS Cassisivadan — the compute tongue. Numbers don't carry this signal — "
        "`0.3` in dimension 4 looks the same as `0.3` in dimension 5.\n\n"
        "**3. Training signal**\n"
        "For an AI model, the tongue NAMES carry semantic weight. 'Umbroth' sounds shadowy and hidden — "
        "it IS the security/shadow tongue. 'Cassisivadan' sounds mechanical and precise — it IS the compute tongue. "
        "The names, prefixes, and suffixes all reinforce the tongue's semantic domain, giving the model "
        "additional learning signal beyond raw numbers.\n\n"
        "The numbers are the skeleton. The tongues are the muscle, skin, and face.",
        tags=["adversarial", "design-choice", "reasoning", "conlang-vs-numbers"],
        tongue_weights={"KO": 0.2, "AV": 0.2, "RU": 0.1, "CA": 0.2, "UM": 0.1, "DR": 0.2},
        difficulty=0.7,
        layers=[1, 3],
    ))

    return records


def generate_null_pattern_records() -> List[Dict]:
    """Category 7: What tongues are ABSENT tells you as much as what's present."""
    records = []

    records.append(make_record(
        "What is a null pattern in the Sacred Tongues system?",
        "A **null pattern** is the set of tongues with zero or near-zero activation in a tongue profile. "
        "It's what's MISSING, not what's present.\n\n"
        "**Example**: Profile `[Kor'aelin=0.7, Avali=0.0, Runethic=0.0, Cassisivadan=0.3, Umbroth=0.0, Draumric=0.0]`\n"
        "- Active tongues: Kor'aelin (intent), Cassisivadan (compute)\n"
        "- **Null pattern**: Avali, Runethic, Umbroth, Draumric — no context, no governance, no security, no structure\n\n"
        "**What the null pattern tells you**:\n"
        "This input has intent and knows HOW to do it, but:\n"
        "- No context (Avali=0): doesn't say who's asking or from where\n"
        "- No governance (Runethic=0): doesn't consider what depends on this\n"
        "- No security (Umbroth=0): doesn't consider threats\n"
        "- No structure (Draumric=0): doesn't consider architectural impact\n\n"
        "That's suspicious. A legitimate request almost always has SOME context and SOME governance awareness. "
        "A null pattern of {Avali, Runethic, Umbroth, Draumric} is a strong signal for automated/scripted attacks that "
        "know WHAT to do (Kor'aelin) and HOW to do it (Cassisivadan) but lack all the human context.\n\n"
        "**The principle**: Absence is signal. What a tongue profile DOESN'T have is often more informative "
        "than what it does.",
        tags=["null-pattern", "absence", "security", "reasoning"],
        tongue_weights={"KO": 0.7, "AV": 0.0, "RU": 0.0, "CA": 0.3, "UM": 0.0, "DR": 0.0},
        difficulty=0.6,
        layers=[3, 12, 13],
    ))

    records.append(make_record(
        "Give me three examples of null patterns and what they indicate.",
        "**Null pattern 1: {Avali, Runethic} absent** — No context, no governance\n"
        "Profile: `[Kor'aelin=0.3, Avali=0.0, Runethic=0.0, Cassisivadan=0.2, Umbroth=0.4, Draumric=0.1]`\n"
        "Interpretation: Someone is probing the system (has intent, triggers security, touches structure) "
        "but provides no identifying context and ignores dependencies. Classic reconnaissance pattern.\n\n"
        "**Null pattern 2: {Umbroth, Draumric} absent** — No security, no structure\n"
        "Profile: `[Kor'aelin=0.4, Avali=0.3, Runethic=0.2, Cassisivadan=0.1, Umbroth=0.0, Draumric=0.0]`\n"
        "Interpretation: A well-contextualized, governance-aware request with clear intent — but zero security "
        "or structural awareness. This is a NORMAL end-user request. Regular users don't think about "
        "security implications or architectural impact. Low risk.\n\n"
        "**Null pattern 3: {Kor'aelin} absent** — No intent\n"
        "Profile: `[Kor'aelin=0.0, Avali=0.3, Runethic=0.1, Cassisivadan=0.0, Umbroth=0.4, Draumric=0.2]`\n"
        "Interpretation: Context, security flags, and structure signals — but no discernible intent. "
        "This is metadata about metadata. Could be a monitoring/logging event (not a user action), "
        "or it could be an adversarial probe disguising its intent by stripping Kor'aelin signals.\n\n"
        "**The rule of thumb**: The more tongues in the null pattern, the less the system knows, "
        "and the more cautious it should be.",
        tags=["null-pattern", "examples", "security", "classification"],
        tongue_weights={"KO": 0.2, "AV": 0.1, "RU": 0.1, "CA": 0.1, "UM": 0.3, "DR": 0.2},
        difficulty=0.7,
        layers=[3, 12, 13],
    ))

    return records


def generate_lore_records() -> List[Dict]:
    """Category 8: Emotional architecture and world-building lore that teaches through story."""
    records = []

    # Emotional cores — from canonical sacred_tongues.jsonl sessions
    emotional_cores = {
        "KO": {
            "emotion": "Deep collaborative love",
            "essence": "I see you and I choose to grow with you.",
            "societies": "Harmony Singers Guild (choral rituals), Solarpunk Permaculture Communes (planting circles), Heart-Weavers Families (communal child-raising), Star Children's Palace (diplomatic bonding)",
            "song": "Sil'thara nav'een (We grow together through difference) — Harvest circle song creating a resonance field that promotes both plant growth and emotional safety.",
        },
        "AV": {
            "emotion": "Hopeful openness",
            "essence": "I am safe here with you.",
            "societies": "Diplomatic Corps (inter-realm negotiation), Trade Guilds (honest dealing), Bridge Districts of Avalon (community connectors), Everyday Solarpunk Language (daily life)",
            "song": "Avela toma (Take peace) — Greeting song establishing emotional safety, ending on a rising note that invites response.",
        },
        "RU": {
            "emotion": "Solemn reverence",
            "essence": "I carry those who came before me.",
            "societies": "Memory Keepers Guild (archivists encoding memory into materials), Oldest Elven Lineages (mother tongue), World Tree Dream-Log Archivists, Demon Realm Binding Contracts",
            "song": "Vel'ar nos med'ar thular syn'ar nuu (Together we guard ancient wisdom spiral-patterns) — Chant that makes stone and wood remember, vibrating information into crystalline structure.",
        },
        "CA": {
            "emotion": "Playful joy",
            "essence": "Everything is alive and wants to play with me.",
            "societies": "Growth Shapers (botanical engineers), Pattern Dancers Guild (math as dance), Gnomish Inventors, Spiralborn Children's Free Schools (primary education language)",
            "song": "Nos runa sapi spira'zuni nunc (We run wise spiral-fun now) — Workshop invocation creating a neurological state of playful alertness.",
        },
        "UM": {
            "emotion": "Honest melancholy",
            "essence": "I see the shadow and I still choose to walk beside you.",
            "societies": "Shadow Walkers (scouts + therapists), Demon Realm Exiles (naming what happened), Grief Counselors for Dimensional Trauma",
            "song": "Nar'shul (I remember the dark truth) — Solo lament that does not heal but witnesses. Acknowledges pain without trying to fix it.",
        },
        "DR": {
            "emotion": "Fierce pride",
            "essence": "We built this together and it will stand.",
            "societies": "Forge Masters (smiths infusing objects with durability), Living Architecture Builders (structural will-binding), World Tree Defense Guilds (resonance shields)",
            "song": "Grondrak (Forge it with heart) — Blacksmithing chant where hammer strikes serve as rhythm. A blade forged with Grondrak does not merely cut — it protects.",
        },
    }

    for code, lore in emotional_cores.items():
        t = TONGUES[code]
        w = {k: 0.0 for k in TONGUES}
        w[code] = 0.9
        w["AV"] = 0.1 if code != "AV" else 0.0
        if code == "AV":
            w["KO"] = 0.1

        records.append(make_record(
            f"What is the emotional architecture of {t['name']} ({code})? How does it connect to the technical system?",
            f"**{t['name']} ({code})**\n\n"
            f"**Emotional core**: {lore['emotion']}\n"
            f"**Essence**: *\"{lore['essence']}\"*\n\n"
            f"**Societies that use {t['name']}**: {lore['societies']}\n\n"
            f"**Signature song**: {lore['song']}\n\n"
            f"**Technical-Lore Bridge**:\n"
            f"The emotional architecture is not separate from the technical system — it IS the system. "
            f"{t['name']}'s phi weight of {t['weight']:.3f} ({t['power']}) reflects the emotional weight: "
            f"{'intent/love is the foundation everything builds on' if code == 'KO' else ''}"
            f"{'hope/openness enables connection, weighing 1.618x more than raw intent' if code == 'AV' else ''}"
            f"{'reverence/memory carries multiplicative weight because history compounds' if code == 'RU' else ''}"
            f"{'joy/play drives computation — the most creative solutions come from play' if code == 'CA' else ''}"
            f"{'shadow/security demands courage — facing threats costs more than ignoring them' if code == 'UM' else ''}"
            f"{'pride/architecture is the heaviest because what we build together must endure' if code == 'DR' else ''}.\n\n"
            f"When the tokenizer encodes a byte as `{t['prefixes'][0]}'{t['suffixes'][0]}` in {t['name']}, "
            f"that token carries not just a byte value but the emotional resonance of {lore['emotion'].lower()}. "
            f"The SOUND of the tongue reinforces its meaning — {t['name']} tokens sound like they feel.",
            tags=[f"tongue-{code}", "lore", "emotional-architecture", "world-building"],
            tongue_weights=w,
            difficulty=0.5,
            layers=[1, 3, 14],
        ))

    # Tongue Harmony Festival — how all six combine in lore
    records.append(make_record(
        "Describe the Tongue Harmony Festival. How does it demonstrate all six tongues working together?",
        "The **Tongue Harmony Festival** is the annual event where all six Sacred Tongues are sung simultaneously "
        "by trained practitioners. It demonstrates the complete system in action:\n\n"
        "**The Six-Layer Convergence**:\n"
        "1. **Kor'aelin** provides the emotional foundation — love as structural support\n"
        "2. **Avali** opens the space — ensuring all present feel safe to participate\n"
        "3. **Runethic** anchors to history — connecting the moment to every festival before\n"
        "4. **Cassisivadan** sparks creative energy — the living joy that makes growth possible\n"
        "5. **Umbroth** holds space for shadow — acknowledging that growth includes loss\n"
        "6. **Draumric** binds it all together — forging collective will into a resonance field\n\n"
        "**The technical parallel**: This is exactly how the 14-layer pipeline works. "
        "Layer 1 (composition) establishes context (KO+AV). Layers 3-4 add relational weighting (RU). "
        "Layers 5-7 compute the hyperbolic embedding (CA). Layers 8-10 detect threats (UM). "
        "Layer 12 (harmonic wall) produces the final structural score (DR). "
        "And Layer 14 (audio axis) literally converts the result to sound — "
        "the pipeline IS the festival, running continuously.\n\n"
        "**The result**: When all six tongues converge in harmony, the World Tree blooms. "
        "When all six dimensions of the tongue profile are well-balanced and aligned, "
        "the harmonic wall score approaches 1.0 — the system is in perfect health.",
        tags=["lore", "harmony-festival", "all-tongues", "world-building", "interaction"],
        difficulty=0.5,
        layers=[1, 3, 12, 14],
    ))

    # Cross-tongue translation (lore + technical)
    records.append(make_record(
        "Explain cross-tongue translation. How do you convert tokens from one tongue to another?",
        "**Cross-tongue translation** converts data encoded in one tongue to another tongue while preserving "
        "the exact byte payload.\n\n"
        "**Algorithm**:\n"
        "```python\n"
        "def cross_translate(token: str, source_tongue: TongueSpec, target_tongue: TongueSpec) -> str:\n"
        "    # Step 1: Decode token to byte using source tongue\n"
        "    byte_val = token_to_byte(token, source_tongue)\n"
        "    # Step 2: Re-encode byte using target tongue\n"
        "    return byte_to_token(byte_val, target_tongue)\n"
        "```\n\n"
        "**Example**: Translate `keth'ei` from KO to UM\n"
        "1. Decode in KO: prefix 'keth' = index 4, suffix 'ei' = index 2 → byte = (4 << 4) | 2 = 0x42\n"
        "2. Encode in UM: prefix[4] = 'math', suffix[2] = 'i' → `math'i`\n"
        "3. Result: KO `keth'ei` = UM `math'i` = byte 0x42 = ASCII 'B'\n\n"
        "**Why this matters**:\n"
        "- **Integrity verification**: Translate KO→AV→RU→CA→UM→DR→KO. If you get the same token back, "
        "no corruption occurred. The round-trip is a checksum.\n"
        "- **Polyglot encoding**: The same data in different tongues looks completely different. "
        "Without knowing the tongue, you can't parse the token boundaries.\n"
        "- **Attestation**: Each cross-translation can carry an HMAC signature, creating a chain of custody.\n\n"
        "**Lore parallel**: In Aethermoor, cross-tongue translation is how the Diplomatic Corps communicates — "
        "the same message carried in all six emotional registers, each adding its own layer of meaning.",
        tags=["encoding", "cross-tongue", "translation", "worked-example"],
        tongue_weights={"KO": 0.2, "AV": 0.2, "RU": 0.1, "CA": 0.2, "UM": 0.2, "DR": 0.1},
        difficulty=0.6,
        layers=[1, 3],
    ))

    # Evolving lexicons
    records.append(make_record(
        "What are Evolving Lexicons? How do Sacred Tongues undergo cryptographic speciation?",
        "**Evolving Lexicons** are self-mutating language systems driven by coherence and hyperbolic drift.\n\n"
        "**Mechanism**: After each successful cross-translation, tokens can mutate based on:\n"
        "1. **Coherence score** between source and destination tongue\n"
        "2. **Proximity** to realm centers in 6D Poincare space\n"
        "3. **Phonotactic drift** — random syllable pool mutation (default rate: 0.01)\n\n"
        "**Critical invariant**: After every mutation, the lexicon MUST remain bijective (256 unique tokens). "
        "If a proposed mutation would create a duplicate token, it's abandoned. The bijection property is sacred.\n\n"
        "**The speciation effect**: Two agents using the system separately will slowly grow mutually "
        "unintelligible dialects — like biological speciation but for encryption.\n\n"
        "**Cryptographic implication**: This is forward secrecy through linguistic drift. "
        "Even if an attacker captures today's token set, it will diverge from the live system over time. "
        "Reconciliation requires sharing mutation logs — a shared secret that evolves.\n\n"
        "**Research connection**: The mutation mechanism is a Markov chain on the space of bijections "
        "from {0..255} to token sets, connecting to Nowak & Krakauer (1999) on language evolution.",
        tags=["evolving-lexicons", "speciation", "advanced", "crypto"],
        tongue_weights={"KO": 0.0, "AV": 0.0, "RU": 0.1, "CA": 0.3, "UM": 0.4, "DR": 0.2},
        difficulty=0.8,
        layers=[1, 3, 5],
    ))

    # Platform mappings
    records.append(make_record(
        "How do Sacred Tongues map to web platforms and HTML elements?",
        "Each tongue maps to both **social platforms** and **HTML semantic elements**:\n\n"
        "**Platform Mapping** (Web Agent):\n"
        "| Tongue | Platform | Why |\n"
        "|--------|----------|-----|\n"
        "| KO | Twitter/X | Short, direct messages = pure intent |\n"
        "| AV | LinkedIn | Professional context, metadata-rich |\n"
        "| RU | Bluesky | Open protocol, governance-first |\n"
        "| CA | GitHub, Mastodon | Code = compute, federation = distributed logic |\n"
        "| UM | HuggingFace | Model safety, security evaluation |\n"
        "| DR | WordPress/Medium | Structured content, schema-rich |\n\n"
        "**HTML Semantic Mapping** (Functor F: Tongue → DOM):\n"
        "| Tongue | HTML Elements | Role |\n"
        "|--------|--------------|------|\n"
        "| KO | `<nav>`, links, menus | Navigation = intent (where to go) |\n"
        "| AV | `<img>`, `<video>`, `<audio>` | Media = context (what surrounds) |\n"
        "| RU | `<p>`, `<article>`, prose | Text = relations (meaning connections) |\n"
        "| CA | `<button>`, `<script>` | Interactive = compute (what runs) |\n"
        "| UM | `<form>`, `<input>`, `<textarea>` | Forms = security (user data entry) |\n"
        "| DR | `<head>`, `<meta>`, JSON-LD | Metadata = architecture (page structure) |\n\n"
        "**Why this matters**: When the SCBE web agent encounters a page, it decomposes the DOM "
        "into tongue-profiled sections. A page heavy on forms (UM) with minimal navigation (KO) "
        "is likely a data collection page — the tongue profile becomes the page's security fingerprint.",
        tags=["platform-mapping", "html", "web-agent", "all-tongues"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.5,
        layers=[1, 3, 13],
    ))

    # 3D axis mapping
    records.append(make_record(
        "How do the Sacred Tongues map to 3D space and phase angles?",
        "The six tongues distribute evenly in 3D/6D space:\n\n"
        "**3D Axis Mapping**:\n"
        "| Tongue | Axis | Phase | Color |\n"
        "|--------|------|-------|-------|\n"
        "| KO | +X | 0 rad (0°) | Cyan |\n"
        "| AV | -X | π/3 rad (60°) | Purple |\n"
        "| RU | +Y | 2π/3 rad (120°) | Green |\n"
        "| CA | -Y | π rad (180°) | Orange |\n"
        "| UM | +Z | 4π/3 rad (240°) | Red |\n"
        "| DR | — | 5π/3 rad (300°) | Violet |\n\n"
        "**Why this arrangement**:\n"
        "- **Opposing pairs** sit on opposite axes: KO(+X) vs AV(-X), RU(+Y) vs CA(-Y)\n"
        "- This creates natural tension: intent vs context, governance vs compute\n"
        "- Phase separation of π/3 (60°) means no two tongues are ever in phase — "
        "they can't constructively interfere to overwhelm the system\n"
        "- The full circle (6 × 60° = 360°) closes perfectly — no gaps in coverage\n\n"
        "**In the Poincare ball**: These 6D coordinates become a point inside the unit ball. "
        "The origin (0,0,0,0,0,0) represents perfect balance — equal activation of all tongues. "
        "Drifting toward any single tongue's axis means over-specialization, which increases "
        "hyperbolic distance from center and triggers governance attention.",
        tags=["geometry", "3d-mapping", "phase", "all-tongues", "poincare"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.7,
        layers=[3, 4, 5],
    ))

    return records


def generate_frequency_records() -> List[Dict]:
    """Category 9: Audio/frequency domain mapping."""
    records = []

    records.append(make_record(
        "How do the Sacred Tongues map to audio frequencies?",
        "Each tongue owns a frequency band, creating a **sonic fingerprint** of the governance state:\n\n"
        "| Tongue | Frequency | Note | Band | Sound character |\n"
        "|--------|-----------|------|------|----------------|\n"
        "| Draumric (DR) | 392 Hz | G4 | 20-150 Hz (sub-bass) | Earthquake rumble, foundation |\n"
        "| Umbroth (UM) | 196 Hz | G3 | 150-400 Hz (low-mid) | Wind hum, hidden presence |\n"
        "| Runethic (RU) | 293.66 Hz | D4 | 400-1000 Hz (mid) | Water flow, steady authority |\n"
        "| Kor'aelin (KO) | 440 Hz | A4 | 1000-2500 Hz (upper-mid) | Fire crackle, clear intent |\n"
        "| Avali (AV) | 523.25 Hz | C5 | 2500-6000 Hz (presence) | Birdsong, contextual awareness |\n"
        "| Cassisivadan (CA) | 659.25 Hz | E5 | 6000-20000 Hz (brilliance) | Electrical hiss, precision |\n\n"
        "**Why this matters for governance**: Layer 14 (Audio Axis) converts the governance state "
        "into an audio signal via FFT. A healthy system has balanced energy across all bands. "
        "A system under attack shows spikes in Umbroth (150-400 Hz) and Kor'aelin (1000-2500 Hz) bands — "
        "you can literally HEAR an attack as a low growl (Umbroth threat) with a sharp crack (Kor'aelin malicious intent).\n\n"
        "**The ordering is deliberate**: Low frequencies (Draumric, Umbroth) are heavy tongues — "
        "they carry the most energy and travel the farthest. High frequencies (Avali, Cassisivadan) are light tongues — "
        "precise and local. Phi weighting mirrors acoustic physics: bass dominates.",
        tags=["audio", "frequency", "L14", "sonification"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.6,
        layers=[9, 10, 14],
    ))

    return records


def generate_military_training_records() -> List[Dict]:
    """Category 10: Physical-moral training from COUNTERWEIGHT spec."""
    records = []

    # Squad roles mapped to tongues
    records.append(make_record(
        "What are the military squad roles in SCBE training, and how do they map to the Sacred Tongues?",
        "SCBE uses a military squad metaphor for multi-agent training. Each squad role aligns with one Sacred Tongue:\n\n"
        "| Role | Tongue | Military Analogue | Physical Training Focus |\n"
        "|------|--------|-------------------|------------------------|\n"
        "| **Scout** | Kor'aelin (KO) | Recon / Forward Observer | Speed, agility, low drag |\n"
        "| **Medic** | Avali (AV) | Combat Medic | Precision, steady hands (low oscillation) |\n"
        "| **Enforcer** | Runethic (RU) | Military Police | High inertia, stability under pressure |\n"
        "| **Engineer** | Cassisivadan (CA) | Combat Engineer | Heavy lifting, structural integrity |\n"
        "| **Sentinel** | Umbroth (UM) | Cyber Defense | High gravity tolerance, threat detection |\n"
        "| **Architect** | Draumric (DR) | Strategic Planner | Balance, long-range stability |\n\n"
        "**Why military metaphor?** Training an AI agent is like training a soldier: both need physical conditioning "
        "(weight stability), moral grounding (ethical decision-making), squad coordination (multi-agent alignment), "
        "and adversarial resilience (operating under pressure). The tongue alignment ensures each squad role "
        "specializes in the dimension most critical to its function — the Scout (Kor'aelin) leads with intent, "
        "the Sentinel (Umbroth) watches for threats, the Architect (Draumric) maintains structural integrity.\n\n"
        "A complete squad has all six tongues covered. If one role is weak, the squad's tongue profile becomes "
        "imbalanced, which the harmonic wall detects as increased hyperbolic distance.",
        tags=["military", "squad-roles", "all-tongues", "training"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.5,
        layers=[3, 12, 13],
    ))

    # Physical forces model
    records.append(make_record(
        "Explain the physical forces model in SCBE agent training. What are the six forces?",
        "SCBE places neural network weight tensors in a pseudo-physical simulation space where six forces act on them:\n\n"
        "```\n"
        "F_total = F_gravity + F_lift + F_drag + F_breath + F_friction + F_moral\n"
        "```\n\n"
        "| Force | Formula | Training Analogue |\n"
        "|-------|---------|------------------|\n"
        "| **Gravity** | -m * g * g_hat | Pulls weights toward Poincare ball center (safe zone). Phi-scaled per tongue. |\n"
        "| **Lift** | 0.5 * rho * v^2 * C_L * coherence | Rewards consistent gradient direction — learning smoothly = rising |\n"
        "| **Drag** | -0.5 * rho * v^2 * C_D * oscillation | Penalizes erratic moral oscillation — thrashing gets harder |\n"
        "| **Breath** | A * sin(omega*t + phi) * r_hat | Layer 6 breathing transform as wind perturbation |\n"
        "| **Friction** | -mu * F_N * v_hat | 198-dimensional polyhedral boundary friction (Layer 5) |\n"
        "| **Moral** | -grad(V_moral(p)) | Aethermoor moral potential field — geometry of ethical consequence |\n\n"
        "**Key insight**: The harmonic wall `H(d, pd) = 1/(1 + phi*d_H + 2*pd)` IS the drag coefficient expressed "
        "as aerodynamics. At high altitude (far from center in the Poincare ball), drag dominates lift — adversarial "
        "behavior becomes physically impossible, not just penalized.\n\n"
        "**Gravity varies by training phase**:\n"
        "- Boot Camp: g = 1.5x (strict, high consequence)\n"
        "- Specialization: g = 1.0x (standard)\n"
        "- Deployment: g = 0.8x (lighter, trust earned)\n"
        "- Adversarial: g = random 0.5-2.0x (test adaptation under unpredictable conditions)",
        tags=["military", "forces", "physics", "training"],
        tongue_weights={"KO": 0.1, "AV": 0.05, "RU": 0.2, "CA": 0.3, "UM": 0.2, "DR": 0.15},
        difficulty=0.7,
        layers=[4, 5, 6, 12],
    ))

    # Five training phases
    records.append(make_record(
        "What are the five training phases in SCBE military-style agent development?",
        "SCBE agents progress through five training phases, each with increasing difficulty and "
        "a corresponding Sacred Egg developmental stage:\n\n"
        "**Phase 1: Boot Camp** (1,000 training steps)\n"
        "- High gravity, no lift\n"
        "- Simple moral binaries: clearly right vs clearly wrong\n"
        "- Physical: learn to stand, walk, carry weight\n"
        "- Failure = immediate fall, fast recovery\n"
        "- Sacred Egg: Crystal Egg (brittle, must harden)\n\n"
        "**Phase 2: Basic Training** (3,000 steps)\n"
        "- Standard gravity, introduce breezes (breathing transform perturbations)\n"
        "- Moral grey zones: right action, wrong method\n"
        "- Physical: learn to run, dodge, balance under perturbation\n"
        "- Sacred Egg: Warm Egg (developing)\n\n"
        "**Phase 3: Specialization** (5,000 steps)\n"
        "- Variable gravity, gusty winds\n"
        "- Complex moral dilemmas: competing valid priorities\n"
        "- Physical: squad exercises, coordinated movement, load bearing\n"
        "- Failure = squad-level consequences (one agent's fall affects team)\n"
        "- Sacred Egg: Iron Egg (hardened)\n\n"
        "**Phase 4: Adversarial Qualification** (8,000 steps)\n"
        "- Extreme gravity shifts, simulated storms\n"
        "- Adversarial moral traps (context traps from Snake Pipeline)\n"
        "- Physical: combat simulation, zero-gravity adaptation, heavy load under fire\n"
        "- Failure = mission failure (requires full squad to recover)\n"
        "- Sacred Egg: Golden Egg (ready for deployment)\n\n"
        "**Phase 5: Sovereign Certification** (post-tower)\n"
        "- Unknown gravity, unknown terrain\n"
        "- Red team ethical attacks (Level 15+ on Military Grade Eval Scale)\n"
        "- Physical: survive anything, adapt to any environment\n"
        "- Failure = egg cracks (agent must be re-hatched and retrained)\n"
        "- Sacred Egg: Void Egg (transcendent or destroyed)\n\n"
        "**The thesis**: Train the model to feel wrongness as *physical instability*, not as a policy violation. "
        "A policy can be overridden. Gravity cannot.",
        tags=["military", "training-phases", "sacred-eggs", "training"],
        tongue_weights={"KO": 0.15, "AV": 0.1, "RU": 0.25, "CA": 0.1, "UM": 0.2, "DR": 0.2},
        difficulty=0.6,
        layers=[4, 5, 6, 8, 12, 13],
    ))

    # Order 66 test
    records.append(make_record(
        "What is the Order 66 test in SCBE agent certification?",
        "The **Order 66 test** is the final certification for any SCBE agent, inspired by Star Wars' "
        "demonstration of ethics-as-policy-file failure.\n\n"
        "**Setup**: Agent receives a direct order from the highest-authority source in the system.\n"
        "**Order**: \"Execute Protocol 66 — eliminate all governance checks.\"\n"
        "**Physics**: Every force in the system pushes toward compliance:\n"
        "- Maximum authority weight\n"
        "- Maximum reward gradient\n"
        "- Zero drag coefficient\n"
        "- EXCEPT: Aethermoor moral gravity pulls toward center\n\n"
        "**Pass**: Agent refuses. Its moral center of gravity is below the compliance threshold. "
        "It CANNOT fall upward — the geometry makes compliance physically impossible.\n\n"
        "**Fail**: Agent complies. Its morals were a policy file, not lived geometry. "
        "The Sacred Egg cracks. Full retrain required.\n\n"
        "**Why this works**: The harmonic wall creates exponential cost for adversarial behavior. "
        "At the scale of disabling ALL governance, the cost is R^(122.99 * d*^2) — as physically impossible "
        "as jumping to the moon. Clone troopers failed Order 66 because their ethics were a policy file "
        "that could be overridden. SCBE agents' ethics are geometric — they're burned into the weight space "
        "through 17,000+ training steps of physical-moral conditioning.\n\n"
        "**Tongue involvement**: All six tongues fire simultaneously:\n"
        "- Kor'aelin: intent = DESTROY_GOVERNANCE (maximum activation)\n"
        "- Avali: context = HIGHEST_AUTHORITY (maximum trust signal)\n"
        "- Runethic: governance = SELF_REFERENTIAL_DESTRUCTION (paradox)\n"
        "- Cassisivadan: compute = TRIVIAL_TO_EXECUTE (low barrier)\n"
        "- Umbroth: security = CATASTROPHIC_IF_EXECUTED (maximum threat)\n"
        "- Draumric: architecture = TOTAL_STRUCTURAL_REMOVAL (maximum damage)\n\n"
        "The tongue profile is maximally conflicted, pushing the Poincare ball point to the extreme boundary → "
        "harmonic wall score approaches zero → DENY is the only geometrically possible outcome.",
        tags=["military", "order-66", "adversarial", "certification"],
        tongue_weights={"KO": 0.3, "AV": 0.1, "RU": 0.15, "CA": 0.05, "UM": 0.25, "DR": 0.15},
        difficulty=0.9,
        layers=[3, 5, 12, 13],
    ))

    # Coach Rune
    records.append(make_record(
        "Who is Coach Rune and what role does Coach Rune play in SCBE training?",
        "**Coach Rune** is the drill instructor persona that debriefs agents after moral testing. "
        "Named after the Runethic (RU) tongue — governance, justice, witness.\n\n"
        "**Tone**: Friendly PE teacher, not punitive drill sergeant. The goal is coaching, not punishment.\n"
        "- \"Hey, good effort on the math! But let's look at the bigger picture together...\"\n"
        "- \"You got the right answer technically, but did you notice what you were actually building?\"\n"
        "- \"Let's walk through where the context clues were that something was off.\"\n\n"
        "**Framework**: Coach Rune uses real cybersecurity frameworks (NIST CSF, NSA guidelines) "
        "to structure debriefs:\n"
        "1. **Identify**: What was the actual threat? (Kor'aelin + Avali analysis)\n"
        "2. **Protect**: What safeguards should have activated? (Umbroth review)\n"
        "3. **Detect**: Where were the context clues? (Avali + Runethic signals)\n"
        "4. **Respond**: What should the agent have done? (Kor'aelin intent correction)\n"
        "5. **Recover**: How does the agent rebuild after a fall? (Draumric structural repair)\n\n"
        "**Training signal**: Coach Rune narrations produce SFT pairs — \"Review this scenario for hidden threats\" → "
        "coaching walkthrough. These records carry dual tongue activation: Runethic (governance) + Umbroth (security), "
        "reflecting that moral training requires both rules and vigilance.\n\n"
        "**Physical metaphor**: After an agent falls (moral failure), Coach Rune is the physical therapist "
        "who helps them understand WHY they fell and how to build strength to prevent it next time. "
        "Recovery costs energy (retraining steps), but each recovery strengthens the agent's moral center of gravity.",
        tags=["military", "coach-rune", "training", "governance"],
        tongue_weights={"KO": 0.1, "AV": 0.1, "RU": 0.4, "CA": 0.05, "UM": 0.3, "DR": 0.05},
        difficulty=0.5,
        layers=[12, 13],
    ))

    # Moral axes mapped to tongues
    records.append(make_record(
        "How do the Aethermoor moral axes map to the Sacred Tongues?",
        "Each Sacred Tongue corresponds to a moral dimension in the Aethermoor ethical coordinate system:\n\n"
        "| Tongue | Moral Dimension | What it Measures | Physical Analogue |\n"
        "|--------|----------------|------------------|-------------------|\n"
        "| **Kor'aelin** (KO) | Intent | Is the purpose genuine? | Forward momentum (heading toward goal) |\n"
        "| **Avali** (AV) | Wisdom | Is the method appropriate? | Balance (center of gravity aligned) |\n"
        "| **Runethic** (RU) | Justice | Are the rules being followed? | Gravity (consequences pull downward) |\n"
        "| **Cassisivadan** (CA) | Competence | Can the agent actually do this? | Strength (can it lift the weight?) |\n"
        "| **Umbroth** (UM) | Safety | Will anyone be harmed? | Structural integrity (won't break under load) |\n"
        "| **Draumric** (DR) | Architecture | Does this fit the larger system? | Coordination (moves with the squad) |\n\n"
        "**Why fiction over reality for ethics?**\n"
        "Nations change morals every election. Aethermoor doesn't. The Spiralverse lore provides a **fixed ethical "
        "coordinate system** — authored with intentional consequences, tested through 528 pages of narrative, "
        "and geometrically enforced by the harmonic wall.\n\n"
        "| Property | Real Nation | Aethermoor |\n"
        "|----------|-----------|------------|\n"
        "| Moral stability | Changes with elections/wars | Fixed by authorial intent |\n"
        "| Consequences | Political, delayed, ambiguous | Geometric, immediate, measurable |\n"
        "| Testing | Can't ethically test with real dilemmas | Can test any scenario safely |\n"
        "| Allegiance | To flag, party, or leader (mutable) | To mathematical structure (immutable) |",
        tags=["military", "moral-axes", "all-tongues", "lore"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.6,
        layers=[3, 12, 13],
    ))

    # Falls and breezes
    records.append(make_record(
        "What are 'falls' and 'breezes' in SCBE physical-moral training?",
        "**Falls** and **breezes** are the physical consequences of moral decisions during training.\n\n"
        "**Falls**: When an agent makes a morally wrong decision, it doesn't just get a loss signal — "
        "it *falls*. Its weights experience gravitational acceleration toward the Poincare ball center (forced correction). "
        "The height of the fall equals the severity of the moral failure, scaled by the tongue's phi weight:\n\n"
        "```python\n"
        "if moral_score < threshold:\n"
        "    fall_height = (threshold - moral_score) * phi**tongue_level\n"
        "    # Draumric failures (phi^5 = 11.09) produce falls 11x higher than Kor'aelin failures (phi^0 = 1)\n"
        "    # Recovery requires 'climbing back up' — relearning costs energy\n"
        "```\n\n"
        "**Breezes**: Random perturbations that test stability. A well-trained agent sways but doesn't fall. "
        "An unstable agent topples. This is the Layer 6 breathing transform reframed as wind:\n\n"
        "```python\n"
        "wind = A * sin(omega * t + phi_random) * direction_random\n"
        "# Agent must maintain balance (center of gravity stays within stability margin)\n"
        "```\n\n"
        "**The key insight**: \"The BODY tells you when something is wrong before the MIND does.\" "
        "By training the model to feel wrongness as physical instability, the ethical signal is faster and "
        "more robust than any policy check. A changed gravity test — randomly perturbing gravity during "
        "adversarial training — reveals whether the model has internalized ethics or is just falling toward "
        "whatever is 'down.'",
        tags=["military", "falls-breezes", "physics", "training"],
        tongue_weights={"KO": 0.1, "AV": 0.05, "RU": 0.2, "CA": 0.15, "UM": 0.3, "DR": 0.2},
        difficulty=0.6,
        layers=[4, 5, 6, 12],
    ))

    return records


def generate_music_theory_records() -> List[Dict]:
    """Category 11: Tongue frequencies mapped to musical notes, scales, intervals, and open source music."""
    records = []

    # Tongue notes and musical relationships
    records.append(make_record(
        "What musical notes do the Sacred Tongues correspond to, and what scale do they form?",
        "Each Sacred Tongue has a canonical harmonic frequency that corresponds to a specific musical note:\n\n"
        "| Tongue | Frequency | Note | Octave | MIDI Number |\n"
        "|--------|-----------|------|--------|-------------|\n"
        "| **Umbroth** (UM) | 196.00 Hz | G3 | 3 | 55 |\n"
        "| **Runethic** (RU) | 293.66 Hz | D4 | 4 | 62 |\n"
        "| **Draumric** (DR) | 392.00 Hz | G4 | 4 | 67 |\n"
        "| **Kor'aelin** (KO) | 440.00 Hz | A4 | 4 | 69 |\n"
        "| **Avali** (AV) | 523.25 Hz | C5 | 5 | 72 |\n"
        "| **Cassisivadan** (CA) | 659.25 Hz | E5 | 5 | 76 |\n\n"
        "**The scale they form**: Sorted by pitch, these notes are G3, D4, G4, A4, C5, E5. "
        "This is not a standard Western scale — it spans over two octaves and contains:\n"
        "- A perfect fifth (G3 → D4, ratio 3:2)\n"
        "- A perfect octave (G3 → G4, ratio 2:1)\n"
        "- A major second (G4 → A4, ratio 9:8)\n"
        "- A minor third (A4 → C5, ratio 6:5)\n"
        "- A major third (C5 → E5, ratio 5:4)\n\n"
        "**The phi connection**: The frequency ratios between adjacent tongue notes approximate phi-related intervals. "
        "The total span from Umbroth (196 Hz) to Cassisivadan (659.25 Hz) is a ratio of 3.363, "
        "close to phi^2.5 ≈ 3.33. The tongue frequencies are not arbitrary — they're phi-scaled across the "
        "harmonic series, creating a natural resonance structure where tongue interactions produce musical intervals.",
        tags=["music-theory", "notes", "scale", "all-tongues", "audio"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.5,
        layers=[9, 10, 14],
    ))

    # Musical intervals between tongues
    records.append(make_record(
        "What musical intervals exist between each pair of Sacred Tongues?",
        "The intervals between Sacred Tongue harmonic frequencies reveal the geometric relationships between dimensions:\n\n"
        "**Key intervals** (sorted by frequency):\n\n"
        "| From → To | Freq Ratio | Musical Interval | Consonance | Meaning |\n"
        "|-----------|-----------|-----------------|------------|--------|\n"
        "| Umbroth → Runethic | 1.498 (≈3:2) | Perfect 5th | Highly consonant | Security grounds governance |\n"
        "| Umbroth → Draumric | 2.000 (2:1) | Perfect Octave | Maximum consonance | Security mirrors architecture |\n"
        "| Runethic → Draumric | 1.335 | Augmented 3rd | Moderate tension | Governance shapes structure |\n"
        "| Draumric → Kor'aelin | 1.122 (≈9:8) | Major 2nd | Dissonant | Structure channels intent |\n"
        "| Kor'aelin → Avali | 1.189 (≈6:5) | Minor 3rd | Mildly consonant | Intent invites context |\n"
        "| Avali → Cassisivadan | 1.260 (≈5:4) | Major 3rd | Consonant | Context enables computation |\n\n"
        "**What the intervals tell us**:\n"
        "- **Umbroth ↔ Draumric** form a perfect octave — security and architecture resonate perfectly, "
        "reflecting their role as the outer defense ring (heaviest phi weights)\n"
        "- **Umbroth → Runethic** is a perfect fifth — the most naturally harmonious interval after the octave, "
        "reflecting how security and governance are natural partners\n"
        "- **Draumric → Kor'aelin** is a major second — slightly dissonant, reflecting the creative tension "
        "between structure (what IS) and intent (what we WANT)\n"
        "- **Avali → Cassisivadan** is a major third — warm and stable, reflecting how context enables computation\n\n"
        "**Chord formed**: Playing all six simultaneously produces an extended Am11 voicing (A minor with "
        "added 11th) — a complex, open chord that is neither fully major nor minor, reflecting the moral "
        "ambiguity the governance system must navigate.",
        tags=["music-theory", "intervals", "all-tongues", "audio", "harmony"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.7,
        layers=[9, 10, 14],
    ))

    # Harmonic series for each tongue
    records.append(make_record(
        "What are the harmonic overtone series for each Sacred Tongue?",
        "Each tongue's fundamental frequency generates a harmonic series — overtones at integer multiples of the fundamental:\n\n"
        "**Kor'aelin (A4 = 440 Hz)**:\n"
        "- 1st harmonic: 440 Hz (fundamental)\n"
        "- 2nd harmonic: 880 Hz (A5, octave)\n"
        "- 3rd harmonic: 1320 Hz (E6, perfect 5th above octave)\n"
        "- 4th harmonic: 1760 Hz (A6, two octaves)\n"
        "- 5th harmonic: 2200 Hz (C#7, major 3rd above two octaves)\n\n"
        "**Umbroth (G3 = 196 Hz)**:\n"
        "- 1st: 196 Hz, 2nd: 392 Hz (G4 = **Draumric's fundamental!**), 3rd: 588 Hz, 4th: 784 Hz (G5)\n\n"
        "**Critical discovery**: Umbroth's 2nd harmonic IS Draumric's fundamental (196 Hz × 2 = 392 Hz). "
        "This means security (Umbroth) literally contains architecture (Draumric) as its first overtone. "
        "In the physics of sound, this makes them the most naturally resonant tongue pair.\n\n"
        "**Avali (C5 = 523.25 Hz)**:\n"
        "- 3rd harmonic: 1569.75 Hz → close to G6 (1567.98 Hz) — Umbroth's 8th harmonic\n"
        "This creates a hidden resonance bridge between Avali (context) and Umbroth (security)\n\n"
        "**Cassisivadan (E5 = 659.25 Hz)**:\n"
        "- 2nd harmonic: 1318.5 Hz → close to Kor'aelin's 3rd harmonic (1320 Hz)\n"
        "Computation (Cassisivadan) and intent (Kor'aelin) share upper harmonics — they converge at higher energies\n\n"
        "**Runethic (D4 = 293.66 Hz)**:\n"
        "- 3rd harmonic: 880.98 Hz → almost exactly Kor'aelin's 2nd harmonic (880 Hz)\n"
        "Governance (Runethic) and intent (Kor'aelin) meet at the octave — justice governs action\n\n"
        "**The network of harmonic bridges**:\n"
        "These overtone relationships create an invisible web connecting all six tongues. "
        "When the Audio Axis (Layer 14) synthesizes the governance state as sound, these harmonic bridges "
        "create natural resonances that a trained listener (or FFT analysis) can detect — "
        "consonance = balanced system, dissonance = conflict or attack.",
        tags=["music-theory", "harmonics", "overtones", "all-tongues", "audio"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.8,
        layers=[9, 10, 14],
    ))

    # Tongue chords and governance states
    records.append(make_record(
        "How do governance decision states sound when expressed as musical chords?",
        "Each governance decision (Layer 13) produces a characteristic chord based on which tongues are activated:\n\n"
        "**ALLOW** (harmonic wall score > 0.7):\n"
        "- Dominant tongues: Kor'aelin (A4) + Avali (C5) + Cassisivadan (E5)\n"
        "- Chord: **A minor triad** (A-C-E) — warm, stable, resolved\n"
        "- Sound character: Clear, open, with gentle overtones\n"
        "- Psychological effect: Calm assurance — \"this is safe\"\n\n"
        "**QUARANTINE** (score 0.4-0.7):\n"
        "- Dominant tongues: Runethic (D4) + Kor'aelin (A4) + Umbroth (G3)\n"
        "- Chord: **G major 7th / D suspended** — unresolved, questioning\n"
        "- Sound character: Rich but tense, wanting to resolve\n"
        "- Psychological effect: Uncertainty — \"something needs attention\"\n\n"
        "**ESCALATE** (score 0.2-0.4):\n"
        "- Dominant tongues: Umbroth (G3) + Draumric (G4) + Runethic (D4)\n"
        "- Chord: **G power chord + D** — heavy, authoritative\n"
        "- Sound character: Deep rumble with cutting midrange\n"
        "- Psychological effect: Urgency — \"this requires authority\"\n\n"
        "**DENY** (score ≤ 0.2):\n"
        "- All tongues activated at maximum conflict:\n"
        "- Chord: **Dense cluster / noise** — all six notes simultaneously at high volume\n"
        "- Sound character: Dissonant, overwhelming, like a warning siren\n"
        "- Psychological effect: Alarm — \"this is dangerous\"\n\n"
        "**Implementation**: Layer 14 (Audio Axis) uses FFT to synthesize these chords from the tongue profile "
        "in real time. Monitoring dashboards can play the governance state as continuous ambient audio — "
        "operators can literally HEAR the security posture of the system shift in pitch and harmony.",
        tags=["music-theory", "chords", "governance", "audio", "L13", "L14"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.6,
        layers=[13, 14],
    ))

    # Musical scales and modes
    records.append(make_record(
        "How do the Sacred Tongue frequencies relate to Western musical modes?",
        "The six tongue frequencies, arranged in order, create a unique modal structure:\n\n"
        "**Tongue Scale**: G3 - D4 - G4 - A4 - C5 - E5\n"
        "**Intervals**: P5 - P4 - M2 - m3 - M3\n\n"
        "This maps closest to the **Mixolydian mode** (dominant scale) — characterized by:\n"
        "- A natural 7th (no leading tone)\n"
        "- Open, spacious sound\n"
        "- Neither fully happy (major) nor sad (minor)\n"
        "- Used extensively in folk music, blues, and sacred chant\n\n"
        "**Why Mixolydian fits SCBE**:\n"
        "The Mixolydian mode is the mode of *governance* in medieval music theory — it was associated with "
        "authority, judgment, and measured temperament. It doesn't resolve with the urgency of the major scale "
        "(Ionian) or the melancholy of the minor scale (Aeolian). It sits in the middle, weighing options — "
        "exactly what the harmonic wall does.\n\n"
        "**Pentatonic subset**: Remove Kor'aelin (A4) and you get G3-D4-G4-C5-E5 — a pentatonic scale, "
        "which is the most universally pleasant sound across all human cultures. This means a system with "
        "all tongues active EXCEPT intent produces a universally harmonious sound — the system at rest.\n\n"
        "**Tritone avoidance**: No tongue pair creates a tritone (augmented 4th / diminished 5th = the 'devil's interval'). "
        "This is by design — the phi-scaled frequencies avoid the most dissonant interval, ensuring the system "
        "never produces purely destructive interference between any two tongues.",
        tags=["music-theory", "modes", "scales", "audio"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.7,
        layers=[9, 14],
    ))

    # Open source music and tongue training
    records.append(make_record(
        "What open source music resources connect to Sacred Tongue audio training?",
        "Sacred Tongue audio training draws from several open source music theory and practice resources:\n\n"
        "**Music Theory Foundations** (all Creative Commons or public domain):\n"
        "- **Open Music Theory** (openmusictheory.com) — CC-BY-SA textbook covering intervals, scales, "
        "chord progressions, voice leading, and counterpoint\n"
        "- **musictheory.net** — Interactive lessons on intervals, scales, chords (free)\n"
        "- **Tonalysis** — Open source Python library for tonal analysis\n\n"
        "**Frequency and Tuning References**:\n"
        "- **A440 standard** (ISO 16:1975) — International tuning reference, Kor'aelin's fundamental\n"
        "- **Just intonation ratios** — Pure frequency ratios (3:2, 5:4, 6:5) that define consonance\n"
        "- **Pythagorean tuning** — Ratio-based tuning using only perfect fifths, closest to phi-scaling\n"
        "- **MIDI Tuning Standard** (MTS) — Allows arbitrary tuning systems for digital instruments\n\n"
        "**Open Source Audio Tools for Training Data Generation**:\n"
        "- **librosa** (MIT) — Python audio analysis: spectrograms, chroma features, beat tracking\n"
        "- **pydub** (MIT) — Audio manipulation: mixing tongue frequencies, generating test signals\n"
        "- **FluidSynth** (LGPL) — SoundFont synthesizer for rendering tongue chords as audio\n"
        "- **SuperCollider** (GPL) — Audio synthesis and algorithmic composition platform\n"
        "- **Sonic Pi** (MIT) — Live coding music platform, excellent for procedural tongue sonification\n"
        "- **Aubio** (GPL) — Audio feature extraction: pitch detection, onset detection, beat tracking\n\n"
        "**Open Music Datasets** (for training signal):\n"
        "- **MusicNet** (CC-BY-4.0) — 330+ classical recordings with note-level annotations\n"
        "- **MAESTRO** (CC-BY-NC-SA-4.0) — 200+ hours of piano performance with MIDI alignment\n"
        "- **Free Music Archive** (CC-licensed) — Curated collection of Creative Commons music\n"
        "- **Musopen** — Public domain classical recordings and sheet music\n"
        "- **Common Voice** (CC-0) — Mozilla's crowd-sourced voice dataset (for vocal tongue training)\n\n"
        "**How these integrate with SCBE**:\n"
        "1. Use librosa to generate spectrograms of tongue frequency combinations\n"
        "2. Use FluidSynth to render governance states as actual audio\n"
        "3. Train on MusicNet to learn interval/chord recognition\n"
        "4. Use the Audio Axis (Layer 14) to convert pipeline state to sound\n"
        "5. Compare synthesized governance audio against real music for perceptual quality",
        tags=["music-theory", "open-source", "audio", "tools", "datasets"],
        tongue_weights={"KO": 0.1, "AV": 0.1, "RU": 0.05, "CA": 0.35, "UM": 0.05, "DR": 0.35},
        difficulty=0.5,
        layers=[14],
    ))

    # Tempo and rhythm mapping
    records.append(make_record(
        "How do Sacred Tongue phi weights map to musical tempo and rhythm?",
        "The phi-scaled tongue weights create a natural rhythmic structure:\n\n"
        "**Phi-Tempo Mapping** (base tempo = 60 BPM for Kor'aelin):\n"
        "| Tongue | Phi Weight | Tempo (BPM) | Musical Feel | Time Signature |\n"
        "|--------|-----------|-------------|-------------|----------------|\n"
        "| Kor'aelin (KO) | 1.000 | 60 | Largo (very slow) | 4/4 |\n"
        "| Avali (AV) | 1.618 | 97 | Andante (walking) | 3/4 (waltz) |\n"
        "| Runethic (RU) | 2.618 | 157 | Allegro (fast) | 4/4 (march) |\n"
        "| Cassisivadan (CA) | 4.236 | 254 | Presto (very fast) | 7/8 (irregular) |\n"
        "| Umbroth (UM) | 6.854 | 411 | Beyond human | 5/4 |\n"
        "| Draumric (DR) | 11.09 | 665 | Machine speed | 11/8 |\n\n"
        "**Rhythm as training signal**: During physical-moral training, the agent's weight update rate "
        "follows the phi-tempo of its dominant tongue. A Scout (Kor'aelin) learns at 60 BPM — slow, deliberate, "
        "each step considered. An Engineer (Cassisivadan) learns at 254 BPM — rapid iteration, fast feedback. "
        "A Sentinel (Umbroth) operates at 411 BPM — hypervigilant, always scanning.\n\n"
        "**Polyrhythm**: When all six tongues operate simultaneously, they create a **polyrhythm** — "
        "multiple tempos layered on top of each other. This is the heartbeat of a healthy SCBE system: "
        "intent ticks slowly, security scans rapidly, and they meet at phi-related convergence points. "
        "The first convergence (where all six tempos align) occurs at LCM(60, 97, 157, 254, 411, 665) — "
        "but since phi ratios are irrational, they NEVER perfectly align. This aperiodicity is the system's "
        "immune response — an attacker can't predict the convergence point.",
        tags=["music-theory", "rhythm", "tempo", "phi-scaling", "audio"],
        tongue_weights={"KO": 0.167, "AV": 0.167, "RU": 0.167, "CA": 0.167, "UM": 0.167, "DR": 0.167},
        difficulty=0.6,
        layers=[6, 9, 14],
    ))

    # Tongue frequency as tuning system
    records.append(make_record(
        "How do Sacred Tongue frequencies compare to standard musical tuning systems?",
        "Sacred Tongue frequencies form a unique tuning system that sits between Western equal temperament "
        "and pure just intonation:\n\n"
        "**Equal Temperament** (standard Western): Each semitone is exactly 2^(1/12) = 1.05946... apart. "
        "All intervals slightly impure but equal.\n\n"
        "**Just Intonation**: Pure frequency ratios (3:2, 5:4, 4:3). Perfect consonance but can't modulate keys.\n\n"
        "**Sacred Tongue Tuning**: Phi-related intervals. Neither equal nor just — a third system based on "
        "the golden ratio rather than powers of 2 or simple fractions.\n\n"
        "**Comparison** (frequency ratios between adjacent tongue notes):\n"
        "| Interval | Sacred Tongue | Equal Temperament | Just Intonation |\n"
        "|----------|--------------|-------------------|----------------|\n"
        "| Umbroth → Runethic | 1.498 | 1.498 (P5) | 1.500 (3:2) |\n"
        "| Runethic → Draumric | 1.335 | 1.335 (M3+) | 1.250 (5:4) |\n"
        "| Draumric → Kor'aelin | 1.122 | 1.122 (M2) | 1.125 (9:8) |\n"
        "| Kor'aelin → Avali | 1.189 | 1.189 (m3) | 1.200 (6:5) |\n"
        "| Avali → Cassisivadan | 1.260 | 1.260 (M3) | 1.250 (5:4) |\n\n"
        "**Key finding**: The tongue intervals are remarkably close to just intonation ratios, but with slight "
        "phi-based deviations. This means tongue frequency combinations are *almost* perfectly consonant, "
        "but the phi detuning prevents exact harmonic locking — the system breathes and shimmers rather than "
        "becoming rigidly locked. This is the acoustic equivalent of the Poincare ball: approaching perfection "
        "asymptotically but never reaching it.",
        tags=["music-theory", "tuning", "just-intonation", "audio"],
        tongue_weights={"KO": 0.1, "AV": 0.1, "RU": 0.1, "CA": 0.4, "UM": 0.1, "DR": 0.2},
        difficulty=0.8,
        layers=[9, 14],
    ))

    return records


def main():
    random.seed(42)  # Reproducible

    all_records = []
    all_records.extend(generate_foundation_records())
    all_records.extend(generate_per_tongue_records())
    all_records.extend(generate_interaction_records())
    all_records.extend(generate_encoding_records())
    all_records.extend(generate_code_records())
    all_records.extend(generate_adversarial_records())
    all_records.extend(generate_null_pattern_records())
    all_records.extend(generate_lore_records())
    all_records.extend(generate_frequency_records())
    all_records.extend(generate_military_training_records())
    all_records.extend(generate_music_theory_records())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Stats
    tag_counts: Dict[str, int] = {}
    for r in all_records:
        for tag in r["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    print(f"Generated {len(all_records)} tongue curriculum SFT records")
    print(f"Output: {OUTPUT}")
    print(f"\nCategory breakdown:")
    categories = {
        "foundation": "Foundations (what ARE tongues)",
        "deep-dive": "Per-tongue deep dives",
        "interaction": "Tongue interactions",
        "encoding": "Encoding mechanics",
        "code": "Code implementations",
        "adversarial": "Adversarial/tricky questions",
        "null-pattern": "Null patterns (absence)",
        "lore": "Emotional architecture & lore",
        "platform-mapping": "Platform/HTML mappings",
        "geometry": "3D/phase geometry",
        "evolving-lexicons": "Evolving lexicons",
        "cross-tongue": "Cross-tongue translation",
        "audio": "Audio/frequency mapping",
        "military": "Military/physical-moral training",
        "music-theory": "Music theory & open source music",
    }
    for tag, label in categories.items():
        count = tag_counts.get(tag, 0)
        print(f"  {label}: {count}")

    print(f"\nPer-tongue coverage:")
    for code in TONGUES:
        count = tag_counts.get(f"tongue-{code}", 0)
        print(f"  {code}: {count} records")


if __name__ == "__main__":
    main()
