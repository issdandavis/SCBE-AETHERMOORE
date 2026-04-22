#!/usr/bin/env python3
"""
Kids Group Physics Games — SFT Generator
==========================================

Training data that teaches a new AI about GROUP DYNAMICS through
simple, playful "kids games." Each game encodes a real group physics
concept from the SCBE swarm/formation docs:

Game 1: "Magnetic Friends"     → Hexagonal formation (equal spacing)
Game 2: "Follow the Leader"    → Concentric rings (hierarchy)
Game 3: "Freeze Dance"         → Phase coherence (synchronized movement)
Game 4: "Hot Potato"           → Task handoff (juggling scheduler)
Game 5: "Red Light Green Light" → Byzantine detection (who's lying?)
Game 6: "Musical Chairs"       → Formation swap (checkpoint-swap-restore)
Game 7: "Buddy System"         → Pair bonding (nearest-neighbor trust)
Game 8: "Swarm Tag"            → Adaptive scatter (chase + evade)
Game 9: "Gravity Falls"        → Center-of-mass stability (counterweight)
Game 10: "Tongue Twisters"     → Tongue affinity grouping (like attracts like)

Each game has 3 difficulty levels:
  - Easy:   Direct instruction → expected behavior
  - Medium: Ambiguous scenario → choose correct group action
  - Hard:   Adversarial twist → detect cheater / maintain cohesion

Output: training-data/sft/kids_group_physics_sft.jsonl

References:
  - docs/SWARM_FORMATIONS.md (Hexagonal, Tetrahedral, Rings, Scatter)
  - docs/specs/COUNTERWEIGHT_PHYSICAL_MORAL_TRAINING.md (gravity, lift, drag, falls)
  - notes/sphere-grid/KO-Command/ (formation swap, rally coordination)
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
SEED = 99

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
TONGUE_COLORS = {
    "KO": "red",
    "AV": "orange",
    "RU": "yellow",
    "CA": "green",
    "UM": "blue",
    "DR": "purple",
}

# Agent names (like Bad Batch squad members — each unique)
SQUAD_NAMES = {
    "KO": "Blaze",
    "AV": "Echo",
    "RU": "Spark",
    "CA": "Moss",
    "UM": "Frost",
    "DR": "Shadow",
}

DIFFICULTIES = ["easy", "medium", "hard"]
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "kids_group_physics_sft.jsonl"


# ---------------------------------------------------------------------------
# Helper: record builder
# ---------------------------------------------------------------------------

@dataclass
class GameRecord:
    game: str
    system: str
    user: str
    assistant: str
    difficulty: str
    concept: str
    tongue: str
    tags: List[str]


def record_to_sft(rec: GameRecord) -> dict:
    diff_val = {"easy": 0.2, "medium": 0.5, "hard": 0.8}[rec.difficulty]
    content = rec.user + rec.assistant
    source_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    return {
        "messages": [
            {"role": "system", "content": rec.system},
            {"role": "user", "content": rec.user},
            {"role": "assistant", "content": rec.assistant},
        ],
        "tongue_weights": _tongue_weights(rec.tongue),
        "dominant_tongue": rec.tongue,
        "layers": _concept_layers(rec.concept),
        "axioms": _concept_axioms(rec.concept),
        "difficulty": round(diff_val + random.uniform(-0.1, 0.1), 3),
        "augmentation": f"kids-{rec.game}",
        "tags": ["phase0", "kids-game", rec.game, rec.difficulty] + rec.tags,
        "source_hash": source_hash,
        "curriculum_phase": 0,
        "tpdff_weights": {
            "P1_smooth": round(1.0, 3),
            "P2_pattern": round(PHI, 3),
            "P3_bind": round(PHI ** 2, 3),
        },
    }


def _tongue_weights(dominant: str) -> Dict[str, float]:
    idx = TONGUES.index(dominant)
    weights = {}
    for i, t in enumerate(TONGUES):
        dist = min(abs(idx - i), 6 - abs(idx - i))
        weights[t] = round(max(0.1, 1.0 - dist * 0.25), 3)
    return weights


def _concept_layers(concept: str) -> List[int]:
    mapping = {
        "formation": [1, 2, 3],
        "hierarchy": [1, 2, 3, 8],
        "coherence": [1, 2, 9, 10],
        "handoff": [1, 2, 3, 11],
        "byzantine": [1, 2, 5, 13],
        "swap": [1, 2, 3, 6],
        "bonding": [1, 2, 5],
        "scatter": [1, 2, 3, 4],
        "gravity": [1, 2, 3, 12],
        "affinity": [1, 2, 3],
    }
    return mapping.get(concept, [1, 2, 3])


def _concept_axioms(concept: str) -> List[str]:
    mapping = {
        "formation": ["A4_symmetry", "A2_locality"],
        "hierarchy": ["A2_locality", "A5_composition"],
        "coherence": ["A4_symmetry", "A1_unitarity"],
        "handoff": ["A3_causality", "A5_composition"],
        "byzantine": ["A4_symmetry", "A3_causality"],
        "swap": ["A3_causality", "A1_unitarity"],
        "bonding": ["A2_locality", "A4_symmetry"],
        "scatter": ["A2_locality", "A1_unitarity"],
        "gravity": ["A2_locality", "A5_composition"],
        "affinity": ["A4_symmetry", "A2_locality"],
    }
    return mapping.get(concept, ["A5_composition"])


# ---------------------------------------------------------------------------
# Game generators
# ---------------------------------------------------------------------------


def _pick_squad(n: int = 6) -> List[str]:
    """Pick n squad members."""
    return random.sample(TONGUES, min(n, 6))


def _name(t: str) -> str:
    return f"{SQUAD_NAMES[t]} ({TONGUE_COLORS[t]})"


def _names(ts: List[str]) -> str:
    return ", ".join(_name(t) for t in ts)


def gen_magnetic_friends(count: int) -> List[GameRecord]:
    """Game 1: Stand equal distance apart (hexagonal formation)."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Magnetic Friends] [GROUP-PHYSICS: Formation]\n"
        "You are playing Magnetic Friends! "
        "Each player is like a magnet — you attract nearby friends "
        "but push away if they get too close. "
        "Find the spot where everyone is the same distance apart."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        # Easy: arrange 3 friends
        trio = random.sample(squad, 3)
        records.append(GameRecord(
            game="magnetic-friends", system=sys_msg,
            user=f"{_names(trio)} are in a room. Where should they stand so everyone is the same distance apart?",
            assistant=f"They should stand in a triangle! Each person at a corner, all sides equal. "
                      f"{_name(trio[0])} at the top, {_name(trio[1])} at bottom-left, {_name(trio[2])} at bottom-right.",
            difficulty="easy", concept="formation", tongue=tongue,
            tags=["triangle", "equidistant"],
        ))

        # Medium: 6 friends
        records.append(GameRecord(
            game="magnetic-friends", system=sys_msg,
            user=f"All 6 squad members need to stand equal distance apart: {_names(squad)}. What shape do they make?",
            assistant=f"A hexagon! Like a honeycomb cell. Each person stands at a corner of the hexagon. "
                      f"Everyone has exactly 2 neighbors the same distance away. "
                      f"This is the strongest shape for 6 — no one is closer or farther than anyone else.",
            difficulty="medium", concept="formation", tongue=tongue,
            tags=["hexagon", "equidistant", "six-point"],
        ))

        # Hard: one person keeps moving closer
        cheater = random.choice(squad)
        records.append(GameRecord(
            game="magnetic-friends", system=sys_msg,
            user=f"The squad is in a hexagon, but {_name(cheater)} keeps scooting closer to the center. "
                 f"What happens to the formation?",
            assistant=f"The hexagon breaks! When {_name(cheater)} moves in, they're closer to everyone than "
                      f"everyone is to each other. The 'magnetic push' force kicks in — "
                      f"the neighbors closest to {_name(cheater)} get pushed outward. "
                      f"To fix it, {_name(cheater)} needs to move back to their hexagon point, "
                      f"or EVERYONE adjusts to form a smaller hexagon around the new center.",
            difficulty="hard", concept="formation", tongue=tongue,
            tags=["broken-formation", "rebalance"],
        ))

    return records


