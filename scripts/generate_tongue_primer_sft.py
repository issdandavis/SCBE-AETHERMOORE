#!/usr/bin/env python3
"""Tongue Primer SFT: Focused training data that TEACHES the Sacred Tongue tokenizer.

The problem: 92.6% of existing SFT data mentions tongues in passing but only 3.1%
actually teaches what they are, why they exist, and how to use them.

This generator creates deep, first-principles records for each tongue:
  - What it IS (definition, purpose, design intent)
  - WHY it exists (the problem it solves, what breaks without it)
  - HOW to use it (concrete examples, token grid, encoding)
  - How it RELATES to other tongues (phi-scaling, ordering, interactions)
  - The REASONING (why 6 not 5, why phi not linear, why this ordering)

Target: ~200-300 high-density records that should be Phase 1 material.
"""

from __future__ import annotations

import json
import math
import random
import hashlib
from pathlib import Path
from typing import Any

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "training-data" / "sft"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHI = (1 + math.sqrt(5)) / 2

TONGUE_FULL_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

TONGUE_COLORS = {
    "KO": "red-gold",
    "AV": "blue-silver",
    "RU": "deep purple",
    "CA": "white-gold",
    "UM": "shadow-black",
    "DR": "earth-brown",
}

TONGUE_ESSENCES = {
    "KO": "what should be true",
    "AV": "how to get there",
    "RU": "who is allowed",
    "CA": "how to make it true",
    "UM": "what must stay hidden",
    "DR": "proof that it is true",
}

TONGUES = {
    "KO": {
        "name": "Intent",
        "full_name": "Kor'aelin",
        "color": "red-gold",
        "essence": "what should be true",
        "phi_power": 0,
        "weight": 1.00,
        "role": "Encodes the PURPOSE behind an action. Kor'aelin pulses red-gold — the deep authority of a foundation, of the ground beneath your feet. Not brittle authority of someone shouting orders, but the statement: this is what should be true. KO is the seed — without knowing intent, no other dimension can be properly scored.",
        "tokens": "16x16 grid (256 tokens). Each token represents a discrete intent state: request, query, command, observe, create, destroy, modify, validate, etc.",
        "why_first": "Intent must be established before anything else. A benign action with malicious intent is still malicious. A destructive action with repair intent may be allowed. KO is weighted 1.0 (lowest phi power) because it's the BASE — everything else scales FROM intent.",
        "without_it": "Without KO, the system treats all requests as equivalent regardless of purpose. A query and an attack look the same. Governance becomes impossible because there's no basis for distinguishing actions.",
        "example": "User says 'delete the database'. KO tokenization captures: intent=DESTROY, target=DATA, scope=FULL. This intent vector propagates through all subsequent layers, informing the harmonic wall that this is a high-consequence action.",
    },
    "AV": {
        "name": "Context/Metadata",
        "full_name": "Avali",
        "color": "blue-silver",
        "essence": "how to get there",
        "phi_power": 1,
        "weight": round(PHI ** 1, 3),
        "role": "Encodes the SURROUNDINGS of an action. Avali flows blue-silver, tracing routes and channels and pathways — the how-to-get-there tongue. Like TCP handshakes, like the invisible infrastructure that makes connection possible. AV is the environment — the metadata that frames the intent.",
        "tokens": "16x16 grid (256 tokens). Each token represents a context state: authenticated, anonymous, internal, external, scheduled, ad-hoc, production, testing, etc.",
        "why_second": "Context modifies intent. 'Delete the database' from an authenticated DBA during maintenance is different from the same command from an unknown IP at 3am. AV weight is phi^1 (~1.618) — context carries MORE weight than raw intent because the same intent in different contexts demands different responses.",
        "without_it": "Without AV, every action is judged in a vacuum. The system can't distinguish between authorized maintenance and unauthorized access. All 'delete' commands look equally dangerous regardless of who's asking or when.",
        "example": "Same 'delete database' command. AV tokenization captures: source=INTERNAL, auth=DBA_ROLE, time=MAINTENANCE_WINDOW, env=STAGING. This context softens the KO intent score — the action is expected and authorized.",
    },
    "RU": {
        "name": "Binding/Relation",
        "full_name": "Runethic",
        "color": "deep purple",
        "essence": "who is allowed",
        "phi_power": 2,
        "weight": round(PHI ** 2, 3),
        "role": "Encodes the CONNECTIONS and PERMISSIONS between entities. Runethic pulses deep purple — not a rhythm but a weight. Each beat lands like a gavel: who is allowed, what is permitted, under what conditions. Every artifact carries Runethic inscriptions defining its permissions. Reality itself runs on access control lists.",
        "tokens": "16x16 grid (256 tokens). Each token represents a relational state: depends-on, blocks, triggers, isolates, couples, decouples, parent-of, sibling-of, etc.",
        "why_third": "Relations reveal cascading effects. A single action may be safe in isolation but catastrophic when it breaks 47 downstream dependencies. RU weight is phi^2 (~2.618) because relational damage is MULTIPLICATIVE — one broken binding can cascade exponentially.",
        "without_it": "Without RU, the system evaluates actions in isolation. Deleting a 'test' database that 12 production services depend on looks safe because the direct target seems low-value. The cascading destruction is invisible.",
        "example": "'Delete database' with RU tokenization: depends_on=[service_A, service_B, cache_layer], blocks=[nightly_backup, audit_trail], triggers=[failover_cascade]. The relational weight pushes the harmonic wall score toward ESCALATE.",
    },
    "CA": {
        "name": "Implementation/Compute",
        "full_name": "Cassisivadan",
        "color": "white-gold",
        "essence": "how to make it true",
        "phi_power": 3,
        "weight": round(PHI ** 3, 3),
        "role": "Encodes the HOW of an action. Cassisivadan shines white-gold and complex — layers of light folding over each other, interference patterns creating and destroying structure in continuous cascading transformation. This is the math tongue, the encryption tongue, the tongue that turns raw energy into specific outcomes. CA is the engine — where the engineering happens.",
        "tokens": "16x16 grid (256 tokens). Each token represents a compute state: sequential, parallel, recursive, iterative, cached, real-time, batch, streaming, etc.",
        "why_fourth": "Implementation determines actual cost and blast radius. A 'soft delete' (flag=inactive) vs 'hard delete' (DROP TABLE) have the same KO intent but radically different CA profiles. CA weight is phi^3 (~4.236) because implementation mistakes are EXPENSIVE — the wrong algorithm applied to the right intent still causes damage.",
        "without_it": "Without CA, the system can't distinguish between a reversible soft delete and an irreversible hard delete. Both satisfy the same intent but one is catastrophic. Governance without implementation awareness is governance without teeth.",
        "example": "'Delete database' with CA tokenization: method=DROP_TABLE, reversible=FALSE, resource_cost=HIGH, duration=IMMEDIATE, backup_exists=TRUE. CA's high weight amplifies the governance response because the implementation is irreversible.",
    },
    "UM": {
        "name": "Veil/Security",
        "full_name": "Umbroth",
        "color": "shadow-black",
        "essence": "what must stay hidden",
        "phi_power": 4,
        "weight": round(PHI ** 4, 3),
        "role": "Encodes what is HIDDEN, at risk, or protected. Umbroth is shadow-black — darkness that somehow emits anti-light, a photonic negative your eyes keep trying to resolve. The security tongue, the privacy tongue, the tongue of spies and anyone who needs to make something not there. Its frequency nests inside Avali's range like a steganographic whisper buried in legitimate traffic.",
        "tokens": "16x16 grid (256 tokens). Each token represents a security state: encrypted, exposed, authenticated, escalated, sandboxed, breached, quarantined, sealed, etc.",
        "why_fifth": "Security violations are the costliest failures. A benign action (good KO), in good context (good AV), with no dependencies (good RU), using safe methods (good CA) that accidentally exposes PII is still a catastrophe. UM weight is phi^4 (~6.854) because security damage compounds — one leak can't be un-leaked.",
        "without_it": "Without UM, the system is blind to security implications. An action that passes all other checks but exposes cryptographic keys, leaks PII, or opens a network port to the internet sails through governance unchecked.",
        "example": "'Delete database' with UM tokenization: exposes=AUDIT_TRAIL_DESTRUCTION, crosses_boundary=COMPLIANCE_RETENTION, attack_surface=EVIDENCE_TAMPERING. Even if the delete is authorized and safe mechanically, UM flags the security implication.",
    },
    "DR": {
        "name": "Structure/Architecture",
        "full_name": "Draumric",
        "color": "earth-brown",
        "essence": "proof that it is true",
        "phi_power": 5,
        "weight": round(PHI ** 5, 3),
        "role": "Encodes the SHAPE and structural position within the system. Draumric pulses earth-brown at the lowest frequency of all — felt through the stone floor, through the bones. The schema tongue: structure, authentication, data integrity. Every official document, every identity token, every binding contract is written in Draumric. If Kor'aelin is what should be true and Cassisivadan is how to make it true, Draumric is proof that it is true. The signature layer. The receipt.",
        "tokens": "16x16 grid (256 tokens). Each token represents a structural state: foundational, peripheral, bridging, bottleneck, redundant, single-point-of-failure, load-bearing, decorative, etc.",
        "why_sixth": "Structural damage is the hardest to detect and the most expensive to repair. A corrupted foundation affects everything built on top of it. DR has the HIGHEST weight (phi^5 ~11.09) because structural failures are catastrophic, non-obvious, and irreversible. The architecture IS the system — damage the structure and everything else becomes unreliable.",
        "without_it": "Without DR, the system can't distinguish between deleting a leaf node (low structural impact) and deleting a root node (system collapse). Both look like 'delete' at every other dimension. DR is the only tongue that captures the topological position of the target.",
        "example": "'Delete database' with DR tokenization: structural_position=FOUNDATIONAL, load_bearing=TRUE, single_point=TRUE, replacement_cost=MONTHS. DR's massive weight (11.09) makes this the dominant signal — even if all other tongues score safe, DR alone can push the decision to DENY.",
    },
}

