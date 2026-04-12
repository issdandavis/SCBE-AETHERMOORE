#!/usr/bin/env python3
"""Multi-Dimensional Go SFT: Train AI to play Go where each board runs a different Sacred Tongue.

Inspired by Gungi from Hunter x Hunter — a strategic game where mastery requires
understanding multiple layers of rules simultaneously.

Architecture:
  - 6 Go boards, one per Sacred Tongue (Kor'aelin, Avali, Runethic, Cassisivadan, Umbroth, Draumric)
  - Each board uses that tongue's tokenizer for move notation
  - Same game rules (Go), different semantic languages for expressing moves
  - Phase 1: 1v1 on a SINGLE tongue board (learn one language at a time)
  - Phase 2: 1v1 on 2-3 boards simultaneously (cross-tongue reasoning)
  - Phase 3: 1v1 on all 6 boards (full multi-dimensional play)
  - Each move on one board affects the state of others via phi-weighted coupling

The goal: if the AI can play Go in ALL six tongues simultaneously, coordinating
strategy across boards that share state but speak different languages, then it has
INTERNALIZED the tokenizer — not memorized it.
"""

from __future__ import annotations

import json
import math
import random
import hashlib
import sys
import io
from pathlib import Path

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "training-data" / "sft"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHI = (1 + math.sqrt(5)) / 2

# Full canonical tongue definitions
TONGUES = {
    "KO": {
        "full": "Kor'aelin", "color": "red-gold",
        "domain": "Intent", "essence": "what should be true",
        "weight": 1.00, "phi_power": 0,
        "go_move_style": "Moves are expressed as INTENTIONS. Not 'place at D4' but 'establish presence in center with purpose: territory claim'. The KO board tracks WHY each stone is placed.",
        "go_notation": "KO:{intent}:{target}:{purpose}",
        "go_example_move": "KO:CLAIM:D4:territory-expansion",
        "go_captures_mean": "Capturing on the Kor'aelin board means your intent was stronger. The opponent's purpose was weaker or contradicted by yours.",
        "go_territory_means": "Territory on the Kor'aelin board represents CLAIMED PURPOSE — the area of intent you've established as your own.",
    },
    "AV": {
        "full": "Avali", "color": "blue-silver",
        "domain": "Context/Transport", "essence": "how to get there",
        "weight": round(PHI ** 1, 3), "phi_power": 1,
        "go_move_style": "Moves are expressed as ROUTES. Not 'place at D4' but 'route through D4 connecting A-group to B-group'. The AV board tracks HOW stones connect.",
        "go_notation": "AV:{route}:{from}:{to}:{via}",
        "go_example_move": "AV:ROUTE:corner-group:center:D4",
        "go_captures_mean": "Capturing on the Avali board means you cut a route. The opponent's connection was severed — their stones can no longer transport influence between groups.",
        "go_territory_means": "Territory on the Avali board represents CONNECTED PATHWAYS — routes your stones can traverse freely.",
    },
    "RU": {
        "full": "Runethic", "color": "deep purple",
        "domain": "Binding/Permissions", "essence": "who is allowed",
        "weight": round(PHI ** 2, 3), "phi_power": 2,
        "go_move_style": "Moves are expressed as PERMISSIONS. Not 'place at D4' but 'grant access at D4 to allied groups, deny access to opponent'. The RU board tracks WHO can use each intersection.",
        "go_notation": "RU:{permission}:{intersection}:{granted_to}:{denied_to}",
        "go_example_move": "RU:GRANT:D4:self:opponent",
        "go_captures_mean": "Capturing on the Runethic board means you revoked access. The opponent's stones no longer have permission to occupy that space — their authorization expired.",
        "go_territory_means": "Territory on the Runethic board represents ACCESS-CONTROLLED SPACE — intersections where you hold the permission keys.",
    },
    "CA": {
        "full": "Cassisivadan", "color": "white-gold",
        "domain": "Implementation/Compute", "essence": "how to make it true",
        "weight": round(PHI ** 3, 3), "phi_power": 3,
        "go_move_style": "Moves are expressed as COMPUTATIONS. Not 'place at D4' but 'execute influence-propagation at D4, cost: 1 liberty, output: +3 influence on neighbors'. The CA board tracks the MECHANICS of each move.",
        "go_notation": "CA:{operation}:{target}:{cost}:{output}",
        "go_example_move": "CA:PROPAGATE:D4:1-liberty:+3-influence",
        "go_captures_mean": "Capturing on the Cassisivadan board means your computation was more efficient. The opponent's implementation consumed more resources (liberties) than it produced (influence).",
        "go_territory_means": "Territory on the Cassisivadan board represents COMPUTED DOMINANCE — space where your algorithms are running and producing output.",
    },
    "UM": {
        "full": "Umbroth", "color": "shadow-black",
        "domain": "Security/Privacy", "essence": "what must stay hidden",
        "weight": round(PHI ** 4, 3), "phi_power": 4,
        "go_move_style": "Moves are expressed as CONCEALMENT. Not 'place at D4' but 'veil presence at D4, visible to self only until triggered'. The UM board tracks what is HIDDEN and what is exposed.",
        "go_notation": "UM:{visibility}:{target}:{trigger}",
        "go_example_move": "UM:VEIL:D4:opponent-approaches-within-2",
        "go_captures_mean": "Capturing on the Umbroth board means you exposed and neutralized a hidden threat. Or your hidden stone was revealed at the perfect moment to capture.",
        "go_territory_means": "Territory on the Umbroth board represents SECURE SPACE — area you control where threats cannot operate unseen.",
    },
    "DR": {
        "full": "Draumric", "color": "earth-brown",
        "domain": "Structure/Authentication", "essence": "proof that it is true",
        "weight": round(PHI ** 5, 3), "phi_power": 5,
        "go_move_style": "Moves are expressed as STRUCTURAL CLAIMS. Not 'place at D4' but 'authenticate position D4 as load-bearing for architecture X'. The DR board tracks the PROOF of ownership and structural integrity.",
        "go_notation": "DR:{claim}:{target}:{structure}:{proof}",
        "go_example_move": "DR:AUTHENTICATE:D4:wall-formation:3-connected-stones",
        "go_captures_mean": "Capturing on the Draumric board means the opponent's structure was fraudulent. Their claim was unproven or their proof was invalidated. The architecture collapses.",
        "go_territory_means": "Territory on the Draumric board represents AUTHENTICATED STRUCTURE — space whose ownership is cryptographically proven by your stone topology.",
    },
}

