#!/usr/bin/env python3
"""Generate SpaceTor network SFT training data from the 4 SpaceTor modules.

Covers:
  - 3D spatial pathfinding with trust-weighted relay selection
  - Langues Weighting System (Layer 3) trust scoring across 6 Sacred Tongues
  - Hybrid quantum/classical onion encryption
  - Combat multipath redundancy with disjoint paths
  - Fleet multi-agent browser crawl coordination

Output: training-data/sft/spacetor_network_sft.jsonl
"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "training-data" / "sft" / "spacetor_network_sft.jsonl"

SYSTEM = (
    "You are Polly, an AI assistant trained on the SCBE-AETHERMOORE framework. "
    "You have deep knowledge of the SpaceTor network stack: 3D spatial routing, "
    "Langues trust scoring, hybrid quantum/classical encryption, and combat "
    "multipath redundancy."
)


def rec(user: str, assistant: str, tags: list[str]) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tags": tags,
    }


records: list[dict] = []

# ── Space Tor Router ──────────────────────────────────

records.append(rec(
    "What is the SpaceTor router and how does it differ from standard Tor?",
    "SpaceTor is a 3D spatial pathfinding system for relay networks. Standard Tor "
    "selects relay nodes randomly from a directory. SpaceTor adds two critical "
    "dimensions:\n\n"
    "1. **Physical distance** — nodes have 3D coordinates (in AU from Sol), and "
    "light-lag is a real constraint in space networks\n"
    "2. **Trust scoring** — uses the Langues Weighting System (Layer 3) with 6D "
    "trust vectors across the Sacred Tongues (KO/AV/RU/CA/UM/DR)\n\n"
    "The routing algorithm balances anonymity (randomness) against latency "
    "(physical distance) and trust. It selects a 3-hop path: entry (high trust, "
    "close to origin), exit (close to destination), and middle (maximum entropy "
    "to break correlation).\n\n"
    "Key formula for weighted node selection:\n"
    "Cost = (Distance * distWeight) - (Trust * (1 - distWeight))\n\n"
    "Entry nodes get 70% weight on distance, exit nodes get 80%.",
    ["spacetor", "routing", "architecture"],
))

records.append(rec(
    "How does SpaceTor select relay nodes for a 3-hop path?",
    "SpaceTor builds a 3-hop path through these steps:\n\n"
    "1. **Filter** — exclude nodes with trust < minTrust (default 60) or load > 0.9\n"
    "2. **Entry node** — requires trust > 80 (Guard Node). Selected by weighted cost "
    "with 70% emphasis on proximity to origin\n"
    "3. **Exit node** — selected with 80% weight on proximity to destination\n"
    "4. **Middle node** — chosen randomly from remaining candidates (not entry or exit) "
    "for maximum entropy. Random selection breaks correlation between entry and exit\n\n"
    "If trustVector (6D) is available on a node, SpaceTor uses the Langues Metric "
    "Tensor for scoring. Otherwise it falls back to the legacy trustScore (0-100). "
    "The conversion is: legacy = (1 - L_normalized) * 100, because low Langues metric "
    "= high trust.",
    ["spacetor", "routing", "path-selection"],
))

records.append(rec(
    "What is the weighted node selection formula in SpaceTor?",
    "The weighted cost for selecting a relay node is:\n\n"
    "Cost = (Distance * distWeight) - (Trust * (1 - distWeight))\n\n"
    "Where:\n"
    "- Distance = Euclidean 3D distance in AU: sqrt((x2-x1)^2 + (y2-y1)^2 + (z2-z1)^2)\n"
    "- Trust = node trust score (0-100), from Langues metric or legacy\n"
    "- distWeight = how much to prioritize proximity (0.0-1.0)\n\n"
    "Lower cost = better node. The algorithm reduces over all candidates to find "
    "the minimum-cost node.\n\n"
    "Entry guard nodes use distWeight=0.7 (closer to origin preferred).\n"
    "Exit nodes use distWeight=0.8 (closer to destination preferred).\n"
    "Middle nodes are chosen randomly (not by cost) to maximize entropy.",
    ["spacetor", "routing", "formula"],
))

# ── Trust Manager (Langues Weighting System) ──────────

records.append(rec(
    "What is the Langues Weighting System used in SpaceTor trust scoring?",
    "The Langues Weighting System (LWS) implements Layer 3 of the SCBE pipeline. "
    "It computes trust scores across the Six Sacred Tongues:\n\n"
    "L(x,t) = sum(l=1 to 6) nu_l * w_l * exp[beta_l * (d_l + sin(omega_l*t + phi_l))]\n\n"
    "Where:\n"
    "- x = 6D trust vector (one value per Sacred Tongue, in [0,1])\n"
    "- w_l = harmonic weights (golden ratio scaling: 1.0, 1.125, 1.25, 1.333, 1.5, 1.667)\n"
    "- beta_l = growth coefficients (amplification)\n"
    "- d_l = |x_l - mu_l| = deviation from ideal trust value\n"
    "- omega_l = temporal frequencies\n"
    "- phi_l = phase offsets (2*pi*k/6)\n"
    "- nu_l = dimension flux coefficients (breathing)\n\n"
    "The metric is normalized: L_N = L(x,t) / L_max, where L_max occurs at d_l=1, sin=1.\n\n"
    "Trust levels: HIGH (L_N <= 0.3), MEDIUM (0.3-0.5), LOW (0.5-0.7), CRITICAL (> 0.7).",
    ["spacetor", "trust", "langues", "formula"],
))

records.append(rec(
    "How are the Sacred Tongue dimensions used in SpaceTor trust vectors?",
    "Each node in the SpaceTor network has a 6D trust vector, one dimension per "
    "Sacred Tongue:\n\n"
    "- KO (Koraelin) — Intent trust: does the node's behavior match stated intent?\n"
    "- AV (Avali) — Context trust: is the node's metadata consistent?\n"
    "- RU (Runethic) — Binding trust: are the node's connections valid?\n"
    "- CA (Cassisivadan) — Compute trust: does the node compute correctly?\n"
    "- UM (Umbroth) — Security trust: is the node's encryption sound?\n"
    "- DR (Draumric) — Structural trust: is the node's architecture stable?\n\n"
    "Each value is in [0,1] where 0.5 = neutral (ideal). Deviation from 0.5 in any "
    "dimension increases the Langues metric exponentially, lowering trust. The "
    "exponential amplification means a node can't hide malicious intent in one "
    "tongue by being trusted in others — the cost is multiplicative, not additive.",
    ["spacetor", "trust", "sacred-tongues"],
))

records.append(rec(
    "What is the gradient field in SpaceTor trust scoring?",
    "The trust manager computes the gradient nabla L for descent-based trust updates:\n\n"
    "dL/dx_l = nu_l * w_l * beta_l * exp[beta_l * (d_l + sin(omega_l*t + phi_l))] * sign(x_l - mu_l)\n\n"
    "This gradient tells you:\n"
    "- Which tongue dimension is contributing most to distrust\n"
    "- The direction to move the trust vector to reduce the metric\n"
    "- How steeply trust degrades in each dimension\n\n"
    "The gradient is used for anomaly detection: if the gradient suddenly spikes in "
    "one dimension, it means the node's behavior shifted rapidly in that tongue. "
    "A 30%+ drop in trust score triggers an anomaly flag.",
    ["spacetor", "trust", "gradient", "formula"],
))

records.append(rec(
    "What are dimension flux coefficients in SpaceTor?",
    "Dimension flux coefficients (nu_l) control how much each Sacred Tongue "
    "participates in trust scoring. This is the 'breathing' mechanism:\n\n"
    "- nu_l = 1.0 — Full participation (polly mode)\n"
    "- 0.5 < nu_l < 1.0 — Partial participation (demi mode)\n"
    "- nu_l < 0.5 — Weak participation (quasi mode)\n\n"
    "Use cases:\n"
    "- During network startup, set all nu = 1.0 for full trust evaluation\n"
    "- During high-load periods, reduce less critical dimensions to speed scoring\n"
    "- During combat, boost UM (security) and KO (intent) while reducing others\n\n"
    "When flux coefficients change, the maximum possible score L_max is recomputed "
    "to maintain correct normalization.",
    ["spacetor", "trust", "flux", "breathing"],
))

# ── Hybrid Crypto ─────────────────────────────────────

records.append(rec(
    "How does SpaceTor's hybrid encryption work?",
    "SpaceTor uses a hybrid encryption system that supports both quantum key "
    "distribution (QKD) and algorithmic key derivation:\n\n"
    "**Onion building (buildOnion)**:\n"
    "1. Start with the raw payload\n"
    "2. Iterate backwards from exit node to entry node\n"
    "3. For each node: handshake -> derive symmetric key -> AES-256-GCM encrypt -> "
    "prepend routing header\n"
    "4. Each layer wraps: header + delimiter('::') + IV(16B) + authTag + encryptedData\n\n"
    "**Onion peeling (peelOnion)**:\n"
    "1. Parse header to find next hop ID\n"
    "2. Extract IV (16 bytes) and auth tag (16 bytes)\n"
    "3. Derive symmetric key via handshake\n"
    "4. AES-256-GCM decrypt to reveal inner onion\n"
    "5. Return next hop ID + inner onion for forwarding\n\n"
    "Quantum-capable nodes use QKD for the handshake; legacy nodes use the "
    "pi^phi key derivation system. Both produce a 256-bit symmetric key.",
    ["spacetor", "crypto", "onion", "hybrid"],
))

records.append(rec(
    "What encryption algorithm does SpaceTor use for onion layers?",
    "AES-256-GCM (Galois/Counter Mode) for each onion layer:\n\n"
    "- Key: 256-bit symmetric key from QKD or algorithmic handshake\n"
    "- IV: 16 bytes of crypto.randomBytes (unique per layer)\n"
    "- Auth tag: 16 bytes (GCM provides authenticated encryption)\n"
    "- Mode: Encrypt-then-MAC (GCM handles both)\n\n"
    "The wire format per layer is:\n"
    "  [routing_header_json]::[iv_16B][auth_tag_16B][encrypted_data]\n\n"
    "The routing header contains only the next hop ID (or 'DESTINATION' for the "
    "final hop). Each relay can only read its own header — the inner layers are "
    "encrypted with keys the relay doesn't have.",
    ["spacetor", "crypto", "aes", "encryption"],
))

records.append(rec(
    "What is the difference between QKD and algorithmic handshake in SpaceTor?",
    "SpaceTor supports two handshake modes:\n\n"
    "**Quantum Key Distribution (QKD)**:\n"
    "- Used when both nodes have quantumCapable=true\n"
    "- Derives keys using quantum entanglement (BB84 or similar)\n"
    "- Information-theoretically secure against quantum computers\n"
    "- Referenced: arXiv:2505.13239 (Network-wide QKD with Onion Routing)\n\n"
    "**Algorithmic (pi^phi)**:\n"
    "- Used when at least one node is not quantum-capable\n"
    "- Uses classical key derivation with pi^phi mathematical properties\n"
    "- Computationally secure (not information-theoretically secure)\n"
    "- Serves as fallback for legacy infrastructure\n\n"
    "Both produce a 256-bit symmetric key for AES-256-GCM. The relay's "
    "quantumCapable flag determines which handshake is used.",
    ["spacetor", "crypto", "qkd", "handshake"],
))

# ── Combat Network ────────────────────────────────────

records.append(rec(
    "What is the SpaceTor combat network and why is it needed?",
    "The Combat Network handles multipath redundancy for hostile environments. "
    "In combat scenarios, single-path routing is vulnerable — relays can be "
    "destroyed or jammed ('caked'). The solution:\n\n"
    "**Standard mode**: Single 3-hop path (entry -> middle -> exit)\n"
    "**Combat mode**: Two disjoint 3-hop paths sent in parallel\n\n"
    "Disjoint means the paths share no middle nodes, so compromising one path "
    "doesn't compromise the other. If the primary path fails, the backup delivers "
    "the same data independently.\n\n"
    "Implementation:\n"
    "1. Calculate primary path A via SpaceTorRouter\n"
    "2. Generate disjoint path B (excludes A's middle nodes, reduced minTrust)\n"
    "3. Build separate onions for each path\n"
    "4. Fire both simultaneously (Promise.all)\n"
    "5. First successful delivery wins\n\n"
    "Referenced: arXiv:2204.04489 (ShorTor: Multi-hop Overlay Routing)",
    ["spacetor", "combat", "multipath", "redundancy"],
))

records.append(rec(
    "How does SpaceTor generate disjoint paths for combat mode?",
    "Disjoint path generation ensures the backup path shares no middle nodes "
    "with the primary path:\n\n"
    "1. Calculate primary path A normally: [entry_A, middle_A, exit_A]\n"
    "2. For path B, exclude middle_A from candidates\n"
    "3. Reduce minTrust threshold by 10 points (more permissive selection)\n"
    "4. Calculate path B: [entry_B, middle_B, exit_B]\n"
    "5. Entry and exit may overlap (they serve different roles), but middle nodes "
    "must be disjoint\n\n"
    "The minTrust reduction is necessary because the candidate pool shrinks "
    "after excluding path A's middle node. If no disjoint path is available, "
    "the system logs a warning and falls back to a single path.\n\n"
    "In extreme cases (very few nodes), the backup path may share entry/exit "
    "but will always have a different middle node.",
    ["spacetor", "combat", "disjoint-paths"],
))

records.append(rec(
    "What is the TransmissionResult structure in SpaceTor?",
    "TransmissionResult tracks the outcome of each path in a combat send:\n\n"
    "```\n"
    "interface TransmissionResult {\n"
    "  success: boolean;    // Did the packet reach destination?\n"
    "  pathId: string;      // 'PRIMARY', 'BACKUP', or 'STANDARD'\n"
    "  latencyMs: number;   // Round-trip time in milliseconds\n"
    "  error?: string;      // Error message if failed\n"
    "}\n"
    "```\n\n"
    "In standard mode, you get one result (pathId='STANDARD').\n"
    "In combat mode, you get two results: PRIMARY and BACKUP.\n"
    "Success is determined by whether either path delivered the data.",
    ["spacetor", "combat", "types"],
))

# ── Fleet Integration ─────────────────────────────────

records.append(rec(
    "How does SpaceTor integrate with the SCBE fleet system?",
    "The fleet system provides the multi-agent layer above SpaceTor:\n\n"
    "- **Agent Registry** — registers agents with spectral identity for fleet membership\n"
    "- **Fleet Manager** — coordinates SpaceTor routing for inter-agent communication\n"
    "- **Task Dispatcher** — assigns tasks based on Langues trust scores\n"
    "- **Swarm Governance** — roundtable consensus for critical routing decisions\n"
    "- **Browser Pool** — coordinated browser crawl with SpaceTor-secured channels\n"
    "- **Crawl Coordinator** — frontier management for multi-agent web exploration\n\n"
    "The crawl system uses SpaceTor for secure communication between browser agents "
    "and the coordinator. Trust-based task assignment means untrusted agents get "
    "lower-risk crawl targets. Swarm geometry (flux ODE dynamics) governs how "
    "agents coordinate their movement through the information space.",
    ["spacetor", "fleet", "integration"],
))

records.append(rec(
    "What is a Polly Pad in the fleet system?",
    "Polly Pads are personal agent workspaces with dimensional flux. Each agent "
    "in the fleet gets its own Polly Pad — a sandboxed environment where it can:\n\n"
    "- Store notes, sketches, and tools\n"
    "- Track growth milestones and XP\n"
    "- Maintain audit logs (AuditEntry with AuditStatus)\n"
    "- Progress through tiers (TIER_THRESHOLDS)\n\n"
    "The dimensional flux comes from the Sacred Tongue trust vectors — each pad's "
    "capabilities are gated by the agent's trust level. An agent with low UM "
    "(security) trust can't access encryption tools. An agent with high CA "
    "(compute) trust gets access to heavier processing tasks.\n\n"
    "Growth is tracked via getXPForNextTier() and getNextTier(), creating a "
    "progressive trust-building system where agents earn capabilities over time.",
    ["fleet", "polly-pad", "agent-workspace"],
))

# ── Cross-cutting concepts ────────────────────────────

records.append(rec(
    "How does SpaceTor handle the transition from legacy trust to Langues trust?",
    "SpaceTor maintains backward compatibility with two trust systems:\n\n"
    "1. **Legacy trustScore** (0-100): Simple scalar. Used when trustVector is absent.\n"
    "2. **Langues trustVector** (6D, each in [0,1]): Full Langues metric. Preferred.\n\n"
    "The router checks: if node.trustVector exists and has length 6, use "
    "TrustManager.computeTrustScore() for Langues scoring. Otherwise, use the "
    "legacy trustScore directly.\n\n"
    "For Langues -> legacy conversion:\n"
    "  legacy = (1 - L_normalized) * 100\n\n"
    "This inversion is because low Langues metric = high trust (low deviation "
    "from ideal). The conversion ensures both systems produce comparable 0-100 "
    "scores for the weighted path selection algorithm.\n\n"
    "The API provides both updateNodeTrust(id, score) for legacy and "
    "updateNodeTrustVector(id, vector) for Langues.",
    ["spacetor", "trust", "backward-compat"],
))

records.append(rec(
    "What are the arXiv references used in SpaceTor's design?",
    "SpaceTor cites four key papers:\n\n"
    "1. **arXiv:2508.17651** — Path Selection Strategies in Tor: informs the "
    "weighted relay selection algorithm and guard node prioritization\n\n"
    "2. **arXiv:2406.15055** — SaTor: Satellite Routing: the primary inspiration "
    "for 3D spatial routing with light-lag constraints\n\n"
    "3. **arXiv:2505.13239** — Network-wide QKD with Onion Routing: basis for "
    "the hybrid quantum/classical encryption layer\n\n"
    "4. **arXiv:2502.06657** — Onion Routing Key Distribution for QKDN: key "
    "distribution protocol design for quantum-capable nodes\n\n"
    "5. **arXiv:1507.05724** — HORNET: High-speed Onion Routing at the Network "
    "Layer: performance optimization strategies for onion peeling\n\n"
    "6. **arXiv:2204.04489** — ShorTor: Multi-hop Overlay Routing: multipath "
    "routing strategies for the combat network module",
    ["spacetor", "references", "research"],
))

records.append(rec(
    "How does SpaceTor's trust anomaly detection work?",
    "The TrustManager tracks historical trust scores per node and flags anomalies:\n\n"
    "1. Each call to computeTrustScore() appends the raw score to the node's history\n"
    "2. History is capped at 100 entries (ring buffer)\n"
    "3. After each update, the manager computes:\n"
    "   drop = (prev_score - current_score) / prev_score\n"
    "4. If drop > 0.3 (30% trust degradation), an anomaly is flagged with timestamp\n\n"
    "Anomaly strings are stored in the node's anomalies array. They serve as:\n"
    "- Input to the governance layer for routing decisions\n"
    "- Audit trail for trust transitions\n"
    "- Trigger for combat mode activation (high anomaly count = hostile environment)\n\n"
    "A node with multiple anomaly flags may be excluded from path selection "
    "entirely, even if its current trust score passes the minTrust threshold.",
    ["spacetor", "trust", "anomaly-detection"],
))

records.append(rec(
    "What is the relationship between SpaceTor Layers and the SCBE 14-layer pipeline?",
    "SpaceTor maps to several SCBE pipeline layers:\n\n"
    "- **L3 (Weighted Transform)** — The Langues Metric Tensor for trust scoring. "
    "This is the core mathematical engine shared between SpaceTor and the pipeline.\n"
    "- **L5 (Hyperbolic Distance)** — Trust deviation uses exponential amplification "
    "(exp[beta * d]), analogous to hyperbolic distance scaling.\n"
    "- **L6 (Breathing Transform)** — Dimension flux coefficients (nu) control "
    "temporal oscillation in trust scoring, matching the breathing mechanism.\n"
    "- **L12 (Harmonic Wall)** — The trust -> routing decision maps to the harmonic "
    "wall's ALLOW/QUARANTINE/ESCALATE/DENY tiers.\n"
    "- **L13 (Risk Decision)** — Swarm governance for routing decisions uses the "
    "same roundtable consensus as the pipeline's governance layer.\n\n"
    "SpaceTor is essentially the SCBE pipeline applied to network routing: "
    "trust vectors are input, Langues metric is the transform, and routing "
    "decisions are the governance output.",
    ["spacetor", "pipeline", "layer-mapping"],
))

# ── Multi-agent browser crawl ─────────────────────────

records.append(rec(
    "How does the multi-agent browser crawl work with SpaceTor?",
    "The fleet system coordinates multi-agent browser crawling through:\n\n"
    "1. **Crawl Frontier** — maintains the queue of URLs to visit, prioritized "
    "by domain trust score (Langues-scored per domain)\n"
    "2. **Crawl Coordinator** — distributes URLs from the frontier to available "
    "browser agents based on their trust tier\n"
    "3. **Browser Pool** — manages Chrome instances across agents, each sandboxed "
    "in its own Polly Pad workspace\n"
    "4. **Crawl Runner** — executes crawl tasks within a browser, reporting "
    "findings back through SpaceTor-secured channels\n"
    "5. **Crawl Message Bus** — pub/sub messaging between agents using SpaceTor "
    "for secure inter-agent communication\n\n"
    "Trust scoring determines crawl assignments: HIGH trust agents get sensitive "
    "targets (login-required sites, internal domains). LOW trust agents get "
    "public, low-risk targets. CRITICAL trust agents are quarantined and don't "
    "participate in crawls.",
    ["fleet", "browser", "crawl", "multi-agent"],
))

records.append(rec(
    "What is swarm geometry in the fleet system?",
    "Swarm geometry governs how multiple agents coordinate their movement through "
    "information space using flux ODE dynamics:\n\n"
    "Key components:\n"
    "- **Oscillator Bus** — synchronizes agent timing via coupled oscillators. "
    "Agents that drift out of sync lose governance privileges.\n"
    "- **Governed Drift** — agents move through the information landscape with "
    "drift constrained by governance bounds. Too-fast exploration triggers "
    "QUARANTINE.\n"
    "- **Node Kernel** — each agent runs a local kernel that maintains its "
    "state in the swarm. The kernel computes the agent's position in the "
    "swarm geometry and reports to the coordinator.\n\n"
    "The 4-layer swarm architecture:\n"
    "1. Swarm Geometry (spatial layout)\n"
    "2. Oscillator Bus (temporal sync)\n"
    "3. Governed Drift (movement constraints)\n"
    "4. Node Kernel (agent state)\n\n"
    "This maps to physics: agents are particles in a potential field, with "
    "the harmonic wall providing the potential energy surface.",
    ["fleet", "swarm", "geometry", "dynamics"],
))

# ── Write output ──────────────────────────────────────

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"SpaceTor SFT: {len(records)} records -> {OUT}")
