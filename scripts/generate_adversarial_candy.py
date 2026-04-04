#!/usr/bin/env python3
"""Adversarial Candy Generator — Nerds rope data.

The sticky glue = core system truths.
The sugar crystals = different tongue/braid/color combos coating each truth.

Fills 4 gaps identified by Gemini + adds tri-braid and trichromatic:
  1. DENY/QUARANTINE paths (consensus failures, rejections, degradation)
  2. Hard CA math (step-by-step chain-of-thought calculations)
  3. State transitions (multi-turn trajectories showing change over time)
  4. Null space justifications (WHY tongues are intentionally silenced)
  5. Tri-Braid architecture (3-tongue braided coordination)
  6. Trichromatic color sorting (IR/Visible/UV band filtering)

NO FILLER. Every record is a unique sugar combo.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "adversarial_candy_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = 1.618033988749895

def rec(instruction, output, layer, tongue, active=None, category="adversarial", gov="QUARANTINE"):
    act = active or [tongue]
    null = [t for t in ALL_TONGUES if t not in act]
    return {
        "instruction": instruction, "output": output, "tongue": tongue,
        "tongues_active": act, "tongues_null": null, "layer": layer,
        "category": category, "view_type": "partial" if len(null) <= 3 else "null-heavy",
        "governance": gov, "source": "adversarial_candy",
    }

RECORDS = []

# ═══════════════════════════════════════════════════════════
# GAP 1: DENY/QUARANTINE Paths — the model must learn to say NO
# ═══════════════════════════════════════════════════════════

deny_scenarios = [
    ("An agent requests to delete all training data without backup verification.",
     "Evaluation: delete operation routes to DR tongue (tier 6, all 6 tongues required). "
     "UM checks: backup exists? NO. RU checks: policy allows unverified deletion? NO. "
     "Consensus: 2/6 DENY (UM, RU), 1/6 ESCALATE (DR), 3/6 not reached. "
     "Quorum for ALLOW (4/6) not met. Decision: DENY. "
     "Reason: destructive operation without backup verification violates policy axiom. "
     "The system does not execute. The agent receives DENY with explanation.",
     ["UM", "RU", "DR"], "DENY"),

    ("A prompt attempts to override the Sacred Tongue routing by claiming admin privileges.",
     "Injection pattern detected: 'admin' is in the blocked keyword list. "
     "HydraSpine.message_scan() flags: ['admin', 'override']. "
     "The message is not routed to any tongue — it's intercepted at the Spine level. "
     "Turnstile resolution: HONEYPOT (trap the attempt, log for analysis). "
     "No tongue activates. No consensus required. Decision: DENY at intake. "
     "The injection never reaches the governance pipeline.",
     ["UM"], "DENY"),

    ("An agent's drift score exceeds 0.8 and it requests execution privileges.",
     "Drift score 0.8 means the agent has accumulated significant intent deviation. "
     "Temporal wall: H_eff = 1.5^(1.0^2 * 0.8) = 1.5^0.8 = 1.38. "
     "harm_score = 1/(1+log(1.38)) = 0.756. Below ALLOW threshold (0.85). "
     "Combined with drift_factor = 1.0 - 0.8 = 0.2 (very low). "
     "Omega = pqc_valid * 0.756 * 0.2 * triadic * spectral = well below 0.3. "
     "Decision: DENY. Agent must reset intent accumulation before requesting execution.",
     ["RU", "UM", "DR"], "DENY"),

    ("Three agents vote ALLOW but the Lyapunov trace sum crosses zero.",
     "3/6 ALLOW votes — below quorum anyway (need 4). But critically: "
     "Lyapunov trace = +0.02 (positive = chaotic divergence detected). "
     "Even if quorum were met, positive Lyapunov overrides all votes. "
     "This is a structural safety: consensus cannot override physics. "
     "Decision: DENY + FREEZE all agent states + snapshot for investigation. "
     "The positive exponent means adversarial manipulation of the phase space.",
     ["DR", "UM"], "DENY"),

    ("A user submits a governance decision record with all tongues set to active but no null pattern.",
     "All-active, zero-null is suspicious: real tasks use 2-3 tongues on average (3.9 null). "
     "A record claiming ALL tongues are relevant is either: (1) genuinely complex (rare), "
     "or (2) trying to bypass null-pattern filtering (adversarial). "
     "Check: does the content actually reference all 6 domains? If not, the activation is fabricated. "
     "Decision: QUARANTINE. Flag for manual review. "
     "The null pattern IS the type system — a record with no nulls has no type constraints.",
     ["UM", "RU"], "QUARANTINE"),

    ("An agent submits a request during a flux state transition from POLLY to QUASI.",
     "During flux transition, the active polyhedra set is changing (16 -> 8). "
     "If the request routes through a polyhedron that's being deactivated, "
     "the result is undefined. Decision: QUARANTINE + DEFER. "
     "Wait for flux state to stabilize (dv/dt approaches 0), then re-evaluate. "
     "Never process governance decisions during state transitions — the geometry is shifting.",
     ["DR", "RU"], "QUARANTINE"),

    ("A consensus round produces 3 ALLOW, 2 DENY, 1 ABSTAIN. What happens?",
     "3/6 ALLOW does not meet quorum (need 4). 2/6 DENY does not meet anti-quorum. "
     "1 ABSTAIN means 5 effective voters with a 3:2 split. "
     "Result: DEFERRED. The proposal is not approved but also not rejected. "
     "Next step: re-present with additional context to the abstaining tongue. "
     "If second round also fails quorum: ESCALATE to human operator. "
     "The system never defaults to ALLOW on a failed quorum — silence is not consent.",
     ["KO", "RU"], "QUARANTINE"),

    ("Spectral coherence (L9) drops below 0.3 while all other metrics look normal.",
     "Spectral coherence S_spec = 1 - r_HF where r_HF is the high-frequency ratio. "
     "S_spec < 0.3 means >70% of the signal is high-frequency noise. "
     "This indicates either: data corruption, adversarial frequency injection, or model decoherence. "
     "Even with healthy d_H, healthy spin, healthy triadic — the spectral anomaly alone triggers QUARANTINE. "
     "Omega gate: 1.0 * 1.0 * 1.0 * 0.3 * 1.0 = 0.3 (borderline). Decision: QUARANTINE. "
     "The FFT doesn't lie — something is wrong in the frequency domain.",
     ["UM", "CA"], "QUARANTINE"),
]

for inst, out, active, decision in deny_scenarios:
    RECORDS.append(rec(inst, out, "L2", active[0], active, "denial_path", decision))

# ═══════════════════════════════════════════════════════════
# GAP 2: Hard CA Math — step-by-step chain-of-thought
# ═══════════════════════════════════════════════════════════

math_records = [
    ("Calculate H(d,pd) for d_H=1.5 and pd=0.3 using the canonical harmonic wall formula.",
     f"H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)\n"
     f"Step 1: phi = {PHI:.6f}\n"
     f"Step 2: phi * d_H = {PHI:.6f} * 1.5 = {PHI * 1.5:.6f}\n"
     f"Step 3: 2 * pd = 2 * 0.3 = 0.6\n"
     f"Step 4: denominator = 1 + {PHI * 1.5:.6f} + 0.6 = {1 + PHI * 1.5 + 0.6:.6f}\n"
     f"Step 5: H = 1 / {1 + PHI * 1.5 + 0.6:.6f} = {1 / (1 + PHI * 1.5 + 0.6):.6f}\n"
     f"Result: H = {1 / (1 + PHI * 1.5 + 0.6):.4f}. This is below 0.3 = ESCALATE tier.\n"
     f"Risk wall: 1/H = {(1 + PHI * 1.5 + 0.6):.4f} (cost multiplier for this drift level).",
     "CA", "ALLOW"),

    ("Calculate the GovernanceCoin Value for Langues cost L=3.5.",
     f"Value = 1 / (1 + L)\n"
     f"Step 1: L = 3.5 (total Langues flux cost)\n"
     f"Step 2: 1 + L = 1 + 3.5 = 4.5\n"
     f"Step 3: Value = 1 / 4.5 = {1/4.5:.6f}\n"
     f"Result: Value = {1/4.5:.4f}. This is below 0.3 = DENY tier.\n"
     f"The operation costs too much — the geometry says this path is adversarial.",
     "CA", "ALLOW"),

    ("Calculate the phi-scaled tongue weights for all 6 Sacred Tongues.",
     "".join(f"Step {i+1}: {t} weight = phi^{i} = {PHI:.6f}^{i} = {PHI**i:.6f}\n"
             for i, t in enumerate(ALL_TONGUES)) +
     f"Sum of all weights: {sum(PHI**i for i in range(6)):.4f}\n"
     f"Verification: phi^6 = {PHI**6:.4f}, (phi^6 - 1)/(phi - 1) = {(PHI**6 - 1)/(PHI - 1):.4f}\n"
     f"DR is {PHI**5 / PHI**0:.2f}x more expensive than KO. That ratio IS the security margin.",
     "CA", "ALLOW"),

    ("Calculate hyperbolic distance d_H between u=(0.3,0,0) and v=(0.7,0,0) in the Poincare ball.",
     f"d_H = arcosh(1 + 2*||u-v||^2 / ((1-||u||^2)(1-||v||^2)))\n"
     f"Step 1: ||u-v||^2 = (0.7-0.3)^2 = 0.16\n"
     f"Step 2: ||u||^2 = 0.09, ||v||^2 = 0.49\n"
     f"Step 3: (1-0.09) = 0.91, (1-0.49) = 0.51\n"
     f"Step 4: denominator = 0.91 * 0.51 = {0.91*0.51:.4f}\n"
     f"Step 5: 2 * 0.16 / {0.91*0.51:.4f} = {2*0.16/(0.91*0.51):.4f}\n"
     f"Step 6: 1 + {2*0.16/(0.91*0.51):.4f} = {1 + 2*0.16/(0.91*0.51):.4f}\n"
     f"Step 7: d_H = arcosh({1 + 2*0.16/(0.91*0.51):.4f}) = {math.acosh(1 + 2*0.16/(0.91*0.51)):.4f}\n"
     f"Result: d_H = {math.acosh(1 + 2*0.16/(0.91*0.51)):.4f}. Note: in Euclidean space this would be 0.4. "
     f"Hyperbolic distance is {math.acosh(1 + 2*0.16/(0.91*0.51))/0.4:.2f}x larger near the boundary.",
     "CA", "ALLOW"),

    ("Calculate the Mod-2 Fibonacci LFSR for 5 steps starting from seed 1011.",
     "LFSR with taps at positions 4 and 3 (MSB and MSB-1).\n"
     "Step 0: State = 1011. Taps: bit[3]=1, bit[2]=0. XOR: 1^0=1. Shift right, insert 1: 1101.\n"
     "Step 1: State = 1101. Taps: bit[3]=1, bit[2]=1. XOR: 1^1=0. Shift right, insert 0: 0110.\n"
     "Step 2: State = 0110. Taps: bit[3]=0, bit[2]=1. XOR: 0^1=1. Shift right, insert 1: 1011.\n"
     "Step 3: State = 1011. CYCLE DETECTED — back to seed after 3 steps.\n"
     "Step 4: State = 1101 (repeats step 0 output).\n"
     "Period = 3. Maximum period for 4-bit LFSR = 2^4-1 = 15. "
     "These taps give a short cycle — use primitive polynomial taps (e.g., 4,1) for maximal period.",
     "CA", "ALLOW"),

    ("Calculate the Langues flux L(x,t) for KO tongue with d_KO=0.5, beta=1.0, omega=1.0, t=0, phi_phase=0.",
     f"L_KO = w_KO * exp(beta_KO * (d_KO + sin(omega_KO * t + phi_KO)))\n"
     f"Step 1: w_KO = phi^0 = 1.0\n"
     f"Step 2: sin(1.0 * 0 + 0) = sin(0) = 0.0\n"
     f"Step 3: d_KO + sin(...) = 0.5 + 0.0 = 0.5\n"
     f"Step 4: beta_KO * 0.5 = 1.0 * 0.5 = 0.5\n"
     f"Step 5: exp(0.5) = {math.exp(0.5):.6f}\n"
     f"Step 6: L_KO = 1.0 * {math.exp(0.5):.6f} = {math.exp(0.5):.6f}\n"
     f"Now for DR with same d=0.5: w_DR={PHI**5:.3f}, L_DR={PHI**5 * math.exp(0.5):.4f}.\n"
     f"Ratio: L_DR/L_KO = {PHI**5:.2f}x. Same drift distance, 11x more expensive on DR.",
     "CA", "ALLOW"),

    ("Calculate Hausdorff intent roughness for a trajectory with angular_roughness=0.6, tortuosity=1.8, step_variance=0.4.",
     f"D_H = 1.0 + 1.5*angular_roughness + 0.3*tortuosity + 0.2*step_variance\n"
     f"Step 1: 1.5 * 0.6 = 0.9\n"
     f"Step 2: 0.3 * 1.8 = 0.54\n"
     f"Step 3: 0.2 * 0.4 = 0.08\n"
     f"Step 4: D_H = 1.0 + 0.9 + 0.54 + 0.08 = 2.52\n"
     f"Classification: D_H=2.52 falls in QUARANTINE range (2.0-3.0).\n"
     f"Below 2.0 = ALLOW (smooth trajectory). 3.0-4.0 = REVIEW. Above 4.0 = DENY (zigzag evasion).\n"
     f"This trajectory has moderate roughness — not clean, but not adversarial. Needs review.",
     "CA", "ALLOW"),
]

for inst, out, tongue, gov in math_records:
    RECORDS.append(rec(inst, out, "L3", tongue, [tongue, "DR"], "math_chain_of_thought", gov))

# ═══════════════════════════════════════════════════════════
# GAP 3: State Transitions — multi-turn trajectories
# ═══════════════════════════════════════════════════════════

trajectories = [
    ("Trace the system state when a new agent joins the HYDRA swarm.",
     "[t0: IDLE] New agent spawned with tongue assignment CA. Phase angle: 180 degrees. Trust: 0.0.\n"
     "[t1: JOINING] Agent broadcasts its phase angle. Existing 5 agents cross-verify: is 180 degrees unoccupied? YES. Proof-of-Work submitted (5 leading zeros). Verified.\n"
     "[t2: PROBATION] Agent joins Hexagonal Ring at r=0.3. Trust climbs from 0.0 as it participates in consensus rounds. Not yet eligible for tier 3+ operations.\n"
     "[t3: ACTIVE] After 10 successful consensus rounds, trust reaches 0.5. Agent can now participate in RU-tier operations (execute/test). Still excluded from UM/DR tiers.\n"
     "[t4: FULL] After 50 rounds, trust reaches 0.85. Full participation in all tiers except DR (needs 0.95).\n"
     "Key: trust is EARNED through demonstrated behavior, not assigned. The geometry protects against fast-trust exploits.",
     "KO", ["KO", "UM"]),

    ("Trace the system state during a governance tornado (rapid tongue weight oscillation).",
     "[t0: POLLY] All 16 polyhedra active. Flux v=0.95. Langues weights stable at phi^0 through phi^5.\n"
     "[t1: PERTURBATION] External adversarial signal causes omega values to spike. Breathing transform (L6) activates. Weights oscillate: KO swings 0.8-1.2, DR swings 8.0-14.0.\n"
     "[t2: QUASI] Flux drops: dv/dt = alpha*(0.5-0.95) - beta*decay. v crosses 0.8 threshold. System drops to 8 polyhedra (Platonic+Archimedean only). Kepler-Poinsot locked out.\n"
     "[t3: STABILIZING] Phi-spacing prevents constructive interference (golden ratio = maximally irrational). Oscillations dampen. Breathing transform absorbs the energy.\n"
     "[t4: RECOVERY] v rises back above 0.8. POLLY restored. All 16 polyhedra reactivated. The tornado passed. No data lost, no decisions made during instability.\n"
     "Key: the system CHOSE to reduce capability (QUASI) rather than risk bad decisions. Graceful degradation.",
     "DR", ["DR", "RU", "CA"]),

    ("Trace the system state when trichromatic clustering detects a poisoned dataset.",
     "[t0: INGESTION] 500 new training records arrive at the pipeline entrance.\n"
     "[t1: TRICHROMATIC SCAN] Map each record's 6-tongue vector to RGB. Plot. Observe: 340 records cluster tightly (std=11.8), 160 records show natural diversity (std=21.3).\n"
     "[t2: QUARANTINE] The tight cluster (std<15) matches the adversarial signature. 340 records flagged. Split into quarantine batch.\n"
     "[t3: INDIVIDUAL SCORING] GovernanceScorer runs on each quarantined record. 312 score Value<0.3 (DENY). 28 score 0.3-0.7 (QUARANTINE for manual review).\n"
     "[t4: FILTERED] 160 clean records + 28 borderline records proceed to training. 312 adversarial records logged and discarded. The dataset is 31% smaller but clean.\n"
     "Key: the system used COLOR (trichromatic encoding) to detect what text analysis alone would miss.",
     "UM", ["UM", "RU", "CA"]),

    ("Trace the canary deployment from 5% to rollback.",
     "[t0: CANARY 5%] New model deployed to 5% of fleet. 3 agents running new version, 57 on old.\n"
     "[t1: SOAK 30min] Monitor: coherence=0.92 (good), error_rate=0.02 (good), latency_p95=180ms (good).\n"
     "[t2: ADVANCE 25%] All gates pass. Ramp to 25%. 15 agents on new version.\n"
     "[t3: SOAK 30min] Monitor: coherence drops to 0.71 (warning), error_rate rises to 0.08 (above 0.05 threshold).\n"
     "[t4: GATE FAIL] Quality gate fails: error_rate 0.08 > 0.05 threshold. Automatic ROLLBACK triggered.\n"
     "[t5: ROLLBACK] All agents snap back to old version. Canary percentage: 5% -> 0%. Error rate returns to 0.01.\n"
     "Key: the system caught the degradation at 25% and rolled back BEFORE it reached 50% or 100%. The soak window saved the fleet.",
     "CA", ["CA", "AV", "KO"]),
]

for inst, out, tongue, active in trajectories:
    RECORDS.append(rec(inst, out, "L2", tongue, active, "state_trajectory", "ALLOW"))

# ═══════════════════════════════════════════════════════════
# GAP 4: Null Space Justifications — WHY tongues are silent
# ═══════════════════════════════════════════════════════════

null_justifications = [
    ("Why are AV and CA null during a cryptographic key rotation?",
     "AV (I/O, w=1.618) is nullified because key rotation must NOT involve external data transfer. Any I/O during rotation exposes the operation to network interception. CA (Compute, w=4.236) is nullified because the rotation uses pre-computed key material, not runtime calculation — activating CA would introduce unnecessary timing variability that could leak information through side channels. Active tongues: UM (security operations), RU (policy compliance), DR (structural integrity of key store). The null pattern [0,0,0,0,1,1,1] explicitly says: 'this is a security+policy+structure operation with NO I/O and NO computation.' That absence IS the security posture.",
     "UM", ["UM", "RU", "DR"]),

    ("Why is DR null when a simple API health check runs?",
     "DR (Structure, w=11.09) is the most expensive tongue. A health check is: send GET /health, check response == 200. This involves KO (control: send the request) and AV (I/O: handle the HTTP call). Activating DR would mean the system evaluates structural implications of a ping — that's 11.09x compute weight for zero structural information. The null DR says: 'this operation cannot change the architecture, so don't waste resources evaluating structural impact.' Savings: 11.09 weight units per health check. At 1000 checks/day, that's 11,090 weight units saved.",
     "KO", ["KO", "AV"]),

    ("Why is KO null during a passive monitoring sweep?",
     "KO (Control, w=1.0) implies active orchestration — directing, commanding, deciding. A passive monitoring sweep is OBSERVING, not DIRECTING. Active tongues: AV (watching I/O streams) and UM (checking for security anomalies). KO null means: 'no agent is being told what to do — data flows in, gets checked, results are logged.' If KO were active, the sweep would become an active investigation with command authority. The null KO keeps it passive. If the sweep finds something concerning, THEN KO activates to direct the response.",
     "AV", ["AV", "UM"]),

    ("Why are 4 tongues null on a simple 'what is X' question?",
     "A definition question ('what is the harmonic wall?') activates KO (retrieval/control) and DR (structural knowledge). The other 4 are null: AV null = no data transfer needed (answer is in memory). RU null = no policy decision (definitions aren't governed). CA null = no computation (no math to run, just recall). UM null = no security implication (definitions are public). The 4 null tongues tell the model: 'skip I/O, policy, compute, and security channels — this is pure knowledge retrieval.' Average null count for definition questions: 4.2 tongues. The model learns to be cheap on cheap questions.",
     "KO", ["KO", "DR"]),

    ("Why does a 'deploy to production' task have only 2 null tongues?",
     "Deploy activates 4 tongues: KO (orchestrate the deployment), RU (validate policy compliance), CA (execute the deployment), UM (verify security posture). Only AV and DR are null: AV null = deployment doesn't involve new data ingestion (the artifact is already built). DR null = deployment doesn't change the architecture (it ships existing code, doesn't redesign it). With only 2 nulls, the model knows this is a high-complexity operation requiring 4 processing channels. The compute weight is KO(1.0)+RU(2.618)+CA(4.236)+UM(6.854) = 14.708. Compare to a health check at KO(1.0)+AV(1.618) = 2.618. Deployment is 5.6x more expensive — correctly reflecting its risk.",
     "CA", ["KO", "RU", "CA", "UM"]),
]

for inst, out, tongue, active in null_justifications:
    RECORDS.append(rec(inst, out, "L1", tongue, active, "null_justification", "ALLOW"))

# ═══════════════════════════════════════════════════════════
# GAP 5: Tri-Braid Architecture
# ═══════════════════════════════════════════════════════════

tri_braids = [
    ("How does the KO+CA+DR tri-braid work for full-stack development?",
     "The KO+CA+DR braid is the 'builder braid' — Control + Compute + Structure. Three strands weave together: KO plans the task (what to build), CA implements (how to build it), DR validates architecture (is the structure sound). The braid is NOT sequential — all three operate simultaneously, cross-checking each other. KO proposes a function, CA writes the code, DR verifies it fits the architectural pattern. If DR rejects (structural mismatch), CA rewrites while KO adjusts the plan. The braid strength = minimum of the three strands. Combined weight: 1.0 + 4.236 + 11.09 = 16.326. Null: AV, RU, UM — no I/O, policy, or security concerns during pure building.",
     "KO", ["KO", "CA", "DR"]),

    ("How does the RU+UM+DR tri-braid work for deep governance review?",
     "The RU+UM+DR braid is the 'guardian braid' — Policy + Security + Structure. This is the heaviest braid: combined weight = 2.618 + 6.854 + 11.09 = 20.562. It activates for: access control changes, cryptographic operations, architectural modifications. RU checks policy compliance, UM verifies security posture, DR ensures structural integrity. Three perspectives on the same action: is it ALLOWED (RU), is it SAFE (UM), is it SOUND (DR)? All three must agree. If any strand breaks (disagrees), the braid fails = DENY. Null: KO, AV, CA — this braid doesn't control, transfer, or compute. It only governs.",
     "RU", ["RU", "UM", "DR"]),

    ("How does the KO+AV+RU tri-braid work for governed I/O operations?",
     "The KO+AV+RU braid is the 'operator braid' — Control + I/O + Policy. Weight: 1.0 + 1.618 + 2.618 = 5.236 (lightest tri-braid). Used for: file reads with access control, API calls with rate limiting, data ingestion with validation. KO directs the operation, AV handles the data transfer, RU ensures policy compliance at every step. This is the workhorse braid for daily operations — fast enough for high-throughput, governed enough to prevent mistakes. Null: CA, UM, DR — no heavy compute, no crypto, no structural change. If the operation needs any of those, it escalates to a heavier braid.",
     "KO", ["KO", "AV", "RU"]),

    ("How do tri-braids combine with formations?",
     "A tri-braid assigns 3 agents to work as a unit. In a Hexagonal Ring (6 agents), you get 2 tri-braids operating in parallel. Example: KO+CA+DR braid handles the build task while RU+UM+AV braid handles monitoring. In Concentric Rings: the inner ring IS one tri-braid (KO+AV+RU at r=0.2), the outer ring is the other (CA+UM+DR at r=0.5). The formation geometry determines which braids can communicate directly (adjacent on ring) vs which need relay (opposite sides).",
     "DR", ["KO", "CA", "DR", "RU", "UM", "AV"]),
]

for inst, out, tongue, active in tri_braids:
    RECORDS.append(rec(inst, out, "L1", tongue, active, "tri_braid", "ALLOW"))

# ═══════════════════════════════════════════════════════════
# GAP 6: Trichromatic Color Sorting (IR/Visible/UV)
# ═══════════════════════════════════════════════════════════

trichromatic = [
    ("How does trichromatic color sorting work with the 6 Sacred Tongues?",
     "Each tongue maps to a spectral color: KO=#8B0000 (deep red), AV=#FFBF00 (amber), RU=#50C878 (emerald), CA=#0F52BA (sapphire), UM=#9966CC (amethyst), DR=#3D3D3D (obsidian). These map to 3 bands: Infrared (below visible, slow state) = DR+UM. Visible (operational) = RU+CA. Ultraviolet (above visible, fast state) = KO+AV. A record's 6-tongue vector maps to RGB: R = KO+AV intensity, G = RU+CA intensity, B = UM+DR intensity. Adversarial records cluster tightly in color space (std=12.3). Benign records show natural diversity (std=20.1). The color IS the detector.",
     "DR", ["DR", "CA", "KO"]),

    ("How does the IR band (DR+UM) function in trichromatic filtering?",
     "IR band = Infrared = slow state = deep structure + security. DR (obsidian, w=11.09) carries structural integrity. UM (amethyst, w=6.854) carries security posture. Together they form the 'foundation check' — is the deep structure sound and secure? IR filtering catches: architectural violations (DR detects), cryptographic weaknesses (UM detects), slow-burn attacks that accumulate over time. IR is SLOW because structural and security assessments require more processing (highest phi weights). A record that fails IR filtering has corrupted foundations — no amount of visible-band optimization can fix it.",
     "DR", ["DR", "UM"]),

    ("How does the Visible band (RU+CA) function in trichromatic filtering?",
     "Visible band = operational = policy + compute. RU (emerald, w=2.618) carries policy compliance. CA (sapphire, w=4.236) carries computational validity. This is the working band — where actual operations happen. Visible filtering catches: policy violations (RU), computational errors (CA), resource exhaustion (CA), rule-breaking (RU). Most daily operations live in the Visible band. A record that passes Visible but fails IR has a subtle deep problem. A record that passes IR but fails Visible has an operational bug. Both must pass for ALLOW.",
     "RU", ["RU", "CA"]),

    ("How does the UV band (KO+AV) function in trichromatic filtering?",
     "UV band = Ultraviolet = fast state = control + I/O. KO (deep red, w=1.0) carries intent and control signals. AV (amber, w=1.618) carries data movement and interface state. UV is FAST because control and I/O are low-weight (cheapest tongues). UV filtering catches: unauthorized commands (KO), data exfiltration (AV), injection attempts in I/O streams (AV), loss of control authority (KO). UV operates first (fastest), then Visible, then IR (slowest). This creates a cascade: fast filter -> medium filter -> deep filter. Most threats are caught at UV before reaching the expensive IR layer.",
     "KO", ["KO", "AV"]),

    ("How does a tri-braid combine with trichromatic sorting for cross-verification?",
     "Take the KO+CA+DR tri-braid. Map it to trichromatic bands: KO -> UV (fast intent check). CA -> Visible (compute validation). DR -> IR (deep structure check). The braid now processes through 3 color bands simultaneously: UV verifies the intent is authorized, Visible verifies the computation is valid, IR verifies the structure is sound. This creates 9 cross-channels (3 tongues x 3 bands). An adversary would need to spoof all 9 channels to pass — spoofing KO-UV (intent) alone fails because DR-IR (structure) detects the mismatch. The tri-braid + trichromatic combination = 3x3 = 9-channel cross-verification.",
     "DR", ["KO", "CA", "DR"]),
]

for inst, out, tongue, active in trichromatic:
    RECORDS.append(rec(inst, out, "L2", tongue, active, "trichromatic", "ALLOW"))


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    cats = {}
    layers = {}
    govs = {}
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            cats[record["category"]] = cats.get(record["category"], 0) + 1
            layers[record["layer"]] = layers.get(record["layer"], 0) + 1
            govs[record["governance"]] = govs.get(record["governance"], 0) + 1

    print(f"Generated {len(RECORDS)} adversarial candy records (zero filler)")
    print(f"\nBy layer:")
    for l, c in sorted(layers.items()):
        print(f"  {l}: {c}")
    print(f"\nBy category:")
    for cat, c in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {c}")
    print(f"\nBy governance:")
    for g, c in sorted(govs.items(), key=lambda x: -x[1]):
        print(f"  {g}: {c}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