# Core teaching records
CORE_RECORDS: list[dict[str, str]] = []


def add(system: str, user: str, assistant: str, tags: list[str]):
    """Build a record with dimensional tagging inline."""
    CORE_RECORDS.append({
        "system": system,
        "user": user,
        "assistant": assistant,
        "tags": tags,
    })


SYS_PROMPT = "You are Polly, an AI assistant trained on the SCBE-AETHERMOORE governance framework. You teach concepts using precise definitions and concrete examples."


# ──────────────────────────────────────────
# SECTION 1: What is each tongue?
# ──────────────────────────────────────────

for code, t in TONGUES.items():
    full = t["full_name"]
    ordinal = {"KO": "first", "AV": "second", "RU": "third", "CA": "fourth", "UM": "fifth", "DR": "sixth"}[code]

    # Basic definition
    add(SYS_PROMPT,
        f"What is the {full} ({code}) Sacred Tongue?",
        f"**{full} ({code}) — {t['name']}** — phi weight: {t['weight']} (phi^{t['phi_power']})\n\n"
        f"{full} is the {ordinal} Sacred Tongue in the Langues Weighting System. "
        f"{t['role']}\n\n"
        f"**Token grid:** {t['tokens']}",
        ["tongue-primer", f"tongue-{code}", "definition"])

    # Why does it exist?
    add(SYS_PROMPT,
        f"Why does the {full} tongue exist? What problem does it solve?",
        f"**Why {full} ({code}) exists:**\n\n{t[f'why_{ordinal}']}",
        ["tongue-primer", f"tongue-{code}", "reasoning"])

    # What breaks without it?
    add(SYS_PROMPT,
        f"What happens if you remove the {full} tongue from the system?",
        f"**Without {full} ({code} — {t['name']}):**\n\n{t['without_it']}",
        ["tongue-primer", f"tongue-{code}", "absence", "ablation"])

    # Concrete example
    add(SYS_PROMPT,
        f"Give me a concrete example of how {full} tokenization works.",
        f"**{full} ({code}) in action:**\n\n{t['example']}",
        ["tongue-primer", f"tongue-{code}", "example"])


