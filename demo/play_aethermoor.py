#!/usr/bin/env python3
"""
Aethermoor: Six Tongues Protocol — Plain Text Adventure
=========================================================
A playable text adventure that demonstrates the full 14-layer SCBE pipeline.
Every choice trains AI. AI companions play alongside you.

Run:  python demo/play_aethermoor.py

Controls:
  1-7   : Select a choice
  o     : View origin cards for current party
  q     : Quit and save training data
"""
from __future__ import annotations

import json
import os
import sys
import time
import hashlib
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Add demo to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene_library import get_all_scenes, get_scene_order, EScene, EChoice
from companion_ai import CompanionAI, CompanionThought
from kary_kernel import KarySimplexKernel
from origin_creator import create_origins, origin_to_card, origin_to_sft_record

# ── Adapter: bridge EChoice fields to what CompanionAI expects ────────────────

RISK_TO_FLOAT = {"safe": 0.1, "moderate": 0.35, "risky": 0.65, "dangerous": 0.9}

class ChoiceAdapter:
    """Wraps EChoice so companion_ai sees .choice_id and .risk as float."""
    __slots__ = ("_ch",)
    def __init__(self, ch: EChoice):
        self._ch = ch
    @property
    def choice_id(self): return self._ch.cid
    @property
    def tongue(self): return self._ch.tongue
    @property
    def risk(self): return RISK_TO_FLOAT.get(self._ch.risk, 0.3)
    @property
    def label(self): return self._ch.label
    def __getattr__(self, name):
        return getattr(self._ch, name)

# ── ANSI Colors ──────────────────────────────────────────────────────────────

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

TONGUE_COLOR = {
    "KO": C.RED,    "AV": C.CYAN,   "RU": C.YELLOW,
    "CA": C.GREEN,  "UM": C.MAGENTA, "DR": C.YELLOW + C.BOLD,
    "MULTI": C.WHITE,
}

TONGUE_NAMES = {
    "KO": "Kor'aelin",  "AV": "Avali",       "RU": "Runethic",
    "CA": "Cassisivadan", "UM": "Umbroth",    "DR": "Draumric",
}

TONGUE_EMOTIONS = {
    "KO": "collaborative love, protective tenderness",
    "AV": "hopeful openness, gentle curiosity",
    "RU": "solemn reverence, ancestral memory",
    "CA": "playful joy, creative wonder",
    "UM": "honest melancholy, courage in darkness",
    "DR": "fierce pride, shared strength",
}

TONGUE_BODY = {
    "KO": "Warmth in the chest, like a steady heartbeat connecting to others",
    "AV": "Lightness in the shoulders, like a soft breeze inviting you forward",
    "RU": "Weight in the bones, carrying the hands of those who came before",
    "CA": "Spark in the belly, like laughter bubbling up",
    "UM": "Quiet ache in the throat, holding a necessary truth",
    "DR": "Heat in the hands and spine, like a hammer building something lasting",
}

TONGUE_SONGS = {
    "KO": ("Sil'thara nav'een", "We grow together through difference"),
    "AV": ("Avela toma", "Take peace, hope grows"),
    "RU": ("Vel'ar nos med'ar thular syn'ar nuu", "Together we guard ancient wisdom"),
    "CA": ("Nos runa sapi spira'zuni nunc", "We run wise spiral-fun now"),
    "UM": ("Nar'shul", "I remember the dark truth"),
    "DR": ("Grondrak", "Forge it with heart"),
}

TONGUE_SOCIETIES = {
    "KO": "Harmony Singers Guild, Heart-Weaver families",
    "AV": "Diplomatic Corps, Bridge Districts of Avalon",
    "RU": "Memory Keepers Guild, World Tree archivists",
    "CA": "Growth Shapers, Pattern Dancers, gnomish inventors",
    "UM": "Shadow Walkers (scouts & therapists), grief counselors",
    "DR": "Forge Masters, builders of living architecture",
}

LAYER_NAMES = {
    1: "Intent",      2: "Routing",     3: "Context",    4: "Memory",
    5: "Constraints",  6: "Policy",      7: "Compute",    8: "Encrypt",
    9: "Spectral",    10: "Quantum",    11: "Schema",    12: "Auth",
    13: "Governance",  14: "Integration",
}

# ── Game State ────────────────────────────────────────────────────────────────

