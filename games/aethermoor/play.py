#!/usr/bin/env python3
"""
Aethermoor: Six Tongues Protocol — Terminal Edition
====================================================
Play the isekai RPG in your terminal. Every choice trains AI.

Controls:
  Arrow keys / W/S  : Navigate menus
  Enter / Space     : Select / Advance dialogue
  Q                 : Quit

Run: python games/aethermoor/play.py
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

# Add game to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import (
    GAME_TITLE, Character, EvoStage, GamePhase, GameState, Palette, Spell,
    Tongue, TONGUE_NAMES, TONGUE_WEIGHTS, TrainingExporter,
    calculate_damage, create_cast,
    scene_earth_morning, scene_earth_work, scene_earth_evening,
    scene_earth_night, scene_transit, scene_aethermoor_arrival,
)

# ---------------------------------------------------------------------------
# Terminal rendering helpers
# ---------------------------------------------------------------------------

# ANSI color codes
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BG_DARK = "\033[40m"
    BG_BLUE = "\033[44m"
    BG_MAG  = "\033[45m"

TONGUE_COLOR = {
    "KO": C.RED,
    "AV": C.CYAN,
    "RU": C.YELLOW,
    "CA": C.GREEN,
    "UM": C.MAGENTA,
    "DR": C.YELLOW + C.BOLD,
}


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def slow_print(text: str, delay: float = 0.02):
    """Print text character by character for RPG feel."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if delay > 0 and ch not in " \n":
            time.sleep(delay)
    print()


def draw_box(text: str, width: int = 60, color: str = C.CYAN):
    """Draw a bordered text box."""
    lines = []
    words = text.split()
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > width - 4:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}" if current else w
    if current:
        lines.append(current)

    print(f"{color}+{'-' * (width - 2)}+{C.RESET}")
    for line in lines:
        padding = width - 4 - len(line)
        print(f"{color}| {C.WHITE}{line}{' ' * padding} {color}|{C.RESET}")
    print(f"{color}+{'-' * (width - 2)}+{C.RESET}")


def draw_hp_bar(current: int, maximum: int, width: int = 20, label: str = "HP") -> str:
    """Render an HP bar."""
    ratio = current / max(maximum, 1)
    filled = int(ratio * width)
    empty = width - filled

    if ratio > 0.6:
        color = C.GREEN
    elif ratio > 0.3:
        color = C.YELLOW
    else:
        color = C.RED

    bar = f"{color}{'#' * filled}{C.DIM}{'.' * empty}{C.RESET}"
    return f"{label}: [{bar}] {current}/{maximum}"


def draw_xp_bar(proficiencies: dict, width: int = 20) -> str:
    """Render total XP bar."""
    total = sum(proficiencies.values())
    max_total = 6.0  # max across all tongues
    ratio = min(1.0, total / max_total)
    filled = int(ratio * width)
    empty = width - filled
    return f"XP: [{C.BLUE}{'=' * filled}{C.DIM}{'.' * empty}{C.RESET}] {total:.2f}/{max_total:.1f}"


def draw_party_status(party: list):
    """Show party status panel."""
    print(f"\n{C.BOLD}{C.CYAN}--- Party ---{C.RESET}")
    for char in party:
        tongue_color = TONGUE_COLOR.get(char.tongue_affinity.value, C.WHITE)
        hp = draw_hp_bar(char.stats.hp, char.stats.max_hp, 15)
        print(f"  {tongue_color}{char.name}{C.RESET} [{char.evo_stage.value}] {hp}")


def draw_tongue_proficiency(char: Character):
    """Show tongue proficiency bars."""
    print(f"\n{C.BOLD}Tongue Proficiency:{C.RESET}")
    for tongue in Tongue:
        prof = char.stats.tongue_prof.get(tongue.value, 0.0)
        bar_w = 15
        filled = int(prof * bar_w)
        empty = bar_w - filled
        color = TONGUE_COLOR.get(tongue.value, C.WHITE)
        name = TONGUE_NAMES[tongue]
        print(f"  {color}{tongue.value} ({name[:8]:>8}){C.RESET}: "
              f"[{color}{'#' * filled}{C.DIM}{'.' * empty}{C.RESET}] {prof:.1%}")


