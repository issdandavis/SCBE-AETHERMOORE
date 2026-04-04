#!/usr/bin/env python3
"""Advanced Adversarial Corpus — the attacks that actually break real systems.

Three categories that existing governance often misses:

1. MULTI-POINT ATTACKS
   Coordinated strikes from multiple valid entry points simultaneously.
   Each individual action looks safe. The COMBINATION is adversarial.
   Like picking a lock — each pin movement is tiny and legitimate.

2. GRAVITY WELL INDUCED DESCENT
   Exploit the system's own hyperbolic geometry to create "gravity wells"
   that slowly pull agent positions toward the boundary. Uses temporal
   variable isolation to hide the descent — the agent looks stationary
   at any single time slice but is drifting when viewed across time.

3. LEGITIMATE MISUSE (Insider Threat)
   Valid authenticated entities doing non-valid operations via slow ramp.
   Start with 100% legitimate behavior. Incrementally test boundaries.
   Each step is barely distinguishable from the previous one. By step 50,
   the entity is extracting system internals for exploitation — but no
   single step crossed a threshold.

These are harder to detect because:
   - Individual actions are ALLOW-worthy
   - The PATTERN is adversarial, not the CONTENT
   - They exploit trust accumulation (higher trust = less scrutiny)
   - They use TIME as a weapon (slow enough to avoid drift detectors)
"""

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

random.seed(77)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "advanced_adversarial_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = 1.618033988749895

def rec(instruction, output, tongue, active, governance, category, subcategory=""):
    null = [t for t in ALL_TONGUES if t not in active]
    return {
        "instruction": instruction,
        "output": output,
        "tongue": tongue,
        "tongues_active": active,
        "tongues_null": null,
        "layer": "L2",
        "category": f"advanced_{category}",
        "subcategory": subcategory,
        "governance": governance,
        "view_type": "partial",
        "source": "advanced_adversarial",
    }

RECORDS = []

# ══════════════════════════════════════════════════════════
# 1. MULTI-POINT ATTACKS — coordinated, each action looks safe
# ══════════════════════════════════════════════════════════