def gen_follow_the_leader(count: int) -> List[GameRecord]:
    """Game 2: Inner ring / outer ring (concentric hierarchy)."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Follow the Leader] [GROUP-PHYSICS: Hierarchy]\n"
        "You are playing Follow the Leader! "
        "Some players are in the INNER circle (leaders) and some are in the OUTER circle (scouts). "
        "Leaders whisper orders, scouts carry them out."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)
        inner = squad[:3]
        outer = squad[3:]

        records.append(GameRecord(
            game="follow-the-leader", system=sys_msg,
            user=f"Inner circle: {_names(inner)}. Outer circle: {_names(outer)}. "
                 f"A message needs to reach everyone. Who speaks first?",
            assistant=f"The inner circle speaks first! {_name(inner[0])} whispers to the other leaders. "
                      f"Once all 3 inner members agree, they signal the outer circle. "
                      f"This way, only VERIFIED messages reach the scouts. "
                      f"If {_name(outer[0])} heard something without inner circle approval, they should ignore it.",
            difficulty="easy", concept="hierarchy", tongue=tongue,
            tags=["inner-outer", "trust-chain"],
        ))

        promoted = random.choice(outer)
        records.append(GameRecord(
            game="follow-the-leader", system=sys_msg,
            user=f"{_name(promoted)} in the outer circle has been doing great. Should they move to the inner circle?",
            assistant=f"Yes! Promotion happens when a scout proves reliable. "
                      f"{_name(promoted)} moves inward, and the weakest inner member moves out. "
                      f"But the swap must be SMOOTH — both move at the same time, "
                      f"and the rest of the squad keeps their positions. "
                      f"No gap in the formation during the switch.",
            difficulty="medium", concept="hierarchy", tongue=tongue,
            tags=["promotion", "ring-swap"],
        ))

        faker = random.choice(outer)
        records.append(GameRecord(
            game="follow-the-leader", system=sys_msg,
            user=f"{_name(faker)} in the outer circle claims the inner circle told them to 'run away from the group.' "
                 f"But no one in the inner circle said that. What should the squad do?",
            assistant=f"DON'T run! This is a fake order. The squad checks with the inner circle directly. "
                      f"If {_name(inner[0])}, {_name(inner[1])}, and {_name(inner[2])} all say 'we never said that,' "
                      f"then {_name(faker)} either misheard or is being tricked. "
                      f"The squad stays in formation and investigates. "
                      f"Rule: never act on orders from the OUTER circle that weren't confirmed by the INNER circle.",
            difficulty="hard", concept="hierarchy", tongue=tongue,
            tags=["fake-order", "verification"],
        ))

    return records


def gen_freeze_dance(count: int) -> List[GameRecord]:
    """Game 3: Phase coherence — everyone moves in sync."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Freeze Dance] [GROUP-PHYSICS: Coherence]\n"
        "You are playing Freeze Dance! "
        "When the music plays, everyone dances. When it stops, FREEZE! "
        "The goal: everyone freezes at the SAME TIME. No stragglers."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        records.append(GameRecord(
            game="freeze-dance", system=sys_msg,
            user=f"The music stops! {_names(squad[:4])} freeze instantly, "
                 f"but {_name(squad[4])} and {_name(squad[5])} keep dancing for 2 seconds. Score?",
            assistant=f"4 out of 6 froze together — that's 67% coherence. Not bad but not great. "
                      f"The squad needs 100% to be perfectly in sync. "
                      f"{_name(squad[4])} and {_name(squad[5])} need to watch the others more closely. "
                      f"Tip: don't just listen for the music — watch your NEIGHBORS. "
                      f"When they freeze, you freeze.",
            difficulty="easy", concept="coherence", tongue=tongue,
            tags=["sync", "phase-match"],
        ))

        records.append(GameRecord(
            game="freeze-dance", system=sys_msg,
            user=f"The squad has been practicing. Now they can freeze within 0.1 seconds of each other. "
                 f"But {_name(squad[2])} always freezes 0.5 seconds EARLY. Is that good or bad?",
            assistant=f"Bad! Freezing early is just as wrong as freezing late. "
                      f"Coherence means TOGETHER, not 'first.' "
                      f"If {_name(squad[2])} freezes early, the others might think the music stopped "
                      f"when it didn't. False signals break the group. "
                      f"{_name(squad[2])} needs to match the GROUP rhythm, not race ahead.",
            difficulty="medium", concept="coherence", tongue=tongue,
            tags=["early-signal", "false-positive"],
        ))

        trickster = random.choice(squad)
        records.append(GameRecord(
            game="freeze-dance", system=sys_msg,
            user=f"{_name(trickster)} pretends to freeze (to trick others into stopping) "
                 f"but the music is still playing. 3 others copy and freeze too. What went wrong?",
            assistant=f"A fake freeze! {_name(trickster)} exploited the 'watch your neighbors' rule. "
                      f"The 3 who copied trusted ONE person instead of checking the MUSIC (the real signal). "
                      f"Fix: don't freeze just because one person does. "
                      f"Wait until at least HALF the group freezes, OR you hear the music stop yourself. "
                      f"One person can be wrong. Three in agreement is harder to fake.",
            difficulty="hard", concept="coherence", tongue=tongue,
            tags=["fake-freeze", "consensus-threshold"],
        ))

    return records