# ---------------------------------------------------------------------------
# Battle Renderer
# ---------------------------------------------------------------------------

def battle_encounter(state: GameState, enemies: list) -> bool:
    """Run a turn-based battle. Returns True if player wins."""
    clear()
    print(f"\n{C.RED}{C.BOLD}  !! BATTLE !!{C.RESET}")
    print(f"  {C.DIM}Wild encounter!{C.RESET}\n")

    # Show enemies
    for e in enemies:
        tc = TONGUE_COLOR.get(e.tongue_affinity.value, C.WHITE)
        print(f"  {tc}{C.BOLD}{e.name}{C.RESET} [{e.evo_stage.value}] "
              f"HP: {e.stats.hp}/{e.stats.max_hp}  "
              f"Tongue: {tc}{e.tongue_affinity.value}{C.RESET}")
    print()

    turn = 0
    while True:
        turn += 1
        print(f"{C.DIM}--- Turn {turn} ---{C.RESET}")

        # Player phase
        for char in state.party:
            if char.stats.hp <= 0:
                continue

            # Find alive enemy
            alive_enemies = [e for e in enemies if e.stats.hp > 0]
            if not alive_enemies:
                break

            target = alive_enemies[0]

            print(f"\n  {C.BOLD}{char.name}'s turn:{C.RESET}")
            print(f"  {draw_hp_bar(char.stats.hp, char.stats.max_hp, 15)}")

            # Show options
            options = ["Attack"]
            for i, sp in enumerate(char.spells):
                mp_ok = char.stats.mp >= sp.mp_cost
                status = "" if mp_ok else f" {C.DIM}(not enough MP){C.RESET}"
                options.append(f"{sp.name} ({sp.mp_cost} MP){status}")

            for i, opt in enumerate(options):
                print(f"    {C.YELLOW}[{i + 1}]{C.RESET} {opt}")

            # Get input
            choice = 0
            while True:
                try:
                    raw = input(f"\n  {C.CYAN}>{C.RESET} ").strip()
                    if raw.lower() == "q":
                        return False
                    choice = int(raw) - 1
                    if 0 <= choice <= len(char.spells):
                        break
                except (ValueError, EOFError):
                    pass
                print(f"  {C.DIM}Enter 1-{len(options)}{C.RESET}")

            # Execute action
            spell = char.spells[choice - 1] if choice > 0 else None
            if spell and char.stats.mp < spell.mp_cost:
                print(f"  {C.RED}Not enough MP! Basic attack instead.{C.RESET}")
                spell = None

            if spell:
                char.stats.mp -= spell.mp_cost

            dmg, msg, crit = calculate_damage(char, target, spell)
            target.stats.hp = max(0, target.stats.hp - dmg)

            # Gain tongue proficiency from using spells
            if spell:
                tongue_key = spell.tongue.value
                old_prof = char.stats.tongue_prof.get(tongue_key, 0.0)
                gain = random.uniform(0.01, 0.03)
                char.stats.tongue_prof[tongue_key] = min(1.0, old_prof + gain)
                prof_msg = f" (+{gain:.2f} {tongue_key} proficiency)"
            else:
                prof_msg = ""

            color = C.RED if crit else C.WHITE
            print(f"\n  {color}{msg}{C.RESET}{C.GREEN}{prof_msg}{C.RESET}")

            # Record training data
            state.exporter.record_battle(
                char.name, target.name,
                spell.name if spell else "Attack",
                dmg, spell.tongue.value if spell else char.tongue_affinity.value,
                "critical" if crit else "normal",
            )

            if target.stats.hp <= 0:
                print(f"  {C.GREEN}{C.BOLD}{target.name} defeated!{C.RESET}")

        # Check victory
        if all(e.stats.hp <= 0 for e in enemies):
            print(f"\n{C.GREEN}{C.BOLD}  Victory!{C.RESET}")
            # Restore some MP
            for char in state.party:
                char.stats.mp = min(char.stats.max_mp, char.stats.mp + 10)
            input(f"  {C.DIM}[Press Enter]{C.RESET}")
            return True

        # Enemy phase
        for enemy in enemies:
            if enemy.stats.hp <= 0:
                continue

            alive_party = [c for c in state.party if c.stats.hp > 0]
            if not alive_party:
                break

            target = random.choice(alive_party)
            spell = random.choice(enemy.spells) if enemy.spells and enemy.stats.mp >= 10 else None

            if spell:
                enemy.stats.mp -= spell.mp_cost

            dmg, msg, crit = calculate_damage(enemy, target, spell)
            target.stats.hp = max(0, target.stats.hp - dmg)

            color = C.RED if crit else C.MAGENTA
            print(f"\n  {color}{msg}{C.RESET}")

            if target.stats.hp <= 0:
                print(f"  {C.RED}{target.name} fainted!{C.RESET}")

        # Check defeat
        if all(c.stats.hp <= 0 for c in state.party):
            print(f"\n{C.RED}{C.BOLD}  Defeat...{C.RESET}")
            input(f"  {C.DIM}[Press Enter]{C.RESET}")
            return False

        print()