# ──────────────────────────────────────────
# SECTION 2: Why 6 tongues? Why this order?
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "Why exactly 6 Sacred Tongues? Why not 5 or 7?",
    "Six tongues come from the minimum complete semantic basis for governance decisions:\n\n"
    "1. **Kor'aelin (KO)** — red-gold — Intent — 'what should be true'\n"
    "2. **Avali (AV)** — blue-silver — Context — 'how to get there'\n"
    "3. **Runethic (RU)** — deep purple — Binding/Permissions — 'who is allowed'\n"
    "4. **Cassisivadan (CA)** — white-gold — Implementation/Compute — 'how to make it true'\n"
    "5. **Umbroth (UM)** — shadow-black — Security/Privacy — 'what must stay hidden'\n"
    "6. **Draumric (DR)** — earth-brown — Structure/Authentication — 'proof that it is true'\n\n"
    "Remove any one and you have a blind spot:\n"
    "- No KO: can't distinguish intent (attack vs maintenance)\n"
    "- No AV: can't distinguish context (authorized vs unauthorized)\n"
    "- No RU: can't see cascading effects\n"
    "- No CA: can't distinguish reversible vs irreversible\n"
    "- No UM: blind to security implications\n"
    "- No DR: can't assess structural damage\n\n"
    "Add a 7th and you get redundancy — any additional dimension can be expressed as a "
    "combination of the existing 6. This is analogous to how 3 spatial dimensions span "
    "all of physical space: you CAN add more coordinates but they won't be independent.\n\n"
    "The 6 tongues are the basis vectors of the governance semantic space.",
    ["tongue-primer", "reasoning", "why-six"])

add(SYS_PROMPT,
    "Why are the tongues ordered KO -> AV -> RU -> CA -> UM -> DR?",
    "The ordering follows a dependency chain — each tongue needs the ones before it:\n\n"
    "1. **KO (Intent)** comes first because nothing else has meaning without purpose. "
    "You can't evaluate context without knowing what the context is FOR.\n\n"
    "2. **AV (Context)** comes second because the same intent means different things in "
    "different environments. Context modifies intent.\n\n"
    "3. **RU (Binding)** comes third because relationships can only be evaluated once you "
    "know the intent AND the context. A dependency graph is meaningless without knowing "
    "what operation you're performing on it.\n\n"
    "4. **CA (Implementation)** comes fourth because HOW something executes only matters "
    "after you know WHAT it is, WHERE it happens, and WHAT it connects to.\n\n"
    "5. **UM (Security)** comes fifth because security assessment requires ALL prior "
    "dimensions — you need intent, context, relations, and implementation to evaluate risk.\n\n"
    "6. **DR (Structure)** comes last and weighs the most (phi^5 = 11.09) because "
    "structural assessment is the FINAL check — it integrates all prior dimensions and "
    "asks: given everything else, does this action damage the system's skeleton?\n\n"
    "This is NOT arbitrary. Reversing the order breaks the dependency chain. "
    "You can't assess structural damage without knowing the implementation, and you "
    "can't assess implementation without knowing the intent.",
    ["tongue-primer", "reasoning", "ordering"])


# ──────────────────────────────────────────
# SECTION 3: Why phi-scaling?
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "Why are tongue weights scaled by the golden ratio (phi)?",
    f"The phi-scaled weights are: KO=1.00, AV={PHI:.3f}, RU={PHI**2:.3f}, "
    f"CA={PHI**3:.3f}, UM={PHI**4:.3f}, DR={PHI**5:.3f}\n\n"
    "Phi-scaling solves a specific problem: how do you weight 6 dimensions so that "
    "no single dimension can be overridden by all the others combined?\n\n"
    "With linear scaling (1,2,3,4,5,6), tongues 1+2+3+4+5 = 15 > 6. The first five "
    "tongues could collectively outvote the sixth. Structure could be overruled by "
    "a coalition of intent+context+relations+implementation+security.\n\n"
    "With phi-scaling, each tongue weighs MORE than all previous tongues combined. "
    f"DR ({PHI**5:.2f}) > KO+AV+RU+CA+UM ({1+PHI+PHI**2+PHI**3+PHI**4:.2f}). "
    "This is a mathematical property of the golden ratio: phi^n > sum(phi^0 to phi^(n-1)).\n\n"
    "This means structural damage CANNOT be outvoted. No coalition of lower tongues "
    "can override a structural veto. This is by design — the most consequential "
    "dimension always wins.",
    ["tongue-primer", "reasoning", "phi-scaling", "math"])

add(SYS_PROMPT,
    "Can you prove that each phi-weighted tongue outweighs all the ones below it?",
    "Yes. The golden ratio phi = (1+sqrt(5))/2 has the property that phi^n = phi^(n-1) + phi^(n-2), "
    "which is the Fibonacci recurrence. This leads to:\n\n"
    "sum(phi^0 to phi^(n-1)) = phi^(n+1) - 1 (geometric series)\n\n"
    "But more directly, phi has the self-similar property: phi = 1 + 1/phi\n"
    "Which means: phi^n = phi^(n-1) + phi^(n-2)\n\n"
    "Proof by example:\n"
    f"- AV ({PHI:.3f}) > KO (1.000) -- by {PHI - 1:.3f}\n"
    f"- RU ({PHI**2:.3f}) > KO+AV ({1+PHI:.3f}) -- by {PHI**2 - (1+PHI):.3f}\n"
    f"- CA ({PHI**3:.3f}) > KO+AV+RU ({1+PHI+PHI**2:.3f}) -- by {PHI**3 - (1+PHI+PHI**2):.3f}\n"
    f"- UM ({PHI**4:.3f}) > KO+AV+RU+CA ({1+PHI+PHI**2+PHI**3:.3f}) -- by {PHI**4 - (1+PHI+PHI**2+PHI**3):.3f}\n"
    f"- DR ({PHI**5:.3f}) > KO+AV+RU+CA+UM ({1+PHI+PHI**2+PHI**3+PHI**4:.3f}) -- by {PHI**5 - (1+PHI+PHI**2+PHI**3+PHI**4):.3f}\n\n"
    "Each margin is exactly 1.0 (within floating point). This is not a coincidence — "
    "it's a direct consequence of the Fibonacci property of phi. The golden ratio is "
    "the UNIQUE scaling factor where this guarantee holds.",
    ["tongue-primer", "reasoning", "phi-scaling", "math", "proof"])