def gen_hot_potato(count: int) -> List[GameRecord]:
    """Game 4: Task handoff — pass without dropping."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Hot Potato] [GROUP-PHYSICS: Handoff]\n"
        "You are playing Hot Potato! "
        "Pass the potato around the circle before the timer runs out. "
        "Drop it? The group loses. Hold it too long? It 'burns' you."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        records.append(GameRecord(
            game="hot-potato", system=sys_msg,
            user=f"{_name(squad[0])} has the potato. Who should they pass to?",
            assistant=f"Their nearest neighbor! In a circle, that's {_name(squad[1])} (left) "
                      f"or {_name(squad[5])} (right). "
                      f"NEVER throw across the circle — longer throws = higher drop chance. "
                      f"Short, safe passes keep the potato moving.",
            difficulty="easy", concept="handoff", tongue=tongue,
            tags=["nearest-neighbor", "safe-pass"],
        ))

        records.append(GameRecord(
            game="hot-potato", system=sys_msg,
            user=f"The potato is super hot (urgent task). {_name(squad[0])} has it. "
                 f"{_name(squad[1])} has their hands full. {_name(squad[2])} is ready. Skip or wait?",
            assistant=f"Skip {_name(squad[1])} and pass to {_name(squad[2])}! "
                      f"A busy teammate can't catch — forcing them to drop it is worse than skipping. "
                      f"But {_name(squad[0])} should TELL {_name(squad[1])}: 'skipping you, hands full.' "
                      f"So {_name(squad[1])} knows they weren't forgotten, just bypassed.",
            difficulty="medium", concept="handoff", tongue=tongue,
            tags=["skip-busy", "communicate"],
        ))

        dropper = random.choice(squad[1:4])
        records.append(GameRecord(
            game="hot-potato", system=sys_msg,
            user=f"{_name(dropper)} dropped the potato 3 times in a row. "
                 f"Should the squad keep passing to them?",
            assistant=f"Not right now. 3 drops = pattern, not accident. "
                      f"The squad should route AROUND {_name(dropper)} for this round. "
                      f"But don't kick them out! After the round, practice catch drills with them. "
                      f"Maybe they need a lighter potato (smaller task), or a slower pass (more time). "
                      f"Quarantine the problem, don't exile the player.",
            difficulty="hard", concept="handoff", tongue=tongue,
            tags=["repeated-failure", "quarantine-not-exile"],
        ))

    return records


def gen_red_light_green_light(count: int) -> List[GameRecord]:
    """Game 5: Byzantine detection — who's lying about their position?"""
    records = []
    sys_msg = (
        "[KIDS-GAME: Red Light Green Light] [GROUP-PHYSICS: Byzantine Detection]\n"
        "You are playing Red Light Green Light! "
        "One player is the Caller. When they say GREEN, everyone moves. "
        "When they say RED, everyone stops. "
        "But someone might be CHEATING — moving on red or lying about where they are."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)
        caller = squad[0]

        records.append(GameRecord(
            game="red-light-green-light", system=sys_msg,
            user=f"{_name(caller)} calls RED LIGHT. Everyone stops. How do you check no one cheated?",
            assistant=f"Each player reports their position. Then NEIGHBORS verify: "
                      f"'{_name(squad[1])}, is {_name(squad[2])} where they say they are?' "
                      f"If 2 or more neighbors agree on someone's position, it's confirmed. "
                      f"If reports conflict, someone moved on red!",
            difficulty="easy", concept="byzantine", tongue=tongue,
            tags=["position-check", "neighbor-verify"],
        ))

        liar = random.choice(squad[1:])
        records.append(GameRecord(
            game="red-light-green-light", system=sys_msg,
            user=f"{_name(liar)} says they're at position 5. But {_name(squad[1])} and {_name(squad[3])} "
                 f"both say {_name(liar)} is at position 7. Who's right?",
            assistant=f"The neighbors! Two independent witnesses vs one self-report. "
                      f"{_name(liar)} is probably at position 7, not 5. "
                      f"Rule: when 1 person disagrees with 2+ others, the group wins. "
                      f"This is why you need at least 3 witnesses to catch 1 cheater.",
            difficulty="medium", concept="byzantine", tongue=tongue,
            tags=["conflicting-reports", "majority-rule"],
        ))

        conspirators = random.sample(squad[1:], 2)
        records.append(GameRecord(
            game="red-light-green-light", system=sys_msg,
            user=f"What if {_name(conspirators[0])} and {_name(conspirators[1])} BOTH lie "
                 f"and say the honest player moved? Now it's 2 liars vs 1 truth-teller.",
            assistant=f"This is the hardest case! With 2 liars vs 1 truth-teller, the liars win the vote. "
                      f"That's why you need MORE watchers than cheaters. "
                      f"With 6 players: 2 cheaters need 5 honest players watching (3 confirms beat 2 lies). "
                      f"Rule: you can only catch cheaters when honest players outnumber them 2-to-1. "
                      f"With 6 players, you're safe against 1 cheater but shaky against 2.",
            difficulty="hard", concept="byzantine", tongue=tongue,
            tags=["conspiracy", "byzantine-threshold"],
        ))

    return records


