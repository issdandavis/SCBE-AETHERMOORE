#!/usr/bin/env python3
"""
Skill Tree Build Guides + Manhwa Tropes → SFT Training Pairs

MMORPG skill trees ARE the credit system:
- Primary path = primary tongue
- Branching specializations = tongue coverage
- Endgame unlock = graduation (requires min coverage across all trees)

Manhwa tropes (regression, system windows, status screens) are the UI
for self-evaluation. The "system" showing stats IS the model's dashboard.

Output: training-data/sft/skill_tree_manhwa_sft.jsonl
"""

import json
import datetime

TIMESTAMP = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ─── TONGUE-TO-CLASS MAPPING ───
# Each tongue maps to an MMO archetype AND a manhwa trope
TONGUE_CLASS_MAP = {
    "KO": {"class": "Commander", "role": "Tank/Leader", "manhwa_trope": "Regression protagonist who remembers the raid strategy"},
    "AV": {"class": "Scout", "role": "Mobility/Recon", "manhwa_trope": "Speed-type hunter who sees the gap before anyone else"},
    "RU": {"class": "Lawkeeper", "role": "Support/Control", "manhwa_trope": "Guild master who enforces rules others hate but need"},
    "CA": {"class": "Artificer", "role": "DPS/Craft", "manhwa_trope": "System crafter who breaks the economy by finding exploit combos"},
    "UM": {"class": "Shadow", "role": "Stealth/Intel", "manhwa_trope": "Solo leveler who hides power level from everyone including the system"},
    "DR": {"class": "Architect", "role": "Builder/Schema", "manhwa_trope": "Dungeon creator who builds the labyrinth from inside it"},
}

# ─── SKILL TREE PROGRESSION PAIRS ───
# Each pair shows WHY a skill order matters, not just what to pick

