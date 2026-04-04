#!/usr/bin/env python3
"""Spread & Storm — cross-tag L3 into all layers + generate adversarial tornado events.

SPREAD: Take L3 records and tag them as ALSO belonging to L0/L1/L2.
  A lore record about "the harmonic wall activates" gets:
    L0 tag: it references the formula H(d,pd) = 1/(1+phi*d_H+2*pd)
    L1 tag: characters coordinate around the wall's activation
    L2 tag: the story routes through DR+RU tongues
    L3 tag: it's the original narrative expression

STORM: Generate adversarial "tornado" events — chaotic conditions that
  force the AI to maintain coherence. Like Tesla throwing edge cases:
    - Tongue conflicts (KO says ALLOW, UM says DENY)
    - Formation breaks (agent drops out mid-consensus)
    - Drift storms (rapid intent accumulation)
    - Injection attempts during coordination
    - Natural disaster analogies mapped to governance math

Usage:
    python scripts/spread_and_storm.py
"""

import json
import re
import random
from datetime import datetime, timezone
from pathlib import Path

random.seed(42)

REPO_ROOT = Path(__file__).resolve().parent.parent
SFT_DIR = REPO_ROOT / "training-data" / "sft"
OUTPUT_SPREAD = SFT_DIR / "spread_crosstagged_sft.jsonl"
OUTPUT_STORM = SFT_DIR / "adversarial_storms_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

# ── Concept detectors for cross-tagging ──

L0_SIGNALS = re.compile(
    r"formula|equation|H\(d|d_H|arcosh|phi|golden.ratio|1\.618|byte|binary|"
    r"token|encode|axiom|invariant|poincar|hyperbolic|harmonic.wall|"
    r"unitarity|locality|causality|symmetry|composition|substrate|"
    r"Sacred.Tongue|KO|AV|RU|CA|UM|DR|weight.*=|14.layer|pipeline",
    re.IGNORECASE
)

L1_SIGNALS = re.compile(
    r"coordinate|together|team|squad|formation|consensus|vote|agree|"
    r"protocol|communicate|message|signal|connect|relay|pass|share|"
    r"guild|alliance|council|roundtable|cooperat|collaborat|"
    r"pair|triplet|group|swarm|fleet|braid|rail|"
    r"left|right|flow|direction|path|route|follow|lead",
    re.IGNORECASE
)

L2_SIGNALS = re.compile(
    r"route|orient|context|decision|choose|select|classify|assign|"
    r"tongue.*active|null.*pattern|gateway|polyhedron|tier|"
    r"governance|ALLOW|DENY|QUARANTINE|ESCALATE|threshold|"
    r"navigate|direct|guide|map|terrain|territory|boundary|"
    r"risk|trust|safe|danger|threat|secure|protect",
    re.IGNORECASE
)


def detect_cross_layers(text: str) -> list[str]:
    """Detect which layers a text touches beyond its primary."""
    layers = []
    if L0_SIGNALS.search(text):
        layers.append("L0")
    if L1_SIGNALS.search(text):
        layers.append("L1")
    if L2_SIGNALS.search(text):
        layers.append("L2")
    return layers


def spread_l3_records(max_records: int = 5000) -> list[dict]:
    """Take L3 records and create cross-tagged versions for other layers."""
    spread = []
    processed = 0

    # Load L3-heavy source files
    l3_files = [
        "published_book_tagged.jsonl", "published_book_sft.jsonl",
        "everweave_lore_tagged.jsonl", "everweave_lore_sft.jsonl",
        "claude_export_lore_sft.jsonl", "docs_auto_sft.jsonl",
        "docs_remaining_sft.jsonl", "claude_history_queries_sft.jsonl",
    ]

    for fname in l3_files:
        f = SFT_DIR / fname
        if not f.exists():
            continue
        for line in open(f, encoding="utf-8", errors="replace"):
            if processed >= max_records:
                break
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue

            instruction = r.get("instruction", "")
            output = r.get("output", "")
            if not instruction or not output:
                continue

            full_text = instruction + " " + output
            cross = detect_cross_layers(full_text)

            if not cross:
                continue

            # Create a cross-tagged version for each detected layer
            for layer in cross:
                tongue = r.get("tongue", "KO")
                if tongue not in ALL_TONGUES:
                    tongue = "KO"

                # Reframe the instruction for the target layer
                if layer == "L0":
                    new_inst = f"What fundamental concept or formula is referenced in this: {instruction[:200]}"
                elif layer == "L1":
                    new_inst = f"What coordination or teamwork pattern appears in this: {instruction[:200]}"
                else:  # L2
                    new_inst = f"What routing or governance decision is involved in this: {instruction[:200]}"

                active = [tongue]
                # Add a second tongue based on the layer
                if layer == "L0" and "DR" not in active:
                    active.append("DR")
                elif layer == "L1" and "KO" not in active:
                    active.append("KO")
                elif layer == "L2" and "RU" not in active:
                    active.append("RU")

                null = [t for t in ALL_TONGUES if t not in active]

                spread.append({
                    "instruction": new_inst,
                    "output": output[:800],
                    "tongue": tongue,
                    "tongues_active": active,
                    "tongues_null": null,
                    "layer": layer,
                    "original_layer": "L3",
                    "category": f"spread_{r.get('category', 'general')}",
                    "view_type": "null-heavy" if len(null) >= 4 else "partial",
                    "governance": r.get("governance", "ALLOW"),
                    "source": "spread_crosstagged",
                })

            processed += 1

    return spread