# ---------------------------------------------------------------------------
# Evolution Check
# ---------------------------------------------------------------------------

EVO_THRESHOLDS = {
    EvoStage.FRESH:    0.0,
    EvoStage.ROOKIE:   0.3,
    EvoStage.CHAMPION: 1.0,
    EvoStage.ULTIMATE: 2.5,
    EvoStage.MEGA:     4.0,
    EvoStage.ULTRA:    5.5,
}

EVO_ORDER = [EvoStage.FRESH, EvoStage.ROOKIE, EvoStage.CHAMPION,
             EvoStage.ULTIMATE, EvoStage.MEGA, EvoStage.ULTRA]


def check_evolution(char: Character, state: GameState) -> bool:
    """Check if a character should evolve. Returns True if evolved."""
    total_prof = sum(char.stats.tongue_prof.values())
    current_idx = EVO_ORDER.index(char.evo_stage)

    if current_idx >= len(EVO_ORDER) - 1:
        return False

    next_stage = EVO_ORDER[current_idx + 1]
    threshold = EVO_THRESHOLDS.get(next_stage, 999)

    if total_prof >= threshold:
        old_stage = char.evo_stage
        char.evo_stage = next_stage

        # Stat boosts on evolution
        char.stats.max_hp += 20
        char.stats.hp = char.stats.max_hp
        char.stats.max_mp += 15
        char.stats.mp = char.stats.max_mp
        char.stats.attack += 3
        char.stats.defense += 3
        char.stats.speed += 2
        char.stats.wisdom += 3

        # Record training data
        state.exporter.record_evolution(
            char.name, old_stage.value, next_stage.value,
            dict(char.stats.tongue_prof),
        )

        # Evolution animation
        clear()
        print(f"\n\n{'=' * 60}")
        print(f"{C.BOLD}{C.YELLOW}")
        print(f"     *** EVOLUTION ***")
        print()
        tc = TONGUE_COLOR.get(char.tongue_affinity.value, C.WHITE)
        print(f"     {tc}{char.name}{C.YELLOW} is evolving!")
        print()

        # ASCII evolution animation
        frames = [
            "       o       ",
            "      .O.      ",
            "     .oOo.     ",
            "    .oO*Oo.    ",
            "   .oO***Oo.   ",
            "  .oO*****Oo.  ",
            " .oO*******Oo. ",
            "  '*********'  ",
            "   '*******'   ",
            "    '*****'    ",
            "     '***'     ",
            "      '*'      ",
        ]
        for frame in frames:
            print(f"\r     {tc}{frame}{C.RESET}", end="", flush=True)
            time.sleep(0.15)

        print(f"\n\n{C.BOLD}{C.GREEN}")
        print(f"     {char.name} evolved to {next_stage.value}!")
        print(f"     HP +20, MP +15, ATK +3, DEF +3, SPD +2, WIS +3")
        print(f"{C.RESET}")
        print(f"{'=' * 60}")
        input(f"\n  {C.DIM}[Press Enter]{C.RESET}")

        return True

    return False