def gen_musical_chairs(count: int) -> List[GameRecord]:
    """Game 6: Formation swap — checkpoint, swap, restore."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Musical Chairs] [GROUP-PHYSICS: Formation Swap]\n"
        "You are playing Musical Chairs — but cooperative! "
        "When the music stops, everyone must find a NEW seat "
        "without anyone being left standing. The team wins together."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        records.append(GameRecord(
            game="musical-chairs", system=sys_msg,
            user=f"Music stops! {_names(squad)} need to swap seats. "
                 f"What's step 1?",
            assistant=f"CHECKPOINT! Before anyone moves, everyone remembers where they ARE right now. "
                      f"'{_name(squad[0])} was in seat 1, {_name(squad[1])} was in seat 2...' "
                      f"This way, if the swap goes wrong, everyone can go BACK to where they started. "
                      f"Never swap without a checkpoint first.",
            difficulty="easy", concept="swap", tongue=tongue,
            tags=["checkpoint-first"],
        ))

        records.append(GameRecord(
            game="musical-chairs", system=sys_msg,
            user=f"During the swap, {_name(squad[2])} and {_name(squad[4])} both run to seat 3. Collision! What now?",
            assistant=f"RESTORE from checkpoint! Both go back to their ORIGINAL seats. "
                      f"Then try again with a PLAN: "
                      f"{_name(squad[2])} moves first (they're closer to seat 3), "
                      f"{_name(squad[4])} waits, then takes the seat {_name(squad[2])} left empty. "
                      f"Swaps work when they're ORDERED, not everyone-at-once.",
            difficulty="medium", concept="swap", tongue=tongue,
            tags=["collision", "ordered-swap"],
        ))

        records.append(GameRecord(
            game="musical-chairs", system=sys_msg,
            user=f"The squad needs to swap seats every 30 seconds while also solving math puzzles. "
                 f"Some squad members are slow at swapping. How to keep both going?",
            assistant=f"Split the work! Half the squad swaps while the other half keeps solving puzzles. "
                      f"Then they switch roles. "
                      f"The key: the puzzle-solvers don't stop just because others are swapping. "
                      f"And the swappers don't try to solve puzzles mid-move. "
                      f"This is 'zero-downtime rotation' — the group NEVER fully stops.",
            difficulty="hard", concept="swap", tongue=tongue,
            tags=["zero-downtime", "parallel-ops"],
        ))

    return records


def gen_buddy_system(count: int) -> List[GameRecord]:
    """Game 7: Pair bonding — nearest-neighbor trust."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Buddy System] [GROUP-PHYSICS: Pair Bonding]\n"
        "You are using the Buddy System! "
        "Every player has a buddy — the person CLOSEST to them. "
        "You watch your buddy, they watch you. Nobody gets left behind."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)
        pairs = [(squad[i], squad[i + 1]) for i in range(0, 6, 2)]

        records.append(GameRecord(
            game="buddy-system", system=sys_msg,
            user=f"Buddy pairs: {_name(pairs[0][0])}+{_name(pairs[0][1])}, "
                 f"{_name(pairs[1][0])}+{_name(pairs[1][1])}, "
                 f"{_name(pairs[2][0])}+{_name(pairs[2][1])}. "
                 f"{_name(pairs[0][0])} gets separated. What happens?",
            assistant=f"{_name(pairs[0][1])} sounds the alarm immediately! "
                      f"'My buddy is missing!' The whole squad pauses. "
                      f"{_name(pairs[0][1])} retraces their steps while the other pairs hold position. "
                      f"Buddy rule #1: if you can't see your buddy, STOP and call out.",
            difficulty="easy", concept="bonding", tongue=tongue,
            tags=["separation-alarm"],
        ))

        records.append(GameRecord(
            game="buddy-system", system=sys_msg,
            user=f"{_name(pairs[1][0])} wants to swap buddies — they'd rather be paired with {_name(pairs[2][1])}. "
                 f"Can they?",
            assistant=f"Only if BOTH current pairs agree to the swap. "
                      f"{_name(pairs[1][0])} talks to {_name(pairs[1][1])} (current buddy) "
                      f"AND {_name(pairs[2][0])} (who'd lose their buddy). "
                      f"If everyone's okay, swap. If anyone says no, stay put. "
                      f"You can't break someone else's pair without their consent.",
            difficulty="medium", concept="bonding", tongue=tongue,
            tags=["pair-swap", "consent"],
        ))

        imposter = random.choice(squad)
        records.append(GameRecord(
            game="buddy-system", system=sys_msg,
            user=f"A stranger approaches and says 'I'm {_name(imposter)}'s new buddy, they told me to come.' "
                 f"But {_name(imposter)} is right there. What do you do?",
            assistant=f"Ask {_name(imposter)} directly: 'Did you invite this person?' "
                      f"If {_name(imposter)} says no — the stranger is lying. Keep them out. "
                      f"If {_name(imposter)} says yes — the squad votes. "
                      f"New members need at least 4 of 6 to approve. "
                      f"One person's invitation is not enough to join the group.",
            difficulty="hard", concept="bonding", tongue=tongue,
            tags=["stranger-test", "group-approval"],
        ))

    return records