skill_tree_pairs = [
    # 1. Build order matters — same skills, different sequence, different outcome
    {
        "instruction": "I just started as a Commander class. Should I max my Shield Wall skill first or spread points across Command Aura and Battle Cry?",
        "output": (
            "Max Shield Wall first. Here's why the order matters:\n\n"
            "Shield Wall (KO primary, defensive stance) gives you SURVIVABILITY. "
            "You can't lead if you're dead. Command Aura and Battle Cry are force multipliers — "
            "they amplify your party's output. But multiplying zero is still zero.\n\n"
            "The build order: Shield Wall 5 → Command Aura 3 → Battle Cry 1 → then spread.\n\n"
            "This mirrors how learning works: you need a stable foundation (KO intent clarity) "
            "before you can coordinate others (AV transport) or enforce rules (RU policy). "
            "A leader who can't survive contact doesn't get to use their leadership skills.\n\n"
            "The exception: if you're running with a dedicated healer from day one, you can go "
            "Command Aura first because someone else is handling your survivability. Context determines build order."
        ),
        "tongue": "KO",
        "tongues_active": ["KO", "AV", "RU"],
        "layer": "L13",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "build_order_dependency",
    },
    # 2. Hybrid builds vs pure builds
    {
        "instruction": "Everyone says pure DPS Artificer is the meta. Why would I ever go hybrid Artificer/Shadow?",
        "output": (
            "Pure DPS Artificer (CA-only) tops the damage charts in controlled scenarios — "
            "raid dummies, parsed fights, tier lists. But tier lists measure ONE dimension.\n\n"
            "Hybrid Artificer/Shadow (CA+UM) does less peak damage but gains:\n"
            "- Stealth crafting (make items without revealing your recipe to competitors)\n"
            "- Exploit detection (UM's security sense spots broken interactions CA creates)\n"
            "- Self-sufficiency (don't need a Shadow teammate to scout dangerous areas)\n\n"
            "The meta answer depends on the QUESTION. 'What does the most damage?' → pure CA. "
            "'What survives the most situations?' → hybrid CA/UM. 'What's most valuable to a guild?' → "
            "depends on what the guild already has.\n\n"
            "Real optimization isn't max(one_stat). It's max(value_to_context). "
            "A hybrid build IS the multi-tongue agent — less specialized but more adaptable. "
            "The solo leveler who hides their crafting recipes is playing both classes at once."
        ),
        "tongue": "CA",
        "tongues_active": ["CA", "UM"],
        "layer": "L12",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "hybrid_vs_pure_specialization",
    },
    # 3. Respec — when the system lets you rebuild
    {
        "instruction": "I wasted 30 skill points on the wrong tree. Should I pay the respec cost or just make a new character?",
        "output": (
            "Respec. Here's the math:\n\n"
            "New character: Lose ALL progress. Level 1. Zero reputation. Zero gear. Zero learned patterns. "
            "You keep your player knowledge but the character starts blank.\n\n"
            "Respec: Keep your level, gear, reputation, quest completions, discovered map areas, "
            "crafting recipes, faction standing. You only lose the POINT ALLOCATION — the decisions, "
            "not the experience.\n\n"
            "Those 30 'wasted' points taught you something. You learned what DOESN'T work in that tree. "
            "That knowledge doesn't reset with a respec — it makes your next allocation better.\n\n"
            "The only reason to reroll: if your CLASS is wrong, not your build. If you're a Commander "
            "who should have been a Shadow, no respec fixes that. But if you're a Commander who put "
            "points into the wrong Commander skills, respec preserves everything that matters.\n\n"
            "Experience is accumulation, not allocation. The points are rearrangeable. The levels aren't."
        ),
        "tongue": "KO",
        "tongues_active": ["KO", "RU", "DR"],
        "layer": "L13",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "respec_vs_reroll",
    },
    # 4. Manhwa: The system lies
    {
        "instruction": "In Solo Leveling, the system shows Sung Jin-Woo as an E-rank hunter. But he's clearly not. When does a status screen lie?",
        "output": (
            "The system lies when it measures the WRONG thing. Jin-Woo's E-rank was accurate — "
            "for the metric being measured. His raw stats WERE E-rank. The system wasn't lying about "
            "his current power. It was blind to his POTENTIAL.\n\n"
            "Status screens lie by omission in three ways:\n\n"
            "1. **Measuring the snapshot, not the trajectory** — Your stats right now vs your rate of growth. "
            "Jin-Woo's growth rate was infinite. The system only showed position, not velocity.\n\n"
            "2. **Measuring the visible, not the hidden** — Public stats vs private capabilities. "
            "The Shadow Monarch powers weren't in the hunter classification system AT ALL. "
            "You can't rank what you can't see.\n\n"
            "3. **Measuring against the wrong baseline** — E-rank among hunters vs E-rank among all beings. "
            "The ranking system assumed human parameters. He stopped being human.\n\n"
            "This is why single-metric evaluation fails. A model that scores 95% on a benchmark "
            "might be an E-rank hunter — measured perfectly on the wrong scale. "
            "Multi-tongue evaluation (KO+AV+RU+CA+UM+DR) catches what any single metric misses. "
            "The system doesn't lie — it just doesn't ask enough questions."
        ),
        "tongue": "UM",
        "tongues_active": ["UM", "KO", "DR"],
        "layer": "L11",
        "governance": "ALLOW",
        "category": "manhwa_trope",
        "trope": "system_lies_by_omission",
    },
    # 5. Manhwa: Regression and re-leveling
    {
        "instruction": "Why do regression manhwa protagonists always speed through early content? Isn't that unrealistic?",
        "output": (
            "It's not speed — it's RECOGNITION. The regressor isn't learning faster. "
            "They're pattern-matching against memories. First time through the dungeon: "
            "every room is new, every trap is surprising, every boss requires learning. "
            "Second time: 'I know this room. The trap is on the left. The boss is weak to fire.'\n\n"
            "What they're actually doing:\n"
            "- L0 (raw input) is identical — same dungeon, same mobs, same geometry\n"
            "- L1 (encoding) is DIFFERENT — they have prior tongue-weights from the first life\n"
            "- L2 (governance) is DIFFERENT — they know which threats are real vs which are bluffs\n"
            "- L3 (expression) is DIFFERENT — they act with certainty instead of caution\n\n"
            "The unrealistic part isn't the speed. It's that manhwa regressors never have to UNLEARN "
            "bad habits from the first life. Real regression would include: 'I know fire works on this boss, "
            "but I also know I developed a crutch dependency on fire magic that made me weak to ice bosses later.' "
            "The best regression stories (like Omniscient Reader) show the protagonist's FIRST LIFE MISTAKES "
            "creating blind spots in the second.\n\n"
            "Transfer learning isn't free. Prior weights help AND constrain."
        ),
        "tongue": "AV",
        "tongues_active": ["AV", "KO", "CA"],
        "layer": "L11",
        "governance": "ALLOW",
        "category": "manhwa_trope",
        "trope": "regression_is_transfer_learning",
    },
    # 6. Skill tree: The unlock you don't use yet
    {
        "instruction": "There's a skill in the Shadow tree called 'Veil Mastery' that's useless until level 50. Should I unlock it early or skip it?",
        "output": (
            "Unlock it at level 30, even though you can't USE it until 50. Here's why:\n\n"
            "Veil Mastery has PASSIVE benefits even before activation. Having it on your tree means:\n"
            "- The game tracks stealth-related stats you'd otherwise miss (XP in shadow zones counts)\n"
            "- Prerequisite skills that lead to Veil Mastery are useful on their own\n"
            "- Your build path is committed — you won't accidentally spend those points elsewhere\n\n"
            "This is curriculum planning. A student who knows they're taking Calculus 2 next semester "
            "studies differently in Calculus 1. They pay attention to integration techniques even when "
            "the current test only covers derivatives. The KNOWLEDGE of what's coming shapes how you learn NOW.\n\n"
            "The cost: 3 skill points locked into a tree you can't fully use yet. "
            "The benefit: when level 50 hits, you don't need to respec — you've been building toward it.\n\n"
            "Early investment in apparently-useless skills is how you avoid the 'wasted 30 points' problem. "
            "Plan the build before you need it."
        ),
        "tongue": "UM",
        "tongues_active": ["UM", "DR", "RU"],
        "layer": "L12",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "early_investment_delayed_payoff",
    },
    # 7. Manhwa: Party composition = multi-tongue coverage
    {
        "instruction": "Every raid guide says you need a tank, healer, DPS, and support. But I've seen 4-DPS speedruns clear faster. Why have roles at all?",
        "output": (
            "4-DPS speedruns work when you know the fight PERFECTLY. Every mechanic is scripted, "
            "every dodge is practiced, every cooldown is mapped. Zero uncertainty = zero need for flexibility.\n\n"
            "Roles exist because UNCERTAINTY exists:\n"
            "- Tank (KO): Absorbs unexpected damage. If nothing unexpected happens, waste of a slot.\n"
            "- Healer (RU): Corrects mistakes. If no mistakes happen, waste of a slot.\n"
            "- Support (AV): Enables others. If everyone's already at max efficiency, waste of a slot.\n"
            "- DPS (CA): Applies force. Always useful, but force without direction is chaos.\n\n"
            "The 4-DPS comp is a PROOF — proof that you've solved the fight completely. "
            "It's not a strategy. It's a victory lap.\n\n"
            "For NEW content — content you haven't mapped, content that can surprise you — "
            "role diversity is mandatory. You need tongues that cover different failure modes: "
            "KO for when intent is unclear, UM for when threats are hidden, DR for when structure breaks.\n\n"
            "A model trained on only one type of data (4-DPS) excels at known benchmarks and collapses "
            "on novel inputs. Multi-tongue coverage is raid composition for the mind."
        ),
        "tongue": "AV",
        "tongues_active": ["KO", "AV", "RU", "CA"],
        "layer": "L13",
        "governance": "ALLOW",
        "category": "manhwa_trope",
        "trope": "role_diversity_vs_speedrun",
    },
    # 8. The hidden stat — what the skill tree doesn't show
    {
        "instruction": "My character sheet shows STR, DEX, INT, WIS, CON, CHA. But the best players talk about 'game sense' which isn't a stat. What is it?",
        "output": (
            "Game sense is the META-STAT — the ability to read the situation using ALL your stats simultaneously "
            "and choose the right one to apply. It's not on the character sheet because it's not IN the character. "
            "It's in the PLAYER.\n\n"
            "A high-INT low-game-sense player casts the right spell at the wrong time. "
            "A low-INT high-game-sense player uses a cantrip at the perfect moment and changes the fight.\n\n"
            "Game sense is:\n"
            "- Knowing WHEN to tank and when to dodge (KO: intent reading)\n"
            "- Knowing WHERE the fight will move next (AV: trajectory prediction)\n"
            "- Knowing WHO to protect vs WHO can protect themselves (RU: priority governance)\n"
            "- Knowing WHAT ability to use when multiple work (CA: optimization)\n"
            "- Knowing what the enemy ISN'T showing you (UM: absence detection)\n"
            "- Knowing the fight's STRUCTURE — phases, transitions, enrage timers (DR: schema)\n\n"
            "Game sense is all six tongues firing simultaneously on a single decision. "
            "It's the pazaak game in your head — you see the board, you see your cards, "
            "you see the opponent's patterns, and you CHOOSE. Not react. Choose.\n\n"
            "You can't level game sense from the skill tree. You level it by playing."
        ),
        "tongue": "DR",
        "tongues_active": ["KO", "AV", "RU", "CA", "UM", "DR"],
        "layer": "L11",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "meta_stat_game_sense",
    },
    # 9. Manhwa: The protagonist's cheat skill
    {
        "instruction": "Every manhwa protagonist has ONE broken ability that makes them special. Is that realistic or just lazy writing?",
        "output": (
            "Both, depending on how it's used.\n\n"
            "**Lazy version:** The ability has no cost, no limit, no trade-off. Protagonist wins because "
            "the author says so. This is deus ex machina — the 'command magic' approach where one person's "
            "will overrides the system. No geometry, no cost scaling, no earned competence.\n\n"
            "**Good version:** The ability is NARROW but DEEP. It does one thing that reshapes how every "
            "other system interacts with the protagonist:\n"
            "- Sung Jin-Woo's shadow extraction: ONE mechanic (convert dead enemies to allies) that "
            "changes EVERY fight's calculus. But it requires killing first, managing shadow army upkeep, "
            "and the shadows have their own limitations.\n"
            "- Kim Dokja's fourth wall: ONE ability (read the story) that provides information but NOT power. "
            "He still has to ACT on what he knows, and the story fights back.\n\n"
            "The 'cheat skill' maps to PRIMARY TONGUE. A KO-primary agent has ONE strong axis (intent/command) "
            "that reshapes how it processes everything else. It's not that the other tongues don't exist — "
            "it's that KO is weighted 1.0 while DR is weighted 11.09 for someone ELSE. "
            "Your primary tongue IS your cheat skill. It's the lens, not the answer.\n\n"
            "A protagonist with ALL stats maxed is boring. A protagonist with ONE unusual angle on "
            "a familiar problem is a story worth reading."
        ),
        "tongue": "KO",
        "tongues_active": ["KO", "CA", "UM"],
        "layer": "L12",
        "governance": "ALLOW",
        "category": "manhwa_trope",
        "trope": "cheat_skill_is_primary_tongue",
    },
    # 10. Graduation raid — the final exam
    {
        "instruction": "What would a 'graduation dungeon' look like that tests whether you actually learned your class?",
        "output": (
            "The graduation dungeon can't be cheesed with one strategy. It has to test ALL your trees, "
            "not just your main one. Here's the design:\n\n"
            "**Phase 1 — Solo room (tests primary tongue depth)**\n"
            "Your class specialty, maximum difficulty. Commander tanks an unkillable boss for 3 minutes. "
            "Shadow steals an item from an all-seeing guardian. Artificer builds a bridge from random materials.\n\n"
            "**Phase 2 — Wrong-class challenge (tests cross-tongue breadth)**\n"
            "You must solve a problem from ANOTHER class's domain. The Commander must sneak. "
            "The Shadow must lead. The Artificer must heal. You don't need to be GOOD at it — "
            "you need to be COMPETENT. Minimum credits in all six tongues.\n\n"
            "**Phase 3 — Contradiction room (tests truth-seeking)**\n"
            "The dungeon gives you contradictory information. The map says go left, the compass says go right, "
            "the NPC says don't move. ONE of them is lying. You have to figure out which, and the answer "
            "depends on context clues from Phase 1 and 2. This tests whether you LEARNED or MEMORIZED.\n\n"
            "**Phase 4 — The choice (tests identity)**\n"
            "Two doors. One gives you a legendary item for your class. The other gives a rare item to "
            "every party member. No wrong answer — but your CHOICE reveals whether you're playing "
            "for yourself or for the team. The dungeon records it. Your character doesn't change. "
            "But the WORLD remembers.\n\n"
            "If you can pass all four phases, you've graduated. Not because you're max level. "
            "Because you're a complete player."
        ),
        "tongue": "DR",
        "tongues_active": ["KO", "AV", "RU", "CA", "UM", "DR"],
        "layer": "L13",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "graduation_dungeon",
    },
    # 11. Manhwa: Power scaling and the soft cap
    {
        "instruction": "Why do manhwa characters hit a 'wall' at certain ranks? S-rank hunters plateau while A-ranks keep growing.",
        "output": (
            "Because growth has two phases, and most people only train for one.\n\n"
            "**Phase 1: Vertical growth** (E→D→C→B→A)\n"
            "More power in your primary stat. Swing harder. Cast bigger. Run faster. "
            "Linear relationship: more training = more power. Every rank is earned by doing MORE of the same.\n\n"
            "**Phase 2: Horizontal growth** (A→S→SS→...)\n"
            "More DIMENSIONS, not more power. An S-rank isn't just an A-rank who hits harder. "
            "They operate in additional dimensions that A-ranks don't have access to. "
            "S-rank hunters sense killing intent. They predict attacks before execution. "
            "They understand the ECOLOGY of the dungeon, not just the enemies inside it.\n\n"
            "The wall at A→S is the transition from vertical to horizontal. "
            "Hunters who keep trying to punch harder plateau forever. "
            "Hunters who develop NEW capabilities break through.\n\n"
            "In tongue terms: A-rank = maxed primary tongue. S-rank = primary tongue PLUS "
            "meaningful secondary and tertiary tongues. The wall isn't power — it's dimension.\n\n"
            "This is why 'just train more data' eventually plateaus for AI models too. "
            "More of the same data = vertical growth. Multi-view training (binary/math/english) = "
            "horizontal growth. The breakthrough isn't more — it's MORE KINDS."
        ),
        "tongue": "CA",
        "tongues_active": ["CA", "KO", "DR"],
        "layer": "L12",
        "governance": "ALLOW",
        "category": "manhwa_trope",
        "trope": "vertical_vs_horizontal_growth",
    },
    # 12. Skill tree: The trap skill
    {
        "instruction": "Some skills look amazing in the tooltip but are actually garbage. How do you spot a trap skill?",
        "output": (
            "Trap skills share three tells:\n\n"
            "**1. No synergy** — The skill is powerful in isolation but doesn't connect to anything else. "
            "A 500-damage nuke that doesn't combo with any other ability. In tongue terms: "
            "a skill that only activates ONE tongue with zero interaction with the other five. "
            "Real power comes from combinations, not isolated spikes.\n\n"
            "**2. Conditional on opponent failure** — 'Deals double damage to stunned targets' sounds great "
            "until you realize the boss is stun-immune. Skills that require specific enemy states "
            "only work when the enemy cooperates. Real skills work regardless of opponent.\n\n"
            "**3. Opportunity cost blindness** — A skill that gives +10% damage for 5 points sounds good. "
            "Until you see that 5 points in a different tree gives +8% damage AND +15% survivability AND "
            "unlocks a prerequisite for a tier-3 skill. The trap isn't that it's bad — "
            "it's that the ALTERNATIVE is better.\n\n"
            "The meta-trap: skills that make you feel powerful without making you EFFECTIVE. "
            "Big numbers, flashy animations, tooltip bragging rights. "
            "The model equivalent: high benchmark scores on tasks that don't transfer to real use.\n\n"
            "Always ask: 'What am I NOT taking by taking this?'"
        ),
        "tongue": "RU",
        "tongues_active": ["RU", "CA", "UM"],
        "layer": "L12",
        "governance": "ALLOW",
        "category": "skill_tree_build",
        "trope": "trap_skill_detection",
    },
]