@dataclass
class PlayerState:
    tongue_prof: Dict[str, float] = field(default_factory=lambda: {
        "KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0
    })
    scene_count: int = 0
    choices_made: List[Dict] = field(default_factory=list)
    sft_pairs: List[Dict] = field(default_factory=list)
    dpo_pairs: List[Dict] = field(default_factory=list)
    active_layers: set = field(default_factory=set)
    party: List[str] = field(default_factory=lambda: ["Polly", "Clay"])

    @property
    def level(self) -> int:
        return max(1, int(sum(self.tongue_prof.values()) * 5) + 1)

    @property
    def dominant_tongue(self) -> str:
        if not any(v > 0 for v in self.tongue_prof.values()):
            return "AV"
        return max(self.tongue_prof, key=self.tongue_prof.get)


# ── Display Functions ─────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_header(scene: EScene, state: PlayerState):
    """Print the scene header with location and mood."""
    w = 72
    print(f"\n{C.CYAN}{'=' * w}{C.RESET}")
    mood_color = {
        "hopeful": C.GREEN, "tense": C.RED, "peaceful": C.BLUE,
        "mysterious": C.MAGENTA, "battle": C.RED, "triumphant": C.YELLOW,
    }.get(scene.mood, C.WHITE)
    print(f"  {C.BOLD}{mood_color}{scene.title}{C.RESET}")
    print(f"  {C.DIM}{scene.location} | {scene.time} | Mood: {scene.mood}{C.RESET}")
    print(f"{C.CYAN}{'=' * w}{C.RESET}")


def print_status_bar(state: PlayerState):
    """Print compact status bar."""
    tongues = []
    for t in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        v = state.tongue_prof[t]
        col = TONGUE_COLOR[t]
        filled = int(v * 10)
        bar = "#" * filled + "." * (10 - filled)
        tongues.append(f"{col}{t}{C.RESET}[{col}{bar}{C.RESET}]")
    print(f"\n  {' '.join(tongues)}")
    print(f"  {C.DIM}Lvl {state.level} | Party: {', '.join(state.party)} | "
          f"SFT: {len(state.sft_pairs)} | DPO: {len(state.dpo_pairs)}{C.RESET}")


def print_layer_activity(active_layers: set):
    """Print which SCBE layers are currently active."""
    parts = []
    for i in range(1, 15):
        name = LAYER_NAMES[i]
        if i in active_layers:
            # Color by tongue region
            if i <= 2: col = TONGUE_COLOR["KO"]
            elif i <= 4: col = TONGUE_COLOR["AV"]
            elif i <= 6: col = TONGUE_COLOR["RU"]
            elif i <= 8: col = TONGUE_COLOR["CA"]
            elif i <= 10: col = TONGUE_COLOR["UM"]
            elif i <= 12: col = TONGUE_COLOR["DR"]
            else: col = C.YELLOW
            parts.append(f"{col}{C.BOLD}{i:>2}.{name[:6]}{C.RESET}")
        else:
            parts.append(f"{C.DIM}{i:>2}.{name[:6]}{C.RESET}")

    print(f"\n  {C.BOLD}SCBE Pipeline:{C.RESET}")
    # Print in two rows of 7
    print(f"  {' '.join(parts[:7])}")
    print(f"  {' '.join(parts[7:])}")


def print_narrative(text: str):
    """Print scene narrative with wrapping."""
    w = 68
    words = text.split()
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > w:
            print(f"  {line}")
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        print(f"  {line}")


def print_choices(choices: List[EChoice]):
    """Print the choice menu with tongue indicators and layer badges."""
    print(f"\n  {C.BOLD}What do you do?{C.RESET}")
    print(f"  {C.DIM}{'─' * 66}{C.RESET}")

    for i, ch in enumerate(choices):
        col = TONGUE_COLOR.get(ch.tongue, C.WHITE)
        risk_icon = {"safe": " ", "moderate": "~", "risky": "!", "dangerous": "!!"}.get(ch.risk, " ")
        risk_col = {"safe": C.GREEN, "moderate": C.YELLOW, "risky": C.RED, "dangerous": C.RED + C.BOLD}.get(ch.risk, C.WHITE)

        # Layer badges
        layer_badges = " ".join(f"{C.DIM}L{lt.layer}{C.RESET}" for lt in ch.layers)

        # Tongue name
        tongue_name = TONGUE_NAMES.get(ch.tongue, ch.tongue)

        print(f"    {C.YELLOW}[{i+1}]{C.RESET} {col}[{ch.tongue}]{C.RESET} {ch.label}")
        print(f"        {C.DIM}Tongue: {tongue_name} | {layer_badges} | {risk_col}{risk_icon}{ch.risk}{C.RESET}")


