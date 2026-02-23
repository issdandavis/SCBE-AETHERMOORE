#!/usr/bin/env python3
"""
spiralverse_game_to_sft.py — Export SFT training pairs from Spiralverse game systems.

Tributaries:
  1. Combat telemetry  (attack/dodge/block decisions, enemy AI, damage events)
  2. Story branching   (ChoiceScript choices with effects and karma)
  3. MMO chat          (slash commands, AI agent dialogue, emotes)
  4. Lore discoveries  (Morrowind-style book content + cross-references)
  5. Dream sequences   (day event replay + Polly commentary)
  6. World exploration  (region descriptions, tongue affinities, connections)

Output: training-data/sft_spiralverse_game.jsonl

Usage:
    python scripts/spiralverse_game_to_sft.py
    python scripts/spiralverse_game_to_sft.py --output training-data/sft_spiralverse_game.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

METADATA_BASE = {
    "source": "spiralverse_game",
    "version": "1.0.0",
    "author": "Issac Davis",
    "origin": "tuxemon_spiralverse",
    "source_type": "game_telemetry",
    "quality": {"dedup": True, "validated": True},
}


def _meta(track: str = "system", **extra: Any) -> dict:
    m = dict(METADATA_BASE)
    m["track"] = track
    m.update(extra)
    return m


# ---------------------------------------------------------------------------
# Tributary 1: Combat telemetry
# ---------------------------------------------------------------------------

def gen_combat_pairs() -> list[dict]:
    """Generate SFT pairs from the Zelda-style combat system."""
    pairs = []

    # Combat mechanics explanation pairs
    combat_scenarios = [
        {
            "situation": "A Goblin is 1 tile away, facing the player. Player HP 25/30.",
            "action": "attack",
            "reasoning": "The enemy is within melee range and the player has sufficient HP. Press Z to swing sword in the facing direction. The attack hitbox extends 1 tile forward.",
        },
        {
            "situation": "Two enemies closing in. Player HP 8/30, no shield.",
            "action": "dodge",
            "reasoning": "Low HP makes taking damage risky. Press X to dodge roll — this grants invincibility frames (0.3s) and moves 4 tiles/sec in the facing direction for 0.25s. Use the i-frames to escape the pinch.",
        },
        {
            "situation": "A strong enemy is winding up an attack. Player HP 20/30.",
            "action": "block",
            "reasoning": "Hold C to raise shield. Blocking reduces incoming damage to 1/3 of the base amount. Since HP is comfortable, tanking the reduced hit is safer than risking a mis-timed dodge.",
        },
        {
            "situation": "Enemy is at 1 HP, player is at full health.",
            "action": "attack",
            "reasoning": "Finish the enemy with a sword swing (Z). One hit will deal base attack (8) minus enemy defense, which is more than enough to kill a 1 HP target.",
        },
        {
            "situation": "Player just took a hit. I-frames are active for 0.3 seconds.",
            "action": "attack",
            "reasoning": "I-frames make the player invincible temporarily. Use this window aggressively — press Z to counterattack while immune to further damage.",
        },
        {
            "situation": "Guard-type enemy stands still near a treasure. Player approaches from the side.",
            "action": "attack",
            "reasoning": "Guard enemies only chase when the player enters their aggro range (3 tiles). Strike first from maximum melee range (1 tile) to get a free hit before the guard reacts.",
        },
        {
            "situation": "A Patrol enemy is walking away from the player.",
            "action": "approach and attack",
            "reasoning": "Patrol enemies follow a set route. Close the gap while their back is turned, then press Z for a clean first strike. They won't aggro until you enter their detection range.",
        },
        {
            "situation": "Player HP 3/30. Dream sequence available (sleep at inn).",
            "action": "retreat and sleep",
            "reasoning": "Critically low HP. Dreams fully restore HP and generate training data from the day's events. Retreat to the nearest inn, sleep, and return at full strength.",
        },
    ]

    for i, scenario in enumerate(combat_scenarios):
        pairs.append({
            "id": f"sft-game-combat-{i+1:03d}",
            "category": "action_combat",
            "instruction": (
                f"Spiralverse action combat scenario: {scenario['situation']} "
                f"What should the player do? (Z=attack, X=dodge, C=block)"
            ),
            "response": (
                f"Action: {scenario['action'].upper()}\n\n"
                f"Reasoning: {scenario['reasoning']}"
            ),
            "metadata": _meta("functions", tributary="combat"),
        })

    # Combat system architecture pairs
    system_pairs = [
        (
            "How does the Spiralverse action combat hitbox system work?",
            "The Spiralverse combat system uses tile-space rectangular hitboxes. Each "
            "CombatEntity has a hitbox at its tile position (1x1 tile). When the player "
            "attacks (Z key), an attack hitbox spawns 1 tile in the facing direction. "
            "Overlap detection uses AABB (Axis-Aligned Bounding Box) collision: two hitboxes "
            "overlap if x1 < x2+w2 AND x1+w1 > x2 AND y1 < y2+h2 AND y1+h1 > y2. Damage "
            "is calculated as max(1, attacker.attack - defender.defense). Blocked damage is "
            "reduced to floor(damage / 3)."
        ),
        (
            "Explain the invincibility frame system in Spiralverse combat.",
            "After taking damage, a CombatEntity enters invincibility frames (i-frames) for "
            "0.5 seconds. During i-frames, all incoming damage is nullified (take_damage returns 0). "
            "Dodge rolling (X key) also grants i-frames for the roll duration (0.3s). The i-frame "
            "timer counts down each frame: _invincible_timer -= dt. When it hits 0, the entity "
            "becomes vulnerable again. This prevents stun-locking and rewards well-timed dodges."
        ),
        (
            "How does enemy AI work in Spiralverse overworld combat?",
            "Enemy AI uses four behavior states: PATROL (walk a set route, 1.5 tiles/sec), "
            "CHASE (pursue the player at 2.0 tiles/sec when within aggro_range of 3 tiles), "
            "GUARD (stand still until player enters aggro_range, then chase), and FLEE (run "
            "away when HP drops below 20%). State transitions happen in update_ai(): if the "
            "player is within aggro_range and behavior allows chasing, switch to CHASE. If "
            "within attack_range (1.2 tiles), attack. The AI decision loop runs every frame, "
            "with attack cooldowns preventing spam."
        ),
        (
            "How does Spiralverse combat generate AI training data?",
            "Every combat action is logged to combat_log with timestamp, event type, player "
            "HP, player position, and action-specific data. The get_training_pairs() method "
            "converts logs to SFT instruction/response pairs. Example: a 'player_attack' event "
            "becomes instruction='Action combat: Player at (2.0, 3.0), facing right, HP 25. "
            "Enemy Goblin nearby. What do you do?' with output='Attack! Deal 7 damage.' This "
            "teaches the AI to make combat decisions based on spatial context."
        ),
        (
            "What is knockback in Spiralverse combat and how does it work?",
            "Knockback is a physics-based displacement applied when an entity takes damage. "
            "The knockback direction is determined by the attacker's facing direction. Knockback "
            "speed starts at 6 tiles/sec and decays over 0.2 seconds via linear interpolation. "
            "During knockback, the entity enters hit_stun state and cannot act. The position "
            "update: tile_x += kb_dx * kb_speed * dt, tile_y += kb_dy * kb_speed * dt, where "
            "(kb_dx, kb_dy) are the direction offsets. Knockback prevents enemies from immediately "
            "counterattacking after being hit."
        ),
    ]

    for i, (instruction, response) in enumerate(system_pairs):
        pairs.append({
            "id": f"sft-game-combat-sys-{i+1:03d}",
            "category": "action_combat",
            "instruction": instruction,
            "response": response,
            "metadata": _meta("functions", tributary="combat"),
        })

    return pairs


# ---------------------------------------------------------------------------
# Tributary 2: Story branching
# ---------------------------------------------------------------------------

def gen_story_pairs() -> list[dict]:
    """Generate SFT pairs from the ChoiceScript branching story system."""
    pairs = []

    # Story choice scenarios
    story_choices = [
        {
            "scene": "tongue_choice",
            "context": "After awakening through the portal into the Spiralverse, Polly asks you to choose your Sacred Tongue affinity.",
            "choices": ["Kor'aelin (KO) — Heart-Eternal, collaborative resonance",
                       "Avali (AV) — Common Tongue, diplomacy and context",
                       "Runethic (RU) — Ancient Tongue, temporal anchoring",
                       "Cassisivadan (CA) — Nature's Speech, ecological communion"],
            "analysis": "This choice determines your starter monster type and tongue affinity. KO gives Lightning/Metal types (Spirling line), AV gives Cosmic/Aether types, RU gives Earth/Wood types (Embrite line), CA gives Fire/Shadow types. Each tongue also affects which NPCs trust you more and which regions feel 'home'.",
        },
        {
            "scene": "mom_quest",
            "context": "Mom hands you Dad's keys and asks you to bring them to him at the beach. On the way, you encounter NPCs.",
            "choices": ["Go straight to the beach (efficient)", "Explore Dawn Village first (lore)", "Help the NPC with their problem (karma)"],
            "analysis": "The Fable-style reactive dad will comment on your journey. Going straight shows discipline. Exploring reveals lore books and region info. Helping NPCs builds karma which affects future story branches and NPC trust levels.",
        },
        {
            "scene": "first_enemy",
            "context": "A wild monster blocks the path to the beach. You have your starter and basic combat abilities.",
            "choices": ["Fight with Zelda combat (Z/X/C)", "Use monster battle (traditional turn-based)", "Try to sneak past"],
            "analysis": "Spiralverse offers hybrid combat: real-time Zelda action for overworld and traditional monster battles. Fighting builds combat training data. Sneaking teaches evasion patterns. Monster battles generate turn-based strategy data.",
        },
        {
            "scene": "guild_invitation",
            "context": "After meeting Dad, a Guild Scout approaches. Each Sacred Tongue guild offers different benefits.",
            "choices": ["Join the KO Guild (collaboration bonuses)", "Join the tongue-matching guild", "Decline and go independent", "Ask for more information"],
            "analysis": "Guild membership affects: chat channels available (/guild), multiplayer party matching, training data categories generated, and story branches. Independent players get freedom but miss guild-exclusive lore.",
        },
    ]

    for i, choice in enumerate(story_choices):
        choices_text = "\n".join(f"  {j+1}. {c}" for j, c in enumerate(choice["choices"]))
        pairs.append({
            "id": f"sft-game-story-{i+1:03d}",
            "category": "story_branching",
            "instruction": (
                f"Spiralverse story scene '{choice['scene']}': {choice['context']}\n\n"
                f"Available choices:\n{choices_text}\n\n"
                f"Analyze these choices and their consequences."
            ),
            "response": choice["analysis"],
            "metadata": _meta("system", tributary="story"),
        })

    # Story engine architecture
    engine_pairs = [
        (
            "How does the Spiralverse ChoiceScript branching system work?",
            "The StoryEngine manages chapters containing scenes. Each StoryScene has dialogue "
            "lines, a speaker, and a list of StoryChoice objects. Each choice has: text (what "
            "the player sees), next_scene (where it leads), effects dict (set_var, karma, "
            "relationship changes), and conditions (variable checks that must pass). When the "
            "player makes a choice, the engine: 1) checks conditions, 2) applies effects to "
            "the variable store, 3) logs the choice for AI training, 4) navigates to next_scene. "
            "Every choice generates an SFT pair: instruction=context+choices, output=selected choice."
        ),
        (
            "How does the Spiralverse story system export AI training data?",
            "The StoryEngine maintains a training_log of every choice made. export_training_data() "
            "converts each log entry to an SFT pair with instruction='Story context: {scene_context}. "
            "Choices: {options}. What do you choose?' and output='Choose: {selected_choice}. "
            "Reasoning: {effects applied}'. The export_sft_jsonl(path) method writes these as "
            "JSONL. DPO (Direct Preference Optimization) pairs can also be generated by pairing "
            "chosen vs. rejected options, teaching the model preference alignment."
        ),
    ]

    for i, (instruction, response) in enumerate(engine_pairs):
        pairs.append({
            "id": f"sft-game-story-sys-{i+1:03d}",
            "category": "story_branching",
            "instruction": instruction,
            "response": response,
            "metadata": _meta("system", tributary="story"),
        })

    return pairs


# ---------------------------------------------------------------------------
# Tributary 3: MMO chat
# ---------------------------------------------------------------------------

def gen_chat_pairs() -> list[dict]:
    """Generate SFT pairs from the MMO chat system."""
    pairs = []

    chat_examples = [
        ("/say Hello everyone!", "SAY", "[SAY] Player: Hello everyone!", "Basic local chat visible to nearby players."),
        ("/shout WORLD BOSS AT VOLCANIC RIM!", "SHOUT", "[SHOUT] Player: WORLD BOSS AT VOLCANIC RIM!", "Server-wide announcement, costs stamina to prevent spam."),
        ("/whisper Aria Be careful in the Shadow Wastes", "WHISPER", "[WHISPER -> Aria] Player: Be careful in the Shadow Wastes", "Private message to a specific player."),
        ("/emote dance", "EMOTE", "[EMOTE] Player dances!", "Expressive animation visible to nearby players. Available: wave, dance, bow, laugh, shrug, flex, meditate, caw."),
        ("/party Let's tackle Crystal Caverns", "PARTY", "[PARTY] Player: Let's tackle Crystal Caverns", "Message visible only to party members."),
        ("/guild Need 2 more for Thunder Peaks raid", "GUILD", "[GUILD] Player: Need 2 more for Thunder Peaks raid", "Message to all online guild members."),
        ("/trade SomeGuy", "TRADE", "[TRADE] Player wants to trade with SomeGuy", "Initiates a trade request with another player."),
    ]

    for i, (command, channel, output, explanation) in enumerate(chat_examples):
        pairs.append({
            "id": f"sft-game-chat-{i+1:03d}",
            "category": "mmo_chat",
            "instruction": f"Spiralverse MMO: Player types '{command}'. What happens?",
            "response": f"Channel: {channel}\nOutput: {output}\n\n{explanation}",
            "metadata": _meta("functions", tributary="chat"),
        })

    # AI chat agent behavior
    ai_contexts = [
        ("battle_brag", "Just beat a wild Embrite!", "The AI agent generates boastful but friendly dialogue about recent combat victories, encouraging other players."),
        ("lore_discuss", "Found the Book of Six Tongues in Spirit Woods", "The AI agent shares lore discoveries and asks questions about Sacred Tongue meanings, promoting exploration."),
        ("trade_offer", "Looking for Frost-type monster, have Fire-types to trade", "The AI agent generates trade requests based on its monster inventory and desired types."),
        ("quest_hint", "Anyone know where the World Tree approach is?", "The AI agent provides subtle directional hints without spoiling, referencing region connections."),
        ("greeting", "entering Aether Clearing", "The AI agent greets players entering a region with tongue-appropriate phrases (e.g., KO phrases in KO-aligned regions)."),
    ]

    for i, (context, trigger, explanation) in enumerate(ai_contexts):
        pairs.append({
            "id": f"sft-game-chat-ai-{i+1:03d}",
            "category": "mmo_chat",
            "instruction": f"Spiralverse AI chat agent context '{context}': {trigger}. How should the AI respond?",
            "response": explanation,
            "metadata": _meta("functions", tributary="chat"),
        })

    return pairs


# ---------------------------------------------------------------------------
# Tributary 4: Lore books
# ---------------------------------------------------------------------------

def gen_lore_pairs() -> list[dict]:
    """Generate SFT pairs from Morrowind-style lore books."""
    pairs = []

    # Import lore library from game module
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tuxemon-spiralverse"))
        from tuxemon.spiralverse_world import LORE_LIBRARY
        for slug, book in LORE_LIBRARY.items():
            # Book content as knowledge pair
            pairs.append({
                "id": f"sft-game-lore-{slug}",
                "category": "spiralverse-lore",
                "instruction": f"What does the Spiralverse lore book '{book.title}' contain?",
                "response": (
                    f"Title: {book.title}\n"
                    f"Author: {book.author}\n"
                    f"Location hint: {book.location_hint}\n"
                    f"Sacred Tongue: {book.tongue}\n\n"
                    f"{book.text}"
                ),
                "metadata": _meta("system", tributary="lore", book_slug=slug),
            })

            # Discovery scenario pair
            pairs.append({
                "id": f"sft-game-lore-disc-{slug}",
                "category": "spiralverse-lore",
                "instruction": (
                    f"A player discovers the lore book '{book.title}' by {book.author} "
                    f"in {book.location_hint}. This book is associated with the {book.tongue} "
                    f"Sacred Tongue. What should the LoreCodex record?"
                ),
                "response": (
                    f"The LoreCodex records: slug='{slug}', discovery timestamp, and increments "
                    f"read_count. The DayTracker logs a 'lore_found' event with book='{slug}'. "
                    f"At sleep time, the DreamGenerator may incorporate this discovery into a "
                    f"dream sequence: 'The words from \"{book.title}\" float before your eyes, "
                    f"glowing with aether...' This creates a reinforcement loop where discoveries "
                    f"are replayed during dreams, deepening the AI's understanding."
                ),
                "metadata": _meta("system", tributary="lore", book_slug=slug),
            })
    except ImportError:
        print("  WARN: Could not import LORE_LIBRARY from game module", file=sys.stderr)

    return pairs


# ---------------------------------------------------------------------------
# Tributary 5: Dream sequences
# ---------------------------------------------------------------------------

def gen_dream_pairs() -> list[dict]:
    """Generate SFT pairs from the sleep/dream mechanic."""
    pairs = []

    dream_scenarios = [
        {
            "day_events": ["Won battle against Goblin", "Found lore: Book of Six Tongues", "Explored Dawn Village"],
            "dream": [
                "=== DREAM SEQUENCE (Night 1) ===",
                "You relive the fight. This time, you see openings you missed before.",
                "The words from 'The Book of Six Tongues' float before your eyes, glowing with aether...",
                "You dream of Dawn Village, but it looks different — more vivid, more alive.",
                "Polly perches on your dream-shoulder: 'Your mind processes the day's lessons...'",
                ">>> HP fully restored <<<",
            ],
        },
        {
            "day_events": ["Lost battle against Dragon Guard", "Talked to Aria about ancient history", "Chose to help the NPC merchant"],
            "dream": [
                "=== DREAM SEQUENCE (Night 2) ===",
                "In your dream, the Dragon Guard appears again, but this time everything is different...",
                "Aria's words echo in a vast, empty space...",
                "Your choice echoes through dream-space, branching into infinite possibilities.",
                "Polly caws softly: 'Even in sleep, the spiral teaches...'",
                ">>> HP fully restored <<<",
            ],
        },
        {
            "day_events": ["Combat: attack", "Combat: dodge", "Combat: block"],
            "dream": [
                "=== DREAM SEQUENCE (Night 3) ===",
                "Your sword arm moves in your sleep. Muscle memory forming.",
                "The dodge roll replays perfectly in your dream. Your body learns.",
                "You dream of combat — faster, sharper, more precise than reality.",
                "Polly watches: 'Practice makes permanent, even in dreams.'",
                ">>> HP fully restored <<<",
            ],
        },
    ]

    for i, scenario in enumerate(dream_scenarios):
        events_text = "\n".join(f"  - {e}" for e in scenario["day_events"])
        dream_text = "\n".join(scenario["dream"])
        pairs.append({
            "id": f"sft-game-dream-{i+1:03d}",
            "category": "dream_system",
            "instruction": (
                f"Spiralverse sleep mechanic: The player goes to sleep after these day events:\n"
                f"{events_text}\n\n"
                f"Generate a dream sequence that replays and reinforces today's experiences."
            ),
            "response": dream_text,
            "metadata": _meta("system", tributary="dreams"),
        })

    # Dream system architecture
    pairs.append({
        "id": "sft-game-dream-arch-001",
        "category": "dream_system",
        "instruction": "How does the Spiralverse dream generation system work?",
        "response": (
            "The DreamGenerator creates dream sequences from daily events tracked by the "
            "DayTracker. Process:\n\n"
            "1. DayTracker.end_day() returns all logged events (battles, NPC talks, lore "
            "discoveries, choices, exploration, combat actions)\n"
            "2. DreamGenerator.generate(events) weights events by type: battles=3, lore=2, "
            "choices=2, npc_talk=1, exploration=1, combat=1\n"
            "3. Top events by weight are selected (max 5 dream lines)\n"
            "4. Each event maps to a DREAM_TEMPLATES dict with 3 variations per type\n"
            "5. Templates use string formatting with event metadata (opponent name, NPC name, "
            "book title, area name)\n"
            "6. Polly adds a commentary line at the end\n"
            "7. HP is fully restored\n"
            "8. The entire dream sequence is exported as an SFT training pair, teaching the AI "
            "to synthesize daily experiences into narrative dream sequences."
        ),
        "metadata": _meta("system", tributary="dreams"),
    })

    return pairs


# ---------------------------------------------------------------------------
# Tributary 6: World exploration
# ---------------------------------------------------------------------------

def gen_world_pairs() -> list[dict]:
    """Generate SFT pairs from world regions and map system."""
    pairs = []

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tuxemon-spiralverse"))
        from tuxemon.spiralverse_world import WORLD_REGIONS
        for slug, region in WORLD_REGIONS.items():
            connections = ", ".join(region.connected_to)
            pairs.append({
                "id": f"sft-game-region-{slug}",
                "category": "world_exploration",
                "instruction": f"Describe the Spiralverse region '{region.name}' and its properties.",
                "response": (
                    f"Region: {region.name} (slug: {slug})\n"
                    f"Description: {region.description}\n"
                    f"Sacred Tongue affinity: {region.tongue}\n"
                    f"Level range: {region.level_range[0]}-{region.level_range[1]}\n"
                    f"Grid position: ({region.x}, {region.y}), size {region.w}x{region.h}\n"
                    f"Connected to: {connections}\n\n"
                    f"The tongue affinity means {region.tongue}-aligned players and monsters "
                    f"are stronger here. AI chat agents in this region use {region.tongue} "
                    f"tongue phrases for greetings."
                ),
                "metadata": _meta("system", tributary="world", region=slug),
            })

        # World map navigation pairs
        nav_pairs = [
            ("How do I get from Aether Clearing to the World Tree?",
             "From Aether Clearing (starting area, KO-aligned), follow this route:\n"
             "1. Aether Clearing -> Dawn Village (north, safe, level 1-3)\n"
             "2. Dawn Village -> Spirit Woods (east, RU-aligned, level 4-7)\n"
             "3. Spirit Woods -> Trade Road (south, AV-aligned, level 8-12)\n"
             "4. Trade Road -> World Tree Approach (east, level 15-20)\n"
             "5. World Tree Approach -> World Tree Grove (final area, level 20-25)\n\n"
             "Alternative dangerous route: Aether Clearing -> Mushroom Hollow -> Deep Earth -> "
             "World Tree Approach (shorter but higher level enemies)."),
            ("What regions are safe for a level 5 player?",
             "Safe regions for level 5:\n"
             "- Aether Clearing (level 1-3, KO) — starting area\n"
             "- Dawn Village (level 1-3, AV) — town hub\n"
             "- Sunset Beach (level 2-5, RU) — Dad's location\n"
             "- Mushroom Hollow (level 3-6, CA) — fungal maze\n\n"
             "Approaching danger zone:\n"
             "- Spirit Woods (level 4-7, RU) — manageable with good gear\n"
             "- Coral Depths (level 5-9, UM) — underwater, needs preparation\n\n"
             "Avoid: Volcanic Rim (8-13), Shadow Wastes (10-15), Thunder Peaks (12-18)."),
        ]
        for i, (q, a) in enumerate(nav_pairs):
            pairs.append({
                "id": f"sft-game-nav-{i+1:03d}",
                "category": "world_exploration",
                "instruction": q,
                "response": a,
                "metadata": _meta("system", tributary="world"),
            })

    except ImportError:
        print("  WARN: Could not import WORLD_REGIONS from game module", file=sys.stderr)

    return pairs


# ---------------------------------------------------------------------------
# Tributary 7: Game mechanics (jump, click-to-move, HUD)
# ---------------------------------------------------------------------------

def gen_mechanics_pairs() -> list[dict]:
    """Generate SFT pairs about core game mechanics."""
    pairs = []

    mechanics = [
        (
            "How does the Spiralverse click-to-move pathfinding work?",
            "The MouseClickMiddleware converts mouse clicks to NPC pathfinding commands. When "
            "the player clicks on the game screen: 1) The click position (screen pixels) is "
            "converted to tile coordinates using camera viewport offset and tile_size division. "
            "2) The target tile is clamped to map bounds. 3) character.pathfind((tile_x, tile_y)) "
            "is called, which uses A* pathfinding built into the Tuxemon engine. The middleware "
            "runs at priority 15 in the event pipeline, after jump (12) but before world commands (30)."
        ),
        (
            "How does Mario-style jumping work in Spiralverse?",
            "The JumpController implements single-jump physics (no double jump). Press SPACE "
            "to jump. Parameters: gravity=500 px/s², jump_power=-180 px/s (upward velocity), "
            "max_height=40px. The physics loop each frame: velocity += gravity * dt, then "
            "visual_y += velocity * dt. When visual_y returns to 0 (ground level), the jump "
            "ends and grounded=True. The visual_offset_y property is used by the renderer to "
            "offset the sprite vertically. This gives AI players a sense of vertical dimension."
        ),
        (
            "What does the Spiralverse side panel HUD show?",
            "The SidePanelHUD draws 6 buttons in the right-side letterbox (black bar) of the "
            "game screen. Buttons: INV (opens ItemMenu), MAP (opens NuPhoneMap), DIR (compass, "
            "placeholder), PAD (opens NuPhone), WAL (opens NuPhoneBanking), KEY (keys, "
            "placeholder). Each button is a 50x30px rectangle with hover highlighting. Clicking "
            "a button pushes the corresponding state onto the game state stack."
        ),
        (
            "How do Spiralverse game systems generate AI training data?",
            "Every game system exports SFT (Supervised Fine-Tuning) pairs:\n\n"
            "- Combat: attack/dodge/block decisions with spatial context -> combat strategy pairs\n"
            "- Story: ChoiceScript branches with effects -> narrative decision pairs\n"
            "- Chat: slash commands and AI dialogue -> social interaction pairs\n"
            "- Lore: book discoveries -> knowledge retrieval pairs\n"
            "- Dreams: daily event synthesis -> narrative generation pairs\n"
            "- Exploration: region traversal -> spatial reasoning pairs\n\n"
            "Combined, a single game session generates 50-200 SFT pairs. The daily_training_wave.py "
            "pipeline merges these with codebase and lore data for fine-tuning."
        ),
    ]

    for i, (q, a) in enumerate(mechanics):
        pairs.append({
            "id": f"sft-game-mech-{i+1:03d}",
            "category": "game_mechanics",
            "instruction": q,
            "response": a,
            "metadata": _meta("functions", tributary="mechanics"),
        })

    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Export Spiralverse game SFT training pairs")
    parser.add_argument(
        "--output", "-o",
        default="training-data/sft_spiralverse_game.jsonl",
        help="Output JSONL path (relative to repo root)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_path = repo_root / args.output

    print("=== Spiralverse Game -> SFT Export ===", file=sys.stderr)

    all_pairs: list[dict] = []

    # Generate from each tributary
    tributaries = [
        ("Combat telemetry", gen_combat_pairs),
        ("Story branching", gen_story_pairs),
        ("MMO chat", gen_chat_pairs),
        ("Lore books", gen_lore_pairs),
        ("Dream sequences", gen_dream_pairs),
        ("World exploration", gen_world_pairs),
        ("Game mechanics", gen_mechanics_pairs),
    ]

    for name, gen_fn in tributaries:
        pairs = gen_fn()
        print(f"  {name}: {len(pairs)} pairs", file=sys.stderr)
        all_pairs.extend(pairs)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_pairs:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_pairs)} SFT pairs -> {output_path}", file=sys.stderr)

    # Category breakdown
    cats: dict[str, int] = {}
    for r in all_pairs:
        cat = r["category"]
        cats[cat] = cats.get(cat, 0) + 1
    print("\nBy category:", file=sys.stderr)
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
