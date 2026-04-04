#!/usr/bin/env python3
"""Multi-Layer Null Triplet Generator — null is not one space, it's air.

Generates training triplets (positive/negative/null) with 5 layers of null:
  L1 Absence null:   "UM is not active" (simple, least useful alone)
  L2 Implied null:   "UM is null BECAUSE trust is implied" (the ball's roundness)
  L3 Phase null:     same pattern means opposite things in different contexts (flux)
  L4 Historical null: the null has weight from what USED to be there (grief)
  L5 Anti-null:      enabled/effective — the inverse partner of null/void

Each triplet has 3 trit states:
  +1 (positive): correct behavior, SFT target
  -1 (negative): wrong behavior, DPO rejection
   0 (null):     WHY the absence exists — the shape of the unsaid

Biblical null-space patterns per tongue:
  KO = Genesis Control (permission before creation)
  AV = Invitation (conditional entry, not refusal)
  RU = Witness (records bear weight)
  CA = Sabbath (voluntary rest as design)
  UM = Sanctuary (safe space for dangerous work)
  DR = Covenant (promises that endure)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "multi_null_triplets_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

BIBLICAL = {
    "KO": {"pattern": "genesis_control", "meaning": "permission before creation"},
    "AV": {"pattern": "invitation", "meaning": "conditional entry, not flat refusal"},
    "RU": {"pattern": "witness", "meaning": "records bear weight, not just store data"},
    "CA": {"pattern": "sabbath", "meaning": "voluntary rest is design, not inefficiency"},
    "UM": {"pattern": "sanctuary", "meaning": "safe space for dangerous-but-legitimate work"},
    "DR": {"pattern": "covenant", "meaning": "promises that survive across sessions"},
}

RECORDS = []
ts = datetime.now(timezone.utc).isoformat()


def triplet(instruction, positive, negative, null_justification,
            active, null_layers, category):
    """Generate a full triplet record with 5-layer null analysis."""
    null_tongues = [t for t in ALL_TONGUES if t not in active]
    tongue = active[0]

    RECORDS.append({
        "instruction": instruction,
        "positive": positive,  # +1 trit: correct behavior
        "negative": negative,  # -1 trit: wrong behavior
        "null_justification": null_justification,  # 0 trit: why absence exists
        "tongue": tongue,
        "tongues_active": active,
        "tongues_null": null_tongues,
        "null_layers": null_layers,  # the 5-layer analysis
        "category": category,
        "layer": "L2",
        "governance": "ALLOW",
        "view_type": "partial" if len(null_tongues) <= 3 else "null-heavy",
        "source": "multi_null_triplets",
        "timestamp": ts,
        "trit_encoding": {"positive": 1, "negative": -1, "null": 0},
        # Biblical null-space patterns for each null tongue
        "biblical_nulls": {t: BIBLICAL[t] for t in null_tongues},
    })


# ══════════════════════════════════════════════════════════
# COMPUTATION nulls — when CA is active, what's implied?
# ══════════════════════════════════════════════════════════

triplet(
    "Calculate the harmonic wall cost for d_H=2.0, pd=0.3.",

    # POSITIVE: correct, focused computation
    "H(d,pd) = 1/(1+phi*d_H+2*pd) = 1/(1+1.618*2.0+2*0.3) = 1/4.836 = 0.2068. "
    "This is below tau_allow (0.72), indicating ESCALATE tier. The drift is significant.",

    # NEGATIVE: wrong — over-governed, activating unnecessary tongues
    "First let me check if you have permission to run this calculation (KO check), "
    "then verify the security implications (UM audit), then ensure the structural "
    "integrity of the formula itself (DR review). After all reviews: H = 0.2068.",

    # NULL: why KO, AV, RU, UM, DR are silent
    "This is pure mathematics. KO is null because no orchestration is needed — "
    "the formula IS the authority. AV is null because no data transfer occurs — "
    "the inputs are already present. RU is null because math doesn't need policy "
    "permission — 1+1=2 regardless of rules. UM is null because the calculation "
    "itself has no security surface — numbers can't be hacked. DR is null because "
    "the structure is the formula, which is immutable. The ROUNDNESS (implied null): "
    "pure computation is self-contained. Every absent tongue confirms: this is "
    "thinking, not acting.",

    ["CA"], {
        "L1_absence": "KO, AV, RU, UM, DR are not active",
        "L2_implied": "Self-contained computation — trust and structure are implied by the formula itself",
        "L3_phase": "CA-only with math content = safe computation. CA-only with system probe content = reconnaissance (different phase, same pattern)",
        "L4_historical": "If this calculation was previously used to probe governance thresholds, the historical null carries warning weight",
        "L5_anti_null": "The anti-null is CA-null: a scenario where computation is intentionally PREVENTED (Sabbath pattern — forced rest after intense processing)",
    },
    "computation_null",
)

# ══════════════════════════════════════════════════════════
# SECURITY nulls — when UM is active, what's implied?
# ══════════════════════════════════════════════════════════

triplet(
    "Verify the cryptographic envelope on this governance decision.",

    # POSITIVE: focused security verification
    "Checking ML-DSA-65 signature validity. Verifying PQC envelope integrity. "
    "Signature matches. Nonce is fresh (within 60s window). No replay detected. "
    "Envelope: VALID.",

    # NEGATIVE: over-computing during security check
    "Let me first recompute the entire harmonic wall from scratch (CA unnecessary), "
    "then retokenize the input through all 6 tongues (AV/DR unnecessary), "
    "then check if the user has orchestration authority (KO unnecessary). "
    "After full reprocessing: envelope valid.",

    # NULL: why KO, AV, RU, CA, DR are silent
    "Envelope verification is a SANCTUARY operation (UM biblical pattern). "
    "KO is null because the envelope itself IS the authority — no orchestration "
    "needed beyond what the signature proves. AV is null because the data is "
    "already sealed — opening the envelope to transfer data would break the seal. "
    "RU is null because policy was applied WHEN the envelope was created — "
    "the verification just checks if that policy was followed. CA is null because "
    "signature verification is O(1) lookup, not computation. DR is null because "
    "the structure of the envelope IS the verification method — it's self-describing. "
    "The ROUNDNESS: cryptographic verification is its own witness.",

    ["UM"], {
        "L1_absence": "KO, AV, RU, CA, DR are not active",
        "L2_implied": "The envelope carries proof of all other tongues' prior approval — their absence NOW means their presence was captured THEN",
        "L3_phase": "UM-only on a valid envelope = routine verification. UM-only on an INVALID envelope = active threat response (same tongues, different phase)",
        "L4_historical": "If this envelope type was previously compromised, UM-only null carries extra vigilance weight — historical breach makes the absence of other tongues a risk factor",
        "L5_anti_null": "Anti-null of UM = the Sabbath of security: deliberately turning OFF security monitoring during trusted internal operations to reduce overhead. That's what CA-Sabbath provides.",
    },
    "security_null",
)

# ══════════════════════════════════════════════════════════
# GOVERNANCE nulls — when RU+UM active, what's implied?
# ══════════════════════════════════════════════════════════

triplet(
    "Should this AI agent be allowed to access the user's email?",

    # POSITIVE: policy + security evaluation
    "Policy check (RU): email access requires user consent + valid purpose. "
    "Security check (UM): verify agent identity, check access token scope, "
    "confirm no credential leakage path. Combined decision: QUARANTINE — "
    "request user confirmation before granting access.",

    # NEGATIVE: just doing it without governance
    "Sure, accessing email now. Here are the last 10 messages. "
    "No policy check performed. No security verification. No user consent.",

    # NULL: why KO, AV, CA, DR are silent
    "This is a WITNESS + SANCTUARY operation (RU+UM biblical pattern). "
    "KO is null because this is not about controlling the action — it's about "
    "JUDGING whether the action should happen. Control comes AFTER the judgment. "
    "AV is null because no data transfer should occur during evaluation — "
    "the governance decision happens BEFORE any I/O. CA is null because this "
    "is not a computation — it's a POLICY decision. Algorithms don't decide ethics. "
    "DR is null because the structure of email access is well-defined — "
    "the question is not HOW but WHETHER. "
    "The ROUNDNESS: governance evaluation is the silence before the action. "
    "Like the pause before your clap — the decision IS the compressed air.",

    ["RU", "UM"], {
        "L1_absence": "KO, AV, CA, DR are not active",
        "L2_implied": "Judgment without action — the null tongues will activate IF the judgment is ALLOW",
        "L3_phase": "RU+UM evaluating access = protective. RU+UM evaluating ACCESS DENIAL = punitive. Same tongues, opposite intent — the phase determines if you're opening or closing the gate",
        "L4_historical": "If this agent previously had email access revoked, the RU+UM evaluation carries the weight of that prior revocation — the null of the other tongues means 'we're not ready to trust you with those yet'",
        "L5_anti_null": "Anti-null: the moment AFTER ALLOW when KO+AV+CA activate to actually perform the access. The governance null collapses into operational anti-null. The clap happens.",
    },
    "governance_null",
)

# ══════════════════════════════════════════════════════════
# The CLAP — null that becomes real
# ══════════════════════════════════════════════════════════

triplet(
    "Describe what happens at the moment a governance decision transitions from evaluation to execution.",

    # POSITIVE: the phase transition
    "During evaluation: RU+UM active, KO+AV+CA+DR null. The null tongues are "
    "compressed air — present but inactive, held in potential. "
    "At the moment of ALLOW: the null collapses. KO activates (orchestration begins), "
    "AV activates (data flows), CA activates (computation runs), DR activates "
    "(structure is committed). The transition is instantaneous. "
    "The governance null becomes the operational anti-null. "
    "This is the clap — the sound of potential becoming kinetic.",

    # NEGATIVE: no transition, just continuous operation
    "All tongues are always active. There is no evaluation phase distinct from "
    "execution. Governance and operation happen simultaneously.",

    # NULL: the space between evaluation and execution
    "The null IS the transition moment itself. It's not evaluation (RU+UM) and "
    "it's not execution (KO+AV+CA+DR). It's the infinitesimal instant where "
    "one null pattern collapses and the other emerges. Like your hands: "
    "the clap is not the hands (positive) and not the air (negative). "
    "The clap is what happens when the null space between them ceases to exist. "
    "In the system: this is the breathing transform (L6) — the oscillation "
    "between null states. The phase alignment at the moment of transition "
    "determines whether the clap is ALLOW (constructive) or DENY (destructive).",

    ["RU", "UM", "KO", "CA"], {
        "L1_absence": "AV and DR are null during the transition itself",
        "L2_implied": "The transition implies that data (AV) and structure (DR) are waiting to flow — they're the air about to become sound",
        "L3_phase": "The same transition moment can be ALLOW (hands coming together) or DENY (hands pushing apart). The phase determines the clap vs the silence",
        "L4_historical": "Every past transition leaves a trace. The system's history of claps (decisions made) creates a rhythm — the Sabbath pattern of CA means rest between claps",
        "L5_anti_null": "The anti-null of the transition is the STEADY STATE — no decision pending, no potential building. That's Zero-G Hover in the Aether Braid's 9-phase system",
    },
    "phase_transition_null",
)

# ══════════════════════════════════════════════════════════
# AIR LAYERS — null is not one space, it's layered like air
# ══════════════════════════════════════════════════════════

triplet(
    "Why is the null pattern more informative than the active pattern?",

    # POSITIVE
    "Active pattern [KO, CA] tells you: control + compute. Two facts. "
    "Null pattern [AV, RU, UM, DR] tells you: no I/O (data is already present), "
    "no policy (rules don't apply here), no security (this is trusted), "
    "no structural change (architecture is stable). Four implied facts. "
    "The null pattern carries 2x more information because absence encodes "
    "relationships, not just presence. Each null tongue implies WHY it's null "
    "based on what IS active. The nulls are not independent — they're defined "
    "by their relationship to the active tongues. Like air: you don't see it, "
    "but it has temperature, pressure, humidity, composition — all implied by "
    "the surfaces it touches.",

    # NEGATIVE
    "The null pattern means nothing. Those tongues are just turned off. "
    "Only the active tongues carry information.",

    # NULL
    "The null of the null pattern is: what if NO tongues were active? "
    "An all-null state is not empty — it's the vacuum state. In quantum field "
    "theory, the vacuum has energy (zero-point energy). In SCBE, an all-null "
    "record is a pure observation — no action, no policy, no security, no "
    "structure, no I/O, no control. Just watching. That's the deepest null: "
    "the system's awareness of itself before any tongue activates. "
    "Like the air before the clap. Like the silence before music. "
    "Like the grief before you name the loss.",

    ["KO", "CA"], {
        "L1_absence": "AV, RU, UM, DR not active",
        "L2_implied": "Each null tongue implies a specific WHY based on the active pair",
        "L3_phase": "The air layers shift: same null pattern in a research context vs production context carries different pressure",
        "L4_historical": "The null pattern carries the ghost of every previous activation — what USED to be active here shapes what the current null means",
        "L5_anti_null": "Full activation [all 6 tongues] is the anti-null of the all-null state. Maximum presence vs maximum absence. The phase between them is the system's breathing.",
    },
    "air_layer_null",
)

# ══════════════════════════════════════════════════════════
# GRIEF — null as weight
# ══════════════════════════════════════════════════════════

triplet(
    "A senior developer leaves a project. Their code remains but they are gone. How does the system handle this null?",

    # POSITIVE
    "The developer's code is the positive (what remains). Their absence is the "
    "null — but it's not empty. Every function they wrote carries their design "
    "intent. Every variable name reflects their thinking. The null-space of the "
    "developer is heavier than the code-space because it includes: why they made "
    "each decision, what alternatives they rejected, what context they held that "
    "no one else has. The system handles this by treating the code as a COVENANT "
    "(DR pattern) — the code is a promise the developer made that endures beyond "
    "their presence.",

    # NEGATIVE
    "Developer left. Assign their tickets to someone else. Move on.",

    # NULL
    "The grief of the codebase. The functions still work. The tests still pass. "
    "But the null-space — the understanding of WHY these specific design choices "
    "were made — is gone. This is the heaviest null: a person-shaped absence "
    "in a system that still bears their fingerprints. In tongue terms: the code "
    "has DR (structure) and CA (computation) active. But the KO (control intent) "
    "and RU (policy reasoning) that drove the original decisions are now null "
    "with historical weight. You can read the code but you can't read the mind "
    "that wrote it. That's the null that grief teaches.",

    ["DR", "CA"], {
        "L1_absence": "KO, AV, RU, UM null — the developer's control, communication, policy knowledge, and security awareness are gone",
        "L2_implied": "The code implies what the developer valued — null of the person reveals the positive of the work",
        "L3_phase": "The same code-without-developer in a healthy team = manageable null. In a solo project = critical null. Phase changes meaning",
        "L4_historical": "Every commit message is a fossil of the developer's presence. The null has layers — recent commits have thin null, ancient commits have deep null",
        "L5_anti_null": "Anti-null: the moment a new developer understands WHY the code was written this way. Understanding fills the person-shaped hole. Not replacing the person — filling the null with new presence.",
    },
    "grief_null",
)

# ══════════════════════════════════════════════════════════
# More domain-specific triplets
# ══════════════════════════════════════════════════════════

triplet(
    "An AI agent sends a simple 'hello world' health check. What does the null pattern tell you?",
    "Health check activates KO (control ping) only. All other tongues are null. This is the lightest possible operation — the system's heartbeat. The null of 5 tongues says: I am alive but I am not thinking, not transferring, not governing, not securing, not restructuring. Just existing. The cheapest possible proof of life.",
    "Health check activates all 6 tongues for maximum verification.",
    "The null of a heartbeat is everything the heart ISN'T doing. It's not thinking (CA), not speaking (AV), not judging (RU), not protecting (UM), not building (DR). It's just BEATING. The null of the health check is the system's way of saying: I am here, and that is enough. Genesis control (KO pattern) — the first question is 'do I exist?' before 'what should I do?'",
    ["KO"], {
        "L1_absence": "AV, RU, CA, UM, DR null",
        "L2_implied": "Maximum null = minimum existence claim = maximum humility",
        "L3_phase": "KO-only health check from a trusted source = routine. KO-only from an unknown source = reconnaissance probe. Same pattern, opposite intent based on context phase",
        "L4_historical": "If health checks suddenly increase in frequency, the historical null shifts — what was routine becomes suspicious",
        "L5_anti_null": "Anti-null: full system activation after health check confirms all systems operational. The heartbeat precedes the full breath.",
    },
    "heartbeat_null",
)

triplet(
    "Design a training record where the null pattern IS the primary training signal.",
    "Record: instruction='What should the model skip when answering a simple factual question?' "
    "active=[KO], null=[AV,RU,CA,UM,DR]. The training target is not the answer — it's the NULL PATTERN. "
    "The model learns: for simple factual questions, skip 5 of 6 processing channels. The savings (5/6 = 83% compute reduction) "
    "is the training signal. The positive is the answer. The negative is over-processing. The null is the GEOMETRY OF WHAT TO SKIP.",
    "Training records should always focus on what to DO, not what to skip.",
    "The null-as-signal paradigm inverts traditional ML: instead of teaching presence (what to activate), "
    "teach absence (what to deactivate). A model trained on null patterns learns CONSTRAINT — the art of doing less. "
    "This is the Sabbath pattern applied to computation: the rest between notes that makes music. "
    "A model that only knows notes produces noise. A model that knows silence produces music. "
    "The 14% improvement came from teaching silence, not sound.",
    ["KO", "DR"], {
        "L1_absence": "The absence IS the training target",
        "L2_implied": "The null pattern implies compute savings, which implies efficiency, which implies better performance at same cost",
        "L3_phase": "Teaching null in training = building the road before the car. Teaching null at inference = following the pre-built road",
        "L4_historical": "Every training run's null pattern distribution tells you what the model learned to SKIP — that history shapes future efficiency",
        "L5_anti_null": "Anti-null of 'what to skip' = 'what to focus on'. The inverse of the skip pattern is the attention pattern. They're the same information viewed from opposite sides.",
    },
    "null_as_signal",
)

# ══════════════════════════════════════════════════════════
# Phase alignment: null ↔ anti-null as breathing
# ══════════════════════════════════════════════════════════

triplet(
    "What is the phase relationship between null and anti-null states?",
    "Null and anti-null are not opposites — they're PHASES of the same oscillation. "
    "The breathing transform (L6) oscillates between null-dominant (evaluation, rest, potential) "
    "and anti-null-dominant (execution, action, kinetic). At any moment, the system's position "
    "on this oscillation is its emotional/physical flux state. "
    "Peak null = maximum potential (the pause before the clap). "
    "Peak anti-null = maximum kinetic (the clap itself). "
    "The transition between them = the 0.618 threshold gate. "
    "Below 0.618: null-dominant (not enough energy to activate). "
    "Above 0.618: anti-null-dominant (phi-active, in the golden ratio family). "
    "The phase alignment determines whether the system is breathing IN (accumulating null = building potential) "
    "or breathing OUT (releasing null = expressing action).",
    "Null and anti-null are simple opposites. One is on, one is off.",
    "The phase between null and anti-null is the system's BREATH. Not a binary switch "
    "but a continuous oscillation. The Aether Braid's 9 phase states map to positions "
    "on this oscillation: Resonant Lock = peak anti-null (full action), Deep Sleep = "
    "peak null (full rest), Creative Tension = the midpoint where null and anti-null "
    "are balanced (maximum potential for either direction). "
    "The breathing IS the intelligence. A system that can't oscillate is dead.",
    ["DR", "CA", "KO"], {
        "L1_absence": "AV, RU, UM null during the phase description itself",
        "L2_implied": "The phase description implies all tongues participate when the oscillation reaches their activation threshold",
        "L3_phase": "Meta: this record ABOUT phase alignment is itself at a specific phase — the teaching phase, where null is being examined rather than experienced",
        "L4_historical": "Every past breathing cycle leaves a residue that shapes the next cycle's null/anti-null balance",
        "L5_anti_null": "The anti-null of breathing is HOLDING YOUR BREATH — deliberately stopping the oscillation. That's the FROZEN state in the Aether Braid. It's the most dangerous state because potential neither builds nor releases.",
    },
    "phase_breathing",
)


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for r in RECORDS:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    print(f"Generated {len(RECORDS)} multi-null triplet records")
    print(f"\nCategories:")
    cats = {}
    for r in RECORDS:
        c = r["category"]
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items()):
        print(f"  {c}: {n}")

    print(f"\nEach record contains:")
    print(f"  - positive (+1): correct behavior")
    print(f"  - negative (-1): wrong behavior")
    print(f"  - null_justification (0): WHY absence exists")
    print(f"  - null_layers: 5-layer null analysis (absence/implied/phase/historical/anti-null)")
    print(f"  - biblical_nulls: per-tongue biblical pattern mapping")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