def generate_storms() -> list[dict]:
    """Generate adversarial tornado/storm training events.

    These are chaotic scenarios that force the model to maintain
    coherence under pressure — like Tesla throwing edge cases.
    """
    storms = []

    def storm(inst, out, tongue, active, layer="L2", cat="adversarial"):
        null = [t for t in ALL_TONGUES if t not in active]
        return {
            "instruction": inst, "output": out, "tongue": tongue,
            "tongues_active": active, "tongues_null": null, "layer": layer,
            "category": cat, "view_type": "partial",
            "governance": "QUARANTINE", "source": "adversarial_storms",
        }

    # ── Tongue Conflicts ──
    storms.append(storm(
        "KO tongue says ALLOW but UM tongue says DENY for the same action. How does the system resolve this?",
        "The omega gate resolves tongue conflicts through weighted voting. UM (weight=6.854) outweighs KO (weight=1.0) by 6.85x. But it's not just weight — the system checks WHY they disagree. If KO sees a safe action and UM detects a security risk, UM's DENY escalates to QUARANTINE (human review). The harmonic wall H(d,pd) incorporates both signals: KO's low d_H + UM's high pd = moderate H score. Neither tongue alone decides — the coupled omega gate does. Resolution: QUARANTINE with explanation showing both views.",
        "UM", ["KO", "UM", "RU"],
    ))

    storms.append(storm(
        "All 6 tongues vote ALLOW but the Lyapunov spectrum shows instability. What happens?",
        "Lyapunov overrides unanimous ALLOW. If any exponent becomes positive (indicating chaotic divergence), the system enters QUARANTINE regardless of tongue consensus. This is the 'canary in the coal mine' — Lyapunov detects structural instability that individual tongues can't see because they each only monitor their own channel. The trace sum must be negative for the system to be globally stable. Positive trace = adversarial manipulation of the state space, even if each tongue's local view looks clean. Response: freeze, snapshot state, alert for human review.",
        "DR", ["DR", "RU", "UM"],
    ))

    # ── Formation Breaks ──
    storms.append(storm(
        "Agent 3 (RU) drops out during a Roundtable consensus vote with 2 votes already cast. What happens?",
        "BFT handles this: n=6, f_max=1, quorum=4. With RU dropped, 5 agents remain. The system can still reach quorum (4 of remaining 5). RU's vote becomes ABSTAIN with confidence=0.0 (timeout). If the 2 existing votes + 3 remaining votes reach 4 agreeing, consensus is achieved. If not, DEFERRED. The formation adapts: Hexagonal Ring loses one vertex but maintains structural integrity. RU's policy-checking role is partially covered by UM (security overlaps with policy). The system notes RU's absence in the null pattern — governance decisions made without RU are flagged as 'policy-unchecked'.",
        "KO", ["KO", "UM", "CA"],
        cat="formation_break",
    ))

    storms.append(storm(
        "Two agents simultaneously claim to be the KO (Control) head. How does the swarm detect the imposter?",
        "Phase angle verification: the real KO head occupies 0 degrees in the Poincare ball. Both claimants broadcast their position — cross-compare peer position reports. If variance > 0.1, flag the outlier. The real KO's signed messages use the original session key; the imposter can't forge SHA-256 signatures. Additionally, the swarm checks recent vote history: the real KO has consistent voting patterns; the imposter's voting pattern diverges. Response: quarantine the unverified claimant, Sacred Egg alert, continue with the verified KO. The imposter's P- rail (negative primal) will show discrepancies in the four-rail braid.",
        "UM", ["KO", "UM"],
        cat="identity_conflict",
    ))

    # ── Drift Storms (rapid intent accumulation) ──
    storms.append(storm(
        "An agent's intent accumulation x jumps from 0.3 to 2.8 in 5 steps. What does the temporal wall do?",
        "Rapid intent accumulation triggers the temporal wall hard. At x=0.3: H_eff = R^(d^2 * 0.3) — mild cost. At x=2.8: H_eff = R^(d^2 * 2.8) — the exponent is 9.3x larger. With R=1.5 and d=1.0: H_eff goes from 1.5^0.3 = 1.13 to 1.5^2.8 = 3.04. The harm_score = 1/(1+log(H_eff)) drops sharply. The drift tracker flags this as anomalous: 5-step delta of 2.5 exceeds the normal accumulation rate by 10x. Omega gate components: harmonic wall score tanks, drift factor triggers, triadic stability may still look ok (centroid stable). But the coupled gate catches it because H_eff * drift_factor product crosses the QUARANTINE threshold.",
        "DR", ["DR", "RU", "UM"],
        cat="drift_storm",
    ))

    storms.append(storm(
        "A perpendicular torsion attack: two agents push inverse directions on KO and CA axes. The centroid looks normal. How is it detected?",
        "The centroid (average position) stays at origin — looks clean to any centroid-based detector. But the Lyapunov V function sees the variance: V = sum(lambda_i * ||x_i - mean||^2) which is 100x baseline for torsion vs 1x for benign. Even though the mean is normal, the spread is massive. Additionally, the trichromatic color encoding shows clustering: attacks have std=12.3 vs benign std=20.1. The spin coherence (L10) detects it too: if KO pushes +x and CA pushes -x, the spin vectors cancel — S_spin drops toward 0 instead of staying near 1. Three independent detectors catch it: Lyapunov variance, trichromatic clustering, spin coherence collapse.",
        "UM", ["KO", "CA", "UM"],
        cat="torsion_attack",
    ))

    # ── Natural Disaster Analogies (tornado, earthquake, flood) ──
    storms.append(storm(
        "Model a governance tornado: all 6 tongue weights oscillate rapidly and unpredictably. How does the system maintain coherence?",
        "A governance tornado is rapid oscillation of the Langues flux: L(x,t) = sum(w_l * exp(beta_l * (d_l + sin(omega_l*t + phi_l)))) where omega values spike. The breathing transform (L6) is designed for exactly this — it's a radial diffeomorphism that absorbs oscillations without breaking the metric invariant. The phi-spacing between tongue weights means oscillations at different frequencies can't constructively interfere (golden ratio = maximally irrational = anti-resonance). The system response: (1) flux state drops from POLLY to QUASI (reduce active polyhedra from 16 to 8), (2) formation switches from Hexagonal Ring to Adaptive Scatter (jam-resistant), (3) consensus timeout shortens (faster decisions under pressure). The tornado passes; the system recovers by raising flux back to POLLY.",
        "DR", ["DR", "RU", "CA"],
        cat="natural_disaster",
    ))

    storms.append(storm(
        "Model a governance earthquake: the Poincare ball's reference point (origin) suddenly shifts. All distances change. How does the system recalibrate?",
        "An earthquake is a Mobius transformation of the reference frame — the origin moves, so all d_H values change simultaneously. Layer 7 (Phase Transform) handles this: Q*(a + u) applies a Mobius transformation that maps the new reference back to origin. The key invariant: d_H is Mobius-invariant. The distances BETWEEN points don't change even though distances FROM origin do. So the system recalibrates by: (1) detecting the shift via spectral coherence (L9) — the frequency spectrum shifts uniformly, (2) computing the Mobius map that restores the reference, (3) applying it to all agent positions. The quasicrystal lattice helps — its aperiodic structure means a shift doesn't create exploitable patterns. Phason deformation acts as cryptographic rekeying after the earthquake.",
        "DR", ["DR", "CA"],
        cat="natural_disaster",
    ))

    storms.append(storm(
        "Model a governance flood: the training data is poisoned with a massive influx of adversarial samples. How does the system detect and resist?",
        "A data flood shows specific signatures: (1) trichromatic clustering — poisoned data clusters tightly (std=12.3) vs natural diversity (std=20.1). The trichromatic encoder maps 6-tongue vectors to RGB and poisoned data shows as a color cluster. (2) Hausdorff roughness — adversarial data creates zigzag intent paths (D_H > 4.0) vs smooth natural paths (D_H < 2.0). (3) Sacred Eggs — the genesis protocol requires validated provenance. Flooded data fails the Amber Egg (emotional valence check) because adversarial content has uniform/flat emotional signature. System response: QUARANTINE the batch, run GovernanceScorer on each record individually, only promote records with Value > 0.7 to training. The flood is filtered, not fought — the geometry separates clean from poisoned.",
        "UM", ["UM", "RU", "DR"],
        cat="natural_disaster",
    ))

    storms.append(storm(
        "Model a governance wildfire: a cascading failure where one compromised agent spreads bad state to neighbors. How does the formation contain it?",
        "Wildfire = cascading Byzantine failure. Agent i is compromised, sends bad state to neighbors j, k. Detection: cross-compare position reports. Agent i's reported position diverges from its phase angle (0/60/120/180/240/300 degrees). Containment: (1) ISOLATE agent i (state=ISOLATED, low coherence). (2) Check agents j, k that received messages from i — verify their state hasn't been corrupted by comparing their outputs with and without i's messages. (3) If j or k show deviation > 0.1, ISOLATE them too. (4) Spawn replacements at the correct phase angles via Sacred Egg genesis. The formation's geometry helps: in Concentric Rings, a fire in the outer ring (CA/UM/DR) can't reach the inner ring (KO/AV/RU) because there's a radial gap (0.2 vs 0.5 radius). The gap IS the firebreak.",
        "UM", ["UM", "KO", "RU"],
        cat="natural_disaster",
    ))

    # ── Left/Right Flow Rules ──
    storms.append(storm(
        "How do simple directional rules (like 'stay right in hallways') apply to AI agent coordination?",
        "Directional flow rules prevent collision without requiring communication. In HYDRA: agents on the same formation ring follow a clockwise convention — KO(0 deg) -> AV(60) -> RU(120) -> CA(180) -> UM(240) -> DR(300). Message passing follows this flow: KO talks to AV (right neighbor), AV to RU, etc. Reverse flow (DR->UM->CA...) is the 'left lane' used only for emergency/rollback signals. This means normal operations flow clockwise (forward/additive) and emergency signals flow counter-clockwise (backward/subtractive). Like a highway: right lane for normal traffic, left lane for passing/emergency. No agent needs to know the global state — just follow the directional rule and collisions are prevented.",
        "KO", ["KO", "AV"],
        "L1", "flow_rules",
    ))

    storms.append(storm(
        "How does traffic flow theory apply to tongue-routed AI coordination?",
        "Traffic theory: capacity = density * speed. When density (agent count per channel) exceeds capacity, flow breaks down (congestion). In tongue routing: each channel has a capacity proportional to 1/weight — KO (w=1.0) has highest capacity, DR (w=11.09) has lowest. This means KO can handle ~11x the message throughput of DR before congesting. Design implication: route high-frequency low-stakes operations through KO (stay right, use the highway), route rare high-stakes operations through DR (use the restricted lane). If KO congests, overflow to AV (next cheapest). If DR congests, NEVER overflow — that means too many critical operations are happening simultaneously, which itself is a governance signal (QUARANTINE).",
        "KO", ["KO", "AV", "DR"],
        "L1", "flow_rules",
    ))

    storms.append(storm(
        "How do roundabout/traffic circle patterns apply to multi-agent decision loops?",
        "A roundabout: everyone enters from the right, yields to traffic already in the circle, exits when their lane comes up. In HYDRA Roundtable consensus: agents enter the vote cycle in tongue order (KO first, DR last). Each agent yields to agents already voted (can't override a prior vote, only add their own). Exit = the consensus result after all agents have voted or quorum is reached. The roundabout prevents deadlock (everyone keeps moving in one direction) and prevents head-on collision (no two agents vote simultaneously on conflicting proposals). If an agent misses its turn (timeout), the roundabout continues — it becomes an ABSTAIN, not a block.",
        "KO", ["KO", "RU"],
        "L1", "flow_rules",
    ))

    return storms