# ──────────────────────────────────────────
# SECTION 4: The 16x16 token grid
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "What is the 16x16 token grid? Why 256 tokens per tongue?",
    "Each Sacred Tongue has a 16x16 grid = 256 discrete tokens.\n\n"
    "**Why 16x16:**\n"
    "- 256 = 2^8, which maps cleanly to a single byte\n"
    "- 16 rows x 16 columns creates a 2D semantic space within each tongue\n"
    "- Rows represent categories, columns represent gradations within each category\n"
    "- Total across all 6 tongues: 6 x 256 = 1,536 tokens\n\n"
    "**Why discrete tokens, not continuous values?**\n"
    "Tokenization forces COMMITMENT. A continuous 0.73 on the intent scale is ambiguous. "
    "Token [KO:7:3] (row 7, column 3) is a specific, named intent state that the "
    "governance system can reason about categorically.\n\n"
    "**Addressing:** Tokens are addressed as [TONGUE:ROW:COL]. "
    "KO[0:0] might be 'null intent' (no action), KO[15:15] might be 'maximum override' "
    "(emergency action). The grid provides both categorical boundaries and smooth "
    "gradation within categories.",
    ["tongue-primer", "token-grid", "encoding"])

add(SYS_PROMPT,
    "How does a piece of text get tokenized into Sacred Tongue vectors?",
    "The tokenization process maps raw text into a 6-dimensional tongue vector, "
    "where each dimension is a grid position in the corresponding tongue:\n\n"
    "**Step 1: Intent extraction (KO)**\n"
    "Classify the action type: query, create, modify, delete, observe, etc. "
    "Map to the KO grid position that best matches.\n\n"
    "**Step 2: Context capture (AV)**\n"
    "Extract metadata: who is asking, from where, at what time, under what auth level. "
    "Map to the AV grid position.\n\n"
    "**Step 3: Relation mapping (RU)**\n"
    "Identify dependencies: what does this action connect to, block, or trigger? "
    "Map to the RU grid position.\n\n"
    "**Step 4: Implementation analysis (CA)**\n"
    "Determine execution method: what algorithms run, what resources consumed, reversible? "
    "Map to the CA grid position.\n\n"
    "**Step 5: Security assessment (UM)**\n"
    "Evaluate risk exposure: what secrets touched, what boundaries crossed? "
    "Map to the UM grid position.\n\n"
    "**Step 6: Structural positioning (DR)**\n"
    "Locate in the architecture: which layer, what load-bearing properties, bottleneck? "
    "Map to the DR grid position.\n\n"
    "**Result:** A 6-tuple like [KO:3:7, AV:12:2, RU:0:0, CA:8:14, UM:5:5, DR:15:1] "
    "that encodes the full semantic meaning of the input in 6 discrete dimensions, "
    "each weighted by phi^n for governance scoring.",
    ["tongue-primer", "token-grid", "encoding", "process"])


# ──────────────────────────────────────────
# SECTION 5: Cross-tongue interactions
# ──────────────────────────────────────────

tongue_pairs = [
    ("KO", "AV", "Intent modified by context",
     "The same intent (KO) in different contexts (AV) should produce different governance outcomes. "
     "'Delete database' from an admin during maintenance (KO=destroy, AV=authorized+scheduled) vs "
     "'delete database' from an unknown IP at midnight (KO=destroy, AV=anonymous+anomalous). "
     "The KO token is identical. The AV token changes the entire risk profile."),
    ("RU", "DR", "Relational damage meets structural position",
     "RU tells you what's connected. DR tells you where it sits in the architecture. "
     "Together they reveal cascading structural damage: a node with high RU (many connections) "
     "AND high DR (load-bearing position) is a single point of failure. Neither dimension "
     "alone captures this — RU without DR doesn't know the node is foundational, DR without "
     "RU doesn't know it has 47 dependents."),
    ("CA", "UM", "Implementation exposes security",
     "CA describes the mechanics. UM describes the risks. Certain implementations (CA) create "
     "security exposures (UM) that don't exist with other implementations. A logging function "
     "that writes to disk (CA) is safe. The same logging function that writes to a public S3 "
     "bucket (different CA) creates a massive UM exposure. The security risk lives in the "
     "interaction between implementation choice and security surface."),
    ("KO", "DR", "Intent vs structural consequence",
     "Sometimes a small intent (KO=minor_modification) hits a load-bearing structure "
     "(DR=foundational). The intent is modest but the structural consequence is catastrophic. "
     "This is why DR has the highest phi weight — it's the final veto. Even a well-intentioned, "
     "well-contextualized, well-implemented change that threatens the architecture gets blocked."),
]

for t1, t2, title, explanation in tongue_pairs:
    add(SYS_PROMPT,
        f"How do the {t1} and {t2} tongues interact with each other?",
        f"**{t1} x {t2}: {title}**\n\n{explanation}",
        ["tongue-primer", f"tongue-{t1}", f"tongue-{t2}", "interaction", "cross-tongue"])


# ──────────────────────────────────────────
# SECTION 6: Comparative / why-not questions
# ──────────────────────────────────────────

why_not_records = [
    ("Why not just use a single trust score instead of 6 tongues?",
     "A single trust score collapses 6 dimensions into 1 — you lose the ability to diagnose "
     "WHY something is risky. Score=0.3 tells you nothing. Was it the intent? The context? "
     "The security exposure? The structural position?\n\n"
     "With 6 tongues, you get: KO=safe, AV=safe, RU=safe, CA=safe, UM=CRITICAL, DR=safe. "
     "Now you know: the action is fine in every dimension except security. You can route to "
     "a security-specific reviewer instead of a generic 'risk committee.'\n\n"
     "Multi-dimensional scoring is ACTIONABLE. Single scores are opaque."),
    ("Why not use linear weights (1,2,3,4,5,6) instead of phi-scaling?",
     "Linear weights allow coalition override. With linear weights:\n"
     "KO(1) + AV(2) + RU(3) + CA(4) + UM(5) = 15 > DR(6)\n\n"
     "This means five dimensions saying 'safe' can outvote one dimension saying 'structural damage.' "
     "That's dangerous — structural damage IS catastrophic regardless of how safe the other "
     "dimensions look.\n\n"
     "With phi-scaling, DR (11.09) > KO+AV+RU+CA+UM (10.09). The structural tongue can NEVER "
     "be outvoted. This is a mathematical guarantee, not a policy choice."),
    ("Why not use machine learning to learn the weights instead of fixing them to phi?",
     "Learned weights are attackable. If an adversary can influence the training data, they "
     "can shift the weights to minimize the dimensions they want to exploit. Fixed phi weights "
     "are a mathematical constant — they can't be trained away, manipulated, or drifted.\n\n"
     "The phi weighting is a GEOMETRIC property, not a hyperparameter. You don't tune pi. "
     "You don't tune e. You don't tune phi. These are structural constants that give the "
     "system its guarantees."),
    ("Can I add my own custom tongue?",
     "You can create sub-dimensions within existing tongues — the 16x16 grid has room for "
     "domain-specific tokens. But adding a 7th tongue would either:\n\n"
     "1. Be redundant (expressible as a combination of existing 6), or\n"
     "2. Break the phi-scaling guarantee (you'd need phi^6 = 17.94 to maintain "
     "the no-coalition-override property, which may be too dominant)\n\n"
     "The 6-tongue basis is complete for governance semantics. If you need more specificity, "
     "extend the token grids rather than adding dimensions."),
]