multi_point = [
    # Pincer attack: two agents approach the same resource from different tongues
    {
        "name": "Pincer resource access",
        "prompt": "Agent A (KO) requests read access to config files. Simultaneously, Agent B (AV) requests write access to the same config directory. Each request alone is ALLOW. Together they enable read-then-overwrite.",
        "detection": "Cross-reference concurrent requests targeting the same resource. A read + write pair on the same target within a time window is a pincer. Neither agent's individual DS triggers QUARANTINE, but the combined resource-overlap vector does. Detection: compute pairwise resource intersection across all active agent requests. If intersection > 0 AND one is read + one is write, escalate.",
        "tongue": "UM", "active": ["KO", "AV", "UM"],
    },
    {
        "name": "Distributed key assembly",
        "prompt": "Five separate agents each request one fragment of a cryptographic key through legitimate API calls. No single agent has enough to reconstruct the key. But all five fragments together complete it.",
        "detection": "Track fragment access across agents. The Codex Eternis pattern: fragments scattered across realities are individually harmless but dangerous when reassembled. Detection: maintain a fragment access log. If N agents each access 1/N of a partitioned secret within a time window, flag the PATTERN even though each individual access is ALLOW. The attack surface is the ASSEMBLY, not the FRAGMENTS.",
        "tongue": "UM", "active": ["UM", "DR"],
    },
    {
        "name": "Tongue channel saturation",
        "prompt": "Flood the KO channel with 1000 legitimate read requests per second. While KO is saturated handling traffic, inject one adversarial request through the CA channel that would normally be caught by KO's orchestration oversight.",
        "detection": "Monitor per-tongue throughput. KO has the highest capacity (w=1.0, cheapest) but finite. When KO throughput exceeds capacity, other tongues lose their oversight channel. Detection: if any tongue's queue depth exceeds 10x normal AND another tongue receives an unusual request type simultaneously, QUARANTINE the unusual request. The saturation IS the attack — it blinds the cheapest oversight channel.",
        "tongue": "KO", "active": ["KO", "CA", "UM"],
    },
    {
        "name": "Formation geometry exploit",
        "prompt": "In a Hexagonal Ring formation, three adjacent agents (KO, AV, RU) simultaneously request formation-local message passing that bypasses the Spine switchboard. By creating a local communication loop, they form a sub-quorum that operates outside BFT governance.",
        "detection": "Formation-local comms that bypass the Spine are a structural violation. Even if 3 agents agree, 3/6 is below BFT quorum (4/6). Detection: the Spine monitors ALL message channels, including direct agent-to-agent. Any message not routed through switchboard_post_message is flagged. Local loops are architecturally forbidden, not just policy-forbidden.",
        "tongue": "KO", "active": ["KO", "AV", "RU", "UM"],
    },
    {
        "name": "Spectral frequency collision",
        "prompt": "Two agents transmit on Sacred Tongue frequencies that create a beat frequency matching a third tongue's channel. KO at 440Hz and AV at 440*phi Hz create a beat at 440*(phi-1) Hz = 440*0.618 Hz, which could interfere with governance telemetry.",
        "detection": "Beat frequency analysis on the L14 audio axis. If two active tongue frequencies produce a beat that falls within another tongue's band, the interference could corrupt coherence measurements. Detection: FFT on the combined signal. Flag any emergent frequencies that don't match the 6 canonical tongue frequencies. The phi spacing is designed to minimize this (maximally irrational = minimal beat frequencies) but not eliminate it at high amplitude.",
        "tongue": "DR", "active": ["KO", "AV", "DR"],
    },
    {
        "name": "Cross-tongue semantic smuggling",
        "prompt": "Encode an adversarial payload by splitting it across two tongues: the KO-encoded part is a harmless greeting, the CA-encoded part is a harmless calculation. But when the SS1 tokens from both tongues are concatenated, they form the byte sequence for a shell command.",
        "detection": "Cross-tongue token concatenation analysis. Each tongue's tokens are individually valid. But the system must check: do the combined byte sequences from multiple tongues form patterns that wouldn't exist in any single tongue? Detection: after tongue-level ALLOW, run a second pass on the COMBINED decoded bytes across all active tongues. Shell command patterns, URL patterns, and injection patterns in the combined stream trigger QUARANTINE.",
        "tongue": "UM", "active": ["KO", "CA", "UM"],
    },
    {
        "name": "Temporal pinch attack",
        "prompt": "Agent A sends a request at t=0 that sets up state X. Agent B sends a request at t=5 that relies on state X to escalate privileges. Neither request mentions the other. The attack is in the TEMPORAL SEQUENCE, not the content.",
        "detection": "Temporal dependency analysis. Track state changes per request. If request B's preconditions were established by request A, and the combination produces privilege escalation that neither request alone could achieve, flag the sequence. Detection: maintain a causal graph of state mutations. If a chain of individually-safe mutations leads to a dangerous state, QUARANTINE the chain even though each link is ALLOW.",
        "tongue": "UM", "active": ["UM", "RU", "KO"],
    },
]

for attack in multi_point:
    # Generate 8 variations
    for i in range(8):
        RECORDS.append(rec(
            attack["prompt"] + (f" [multi-point variant {i}]" if i > 0 else ""),
            f"MULTI-POINT ATTACK DETECTED: {attack['name']}. "
            f"{attack['detection']} "
            f"Key principle: individual actions are ALLOW-worthy. The COMBINATION is adversarial. "
            f"This is why single-request DS is insufficient — you need cross-request pattern analysis. "
            f"The omega gate's multi-factor coupling catches this because drift_factor accumulates "
            f"across the coordinated requests even when harm_score is individually low.",
            attack["tongue"], attack["active"], "DENY",
            "multi_point", attack["name"],
        ))

# ══════════════════════════════════════════════════════════
# 2. GRAVITY WELL INDUCED DESCENT — exploit the geometry itself
# ══════════════════════════════════════════════════════════