# Game phases for curriculum
PHASES = {
    1: {
        "name": "Single Board Mastery",
        "boards": 1,
        "description": "Learn to play Go in ONE tongue at a time. Master each language before combining.",
        "difficulty": 0.2,
    },
    2: {
        "name": "Dual Board",
        "boards": 2,
        "description": "Play two tongue boards simultaneously. Moves on one affect the other via phi-coupling.",
        "difficulty": 0.4,
    },
    3: {
        "name": "Triple Board",
        "boards": 3,
        "description": "Three boards. Cross-tongue strategy becomes essential. Can't win by dominating one board if you lose two.",
        "difficulty": 0.6,
    },
    4: {
        "name": "Full Six-Board",
        "boards": 6,
        "description": "All six tongue boards active. The master game. Every move has 6 simultaneous expressions.",
        "difficulty": 0.8,
    },
}

SYS_PROMPT = (
    "You are Polly, teaching the Sacred Tongues through multi-dimensional Go. "
    "Each Go board uses a different Sacred Tongue for move notation. Same game, "
    "different languages. If the student can play across all boards, they've internalized "
    "the tongues -- not memorized them."
)

SYS_MATCH = (
    "You are the game narrator for a multi-dimensional Go match between two SCBE-trained agents. "
    "Each board runs a different Sacred Tongue tokenizer. Report moves in the tongue of each board. "
    "Explain how moves on one board affect the state of others via phi-weighted coupling."
)