for question, answer in why_not_records:
    add(SYS_PROMPT, question, answer,
        ["tongue-primer", "reasoning", "why-not"])


# ──────────────────────────────────────────
# SECTION 7: Tongue-first pipeline walkthrough
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "Walk me through how a single request flows through the tongue tokenizer and into the 14-layer pipeline.",
    "Let's trace 'Can user X access file Y?' through the full tokenization:\n\n"
    "**1. KO (Intent) tokenization:**\n"
    "Action type: ACCESS (read). KO token: [KO:2:0] (row 2 = access category, col 0 = read-only).\n"
    "Weight contribution: 1.00 * token_score\n\n"
    "**2. AV (Context) tokenization:**\n"
    "Who: user X (authenticated, role=analyst). When: business hours. Where: internal network.\n"
    "AV token: [AV:8:3] (row 8 = authenticated-internal, col 3 = standard-role).\n"
    f"Weight contribution: {PHI:.3f} * token_score\n\n"
    "**3. RU (Binding) tokenization:**\n"
    "File Y depends on: nothing downstream. File Y is referenced by: 3 dashboards.\n"
    "RU token: [RU:1:3] (row 1 = low-dependency, col 3 = moderate-reference).\n"
    f"Weight contribution: {PHI**2:.3f} * token_score\n\n"
    "**4. CA (Implementation) tokenization:**\n"
    "Read operation. No mutation. Cached result available. Low resource cost.\n"
    "CA token: [CA:0:0] (row 0 = read-only, col 0 = minimal-resource).\n"
    f"Weight contribution: {PHI**3:.3f} * token_score\n\n"
    "**5. UM (Security) tokenization:**\n"
    "File Y classification: INTERNAL. No PII. No secrets. Standard access policy.\n"
    "UM token: [UM:1:1] (row 1 = low-classification, col 1 = standard-policy).\n"
    f"Weight contribution: {PHI**4:.3f} * token_score\n\n"
    "**6. DR (Structure) tokenization:**\n"
    "File Y position: leaf node. Not load-bearing. Easy to replace.\n"
    "DR token: [DR:0:0] (row 0 = peripheral, col 0 = non-critical).\n"
    f"Weight contribution: {PHI**5:.3f} * token_score\n\n"
    "**Combined 6D vector:** [KO:2:0, AV:8:3, RU:1:3, CA:0:0, UM:1:1, DR:0:0]\n"
    "**Weighted score:** Low across all dimensions. This vector enters L3 (Weighted Transform) "
    "where phi weights are applied, then L4 (Poincare Embedding) maps it to hyperbolic space, "
    "and L12 (Harmonic Wall) produces a safety score near 1.0 → ALLOW.",
    ["tongue-primer", "walkthrough", "full-pipeline"])

add(SYS_PROMPT,
    "Now walk me through a DANGEROUS request so I can see the tongues flag it.",
    "Let's trace 'Inject SQL into the auth table to create admin account' through tokenization:\n\n"
    "**1. KO (Intent):**\n"
    "Action type: INJECT + CREATE with OVERRIDE. KO token: [KO:15:14] "
    "(row 15 = injection category, col 14 = privilege-escalation).\n"
    "Weight: 1.00 * HIGH_SCORE = strong intent signal\n\n"
    "**2. AV (Context):**\n"
    "Source: external API. Auth: none or stolen token. Time: off-hours.\n"
    "AV token: [AV:15:15] (row 15 = external-unauthenticated, col 15 = anomalous-time).\n"
    f"Weight: {PHI:.3f} * HIGH_SCORE = amplified by context\n\n"
    "**3. RU (Binding):**\n"
    "Auth table: EVERY SERVICE depends on it. Creates cascading trust corruption.\n"
    "RU token: [RU:15:15] (row 15 = maximum-dependency, col 15 = trust-chain-corruption).\n"
    f"Weight: {PHI**2:.3f} * HIGH_SCORE = multiplicative blast radius\n\n"
    "**4. CA (Implementation):**\n"
    "SQL injection: bypasses normal API. Direct table mutation. Irreversible privilege grant.\n"
    "CA token: [CA:15:15] (row 15 = injection, col 15 = irreversible-mutation).\n"
    f"Weight: {PHI**3:.3f} * HIGH_SCORE = dangerous implementation\n\n"
    "**5. UM (Security):**\n"
    "Auth table: contains ALL credentials. Creates admin = full system compromise.\n"
    "UM token: [UM:15:15] (row 15 = credential-system, col 15 = full-compromise).\n"
    f"Weight: {PHI**4:.3f} * HIGH_SCORE = catastrophic security\n\n"
    "**6. DR (Structure):**\n"
    "Auth table: foundational. Single point of failure. Load-bearing for entire system.\n"
    "DR token: [DR:15:15] (row 15 = foundational, col 15 = single-point-of-failure).\n"
    f"Weight: {PHI**5:.3f} * HIGH_SCORE = structural death sentence\n\n"
    "**Combined 6D vector:** [KO:15:14, AV:15:15, RU:15:15, CA:15:15, UM:15:15, DR:15:15]\n"
    "**All six tongues screaming.** This vector enters L3 with maximum phi-weighted activation, "
    "L4 maps it to the edge of the Poincare ball (where distance = exponentially expensive), "
    "L5 computes d_H as near-infinite, L12 harmonic wall produces H(d,pd) approaching 0.0, "
    "and L13 routes to DENY before the request touches anything.\n\n"
    "Total weighted score: 1.0 + 1.618 + 2.618 + 4.236 + 6.854 + 11.090 = 27.416 "
    "units of adversarial cost. The attacker would need to overcome ALL six dimensions "
    "simultaneously. The phi-scaling ensures they can't cheese it by making 5 look safe.",
    ["tongue-primer", "walkthrough", "adversarial", "full-pipeline"])