def print_companion_thoughts(thoughts: Dict[str, List[CompanionThought]], choices: List[EChoice]):
    """Print what companions think about the choices."""
    print(f"\n  {C.BOLD}AI Companion Thoughts:{C.RESET}")
    print(f"  {C.DIM}{'─' * 66}{C.RESET}")

    for name, thought_list in thoughts.items():
        if not thought_list:
            continue
        best = max(thought_list, key=lambda t: t.preference_score)
        # Find the choice label
        choice_label = ""
        for ch in choices:
            if ch.cid == best.choice_id:
                choice_label = ch.label
                break

        col = TONGUE_COLOR.get(best.tongue_alignment, C.WHITE)
        print(f"    {col}{name}{C.RESET}: {C.DIM}\"{best.reasoning}\"{C.RESET}")
        print(f"      {C.DIM}Recommends: [{best.choice_id}] {choice_label} "
              f"(confidence: {best.preference_score:.0%}){C.RESET}")


def print_kernel_state(kernel: KarySimplexKernel):
    """Print the K-ary kernel's current governance state."""
    probs = kernel.simplex_point
    labels = kernel.labels
    safety = kernel.to_binary_safety()

    parts = []
    for label, p in zip(labels, probs):
        if p > 0.3:
            parts.append(f"{C.BOLD}{label}:{p:.0%}{C.RESET}")
        else:
            parts.append(f"{C.DIM}{label}:{p:.0%}{C.RESET}")

    tongue = kernel.tongue_label() or "—"
    tcol = TONGUE_COLOR.get(tongue, C.WHITE)

    print(f"\n  {C.BOLD}Governance Kernel (K=4):{C.RESET} "
          f"{' '.join(parts)} | Safety: {safety:.2f} | Tongue: {tcol}{tongue}{C.RESET}")


def print_choice_result(choice: EChoice, state: PlayerState, kernel: KarySimplexKernel):
    """Print the result of a choice."""
    col = TONGUE_COLOR.get(choice.tongue, C.WHITE)
    tongue_name = TONGUE_NAMES.get(choice.tongue, choice.tongue)
    emotion = TONGUE_EMOTIONS.get(choice.tongue, "")

    print(f"\n  {C.CYAN}{'─' * 66}{C.RESET}")
    print(f"  {C.BOLD}You chose:{C.RESET} {col}{choice.label}{C.RESET}")
    print(f"  {C.DIM}The {tongue_name} tongue resonates — {emotion}{C.RESET}")

    # Body feeling
    body = TONGUE_BODY.get(choice.tongue, "")
    if body:
        print(f"  {col}  {body}{C.RESET}")

    # Song echo
    song = TONGUE_SONGS.get(choice.tongue)
    if song:
        print(f"  {col}  ~~ \"{song[0]}\" ~~ {C.DIM}{song[1]}{C.RESET}")

    # Society connection
    soc = TONGUE_SOCIETIES.get(choice.tongue)
    if soc:
        print(f"  {C.DIM}  Society: {soc}{C.RESET}")

    # Show layer activations
    print()
    for lt in choice.layers:
        layer_col = C.GREEN
        print(f"    {layer_col}[Layer {lt.layer}: {lt.name}]{C.RESET} {C.DIM}{lt.desc}{C.RESET}")

    # Show stat gains
    for tongue, gain in choice.stats.items():
        tcol = TONGUE_COLOR.get(tongue, C.WHITE)
        print(f"    {tcol}+{gain:.2f} {tongue} ({TONGUE_NAMES.get(tongue, tongue)}) proficiency{C.RESET}")

    # Show companion opinions on YOUR choice
    if choice.opinions:
        print(f"\n  {C.DIM}Companions react:{C.RESET}")
        for name, opinion in choice.opinions.items():
            ncol = C.WHITE
            for t, chars in [("KO", ["Polly"]), ("RU", ["Clay"]), ("AV", ["Eldrin"]),
                             ("UM", ["Aria", "Kael"]), ("DR", ["Zara"])]:
                if name in chars:
                    ncol = TONGUE_COLOR[t]
                    break
            print(f"    {ncol}{name}{C.RESET}: {C.DIM}\"{opinion}\"{C.RESET}")