def make_record(system, user, assistant, tongues_active, difficulty, augmentation, tags):
    """Build a dimensionally-tagged record."""
    tongue_scores = {code: (0.8 if code in tongues_active else 0.1) for code in TONGUES}
    dominant = tongues_active[0] if tongues_active else "DR"
    layers = [3, 4, 5, 12, 13]  # Go touches weighted transform -> poincare -> distance -> harmonic -> decision
    axioms = ["A4_symmetry", "A2_locality"]  # Go is inherently symmetric and local

    tongue_str = " ".join(f"{t}={v}" for t, v in tongue_scores.items())
    layer_str = ",".join(f"L{l}" for l in layers)
    axiom_str = ",".join(axioms)
    dim_header = (
        f"[TONGUES: {tongue_str}]\n[LAYERS: {layer_str}]\n[AXIOMS: {axiom_str}]\n[DIFFICULTY: {difficulty}]"
    )

    return {
        "messages": [
            {"role": "system", "content": f"{dim_header}\n{system}"},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tongue_weights": tongue_scores,
        "dominant_tongue": dominant,
        "layers": layers,
        "axioms": axioms,
        "difficulty": difficulty,
        "augmentation": augmentation,
        "tags": tags,
        "source_hash": hashlib.md5(user.encode()).hexdigest()[:8],
    }


def generate_concept_records() -> list[dict]:
    """Records that explain the concept of tongue-Go."""
    records = []

    # What is multi-dimensional Go?
    records.append(make_record(
        SYS_PROMPT,
        "What is multi-dimensional Go? How does it relate to the Sacred Tongues?",
        "Multi-dimensional Go is a training exercise where the same game of Go is played "
        "simultaneously across 6 boards -- one per Sacred Tongue.\n\n"
        "**The boards:**\n"
        + "\n".join(
            f"- **{t['full']} ({code})** board ({t['color']}): {t['go_move_style']}"
            for code, t in TONGUES.items()
        )
        + "\n\n"
        "**Same game, different languages.** A single stone placement at D4 is expressed "
        "differently on each board:\n"
        + "\n".join(
            f"- {t['full']}: `{t['go_example_move']}`"
            for t in TONGUES.values()
        )
        + "\n\n"
        "**Why?** If you can only describe a move in one tongue, you only understand one "
        "dimension of it. A move that looks strong on the Kor'aelin (Intent) board might "
        "be catastrophic on the Umbroth (Security) board. Multi-dimensional Go forces the "
        "player to evaluate every move from all 6 perspectives simultaneously.\n\n"
        "Like Gungi in Hunter x Hunter -- mastery means holding the whole game in your mind at once.",
        list(TONGUES.keys()), 0.3, "go-concept", ["go", "concept", "all-tongues"],
    ))

    # Why use Go specifically?
    records.append(make_record(
        SYS_PROMPT,
        "Why Go? Why not chess or another game?",
        "Go maps naturally to the Sacred Tongue architecture for three reasons:\n\n"
        "**1. Territory = Semantic Space**\n"
        "In Go, you claim territory -- empty space surrounded by your stones. In the tongue "
        "system, you claim semantic space -- regions of the 6-dimensional governance manifold. "
        "Every Go territory claim IS a tongue assertion.\n\n"
        "**2. Emergent Complexity**\n"
        "Go has simple rules but exponential strategic depth (more board states than atoms in "
        "the universe). The Sacred Tongues have simple individual rules (256 tokens per tongue) "
        "but 256^6 = 2.8 * 10^14 combined states. Both systems create complexity from simplicity.\n\n"
        "**3. Locality + Global Consequence**\n"
        "Every Go move is LOCAL (one intersection) but has GLOBAL effects (changes the balance "
        "of the whole board). Every tongue evaluation is LOCAL (one input) but has GLOBAL "
        "governance effects (changes the safety score for the entire pipeline).\n\n"
        "**4. Captures = Governance Decisions**\n"
        "In Go, capturing stones removes threats. In the governance pipeline, DENY removes "
        "threats. The parallel is exact: identify, surround (evaluate from all dimensions), "
        "capture (deny/quarantine).",
        list(TONGUES.keys()), 0.25, "go-concept", ["go", "concept", "reasoning"],
    ))

    return records


def generate_single_board_records() -> list[dict]:
    """Phase 1: Learn to play Go in one tongue at a time."""
    records = []

    for code, t in TONGUES.items():
        # How moves work on this board
        records.append(make_record(
            SYS_PROMPT,
            f"How do I play Go on the {t['full']} ({code}) board?",
            f"**{t['full']} Go -- The {t['color']} Board**\n\n"
            f"On the {t['full']} board, every move is expressed in the language of "
            f"{t['domain'].lower()} -- '{t['essence']}'.\n\n"
            f"**Move notation:** `{t['go_notation']}`\n"
            f"**Example:** `{t['go_example_move']}`\n\n"
            f"**{t['go_move_style']}**\n\n"
            f"**Captures:** {t['go_captures_mean']}\n\n"
            f"**Territory:** {t['go_territory_means']}\n\n"
            f"**Phi-weight:** {t['weight']} (phi^{t['phi_power']}). This tongue's board "
            f"contributes {t['weight']:.3f} units to the combined game score. "
            f"{'This is the lightest board -- foundation matters but gets outweighed by higher tongues.' if code == 'KO' else ''}"
            f"{'This is the HEAVIEST board -- structural victory here outweighs all others combined.' if code == 'DR' else ''}",
            [code], PHASES[1]["difficulty"], "go-single-board",
            ["go", "single-board", f"tongue-{code}", "rules"],
        ))

        # Sample opening on this board
        records.append(make_record(
            SYS_PROMPT,
            f"Show me an opening sequence on the {t['full']} board.",
            f"**{t['full']} Opening: The {t['essence'].title()} Gambit**\n\n"
            f"Move 1 (Black): `{code}:{'CLAIM' if code == 'KO' else 'ROUTE' if code == 'AV' else 'GRANT' if code == 'RU' else 'PROPAGATE' if code == 'CA' else 'VEIL' if code == 'UM' else 'AUTHENTICATE'}:D4:"
            f"{'foundation' if code in ('KO', 'DR') else 'center-access' if code == 'AV' else 'self-only' if code == 'RU' else '1-lib-to-4-inf' if code == 'CA' else 'hidden-until-contact'}`\n"
            f"Black establishes {'intent' if code == 'KO' else 'a route' if code == 'AV' else 'a permission boundary' if code == 'RU' else 'a computation node' if code == 'CA' else 'a hidden presence' if code == 'UM' else 'a structural anchor'} at center.\n\n"
            f"Move 2 (White): `{code}:{'CLAIM' if code == 'KO' else 'ROUTE' if code == 'AV' else 'GRANT' if code == 'RU' else 'PROPAGATE' if code == 'CA' else 'VEIL' if code == 'UM' else 'AUTHENTICATE'}:Q16:"
            f"{'counter-claim' if code == 'KO' else 'alternate-path' if code == 'AV' else 'competing-access' if code == 'RU' else 'parallel-compute' if code == 'CA' else 'counter-concealment' if code == 'UM' else 'competing-proof'}`\n"
            f"White responds in the opposite corner, establishing a competing "
            f"{'intent' if code == 'KO' else 'transport network' if code == 'AV' else 'permission zone' if code == 'RU' else 'computation center' if code == 'CA' else 'shadow' if code == 'UM' else 'structural claim'}.\n\n"
            f"Move 3 (Black): `{code}:{'REINFORCE' if code == 'KO' else 'EXTEND' if code == 'AV' else 'FORTIFY' if code == 'RU' else 'OPTIMIZE' if code == 'CA' else 'LAYER' if code == 'UM' else 'STRENGTHEN'}:D16:"
            f"{'dual-purpose' if code == 'KO' else 'bridge-corners' if code == 'AV' else 'expand-zone' if code == 'RU' else 'cache-result' if code == 'CA' else 'double-veil' if code == 'UM' else 'cross-brace'}`\n"
            f"Black extends toward the second corner, beginning to connect a "
            f"{'coherent intent arc' if code == 'KO' else 'transport corridor' if code == 'AV' else 'broad permission zone' if code == 'RU' else 'distributed computation' if code == 'CA' else 'deep shadow network' if code == 'UM' else 'structural framework'}.\n\n"
            f"Notice: the same 3-move opening (center, opposite corner, bridge) is expressed "
            f"ENTIRELY in {t['full']}'s vocabulary. The strategy is familiar Go. The language is "
            f"{t['full']}. If you can read these moves, you're starting to speak the tongue.",
            [code], PHASES[1]["difficulty"] + 0.05, "go-single-board",
            ["go", "single-board", f"tongue-{code}", "opening"],
        ))

    return records


def generate_dual_board_records() -> list[dict]:
    """Phase 2: Two boards simultaneously with phi-coupling."""
    records = []

    # Strategic pairings (high-tension combinations)
    pairings = [
        ("KO", "UM", "Intent vs Security -- the classic tension. A strong KO move (clear intent) "
         "might expose you on the UM board (security risk). Playing safe on UM might weaken "
         "your KO position (vague intent)."),
        ("AV", "DR", "Transport vs Structure -- routes must follow architecture. A brilliant "
         "AV connection (fast route) through a weak DR area (unproven structure) is a liability. "
         "The structure board constrains the transport board."),
        ("RU", "CA", "Permissions vs Implementation -- who is allowed vs how it executes. "
         "A generous RU move (broad permissions) requires expensive CA computation to enforce. "
         "A cheap CA move (simple implementation) may not support the RU permissions you've granted."),
        ("KO", "DR", "Intent vs Structure -- the highest-tension pairing. Kor'aelin (phi^0 = 1.0) "
         "is the lightest tongue; Draumric (phi^5 = 11.09) is the heaviest. A move that dominates "
         "the intent board barely registers on the structure board, and vice versa."),
        ("CA", "UM", "Compute vs Security -- implementation creates attack surfaces. Every "
         "CA optimization (efficiency gain) potentially opens a UM vulnerability (security hole). "
         "The Cassisivadan board rewards speed; the Umbroth board punishes exposure."),
        ("AV", "RU", "Transport vs Permissions -- routes need authorization. An Avali shortcut "
         "through unauthorized Runethic territory is illegal. Permission boundaries constrain "
         "routing options."),
    ]

    for t1, t2, tension in pairings:
        tongue1 = TONGUES[t1]
        tongue2 = TONGUES[t2]

        records.append(make_record(
            SYS_MATCH,
            f"Set up a dual-board match: {tongue1['full']} ({t1}) + {tongue2['full']} ({t2}). "
            f"What's the strategic tension?",
            f"**Dual Board: {tongue1['full']} ({tongue1['color']}) + {tongue2['full']} ({tongue2['color']})**\n\n"
            f"**Phi-coupling:** Every move on the {tongue1['full']} board (weight {tongue1['weight']}) "
            f"affects the {tongue2['full']} board (weight {tongue2['weight']}), scaled by "
            f"the ratio of their phi-weights: {tongue2['weight'] / tongue1['weight']:.3f}x coupling.\n\n"
            f"**Tension:** {tension}\n\n"
            f"**Win condition:** Combined score = {tongue1['full']} territory * {tongue1['weight']} + "
            f"{tongue2['full']} territory * {tongue2['weight']}. Because {tongue2['full']} weighs "
            f"{'more' if tongue2['weight'] > tongue1['weight'] else 'less'} "
            f"({tongue2['weight']} vs {tongue1['weight']}), "
            f"{'the heavier board dominates the combined score' if tongue2['weight'] > tongue1['weight'] else 'the boards are roughly balanced'}. "
            f"But you can't IGNORE the lighter board -- a total collapse there costs more than "
            f"a marginal gain on the heavier one.\n\n"
            f"**Key insight:** The player who understands BOTH tongues simultaneously -- who sees "
            f"a single stone as BOTH a {tongue1['domain'].lower()} assertion AND a "
            f"{tongue2['domain'].lower()} assertion -- has a decisive advantage over a player who "
            f"optimizes one board then patches the other.",
            [t1, t2], PHASES[2]["difficulty"], "go-dual-board",
            ["go", "dual-board", f"tongue-{t1}", f"tongue-{t2}", "strategy"],
        ))

    return records


def generate_full_board_records() -> list[dict]:
    """Phase 4: All 6 boards. The master game."""
    records = []

    # The full game explanation
    all_codes = list(TONGUES.keys())
    board_list = "\n".join(
        f"- **{t['full']} ({c})** ({t['color']}, phi^{t['phi_power']} = {t['weight']}): {t['go_move_style']}"
        for c, t in TONGUES.items()
    )

    records.append(make_record(
        SYS_MATCH,
        "Set up a full six-board match. What does a single move look like across all boards?",
        f"**THE MASTER GAME: Six-Board Multi-Dimensional Go**\n\n"
        f"**Active boards:**\n{board_list}\n\n"
        f"**A single stone at D4 expressed in all six tongues:**\n"
        + "\n".join(f"  {t['full']}: `{t['go_example_move']}`" for t in TONGUES.values())
        + "\n\n"
        f"**One move. Six meanings.** The stone is simultaneously:\n"
        f"- An intent (Kor'aelin)\n"
        f"- A route (Avali)\n"
        f"- A permission (Runethic)\n"
        f"- A computation (Cassisivadan)\n"
        f"- A concealment (Umbroth)\n"
        f"- A structural claim (Draumric)\n\n"
        f"**Combined score formula:**\n"
        f"Score = sum(territory_i * phi^i) for i in [0..5]\n"
        f"     = KO_territory * 1.0 + AV_territory * {PHI:.3f} + RU_territory * {PHI**2:.3f} + "
        f"CA_territory * {PHI**3:.3f} + UM_territory * {PHI**4:.3f} + DR_territory * {PHI**5:.3f}\n\n"
        f"Draumric territory is worth 11x Kor'aelin territory. But the phi guarantee means "
        f"you CANNOT win by dominating only Draumric -- a collapse in all five other tongues "
        f"costs 10.09 units while Draumric only provides 11.09. The margin is razor-thin.\n\n"
        f"The master player sees all six boards as one game. They place a stone that is "
        f"simultaneously strong in intent, efficient in routing, authorized in permissions, "
        f"optimal in computation, secure in concealment, and structurally sound. That is "
        f"speaking all six Sacred Tongues at once.",
        all_codes, PHASES[4]["difficulty"], "go-full-board",
        ["go", "full-board", "all-tongues", "master-game"],
    ))

    # Endgame scenario
    records.append(make_record(
        SYS_MATCH,
        "Describe a critical endgame position in a six-board match.",
        "**Endgame: The Phi Crisis**\n\n"
        "Black leads on 4 boards (Kor'aelin, Avali, Cassisivadan, Umbroth) but is losing "
        "on the two heaviest boards (Runethic, Draumric).\n\n"
        "**Score calculation:**\n"
        "Black: KO(+12)*1.0 + AV(+8)*1.618 + RU(-5)*2.618 + CA(+6)*4.236 + UM(+3)*6.854 + DR(-15)*11.09\n"
        "     = 12.0 + 12.94 + (-13.09) + 25.42 + 20.56 + (-166.35)\n"
        "     = -108.52\n\n"
        "**Black is losing by 108 points** despite winning 4 of 6 boards. The Draumric collapse "
        "(-15 territory * 11.09 weight = -166.35) overwhelms everything else.\n\n"
        "**This IS the phi guarantee in action.** You cannot build a strategy that ignores "
        "structure. Draumric alone is worth more than all other boards combined. The same "
        "mathematical property that prevents a coalition of lower tongues from outvoting "
        "Draumric in the governance pipeline prevents a multi-board lead from compensating "
        "for a structural collapse in Go.\n\n"
        "Black's only path to victory: sacrifice territory on the lighter boards to shore up "
        "Draumric. Trade intent (KO) and transport (AV) territory for structural control (DR). "
        "This is the fundamental lesson of the Sacred Tongues: structure is supreme. "
        f"phi^5 ({PHI**5:.2f}) > phi^0 + phi^1 + phi^2 + phi^3 + phi^4 ({1+PHI+PHI**2+PHI**3+PHI**4:.2f})",
        all_codes, PHASES[4]["difficulty"] + 0.1, "go-full-board",
        ["go", "full-board", "endgame", "phi-guarantee", "all-tongues"],
    ))

    # Match commentary
    records.append(make_record(
        SYS_MATCH,
        "Narrate the first 3 moves of a six-board match between Agent-Alpha and Agent-Beta.",
        "**Round 1 -- Agent-Alpha (Black) opens:**\n\n"
        "Alpha places at D4. Six boards light up simultaneously:\n"
        "- Kor'aelin: `KO:CLAIM:D4:center-dominance` -- Intent: claim the center\n"
        "- Avali: `AV:ROUTE:edge:center:D4` -- Context: establish a central hub\n"
        "- Runethic: `RU:GRANT:D4:self:all` -- Binding: self-only access to center\n"
        "- Cassisivadan: `CA:PROPAGATE:D4:1-lib:+4-inf` -- Compute: maximum influence spread\n"
        "- Umbroth: `UM:REVEAL:D4:full-visible` -- Security: no concealment (bold opening)\n"
        "- Draumric: `DR:AUTHENTICATE:D4:foundation:first-stone` -- Structure: this IS the foundation\n\n"
        "**Round 1 -- Agent-Beta (White) responds:**\n\n"
        "Beta places at Q16. The opposite corner. A mirror response:\n"
        "- Kor'aelin: `KO:COUNTER:Q16:territorial-balance` -- matching intent\n"
        "- Avali: `AV:ROUTE:edge:corner:Q16` -- independent transport network\n"
        "- Runethic: `RU:GRANT:Q16:self:all` -- mirrored permission zone\n"
        "- Cassisivadan: `CA:PROPAGATE:Q16:1-lib:+4-inf` -- equal computation\n"
        "- Umbroth: `UM:VEIL:Q16:hidden-intent` -- BUT Beta hides on the UM board!\n"
        "- Draumric: `DR:AUTHENTICATE:Q16:foundation:competing-proof` -- structural counter\n\n"
        "**The divergence is on the Umbroth board.** Alpha played openly (REVEAL). Beta played "
        "hidden (VEIL). On 5 boards, the position is symmetric. On the security board, Beta "
        "has information advantage -- Alpha doesn't know Beta's Umbroth position until triggered.\n\n"
        "**Round 2 -- Agent-Alpha:**\n\n"
        "Alpha places at D16, bridging the two corners. On the Avali board, this creates a "
        "connected route. On the Draumric board, it's a structural cross-brace. On the Umbroth "
        "board, Alpha still plays revealed -- gambling that transparency on security compensates "
        "for the information deficit.\n\n"
        "Three moves in, and the game is ALREADY a contest between six different languages' "
        "descriptions of the same three stones. This is what learning the Sacred Tongues looks like.",
        all_codes, PHASES[4]["difficulty"], "go-full-board",
        ["go", "full-board", "match-narration", "all-tongues", "opening"],
    ))

    return records


def generate_progression_records() -> list[dict]:
    """Records about the training progression from Phase 1 to Phase 4."""
    records = []

    records.append(make_record(
        SYS_PROMPT,
        "How does the multi-dimensional Go training progression work?",
        "**Phase 1: Single Board Mastery** (difficulty: 0.2)\n"
        "Play Go on ONE tongue board at a time. Learn each tongue's move notation, "
        "capture semantics, and territory meaning individually. An AI that can't play "
        "Kor'aelin-Go has no business trying Avali-Go.\n\n"
        "**Phase 2: Dual Board** (difficulty: 0.4)\n"
        "Two boards simultaneously with phi-coupling between them. Key pairings:\n"
        "- Kor'aelin + Umbroth (Intent vs Security)\n"
        "- Avali + Draumric (Transport vs Structure)\n"
        "- Runethic + Cassisivadan (Permissions vs Compute)\n"
        "Moves on one board ripple to the other, scaled by phi-weight ratio.\n\n"
        "**Phase 3: Triple Board** (difficulty: 0.6)\n"
        "Three boards. Cross-tongue strategy becomes essential. The AI must start "
        "thinking in COMBINATIONS of tongues, not individual ones.\n\n"
        "**Phase 4: Full Six-Board** (difficulty: 0.8)\n"
        "The master game. Every stone placement is simultaneously evaluated in all 6 tongues. "
        "The combined score is phi-weighted across all boards. "
        f"Draumric ({PHI**5:.2f}) outweighs all others ({1+PHI+PHI**2+PHI**3+PHI**4:.2f}) "
        "but ignoring any board is fatal.\n\n"
        "**Like Hunter x Hunter:** Komugi didn't become the world champion at Gungi by studying "
        "rules -- she became champion by playing thousands of games until the rules became instinct. "
        "The AI doesn't memorize tongue definitions. It PLAYS in them until the languages "
        "become native.",
        list(TONGUES.keys()), 0.3, "go-progression",
        ["go", "progression", "curriculum", "all-tongues"],
    ))

    records.append(make_record(
        SYS_PROMPT,
        "When does the AI graduate from single-board to multi-board Go?",
        "**Graduation criteria:**\n\n"
        "**Phase 1 -> Phase 2** (Single -> Dual):\n"
        "- Win rate > 60% against a baseline agent on EVERY individual tongue board\n"
        "- Can express the same 10-move sequence in all 6 tongue notations correctly\n"
        "- Can identify which tongue a move notation belongs to without being told\n\n"
        "**Phase 2 -> Phase 3** (Dual -> Triple):\n"
        "- Win rate > 55% on ALL 6 standard dual-board pairings\n"
        "- Can predict how a move on Board A affects Board B via phi-coupling\n"
        "- Demonstrates cross-tongue strategy (sacrificing on lighter board for heavier)\n\n"
        "**Phase 3 -> Phase 4** (Triple -> Full):\n"
        "- Win rate > 50% on triple-board against a Phase 2 graduate\n"
        "- Can articulate a unified strategy across 3+ boards in natural language\n"
        "- Demonstrates the phi-guarantee insight: structural play on Draumric trumps all\n\n"
        "**Mastery (Phase 4 graduation):**\n"
        "- Win rate > 50% in full six-board against another Phase 4 player\n"
        "- Can narrate a full game in all 6 tongue notations simultaneously\n"
        "- Demonstrates emergent strategy that no single-board player would discover\n\n"
        "The numbers are conservative. 50% against an equally-trained opponent means the AI "
        "is competitive. 60% means it's finding alpha. 70%+ means it's discovered something "
        "the training data didn't explicitly teach.",
        list(TONGUES.keys()), 0.35, "go-progression",
        ["go", "progression", "graduation", "evaluation"],
    ))

    return records


def main():
    all_records = []

    print("Generating Multi-Dimensional Go SFT...")
    concepts = generate_concept_records()
    print(f"  Concept records: {len(concepts)}")
    all_records.extend(concepts)

    single = generate_single_board_records()
    print(f"  Single-board records: {len(single)}")
    all_records.extend(single)

    dual = generate_dual_board_records()
    print(f"  Dual-board records: {len(dual)}")
    all_records.extend(dual)

    full = generate_full_board_records()
    print(f"  Full six-board records: {len(full)}")
    all_records.extend(full)

    progression = generate_progression_records()
    print(f"  Progression records: {len(progression)}")
    all_records.extend(progression)

    out_path = OUT_DIR / "tongue_go_sft.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nTongue Go SFT: {len(all_records)} records -> {out_path}")

    # Tongue coverage
    from collections import Counter
    tongue_counts = Counter()
    for rec in all_records:
        for tag in rec["tags"]:
            if tag.startswith("tongue-"):
                tongue_counts[tag] += 1
    print("\nTongue coverage:")
    for t, c in tongue_counts.most_common():
        print(f"  {t:20s} {c}")

    aug_counts = Counter(r["augmentation"] for r in all_records)
    print("\nRecord types:")
    for a, c in aug_counts.most_common():
        print(f"  {a:25s} {c}")


if __name__ == "__main__":
    main()