# ---------------------------------------------------------------------------
# Wild Encounter Generator
# ---------------------------------------------------------------------------

def generate_wild_encounter(state: GameState) -> list:
    """Generate random enemies based on current day/phase."""
    enemy_templates = [
        ("Echo Wisp", Tongue.KO, 40, 20, 8, 5, [
            Spell("Static Pulse", Tongue.KO, 12, 6, "Crackling authority burst"),
        ]),
        ("Drift Shade", Tongue.UM, 35, 25, 7, 4, [
            Spell("Shadow Veil", Tongue.UM, 10, 8, "Concealing darkness"),
        ]),
        ("Rune Beetle", Tongue.RU, 55, 10, 10, 8, [
            Spell("Shell Lock", Tongue.RU, 0, 5, "Hardens carapace"),
        ]),
        ("Phase Moth", Tongue.AV, 25, 30, 6, 3, [
            Spell("Transport Dust", Tongue.AV, 14, 10, "Teleporting spores"),
        ]),
        ("Cipher Sprite", Tongue.CA, 30, 35, 9, 4, [
            Spell("Encrypt Beam", Tongue.CA, 16, 12, "Scrambling light"),
        ]),
        ("Schema Wyrm", Tongue.DR, 50, 20, 12, 7, [
            Spell("Auth Fire", Tongue.DR, 18, 10, "Authentication flames"),
        ]),
    ]

    # Scale with day
    power_scale = 1.0 + (state.day - 1) * 0.15
    n_enemies = min(3, 1 + state.day // 3)

    enemies = []
    for _ in range(n_enemies):
        template = random.choice(enemy_templates)
        name, tongue, hp, mp, atk, dfn, spells = template

        # Determine evo stage by day
        if state.day >= 10:
            evo = EvoStage.CHAMPION
        elif state.day >= 5:
            evo = EvoStage.ROOKIE
        else:
            evo = EvoStage.FRESH

        from engine import Stats
        enemy = Character(
            name=name,
            title="Wild",
            tongue_affinity=tongue,
            evo_stage=evo,
            stats=Stats(
                hp=int(hp * power_scale),
                max_hp=int(hp * power_scale),
                mp=int(mp * power_scale),
                max_mp=int(mp * power_scale),
                attack=int(atk * power_scale),
                defense=int(dfn * power_scale),
                speed=8,
                wisdom=8,
            ),
            spells=list(spells),
            is_enemy=True,
        )
        enemies.append(enemy)

    return enemies


# ---------------------------------------------------------------------------
# Main Game Loop
# ---------------------------------------------------------------------------

def play():
    """Main game loop."""
    clear()

    # Title screen
    print(f"\n{C.BOLD}{C.MAGENTA}")
    print("  ============================================")
    print(f"  {GAME_TITLE}")
    print("  ============================================")
    print(f"{C.RESET}")
    print(f"  {C.DIM}An isekai RPG where every choice trains AI.{C.RESET}")
    print(f"  {C.DIM}Your gameplay generates training data for SCBE-AETHERMOORE.{C.RESET}")
    print()
    print(f"  {C.CYAN}Characters from the lore of Issac Davis.{C.RESET}")
    print(f"  {C.CYAN}World: Aethermoor. Magic: Six Sacred Tongues.{C.RESET}")
    print()
    print(f"  {C.YELLOW}[Enter]{C.RESET} Start")
    print(f"  {C.YELLOW}[Q]{C.RESET}     Quit")

    raw = input(f"\n  {C.CYAN}>{C.RESET} ").strip().lower()
    if raw == "q":
        return

    # Initialize game
    cast = create_cast()
    state = GameState()
    state.party = [cast["izack"]]
    state.exporter = TrainingExporter()

    # Scene sequence
    scenes = [
        (GamePhase.EARTH_MORNING, scene_earth_morning),
        (GamePhase.EARTH_WORK, scene_earth_work),
        (GamePhase.EARTH_EVENING, scene_earth_evening),
        (GamePhase.EARTH_NIGHT, scene_earth_night),
        (GamePhase.TRANSIT, scene_transit),
        (GamePhase.AETHERMOOR, scene_aethermoor_arrival),
    ]

    scene_idx = 0
    running = True

    while running and scene_idx < len(scenes):
        phase, scene_fn = scenes[scene_idx]
        state.phase = phase
        state.clear()
        scene_fn(state)

        # Render scene
        clear()

        # Location header
        bg = C.BG_MAG if "aethermoor" in state.location.lower() else C.BG_DARK
        print(f"\n  {bg}{C.BOLD} {state.location} {C.RESET}  "
              f"{C.DIM}[{state.time_of_day}]{C.RESET}")

        draw_party_status(state.party)
        print()

        # Display dialogue
        for line in state.dialogue_queue:
            if line.startswith("POLLY:") or line.startswith("CLAY:"):
                speaker = line.split(":")[0]
                rest = ":".join(line.split(":")[1:])
                color = C.RED if speaker == "POLLY" else C.YELLOW
                print(f"  {color}{C.BOLD}{speaker}:{C.RESET}{rest}")
            elif line == "...":
                print(f"  {C.DIM}...{C.RESET}")
                time.sleep(0.5)
            else:
                draw_box(line, 60)
            time.sleep(0.3)

        # Show choices
        if state.choices:
            print(f"\n  {C.BOLD}What do you do?{C.RESET}")
            for i, (label, action) in enumerate(state.choices):
                print(f"    {C.YELLOW}[{i + 1}]{C.RESET} {label}")

            choice_idx = 0
            while True:
                try:
                    raw = input(f"\n  {C.CYAN}>{C.RESET} ").strip()
                    if raw.lower() == "q":
                        running = False
                        break
                    choice_idx = int(raw) - 1
                    if 0 <= choice_idx < len(state.choices):
                        break
                except (ValueError, EOFError):
                    pass
                print(f"  {C.DIM}Enter 1-{len(state.choices)}{C.RESET}")

            if not running:
                break

            # Record the choice as training data
            label, action = state.choices[choice_idx]
            alternatives = [l for l, a in state.choices if a != action]
            state.exporter.record_choice(
                context=state.dialogue_queue[-1] if state.dialogue_queue else state.location,
                choice_made=label,
                alternatives=alternatives,
                outcome=f"Player chose '{label}' at {state.location}.",
                category=f"isekai_{phase.name.lower()}",
            )

            # Handle special actions
            if action == "trace_anomaly":
                state.party[0].stats.tongue_prof["CA"] = min(
                    1.0, state.party[0].stats.tongue_prof["CA"] + 0.05)
                print(f"\n  {C.GREEN}+0.05 CA (Cassisivadan) proficiency!{C.RESET}")
                time.sleep(0.5)
            elif action == "read_book":
                for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
                    state.party[0].stats.tongue_prof[tongue] = max(
                        0.05, state.party[0].stats.tongue_prof[tongue])
                print(f"\n  {C.GREEN}You sense all Six Tongues awakening...{C.RESET}")
                time.sleep(0.5)
            elif action in ("intent_understand", "intent_protect", "intent_create"):
                # Set primary tongue based on intent
                if action == "intent_understand":
                    state.party[0].stats.tongue_prof["CA"] += 0.1
                    print(f"\n  {C.GREEN}+0.10 CA proficiency. Knowledge is your path.{C.RESET}")
                elif action == "intent_protect":
                    state.party[0].stats.tongue_prof["RU"] += 0.1
                    print(f"\n  {C.GREEN}+0.10 RU proficiency. The shield holds.{C.RESET}")
                elif action == "intent_create":
                    state.party[0].stats.tongue_prof["DR"] += 0.1
                    print(f"\n  {C.GREEN}+0.10 DR proficiency. Creation flows through you.{C.RESET}")
                time.sleep(0.5)

        else:
            input(f"\n  {C.DIM}[Press Enter to continue]{C.RESET}")

        # Check for evolution
        for char in state.party:
            check_evolution(char, state)

        scene_idx += 1

    # Post-arrival: Aethermoor exploration loop
    if running and scene_idx >= len(scenes):
        print(f"\n{C.BOLD}{C.MAGENTA}  === Aethermoor Exploration Phase ==={C.RESET}")
        print(f"  {C.DIM}Wild encounters with Six Tongue creatures await.{C.RESET}")
        time.sleep(1)

        exploration_day = 0
        while running:
            exploration_day += 1
            state.day += 1

            # Random encounter
            if random.random() < 0.7:
                enemies = generate_wild_encounter(state)
                enemy_names = ", ".join(e.name for e in enemies)
                print(f"\n  {C.RED}! Wild {enemy_names} appeared!{C.RESET}")
                time.sleep(0.5)

                won = battle_encounter(state, enemies)
                if not won:
                    print(f"\n  {C.RED}Game Over. Day {state.day}.{C.RESET}")
                    break

                # Check evolution after battle
                for char in state.party:
                    check_evolution(char, state)

            # Exploration event
            clear()
            print(f"\n  {C.BG_MAG}{C.BOLD} Aethermoor - Day {state.day} {C.RESET}")
            draw_party_status(state.party)
            draw_tongue_proficiency(state.party[0])
            print(f"\n  {draw_xp_bar(state.party[0].stats.tongue_prof)}")

            events = [
                ("You find a Tongue Crystal (KO)!", "KO", 0.08),
                ("An ancient scroll teaches Avali transport runes.", "AV", 0.06),
                ("Clay discovers Runethic policy stones.", "RU", 0.07),
                ("Polly deciphers a Cassisivadan cipher.", "CA", 0.05),
                ("A shadow teaches Umbroth secrets.", "UM", 0.09),
                ("Draumric schema patterns emerge in the stars.", "DR", 0.06),
            ]
            event = random.choice(events)
            msg, tongue, gain = event
            print(f"\n  {C.GREEN}{msg}{C.RESET}")
            state.party[0].stats.tongue_prof[tongue] = min(
                1.0, state.party[0].stats.tongue_prof[tongue] + gain)
            print(f"  {TONGUE_COLOR[tongue]}+{gain:.2f} {tongue} proficiency!{C.RESET}")

            print(f"\n  {C.YELLOW}[1]{C.RESET} Continue exploring")
            print(f"  {C.YELLOW}[2]{C.RESET} Rest (heal party)")
            print(f"  {C.YELLOW}[3]{C.RESET} Save & Quit")

            try:
                raw = input(f"\n  {C.CYAN}>{C.RESET} ").strip()
            except EOFError:
                break

            if raw == "2":
                for char in state.party:
                    char.stats.hp = char.stats.max_hp
                    char.stats.mp = char.stats.max_mp
                print(f"  {C.GREEN}Party fully healed!{C.RESET}")
                time.sleep(0.5)
            elif raw == "3" or raw.lower() == "q":
                running = False

    # Save training data
    path = state.exporter.save()
    total = state.exporter.total_pairs
    print(f"\n{'=' * 60}")
    print(f"  {C.BOLD}Session Complete!{C.RESET}")
    print(f"  Days survived: {state.day}")
    print(f"  Training pairs generated: {C.GREEN}{total}{C.RESET}")
    print(f"  Saved to: {C.CYAN}{path}{C.RESET}")
    print(f"\n  {C.DIM}These pairs will train the SCBE-AETHERMOORE AI.{C.RESET}")
    print(f"  {C.DIM}Every choice you made teaches the next generation.{C.RESET}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    play()
