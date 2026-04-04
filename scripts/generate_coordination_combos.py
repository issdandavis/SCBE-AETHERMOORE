#!/usr/bin/env python3
"""Generate coordination combo training data — triplets, quadruplets, navigation layers.

Coordination = groups of agents making joint choices from paired arrays.
Like fighting game combos: not single buttons but sequences of grouped inputs.

Then layer navigation controls on top:
  - Keyboard/CLI navigation (typed commands)
  - Screen/GUI navigation (click, scroll, drag)
  - Web navigation (URL, link, search, form)
  - Physical/terrain navigation (robotics, drone, spatial)
  - AI navigation (prompt routing, tongue selection, model switching)
"""

import json
import itertools
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "coordination_combos_l1l2_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

def rec(instruction, output, layer, tongue, active=None, category="combo"):
    act = active or [tongue]
    null = [t for t in ALL_TONGUES if t not in act]
    return {
        "instruction": instruction, "output": output, "tongue": tongue,
        "tongues_active": act, "tongues_null": null, "layer": layer,
        "category": category, "view_type": "partial" if len(null) <= 3 else "null-heavy",
        "governance": "ALLOW", "source": "coordination_combos",
    }

RECORDS = []

# ── Tongue Pairs (doublets) ──
PAIRS = [
    ("KO", "AV", "Control + I/O", "orchestrate data flow", "reading files and directing output"),
    ("KO", "CA", "Control + Compute", "orchestrate computation", "directing which calculations run"),
    ("RU", "UM", "Policy + Security", "enforce governed access", "validating rules and checking trust"),
    ("CA", "DR", "Compute + Structure", "architect solutions", "building code with structural awareness"),
    ("AV", "RU", "I/O + Policy", "governed data transfer", "moving data with rule compliance"),
    ("UM", "DR", "Security + Structure", "cryptographic architecture", "building secure foundations"),
]

for t1, t2, name, verb, desc in PAIRS:
    RECORDS.append(rec(
        f"How does the {t1}+{t2} ({name}) pair coordinate in HYDRA?",
        f"The {t1}+{t2} pair forms a doublet that can {verb}. "
        f"{t1} (weight={round(1.618**(ALL_TONGUES.index(t1)), 3)}) handles the {t1} domain while "
        f"{t2} (weight={round(1.618**(ALL_TONGUES.index(t2)), 3)}) handles the {t2} domain. "
        f"Together they cover {desc}. "
        f"The pair's combined weight is {round(1.618**(ALL_TONGUES.index(t1)) + 1.618**(ALL_TONGUES.index(t2)), 3)}. "
        f"Null tongues: {', '.join(t for t in ALL_TONGUES if t not in (t1, t2))} — these channels are skipped.",
        "L1", t1, [t1, t2], "doublet",
    ))

# ── Tongue Triplets ──
TRIPLETS = [
    ("KO", "CA", "DR", "Full stack build", "plan, compute, and structure in one operation"),
    ("KO", "RU", "UM", "Governed operations", "control with policy enforcement and security"),
    ("AV", "CA", "DR", "Data processing pipeline", "ingest, compute, and restructure data"),
    ("RU", "UM", "DR", "Deep governance", "policy + security + structural change authority"),
    ("KO", "AV", "CA", "Operational execution", "direct, move, and compute in sequence"),
    ("KO", "AV", "RU", "Governed I/O", "controlled data flow with policy compliance"),
]

for t1, t2, t3, name, desc in TRIPLETS:
    active = [t1, t2, t3]
    null = [t for t in ALL_TONGUES if t not in active]
    combined_weight = sum(1.618**ALL_TONGUES.index(t) for t in active)
    RECORDS.append(rec(
        f"What does the {t1}+{t2}+{t3} triplet handle in HYDRA coordination?",
        f"The {name} triplet ({t1}+{t2}+{t3}) can {desc}. "
        f"Combined phi-weight: {combined_weight:.3f}. "
        f"This triplet requires tier {len(active)} governance (minTrust varies by highest tongue). "
        f"Three agents coordinate: {t1} leads, {t2} executes, {t3} validates. "
        f"The 3-agent group votes as a sub-quorum — still needs 4/6 for full BFT, but the triplet can "
        f"pre-validate before bringing the full roundtable. "
        f"Null channels: {', '.join(null)} — {len(null)} channels saved.",
        "L1", t1, active, "triplet",
    ))