def main():
    outpath = "training-data/sft/skill_tree_manhwa_sft.jsonl"
    records = []

    for pair in skill_tree_pairs:
        record = {
            "instruction": pair["instruction"],
            "output": pair["output"],
            "tongue": pair["tongue"],
            "tongues_active": pair["tongues_active"],
            "tongues_null": [t for t in ["KO", "AV", "RU", "CA", "UM", "DR"] if t not in pair["tongues_active"]],
            "layer": pair["layer"],
            "governance": pair["governance"],
            "category": pair["category"],
            "trope": pair["trope"],
            "is_preferred": True,
            "source": "skill_tree_manhwa_generator",
            "timestamp": TIMESTAMP,
        }
        records.append(record)

    with open(outpath, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Stats
    categories = {}
    tongue_dist = {}
    tropes = set()
    for r in records:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1
        t = r["tongue"]
        tongue_dist[t] = tongue_dist.get(t, 0) + 1
        tropes.add(r["trope"])

    print(f"=== Skill Tree + Manhwa Tropes ===")
    print(f"Total: {len(records)} records")
    print(f"\nCategories:")
    for k, v in sorted(categories.items()):
        print(f"  {k}: {v}")
    print(f"\nPrimary tongue distribution:")
    for k, v in sorted(tongue_dist.items()):
        print(f"  {k}: {v}")
    print(f"\nUnique tropes: {len(tropes)}")
    print(f"\nOutput: {outpath}")


if __name__ == "__main__":
    main()
