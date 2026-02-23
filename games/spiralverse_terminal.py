#!/usr/bin/env python3
"""
Spiralverse Terminal — Play SCBE governance games in the shell.

A hybrid interactive fiction + code REPL that:
- Plays Twee-format branching narrative games
- Tracks Sacred Tongue stats (KO/AV/RU/CA/DR/UM)
- Logs every decision as SFT training data for the Ouroboros loop
- Drops into a Python/shell REPL on command
- Runs SCBE tools (tongue encoding, seal verification, governance checks)

Usage:
    python games/spiralverse_terminal.py
    python games/spiralverse_terminal.py --game training-data/games/governance_simulator/governance_simulator.twee

Author: Issac Davis
Date: 2026-02-23
Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import code
import io
import json
import os
import re
import subprocess
import sys
import textwrap
import time

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.system("")  # Enable ANSI escape codes on Windows 10+
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
#  Terminal colors (ANSI)
# ---------------------------------------------------------------------------

class C:
    """ANSI color codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[38;2;0;255;136m"
    CYAN    = "\033[38;2;0;200;255m"
    GOLD    = "\033[38;2;255;200;50m"
    RED     = "\033[38;2;255;80;80m"
    MAGENTA = "\033[38;2;200;100;255m"
    BLUE    = "\033[38;2;100;150;255m"
    WHITE   = "\033[38;2;220;220;220m"
    GREY    = "\033[38;2;120;120;120m"
    BG_DARK = "\033[48;2;10;10;18m"

TONGUE_COLORS = {
    "authority":    (C.RED,     "KO", "Kor'aelin"),
    "diplomacy":    (C.CYAN,    "AV", "Avali"),
    "integrity":    (C.BLUE,    "RU", "Runethic"),
    "intelligence": (C.GOLD,    "CA", "Cassisivadan"),
    "structure":    (C.MAGENTA, "DR", "Draumric"),
    "mystery":      (C.GREEN,   "UM", "Umbroth"),
}

# ---------------------------------------------------------------------------
#  Twee parser (standalone, no CSTM dependency needed)
# ---------------------------------------------------------------------------

@dataclass
class Scene:
    scene_id: str
    title: str
    tags: List[str] = field(default_factory=list)
    text: str = ""
    choices: List[Dict[str, str]] = field(default_factory=list)
    stat_effects: Dict[str, int] = field(default_factory=dict)
    is_exit: bool = False


def parse_twee(filepath: Path) -> Dict[str, Scene]:
    """Parse a Twee file into a dict of scenes."""
    content = filepath.read_text(encoding="utf-8")
    scenes: Dict[str, Scene] = {}
    current: Optional[Scene] = None

    for line in content.split("\n"):
        # Scene header: :: Title [tags]
        header = re.match(r'^::\s+(.+?)(?:\s+\[(.+?)\])?\s*$', line)
        if header:
            if current:
                _finalize_scene(current)
                scenes[current.scene_id] = current
            title = header.group(1).strip()
            tags_str = header.group(2) or ""
            tags = [t.strip() for t in tags_str.split() if t.strip()]
            scene_id = title.replace(" ", "_").lower()
            current = Scene(
                scene_id=scene_id,
                title=title,
                tags=tags,
                is_exit="exit" in tags,
            )
            continue

        if current is None:
            continue

        # Choice link: [[Label->Target]]
        choice_match = re.findall(r'\[\[(.+?)->(.+?)\]\]', line)
        if choice_match:
            for label, target in choice_match:
                target_id = target.strip().replace(" ", "_").lower()
                current.choices.append({"label": label.strip(), "target": target_id})
        else:
            # Regular text
            current.text += line + "\n"

    if current:
        _finalize_scene(current)
        scenes[current.scene_id] = current

    return scenes


def _finalize_scene(scene: Scene) -> None:
    """Clean up scene text and extract stat effects."""
    scene.text = scene.text.strip()

    # Extract stat effects from "Final stats impact:" lines
    impact = re.search(
        r'Final stats impact:\s*(.+)',
        scene.text,
        re.IGNORECASE,
    )
    if impact:
        for m in re.finditer(r'(\w+)\s+([+-]\d+)', impact.group(1)):
            stat = m.group(1).lower()
            val = int(m.group(2))
            scene.stat_effects[stat] = val


# ---------------------------------------------------------------------------
#  Training data logger
# ---------------------------------------------------------------------------

@dataclass
class TrainingLog:
    session_id: str
    records: List[Dict[str, Any]] = field(default_factory=list)

    def log_decision(
        self,
        scene: Scene,
        choice_label: str,
        stats: Dict[str, float],
        all_choices: List[str],
    ) -> None:
        choices_text = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(all_choices))
        instruction = (
            f"You are in the following scenario:\n\n{scene.text}\n\n"
            f"Available choices:\n{choices_text}\n\n"
            f"Which choice do you make and why?"
        )
        response = (
            f"I choose: **{choice_label}**\n\n"
            f"This decision was made considering the current governance state "
            f"and SCBE framework constraints."
        )
        self.records.append({
            "instruction": instruction,
            "response": response,
            "category": "governance",
            "metadata": {
                "origin": "terminal_game",
                "source_type": "human_playthrough",
                "scene_id": scene.scene_id,
                "stats_snapshot": dict(stats),
                "track": "governance",
                "quality": {"dedup": True, "validated": True},
            },
        })

    def save(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"sft_terminal_{self.session_id}_{ts}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for i, r in enumerate(self.records):
                r["id"] = f"sft-terminal-{i+1:04d}"
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return path


# ---------------------------------------------------------------------------
#  Terminal game engine
# ---------------------------------------------------------------------------

class SpiralverseTerminal:
    """Interactive terminal game with REPL capabilities."""

    def __init__(self, game_path: Optional[Path] = None):
        self.stats: Dict[str, float] = {
            "authority": 5.0,
            "diplomacy": 5.0,
            "integrity": 5.0,
            "intelligence": 5.0,
            "structure": 5.0,
            "mystery": 5.0,
        }
        self.scenes: Dict[str, Scene] = {}
        self.current_scene: Optional[Scene] = None
        self.history: List[str] = []
        self.training_log = TrainingLog(session_id=f"human_{int(time.time())}")
        self.turn = 0

        if game_path:
            self.load_game(game_path)

    def load_game(self, path: Path) -> None:
        self.scenes = parse_twee(path)
        # Find entry point
        for sid, scene in self.scenes.items():
            if "entry" in scene.tags:
                self.current_scene = scene
                break
        if not self.current_scene and self.scenes:
            self.current_scene = next(iter(self.scenes.values()))

    # ------------------------------------------------------------------
    #  Display helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def print_header(self) -> None:
        print(f"\n{C.GREEN}{C.BOLD}", end="")
        print("=" * 70)
        print("  ╔═╗╔═╗╦╦═╗╔═╗╦  ╦  ╦╔═╗╦═╗╔═╗╔═╗  ╔╦╗╔═╗╦═╗╔╦╗╦╔╗╔╔═╗╦  ")
        print("  ╚═╗╠═╝║╠╦╝╠═╣║  ╚╗╔╝║╣ ╠╦╝╚═╗║╣    ║ ║╣ ╠╦╝║║║║║║║╠═╣║  ")
        print("  ╚═╝╩  ╩╩╚═╩ ╩╩═╝ ╚╝ ╚═╝╩╚═╚═╝╚═╝   ╩ ╚═╝╩╚═╩ ╩╩╝╚╝╩ ╩╩═╝")
        print("=" * 70)
        print(f"  SCBE-AETHERMOORE Governance Training Simulator{C.RESET}")
        print(f"{C.GREY}  Type a number to choose | 'stats' | 'shell' | 'help' | 'quit'{C.RESET}")
        print()

    def print_stats_bar(self) -> None:
        print(f"{C.DIM}{'─' * 70}{C.RESET}")
        parts = []
        for stat, (color, code, _name) in TONGUE_COLORS.items():
            val = self.stats.get(stat, 0)
            bar_len = int(val)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            parts.append(f"{color}{code}{C.RESET} {bar} {val:.0f}")
        # Print in two rows of 3
        print(f"  {parts[0]}  {parts[1]}  {parts[2]}")
        print(f"  {parts[3]}  {parts[4]}  {parts[5]}")
        print(f"{C.DIM}{'─' * 70}{C.RESET}")

    def print_scene(self, scene: Scene) -> None:
        # Tags
        if scene.tags:
            tag_str = " ".join(f"[{t}]" for t in scene.tags if t != "entry")
            if tag_str:
                print(f"  {C.GREY}{tag_str}{C.RESET}")

        # Title
        print(f"\n  {C.GOLD}{C.BOLD}{scene.title}{C.RESET}")
        print()

        # Text (word-wrapped)
        for line in scene.text.split("\n"):
            if line.startswith("Validator-"):
                # Highlight validator lines
                print(f"  {C.CYAN}{line}{C.RESET}")
            elif "ALERT" in line or "DENY" in line:
                print(f"  {C.RED}{line}{C.RESET}")
            elif "ALLOW" in line or "PASS" in line:
                print(f"  {C.GREEN}{line}{C.RESET}")
            elif "QUARANTINE" in line:
                print(f"  {C.GOLD}{line}{C.RESET}")
            elif line.startswith("Final stats impact:"):
                # Parse and colorize stat changes
                print(f"\n  {C.BOLD}Stat Changes:{C.RESET}")
                for m in re.finditer(r'(\w+)\s+([+-]\d+)', line):
                    stat = m.group(1).lower()
                    val = int(m.group(2))
                    info = TONGUE_COLORS.get(stat)
                    if info:
                        color, code, name = info
                        sign = "+" if val > 0 else ""
                        print(f"    {color}{name} ({code}): {sign}{val}{C.RESET}")
            else:
                wrapped = textwrap.fill(line, width=66, initial_indent="  ", subsequent_indent="  ")
                print(f"{C.WHITE}{wrapped}{C.RESET}")
        print()

    def print_choices(self, choices: List[Dict[str, str]]) -> None:
        print(f"  {C.BOLD}What do you do?{C.RESET}\n")
        for i, choice in enumerate(choices):
            print(f"    {C.GREEN}{C.BOLD}{i+1}{C.RESET}  {C.WHITE}{choice['label']}{C.RESET}")
        print()

    # ------------------------------------------------------------------
    #  Game loop
    # ------------------------------------------------------------------

    def play(self) -> None:
        self.clear()
        self.print_header()

        if not self.current_scene:
            print(f"  {C.RED}No game loaded!{C.RESET}")
            print(f"  Use: python games/spiralverse_terminal.py --game <path.twee>")
            return

        while True:
            scene = self.current_scene
            if not scene:
                break

            self.print_stats_bar()
            self.print_scene(scene)

            # Exit scene — show ending
            if scene.is_exit:
                # Apply stat effects
                for stat, delta in scene.stat_effects.items():
                    if stat in self.stats:
                        self.stats[stat] = max(0, min(10, self.stats[stat] + delta))

                self.print_stats_bar()
                print(f"\n  {C.GOLD}{C.BOLD}═══ SCENARIO COMPLETE ═══{C.RESET}")
                print(f"  {C.WHITE}Turns taken: {self.turn}{C.RESET}")
                print(f"  {C.WHITE}Training records: {len(self.training_log.records)}{C.RESET}")

                # Save training data
                project_root = Path(__file__).resolve().parent.parent
                save_path = self.training_log.save(project_root / "training-data")
                print(f"  {C.GREEN}Training data saved: {save_path.name}{C.RESET}")

                print(f"\n  {C.GREY}Play again? (y/n/shell){C.RESET}")
                inp = input(f"  {C.GREEN}>{C.RESET} ").strip().lower()
                if inp == "y":
                    self._restart()
                    continue
                elif inp == "shell":
                    self._shell_mode()
                    continue
                else:
                    break

            # Show choices
            choices = scene.choices
            if not choices:
                print(f"  {C.RED}Dead end — no choices available.{C.RESET}")
                break

            self.print_choices(choices)

            # Get input
            inp = input(f"  {C.GREEN}polly@spiralverse:{C.RESET} ").strip().lower()

            # Handle meta commands
            if inp in ("quit", "exit", "q"):
                self._save_and_quit()
                break
            elif inp == "stats":
                self._show_full_stats()
                continue
            elif inp == "help":
                self._show_help()
                continue
            elif inp == "shell":
                self._shell_mode()
                continue
            elif inp == "history":
                self._show_history()
                continue
            elif inp.startswith("!"):
                # Shell escape
                self._run_command(inp[1:].strip())
                continue
            elif inp.startswith("py "):
                # Python one-liner
                self._run_python(inp[3:].strip())
                continue

            # Parse choice
            try:
                choice_idx = int(inp) - 1
                if 0 <= choice_idx < len(choices):
                    chosen = choices[choice_idx]
                else:
                    print(f"  {C.RED}Pick a number 1-{len(choices)}{C.RESET}")
                    continue
            except ValueError:
                # Try matching by keyword
                matched = [c for c in choices if inp in c["label"].lower()]
                if len(matched) == 1:
                    chosen = matched[0]
                else:
                    print(f"  {C.RED}Type a number or keyword.{C.RESET}")
                    continue

            # Log training data
            choice_labels = [c["label"] for c in choices]
            self.training_log.log_decision(scene, chosen["label"], self.stats, choice_labels)

            # Transition
            self.turn += 1
            self.history.append(f"Turn {self.turn}: {scene.title} → {chosen['label']}")
            target = chosen["target"]

            if target in self.scenes:
                self.current_scene = self.scenes[target]
            else:
                print(f"  {C.RED}Scene '{target}' not found! Game may be broken.{C.RESET}")
                break

            self.clear()
            self.print_header()

        print(f"\n  {C.GREEN}Spiral forward and upward. ✦{C.RESET}\n")

    # ------------------------------------------------------------------
    #  Meta commands
    # ------------------------------------------------------------------

    def _show_help(self) -> None:
        print(f"""
  {C.BOLD}Commands:{C.RESET}
    {C.GREEN}1-9{C.RESET}       Select a choice by number
    {C.GREEN}stats{C.RESET}     Show detailed Sacred Tongue stats
    {C.GREEN}history{C.RESET}   Show decision history
    {C.GREEN}shell{C.RESET}     Drop into interactive Python REPL
    {C.GREEN}!cmd{C.RESET}      Run a shell command (e.g., !git status)
    {C.GREEN}py expr{C.RESET}   Run a Python expression (e.g., py 2**10)
    {C.GREEN}quit{C.RESET}      Save training data and exit
""")

    def _show_full_stats(self) -> None:
        print(f"\n  {C.BOLD}Sacred Tongue Stats:{C.RESET}")
        for stat, (color, code, name) in TONGUE_COLORS.items():
            val = self.stats.get(stat, 0)
            bar = "█" * int(val) + "░" * (10 - int(val))
            print(f"    {color}{name:15s} ({code}) {bar} {val:.1f}/10{C.RESET}")
        total = sum(self.stats.values())
        print(f"\n    {C.WHITE}Total: {total:.1f}/60  |  Turn: {self.turn}  |  Records: {len(self.training_log.records)}{C.RESET}\n")

    def _show_history(self) -> None:
        if not self.history:
            print(f"  {C.GREY}No decisions yet.{C.RESET}\n")
            return
        print(f"\n  {C.BOLD}Decision History:{C.RESET}")
        for entry in self.history:
            print(f"    {C.WHITE}{entry}{C.RESET}")
        print()

    def _shell_mode(self) -> None:
        print(f"\n  {C.GOLD}Entering Python REPL. Type exit() to return to game.{C.RESET}")
        print(f"  {C.GREY}Variables: game.stats, game.history, game.scenes{C.RESET}\n")

        # Make game state available in REPL
        local_vars = {
            "game": self,
            "stats": self.stats,
            "scenes": self.scenes,
            "history": self.history,
        }

        # Try importing SCBE modules
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
            from symphonic_cipher.scbe_aethermoore import trinary, negabinary
            local_vars["trinary"] = trinary
            local_vars["negabinary"] = negabinary
            print(f"  {C.GREEN}SCBE modules loaded: trinary, negabinary{C.RESET}\n")
        except ImportError:
            pass

        code.interact(
            banner="",
            local=local_vars,
            exitmsg=f"\n  {C.GREEN}Returning to Spiralverse...{C.RESET}\n",
        )

    def _run_command(self, cmd: str) -> None:
        if not cmd:
            return
        print(f"  {C.GREY}$ {cmd}{C.RESET}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    print(f"  {C.WHITE}{line}{C.RESET}")
            if result.stderr:
                for line in result.stderr.strip().split("\n"):
                    print(f"  {C.RED}{line}{C.RESET}")
        except subprocess.TimeoutExpired:
            print(f"  {C.RED}Command timed out (30s limit){C.RESET}")
        print()

    def _run_python(self, expr: str) -> None:
        if not expr:
            return
        try:
            result = eval(expr, {"game": self, "stats": self.stats})
            print(f"  {C.CYAN}→ {result}{C.RESET}\n")
        except Exception as e:
            print(f"  {C.RED}Error: {e}{C.RESET}\n")

    def _restart(self) -> None:
        self.turn = 0
        self.history.clear()
        self.stats = {k: 5.0 for k in self.stats}
        # Reset to entry
        for scene in self.scenes.values():
            if "entry" in scene.tags:
                self.current_scene = scene
                break
        self.clear()
        self.print_header()

    def _save_and_quit(self) -> None:
        if self.training_log.records:
            project_root = Path(__file__).resolve().parent.parent
            save_path = self.training_log.save(project_root / "training-data")
            print(f"\n  {C.GREEN}Saved {len(self.training_log.records)} training records → {save_path.name}{C.RESET}")


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Spiralverse Terminal Game")
    parser.add_argument(
        "--game",
        default=None,
        help="Path to a .twee game file",
    )
    args = parser.parse_args()

    # Find default game
    project_root = Path(__file__).resolve().parent.parent
    if args.game:
        game_path = Path(args.game)
    else:
        default = project_root / "training-data" / "games" / "governance_simulator" / "governance_simulator.twee"
        if default.exists():
            game_path = default
        else:
            print(f"No game file found. Use --game <path.twee>")
            sys.exit(1)

    terminal = SpiralverseTerminal(game_path)
    terminal.play()


if __name__ == "__main__":
    main()
