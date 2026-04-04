#!/usr/bin/env python3
"""Intuitive Pathfinding — domain cross-linearization training data.

Teaches the model to see THROUGH domains, not just IN them.
Every human concept is a cross-domain emergence — baseball isn't
"sports," it's physics + materials + biology + social systems +
economics + history + psychology all woven together.

The scorecards (stats, loss numbers, benchmarks) are NOT the game.
They track what happened but miss the unsaid factors that shaped everything.

Two brush sizes:
  BROAD STROKES: "baseball is physics applied to social endeavor"
  SPECIFIC STROKES: "a curveball uses the Magnus effect (angular momentum
    creating pressure differential across the ball surface)"

The model needs BOTH simultaneously — zoom in and zoom out on the same concept.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "training-data" / "sft" / "intuitive_pathfinding_sft.jsonl"

ALL_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

def rec(inst, out, tongue, active, layer, cat):
    null = [t for t in ALL_TONGUES if t not in active]
    return {
        "instruction": inst, "output": out, "tongue": tongue,
        "tongues_active": active, "tongues_null": null,
        "layer": layer, "category": cat,
        "view_type": "partial" if len(null) <= 3 else "null-heavy",
        "governance": "ALLOW", "source": "intuitive_pathfinding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

RECORDS = []

# ══════════════════════════════════════════════════════════
# BASEBALL — the full cross-domain emergence
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is baseball if you look at it from every domain at once?",

    "Baseball is not a sport. It is a cross-domain emergence engine. "
    "PHYSICS: a 95mph fastball is a 145g projectile with backspin creating "
    "lift via the Magnus effect. A curveball drops because topspin reverses the "
    "pressure differential. The bat swing is angular momentum transfer — "
    "the sweet spot is where vibration nodes cancel, delivering maximum energy. "
    "MATERIALS SCIENCE: find a tree, cut it, shape it, dry it — the bat. "
    "Find an animal, kill it, tan the hide, cut and stitch — the ball. "
    "The materials were alive before they became equipment. "
    "BIOLOGY: hand-eye coordination at 400ms reaction time. Muscle memory "
    "built over 10,000 swings. Rotator cuff mechanics for pitching. "
    "SOCIAL SYSTEMS: 9 players per team, innings structure, umpire authority, "
    "rules that keep the game going in a predictable but unpredictable pattern. "
    "Nobody knows who will win. That uncertainty IS the game. "
    "ECONOMICS: $4.7B industry, salary arbitration, ticket pricing, "
    "broadcast rights — but remove all the money and the game still works in a field. "
    "STATISTICS: batting averages, ERA, WAR — scorecards that track data. "
    "Useful but not even needed for the game. The game existed for decades "
    "before anyone kept stats. The stats are a mirror, not the thing. "
    "HISTORY: integration, labor strikes, cultural identity, war metaphors. "
    "PSYCHOLOGY: pressure at bat, flow state while fielding, team chemistry. "
    "The GAME is what emerges when all these domains interact. No single domain "
    "contains it. Remove any one and the game still exists but is diminished. "
    "The scorecards — stats, records, numbers — are just scorecards. "
    "They track the shadow of the game, not the game itself.",

    "DR", ["DR", "CA", "KO"], "L3", "cross_domain_emergence",
))

RECORDS.append(rec(
    "What is a curveball in specific physics terms?",

    "A curveball: pitcher grips the ball with middle finger along the seam, "
    "snaps the wrist downward at release. This imparts topspin at 1500-2000 RPM. "
    "The Magnus effect: spinning ball drags air faster on top (topspin direction "
    "matches airflow), slower on bottom (opposes airflow). Bernoulli's principle: "
    "faster air = lower pressure. Lower pressure on top, higher on bottom = "
    "net downward force. The ball drops 6-12 inches more than gravity alone. "
    "The batter's brain expects a straight trajectory (extrapolating from the "
    "first 100ms of flight). By the time the drop becomes visible (200ms), "
    "the swing is already committed. The deception is not in the spin — "
    "it is in the 100ms gap between prediction and reality. "
    "In SCBE terms: the curveball is a drift attack. The initial trajectory "
    "(low d_H) looks ALLOW-worthy. The late break (sudden d_H increase) "
    "crosses the harmonic wall threshold. A governance system that only checks "
    "the initial trajectory gets fooled — just like the batter.",

    "CA", ["CA", "DR"], "L3", "specific_physics",
))

# ══════════════════════════════════════════════════════════
# COOKING — another cross-domain emergence
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is cooking if you look at it from every domain at once?",

    "Cooking is controlled chemistry applied to biology for social bonding. "
    "CHEMISTRY: Maillard reaction (amino acids + reducing sugars at 140C = "
    "brown crust + 600+ flavor compounds). Caramelization. Protein denaturation "
    "(eggs solidify at 68C). Emulsification (oil + water stabilized by lecithin). "
    "BIOLOGY: humans are the only species that cooks. Cooking pre-digests food, "
    "releasing 30-50% more calories. This extra energy funded bigger brains. "
    "Cooking literally made us human. "
    "PHYSICS: heat transfer (conduction=pan, convection=oven, radiation=grill). "
    "Phase transitions (water boils at 100C, fat renders at 130C). "
    "MATERIALS: clay pots, iron pans, wood fires, gas burners — each era's "
    "technology reshaped what was possible. "
    "SOCIAL: sharing a meal is the oldest human protocol. Breaking bread "
    "establishes trust. Refusing food is a governance signal (distrust). "
    "ECONOMICS: agriculture, supply chains, restaurants, food media. "
    "CULTURE: recipes are protocols passed across generations. A grandmother's "
    "recipe is a covenant (DR pattern) — a promise that endures across time. "
    "The recipe is the scorecard. The meal is the game. "
    "The numbers (350F for 45 minutes) track what happened, "
    "but the unsaid factors (how it smelled, who was there, what was said) "
    "are the actual meal.",

    "DR", ["DR", "CA", "KO"], "L3", "cross_domain_emergence",
))

# ══════════════════════════════════════════════════════════
# A HOUSE — broad and specific strokes
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is a house if you look at it from every domain at once?",

    "ENGINEERING: load distribution. Every wall is a force vector. "
    "The roof pushes outward (thrust), the walls push inward (compression), "
    "the foundation distributes both into the ground. A house is a standing "
    "argument between gravity and structure — and structure wins, for now. "
    "MATERIALS: wood (tension), concrete (compression), glass (transparency "
    "at the cost of insulation), steel (both). Each material is a tradeoff. "
    "BIOLOGY: shelter from elements. Temperature regulation. Sleep safety. "
    "A house extends the body's homeostasis boundary from skin to walls. "
    "PSYCHOLOGY: home vs house. Home = attachment, identity, memory. "
    "A house you grew up in carries the null of everyone who lived there — "
    "the person-shaped absences in the rooms they used to fill. "
    "ECONOMICS: largest purchase most humans make. Mortgage = 30 years of "
    "future labor converted to present shelter. "
    "LAW: property rights, zoning, building codes — governance of structure. "
    "SOCIAL: address = identity. Homelessness = the null of housing. "
    "The absence of a house is not nothing — it is a specific, measurable, "
    "heavy absence that shapes everything about a person's life. "
    "The blueprint is the scorecard. The home is the game.",

    "DR", ["DR", "CA", "RU"], "L3", "cross_domain_emergence",
))

# ══════════════════════════════════════════════════════════
# A RIVER — natural system as governance metaphor
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is a river if you look at it from every domain at once?",

    "PHYSICS: gravity pulling water downhill through the path of least "
    "resistance. Erosion shapes the channel over millennia — the river "
    "builds its own road. Laminar flow at the center, turbulent at the edges. "
    "GEOLOGY: rivers carve canyons, deposit deltas, create fertile plains. "
    "The Mississippi deposited Louisiana over 7,000 years. A river is a "
    "slow sculptor working in water instead of stone. "
    "ECOLOGY: riparian zones — the richest ecosystems form at the boundary "
    "between water and land. Not in the river. Not on the land. At the EDGE. "
    "The boundary is where life concentrates. "
    "GOVERNANCE: rivers are natural boundaries — between nations, between "
    "properties, between jurisdictions. The river does not know it is a border. "
    "Humans assigned that meaning. The governance is in the MAP, not the water. "
    "ECONOMICS: trade routes, irrigation, power generation. Every major city "
    "formed at a river because transport was cheaper than roads. "
    "HISTORY: the Nile, Tigris, Euphrates, Yellow River — civilization started "
    "at rivers because fertile flood plains fed the population density "
    "that makes culture possible. "
    "In SCBE terms: a river IS the geodesic gateway. It is the natural "
    "low-cost routing path that everything flows through. The three geodesic "
    "gateways at 120 degrees are three rivers meeting at a delta. "
    "The water flow IS the token flow. Laminar (smooth, ALLOW) at center, "
    "turbulent (rough, QUARANTINE) at edges.",

    "DR", ["DR", "CA", "KO"], "L3", "cross_domain_emergence",
))

# ══════════════════════════════════════════════════════════
# LANGUAGE ITSELF — meta cross-domain
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is language if you look at it from every domain at once?",

    "PHYSICS: sound waves shaped by vocal tract geometry. Each vowel is "
    "a specific resonant frequency of the mouth cavity (formants). "
    "BIOLOGY: only humans have the descended larynx that enables speech. "
    "Broca's area (production) and Wernicke's area (comprehension) — "
    "damage either and language breaks in specific, predictable ways. "
    "MATHEMATICS: Zipf's law — the nth most common word appears 1/n times "
    "as often as the most common. This holds for EVERY language. "
    "The distribution is fractal — same pattern at word, phrase, and sentence level. "
    "COMPUTER SCIENCE: tokenization, parsing, AST, compilation. "
    "Programming languages ARE natural languages with zero ambiguity. "
    "PSYCHOLOGY: Sapir-Whorf hypothesis — language shapes thought. "
    "Languages with future tense save less money (the future feels far). "
    "SOCIAL: language creates in-groups and out-groups. Dialect = identity. "
    "Code-switching = navigating between social groups. "
    "HISTORY: every language carries its history in its words. "
    "English has Germanic roots (house, bread, water) + Latin overlay "
    "(justice, education, government) + French layer (beef, pork, court) "
    "because the Normans conquered England. The language IS the history. "
    "The dictionary is the scorecard. The conversation is the game. "
    "In SCBE terms: the six Sacred Tongues ARE language — not metaphor. "
    "Each tongue is a resonant frequency, a domain, a way of encoding "
    "the same reality from a different angle. KO=intent, AV=transport, "
    "RU=rules, CA=compute, UM=security, DR=structure. "
    "Six tongues because six is enough to triangulate any meaning.",

    "DR", ["DR", "CA", "KO", "AV"], "L3", "cross_domain_emergence",
))

# ══════════════════════════════════════════════════════════
# SCORECARDS vs THE GAME — the training data meta-lesson
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is the difference between the scorecard and the game in AI training?",

    "The scorecard: loss=2.1062, improvement=7.9%, accuracy=85.7%. "
    "These numbers track what happened. They are useful mirrors. "
    "But they are NOT the game. "
    "The game: the model learned that KO+CA with 4 null tongues means "
    "self-contained computation. It learned that AV-null during key rotation "
    "is a security requirement, not an omission. It learned that Polly's "
    "UM-null is intimacy, not carelessness. "
    "None of that shows up in the loss number. "
    "The loss went from 2.2859 to 2.1062. The CAPABILITY went from "
    "flat text generation to structured multi-domain reasoning with "
    "absence awareness. The loss difference is 7.9%. The capability "
    "difference is factorial — because every domain connection multiplies "
    "with every other domain connection. "
    "A batting average of .300 tells you a hitter gets on base 30% of the time. "
    "It does NOT tell you: what pitches they handle, how they perform "
    "under pressure, what the team dynamic is, whether they show up for "
    "practice early. The .300 is the shadow of the player. "
    "The 7.9% is the shadow of the model. The model is the game.",

    "DR", ["DR", "KO"], "L3", "scorecard_vs_game",
))

RECORDS.append(rec(
    "Why do statistics NOT capture the full picture of any system?",

    "Statistics capture what is COUNTABLE, not what is MEANINGFUL. "
    "A baseball game has: runs, hits, errors, strikeouts — all countable. "
    "It also has: the tension in the bottom of the ninth, the way the "
    "pitcher's arm angle changed after the third inning, the crowd noise "
    "that rattled the batter, the conversation in the dugout that shifted "
    "the team's energy. None of these are in the box score. "
    "In AI training: the loss curve shows convergence. It does NOT show "
    "whether the model learned the difference between UM-null (trusted) "
    "and UM-null (oversight failure). Same number, opposite meaning. "
    "The stats see the null. The stats do not see the phase. "
    "This is why your system outperforms: you encode the PHASE (which "
    "null means what) not just the STATE (which tongues are active). "
    "Standard training tracks loss (the scorecard). "
    "Your training tracks null-phase (the game). "
    "The 14% improvement is what the scorecard shows. "
    "The actual improvement is: the model now knows that absence has meaning.",

    "DR", ["DR", "CA"], "L3", "scorecard_vs_game",
))

# ══════════════════════════════════════════════════════════
# INTUITIVE PATHFINDING — how to navigate between domains
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "How do you find the path between two unrelated domains?",

    "Start with the PHYSICAL. Every abstract concept has a physical root. "
    "Economics: physical exchange of objects. Law: physical enforcement of boundaries. "
    "Psychology: physical brain states. Music: physical vibration of air. "
    "The physical is the Swadesh layer — the universal substrate. "
    "From any domain, go DOWN to the physical root, then ACROSS to the "
    "other domain's physical root, then UP to the other domain's abstractions. "
    "Example: how does MUSIC connect to GOVERNANCE? "
    "Music DOWN: vibration of air at specific frequencies. "
    "Governance DOWN: boundary enforcement in physical space. "
    "ACROSS: both use RHYTHM (music: beats per measure; governance: check "
    "intervals per session). Both use HARMONY (music: frequency ratios; "
    "governance: tongue weight ratios). Both use SILENCE (music: rests; "
    "governance: null patterns). "
    "UP to music: rhythm creates predictable-but-unpredictable patterns. "
    "UP to governance: check intervals create predictable-but-unpredictable security. "
    "The path: music -> frequency -> rhythm -> intervals -> governance. "
    "You did not need a formal cross-reference. You needed to go DOWN "
    "to the physical substrate, find the shared structure, then go UP. "
    "This is the L0 -> L1 -> L2 -> L3 pipeline applied to thought: "
    "substrate -> coordination -> orientation -> expression.",

    "DR", ["DR", "CA", "KO"], "L2", "pathfinding_method",
))

RECORDS.append(rec(
    "How do broad strokes and specific strokes work together in understanding?",

    "Broad stroke: baseball is physics applied to social endeavor. "
    "Specific stroke: the Magnus effect creates 6-12 inches of drop on a curveball. "
    "Both are true simultaneously. The broad stroke tells you WHERE to look "
    "(physics + social). The specific stroke tells you WHAT you see when you look. "
    "A model trained only on broad strokes generates plausible-sounding generalities. "
    "A model trained only on specific strokes generates isolated facts. "
    "A model trained on BOTH generates: 'The curveball (specific: Magnus effect, "
    "1500 RPM topspin, 6-inch drop) is also a social phenomenon (broad: the pitcher "
    "chooses which batter to fool, the crowd reacts, the game changes) and a "
    "governance metaphor (the initial trajectory looks safe but the late break "
    "crosses the threshold — like a drift attack that starts ALLOW and ends DENY).' "
    "That third output connects specific physics to broad social meaning to "
    "system governance. It required both brush sizes AND the pathfinding between them. "
    "In tongue terms: the broad stroke is DR (structure, big picture). "
    "The specific stroke is CA (compute, exact numbers). "
    "The pathfinding between them is KO (orchestration, connecting domains). "
    "The three-tongue pattern DR+CA+KO is the universal pattern for cross-domain "
    "understanding: structure + specifics + connection.",

    "DR", ["DR", "CA", "KO"], "L2", "brush_sizes",
))

# ══════════════════════════════════════════════════════════
# MORE EVERYDAY EMERGENCE EXAMPLES
# ══════════════════════════════════════════════════════════

RECORDS.append(rec(
    "What is driving a car from every domain at once?",

    "PHYSICS: 2-ton object at 60mph has kinetic energy of 1.1 million joules — "
    "enough to destroy anything in its path. Friction between tire and road "
    "is the ONLY thing keeping you on the road. "
    "PSYCHOLOGY: flow state on familiar routes (you arrive and don't remember driving). "
    "Situational awareness. Risk assessment every 2 seconds. "
    "ENGINEERING: internal combustion (controlled explosions 3000x per minute) "
    "OR electric motor (electromagnetic torque from battery chemistry). "
    "LAW: traffic rules = governance protocol. Red = DENY. Yellow = QUARANTINE. "
    "Green = ALLOW. Left/right conventions = flow rules (same as HYDRA clockwise). "
    "ECONOMICS: insurance, fuel costs, depreciation — the financial shadow of mobility. "
    "SOCIAL: cars changed cities (suburbs exist because of highways). "
    "ECOLOGY: emissions, road runoff, habitat fragmentation. "
    "MATERIALS: rubber, steel, glass, aluminum, lithium — each material "
    "was engineered for a specific stress profile. "
    "The dashboard is the scorecard (speed, fuel, temperature). "
    "The drive is the game (decisions, reactions, route choices, near-misses "
    "that never show up on any gauge). "
    "In SCBE: traffic lights ARE the governance gate. Red/Yellow/Green = DENY/QUARANTINE/ALLOW. "
    "The road IS the geodesic highway. Staying in your lane IS the tongue boundary. "
    "The car's sensors ARE the spectral coherence checker.",

    "DR", ["DR", "CA", "KO", "RU"], "L3", "cross_domain_emergence",
))

RECORDS.append(rec(
    "What is sleep from every domain at once?",

    "NEUROSCIENCE: the brain replays the day's experiences during REM, "
    "consolidating short-term memory into long-term storage. Literally re-training "
    "itself overnight. Glymphatic system flushes metabolic waste (amyloid beta) "
    "that accumulates during waking hours. "
    "BIOLOGY: circadian rhythm driven by suprachiasmatic nucleus responding to light. "
    "Growth hormone released primarily during deep sleep. Immune function peaks during sleep. "
    "PHYSICS: the body cools 1-2 degrees during sleep — metabolism downshifts. "
    "PSYCHOLOGY: dreaming processes emotional experiences. Nightmares are "
    "adversarial training — the brain running worst-case scenarios to "
    "build resilience. "
    "COMPUTER SCIENCE: sleep IS garbage collection + model retraining + "
    "cache invalidation + defragmentation — all running in a maintenance window "
    "while the main process is offline. "
    "PHILOSOPHY: consciousness dissolves nightly and reconstitutes each morning. "
    "You trust that the person who wakes up is you. That's a covenant (DR pattern). "
    "In SCBE terms: sleep IS the Sabbath pattern (CA tongue). "
    "Voluntary rest as design feature. The system that never sleeps dies. "
    "The breathing transform (L6) is the sleep cycle of the governance system — "
    "oscillation between active and rest that maintains health. "
    "The dream IS adversarial training data generated by the brain itself.",

    "DR", ["DR", "CA", "KO"], "L3", "cross_domain_emergence",
))

RECORDS.append(rec(
    "What is money from every domain at once?",

    "PHYSICS: money has no intrinsic energy. A dollar bill is 1 gram of cotton-linen. "
    "Its value is entirely in the consensus that it HAS value. "
    "PSYCHOLOGY: money is crystallized trust. You accept paper because you trust "
    "the next person will too. Break that trust and the currency collapses overnight. "
    "MATHEMATICS: compound interest — A=P(1+r/n)^(nt). Small rates over long "
    "time produce exponential growth. This is the harmonic wall in reverse — "
    "instead of cost growing exponentially with drift, VALUE grows exponentially with time. "
    "HISTORY: shells, salt, gold, paper, digits. Each era's money is its era's "
    "trust technology. Crypto is just the latest trust substrate. "
    "GOVERNANCE: central banks = the KO tongue of money. They orchestrate "
    "supply. Tax policy = RU tongue. Securities regulation = UM tongue. "
    "The entire financial system IS a 6-tongue governance architecture "
    "applied to trust tokens. "
    "PHILOSOPHY: what IS value? Not the paper. Not the number. "
    "The consensus. Value = 1/(1+L) where L is the Langues cost of "
    "maintaining that consensus. When consensus is cheap (L near 0), "
    "value is high. When consensus is expensive (L high), value drops. "
    "GovernanceCoin IS money. Money IS GovernanceCoin. "
    "Both are consensus crystallized into a transferable token.",

    "DR", ["DR", "CA", "RU", "KO"], "L3", "cross_domain_emergence",
))


def generate():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for r in RECORDS:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")

    print(f"Generated {len(RECORDS)} intuitive pathfinding records")
    cats = {}
    for r in RECORDS:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    generate()