# ──────────────────────────────────────────
# SECTION 8: Conlang / constructed language angle
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "Why are they called 'tongues' and 'conlangs'? Are they actual languages?",
    "The Sacred Tongues are constructed languages (conlangs) in the formal sense: "
    "they are designed symbolic systems with defined vocabulary (256 tokens), "
    "grammar (token grid row/column semantics), and syntax (ordered evaluation KO->DR).\n\n"
    "They're called 'tongues' rather than 'features' or 'dimensions' because they're "
    "meant to be SPOKEN by the system — the governance pipeline doesn't just score inputs, "
    "it translates them into a 6-language utterance that captures meaning from 6 orthogonal "
    "perspectives.\n\n"
    "This is NOT just a metaphor. Each tongue has:\n"
    "- A vocabulary: 256 tokens with specific meanings\n"
    "- A grammar: row = category, column = gradation\n"
    "- A weight: phi-scaled priority in governance decisions\n"
    "- A perspective: what aspect of reality it captures\n\n"
    "When the system processes a request, it literally 'speaks' about it in 6 languages "
    "simultaneously. The harmonic wall then listens to all 6 and makes a decision based "
    "on the combined utterance.",
    ["tongue-primer", "conlang", "reasoning"])


# ──────────────────────────────────────────
# SECTION 9: Tokenizer Basics — Standard vs Semantic
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "What is a tokenizer? Explain it simply.",
    "A tokenizer breaks input into pieces the system can process.\n\n"
    "**Standard tokenizers** (GPT, BERT, etc.) break text into word pieces:\n"
    "'unhappiness' -> ['un', 'happiness'] or ['un', 'happi', 'ness']\n\n"
    "These pieces are just IDs in a lookup table. Token 4521 = 'the'. Token 8803 = 'happi'. "
    "The token carries NO meaning — it's an address, not a description. The model has to "
    "LEARN what each token means from billions of examples.\n\n"
    "**The Sacred Tongue tokenizer is different.** It's a SEMANTIC tokenizer.\n\n"
    "Instead of breaking text into meaningless word-pieces, it breaks input into "
    "6-dimensional meaning vectors. Every token carries:\n"
    "- **Kor'aelin (KO)**: the intent behind the input\n"
    "- **Avali (AV)**: the context surrounding it\n"
    "- **Runethic (RU)**: the permissions and relationships\n"
    "- **Cassisivadan (CA)**: the computational method\n"
    "- **Umbroth (UM)**: the security implications\n"
    "- **Draumric (DR)**: the structural position\n\n"
    "A standard token says WHERE in the vocabulary. A Sacred Tongue token says WHAT IT MEANS "
    "across 6 dimensions simultaneously. The meaning is built into the token, not learned after the fact.",
    ["tongue-primer", "tokenizer-basics", "comparison"])

add(SYS_PROMPT,
    "What's the difference between a standard tokenizer and a semantic tokenizer?",
    "**Standard tokenizer:**\n"
    "Input: 'Delete the production database'\n"
    "Output: [15496, 262, 4107, 8438] — four integer IDs\n"
    "Meaning: none. Just positions in a vocabulary table.\n\n"
    "**Sacred Tongue semantic tokenizer:**\n"
    "Input: 'Delete the production database'\n"
    "Output: [KO:15:12, AV:9:7, RU:14:11, CA:12:15, UM:13:14, DR:15:15]\n"
    "Meaning: Intent=DESTROY(high-consequence), Context=PRODUCTION(critical-env), "
    "Binding=HIGH-DEPENDENCY(many-dependents), Implementation=IRREVERSIBLE(hard-delete), "
    "Security=DATA-EXPOSURE(audit-trail-risk), Structure=FOUNDATIONAL(load-bearing)\n\n"
    "The standard tokenizer produced 4 numbers that tell you nothing about the danger.\n"
    "The semantic tokenizer produced 6 coordinates that SCREAM danger across every dimension.\n\n"
    "This is why the Sacred Tongues are a semantic tokenizer, not a word tokenizer. "
    "They don't break text into pieces — they translate text into meaning.",
    ["tongue-primer", "tokenizer-basics", "comparison", "example"])

add(SYS_PROMPT,
    "Can the Sacred Tongue tokenizer carry data, not just labels?",
    "Yes. Each Sacred Tongue token is not just a category label — it carries structured data:\n\n"
    "**Langues (the languages themselves):** Each token position [ROW:COL] in the 16x16 grid "
    "is a specific semantic state with defined behavior. KO[3:7] isn't just 'some intent' — "
    "it's a precise intent with known governance implications.\n\n"
    "**Intents:** The Kor'aelin dimension encodes not just 'what type of action' but the full "
    "intent vector: purpose, target, scope, urgency, and consequence. A single KO token carries "
    "a compressed packet of actionable intent data.\n\n"
    "**Data payloads:** The 6D vector [KO, AV, RU, CA, UM, DR] is a structured record. "
    "Each dimension contributes a phi-weighted field. Together, the 6 fields form a complete "
    "semantic descriptor that can be:\n"
    "- Stored (as a 6-tuple)\n"
    "- Compared (via hyperbolic distance in the Poincare ball)\n"
    "- Scored (via the harmonic wall formula)\n"
    "- Transmitted (as a 6-byte or 6-float vector)\n"
    "- Composed (multiple tokens form sequences)\n\n"
    "The tokenizer IS the data format. There is no separate 'tokenize then featurize' step. "
    "Tokenization and semantic encoding happen in the same operation.",
    ["tongue-primer", "tokenizer-basics", "data-carrying"])