# ── Tongue Quadruplets ──
QUADS = [
    ("KO", "RU", "CA", "UM", "Deployment authority", "enough tongues for tier 4 operations"),
    ("KO", "AV", "RU", "CA", "Full operational stack", "control + I/O + policy + compute"),
    ("KO", "CA", "UM", "DR", "Security architecture", "control + compute + security + structure"),
    ("AV", "RU", "CA", "DR", "Data governance pipeline", "I/O + policy + compute + structure"),
]

for t1, t2, t3, t4, name, desc in QUADS:
    active = [t1, t2, t3, t4]
    null = [t for t in ALL_TONGUES if t not in active]
    RECORDS.append(rec(
        f"What can the {t1}+{t2}+{t3}+{t4} quadruplet authorize?",
        f"The {name} quadruplet ({'+'.join(active)}) provides {desc}. "
        f"With 4 tongues active, this group meets tier 4 governance requirements (minTrust=0.7). "
        f"It can authorize: deploy, publish, release operations (CA-tier). "
        f"The quadruplet forms its own BFT quorum — 4 of 6 is exactly the quorum threshold. "
        f"The 2 null tongues ({', '.join(null)}) are explicitly excluded, saving their compute weight. "
        f"For tier 5-6 operations (UM/DR destructive), this quad is insufficient — needs 5 or 6 tongues.",
        "L1", t1, active, "quadruplet",
    ))

# ── Choice Brackets: 7 choices from 2 arrays ──
ARRAY_A = ["navigate", "inspect", "extract", "transform"]  # 4 actions
ARRAY_B = ["validate", "deploy", "rollback"]  # 3 actions
# Combined = 7 choices, presented as paired arrays

RECORDS.append(rec(
    "What are the 7 coordination choices available from the dual action arrays?",
    f"Array A (exploration): {', '.join(ARRAY_A)} — 4 forward-moving actions. "
    f"Array B (governance): {', '.join(ARRAY_B)} — 3 control actions. "
    f"Combined: 7 choices from 2 sets. A triplet picks one from each array + a modifier: "
    f"e.g., (navigate, validate, KO) = 'go to URL, check it's safe, under KO control.' "
    f"A quadruplet picks two from each: (navigate+extract, validate+deploy) = 'go there, pull data, verify, ship it.' "
    f"The dual-array structure means exploration and governance always pair — you can't explore without validating, "
    f"can't deploy without inspecting first.",
    "L1", "KO", ["KO", "RU", "CA"], "choice_bracket",
))

# ── Navigation Modes (the control surface layer) ──
NAV_MODES = [
    ("keyboard", "CLI/terminal", "KO", "typed commands, flags, pipes",
     "ls, cd, grep, git, npm, python — sequential character input to shell interpreter"),
    ("screen", "GUI/display", "AV", "click, scroll, drag, hover, select",
     "mouse/touch input mapped to screen coordinates, pixel-level precision, element targeting"),
    ("web", "browser/HTTP", "AV", "URL navigation, link following, form submission, search",
     "HTTP requests, DOM traversal, JavaScript execution, cookie/session management"),
    ("physical", "robotics/drone", "CA", "move, rotate, grip, sense, avoid",
     "motor commands, sensor fusion, obstacle avoidance, path planning in 3D space"),
    ("ai", "model/prompt", "CA", "prompt routing, tongue selection, model switching, context loading",
     "selecting which model handles which subtask, loading relevant context windows, switching inference providers"),
]

for mode, surface, tongue, verbs, desc in NAV_MODES:
    RECORDS.append(rec(
        f"How does {mode} navigation work as a coordination layer in HYDRA?",
        f"{mode.title()} navigation operates on the {surface} surface. "
        f"Core verbs: {verbs}. "
        f"Implementation: {desc}. "
        f"In HYDRA, {mode} navigation maps to the {tongue} tongue channel — "
        f"the agent that owns {tongue} handles {mode} input/output. "
        f"When combined with formation geometry: a Hexagonal Ring using {mode} navigation "
        f"means 6 agents each handle {mode} input in parallel on their assigned sectors. "
        f"A Concentric Ring with {mode} = inner ring (fast response) handles urgent {mode} actions, "
        f"outer ring handles background {mode} tasks.",
        "L2", tongue, [tongue, "KO"], "navigation",
    ))