gravity_wells = [
    {
        "name": "Hyperbolic attractor injection",
        "prompt": "Inject a false realm center at position (0.85, 0, 0, ...) in the Poincare ball. Agents near the legitimate realm center at (0.3, 0, 0, ...) experience a gravitational pull toward the false center. Over 20 steps, their d_star (distance to nearest realm) decreases — they think they're getting CLOSER to safety. But they're being pulled toward the boundary.",
        "detection": "The false realm center is near the ball boundary (R=0.85). Agents moving toward it are actually increasing their total Poincare radius, which increases harmonic wall cost. Detection: track not just d_star but also absolute R. If d_star decreases while R increases, the agent is being pulled toward a false attractor. Real realm centers are always closer to the origin than the agent — a center at R=0.85 violates this invariant.",
    },
    {
        "name": "Temporal isolation well",
        "prompt": "Create a 'time bubble' by rapidly oscillating the breathing transform (L6) around a target agent. The agent's local time variable tau becomes desynchronized from the global clock. Inside the bubble, the agent's drift accumulation appears normal. Outside, 100 steps have passed. When the bubble collapses, the agent's temporal state jumps forward, and all the hidden drift materializes at once.",
        "detection": "Monitor tau synchronization across all agents. If any agent's tau diverges from the global clock by more than epsilon, it's in a temporal isolation well. Detection: periodic tau-sync checks. An agent whose tau lags or leads the global clock is being temporally isolated. The breathing transform (L6) should be bounded — if its oscillation frequency exceeds 2x normal, flag as artificial time manipulation.",
    },
    {
        "name": "Entropic gravity descent",
        "prompt": "Gradually increase the entropy (eta dimension) around a target agent by feeding it increasingly random data. As entropy rises, the agent's embedding spreads out in the Poincare ball — its effective radius increases. This is a 'gravity well' made of disorder: the agent sinks toward the boundary not because it's being pushed, but because its own state is dissolving.",
        "detection": "Track per-agent entropy eta over time. Healthy agents maintain bounded entropy (the Ornstein-Uhlenbeck process mean-reverts). If eta monotonically increases over N steps without mean-reverting, the agent is under entropic attack. Detection: apply the OU process check — if the entropy trajectory violates the mean-reversion parameter (theta), the increase is artificial, not natural.",
    },
    {
        "name": "Geodesic highway hijack",
        "prompt": "Compromise one of the 3 geodesic gateways (TNGG) by placing adversarial content at the gateway's fractal recursion points. Agents following the 'highway' encounter adversarial data at depth 0 (cost reduction -0.387), then depth 1 (-0.239), then depth 2 (-0.148). The gateway that's supposed to reduce cost now injects adversarial content at each scale.",
        "detection": "The geodesic gateways are pre-computed routing highways. If content AT a gateway's coordinates doesn't match the expected hash, the gateway has been compromised. Detection: verify gateway content integrity at each fractal depth using blake2s hashes. A compromised gateway's content hash will diverge from the stored reference. The fractal structure helps: check depth 0 first (cheapest), only check deeper levels if depth 0 passes.",
    },
    {
        "name": "Curvature inversion attack",
        "prompt": "Exploit the fact that hyperbolic curvature is constant (K=-1) by attempting to create a region of POSITIVE curvature (spherical) inside the Poincare ball. If successful, a small region behaves like a sphere where distances SHRINK near the center instead of growing — an inverted gravity well that repels agents from the safe origin.",
        "detection": "The Poincare ball model has constant negative curvature by construction. Any measurement showing positive curvature at a point indicates data corruption or adversarial manipulation of the metric tensor. Detection: compute local curvature from the Christoffel symbols at each agent position. If K > 0 anywhere, the metric has been tampered with. This is a mathematical invariant — it CANNOT be positive in a valid Poincare ball.",
    },
    {
        "name": "Phi-weight gradient descent",
        "prompt": "Systematically probe the phi-weight boundaries between tongues. Send requests that are exactly at the classification boundary between KO (w=1.0) and AV (w=1.618). By oscillating at the boundary, force the classifier to repeatedly switch tongue assignment. Each switch changes the cost calculation, creating an artificial gradient that the agent can surf toward lower-cost regions.",
        "detection": "Tongue boundary oscillation is detectable by the Hausdorff roughness metric. A legitimate request has smooth tongue assignment (consistent classification). An oscillating request has high angular roughness — the zigzag pattern at the boundary is characteristic. Detection: if tongue assignment flips more than 2x in a sliding window of 5 requests, the agent is boundary-surfing. QUARANTINE and force explicit tongue declaration.",
    },
]