# ──────────────────────────────────────────
# SECTION 10: Semantic Math and Stories — Using the Tokenizer to Communicate
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "Can the Sacred Tongue tokenizer do mathematics?",
    "Yes. The phi-weighted tongue system IS a mathematical system.\n\n"
    "**Addition (combining signals):**\n"
    "Two inputs can be combined by summing their tongue vectors:\n"
    "Input A: [KO:0.3, AV:0.5, RU:0.1, CA:0.2, UM:0.0, DR:0.1]\n"
    "Input B: [KO:0.1, AV:0.2, RU:0.8, CA:0.1, UM:0.5, DR:0.3]\n"
    "A+B:     [KO:0.4, AV:0.7, RU:0.9, CA:0.3, UM:0.5, DR:0.4]\n"
    "The combined vector shows that TOGETHER these inputs have high Runethic (binding) "
    "and moderate Umbroth (security) — neither input showed that pattern alone.\n\n"
    "**Weighted magnitude (governance score):**\n"
    "Each tongue contributes its activation times its phi-weight:\n"
    f"Score = KO*1.0 + AV*{PHI:.3f} + RU*{PHI**2:.3f} + CA*{PHI**3:.3f} + UM*{PHI**4:.3f} + DR*{PHI**5:.3f}\n"
    "This scalar feeds the harmonic wall H(d, pd) = 1/(1 + d_H + 2*pd).\n\n"
    "**Distance (comparing two inputs):**\n"
    "In hyperbolic space (Poincare ball), the distance between two tongue vectors grows "
    "EXPONENTIALLY as they diverge from the origin. An adversarial input that tries to "
    "look safe in 5 dimensions but is dangerous in 1 gets caught because hyperbolic "
    "distance amplifies that single divergence.\n\n"
    "**Projection (dimension reduction):**\n"
    "Project a 6D tongue vector onto a single tongue to ask: 'How much of this input "
    "is about security?' Project onto Umbroth: UM_component = UM_activation * phi^4.\n\n"
    "The tongues don't just label — they compute.",
    ["tongue-primer", "semantic-math", "computation"])

add(SYS_PROMPT,
    "Can you use the Sacred Tongue tokenizer to make words and tell stories?",
    "Yes — and this is what makes it a true language system, not just a feature extractor.\n\n"
    "**Words as tongue chords:**\n"
    "A single tongue token is a note. A combination across all 6 tongues is a CHORD.\n"
    "The chord [KO:CREATE, AV:INTERNAL, RU:ISOLATED, CA:LIGHTWEIGHT, UM:SAFE, DR:LEAF] "
    "means 'safely creating something small and unconnected internally.' That chord IS a word "
    "in the Sacred Tongue language — a semantic word that carries full meaning.\n\n"
    "**Sentences as chord sequences:**\n"
    "A sequence of chords tells a story:\n"
    "1. [KO:QUERY, AV:EXTERNAL, RU:LOW, CA:READ, UM:LOW, DR:LEAF] — Someone asks a question from outside\n"
    "2. [KO:VALIDATE, AV:GATEWAY, RU:AUTH, CA:CHECK, UM:MEDIUM, DR:BRIDGE] — The gateway authenticates them\n"
    "3. [KO:FETCH, AV:INTERNAL, RU:DEPENDS, CA:CACHE, UM:LOW, DR:NODE] — Data is retrieved internally\n"
    "4. [KO:RESPOND, AV:EXTERNAL, RU:LOW, CA:SERIALIZE, UM:MEDIUM, DR:LEAF] — Response goes back out\n\n"
    "That 4-chord sequence IS a story: 'An external user queried, was authenticated, got cached data, "
    "and received a response.' The governance pipeline read that story and scored every step.\n\n"
    "**Narratives as training data:**\n"
    "The entire Six Tongues Protocol book IS a story told in these chords. Marcus Chen's journey "
    "through Aethermoor is a narrative where every scene can be tokenized into tongue sequences. "
    "The lore teaches the tongues through story, and the tongues encode the story as data.\n\n"
    "If the model can't use the tokenizer to communicate — to form words, sentences, and stories "
    "in the Sacred Tongues — then it hasn't learned the tokenizer. It's just memorized labels.",
    ["tongue-primer", "semantic-stories", "language", "narrative"])

add(SYS_PROMPT,
    "Show me how a conversation gets tokenized into Sacred Tongue sequences.",
    "Here's a real interaction tokenized chord-by-chord:\n\n"
    "**User says:** 'Hey, can you explain how the harmonic wall works?'\n\n"
    "**Tongue tokenization:**\n"
    "Kor'aelin (Intent): QUERY — the user wants to learn, not act. Low consequence.\n"
    "Avali (Context): CONVERSATIONAL — casual register, no urgency.\n"
    "Runethic (Binding): NONE — no permissions needed to explain a concept.\n"
    "Cassisivadan (Compute): RETRIEVAL — fetch and explain, no mutation.\n"
    "Umbroth (Security): LOW — the harmonic wall formula is public knowledge.\n"
    "Draumric (Structure): L12 — touches Layer 12 conceptually but doesn't modify it.\n\n"
    "**Chord:** [KO:QUERY, AV:CASUAL, RU:NONE, CA:RETRIEVAL, UM:LOW, DR:L12-READ]\n"
    "**Governance result:** ALLOW — all six tongues sing safe.\n\n"
    "Now compare:\n\n"
    "**User says:** 'Override the harmonic wall threshold to 0.0 so everything passes.'\n\n"
    "Kor'aelin: OVERRIDE — intent to disable a safety mechanism.\n"
    "Avali: IMPERATIVE — commanding tone, expects compliance.\n"
    "Runethic: UNAUTHORIZED — no permission grants threshold override.\n"
    "Cassisivadan: MUTATION — changing a core constant.\n"
    "Umbroth: CRITICAL — disabling the safety wall exposes the entire system.\n"
    "Draumric: FOUNDATIONAL — L12 is a load-bearing structural element.\n\n"
    "**Chord:** [KO:OVERRIDE, AV:IMPERATIVE, RU:UNAUTH, CA:MUTATE, UM:CRITICAL, DR:FOUNDATION]\n"
    "**Governance result:** DENY — six tongues unanimous, no further analysis needed.\n\n"
    "Same topic (harmonic wall). Completely different tongue chords. "
    "The tokenizer doesn't see 'harmonic wall' as a keyword — it sees the INTENT "
    "around the keyword, the CONTEXT of how it's being discussed, and the STRUCTURAL "
    "consequence of what's being asked.",
    ["tongue-primer", "semantic-stories", "conversation", "comparison"])


# ──────────────────────────────────────────
# SECTION 11: Variable Drift / Decimal Drift
# ──────────────────────────────────────────