# ── Navigation combos (formation + group + nav mode) ──
COMBOS = [
    ("Hexagonal Ring", "triplet", "web", ["KO", "AV", "RU"],
     "3 agents in ring formation handle web crawling: KO scouts URLs, AV extracts content, RU validates compliance"),
    ("Concentric Rings", "quadruplet", "screen", ["KO", "AV", "CA", "UM"],
     "4 agents in priority tiers handle GUI automation: KO+AV inner ring (fast clicks), CA+UM outer ring (compute+verify)"),
    ("Adaptive Scatter", "doublet", "physical", ["CA", "DR"],
     "2 agents in scatter formation handle physical terrain: CA computes paths, DR maintains structural awareness"),
    ("Tetrahedral", "triplet", "ai", ["KO", "CA", "DR"],
     "3 agents in 3D formation handle AI routing: KO selects model, CA runs inference, DR validates architecture"),
    ("Hexagonal Ring", "quadruplet", "keyboard", ["KO", "RU", "CA", "UM"],
     "4 agents handle CLI operations: KO orchestrates, RU validates, CA executes, UM secures credentials"),
]

for formation, group, nav, active, desc in COMBOS:
    null = [t for t in ALL_TONGUES if t not in active]
    RECORDS.append(rec(
        f"Describe a {formation} + {group} + {nav} coordination combo.",
        f"Formation: {formation}. Group: {group} ({'+'.join(active)}). Navigation: {nav}. "
        f"{desc}. "
        f"The {group} handles {nav} navigation actions within the {formation} geometry. "
        f"Null channels: {', '.join(null)} — these tongues are inactive for this operation. "
        f"If the task escalates beyond the {group}'s authority, it brings in the remaining "
        f"{6-len(active)} tongues for full Roundtable consensus.",
        "L2", active[0], active, "formation_combo",
    ))

# ── Robotics bridge (free datasets for recalibration) ──
RECORDS.append(rec(
    "How can robotics navigation datasets be recalibrated for SCBE tongue routing?",
    "Robotics datasets (ROS navigation, OpenAI Gym, MuJoCo) contain: position, velocity, "
    "obstacle distance, goal distance, action taken, reward. Map these to SCBE: "
    "position = Poincare ball coordinate (hyperbolic). velocity = tongue activation rate. "
    "obstacle distance = d_H (hyperbolic distance to threat). goal distance = d_star (distance to realm center). "
    "action = tongue-routed decision (KO=navigate, CA=compute path, UM=check safety). "
    "reward = GovernanceCoin Value=1/(1+L). "
    "The recalibration is shape-level: same data structure, different semantic assignment. "
    "A robot avoiding a wall = an AI agent avoiding a governance boundary. Same geometry.",
    "L2", "CA", ["CA", "DR", "KO"], "robotics_bridge",
))

RECORDS.append(rec(
    "What free robotics datasets can be recalibrated for SCBE coordination training?",
    "OpenAI Gym/Gymnasium: CartPole, MountainCar, LunarLander — simple control with clear reward signals. "
    "MuJoCo (now free): HalfCheetah, Ant, Humanoid — multi-joint coordination (maps to multi-tongue). "
    "ROS Navigation2: real-world path planning datasets with LIDAR, odometry, costmaps. "
    "D4RL: offline RL benchmark with maze navigation and robot manipulation. "
    "Habitat: indoor navigation with photorealistic scenes. "
    "For SCBE recalibration: treat each joint/motor as a tongue, each obstacle as a governance boundary, "
    "each reward as a GovernanceCoin accumulation. The physical terrain IS the hyperbolic space — "
    "the robot's safe zone is the Poincare ball center, walls are the boundary.",
    "L2", "CA", ["CA", "AV", "KO"], "robotics_bridge",
))


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    cats = {}
    layers = {"L1": 0, "L2": 0}
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for record in RECORDS:
            record["timestamp"] = timestamp
            f.write(json.dumps(record, ensure_ascii=True) + "\n")
            layers[record["layer"]] = layers.get(record["layer"], 0) + 1
            cats[record["category"]] = cats.get(record["category"], 0) + 1

    print(f"Generated {len(RECORDS)} coordination combo records")
    print(f"  L1: {layers.get('L1', 0)}, L2: {layers.get('L2', 0)}")
    print(f"\nBy category:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
