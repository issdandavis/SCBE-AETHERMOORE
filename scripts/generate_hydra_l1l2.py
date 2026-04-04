#!/usr/bin/env python3
"""Generate L1/L2 training data from HYDRA coordination architecture.

L1 = how agents coordinate (protocols, consensus, token flow, squad roles)
L2 = how to route/orient (tongue selection, tier requirements, formation choice)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "hydra_coordination_l1l2_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

def r(instruction, output, layer, tongue, active=None, category="coordination"):
    act = active or [tongue]
    null = [t for t in ALL_TONGUES if t not in act]
    return {
        "instruction": instruction,
        "output": output,
        "tongue": tongue,
        "tongues_active": act,
        "tongues_null": null,
        "layer": layer,
        "category": category,
        "view_type": "null-heavy" if len(null) >= 4 else "partial",
        "governance": "ALLOW",
        "source": "hydra_coordination_generator",
    }

RECORDS = [
    # ── L1: BFT Consensus Protocol ──
    r("How does Byzantine Fault Tolerance work in the HYDRA swarm?",
      "HYDRA uses BFT with f_max = floor((n-1)/3) where n=6 agents, so f_max=1 (tolerates 1 Byzantine agent). Quorum requires 2f+1 = 3 agreeing votes. Votes are ALLOW/DENY/ABSTAIN/ESCALATE, each cryptographically signed with SHA-256. Concurrent vote collection via asyncio.gather with timeout handling (abstain with confidence=0.0 on timeout). This means the swarm continues operating even if one agent is compromised or offline.",
      "L1", "KO", ["KO", "UM"]),

    r("What is the RoundtableConsensus and how does it extend BFT?",
      "RoundtableConsensus adds 6 sensitivity tiers to basic BFT. Each tier requires progressively more tongue heads to sign: Tier 1 (sensitivity<0.3) = KO only (1.5x multiplier). Tier 2 (<0.5) = KO+RU (5.06x). Tier 3 (<0.7) = KO+RU+UM (38.4x). Tier 4 (<0.8) = KO+RU+UM+CA (656x). Tier 5 (<0.9) = 5 tongues (14,348x). Tier 6 (>=0.9) = all 6 (518,400x attestation diversity). Higher sensitivity = more tongues required = harder to forge consensus.",
      "L1", "UM", ["KO", "RU", "UM"]),

    r("What are the Squad BFT parameters?",
      "Squad BFT: n=6 agents, f_max=1, quorum=4. The constructor enforces n >= 3f+1 at build time. Decisions: APPROVED (quorum reached for), DENIED (quorum reached against), DEFERRED (split vote), NO_QUORUM (timeout/abstain). Proposal categories: action, mode_switch, navigation, repair, abort. All broadcasts go over ClosedNetwork — no external visibility.",
      "L1", "KO", ["KO", "CA"]),

    # ── L1: Squad Roles ──
    r("What are the four squad roles in HYDRA crawl coordination?",
      "SCOUT (+1,0 FORWARD_THRUST): discovers URLs, explores frontiers. ANALYZER (+1,+1 RESONANT_LOCK): deep content extraction and semantic analysis. SENTINEL (0,+1 PERPENDICULAR_POS): safety monitor, watches for threats perpendicular to the mission direction. REPORTER (0,0 ZERO_GRAVITY): neutral aggregator, collects and summarizes without bias. Each role has a thrust vector that determines its position in the formation.",
      "L1", "KO", ["KO", "AV"]),

    r("What agent states exist in the HYDRA swarm governance?",
      "Six states: ACTIVE (normal operations), IDLE (waiting for work), VOTING (participating in consensus), EXECUTING (carrying out approved action), ISOLATED (low coherence score — quarantined but not removed), FROZEN (attack detected — all outputs blocked). State transitions require governance approval. An ISOLATED agent can recover by rebuilding coherence. A FROZEN agent requires manual intervention or Sacred Egg reset.",
      "L1", "RU", ["RU", "UM"]),

    r("How do HYDRA heads communicate with each other?",
      "Through the HydraSpine switchboard: pub/sub message passing over role-channels. Each head can switchboard_enqueue (add to queue), switchboard_post_message (broadcast), or switchboard_get_messages (pull). AI-to-AI messages are scanned for injection patterns — words like 'ignore', 'override', 'sudo', 'admin', 'forget', 'disregard', 'system prompt' are blocked. The Spine also provides turnstile resolution: PIVOT (redirect), DEGRADE (reduce capability), ISOLATE (quarantine), HONEYPOT (trap) on non-ALLOW decisions.",
      "L1", "CA", ["KO", "CA", "UM"]),

    # ── L1: Four-Rail Braid ──
    r("What is the four-rail mission braid in HYDRA?",
      "Every mission packet forks into four parallel rails: P+ (Positive Primal) = the intended action path. P- (Negative Primal) = friction, obstacles, what could go wrong. D+ (Positive Dual) = attestation and confirmation from other agents. D- (Negative Dual) = dissent, contradiction, spoofing signals. The Conductor recomposes all four rails after quorum or timeout. L13 decides: ALLOW/QUARANTINE/ESCALATE/DENY. L14 emits telemetry: energy, centroid, flux, hf_ratio, stability.",
      "L1", "CA", ["CA", "KO"]),

    r("Why does HYDRA use four rails instead of just sending one message?",
      "Single-rail systems are blind to dissent. If you only collect P+ (what worked), you miss P- (what went wrong), D+ (who confirmed), and D- (who disagreed). The four-rail braid gives the Conductor a complete picture: action + friction + confirmation + dissent. This is the communication equivalent of the 14-layer pipeline — multiple views of the same event, combined at L13 for a governance decision. Without D-, a compromised agent's P+ looks indistinguishable from a legitimate one.",
      "L1", "DR", ["CA", "DR"]),

    # ── L1: Multi-Phase Workflows ──
    r("How does HYDRA chain workflow phases?",
      "HydraSpine.define_workflow() chains phases: INIT -> PLANNING -> EXECUTION -> VALIDATION -> COMPLETE. Each phase is a function that returns a decision. Any phase returning decision=DENY halts the entire workflow — no partial execution. This prevents the 'half-done dangerous action' problem. The PLANNING phase uses the KO head to decompose tasks. EXECUTION uses the appropriate tongue head. VALIDATION uses RU+UM to verify the result matches intent.",
      "L1", "KO", ["KO", "RU", "CA"]),

    # ── L2: Tongue Routing ──
    r("How do you route an action to the correct Sacred Tongue in HYDRA?",
      "Action-to-tongue routing: read/list/get/search -> KO. create/update/write -> AV. run/execute/test -> RU. deploy/publish/release -> CA. configure/admin/manage -> UM. delete/destroy/terminate/rollback -> DR. Each tongue has a governance tier with minimum trust: KO=0.1 (1 tongue required), AV=0.3 (2 tongues), RU=0.5 (3 tongues), CA=0.7 (4 tongues), UM=0.85 (5 tongues), DR=0.95 (6 tongues). UM and DR always require a full Roundtable session.",
      "L2", "KO", ["KO", "DR"]),

    r("What governance tier does a 'deploy to production' action require?",
      "Deploy/publish/release routes to CA tongue (tier 4). Requirements: minTrust=0.7, requiredTongues=4 (KO+RU+UM+CA must all sign). Governance multiplier: 656x attestation diversity. The canary manager ramps traffic: 5% -> 25% -> 50% -> 100% with 30-60 minute soak windows between advances. Rollback snaps back to 5% immediately. Each deployment stage maps to a tongue: Build=CA, Test=RU, Stage=UM, Deploy=KO, Monitor=AV, Rollback=DR.",
      "L2", "CA", ["KO", "RU", "CA", "UM"]),

    r("What governance tier does a 'delete database' action require?",
      "Delete/destroy/terminate routes to DR tongue (tier 6, the highest). Requirements: minTrust=0.95, requiredTongues=6 (ALL tongues must sign). Governance multiplier: 518,400x attestation diversity. This is the most expensive operation in the system. A full Roundtable session is mandatory. The phi weight of DR (11.09) means the harmonic wall cost is 11x higher than a KO operation. This makes destructive actions computationally and procedurally expensive — by design.",
      "L2", "DR"),

    r("How does sensitivity level determine which tongues participate in consensus?",
      "Sensitivity maps to tongue participation: sensitivity<0.3 = KO only (basic read operations). <0.5 = KO+RU (writes that need policy check). <0.7 = KO+RU+UM (operations touching security). <0.8 = add CA (compute/deploy operations). <0.9 = add AV (I/O operations). >=0.9 = all 6 (destructive/critical). Navigate=0.2, click=0.3, type=0.4, run=0.6, execute=0.8. The sensitivity is inferred from the action type, not guessed.",
      "L2", "RU", ["KO", "RU", "UM"]),

    # ── L2: Swarm Formations ──
    r("What are the four canonical swarm formations?",
      "1. Hexagonal Ring: 6 agents at 60-degree intervals, r=0.3 in Poincare ball. Default formation for bootstrap, broadcast, low-latency coordination. 2. Tetrahedral (3D): 4 tetrahedron vertices + 2 extra at z-levels. For 3D fault tolerance and Byzantine resistance. 3. Concentric Rings: inner ring (KO/AV/RU at r=0.2), outer ring (CA/UM/DR at r=0.5). For priority allocation and gossip protocols. 4. Adaptive Scatter: force-based with repulsion + centroid attraction + Gaussian drift. Projects back into Poincare ball when ||pos|| >= 1.0. For adversarial environments.",
      "L2", "DR", ["KO", "DR"]),

    r("When should you use Concentric Rings vs Hexagonal Ring formation?",
      "Hexagonal Ring: all agents equidistant, equal priority, uniform coverage. Use when the task is homogeneous and all tongues contribute equally. Concentric Rings: inner ring (KO/AV/RU at r=0.2) has faster access, outer ring (CA/UM/DR at r=0.5) provides depth. Use when the task has priority layers — control/I/O/policy agents need faster response than compute/security/structure agents. The concentric formation maps to IP tier allocation: inner = hot path, outer = cold path.",
      "L2", "DR", ["KO", "DR"]),

    r("How does Adaptive Scatter formation handle adversarial environments?",
      "Adaptive Scatter uses force-based positioning: repulsion (agents push apart to avoid clustering), centroid attraction (swarm stays cohesive), Gaussian drift (randomized movement to avoid predictability), phase-modulated strength (force varies by Sacred Tongue phase angle). When ||pos|| >= 1.0, agents are projected back into the Poincare ball — they can't escape the safe region. Byzantine detection: cross-compare peer position reports, flag if variance > 0.1. Response: quarantine -> Sacred Egg alert -> spawn replacement.",
      "L2", "UM", ["UM", "DR"]),

    # ── L2: Formation Selection ──
    r("How do you choose a swarm formation based on the mission type?",
      "Mission type maps to formation: Exploration/discovery -> Hexagonal Ring (uniform coverage). Deep analysis -> Concentric Rings (priority allocation). Hostile/adversarial -> Adaptive Scatter (jam-resistant). 3D environments/drones -> Tetrahedral (spatial fault tolerance). The normalized canonical families: perimeter_ring (Hexagonal/defensive_circle), hierarchical_shell (Concentric), three_dimensional_resilience (Tetrahedral), focused_probe (investigation_wedge), coverage_mesh (Adaptive Scatter/patrol_grid).",
      "L2", "KO", ["KO", "CA"]),

    # ── L2: Swarm Geometry Physics ──
    r("What is the motion equation for HYDRA swarm agents?",
      "v_i = alpha*Cohesion(x_i, C) + beta*Separation(x_i, neighbors) + gamma*GoalVector + delta*DriftBounded. Trust-weighted centroid: C = sum(tau_i * x_i) / sum(tau_i). Cohesion: linear attraction (stronger when further). Separation: inverse-distance repulsion within separationRadius. Goal: capped at magnitude 1 to prevent goal-dominance. Hard caps: alpha<=2.0, beta<=3.0, gamma<=2.5, delta<=1.0. Speed cap enforced. No-go zones enforced.",
      "L1", "CA", ["CA", "DR"]),

    r("What are the dimensional flux states in the HYDRA swarm?",
      "Flux ODE: dv/dt = alpha*(v_target - v) - beta*decay + gamma*coherence_boost. Four states: POLLY (v>=0.8, full capability, all 16 polyhedra active). QUASI (0.5<=v<0.8, defensive mode, 8 polyhedra). DEMI (0.1<=v<0.5, lockdown, 5 polyhedra). COLLAPSED (v<0.1, emergency shutdown). The flux state determines which PHDM polyhedra are available for routing — degradation is monotonic, never introduces new paths.",
      "L2", "DR", ["DR", "RU"]),

    # ── L1: Fleet Deployment Coordination ──
    r("What is the canary deployment ramp in HYDRA fleet management?",
      "Canary ramp: 5% -> 25% -> 50% -> 100% with 30-60 minute soak windows between advances. During soak, monitor: coherence (spectral + spin), error rate, latency p95, cost per 1K tokens. Quality gates: Safety >= 0.95, Quality >= 0.80, Latency <= 200ms p95, Cost <= $1/1K tokens. If any gate fails during soak, rollback snaps to 5% immediately. Rolling deploy: 1 agent per specialty first, monitor 5 minutes, continue batch if healthy, auto-rollback if degraded.",
      "L1", "CA", ["CA", "AV"]),

    r("How does tongue-aware deployment work?",
      "Each deployment stage maps to a Sacred Tongue: Build=CA (computation, compiling). Test=RU (validation, rule-binding). Stage=UM (hidden, not yet revealed to production). Deploy=KO (asserting into production with control). Monitor=AV (listening, watching for anomalies). Rollback=DR (structured retreat to previous version). This means deployment itself follows the governance geometry — every stage is routed through the appropriate tongue channel with its cost weight.",
      "L2", "KO", ["KO", "CA", "DR"]),

    # ── L1: Attack Scenarios ──
    r("How does HYDRA detect and respond to a Phase-Null Intruder?",
      "A Phase-Null Intruder tries to join the swarm with a forged tongue assignment. Detection: cross-compare peer position reports — variance > 0.1 threshold triggers alert. The intruder's phase angle won't match any of the 6 canonical positions (0, 60, 120, 180, 240, 300 degrees). Response chain: quarantine the suspicious agent, trigger Sacred Egg alert (genesis protocol), spawn a replacement agent at the correct phase angle. The quarantined agent's votes are excluded from future consensus rounds.",
      "L1", "UM", ["UM", "RU"]),

    r("How does HYDRA resist Sybil attacks?",
      "Sybil prevention: each agent must provide a Proof-of-Work with 5 leading zeros before joining the swarm. Combined with the 6-tongue constraint (only 6 valid phase positions), an attacker would need to: (1) solve PoW, (2) forge a valid tongue phase angle, (3) pass BFT consensus from existing agents. Even if they succeed at joining, the RoundtableConsensus requires cryptographic signatures from specific tongue heads — a Sybil agent can't sign as KO if it's not the KO head.",
      "L1", "UM", ["UM", "CA"]),

    # ── L2: HYDRA Layer Stack Orientation ──
    r("How do the 7 HYDRA layers map to the SCBE pipeline?",
      "L7 (User Interface): Terminal/Browser/API — where humans interact. L6 (HYDRA Coordination): Spine+Heads+Limbs — agent orchestration. L5 (Spectral Governance): GFSS anomaly detection + BFT quorum — coherence monitoring. L4 (Swarm Browser): 6 phase-modulated Sacred Tongue agents — parallel execution. L3 (Browser Backends): Chrome MCP/Playwright/Selenium/CDP — actual browser control. L2 (SCBE API Gateway): 4-tier auth + Roundtable endpoints — access control. L1 (SCBE Core): 14-layer cryptographic pipeline — the mathematical foundation.",
      "L2", "DR", ["DR", "KO"]),

    r("How does HydraHead wrap different AI models?",
      "HydraHead is a universal AI interface that wraps any model. Callsign prefixes: CT (Claude), CX (Codex), GP (GPT), GM (Gemini), LC (Local LLM). Each head provides: think(prompt) for direct LLM calls, plan(task) for task decomposition into JSON action arrays, equip_polly_pad() for hot-swappable capability loadouts. The HYDRA multi-model config assigns one model per tongue: KO=TinyLlama (scout), AV=moondream2 (vision), RU=phi-2 (reader), CA=Qwen-1.5B (clicker), UM=SmolLM-1.7B (typer), DR=TinyLlama (judge).",
      "L2", "CA", ["CA", "KO"]),

    # ── L1: Sacred Tongue Interop ──
    r("How do Sacred Tongues interoperate in multi-agent coordination?",
      "Every byte encodes to different tokens per tongue but carries the same binary value — the SS1 bijection is tongue-specific but value-preserving. In coordination: KO (440 Hz, phi^0=1.0) handles intent/nonce. AV (440*phi Hz, phi^1=1.618) handles transport/metadata. RU (440*phi^2 Hz, phi^2=2.618) handles policy/salt/binding. CA (440*phi^3 Hz, phi^3=4.236) handles compute/ciphertext. UM (440*phi^4 Hz, phi^4=6.854) handles security/redaction. DR (440*phi^5 Hz, phi^5=11.09) handles schema/auth tags. Each tongue frequency is phi-spaced from the next.",
      "L1", "DR", ["DR", "KO"]),

    # ── L2: Governance Decision Routing ──
    r("Route a 'search the web for research papers' task through HYDRA governance.",
      "Action: search. Routes to KO tongue (read operation). Governance tier 1: minTrust=0.1, requiredTongues=1 (KO only). Sensitivity: 0.2 (navigate-level). No Roundtable required. The KO Scout head handles this directly — plan the search, execute via browser backend, collect results. Cost: phi^0 = 1.0 (cheapest possible operation). Formation: Hexagonal Ring (uniform coverage for broad search). Null tongues: [AV, RU, CA, UM, DR] — no write, policy, compute, security, or structural operations needed.",
      "L2", "KO"),

    r("Route a 'deploy the new model to production' task through HYDRA governance.",
      "Action: deploy. Routes to CA tongue (tier 4). Sensitivity: 0.8 (execute-level). RequiredTongues: 4 (KO+RU+UM+CA). Full Roundtable session required. Canary ramp: 5% initial, soak 30 min, advance if Safety>=0.95 and Latency<=200ms. Each stage through tongue-aware deployment: Build(CA) -> Test(RU) -> Stage(UM) -> Deploy(KO) -> Monitor(AV). If any gate fails: Rollback(DR) snaps to 5%. Formation: Concentric Rings — inner ring (KO/AV/RU) monitors, outer ring (CA/UM/DR) executes.",
      "L2", "CA", ["KO", "RU", "CA", "UM"]),

    r("Route a 'delete the old training data' task through HYDRA governance.",
      "Action: delete. Routes to DR tongue (tier 6, maximum governance). Sensitivity: 0.95+ (critical). RequiredTongues: 6 (ALL must sign). Full Roundtable with 518,400x attestation diversity. minTrust: 0.95 — the system must be highly confident this is correct. Cost: phi^5 = 11.09 (most expensive operation). Every head votes: KO (is this the right target?), AV (is the data backed up?), RU (does policy allow deletion?), CA (is the operation technically safe?), UM (are there security implications?), DR (is the schema change reversible?). No shortcuts.",
      "L2", "DR"),
]


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    l1_count = 0
    l2_count = 0
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            if record["layer"] == "L1":
                l1_count += 1
            else:
                l2_count += 1

    print(f"Generated {len(RECORDS)} HYDRA coordination records")
    print(f"  L1 (coordination): {l1_count}")
    print(f"  L2 (orientation):  {l2_count}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    generate()