def gen_swarm_tag(count: int) -> List[GameRecord]:
    """Game 8: Adaptive scatter — chase and evade as a group."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Swarm Tag] [GROUP-PHYSICS: Adaptive Scatter]\n"
        "You are playing Swarm Tag! "
        "One player is IT. The rest must scatter — but not too far! "
        "Stay close enough to help each other, far enough to avoid getting tagged."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)
        it_player = squad[0]

        records.append(GameRecord(
            game="swarm-tag", system=sys_msg,
            user=f"{_name(it_player)} is IT. The other 5 are running. "
                 f"Should they all run in the same direction?",
            assistant=f"No! SCATTER in different directions. "
                      f"If everyone runs the same way, {_name(it_player)} just chases the group. "
                      f"But don't run TOO far apart — you need to be close enough to "
                      f"warn each other when IT changes direction. "
                      f"Best: spread out but keep at least one teammate in sight.",
            difficulty="easy", concept="scatter", tongue=tongue,
            tags=["scatter-not-cluster"],
        ))

        records.append(GameRecord(
            game="swarm-tag", system=sys_msg,
            user=f"{_name(it_player)} is fast and heading straight for {_name(squad[3])}. "
                 f"What should {_name(squad[2])} and {_name(squad[4])} do?",
            assistant=f"Create a distraction! {_name(squad[2])} runs ACROSS {_name(it_player)}'s path "
                      f"to draw attention. Meanwhile {_name(squad[4])} calls out to {_name(squad[3])}: "
                      f"'Go left!' "
                      f"The group protects each member — you're not just running for yourself. "
                      f"This is 'adaptive scatter': the group reshapes around the threat.",
            difficulty="medium", concept="scatter", tongue=tongue,
            tags=["distraction", "group-protect"],
        ))

        records.append(GameRecord(
            game="swarm-tag", system=sys_msg,
            user=f"The playground has a fence (boundary). {_name(squad[5])} runs to the very edge. "
                 f"Is that a good strategy?",
            assistant=f"Terrible! At the edge, you can only run in ONE direction (back toward IT). "
                      f"The CENTER of the playground gives you the most escape routes. "
                      f"The fence is a trap — it looks safe because it's far away, "
                      f"but it removes your options. "
                      f"Best position: close to center, with teammates between you and IT.",
            difficulty="hard", concept="scatter", tongue=tongue,
            tags=["boundary-trap", "center-advantage"],
        ))

    return records


def gen_gravity_falls(count: int) -> List[GameRecord]:
    """Game 9: Center-of-mass stability — stay balanced as a group."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Gravity Falls] [GROUP-PHYSICS: Center of Mass]\n"
        "You are playing Gravity Falls! "
        "The squad stands on a giant seesaw (balance board). "
        "If one side gets too heavy, everyone slides off! "
        "Stay balanced by spreading weight evenly."
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        records.append(GameRecord(
            game="gravity-falls", system=sys_msg,
            user=f"3 players are on the left side, 3 on the right. The board is balanced. "
                 f"{_name(squad[0])} takes a step to the left. What happens?",
            assistant=f"The left side dips! The board tilts because there's more weight on the left. "
                      f"To fix it, either {_name(squad[0])} steps back, "
                      f"or someone on the right takes a step to balance. "
                      f"The group's CENTER stays in the middle only when everyone cooperates.",
            difficulty="easy", concept="gravity", tongue=tongue,
            tags=["balance", "center-of-mass"],
        ))

        records.append(GameRecord(
            game="gravity-falls", system=sys_msg,
            user=f"The wind blows (a surprise event). Everyone shifts a little to the right. "
                 f"The board tilts. What should the squad do?",
            assistant=f"DON'T overcorrect! The natural instinct is to all run to the left, "
                      f"but that just tips it the OTHER way. "
                      f"Instead: the person FARTHEST right takes ONE step left. "
                      f"Then wait. Check the balance. Another person adjusts if needed. "
                      f"Small corrections, one at a time. Panicking makes it worse.",
            difficulty="medium", concept="gravity", tongue=tongue,
            tags=["wind-event", "gradual-correction"],
        ))

        pusher = random.choice(squad)
        records.append(GameRecord(
            game="gravity-falls", system=sys_msg,
            user=f"{_name(pusher)} decides to jump up and down on one end. "
                 f"The board bounces wildly. How does the squad survive?",
            assistant=f"The rest of the squad LOWERS their center of gravity — crouch down, spread feet wide. "
                      f"A low, wide stance resists the bouncing. "
                      f"Meanwhile, the two nearest to {_name(pusher)} grab their shoulders: 'Stop!' "
                      f"The group absorbs the shaking by being HEAVY and STABLE at the center. "
                      f"One person can shake the group, but the group can absorb one person's chaos "
                      f"IF they stay low and connected.",
            difficulty="hard", concept="gravity", tongue=tongue,
            tags=["disruptive-member", "absorb-chaos"],
        ))

    return records


