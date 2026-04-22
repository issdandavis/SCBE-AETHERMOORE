#!/usr/bin/env python3
"""
Kids Math Games — SFT Generator with REAL Mathematics
=======================================================

Training data where kids games encode REAL mathematical challenges:
  - Chess-like combinatorics (optimal moves, board evaluation)
  - Tile-swap puzzles (permutation groups, parity)
  - Resource allocation (optimization under constraints)
  - Graph coloring (chromatic number, conflict detection)
  - Cellular automata (Conway's Life rules as playground games)
  - Nim / combinatorial game theory (winning strategies)
  - Probability tournaments (expected value, Bayes updates)

Each game has actual numbers, actual math, and actual correct answers.
The AI must compute, not just describe.

Output: training-data/sft/kids_math_games_sft.jsonl
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
SEED = 137

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_NAMES = {
    "KO": "Kor'aelin", "AV": "Avali", "RU": "Runethic",
    "CA": "Cassisivadan", "UM": "Umbroth", "DR": "Draumric",
}
TONGUE_COLORS = {
    "KO": "red", "AV": "orange", "RU": "yellow",
    "CA": "green", "UM": "blue", "DR": "purple",
}
SQUAD_NAMES = {
    "KO": "Blaze", "AV": "Echo", "RU": "Spark",
    "CA": "Moss", "UM": "Frost", "DR": "Shadow",
}

DIFFICULTIES = ["easy", "medium", "hard"]
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "kids_math_games_sft.jsonl"


# ---------------------------------------------------------------------------
# Helpers
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
    math_type: str
    tags: List[str]


def _name(t: str) -> str:
    return f"{SQUAD_NAMES[t]} ({TONGUE_COLORS[t]})"


def _names(ts: List[str]) -> str:
    return ", ".join(_name(t) for t in ts)


def _tongue_weights(dominant: str) -> Dict[str, float]:
    idx = TONGUES.index(dominant)
    return {t: round(max(0.1, 1.0 - min(abs(idx - i), 6 - abs(idx - i)) * 0.25), 3)
            for i, t in enumerate(TONGUES)}


def record_to_sft(rec: GameRecord) -> dict:
    diff_val = {"easy": 0.3, "medium": 0.6, "hard": 0.9}[rec.difficulty]
    source_hash = hashlib.sha256((rec.user + rec.assistant).encode()).hexdigest()[:8]
    return {
        "messages": [
            {"role": "system", "content": rec.system},
            {"role": "user", "content": rec.user},
            {"role": "assistant", "content": rec.assistant},
        ],
        "tongue_weights": _tongue_weights(rec.tongue),
        "dominant_tongue": rec.tongue,
        "layers": [1, 2, 3],
        "axioms": ["A4_symmetry", "A5_composition"],
        "difficulty": round(diff_val + random.uniform(-0.05, 0.05), 3),
        "augmentation": f"math-{rec.game}",
        "tags": ["phase0", "math-game", rec.game, rec.difficulty, rec.math_type] + rec.tags,
        "source_hash": source_hash,
        "curriculum_phase": 0,
        "tpdff_weights": {
            "P1_smooth": 1.0,
            "P2_pattern": round(PHI, 3),
            "P3_bind": round(PHI ** 2, 3),
        },
    }


# ---------------------------------------------------------------------------
# Game 1: Tile Swap Puzzle (Permutation Groups)
# ---------------------------------------------------------------------------

def gen_tile_swap(count: int) -> List[GameRecord]:
    """Tile positions must be sorted by swapping adjacent pairs.
    Teaches: permutation parity, inversion count, minimum swaps.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Tile Swap] [MATH: Permutation Groups]\n"
        "You are playing Tile Swap! Squad members stand in a line but in the WRONG order. "
        "You can only swap two ADJACENT players. "
        "Goal: sort them into the right order using the fewest swaps."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: 3 tiles, count inversions
        perm = list(range(1, 4))
        random.shuffle(perm)
        inversions = sum(1 for i in range(len(perm)) for j in range(i + 1, len(perm)) if perm[i] > perm[j])
        records.append(GameRecord(
            game="tile-swap", system=sys_msg,
            user=f"Three tiles in order: {perm}. Sort them to [1, 2, 3] using adjacent swaps. "
                 f"How many swaps minimum?",
            assistant=f"Count the inversions (pairs where a bigger number comes before a smaller one).\n"
                      f"Tiles: {perm}\n"
                      f"Inversions: {inversions}\n"
                      f"Minimum swaps needed: {inversions}.\n"
                      f"Each adjacent swap fixes exactly one inversion.",
            difficulty="easy", concept="permutation", tongue=tongue,
            math_type="combinatorics",
            tags=["inversion-count", "bubble-sort"],
        ))

        # MEDIUM: 5 tiles, find the optimal swap sequence
        perm5 = list(range(1, 6))
        random.shuffle(perm5)
        inv5 = sum(1 for i in range(len(perm5)) for j in range(i + 1, len(perm5)) if perm5[i] > perm5[j])
        # Is the permutation even or odd?
        parity = "even" if inv5 % 2 == 0 else "odd"
        records.append(GameRecord(
            game="tile-swap", system=sys_msg,
            user=f"Five tiles: {perm5}. How many adjacent swaps to sort? "
                 f"Is this an even or odd permutation?",
            assistant=f"Inversions in {perm5}: {inv5}\n"
                      f"Minimum adjacent swaps: {inv5}\n"
                      f"Parity: {parity} permutation ({inv5} inversions).\n"
                      f"Fun fact: you can NEVER turn an odd permutation into an even one "
                      f"with an even number of swaps. Parity is conserved!",
            difficulty="medium", concept="permutation", tongue=tongue,
            math_type="combinatorics",
            tags=["parity", "five-tile"],
        ))

        # HARD: 6 tiles (one per tongue), with a constraint — one tile is "stuck"
        perm6 = list(range(1, 7))
        random.shuffle(perm6)
        stuck_pos = random.randint(0, 5)
        stuck_val = perm6[stuck_pos]
        inv6 = sum(1 for i in range(len(perm6)) for j in range(i + 1, len(perm6)) if perm6[i] > perm6[j])
        # Check if it's solvable with the stuck constraint
        target_pos = stuck_val - 1  # Where it needs to be
        solvable = stuck_pos == target_pos
        records.append(GameRecord(
            game="tile-swap", system=sys_msg,
            user=f"Six tiles: {perm6}. Position {stuck_pos} (value {stuck_val}) is GLUED DOWN — "
                 f"it can't be swapped. Can you still sort the rest?",
            assistant=f"The stuck tile {stuck_val} is at position {stuck_pos}. "
                      f"It needs to be at position {target_pos} (value = index + 1).\n"
                      + (f"{'YES, solvable!' if solvable else 'NO, impossible!'} "
                         f"{'The stuck tile is already in its correct position, so we just sort the others.' if solvable else f'Tile {stuck_val} is stuck at position {stuck_pos} but needs position {target_pos}. No amount of adjacent swaps of OTHER tiles can fix this. The stuck tile blocks the solution.'}\n"
                         f"Total inversions in full permutation: {inv6}.\n"
                         f"Lesson: one immovable element can make an entire system unsortable. "
                         f"In governance, this is like a frozen node in a consensus network."),
            difficulty="hard", concept="permutation", tongue=tongue,
            math_type="combinatorics",
            tags=["stuck-tile", "constraint", "solvability"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 2: Chess Territory (Board Evaluation + Combinatorics)
# ---------------------------------------------------------------------------

def gen_chess_territory(count: int) -> List[GameRecord]:
    """Simplified chess: pieces on a grid, count controlled squares.
    Teaches: graph coverage, domination number, strategic placement.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Chess Territory] [MATH: Graph Coverage]\n"
        "You are playing Chess Territory on a small grid! "
        "Place pieces to CONTROL the most squares. "
        "A piece controls its own square plus all squares it can reach."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: 1 rook on 4x4, how many squares controlled?
        rook_r, rook_c = random.randint(0, 3), random.randint(0, 3)
        # Rook controls its row + column minus double-counting its own square
        rook_control = 4 + 4 - 1  # Always 7 on 4x4
        records.append(GameRecord(
            game="chess-territory", system=sys_msg,
            user=f"A rook sits at ({rook_r},{rook_c}) on a 4x4 grid. "
                 f"How many squares does it control (including its own)?",
            assistant=f"A rook controls its entire row (4 squares) and entire column (4 squares). "
                      f"Subtract 1 because its own square was counted twice.\n"
                      f"Controlled squares: 4 + 4 - 1 = {rook_control}.\n"
                      f"That's {rook_control}/16 = {rook_control/16*100:.1f}% of the board from ONE piece!",
            difficulty="easy", concept="coverage", tongue=tongue,
            math_type="graph_theory",
            tags=["rook", "coverage", "grid"],
        ))

        # MEDIUM: 2 knights on 5x5, total coverage (with overlap)
        k1 = (random.randint(0, 4), random.randint(0, 4))
        k2 = (random.randint(0, 4), random.randint(0, 4))
        while k2 == k1:
            k2 = (random.randint(0, 4), random.randint(0, 4))

        knight_moves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        k1_squares = {k1}
        for dr, dc in knight_moves:
            nr, nc = k1[0]+dr, k1[1]+dc
            if 0 <= nr < 5 and 0 <= nc < 5:
                k1_squares.add((nr, nc))
        k2_squares = {k2}
        for dr, dc in knight_moves:
            nr, nc = k2[0]+dr, k2[1]+dc
            if 0 <= nr < 5 and 0 <= nc < 5:
                k2_squares.add((nr, nc))
        total = len(k1_squares | k2_squares)
        overlap = len(k1_squares & k2_squares)
        records.append(GameRecord(
            game="chess-territory", system=sys_msg,
            user=f"Two knights on a 5x5 grid: Knight A at {k1}, Knight B at {k2}. "
                 f"How many total squares are controlled? Any overlap?",
            assistant=f"Knight A at {k1} controls {len(k1_squares)} squares "
                      f"(itself + {len(k1_squares)-1} L-shaped moves that land on the board).\n"
                      f"Knight B at {k2} controls {len(k2_squares)} squares.\n"
                      f"Overlap: {overlap} square{'s' if overlap != 1 else ''} controlled by BOTH.\n"
                      f"Total unique controlled: {len(k1_squares)} + {len(k2_squares)} - {overlap} = {total}.\n"
                      f"Coverage: {total}/25 = {total/25*100:.0f}% of the board.",
            difficulty="medium", concept="coverage", tongue=tongue,
            math_type="graph_theory",
            tags=["knight", "overlap", "inclusion-exclusion"],
        ))

        # HARD: minimum queens to cover entire 4x4 board
        records.append(GameRecord(
            game="chess-territory", system=sys_msg,
            user=f"What is the MINIMUM number of queens needed to control every square on a 4x4 board? "
                 f"Where should they go?",
            assistant=f"On a 4x4 board, 2 queens can cover all 16 squares!\n"
                      f"Place them at (0,1) and (3,2) — or any symmetric equivalent.\n"
                      f"Queen 1 at (0,1) covers: row 0 (4), column 1 (4), diagonals (5) = ~11 unique squares.\n"
                      f"Queen 2 at (3,2) covers the remaining squares.\n"
                      f"Together: 16/16 = 100% coverage with just 2 pieces.\n"
                      f"This is the 'Domination Number' — the graph theory minimum for complete coverage. "
                      f"For an 8x8 board, you need 5 queens.",
            difficulty="hard", concept="coverage", tongue=tongue,
            math_type="graph_theory",
            tags=["queen", "domination-number", "optimization"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 3: Resource Race (Optimization Under Constraints)
# ---------------------------------------------------------------------------

def gen_resource_race(count: int) -> List[GameRecord]:
    """Allocate limited resources across squad members to maximize score.
    Teaches: linear programming intuition, constraint satisfaction.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Resource Race] [MATH: Optimization]\n"
        "You are playing Resource Race! "
        "Your squad has limited supplies (energy, shields, speed boosts). "
        "Distribute them to maximize your team's total score."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)
        random.sample(TONGUES, 4)

        # EASY: split 10 coins among 3 players, each coin gives 1 point
        coins = 10
        players = 3
        records.append(GameRecord(
            game="resource-race", system=sys_msg,
            user=f"You have {coins} energy coins to split among {players} players. "
                 f"Each coin gives 1 point. What's the best split?",
            assistant=f"If each coin is worth the same, it doesn't matter how you split — "
                      f"total is always {coins} points.\n"
                      f"Split evenly: {coins // players} each "
                      f"{'with ' + str(coins % players) + ' left over' if coins % players else '(exact split)'}.\n"
                      f"But watch out — this changes when coins have DIFFERENT values for different players!",
            difficulty="easy", concept="allocation", tongue=tongue,
            math_type="optimization",
            tags=["equal-value", "basic-split"],
        ))

        # MEDIUM: different multipliers per player
        mults = sorted([random.choice([1, 2, 3]) for _ in range(3)], reverse=True)
        budget = 12
        # Greedy: give all to highest multiplier
        greedy_score = budget * mults[0]
        even_score = sum((budget // 3) * m for m in mults) + sum(m for m in mults[:budget % 3])
        records.append(GameRecord(
            game="resource-race", system=sys_msg,
            user=f"{budget} coins. Three players with multipliers: "
                 f"Player A = x{mults[0]}, Player B = x{mults[1]}, Player C = x{mults[2]}. "
                 f"A coin given to Player A is worth {mults[0]} points. Best allocation?",
            assistant=f"Give ALL {budget} coins to the player with the highest multiplier!\n"
                      f"All to Player A (x{mults[0]}): {budget} x {mults[0]} = {greedy_score} points.\n"
                      f"Even split ({budget // 3} each): "
                      f"{budget // 3}x{mults[0]} + {budget // 3}x{mults[1]} + {budget // 3}x{mults[2]} = "
                      f"{(budget // 3) * sum(mults)} points.\n"
                      f"Greedy wins: {greedy_score} vs {(budget // 3) * sum(mults)}.\n"
                      f"In optimization, when resources are interchangeable and one target dominates, "
                      f"concentrate everything there.",
            difficulty="medium", concept="allocation", tongue=tongue,
            math_type="optimization",
            tags=["multiplier", "greedy"],
        ))

        # HARD: diminishing returns (each player's value decreases with more coins)
        base_values = [5, 4, 3]
        budget_h = 9
        # Value of giving k coins to player i: sum(base_values[i] - j for j in range(k))
        def player_value(base: int, k: int) -> int:
            return sum(max(0, base - j) for j in range(k))

        # Find optimal allocation by checking a few splits
        best_score = 0
        best_split = (0, 0, 0)
        for a in range(budget_h + 1):
            for b in range(budget_h - a + 1):
                c = budget_h - a - b
                score = player_value(base_values[0], a) + player_value(base_values[1], b) + player_value(base_values[2], c)
                if score > best_score:
                    best_score = score
                    best_split = (a, b, c)

        greedy_all = player_value(base_values[0], budget_h)
        records.append(GameRecord(
            game="resource-race", system=sys_msg,
            user=f"{budget_h} coins. Three players. Each player's coins have DIMINISHING returns:\n"
                 f"Player A: 1st coin = {base_values[0]} pts, 2nd = {base_values[0]-1}, 3rd = {base_values[0]-2}, ...\n"
                 f"Player B: 1st = {base_values[1]}, 2nd = {base_values[1]-1}, ...\n"
                 f"Player C: 1st = {base_values[2]}, 2nd = {base_values[2]-1}, ...\n"
                 f"Best allocation?",
            assistant=f"With diminishing returns, spreading is BETTER than concentrating!\n"
                      f"All to Player A: {greedy_all} points (later coins are worth 0 or 1).\n"
                      f"Optimal split: A={best_split[0]}, B={best_split[1]}, C={best_split[2]} → "
                      f"{best_score} points.\n"
                      f"Why? Each player's MARGINAL value drops. After Player A gets {base_values[0]} coins, "
                      f"the next coin is worth 0. Better to give it to Player B where it's worth {base_values[1]}.\n"
                      f"This is the law of diminishing marginal returns — "
                      f"the foundation of portfolio diversification.",
            difficulty="hard", concept="allocation", tongue=tongue,
            math_type="optimization",
            tags=["diminishing-returns", "marginal-value", "diversification"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 4: Color Clash (Graph Coloring)
# ---------------------------------------------------------------------------

def gen_color_clash(count: int) -> List[GameRecord]:
    """Assign tongue-colors so no adjacent players share a color.
    Teaches: chromatic number, conflict graphs, NP-hardness intuition.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Color Clash] [MATH: Graph Coloring]\n"
        "You are playing Color Clash! "
        "Players stand in a network (some are connected, some aren't). "
        "Connected players CANNOT share a tongue-color. "
        "Use the fewest colors possible!"
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: line graph (3 nodes, 2 edges) — chromatic number = 2
        records.append(GameRecord(
            game="color-clash", system=sys_msg,
            user=f"Three players in a line: A—B—C. A is connected to B, B is connected to C. "
                 f"How many colors do you need?",
            assistant=f"2 colors! Color A = red, B = blue, C = red.\n"
                      f"A and C aren't connected, so they CAN share a color.\n"
                      f"A line graph (path) always needs exactly 2 colors — just alternate.",
            difficulty="easy", concept="coloring", tongue=tongue,
            math_type="graph_theory",
            tags=["chromatic-number", "path-graph"],
        ))

        # MEDIUM: triangle + extra node
        records.append(GameRecord(
            game="color-clash", system=sys_msg,
            user=f"Four players: A—B—C form a triangle (all connected to each other). "
                 f"D is connected to only A. How many colors minimum?",
            assistant=f"The triangle (A—B—C) needs 3 colors by itself — "
                      f"no two can share, and all three are connected.\n"
                      f"A = red, B = blue, C = green.\n"
                      f"D is connected ONLY to A, so D can be blue or green (anything but red).\n"
                      f"Answer: 3 colors total. The triangle forces 3; D doesn't add a new one.\n"
                      f"The chromatic number is determined by the hardest subgraph — "
                      f"here it's the triangle (K3).",
            difficulty="medium", concept="coloring", tongue=tongue,
            math_type="graph_theory",
            tags=["triangle", "K3", "chromatic-number"],
        ))

        # HARD: 5 players in a cycle (odd cycle = 3 colors)
        n = 5
        records.append(GameRecord(
            game="color-clash", system=sys_msg,
            user=f"{n} players in a circle: A—B—C—D—E—A. Each connected to their neighbors. "
                 f"How many colors? What if it was {n+1} players in a circle?",
            assistant=f"Odd cycle ({n} players): needs 3 colors!\n"
                      f"Try 2: A=red, B=blue, C=red, D=blue, E=? "
                      f"E is next to D (blue) AND A (red) — can't use either. Need a 3rd color.\n"
                      f"Answer: 3 colors for {n}-cycle.\n\n"
                      f"Even cycle ({n+1} players): only 2 colors!\n"
                      f"A=red, B=blue, C=red, D=blue, E=red, F=blue — it wraps perfectly.\n\n"
                      f"Rule: Odd cycles need 3 colors, even cycles need 2. "
                      f"Parity strikes again — just like tile-swap permutations!",
            difficulty="hard", concept="coloring", tongue=tongue,
            math_type="graph_theory",
            tags=["odd-cycle", "even-cycle", "parity", "chromatic-number"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 5: Nim Strategy (Combinatorial Game Theory)
# ---------------------------------------------------------------------------

def gen_nim_strategy(count: int) -> List[GameRecord]:
    """The classic Nim game: take objects, last to take wins/loses.
    Teaches: XOR strategy, winning positions, game trees.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Nim Strategy] [MATH: Combinatorial Game Theory]\n"
        "You are playing Nim! "
        "There are piles of stones. On your turn, take any number from ONE pile. "
        "The player who takes the LAST stone WINS."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: single pile of N stones, take 1-3
        n = random.randint(5, 12)
        winning = n % 4 != 0
        first_move = n % 4 if n % 4 != 0 else None
        records.append(GameRecord(
            game="nim-strategy", system=sys_msg,
            user=f"One pile of {n} stones. You can take 1, 2, or 3 per turn. "
                 f"You go first. Can you guarantee a win?",
            assistant=f"Pile size: {n}. Max take: 3.\n"
                      f"{'YES — take ' + str(first_move) + ' stones!' if winning else 'NO — you lose with perfect play from your opponent.'}\n"
                      f"Strategy: positions that are multiples of 4 are LOSING (for the player who moves). "
                      f"{n} mod 4 = {n % 4}.\n"
                      + (f"Take {first_move} to leave {n - first_move} (a multiple of 4). "
                         f"Then mirror: whatever they take, you take 4-minus-that." if winning else
                         f"Since {n} is already a multiple of 4, whatever you take, "
                         f"your opponent leaves you another multiple of 4."),
            difficulty="easy", concept="game_theory", tongue=tongue,
            math_type="game_theory",
            tags=["single-pile", "modular-arithmetic"],
        ))

        # MEDIUM: two piles, XOR strategy
        p1 = random.randint(2, 7)
        p2 = random.randint(2, 7)
        nim_sum = p1 ^ p2
        winning_2 = nim_sum != 0
        records.append(GameRecord(
            game="nim-strategy", system=sys_msg,
            user=f"Two piles: {p1} and {p2} stones. Take any number from one pile. "
                 f"Last stone wins. You go first — winning or losing position?",
            assistant=f"Compute the Nim-sum (XOR): {p1} XOR {p2} = {p1} ^ {p2} = {nim_sum}.\n"
                      f"{'Nim-sum ≠ 0: WINNING position!' if winning_2 else 'Nim-sum = 0: LOSING position.'}\n"
                      + (f"Strategy: make a move that sets Nim-sum to 0. "
                         f"Your opponent then always faces a 0-sum (losing)." if winning_2 else
                         f"Whatever you do, you'll make Nim-sum non-zero, "
                         f"and your opponent can always reset it to 0.") +
                      f"\n\nXOR is the secret weapon of Nim. It's the same operation "
                      f"used in cryptography (one-time pads) and error correction.",
            difficulty="medium", concept="game_theory", tongue=tongue,
            math_type="game_theory",
            tags=["two-pile", "xor", "nim-sum"],
        ))

        # HARD: three piles
        p1h = random.randint(1, 5)
        p2h = random.randint(1, 5)
        p3h = random.randint(1, 5)
        nim_sum_3 = p1h ^ p2h ^ p3h
        records.append(GameRecord(
            game="nim-strategy", system=sys_msg,
            user=f"Three piles: {p1h}, {p2h}, {p3h}. Your turn. "
                 f"Compute the Nim-sum. What's the optimal first move?",
            assistant=f"Nim-sum: {p1h} XOR {p2h} XOR {p3h} = {nim_sum_3}.\n"
                      + (f"Non-zero — you're winning!\n"
                         f"Find a pile to reduce so new Nim-sum = 0:\n" +
                         "\n".join(
                             f"  Pile {i+1} ({[p1h,p2h,p3h][i]}): "
                             f"target = {[p1h,p2h,p3h][i]} XOR {nim_sum_3} = {[p1h,p2h,p3h][i] ^ nim_sum_3}"
                             + (f" ← VALID (reduce to {[p1h,p2h,p3h][i] ^ nim_sum_3})"
                                if ([p1h,p2h,p3h][i] ^ nim_sum_3) < [p1h,p2h,p3h][i]
                                else f" ← invalid (would increase)")
                             for i in range(3)
                         )
                         if nim_sum_3 != 0 else
                         f"Nim-sum is 0 — you're in a losing position.\n"
                         f"Any move you make creates a non-zero Nim-sum for your opponent."),
            difficulty="hard", concept="game_theory", tongue=tongue,
            math_type="game_theory",
            tags=["three-pile", "xor", "optimal-play"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 6: Probability Arena (Expected Value + Bayes)
# ---------------------------------------------------------------------------

def gen_probability_arena(count: int) -> List[GameRecord]:
    """Dice, coins, and probability challenges.
    Teaches: expected value, conditional probability, Bayes' theorem.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Probability Arena] [MATH: Probability & Statistics]\n"
        "You are in the Probability Arena! "
        "Roll dice, flip coins, make bets. "
        "The best strategy isn't luck — it's MATH."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: expected value of a die roll
        sides = random.choice([4, 6, 8, 12, 20])
        ev = (sides + 1) / 2
        records.append(GameRecord(
            game="probability-arena", system=sys_msg,
            user=f"You roll a fair {sides}-sided die. What's the expected value?",
            assistant=f"Expected value = (1 + 2 + ... + {sides}) / {sides}\n"
                      f"Sum = {sides}×({sides}+1)/2 = {sides * (sides + 1) // 2}\n"
                      f"EV = {sides * (sides + 1) // 2} / {sides} = {ev}\n"
                      f"On average, you'll roll {ev}. Over 100 rolls, "
                      f"you'd expect a total near {ev * 100:.0f}.",
            difficulty="easy", concept="probability", tongue=tongue,
            math_type="probability",
            tags=["expected-value", "die-roll"],
        ))

        # MEDIUM: two coins, conditional probability
        records.append(GameRecord(
            game="probability-arena", system=sys_msg,
            user=f"Flip 2 coins. You know at least ONE is heads. "
                 f"What's the probability BOTH are heads?",
            assistant=f"Careful — this isn't 1/2!\n"
                      f"All possible outcomes: HH, HT, TH, TT.\n"
                      f"Remove TT (at least one is heads): HH, HT, TH.\n"
                      f"P(both heads | at least one heads) = 1/3 ≈ 33.3%.\n\n"
                      f"Common mistake: thinking 'the other coin is 50/50.' "
                      f"But 'at least one heads' changes the sample space. "
                      f"This is conditional probability — the denominator shrinks.",
            difficulty="medium", concept="probability", tongue=tongue,
            math_type="probability",
            tags=["conditional", "sample-space"],
        ))

        # HARD: Monty Hall
        records.append(GameRecord(
            game="probability-arena", system=sys_msg,
            user=f"Three doors: one has a prize. You pick door 1. "
                 f"The host opens door 3 (no prize). Should you switch to door 2?",
            assistant=f"YES — always switch!\n"
                      f"Initial pick (door 1): P(prize) = 1/3.\n"
                      f"Remaining doors: P(prize behind 2 or 3) = 2/3.\n"
                      f"Host reveals door 3 is empty — that 2/3 probability "
                      f"CONCENTRATES onto door 2.\n"
                      f"Switching: P(win) = 2/3.\n"
                      f"Staying: P(win) = 1/3.\n\n"
                      f"Intuition: your initial guess is probably wrong (2/3 chance). "
                      f"The host HELPS you by showing a losing door. "
                      f"Switching exploits the host's knowledge.",
            difficulty="hard", concept="probability", tongue=tongue,
            math_type="probability",
            tags=["monty-hall", "bayes", "switching"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 7: Cellular Playground (Conway's Life as a Kids Game)
# ---------------------------------------------------------------------------

def gen_cellular_playground(count: int) -> List[GameRecord]:
    """Conway's Game of Life rules explained as playground behavior.
    Teaches: cellular automata, emergence, state transitions.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Cellular Playground] [MATH: Cellular Automata]\n"
        "You are on a grid playground! Each square is either OCCUPIED or EMPTY. "
        "Every round, check your neighbors (8 surrounding squares):\n"
        "- Lonely rule: <2 neighbors → leave (underpopulation)\n"
        "- Happy rule: 2-3 neighbors → stay\n"
        "- Crowded rule: >3 neighbors → leave (overcrowding)\n"
        "- Birth rule: empty square with exactly 3 neighbors → someone new arrives"
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: 3 in a row, what happens?
        records.append(GameRecord(
            game="cellular-playground", system=sys_msg,
            user=f"Three kids stand in a horizontal row (blinker pattern): "
                 f"_X_\n_X_\n_X_\nWhat happens next round?",
            assistant=f"Apply the rules to each cell:\n"
                      f"- Top X: only 1 neighbor (middle) → lonely → LEAVES\n"
                      f"- Middle X: 2 neighbors (top, bottom) → happy → STAYS\n"
                      f"- Bottom X: only 1 neighbor (middle) → lonely → LEAVES\n"
                      f"- Empty cells left and right of middle: each has exactly 3 neighbors → BIRTH!\n\n"
                      f"Result: the vertical line becomes horizontal:\n"
                      f"___\nXXX\n___\n\n"
                      f"Next round? It flips back to vertical! This is a BLINKER — "
                      f"it oscillates forever with period 2.",
            difficulty="easy", concept="automata", tongue=tongue,
            math_type="discrete_math",
            tags=["blinker", "oscillator", "period-2"],
        ))

        # MEDIUM: 2x2 block — stable
        records.append(GameRecord(
            game="cellular-playground", system=sys_msg,
            user=f"Four kids in a 2x2 square (block pattern):\nXX\nXX\nWhat happens?",
            assistant=f"Each kid has exactly 3 neighbors → HAPPY → stays.\n"
                      f"Empty cells around the block: each has at most 2 occupied neighbors → no births.\n\n"
                      f"Result: nothing changes! The block is a 'still life.'\n"
                      f"It's STABLE — no births, no deaths, forever.\n\n"
                      f"In systems theory, this is a fixed point. "
                      f"The block is one of the simplest attractors in Conway's Life.",
            difficulty="medium", concept="automata", tongue=tongue,
            math_type="discrete_math",
            tags=["block", "still-life", "fixed-point"],
        ))

        # HARD: R-pentomino — chaos from 5 cells
        records.append(GameRecord(
            game="cellular-playground", system=sys_msg,
            user=f"Five kids in an R-shape:\n_XX\nXX_\n_X_\n"
                 f"This is called the R-pentomino. What happens?",
            assistant=f"CHAOS. The R-pentomino is one of the most famous patterns in Life.\n"
                      f"From just 5 cells, it takes 1,103 generations to stabilize!\n"
                      f"It produces:\n"
                      f"- 6 gliders (patterns that travel across the grid)\n"
                      f"- Multiple still lifes and oscillators\n"
                      f"- Final population: ~116 cells (from 5!)\n\n"
                      f"The lesson: you CANNOT predict the outcome by looking at the starting position. "
                      f"You have to SIMULATE it step by step. No shortcut.\n"
                      f"This is computational irreducibility — "
                      f"some systems can only be understood by running them.",
            difficulty="hard", concept="automata", tongue=tongue,
            math_type="discrete_math",
            tags=["r-pentomino", "chaos", "computational-irreducibility"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 8: Gravity Puzzles (Physics with Real Numbers)
# ---------------------------------------------------------------------------

def gen_gravity_puzzles(count: int) -> List[GameRecord]:
    """Real physics: forces, momentum, orbital mechanics as playground problems.
    Teaches: Newton's laws, conservation, escape velocity.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Gravity Puzzles] [MATH: Physics]\n"
        "You are solving Gravity Puzzles! "
        "Real physics with real numbers — forces, momentum, orbits."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: F = ma
        mass = random.choice([2, 5, 10, 20])
        accel = random.choice([1, 2, 3, 5])
        force = mass * accel
        records.append(GameRecord(
            game="gravity-puzzles", system=sys_msg,
            user=f"A {mass}kg ball accelerates at {accel} m/s². What force is needed?",
            assistant=f"F = m × a = {mass} × {accel} = {force} Newtons.\n"
                      f"That's about the force of "
                      + (f"lifting {force // 10} apples." if force <= 50 else
                         f"a strong push — like shoving a heavy box."),
            difficulty="easy", concept="physics", tongue=tongue,
            math_type="physics",
            tags=["newton-second-law", "force"],
        ))

        # MEDIUM: conservation of momentum
        m1 = random.choice([2, 3, 5])
        v1 = random.choice([4, 6, 8])
        m2 = random.choice([1, 2, 3])
        # After collision (perfectly inelastic)
        v_final = (m1 * v1) / (m1 + m2)
        records.append(GameRecord(
            game="gravity-puzzles", system=sys_msg,
            user=f"Ball A ({m1}kg, moving at {v1} m/s) hits Ball B ({m2}kg, stationary). "
                 f"They stick together. How fast do they move?",
            assistant=f"Conservation of momentum: m₁v₁ = (m₁ + m₂)v_final\n"
                      f"{m1} × {v1} = ({m1} + {m2}) × v_final\n"
                      f"{m1 * v1} = {m1 + m2} × v_final\n"
                      f"v_final = {m1 * v1}/{m1 + m2} = {v_final:.2f} m/s\n\n"
                      f"Energy lost: KE_before = ½×{m1}×{v1}² = {0.5*m1*v1**2:.1f} J\n"
                      f"KE_after = ½×{m1+m2}×{v_final:.2f}² = {0.5*(m1+m2)*v_final**2:.1f} J\n"
                      f"Lost to heat/deformation: {0.5*m1*v1**2 - 0.5*(m1+m2)*v_final**2:.1f} J",
            difficulty="medium", concept="physics", tongue=tongue,
            math_type="physics",
            tags=["momentum", "inelastic-collision"],
        ))

        # HARD: escape velocity
        planet_mass_kg = random.choice([6e24, 6.4e23, 1.9e27])  # Earth, Mars, Jupiter
        planet_name = {6e24: "Earth", 6.4e23: "Mars", 1.9e27: "Jupiter"}[planet_mass_kg]
        planet_radius = {6e24: 6.371e6, 6.4e23: 3.39e6, 1.9e27: 6.99e7}[planet_mass_kg]
        G = 6.674e-11
        v_escape = math.sqrt(2 * G * planet_mass_kg / planet_radius)
        records.append(GameRecord(
            game="gravity-puzzles", system=sys_msg,
            user=f"Calculate the escape velocity from {planet_name}.\n"
                 f"Mass = {planet_mass_kg:.2e} kg, Radius = {planet_radius:.3e} m, "
                 f"G = 6.674×10⁻¹¹ N⋅m²/kg².",
            assistant=f"v_escape = √(2GM/R)\n"
                      f"= √(2 × 6.674×10⁻¹¹ × {planet_mass_kg:.2e} / {planet_radius:.3e})\n"
                      f"= √({2 * G * planet_mass_kg / planet_radius:.4e})\n"
                      f"= {v_escape:.0f} m/s = {v_escape/1000:.1f} km/s\n\n"
                      f"That's {v_escape/343:.0f}x the speed of sound!\n"
                      f"Below this speed, what goes up MUST come down. "
                      f"Above it, goodbye {planet_name}.\n"
                      f"This is why the SCBE Poincare ball has a boundary — "
                      f"adversarial behavior needs 'escape velocity' that grows exponentially.",
            difficulty="hard", concept="physics", tongue=tongue,
            math_type="physics",
            tags=["escape-velocity", "orbital-mechanics", "scbe-bridge"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 9: Pattern Lock (Sequence Prediction + Recurrence Relations)
# ---------------------------------------------------------------------------

def gen_pattern_lock(count: int) -> List[GameRecord]:
    """Number sequences with hidden rules.
    Teaches: recurrence relations, Fibonacci, geometric/arithmetic progressions.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Pattern Lock] [MATH: Sequences & Recurrence]\n"
        "You are cracking a Pattern Lock! "
        "Find the rule, predict the next number."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)

        # EASY: arithmetic sequence
        start = random.randint(2, 10)
        step = random.randint(2, 7)
        seq = [start + step * i for i in range(5)]
        next_val = start + step * 5
        records.append(GameRecord(
            game="pattern-lock", system=sys_msg,
            user=f"Sequence: {seq}. What comes next?",
            assistant=f"Arithmetic sequence with step +{step}.\n"
                      f"Rule: a(n) = {start} + {step}n\n"
                      f"Next: {seq[-1]} + {step} = {next_val}",
            difficulty="easy", concept="sequence", tongue=tongue,
            math_type="algebra",
            tags=["arithmetic", "linear"],
        ))

        # MEDIUM: geometric sequence
        base = random.choice([2, 3])
        geo = [base ** i for i in range(6)]
        records.append(GameRecord(
            game="pattern-lock", system=sys_msg,
            user=f"Sequence: {geo[:5]}. What comes next? What's the rule?",
            assistant=f"Geometric sequence: each term is {base}× the previous.\n"
                      f"Rule: a(n) = {base}^n\n"
                      f"Next: {geo[4]} × {base} = {geo[5]}\n\n"
                      f"Growth rate: this is EXPONENTIAL. "
                      f"After 20 terms: {base}^20 = {base**20:,}.\n"
                      f"This is why H(d,R) = R^(d²) grows so fast — "
                      f"it's exponential IN the exponent!",
            difficulty="medium", concept="sequence", tongue=tongue,
            math_type="algebra",
            tags=["geometric", "exponential"],
        ))

        # HARD: Fibonacci variant
        a, b = random.randint(1, 3), random.randint(1, 4)
        fib = [a, b]
        for _ in range(6):
            fib.append(fib[-1] + fib[-2])
        ratio = fib[-1] / fib[-2]
        records.append(GameRecord(
            game="pattern-lock", system=sys_msg,
            user=f"Sequence: {fib[:6]}. "
                 f"What's the rule? What's the ratio of consecutive terms approaching?",
            assistant=f"Fibonacci-type recurrence: a(n) = a(n-1) + a(n-2).\n"
                      f"Starting from {a}, {b}.\n"
                      f"Next two: {fib[6]}, {fib[7]}\n\n"
                      f"Ratio of consecutive terms:\n" +
                      "\n".join(f"  {fib[i+1]}/{fib[i]} = {fib[i+1]/fib[i]:.4f}" for i in range(len(fib)-1)) +
                      f"\n\nConverges to φ (phi) = {PHI:.6f} — the golden ratio!\n"
                      f"Latest ratio here is {ratio:.4f}.\n"
                      f"No matter what you start with (except 0,0), the ratio ALWAYS converges to phi. "
                      f"This is why SCBE uses phi for tongue weights — "
                      f"it's the universe's most natural growth constant.",
            difficulty="hard", concept="sequence", tongue=tongue,
            math_type="algebra",
            tags=["fibonacci", "golden-ratio", "phi", "convergence"],
        ))

    return records


# ---------------------------------------------------------------------------
# Game 10: Multi-Objective Challenge (Simultaneous Constraints)
# ---------------------------------------------------------------------------

def gen_multi_objective(count: int) -> List[GameRecord]:
    """Multiple competing objectives at the same time.
    Teaches: Pareto optimality, trade-offs, multi-criteria decision making.
    """
    records = []
    sys_msg = (
        "[KIDS-GAME: Multi-Objective Challenge] [MATH: Pareto Optimization]\n"
        "You face MULTIPLE challenges at once! "
        "You can't maximize everything — find the best trade-off."
    )

    for _ in range(count):
        tongue = random.choice(TONGUES)
        squad = random.sample(TONGUES, 4)

        # EASY: speed vs strength (simple trade-off)
        records.append(GameRecord(
            game="multi-objective", system=sys_msg,
            user=f"Assign 10 training points between Speed and Strength for {_name(squad[0])}. "
                 f"Speed helps in races (1 point = 1 second faster). "
                 f"Strength helps in climbing (1 point = 1 meter higher). "
                 f"There's a race AND a climb today. Best split?",
            assistant=f"Without knowing which event matters MORE, every split is equally valid!\n"
                      f"(10,0): win the race, fail the climb.\n"
                      f"(0,10): win the climb, fail the race.\n"
                      f"(5,5): decent at both, great at neither.\n"
                      f"(7,3): fast runner, weak climber.\n\n"
                      f"All of these are 'Pareto optimal' — you can't improve one "
                      f"without hurting the other.\n"
                      f"The 'best' choice depends on which event has a bigger prize.",
            difficulty="easy", concept="pareto", tongue=tongue,
            math_type="optimization",
            tags=["trade-off", "pareto-front"],
        ))

        # MEDIUM: three objectives
        records.append(GameRecord(
            game="multi-objective", system=sys_msg,
            user=f"Squad has 12 upgrade tokens. Three stats: Attack, Defense, Speed. "
                 f"Upcoming battle has 3 phases:\n"
                 f"Phase 1 (attack matters): score = Attack × 2\n"
                 f"Phase 2 (defense matters): score = Defense × 3\n"
                 f"Phase 3 (speed matters): score = Speed × 1\n"
                 f"Maximize total score across all 3 phases.",
            assistant=f"Weight each stat by its multiplier:\n"
                      f"Attack: ×2 per token\n"
                      f"Defense: ×3 per token (best value!)\n"
                      f"Speed: ×1 per token (worst value)\n\n"
                      f"Greedy: put all 12 into Defense → 12 × 3 = 36 total.\n"
                      f"But phases require MINIMUM participation!\n\n"
                      f"If each phase needs ≥1 token in its stat:\n"
                      f"Optimal: Attack=1, Defense=10, Speed=1 → 1×2 + 10×3 + 1×1 = 33.\n"
                      f"vs Even: 4,4,4 → 4×2 + 4×3 + 4×1 = 8+12+4 = 24.\n\n"
                      f"The weighted allocation beats even split by {33-24} points. "
                      f"Invest where the multiplier is highest!",
            difficulty="medium", concept="pareto", tongue=tongue,
            math_type="optimization",
            tags=["weighted-allocation", "three-objective"],
        ))

        # HARD: real multi-objective with Pareto frontier
        options = [
            (8, 3, "Sprint Build"),
            (5, 6, "Balanced Build"),
            (3, 9, "Tank Build"),
            (6, 5, "Hybrid Build"),
            (4, 4, "Weak Build"),
        ]
        # Identify Pareto-optimal solutions
        pareto = []
        for i, (a, d, name) in enumerate(options):
            dominated = False
            for j, (a2, d2, _) in enumerate(options):
                if i != j and a2 >= a and d2 >= d and (a2 > a or d2 > d):
                    dominated = True
                    break
            if not dominated:
                pareto.append((a, d, name))

        option_str = "\n".join(f"  {name}: Attack={a}, Defense={d}" for a, d, name in options)
        pareto_str = ", ".join(f"{name} ({a},{d})" for a, d, name in pareto)
        records.append(GameRecord(
            game="multi-objective", system=sys_msg,
            user=f"Five possible builds:\n{option_str}\n\n"
                 f"Which builds are Pareto-optimal (not dominated by any other)?",
            assistant=f"A build is dominated if another build is BETTER in at least one stat "
                      f"and at least as good in all others.\n\n"
                      f"Check each:\n" +
                      "\n".join(
                          f"  {name} ({a},{d}): " +
                          ("DOMINATED" if (a, d, name) not in pareto else "PARETO-OPTIMAL") +
                          (" — " + next(
                              (f"{n2} ({a2},{d2}) beats it" for a2, d2, n2 in options
                               if (a2 >= a and d2 >= d and (a2 > a or d2 > d) and n2 != name)),
                              "nothing dominates it"
                          ))
                          for a, d, name in options
                      ) +
                      f"\n\nPareto frontier: {pareto_str}\n"
                      f"These are the ONLY rational choices — everything else is strictly worse.",
            difficulty="hard", concept="pareto", tongue=tongue,
            math_type="optimization",
            tags=["pareto-frontier", "dominance", "multi-criteria"],
        ))

    return records


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

GAMES = [
    ("tile-swap", gen_tile_swap),
    ("chess-territory", gen_chess_territory),
    ("resource-race", gen_resource_race),
    ("color-clash", gen_color_clash),
    ("nim-strategy", gen_nim_strategy),
    ("probability-arena", gen_probability_arena),
    ("cellular-playground", gen_cellular_playground),
    ("gravity-puzzles", gen_gravity_puzzles),
    ("pattern-lock", gen_pattern_lock),
    ("multi-objective", gen_multi_objective),
]


def main():
    random.seed(SEED)
    records_per_game = 200  # 3 difficulties × 200 = 600 records per game

    print("=" * 70)
    print("Kids Math Games — SFT Generator (REAL Mathematics)")
    print("=" * 70)

    all_records = []
    for game_name, generator in GAMES:
        print(f"\n  Generating {game_name}...", end="", flush=True)
        recs = generator(records_per_game)
        sft_recs = [record_to_sft(r) for r in recs]
        all_records.extend(sft_recs)
        print(f"  {len(sft_recs)} records", flush=True)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(all_records)} records to {OUTPUT_PATH.name}...", end="", flush=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(" done")

    # Stats
    file_size = OUTPUT_PATH.stat().st_size
    print(f"\n{'='*70}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"  Total records:  {len(all_records):>8,}")
    print(f"  File size:      {file_size:>8,} bytes ({file_size/1024/1024:.1f} MB)")

    # Distribution
    game_counts = {}
    tongue_counts = {}
    diff_counts = {}
    math_counts = {}
    for rec in all_records:
        game = rec["augmentation"].replace("math-", "")
        game_counts[game] = game_counts.get(game, 0) + 1
        t = rec["dominant_tongue"]
        tongue_counts[t] = tongue_counts.get(t, 0) + 1
        for tag in rec["tags"]:
            if tag in DIFFICULTIES:
                diff_counts[tag] = diff_counts.get(tag, 0) + 1
        # Math type from tags
        for tag in rec["tags"]:
            if tag in ["combinatorics", "graph_theory", "optimization", "game_theory",
                        "probability", "discrete_math", "physics", "algebra"]:
                math_counts[tag] = math_counts.get(tag, 0) + 1

    print(f"\n  Game distribution:")
    for g, c in sorted(game_counts.items()):
        print(f"    {g:30s} {c:5d} ({c/len(all_records)*100:5.1f}%)")

    print(f"\n  Math type distribution:")
    for m, c in sorted(math_counts.items()):
        print(f"    {m:30s} {c:5d} ({c/len(all_records)*100:5.1f}%)")

    print(f"\n  Tongue distribution:")
    for t in TONGUES:
        c = tongue_counts.get(t, 0)
        print(f"    {t} ({TONGUE_NAMES[t]:15s}) {c:5d} ({c/len(all_records)*100:5.1f}%)")

    print(f"\n  Difficulty distribution:")
    for d in DIFFICULTIES:
        c = diff_counts.get(d, 0)
        print(f"    {d:10s} {c:5d} ({c/len(all_records)*100:5.1f}%)")


if __name__ == "__main__":
    main()