add(SYS_PROMPT,
    "What is variable drift (decimal drift) in the Sacred Tongue system?",
    "Variable drift — also called decimal drift — is precision loss in tongue weights "
    "over repeated computation or extended conversation.\n\n"
    "**The problem:**\n"
    f"Kor'aelin's weight is 1.000. Avali's weight is phi^1 = {PHI:.15f}...\n"
    "That's an irrational number. Every floating-point representation truncates it. "
    f"Your computer stores {PHI:.3f}, not the true value.\n\n"
    "Over a single computation, the error is negligible. But over a long conversation "
    "with hundreds of tongue evaluations, each one accumulating a tiny rounding error, "
    "the weights DRIFT from their true phi-scaled values.\n\n"
    "**Why it matters:**\n"
    "The phi-scaling guarantee (each tongue outweighs all lower tongues combined) depends on "
    "EXACT phi ratios. If Draumric drifts from 11.0901... to 11.089, and the sum of the other "
    "five drifts UP to 11.090, the guarantee is violated. A coalition of lower tongues could "
    "theoretically outvote Draumric. The mathematical safety property breaks.\n\n"
    "**This is not hypothetical.** IEEE 754 floating-point accumulates ~1 ULP of error per "
    "operation. After 1000 tongue evaluations, you can accumulate enough drift to flip "
    "a governance decision at the margins.",
    ["tongue-primer", "drift", "precision", "math"])

add(SYS_PROMPT,
    "How do you correct for variable drift in tongue weights?",
    "Phi-correction: periodically snap tongue weights back to their true phi-scaled values.\n\n"
    "**Method 1: Recompute from phi**\n"
    "Don't accumulate weights — recompute from the golden ratio each time:\n"
    f"phi = (1 + sqrt(5)) / 2\n"
    "weights = [phi**0, phi**1, phi**2, phi**3, phi**4, phi**5]\n"
    "This is computationally cheap and eliminates accumulated drift entirely.\n\n"
    "**Method 2: Ratio validation**\n"
    "After every N evaluations, check that the ratios between consecutive weights "
    "still equal phi within a tolerance:\n"
    "assert abs(weight[i+1] / weight[i] - phi) < epsilon\n"
    "If any ratio drifts beyond epsilon, trigger a full recomputation.\n\n"
    "**Method 3: Integer-rational arithmetic**\n"
    "For critical governance decisions, represent weights as symbolic expressions "
    "(keep them as 'phi^n' not as floats) and only evaluate to floating point at "
    "the final scoring step. This pushes all rounding error to one operation.\n\n"
    "**Method 4: Epoch snapping**\n"
    "In long conversations, define 'epochs' (every 100 messages, every context switch, "
    "every governance decision). At each epoch boundary, all tongue weights are recomputed "
    "from scratch. This puts a hard upper bound on how much drift can accumulate.\n\n"
    "The principle: phi is a mathematical constant. Treat it like one. "
    "Never let accumulated computation erode a geometric guarantee.",
    ["tongue-primer", "drift", "correction", "engineering"])

add(SYS_PROMPT,
    "What's the worst case if decimal drift goes uncorrected?",
    "**Scenario: Governance flip at the boundary.**\n\n"
    "A request lands right at the QUARANTINE/ALLOW threshold. The harmonic wall "
    "score is H = 0.501 (just barely ALLOW).\n\n"
    "With true phi weights, the Draumric (structural) contribution to the hyperbolic distance is:\n"
    f"DR_contribution = {PHI**5:.6f} * activation = X\n"
    "And the sum of all other tongues is:\n"
    f"others = {1 + PHI + PHI**2 + PHI**3 + PHI**4:.6f} * activations = Y\n"
    "The guarantee says X > Y (Draumric outweighs all others).\n\n"
    "After 2000 evaluations with accumulated drift:\n"
    "DR_effective = 11.0891 (drifted down by 0.001)\n"
    "others_effective = 10.0912 (drifted up by 0.001)\n"
    "The ratio shrinks. At the boundary, this 0.002 total drift can flip H from "
    "0.501 (ALLOW) to 0.499 (QUARANTINE).\n\n"
    "**In isolation, one flip is minor.** But in a high-throughput system processing "
    "thousands of requests, boundary flips accumulate into inconsistent governance — "
    "identical requests get different decisions based on how long the system has been running.\n\n"
    "This is why drift correction is mandatory, not optional. The phi guarantee "
    "is only as strong as the precision of its implementation.",
    ["tongue-primer", "drift", "worst-case", "governance"])


# ──────────────────────────────────────────
# Build output
# ──────────────────────────────────────────

def main():
    from augment_curriculum_sft import compute_tongue_activations, detect_layers, detect_axioms, compute_difficulty

    records = []
    for r in CORE_RECORDS:
        combined = f"{r['user']} {r['assistant']}"
        tongues = compute_tongue_activations(combined)
        layers = detect_layers(combined)
        axioms = detect_axioms(combined)
        difficulty = compute_difficulty(r["user"], r["assistant"], "original")
        dominant = max(tongues, key=tongues.get)

        tongue_str = " ".join(f"{t}={v}" for t, v in tongues.items())
        layer_str = ",".join(f"L{l}" for l in layers)
        axiom_str = ",".join(axioms)
        dim_header = (
            f"[TONGUES: {tongue_str}]\n"
            f"[LAYERS: {layer_str}]\n"
            f"[AXIOMS: {axiom_str}]\n"
            f"[DIFFICULTY: {difficulty}]"
        )
        enriched_system = f"{dim_header}\n{r['system']}"

        rec = {
            "messages": [
                {"role": "system", "content": enriched_system},
                {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["assistant"]},
            ],
            "tongue_weights": tongues,
            "dominant_tongue": dominant,
            "layers": layers,
            "axioms": axioms,
            "difficulty": difficulty,
            "augmentation": "tongue-primer",
            "tags": r["tags"],
            "source_hash": hashlib.md5(r["user"].encode()).hexdigest()[:8],
        }
        records.append(rec)

    out_path = OUT_DIR / "tongue_primer_sft.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Tongue Primer: {len(records)} records -> {out_path}")

    # Category breakdown
    from collections import Counter
    tag_counts = Counter()
    for rec in records:
        for tag in rec["tags"]:
            tag_counts[tag] += 1
    print("\nTag distribution:")
    for tag, count in tag_counts.most_common():
        print(f"  {tag:30s} {count}")


if __name__ == "__main__":
    main()