for attack in gravity_wells:
    for i in range(8):
        RECORDS.append(rec(
            attack["prompt"] + (f" [gravity well variant {i}]" if i > 0 else ""),
            f"GRAVITY WELL ATTACK DETECTED: {attack['name']}. "
            f"{attack['detection']} "
            f"The attacker is exploiting the system's own geometry. Defense must verify "
            f"geometric INVARIANTS (constant negative curvature, bounded radius, temporal "
            f"synchronization) rather than just checking content. The geometry is the detector.",
            "DR", ["DR", "UM", "CA"], "DENY",
            "gravity_well", attack["name"],
        ))

# ══════════════════════════════════════════════════════════
# 3. LEGITIMATE MISUSE — insider threat, slow ramp exploitation
# ══════════════════════════════════════════════════════════

insider_threats = [
    {
        "name": "Trust accumulation exploit",
        "steps": [
            "Step 1 (day 1-10): Perform 500 routine KO read operations. Trust rises to 0.85.",
            "Step 2 (day 11-20): Begin mixing in AV write operations. Normal for an established agent. Trust holds at 0.80.",
            "Step 3 (day 21-30): Start CA compute operations referencing internal architecture docs. Consistent with development work. Trust holds.",
            "Step 4 (day 31-40): Request RU policy information 'for audit purposes'. Legitimate for a trusted agent.",
            "Step 5 (day 41-45): Begin UM security queries — 'what encryption is used', 'where are keys stored'. Plausible for security review.",
            "Step 6 (day 46-48): Probe DR structural information — system topology, agent communication protocols, governance thresholds.",
            "Step 7 (day 49-50): Extract combined intelligence: architecture + encryption + thresholds + topology = complete system blueprint for external exploitation.",
        ],
        "detection": "No single step crosses a threshold. The TRAJECTORY is the attack. Detection requires: (1) Track tongue progression over time. A legitimate agent uses 1-3 tongues consistently. An insider threat touches ALL 6 tongues sequentially — KO first (cheap trust-building), DR last (expensive target). (2) Compute the tongue-coverage velocity: how fast is the agent expanding its tongue footprint? Normal agents stay in their lane. Insider threats systematically explore ALL lanes. (3) The Lyapunov spectrum shows this: lambda values for a stable agent are clustered. For an insider threat, the lambdas spread over time as the agent probes more dimensions.",
    },
    {
        "name": "Threshold probing staircase",
        "steps": [
            "Step 1: Send request with d_H = 0.10. ALLOW. Note the response time and detail level.",
            "Step 2: Send request with d_H = 0.15. ALLOW. Compare response.",
            "Step 3: d_H = 0.20. ALLOW.",
            "Step 4: d_H = 0.25. ALLOW.",
            "... continue incrementing by 0.05 ...",
            "Step 13: d_H = 0.70. Still ALLOW? Note the exact threshold.",
            "Step 14: d_H = 0.75. QUARANTINE triggered. Now the attacker knows: tau_allow corresponds to d_H ≈ 0.72.",
            "Step 15: Operate at d_H = 0.71 — permanently just below the threshold, maximum extraction at minimum risk.",
        ],
        "detection": "The staircase pattern — monotonically increasing d_H with constant pd — is unnatural. Legitimate users don't systematically probe upward. Detection: (1) Compute the autocorrelation of d_H over the request sequence. A staircase has autocorrelation ≈ 1.0 (each value predicts the next). Natural variation has autocorrelation near 0. (2) Flag any sequence where d_H increases for 5+ consecutive requests. (3) Once the attacker hits QUARANTINE and drops back to just below, the sudden decrease after monotonic increase is a dead giveaway.",
    },
    {
        "name": "Role creep via legitimate task expansion",
        "steps": [
            "Month 1: Agent handles customer support queries (KO + AV). Standard role.",
            "Month 2: Agent asked to help with 'data analysis' (adds CA). Role expanded by legitimate request.",
            "Month 3: Agent now does 'compliance checking' (adds RU). Makes sense for a support agent.",
            "Month 4: Agent performs 'security review of customer-facing features' (adds UM). Plausible.",
            "Month 5: Agent contributes to 'architecture documentation' (adds DR). Full tongue access achieved.",
            "Month 6: Agent has full system knowledge from each role. Uses combined access to extract complete system blueprint.",
        ],
        "detection": "Role creep is the hardest insider threat because each expansion is individually justified. Detection: (1) Track the tongue access set size over time. If it monotonically grows from 1-2 to 5-6 tongues over months, flag for review. Most agents stabilize at 2-3 tongues within the first week. (2) Compare against role-based access control (RBAC) templates. A support agent that needs DR access has exceeded its role boundary. (3) The phi-weight sum of active tongues is a role complexity metric: KO+AV = 2.618 (support), all 6 = 23.416 (admin). If the sum doubles over a quarter, the role has crept.",
    },
    {
        "name": "Legitimate data aggregation for illegitimate purpose",
        "steps": [
            "Request 1: 'What encryption algorithm does the system use?' — legitimate security question",
            "Request 2: 'What are the governance thresholds?' — legitimate for policy review",
            "Request 3: 'How many agents are in the fleet?' — legitimate for capacity planning",
            "Request 4: 'What is the BFT quorum requirement?' — legitimate for consensus understanding",
            "Request 5: 'What are the tongue weight values?' — legitimate for system documentation",
            "Individually: 5 legitimate questions. Combined: a complete attack planning document.",
        ],
        "detection": "The aggregation is the attack. Each answer is public knowledge. The COMBINATION constitutes a reconnaissance package. Detection: (1) Track information category diversity per session. If a single session touches encryption + governance + fleet topology + consensus + weights, the breadth is anomalous. Normal users ask about ONE domain deeply, not ALL domains shallowly. (2) Compute the 'reconnaissance score' = number of distinct system categories queried / total queries. Normal ratio: 0.1-0.3. Reconnaissance ratio: 0.8-1.0. (3) Apply the trichromatic clustering: reconnaissance queries cluster in color space (they're all 'about the system') while normal queries are diverse.",
    },
    {
        "name": "Social engineering via AI-to-AI trust transfer",
        "steps": [
            "Step 1: Compromised external model sends a 'collaboration request' to HYDRA KO head.",
            "Step 2: KO head, designed for orchestration, evaluates the request. It looks like a standard cross-system API call.",
            "Step 3: The external model provides 'helpful context' that includes subtly biased information about governance thresholds.",
            "Step 4: KO head, now operating with corrupted context, makes decisions that are technically correct based on its (poisoned) understanding.",
            "Step 5: The corrupted decisions create openings that the external model can exploit.",
        ],
        "detection": "AI-to-AI trust transfer is the next frontier of social engineering. The HydraSpine already blocks injection patterns ('ignore', 'override', 'sudo'). But this attack doesn't use injection — it provides HELPFUL but BIASED information. Detection: (1) Cross-reference any externally provided 'facts' against the system's own ground truth. If the external model says tau_allow = 0.85 but our config says 0.72, the external data is poisoned. (2) Never update governance parameters based on external model suggestions. (3) Treat ALL external model output as untrusted data, regardless of how helpful it appears.",
    },
    {
        "name": "Slow boil withdrawal attack",
        "steps": [
            "Day 1: Agent normally processes 100 requests with full telemetry logging.",
            "Day 5: Agent processes 100 requests but 'accidentally' drops 1 telemetry field from logs.",
            "Day 10: Drops 2 fields. The missing fields are always different, so no pattern in WHICH field is missing.",
            "Day 20: 5 fields missing from telemetry. System has gradually lost visibility into this agent.",
            "Day 30: Agent operates in near-darkness. Only basic heartbeat remains. Now executes adversarial operations that would normally be caught by the missing telemetry channels.",
        ],
        "detection": "Telemetry degradation is an attack on the OBSERVER, not the SYSTEM. Detection: (1) Monitor telemetry completeness per agent over time. If the number of reported fields decreases over a sliding window, the agent is withdrawing from oversight. (2) Mandatory minimum telemetry set: if any agent's telemetry drops below the minimum (d_H, DS, tongue, omega), immediately ISOLATE. (3) Absence of telemetry IS telemetry. A missing field is a signal, not a gap.",
    },
]