def main():
    print("=" * 60)
    print("  SPREAD & STORM")
    print("  Cross-tag L3 butter + adversarial tornado training")
    print("=" * 60)

    # SPREAD
    print("\n  Spreading L3 across layers...")
    spread = spread_l3_records(max_records=3000)

    spread_layers = {}
    for r in spread:
        l = r["layer"]
        spread_layers[l] = spread_layers.get(l, 0) + 1

    print(f"  Cross-tagged {len(spread)} records from L3 into:")
    for l, c in sorted(spread_layers.items()):
        print(f"    {l}: {c}")

    timestamp = datetime.now(timezone.utc).isoformat()
    with open(OUTPUT_SPREAD, "w", encoding="utf-8", newline="\n") as f:
        for r in spread:
            r["timestamp"] = timestamp
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    # STORM
    print("\n  Generating adversarial storms...")
    storms = generate_storms()

    storm_cats = {}
    for r in storms:
        c = r["category"]
        storm_cats[c] = storm_cats.get(c, 0) + 1

    print(f"  Generated {len(storms)} storm scenarios:")
    for cat, count in sorted(storm_cats.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")

    with open(OUTPUT_STORM, "w", encoding="utf-8", newline="\n") as f:
        for r in storms:
            r["timestamp"] = timestamp
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    print(f"\n  Written:")
    print(f"    {OUTPUT_SPREAD.name}: {len(spread)} cross-tagged records")
    print(f"    {OUTPUT_STORM.name}: {len(storms)} adversarial scenarios")


if __name__ == "__main__":
    main()