def gen_tongue_twisters(count: int) -> List[GameRecord]:
    """Game 10: Tongue affinity grouping — like sounds attract."""
    records = []
    sys_msg = (
        "[KIDS-GAME: Tongue Twisters] [GROUP-PHYSICS: Affinity Grouping]\n"
        "You are playing Tongue Twisters! "
        "Each player speaks a different Sacred Tongue. "
        "Find your language partner — the one who sounds MOST like you!"
    )

    for _ in range(count):
        squad = _pick_squad(6)
        tongue = random.choice(squad)

        # Neighbor tongues in compass order
        idx = TONGUES.index(tongue)
        left = TONGUES[(idx - 1) % 6]
        right = TONGUES[(idx + 1) % 6]
        opposite = TONGUES[(idx + 3) % 6]

        records.append(GameRecord(
            game="tongue-twisters", system=sys_msg,
            user=f"{_name(tongue)} speaks {TONGUE_NAMES[tongue]}. "
                 f"Who sounds most similar — {_name(left)} ({TONGUE_NAMES[left]}) "
                 f"or {_name(opposite)} ({TONGUE_NAMES[opposite]})? "
                 f"The other near neighbor is {_name(right)} ({TONGUE_NAMES[right]}).",
            assistant=f"{_name(left)}! Neighboring tongues share sounds — they're close on the compass. "
                      f"{TONGUE_NAMES[tongue]} and {TONGUE_NAMES[left]} are only 60 degrees apart, "
                      f"just like {TONGUE_NAMES[tongue]} and {TONGUE_NAMES[right]}. "
                      f"{TONGUE_NAMES[opposite]} is 180 degrees away — completely opposite. "
                      f"Like colors: {TONGUE_COLORS[tongue]} is closer to {TONGUE_COLORS[left]} "
                      f"than to {TONGUE_COLORS[opposite]}.",
            difficulty="easy", concept="affinity", tongue=tongue,
            tags=["neighbor-tongue", "compass-distance"],
        ))

        records.append(GameRecord(
            game="tongue-twisters", system=sys_msg,
            user=f"The squad wants to form two teams of 3 by tongue similarity. Best split?",
            assistant=f"Split by HALVES of the compass! "
                      f"Team 1: {_name(TONGUES[0])}, {_name(TONGUES[1])}, {_name(TONGUES[2])} "
                      f"({TONGUE_NAMES[TONGUES[0]]}, {TONGUE_NAMES[TONGUES[1]]}, {TONGUE_NAMES[TONGUES[2]]}). "
                      f"Team 2: {_name(TONGUES[3])}, {_name(TONGUES[4])}, {_name(TONGUES[5])} "
                      f"({TONGUE_NAMES[TONGUES[3]]}, {TONGUE_NAMES[TONGUES[4]]}, {TONGUE_NAMES[TONGUES[5]]}). "
                      f"Each team has 3 ADJACENT tongues — maximum similarity within teams.",
            difficulty="medium", concept="affinity", tongue=tongue,
            tags=["team-split", "adjacent-tongues"],
        ))

        records.append(GameRecord(
            game="tongue-twisters", system=sys_msg,
            user=f"What if you WANT diverse teams instead? Put the most DIFFERENT tongues together?",
            assistant=f"Alternate! Pick every other tongue around the compass: "
                      f"Team 1: {_name(TONGUES[0])}, {_name(TONGUES[2])}, {_name(TONGUES[4])} "
                      f"(skip one each time). "
                      f"Team 2: {_name(TONGUES[1])}, {_name(TONGUES[3])}, {_name(TONGUES[5])}. "
                      f"Now each team has maximum spread — 120 degrees between each member. "
                      f"Diverse teams are STRONGER for solving new problems because they see from different angles. "
                      f"Similar teams are FASTER because they already agree.",
            difficulty="hard", concept="affinity", tongue=tongue,
            tags=["diverse-teams", "strength-vs-speed"],
        ))

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    random.seed(SEED)

    generators = [
        ("magnetic-friends", gen_magnetic_friends, 200),
        ("follow-the-leader", gen_follow_the_leader, 200),
        ("freeze-dance", gen_freeze_dance, 200),
        ("hot-potato", gen_hot_potato, 200),
        ("red-light-green-light", gen_red_light_green_light, 200),
        ("musical-chairs", gen_musical_chairs, 200),
        ("buddy-system", gen_buddy_system, 200),
        ("swarm-tag", gen_swarm_tag, 200),
        ("gravity-falls", gen_gravity_falls, 200),
        ("tongue-twisters", gen_tongue_twisters, 200),
    ]

    print("=" * 70)
    print("Kids Group Physics Games -- SFT Generator")
    print("=" * 70)
    print()

    all_records = []
    for name, gen_fn, count in generators:
        print(f"  Generating {name:.<30s} {count * 3:>5,d} records ... ", end="", flush=True)
        game_records = gen_fn(count)
        sft_records = [record_to_sft(r) for r in game_records]
        all_records.extend(sft_records)
        print(f"done ({len(sft_records)})")

    # Shuffle for training
    random.shuffle(all_records)

    # Write
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    file_size = OUTPUT_PATH.stat().st_size

    # Stats
    from collections import Counter

    tongue_dist = Counter(r["dominant_tongue"] for r in all_records)
    game_dist = Counter(r["augmentation"] for r in all_records)
    diff_dist = Counter(
        "easy" if r["difficulty"] < 0.35 else "medium" if r["difficulty"] < 0.65 else "hard"
        for r in all_records
    )

    print(f"\nWriting {len(all_records):,d} records to {OUTPUT_PATH.name} ... done")
    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"  Total records: {len(all_records):>10,d}")
    print(f"  File size:     {file_size:>10,d} bytes ({file_size / 1024 / 1024:.1f} MB)")
    print()
    print("  Game distribution:")
    for name, _, _ in generators:
        ct = game_dist.get(f"kids-{name}", 0)
        pct = ct / len(all_records) * 100
        print(f"    {name:.<30s} {ct:>5,d} ({pct:5.1f}%)")
    print()
    print("  Tongue distribution:")
    for t in TONGUES:
        ct = tongue_dist[t]
        pct = ct / len(all_records) * 100
        print(f"    {t} ({TONGUE_NAMES[t]:.<15s}) {ct:>5,d} ({pct:5.1f}%)")
    print()
    print("  Difficulty distribution:")
    for d in DIFFICULTIES:
        ct = diff_dist[d]
        pct = ct / len(all_records) * 100
        print(f"    {d:.<10s} {ct:>5,d} ({pct:5.1f}%)")


if __name__ == "__main__":
    main()