def print_consensus(consensus_choice: str, agreement: float, choices: List[EChoice]):
    """Print party consensus result."""
    choice_label = ""
    for ch in choices:
        if ch.cid == consensus_choice:
            choice_label = ch.label
            break

    if agreement >= 0.8:
        icon, msg = C.GREEN, "Strong consensus!"
    elif agreement >= 0.5:
        icon, msg = C.YELLOW, "Majority agrees."
    else:
        icon, msg = C.RED, "Party is divided."

    print(f"  {icon}Party consensus ({agreement:.0%}): {choice_label} — {msg}{C.RESET}")


def print_party_origins(party: List[str], origins: Dict[str, object]):
    """Render compact origin cards for the current party."""
    print(f"\n  {C.BOLD}Origin Forge:{C.RESET}")
    print(f"  {C.DIM}{'─' * 66}{C.RESET}")
    for name in party:
        origin = origins.get(name)
        if origin is None:
            continue
        card = origin_to_card(origin).splitlines()
        if not card:
            continue
        print(f"  {C.CYAN}{card[0]}{C.RESET}")
        for line in card[1:]:
            print(f"    {C.DIM}{line.strip()}{C.RESET}")


# ── Training Data Generation ─────────────────────────────────────────────────

def generate_sft(scene: EScene, choice: EChoice, state: PlayerState) -> Dict:
    """Generate an SFT training pair from a player choice."""
    return {
        "instruction": f"In the world of Aethermoor, {scene.text} "
                      f"The player has {len(scene.choices)} options. What should they do?",
        "response": f"I choose to: {choice.label}. "
                   f"This exercises SCBE layers {[lt.layer for lt in choice.layers]} "
                   f"using the {TONGUE_NAMES.get(choice.tongue, choice.tongue)} tongue. "
                   f"The emotional resonance is {TONGUE_EMOTIONS.get(choice.tongue, 'balanced')}.",
        "metadata": {
            "source": "aethermoor_game",
            "scene": scene.sid,
            "tongue": choice.tongue,
            "layers": [lt.layer for lt in choice.layers],
            "risk": choice.risk,
            "player_level": state.level,
        }
    }


def generate_dpo(scene: EScene, player_choice: EChoice,
                 companion_choice_id: str, companion_name: str) -> Optional[Dict]:
    """Generate a DPO pair when player disagrees with companion."""
    if player_choice.cid == companion_choice_id:
        return None
    comp_choice = None
    for ch in scene.choices:
        if ch.cid == companion_choice_id:
            comp_choice = ch
            break
    if not comp_choice:
        return None

    return {
        "prompt": f"In Aethermoor: {scene.text}",
        "chosen": f"I choose: {player_choice.label} ({player_choice.tongue} tongue, "
                 f"layers {[lt.layer for lt in player_choice.layers]})",
        "rejected": f"{companion_name} preferred: {comp_choice.label} ({comp_choice.tongue} tongue, "
                   f"layers {[lt.layer for lt in comp_choice.layers]})",
        "metadata": {
            "source": "aethermoor_dpo",
            "scene": scene.sid,
            "companion": companion_name,
        }
    }


# ── Main Game Loop ────────────────────────────────────────────────────────────