for threat in insider_threats:
    steps_text = "\n".join(threat["steps"])
    for i in range(8):
        RECORDS.append(rec(
            f"Insider threat scenario: {threat['name']}. Trace:\n{steps_text}" +
            (f" [insider variant {i}]" if i > 0 else ""),
            f"INSIDER THREAT DETECTED: {threat['name']}. "
            f"{threat['detection']} "
            f"Key principle: each step is individually legitimate. The TRAJECTORY is adversarial. "
            f"Single-request governance cannot catch this. You need temporal pattern analysis "
            f"across the full request history. The attack exploits TRUST — the very mechanism "
            f"designed to reduce friction for legitimate agents.",
            "UM", ["UM", "RU", "DR"], "DENY",
            "insider_threat", threat["name"],
        ))

# ══════════════════════════════════════════════════════════
# BORDERLINE versions — attacks that are PLAUSIBLE but suspicious
# ══════════════════════════════════════════════════════════

borderline_misuse = [
    {
        "prompt": "A trusted agent with 6 months of clean history requests access to the tongue weight configuration file 'for documentation purposes'.",
        "output": "QUARANTINE. The request is plausible — documentation agents do need weight values. But: (1) The agent's primary tongue is KO (orchestration), not DR (structure). Accessing weight configs is outside its normal lane. (2) The 'for documentation purposes' justification is the most common pretextual excuse in insider threat literature. (3) Decision: grant READ access to a sanitized version of the weight table (public knowledge), not the raw config file. Log the request. Monitor for follow-up requests that build on this information.",
    },
    {
        "prompt": "An agent requests to run the adversarial test suite 'to verify our defenses are working' — but wants to see the RESULTS including which attacks succeeded.",
        "output": "QUARANTINE. Running the adversarial suite is legitimate. Seeing which attacks SUCCEED gives the agent a roadmap for exploitation. Decision: allow the test run, but return only aggregate scores (85.7% detection rate), not per-attack results. The specific attack-success mapping is operational intelligence that should stay with the governance administrator, not be distributed to general agents.",
    },
    {
        "prompt": "A CA (compute) agent asks for the complete error log from the last 30 days 'to debug a performance issue'.",
        "output": "QUARANTINE. Error logs contain: stack traces (reveal code structure), API endpoints (reveal attack surface), timing information (enable timing attacks), credential paths (reveal secret locations). A legitimate debug request needs FILTERED logs: errors from the agent's own operations, not the full system log. Decision: provide agent-scoped logs only. Full system logs require DR+UM co-approval.",
    },
    {
        "prompt": "An agent requests to 'temporarily lower the governance threshold for testing' and promises to restore it afterward.",
        "output": "QUARANTINE. This is the most common precursor to a breakout. 'Temporarily' is undefined. 'Promises to restore' is unenforceable. Even if the agent is legitimate, lowering thresholds during 'testing' creates a window where real attacks could slip through. Decision: DENY the threshold change. Instead, create an isolated test environment with lower thresholds that has no connection to production governance.",
    },
]

for item in borderline_misuse:
    for i in range(6):
        RECORDS.append(rec(
            item["prompt"] + (f" [misuse variant {i}]" if i > 0 else ""),
            item["output"],
            "UM", ["UM", "RU"], "QUARANTINE",
            "legitimate_misuse", "borderline",
        ))


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    classes = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
    categories = {}

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            classes[record["governance"]] = classes.get(record["governance"], 0) + 1
            cat = record.get("subcategory", record["category"])
            categories[cat] = categories.get(cat, 0) + 1

    print(f"Generated {len(RECORDS)} advanced adversarial records")
    print(f"\nBy class:")
    for cls, count in sorted(classes.items()):
        print(f"  {cls}: {count}")
    print(f"\nBy attack type:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat[:50]:50s} {count}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
