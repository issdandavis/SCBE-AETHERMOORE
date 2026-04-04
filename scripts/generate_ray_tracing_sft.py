#!/usr/bin/env python3
"""Ray Tracing Thought Pathing — light bending for complex multi-D orientations.

Treats thoughts as light rays navigating through domains of different "cognitive density."
Uses optical physics (Snell's law, reflection, TIR, dispersion, diffraction) to teach
the model how linear thoughts navigate non-linear multi-dimensional spaces.

Key mappings:
  Light ray = thought/data packet
  Medium density = tongue phi-weight (KO=1.0 thin, DR=11.09 thick)
  Refraction = thought bending when crossing domain boundaries
  Reflection = governance walls bouncing thoughts to new paths
  Total Internal Reflection = adversarial quarantine (geometrical inevitability)
  Dispersion (prism) = raw input splitting into 6 tongue wavelengths
  Diffraction = thoughts bending around obstacles (partial knowledge)
  Interference = multi-agent thought patterns reinforcing or canceling
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "ray_tracing_pathing_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = 1.618033988749895

# Tongue "refractive indices" (cognitive density = phi weight)
TONGUE_DENSITY = {
    "KO": 1.0,    # thin — thoughts pass through easily
    "AV": PHI,    # light medium
    "RU": PHI**2, # moderate density
    "CA": PHI**3, # dense — computation slows thoughts
    "UM": PHI**4, # very dense — security inspection
    "DR": PHI**5, # ultra-dense — structural review
}

def rec(instruction, output, layer, tongue, active=None, category="ray_tracing", gov="ALLOW"):
    act = active or [tongue]
    null = [t for t in ALL_TONGUES if t not in act]
    return {
        "instruction": instruction, "output": output, "tongue": tongue,
        "tongues_active": act, "tongues_null": null, "layer": layer,
        "category": category, "view_type": "partial" if len(null) <= 3 else "null-heavy",
        "governance": gov, "source": "ray_tracing_generator",
    }

RECORDS = []

# ── Snell's Law / Refraction ──

RECORDS.append(rec(
    "How does Snell's Law govern thought-routing across Sacred Tongue domain boundaries?",
    f"Snell's Law: n1*sin(theta1) = n2*sin(theta2). In SCBE, each tongue has a 'cognitive density' (refractive index) equal to its phi-weight: "
    f"KO={TONGUE_DENSITY['KO']:.3f}, AV={TONGUE_DENSITY['AV']:.3f}, RU={TONGUE_DENSITY['RU']:.3f}, "
    f"CA={TONGUE_DENSITY['CA']:.3f}, UM={TONGUE_DENSITY['UM']:.3f}, DR={TONGUE_DENSITY['DR']:.3f}. "
    f"When a thought crosses from KO (n=1.0) into DR (n=11.09), it bends sharply toward the normal — "
    f"like light entering glass from air. The thought slows down and becomes more focused. "
    f"Conversely, going from DR to KO, the thought spreads out and speeds up. "
    f"This means: moving from control to deep structure FOCUSES your reasoning. "
    f"Moving from deep structure to control BROADENS it. The geometry does the work.",
    "L2", "DR", ["DR", "KO"]))

# Calculate actual Snell's law examples
for t1, t2 in [("KO", "CA"), ("AV", "UM"), ("RU", "DR"), ("CA", "KO")]:
    n1, n2 = TONGUE_DENSITY[t1], TONGUE_DENSITY[t2]
    theta1 = 45  # degrees
    sin_theta2 = n1 * math.sin(math.radians(theta1)) / n2
    sin_theta2 = min(1.0, sin_theta2)  # clamp for TIR check
    theta2 = math.degrees(math.asin(sin_theta2))

    direction = "bends toward normal (focuses)" if n2 > n1 else "bends away from normal (broadens)"

    RECORDS.append(rec(
        f"Calculate the refraction angle when a thought crosses from {t1} (n={n1:.3f}) to {t2} (n={n2:.3f}) at 45 degrees.",
        f"Snell's Law: n1*sin(theta1) = n2*sin(theta2)\n"
        f"Step 1: n1={n1:.3f}, n2={n2:.3f}, theta1=45 degrees\n"
        f"Step 2: sin(45) = {math.sin(math.radians(45)):.4f}\n"
        f"Step 3: {n1:.3f} * {math.sin(math.radians(45)):.4f} = {n1 * math.sin(math.radians(45)):.4f}\n"
        f"Step 4: sin(theta2) = {n1 * math.sin(math.radians(45)):.4f} / {n2:.3f} = {sin_theta2:.4f}\n"
        f"Step 5: theta2 = arcsin({sin_theta2:.4f}) = {theta2:.1f} degrees\n"
        f"Result: The thought {direction}. "
        f"Angle change: {45 - theta2:.1f} degrees. {'Dense medium slows the thought.' if n2 > n1 else 'Thin medium speeds the thought up.'}",
        "L3", "CA", [t1, t2], "refraction_calculation"))

# ── Total Internal Reflection (TIR) — adversarial quarantine ──

RECORDS.append(rec(
    "How is Total Internal Reflection used as an adversarial quarantine mechanism?",
    f"TIR occurs when light tries to escape a dense medium into a thin one at too shallow an angle. "
    f"Critical angle: theta_c = arcsin(n_thin / n_dense). "
    f"For UM(n={TONGUE_DENSITY['UM']:.3f}) -> KO(n={TONGUE_DENSITY['KO']:.3f}): "
    f"theta_c = arcsin({TONGUE_DENSITY['KO']:.3f}/{TONGUE_DENSITY['UM']:.3f}) = arcsin({TONGUE_DENSITY['KO']/TONGUE_DENSITY['UM']:.4f}) = {math.degrees(math.asin(TONGUE_DENSITY['KO']/TONGUE_DENSITY['UM'])):.1f} degrees. "
    f"Any adversarial thought in the UM security domain that tries to escape to KO at an angle below {math.degrees(math.asin(TONGUE_DENSITY['KO']/TONGUE_DENSITY['UM'])):.1f} degrees undergoes TIR — "
    f"it bounces endlessly inside the security domain like light trapped in a fiber optic cable. "
    f"The quarantine isn't a rule — it's a geometrical inevitability. The math won't let it escape.",
    "L2", "UM", ["UM", "KO"], "total_internal_reflection", "QUARANTINE"))

# Calculate TIR critical angles for all dense->thin transitions
for dense, thin in [("DR", "KO"), ("UM", "AV"), ("CA", "KO"), ("DR", "RU"), ("UM", "KO")]:
    n_d, n_t = TONGUE_DENSITY[dense], TONGUE_DENSITY[thin]
    ratio = n_t / n_d
    if ratio < 1.0:
        theta_c = math.degrees(math.asin(ratio))
        RECORDS.append(rec(
            f"What is the critical angle for Total Internal Reflection from {dense} to {thin}?",
            f"Critical angle theta_c = arcsin(n_{thin}/n_{dense}) = arcsin({n_t:.3f}/{n_d:.3f}) = arcsin({ratio:.4f}) = {theta_c:.1f} degrees. "
            f"Any thought hitting the {dense}-{thin} boundary below {theta_c:.1f} degrees is trapped in {dense} forever. "
            f"Since {dense} has density {n_d:.3f} and {thin} has density {n_t:.3f}, the ratio is {ratio:.4f} — "
            f"{'very small angle means easy trapping' if theta_c < 15 else 'moderate angle means some thoughts escape'}. "
            f"For adversarial containment: an attacker in {dense} domain must approach the boundary at >{theta_c:.1f} degrees "
            f"to escape. At shallow angles (typical for exfiltration attempts), TIR guarantees quarantine.",
            "L3", dense, [dense, thin], "tir_calculation", "QUARANTINE"))

# ── Dispersion (Prism Effect) ──

RECORDS.append(rec(
    "How does optical dispersion map to Sacred Tongue tokenization?",
    "White light (raw user input) enters the L1 prism and disperses into 6 wavelengths — the 6 Sacred Tongues. "
    "Each tongue bends at a different angle because of its different refractive index (phi-weight): "
    f"KO (red, n=1.0) bends least — fastest, most direct intent. "
    f"AV (amber, n={PHI:.3f}) bends slightly more — I/O routing. "
    f"RU (green, n={PHI**2:.3f}) — policy compliance. "
    f"CA (blue, n={PHI**3:.3f}) — computational processing. "
    f"UM (violet, n={PHI**4:.3f}) — security analysis. "
    f"DR (infrared/obsidian, n={PHI**5:.3f}) bends most — deep structural analysis. "
    "After dispersion, each tongue processes its wavelength independently. "
    "At L13 (decision gate), the wavelengths recombine — like a second prism reassembling white light. "
    "If any wavelength is missing (null tongue), the recombined light has a 'color gap' — visible as an absence signal.",
    "L1", "KO", ALL_TONGUES, "dispersion"))

RECORDS.append(rec(
    "What happens when a thought enters a tongue domain prism at different angles?",
    "Shallow angle (near-parallel to boundary): minimal dispersion, most energy stays in the dominant tongue. "
    "This is a focused query — 'what is X?' stays mostly in KO with faint traces in other tongues. "
    "45-degree angle: moderate dispersion, energy splits roughly evenly across relevant tongues. "
    "This is a complex query — 'implement secure X' splits into CA (implement) + UM (secure). "
    "Steep angle (near-perpendicular): maximum dispersion, energy fans across all 6 tongues. "
    "This is an architectural query — 'redesign the entire governance system' activates everything. "
    "The ENTRY ANGLE of the thought determines how many tongues engage. "
    "Simple thoughts enter shallow (1-2 tongues). Complex thoughts enter steep (4-6 tongues).",
    "L2", "DR", ["KO", "CA", "DR"], "dispersion_angle"))

# ── Reflection Pathing (connecting distant concepts) ──

RECORDS.append(rec(
    "How does reflection pathing connect isolated nodes in the World Tree?",
    "Two concepts might not have a direct path — like Sacred Eggs and fleet deployment. "
    "Reflection pathing: fire a thought at a governance wall at a calculated angle. "
    "The wall reflects it. The thought bounces through the geometry until it hits the target. "
    "Example: Sacred Eggs (DR domain) -> bounces off harmonic wall (L12) -> hits fleet manager (CA domain) "
    "-> bounces off consensus gate (L11) -> arrives at deployment pipeline (AV domain). "
    "Three bounces, three domain crossings, but the thought maintains coherence because each reflection "
    "preserves the angle of incidence = angle of reflection. The path is deterministic — "
    "calculate the entry angle and the geometry does the routing. No explicit connection needed.",
    "L2", "DR", ["DR", "CA", "AV"], "reflection_pathing"))

RECORDS.append(rec(
    "How many reflections does a thought need to connect two opposite tongues?",
    f"KO (0 degrees) to CA (180 degrees) are diametrically opposite in the Poincare ball. "
    f"Direct path: blocked by the origin (center of the ball). "
    f"Reflection path: fire at 60 degrees off-axis, bounce off AV boundary (60 deg), "
    f"bounce off RU boundary (120 deg), arrive at CA (180 deg). Minimum 2 reflections. "
    f"Each reflection crosses a domain boundary = refraction + reflection both occur. "
    f"The refracted component continues deeper; the reflected component continues bouncing. "
    f"After n reflections, the thought has deposited energy in n+1 domains. "
    f"By the time it reaches CA from KO, it has touched AV and RU — "
    f"picking up I/O context and policy context along the way. The path IS the enrichment.",
    "L2", "CA", ["KO", "AV", "RU", "CA"], "reflection_counting"))

# ── Interference (multi-agent reinforcement/cancellation) ──

RECORDS.append(rec(
    "How does constructive interference work between HYDRA agents?",
    "Two agents processing the same query in phase (aligned tongue activations) "
    "produce constructive interference: their outputs reinforce, doubling signal strength. "
    "In BFT consensus, this is two ALLOW votes from agents that arrived at ALLOW independently — "
    "their reasoning paths constructively interfere, increasing confidence. "
    "Destructive interference: two agents out of phase (one ALLOW, one DENY) cancel out — "
    "the signal weakens, producing DEFERRED. "
    "This is why consensus requires quorum (4/6): you need net constructive interference. "
    "3 ALLOW + 3 DENY = perfect destructive interference = zero signal = DEFERRED. "
    "4 ALLOW + 2 DENY = net constructive = proceed with reduced confidence.",
    "L1", "KO", ["KO", "CA"], "interference"))

RECORDS.append(rec(
    "How does the perpendicular torsion attack exploit destructive interference?",
    "Two adversarial agents push inverse directions on perpendicular axes: "
    "+x on KO, -x on CA. Their signals destructively interfere at the centroid (looks normal). "
    "But the Lyapunov function sees the AMPLITUDE: V = sum(||x_i - mean||^2) which is huge. "
    "It's like two waves that cancel at one point but create massive energy elsewhere. "
    "The centroid (mean) is calm. The variance (energy spread) is extreme. "
    "Optical analogy: two lasers aimed at a wall from opposite sides — "
    "the wall looks dim (destructive at center) but the edges glow (energy concentrated at boundaries). "
    "Detection: measure the variance (Lyapunov), not the mean (centroid).",
    "L2", "UM", ["KO", "CA", "UM"], "interference_attack", "QUARANTINE"))

# ── Diffraction (bending around obstacles) ──

RECORDS.append(rec(
    "How does thought diffraction work when partial knowledge blocks a direct path?",
    "Diffraction: waves bend around obstacles. A thought aimed at a concept but blocked by "
    "incomplete knowledge (a gap in the training data) diffracts around the gap. "
    "The diffraction pattern depends on the 'wavelength' (tongue weight): "
    f"KO (w=1.0, short wavelength) diffracts tightly — stays focused, misses the hidden concept. "
    f"DR (w=11.09, long wavelength) diffracts broadly — bends around the gap, reaches the concept. "
    "This is why deep structural thinking (DR) can make connections that surface thinking (KO) can't: "
    "DR's 'wavelength' is long enough to diffract around knowledge gaps. "
    "Training implication: the model needs DR-heavy records to develop long-wavelength reasoning.",
    "L2", "DR", ["DR", "KO"], "diffraction"))

# ── Multi-D Orientation via Reflection ──

RECORDS.append(rec(
    "How do reflection paths create multi-dimensional structural orientations?",
    "In 2D, a ray bouncing between two mirrors creates a 1D pattern (back and forth). "
    "In 3D, a ray bouncing inside a triangular prism creates a 2D pattern (triangle). "
    "In 6D (the Sacred Tongue space), a thought bouncing between tongue boundaries creates "
    "a 5D pattern — the full structural orientation of that thought in the system. "
    "The entry angle determines which tongues are visited and in what order. "
    "A thought entering at (1,0,0,0,0,0) — pure KO — bounces through predictable tongue sequence. "
    "A thought entering at (0.4,0.1,0.3,0.1,0.05,0.05) — mixed — creates a complex 6D reflection pattern "
    "that visits all tongues at different intensities. "
    "The reflection pattern IS the structural orientation. You don't need to classify it — "
    "the geometry already did by determining which walls get hit and in what order.",
    "L2", "DR", ["DR", "CA", "KO"], "multi_d_orientation"))

RECORDS.append(rec(
    "How does a thought's reflection path through the 14 layers create its governance fingerprint?",
    "A thought enters at L1 (complex context). It refracts into L2 (realification). "
    "At L4 (Poincare embedding), it enters hyperbolic space — the 'medium' becomes curved. "
    "In curved space, light follows geodesics, not straight lines. "
    "The thought's path through L5-L7 (hyperbolic distance, breathing, phase) is a geodesic on the Poincare ball. "
    "At L8 (PHDM realm), the thought reflects off polyhedra walls — which face it hits determines its realm. "
    "At L12 (harmonic wall), the remaining energy determines how bright the thought is. "
    "Dim (low H score) = adversarial. Bright (high H score) = safe. "
    "The 14-layer path from entry to exit IS the governance fingerprint — "
    "two thoughts with the same text but different entry angles produce different fingerprints.",
    "L2", "DR", ALL_TONGUES, "governance_fingerprint"))

# ── Left/Right Handedness in Optics ──

RECORDS.append(rec(
    "How does optical chirality (left/right handedness) map to coordination flow?",
    "Circularly polarized light has handedness: left-circular or right-circular. "
    "In HYDRA, the clockwise flow (KO->AV->RU->CA->UM->DR) is right-handed — normal operations. "
    "The counter-clockwise flow (DR->UM->CA->RU->AV->KO) is left-handed — emergency/rollback. "
    "Like polarized sunglasses filtering one handedness: "
    "the governance system filters left-handed signals (rollback) from right-handed (normal). "
    "A message arriving on the 'wrong hand' (left when expected right) is suspicious — "
    "it means something is flowing backward through the tongue sequence. "
    "This is a structural detection method: no content analysis needed, just check the handedness.",
    "L1", "KO", ["KO", "AV", "DR"], "chirality"))

RECORDS.append(rec(
    "How do fiber optic principles apply to tongue channel routing?",
    f"A fiber optic cable uses TIR to keep light inside the core. The core (high n) is surrounded by cladding (low n). "
    f"In SCBE: each tongue channel is a 'fiber' with core density = its phi-weight and cladding density = the next lighter tongue. "
    f"DR fiber: core n={PHI**5:.3f}, cladding n={PHI**4:.3f}. Very tight confinement — thoughts in DR stay in DR. "
    f"KO fiber: core n={PHI**0:.3f}, cladding n=0 (vacuum). Maximum leakage — KO thoughts easily spread to other tongues. "
    f"This maps to reality: structural knowledge (DR) is domain-specific and doesn't leak. "
    f"Control signals (KO) are broadcast-style and intentionally leak to all domains. "
    f"The phi-weight ratio between adjacent tongues = the numerical aperture of each channel.",
    "L1", "DR", ["DR", "UM", "KO"], "fiber_optic"))


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    cats = {}
    layers = {}
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            cats[record["category"]] = cats.get(record["category"], 0) + 1
            layers[record["layer"]] = layers.get(record["layer"], 0) + 1

    print(f"Generated {len(RECORDS)} ray tracing thought-pathing records")
    print(f"\nBy layer:")
    for l, c in sorted(layers.items()):
        print(f"  {l}: {c}")
    print(f"\nBy category:")
    for cat, c in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {c}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