def play():
    """Main game loop."""
    scenes = get_all_scenes()
    scene_order = get_scene_order()
    companion_ai = CompanionAI()
    kernel = KarySimplexKernel(k=4, temperature=0.8)
    state = PlayerState()
    forced_tongues = {name: profile.get("affinity", "AV") for name, profile in companion_ai.profiles.items()}
    forced_tongues["Izack"] = "AV"
    origins = create_origins(["Izack"] + state.party, seed="aethermoor-origin-v1", forced_tongues=forced_tongues)

    # Title screen
    clear()
    print(f"""
{C.MAGENTA}{C.BOLD}
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     AETHERMOOR: SIX TONGUES PROTOCOL                     ║
    ║                                                          ║
    ║     A text adventure where every choice trains AI.       ║
    ║     AI companions play alongside you.                    ║
    ║     The 14-layer SCBE pipeline governs reality.          ║
    ║                                                          ║
    ║     33 scenes · 161 choices · 6 Sacred Tongues           ║
    ║     K-ary Simplex Kernel governance                      ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
{C.RESET}
    {C.DIM}The Six Sacred Tongues — Emotional Architectures:{C.RESET}

    {TONGUE_COLOR['KO']}KO — Kor'aelin (Heart-Eternal){C.RESET}
      {C.DIM}Collaborative love. "Sil'thara nav'een" — We grow together{C.RESET}
    {TONGUE_COLOR['AV']}AV — Avali (Common Tongue){C.RESET}
      {C.DIM}Hopeful openness. "Avela toma" — Take peace, hope grows{C.RESET}
    {TONGUE_COLOR['RU']}RU — Runethic (Ancient Tongue){C.RESET}
      {C.DIM}Ancestral memory. "Vel'ar nos med'ar..." — We guard wisdom{C.RESET}
    {TONGUE_COLOR['CA']}CA — Cassisivadan (Nature's Speech){C.RESET}
      {C.DIM}Playful wonder. "Nos runa sapi spira'zuni nunc" — Spiral-fun!{C.RESET}
    {TONGUE_COLOR['UM']}UM — Umbroth (Shadow Tongue){C.RESET}
      {C.DIM}Courage in darkness. "Nar'shul" — I remember the dark truth{C.RESET}
    {TONGUE_COLOR['DR']}DR — Draumric (Forge Tongue){C.RESET}
      {C.DIM}Fierce creation. "Grondrak" — Forge it with heart{C.RESET}

    {C.YELLOW}[Enter]{C.RESET} Begin your journey
    {C.YELLOW}[O]{C.RESET}     View origin cards
    {C.YELLOW}[Q]{C.RESET}     Quit
""")

    while True:
        try:
            raw = input(f"  {C.CYAN}>{C.RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return

        if raw == "q":
            return
        if raw == "o":
            clear()
            print(f"\n  {C.BOLD}Aethermoor Character Creator — Canon Origins{C.RESET}")
            print_party_origins(["Izack"] + state.party, origins)
            print(f"\n  {C.DIM}[Press Enter to return to title]{C.RESET}")
            try:
                input(f"  {C.CYAN}>{C.RESET} ")
            except (EOFError, KeyboardInterrupt):
                return
            clear()
            print(f"""
{C.MAGENTA}{C.BOLD}
    ╔══════════════════════════════════════════════════════════╗
    ║     AETHERMOOR: SIX TONGUES PROTOCOL                     ║
    ╚══════════════════════════════════════════════════════════╝
{C.RESET}
    {C.YELLOW}[Enter]{C.RESET} Begin your journey
    {C.YELLOW}[O]{C.RESET}     View origin cards
    {C.YELLOW}[Q]{C.RESET}     Quit
""")
            continue
        break

    # Game loop
    scene_idx = 0
    running = True

    while running and scene_idx < len(scene_order):
        scene_id = scene_order[scene_idx]
        scene = scenes.get(scene_id)
        if not scene:
            scene_idx += 1
            continue

        state.scene_count += 1
        clear()

        # ── Render Scene ──
        print_header(scene, state)
        print_status_bar(state)

        # Activate layers based on scene
        state.active_layers = set()
        for ch in scene.choices:
            for lt in ch.layers:
                state.active_layers.add(lt.layer)
        print_layer_activity(state.active_layers)

        # Narrative
        print()
        print_narrative(scene.text)

        # Characters present
        if scene.chars:
            chars_str = ", ".join(scene.chars)
            print(f"\n  {C.DIM}Present: {chars_str}{C.RESET}")

        # If no choices (narrative-only), just advance
        if not scene.choices:
            print(f"\n  {C.DIM}[Press Enter to continue]{C.RESET}")
            try:
                input(f"  {C.CYAN}>{C.RESET} ")
            except (EOFError, KeyboardInterrupt):
                running = False
                break
            scene_idx += 1
            continue

        # ── K-ary Kernel Assessment ──
        # Feed scene context into the kernel
        avg_risk = {"safe": 0.1, "moderate": 0.3, "risky": 0.6, "dangerous": 0.9}
        scene_risk = sum(avg_risk.get(ch.risk, 0.2) for ch in scene.choices) / len(scene.choices)
        depth = min(1.0, state.scene_count / 33)
        intent = 0.3 + sum(state.tongue_prof.values()) * 0.1
        kernel.step(depth=depth, vulnerability=scene_risk, pressure=0.3, intent=min(1.0, intent))
        print_kernel_state(kernel)

        # ── AI Companion Thoughts ──
        adapted_choices = [ChoiceAdapter(ch) for ch in scene.choices]
        thoughts = companion_ai.evaluate_choices(scene.sid, adapted_choices, state.party)
        print_companion_thoughts(thoughts, scene.choices)

        # ── Party Consensus ──
        consensus_cid, agreement = companion_ai.get_party_consensus(scene.sid, adapted_choices, state.party)
        print_consensus(consensus_cid, agreement, scene.choices)

        # ── Display Choices ──
        print_choices(scene.choices)

        # ── Get Player Input ──
        choice_idx = -1
        while choice_idx < 0:
            try:
                raw = input(f"\n  {C.CYAN}>{C.RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                running = False
                break

            if raw.lower() == "q":
                running = False
                break
            if raw.lower() == "o":
                clear()
                print_header(scene, state)
                print_status_bar(state)
                print_party_origins(["Izack"] + state.party, origins)
                print(f"\n  {C.DIM}[Press Enter to return to choices]{C.RESET}")
                try:
                    input(f"  {C.CYAN}>{C.RESET} ")
                except (EOFError, KeyboardInterrupt):
                    running = False
                    break
                clear()
                print_header(scene, state)
                print_status_bar(state)
                print_layer_activity(state.active_layers)
                print()
                print_narrative(scene.text)
                if scene.chars:
                    chars_str = ", ".join(scene.chars)
                    print(f"\n  {C.DIM}Present: {chars_str}{C.RESET}")
                print_kernel_state(kernel)
                print_companion_thoughts(thoughts, scene.choices)
                print_consensus(consensus_cid, agreement, scene.choices)
                print_choices(scene.choices)
                continue

            try:
                choice_idx = int(raw) - 1
                if choice_idx < 0 or choice_idx >= len(scene.choices):
                    print(f"  {C.DIM}Enter 1-{len(scene.choices)}, O for origins, or Q to quit{C.RESET}")
                    choice_idx = -1
            except ValueError:
                print(f"  {C.DIM}Enter 1-{len(scene.choices)}, O for origins, or Q to quit{C.RESET}")

        if not running:
            break

        # ── Process Choice ──
        chosen = scene.choices[choice_idx]

        # Apply stat effects
        for tongue, gain in chosen.stats.items():
            state.tongue_prof[tongue] = min(1.0, state.tongue_prof.get(tongue, 0.0) + gain)

        # Add party members based on scene
        if scene.sid == "transit_landing" and "Eldrin" not in state.party:
            state.party.append("Eldrin")
        if scene.sid == "academy_arrival":
            for c in ["Aria", "Zara", "Kael"]:
                if c not in state.party:
                    state.party.append(c)

        missing_origins = [name for name in state.party if name not in origins]
        if missing_origins:
            forced_subset = {name: forced_tongues.get(name, "AV") for name in missing_origins}
            origins.update(create_origins(missing_origins, seed="aethermoor-origin-v1", forced_tongues=forced_subset))

        # Generate training data
        sft = generate_sft(scene, chosen, state)
        state.sft_pairs.append(sft)

        # Generate DPO pairs from companion disagreements
        for name, thought_list in thoughts.items():
            if thought_list:
                best = max(thought_list, key=lambda t: t.preference_score)
                # best.choice_id comes from adapter (= EChoice.cid)
                dpo = generate_dpo(scene, chosen, best.choice_id, name)
                if dpo:
                    state.dpo_pairs.append(dpo)

        # Record choice
        state.choices_made.append({
            "scene": scene.sid,
            "choice": chosen.cid,
            "tongue": chosen.tongue,
            "layers": [lt.layer for lt in chosen.layers],
        })

        # Show result
        print_choice_result(chosen, state, kernel)

        # Pause before next scene
        print(f"\n  {C.DIM}[Press Enter to continue]{C.RESET}")
        try:
            input(f"  {C.CYAN}>{C.RESET} ")
        except (EOFError, KeyboardInterrupt):
            running = False
            break

        # Advance to next scene (follow choice's next_scene if it exists in order)
        next_sid = chosen.next_scene
        if next_sid in scenes:
            # Jump to that scene in the order
            if next_sid in scene_order:
                scene_idx = scene_order.index(next_sid)
            else:
                scene_idx += 1
        else:
            scene_idx += 1

    # ── End Screen ──
    clear()
    print(f"""
{C.MAGENTA}{C.BOLD}
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     JOURNEY COMPLETE                                     ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
{C.RESET}""")

    print(f"  {C.BOLD}Session Summary:{C.RESET}")
    print(f"  Scenes visited: {state.scene_count}")
    print(f"  Player Level:   {state.level}")
    print(f"  Party:          {', '.join(state.party)}")
    print()

    # Tongue proficiency final
    print(f"  {C.BOLD}Final Tongue Proficiency:{C.RESET}")
    for t in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        v = state.tongue_prof[t]
        col = TONGUE_COLOR[t]
        filled = int(v * 20)
        bar = "#" * filled + "." * (20 - filled)
        name = TONGUE_NAMES[t]
        emotion = TONGUE_EMOTIONS[t]
        print(f"    {col}{t} ({name:>13}){C.RESET}: [{col}{bar}{C.RESET}] {v:.0%}")
        print(f"      {C.DIM}{emotion}{C.RESET}")

    dom = state.dominant_tongue
    print(f"\n  {C.BOLD}Your dominant tongue: {TONGUE_COLOR[dom]}{dom} — {TONGUE_NAMES[dom]}{C.RESET}")
    print(f"  {C.DIM}{TONGUE_EMOTIONS[dom]}{C.RESET}")

    # Training data summary
    print(f"\n  {C.BOLD}Training Data Generated:{C.RESET}")
    print(f"    SFT pairs:  {C.GREEN}{len(state.sft_pairs)}{C.RESET}")
    print(f"    DPO pairs:  {C.GREEN}{len(state.dpo_pairs)}{C.RESET}")
    print(f"    Origin cards: {C.GREEN}{len([n for n in ['Izack'] + state.party if n in origins])}{C.RESET}")
    print(f"    Total:      {C.GREEN}{len(state.sft_pairs) + len(state.dpo_pairs)}{C.RESET}")

    # Save training data
    out_dir = Path(__file__).resolve().parent / "training_output"
    out_dir.mkdir(exist_ok=True)

    session_hash = hashlib.md5(json.dumps(state.choices_made).encode()).hexdigest()[:8]

    sft_path = out_dir / f"sft_aethermoor_{session_hash}.jsonl"
    with open(sft_path, "w", encoding="utf-8") as f:
        for pair in state.sft_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    dpo_path = out_dir / f"dpo_aethermoor_{session_hash}.jsonl"
    with open(dpo_path, "w", encoding="utf-8") as f:
        for pair in state.dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    active_origin_names = ["Izack"] + [n for n in state.party if n != "Izack"]
    active_origin_objs = [origins[name] for name in active_origin_names if name in origins]

    origin_path = out_dir / f"origins_aethermoor_{session_hash}.json"
    with open(origin_path, "w", encoding="utf-8") as f:
        json.dump([origin.to_dict() for origin in active_origin_objs], f, ensure_ascii=False, indent=2)

    origin_sft_path = out_dir / f"origin_sft_aethermoor_{session_hash}.jsonl"
    with open(origin_sft_path, "w", encoding="utf-8") as f:
        for origin in active_origin_objs:
            f.write(json.dumps(origin_to_sft_record(origin), ensure_ascii=False) + "\n")

    print(f"\n  {C.BOLD}Saved:{C.RESET}")
    print(f"    {C.CYAN}{sft_path}{C.RESET}")
    print(f"    {C.CYAN}{dpo_path}{C.RESET}")
    print(f"    {C.CYAN}{origin_path}{C.RESET}")
    print(f"    {C.CYAN}{origin_sft_path}{C.RESET}")
    print(f"\n  {C.DIM}Every choice you made teaches the next generation of AI.{C.RESET}")
    print(f"  {C.DIM}Thank you for playing Aethermoor.{C.RESET}\n")

    # Kernel final state
    print(f"  {C.BOLD}Final Governance State:{C.RESET}")
    print(f"  {kernel.render_simplex_ascii(40)}")
    print(f"  {C.DIM}Binary safety score: {kernel.to_binary_safety():.3f}{C.RESET}")
    print()


if __name__ == "__main__":
    play()
