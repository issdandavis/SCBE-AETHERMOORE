#!/usr/bin/env python3
"""
ROM Emulator Bridge (legal ROM workflow)
========================================

Run a legally owned GB/GBC ROM headless via PyBoy and export training JSONL
records compatible with the existing Colab QLoRA pipeline (`prompt/response`).

This tool is intentionally strict about legal use:
  - It does NOT download ROMs.
  - It only runs local ROM files you provide.
  - You must pass --i-own-this-rom.

Notes:
  - GB/GBC is supported through PyBoy.
  - GBA ROMs (e.g., Pokemon Sapphire) require a separate backend (mGBA/RetroArch)
    and are not implemented in this file yet.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from pokemon_ai_agent import PokemonSmartAgent
    from pokemon_data_gen import build_pair as build_smart_pair
    try:
        from pokemon_data_gen import PokemonConversationGenerator
    except Exception:  # pragma: no cover - optional class
        PokemonConversationGenerator = None  # type: ignore[assignment]
    from pokemon_memory import PokemonCrystalMemoryReader
except Exception:  # pragma: no cover - optional smart-agent modules
    PokemonSmartAgent = None  # type: ignore[assignment]
    build_smart_pair = None  # type: ignore[assignment]
    PokemonConversationGenerator = None  # type: ignore[assignment]
    PokemonCrystalMemoryReader = None  # type: ignore[assignment]

try:
    from pokemon_trainer_hooks import TrainerHooks
except Exception:  # pragma: no cover
    TrainerHooks = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = PROJECT_ROOT / "training-data" / "rom_sessions"


def _safe_import_pyboy() -> Tuple[Any, Any]:
    """Import PyBoy lazily so --help works without optional deps."""
    try:
        from pyboy import PyBoy  # type: ignore
        from pyboy.utils import WindowEvent  # type: ignore
        return PyBoy, WindowEvent
    except Exception as exc:  # pragma: no cover - dependency gate
        raise RuntimeError(
            "PyBoy is required for GB/GBC ROM emulation.\n"
            "Install: pip install pyboy"
        ) from exc


def _safe_import_pil() -> Any:
    try:
        from PIL import Image
        return Image
    except Exception as exc:  # pragma: no cover - dependency gate
        raise RuntimeError("Pillow is required. Install: pip install Pillow") from exc


def _safe_import_ocr() -> Optional[Any]:
    try:
        import pytesseract  # type: ignore
        return pytesseract
    except Exception:
        return None


def infer_rom_system(rom_path: Path) -> str:
    ext = rom_path.suffix.lower()
    if ext == ".gb":
        return "gb"
    if ext == ".gbc":
        return "gbc"
    if ext == ".gba":
        return "gba"
    return "unknown"


def read_rom_title(rom_path: Path, system: str) -> str:
    """Best-effort ROM title extraction from header bytes."""
    try:
        blob = rom_path.read_bytes()
        if system in {"gb", "gbc"} and len(blob) > 0x143:
            raw = blob[0x134:0x144]
            title = raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            return title or rom_path.stem
        if system == "gba" and len(blob) > 0xAB:
            raw = blob[0xA0:0xAC]
            title = raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            return title or rom_path.stem
    except OSError:
        pass
    return rom_path.stem


def normalize_dialogue_text(text: str) -> str:
    cleaned = text.replace("\n", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^a-zA-Z0-9 .,!?':;\-()/]", "", cleaned)
    return cleaned.strip()


def dialogue_like(text: str) -> bool:
    if len(text) < 8:
        return False
    alpha = sum(ch.isalpha() for ch in text)
    return alpha >= max(5, int(len(text) * 0.45))


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_event_type(raw: str, fallback: str = "story_pack") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()
    return cleaned or fallback


def load_story_rows(path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    """Load prompt/response rows from a JSONL story/lore pack."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Story pack not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            prompt = _clean_text(obj.get("prompt") or obj.get("instruction") or obj.get("question"))
            response = _clean_text(obj.get("response") or obj.get("answer"))
            if not prompt or not response:
                continue

            rows.append(
                {
                    "prompt": prompt,
                    "response": response,
                    "event_type": _clean_text(obj.get("event_type")) or "story_pack",
                    "metadata": obj.get("metadata", {}) if isinstance(obj.get("metadata"), dict) else {},
                    "source_path": str(path),
                }
            )
            if limit > 0 and len(rows) >= limit:
                break

    return rows


BUTTON_CHOICES: List[Tuple[str, str, str]] = [
    ("A", "PRESS_BUTTON_A", "RELEASE_BUTTON_A"),
    ("B", "PRESS_BUTTON_B", "RELEASE_BUTTON_B"),
    ("UP", "PRESS_ARROW_UP", "RELEASE_ARROW_UP"),
    ("DOWN", "PRESS_ARROW_DOWN", "RELEASE_ARROW_DOWN"),
    ("LEFT", "PRESS_ARROW_LEFT", "RELEASE_ARROW_LEFT"),
    ("RIGHT", "PRESS_ARROW_RIGHT", "RELEASE_ARROW_RIGHT"),
    ("START", "PRESS_BUTTON_START", "RELEASE_BUTTON_START"),
]
BUTTON_BY_NAME: Dict[str, Tuple[str, str, str]] = {item[0]: item for item in BUTTON_CHOICES}


def choose_button(rng: random.Random) -> Tuple[str, str, str]:
    # Favor A/dirs for dialogue and movement progression.
    weighted = [
        BUTTON_CHOICES[0],  # A
        BUTTON_CHOICES[0],  # A
        BUTTON_CHOICES[1],  # B
        BUTTON_CHOICES[2],  # UP
        BUTTON_CHOICES[3],  # DOWN
        BUTTON_CHOICES[4],  # LEFT
        BUTTON_CHOICES[5],  # RIGHT
        BUTTON_CHOICES[6],  # START
    ]
    return rng.choice(weighted)


@dataclass
class RomPair:
    prompt: str
    response: str
    event_type: str
    metadata: Dict[str, Any]
    timestamp: float


@dataclass
class RunSummary:
    rom_path: str
    rom_title: str
    rom_system: str
    steps: int
    stored_frames: int
    pairs: int
    jsonl_path: str
    gif_path: Optional[str]
    ocr_enabled: bool


class RomEmulatorBridge:
    def __init__(
        self,
        rom_path: Path,
        out_dir: Path,
        steps: int,
        sample_every: int,
        hold_ticks: int,
        ocr_every: int,
        max_pairs: int,
        gif_path: Optional[Path],
        gif_fps: int,
        gif_scale: float,
        gif_max_frames: int,
        seed: int,
        smart_agent: bool = False,
        game: str = "auto",
        hf_repo: str = "",
        hf_token: str = "",
        story_pack_paths: Optional[List[Path]] = None,
        story_pack_mode: str = "off",
        story_pack_every: int = 600,
        story_pack_limit: int = 0,
    ) -> None:
        self.rom_path = rom_path
        self.rom_system = infer_rom_system(rom_path)
        self.rom_title = read_rom_title(rom_path, self.rom_system)
        self.out_dir = out_dir
        self.steps = steps
        self.sample_every = max(1, sample_every)
        self.hold_ticks = max(1, hold_ticks)
        self.ocr_every = max(1, ocr_every)
        self.max_pairs = max(1, max_pairs)
        self.gif_path = gif_path
        self.gif_fps = max(1, gif_fps)
        self.gif_scale = max(0.1, min(1.0, gif_scale))
        self.gif_max_frames = max(1, gif_max_frames)
        self.rng = random.Random(seed)
        self.smart_agent = smart_agent
        self.game = game
        self.hf_repo = hf_repo
        self.hf_token = hf_token
        self.story_pack_paths = list(story_pack_paths or [])
        self.story_pack_mode = (story_pack_mode or "off").lower()
        self.story_pack_every = max(1, story_pack_every)
        self.story_pack_limit = max(0, story_pack_limit)

        self.pairs: List[RomPair] = []
        self.frames: List[Any] = []
        self.last_dialogue: str = ""
        self.current_button: Optional[Tuple[str, str, str]] = None
        self.button_ticks_left = 0

        # Smart agent components (lazy-loaded)
        self._agent: Any = None
        self._data_gen: Any = None
        self._prev_state: Any = None
        self._memory_reader: Any = None
        self._last_decision: Dict[str, Any] = {}

        # Trainer hooks (game-mechanic training data triggers)
        self._hooks: Any = None
        self._hooks_enabled: bool = False

        # Optional lore/story pack rows injected into emulator sessions.
        self._story_rows: List[Dict[str, Any]] = []
        self._story_idx: int = 0

        self.PyBoy, self.WindowEvent = _safe_import_pyboy()
        self.Image = _safe_import_pil()
        self.pytesseract = _safe_import_ocr()

        # Auto-detect game from ROM title
        if self.game == "auto":
            title_lower = self.rom_title.lower()
            if "crystal" in title_lower or "crys" in title_lower:
                self.game = "pokemon_crystal"
            elif "gold" in title_lower or "silver" in title_lower:
                self.game = "pokemon_crystal"  # Same memory map
            elif "red" in title_lower or "blue" in title_lower or "yellow" in title_lower:
                self.game = "pokemon_gen1"
            else:
                self.game = "generic"

    def _init_smart_agent(self) -> bool:
        """Initialize the smart agent and data generator if available."""
        if not self.smart_agent:
            return False
        if self.game not in ("pokemon_crystal",):
            print(f"[bridge] Smart agent not supported for game: {self.game}")
            print("[bridge] Falling back to random input mode.")
            return False
        if PokemonSmartAgent is None or PokemonCrystalMemoryReader is None:
            print("[bridge] Smart agent modules unavailable.")
            print("[bridge] Falling back to random input mode.")
            return False
        self._agent = PokemonSmartAgent()
        if PokemonConversationGenerator is not None:
            self._data_gen = PokemonConversationGenerator()
        else:
            self._data_gen = None

        # Initialize TrainerHooks (game-mechanic training data triggers)
        if TrainerHooks is not None:
            self._hooks = TrainerHooks(
                output_dir=self.out_dir / "hooks",
                hf_repo_id=self.hf_repo,
                hf_token=self.hf_token,
            )
            self._hooks_enabled = True
            print("[bridge] TrainerHooks enabled (PokéCenter/DayCare/Gym/Save triggers)")
        else:
            print("[bridge] TrainerHooks not available (install pokemon_trainer_hooks.py)")

        print("[bridge] Smart agent enabled (Pokemon Crystal memory reader)")
        return True

    def _load_story_pack(self) -> None:
        if self.story_pack_mode == "off" or not self.story_pack_paths:
            return

        combined: List[Dict[str, Any]] = []
        for raw_path in self.story_pack_paths:
            try:
                p = Path(raw_path).expanduser().resolve()
                rows = load_story_rows(p, limit=self.story_pack_limit if self.story_pack_limit > 0 else 0)
                combined.extend(rows)
                print(f"[bridge] Story pack loaded: {p} ({len(rows)} rows)")
            except Exception as exc:
                print(f"[bridge] Story pack load failed ({raw_path}): {exc}")

        self._story_rows = combined
        self._story_idx = 0

    def _emit_story_row(self, step: int) -> bool:
        if not self._story_rows:
            return False
        if len(self.pairs) >= self.max_pairs:
            return False

        row = self._story_rows[self._story_idx % len(self._story_rows)]
        idx = self._story_idx
        self._story_idx += 1
        base_event = _normalize_event_type(_clean_text(row.get("event_type")), fallback="story_pack")
        meta = {
            "source": "rom_story_pack",
            "story_pack_source": row.get("source_path", ""),
            "story_index": idx,
            "step": step,
            "original_event_type": row.get("event_type", ""),
            **(row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}),
        }
        self.pairs.append(
            RomPair(
                prompt=row.get("prompt", ""),
                response=row.get("response", ""),
                event_type=f"story_{base_event}",
                metadata=meta,
                timestamp=time.time(),
            )
        )
        return True

    def run(self) -> RunSummary:
        if self.rom_system == "gba":
            raise RuntimeError(
                "GBA ROM detected. This bridge currently supports GB/GBC via PyBoy only.\n"
                "For Pokemon Sapphire (.gba), add an mGBA/RetroArch backend in Colab first."
            )
        if self.rom_system not in {"gb", "gbc"}:
            raise RuntimeError(
                f"Unsupported ROM extension: {self.rom_path.suffix or '(none)'}.\n"
                "Supported in this bridge: .gb, .gbc"
            )

        self.out_dir.mkdir(parents=True, exist_ok=True)
        session_id = f"rom_{uuid.uuid4().hex[:10]}"
        jsonl_path = self.out_dir / f"{session_id}.jsonl"

        self._load_story_pack()

        # Initialize smart agent if requested.
        use_smart = self._init_smart_agent()

        pyboy = self.PyBoy(
            str(self.rom_path),
            window_type="headless",
            sound=False,
        )
        pyboy.set_emulation_speed(0)
        if use_smart:
            try:
                self._memory_reader = PokemonCrystalMemoryReader.from_pyboy(pyboy)  # type: ignore[union-attr]
            except Exception as exc:
                print(f"[bridge] Memory reader init failed: {exc}")
                print("[bridge] Falling back to random input mode.")
                use_smart = False

        if self.story_pack_mode in {"prepend", "both"} and self._story_rows:
            while len(self.pairs) < self.max_pairs and self._emit_story_row(step=-1):
                if self._story_idx >= len(self._story_rows):
                    break

        try:
            for step in range(self.steps):
                if use_smart:
                    self._drive_smart_input(pyboy, step)
                else:
                    self._drive_input(pyboy)
                pyboy.tick()

                if (
                    self.story_pack_mode in {"interleave", "both"}
                    and self._story_rows
                    and step % self.story_pack_every == 0
                ):
                    self._emit_story_row(step=step)

                if step % self.sample_every == 0:
                    frame = self._capture_frame(pyboy)
                    if frame is not None and len(self.frames) < self.gif_max_frames:
                        self.frames.append(frame)

                # Smart agent: generate conversation data from state transitions
                if use_smart and step % 4 == 0:
                    self._smart_record(pyboy, step)
                elif not use_smart and step % self.ocr_every == 0:
                    self._maybe_record_dialogue(pyboy, step)

                if len(self.pairs) >= self.max_pairs:
                    break

                # Progress indicator
                if step > 0 and step % 1000 == 0:
                    print(f"  [step {step}/{self.steps}] pairs={len(self.pairs)}, "
                          f"frames={len(self.frames)}")
        finally:
            pyboy.stop()

        # Ensure we always emit at least sparse action pairs if nothing was generated.
        if not self.pairs:
            self._emit_sparse_action_pairs()

        # Smart agent data pairs are already added to self.pairs in _smart_record

        with open(jsonl_path, "w", encoding="utf-8") as handle:
            for pair in self.pairs:
                handle.write(json.dumps(asdict(pair), ensure_ascii=False) + "\n")

        saved_gif = None
        if self.gif_path and self.frames:
            saved_gif = self._save_gif(self.gif_path)

        # Print smart mode stats
        if use_smart:
            smart_pairs = sum(
                1 for p in self.pairs
                if p.event_type.startswith((
                    "battle_", "level_", "pokemon_", "badge_", "new_map",
                    "BATTLE_", "LEVEL_", "POKEMON_", "BADGE_", "NEW_MAP",
                    "HEAL", "MON_FAINTED", "rom_smart",
                ))
            )
            print(f"  [smart agent] Generated {smart_pairs} state-based pairs")
            if self._agent and hasattr(self._agent, "get_stats"):
                agent_stats = self._agent.get_stats()
                print(f"  [agent stats] {agent_stats}")

        # Flush TrainerHooks and report stats
        if self._hooks_enabled and self._hooks is not None:
            hooks_path = self._hooks.flush()
            hook_stats = self._hooks.stats()
            hook_pairs = sum(
                1 for p in self.pairs if p.event_type.startswith("hook_")
            )
            print(f"  [trainer hooks] {hook_stats['total_emitted']} events emitted, "
                  f"{hook_pairs} pairs in output")
            if hooks_path:
                print(f"  [trainer hooks] Flushed to: {hooks_path}")

        return RunSummary(
            rom_path=str(self.rom_path),
            rom_title=self.rom_title,
            rom_system=self.rom_system,
            steps=self.steps,
            stored_frames=len(self.frames),
            pairs=len(self.pairs),
            jsonl_path=str(jsonl_path),
            gif_path=str(saved_gif) if saved_gif else None,
            ocr_enabled=self.pytesseract is not None,
        )

    def _drive_smart_input(self, pyboy: Any, step: int) -> None:
        """Use the smart agent to decide the next button press from game state."""
        # Respect button hold/release timing so we do not spam press events.
        if self.current_button is not None and self.button_ticks_left > 0:
            self.button_ticks_left -= 1
            if self.button_ticks_left <= 0:
                _, _, release_name = self.current_button
                pyboy.send_input(getattr(self.WindowEvent, release_name))
            return

        if self._agent is None or self._memory_reader is None:
            self._drive_input(pyboy)
            return

        try:
            snapshot = self._memory_reader.read_snapshot()
        except Exception:
            self._drive_input(pyboy)
            return

        ocr_text = ""
        if step % self.ocr_every == 0:
            ocr_text = self._extract_dialogue_ocr(pyboy)

        decision = self._agent.choose(snapshot, ocr_text)
        self._last_decision = {
            "button": decision.button,
            "reason": decision.reason,
            "confidence": getattr(decision, "confidence", None),
        }
        button_name = decision.button

        btn = BUTTON_BY_NAME.get(button_name)
        if btn:
            _, press_name, _ = btn
            pyboy.send_input(getattr(self.WindowEvent, press_name))
            self.current_button = btn
            self.button_ticks_left = self.hold_ticks
        else:
            self._drive_input(pyboy)

    def _smart_record(self, pyboy: Any, step: int) -> None:
        """Read game state and generate conversation pairs from events.

        Uses PokemonConversationGenerator for rich event-driven pairs
        (battle won, level up, badge earned, etc.) and falls back to the
        built-in _detect_events for basic transition pairs.  Also emits
        periodic state/action rows via build_smart_pair with the agent's
        reasoning included in metadata.
        """
        if self._memory_reader is None:
            return

        try:
            snapshot = self._memory_reader.read_snapshot()
        except Exception:
            return

        if self._prev_state is not None:
            # Use PokemonConversationGenerator for rich event pairs if available
            if self._data_gen is not None and hasattr(self._data_gen, "detect_events"):
                try:
                    events = self._data_gen.detect_events(self._prev_state, snapshot)
                    if events:
                        rich_pairs = self._data_gen.generate_pairs(events, snapshot)
                        for rp in rich_pairs:
                            # Inject agent reasoning into metadata
                            meta = rp.get("metadata", {})
                            meta["step"] = step
                            meta["agent_reasoning"] = self._last_decision.get("reason", "")
                            meta["agent_button"] = self._last_decision.get("button", "")
                            meta["agent_confidence"] = self._last_decision.get("confidence")
                            self.pairs.append(RomPair(
                                prompt=rp.get("prompt", ""),
                                response=rp.get("response", ""),
                                event_type=rp.get("event_type", "smart_event"),
                                metadata=meta,
                                timestamp=float(rp.get("timestamp", time.time())),
                            ))
                except Exception:
                    # Fall through to basic detection below
                    pass

            # Also run basic transition detection for battle-start/end events
            basic_pairs = self._detect_events(self._prev_state, snapshot, step)
            self.pairs.extend(basic_pairs)

        # Always emit sparse state/action rows in smart mode so long runs
        # produce deterministic training data even without major events.
        if build_smart_pair is not None and self._last_decision and step % self.ocr_every == 0:
            try:
                ocr_text = self._extract_dialogue_ocr(pyboy)
                row = build_smart_pair(
                    rom_title=self.rom_title,
                    step=step,
                    snapshot=snapshot,
                    button=self._last_decision.get("button", "A"),
                    reason=self._last_decision.get("reason", "State-based action selection."),
                    ocr_text=ocr_text,
                    confidence=self._last_decision.get("confidence"),
                )
                # Add agent reasoning to metadata
                row_meta = row.get("metadata", {})
                row_meta["agent_reasoning"] = self._last_decision.get("reason", "")
                self.pairs.append(
                    RomPair(
                        prompt=row.get("prompt", ""),
                        response=row.get("response", ""),
                        event_type=row.get("event_type", "rom_smart_decision"),
                        metadata=row_meta,
                        timestamp=float(row.get("timestamp", time.time())),
                    )
                )
            except Exception:
                pass

        # Tick TrainerHooks with full PokemonState for game-mechanic triggers
        if self._hooks_enabled and self._hooks is not None and self._memory_reader is not None:
            try:
                from pokemon_memory import read_pokemon_state
                pokemon_state = read_pokemon_state(self._memory_reader.mem)
                hook_pairs = self._hooks.tick(pokemon_state, step=step)
                for hp in hook_pairs:
                    self.pairs.append(RomPair(
                        prompt=hp.instruction,
                        response=hp.response,
                        event_type=f"hook_{hp.category}",
                        metadata=hp.metadata,
                        timestamp=hp.timestamp,
                    ))
            except Exception:
                pass

        self._prev_state = snapshot

    def _detect_events(
        self, prev: Dict[str, Any], curr: Dict[str, Any], step: int
    ) -> List[RomPair]:
        """Detect game events from state transitions and generate conversation pairs."""
        pairs: List[RomPair] = []
        prev_battle = prev.get("battle", {})
        curr_battle = curr.get("battle", {})
        prev_party = prev.get("party", [])
        curr_party = curr.get("party", [])

        # Battle started
        if curr_battle.get("mode", 0) > 0 and prev_battle.get("mode", 0) == 0:
            enemy_sp = curr_battle.get("enemy_species", 0)
            enemy_lv = curr_battle.get("enemy_level", 0)
            lead = curr_party[0] if curr_party else {}
            bt = "wild" if curr_battle.get("mode") == 1 else "trainer"
            prompt = (
                f"A {bt} battle begins! Enemy Pokemon #{enemy_sp} (Lv.{enemy_lv}) appeared! "
                f"Your lead is #{lead.get('species', 0)} "
                f"(Lv.{lead.get('level', 0)}, HP: {lead.get('hp', 0)}/{lead.get('max_hp', 0)}). "
                f"What should you do?"
            )
            response = (
                f"Assess the type matchup and use your most effective move. "
                f"If your Pokemon is healthy, attack aggressively."
            )
            pairs.append(RomPair(prompt=prompt, response=response,
                event_type="battle_start",
                metadata={"enemy_species": enemy_sp, "enemy_level": enemy_lv, "step": step},
                timestamp=time.time()))

        # Battle ended
        if prev_battle.get("mode", 0) > 0 and curr_battle.get("mode", 0) == 0:
            avg_hp = 0
            if curr_party:
                total_hp = sum(p.get("hp", 0) for p in curr_party)
                total_max = sum(max(1, p.get("max_hp", 1)) for p in curr_party)
                avg_hp = int(100 * total_hp / total_max)
            prompt = f"Battle ended! Team at {avg_hp}% HP. What next?"
            response = (
                f"Head to a Pokemon Center to heal." if avg_hp < 40
                else f"Good win! Keep exploring for more experience."
            )
            pairs.append(RomPair(prompt=prompt, response=response,
                event_type="battle_end", metadata={"team_hp_pct": avg_hp, "step": step},
                timestamp=time.time()))

        # New map
        prev_map = prev.get("map", {})
        curr_map = curr.get("map", {})
        if (curr_map.get("group"), curr_map.get("number")) != (prev_map.get("group"), prev_map.get("number")):
            badges = curr.get("badges", {}).get("total", 0)
            prompt = (
                f"Entered new area (map {curr_map.get('group')}:{curr_map.get('number')}). "
                f"Badges: {badges}, Money: ${curr.get('money', 0):,}. What to explore?"
            )
            response = "Look for items, talk to NPCs, check for a Pokemon Center or Gym nearby."
            pairs.append(RomPair(prompt=prompt, response=response,
                event_type="new_map", metadata={"map": curr_map, "step": step},
                timestamp=time.time()))

        # Level up
        for i, (pm, cm) in enumerate(zip(prev_party, curr_party)):
            if cm.get("level", 0) > pm.get("level", 0):
                prompt = (
                    f"Pokemon #{cm.get('species', 0)} leveled up from "
                    f"Lv.{pm.get('level', 0)} to Lv.{cm.get('level', 0)}! Advice?"
                )
                response = "Keep battling for more XP. Check for new moves at this level."
                pairs.append(RomPair(prompt=prompt, response=response,
                    event_type="level_up",
                    metadata={"species": cm.get("species", 0), "new_level": cm.get("level", 0), "step": step},
                    timestamp=time.time()))

        # Pokemon caught (party grew)
        if len(curr_party) > len(prev_party):
            new_mon = curr_party[-1]
            prompt = (
                f"Caught Pokemon #{new_mon.get('species', 0)} (Lv.{new_mon.get('level', 0)})! "
                f"Party: {len(curr_party)}/6. Good catch?"
            )
            response = "Every new species helps! Consider how its type fits your team."
            pairs.append(RomPair(prompt=prompt, response=response,
                event_type="pokemon_caught",
                metadata={"species": new_mon.get("species", 0), "step": step},
                timestamp=time.time()))

        # Badge earned
        prev_badges = prev.get("badges", {}).get("total", 0)
        curr_badges = curr.get("badges", {}).get("total", 0)
        if curr_badges > prev_badges:
            prompt = f"Earned a badge! Total: {curr_badges}. Next step?"
            response = (
                "All 8 Johto badges! Time for the Elite Four!" if curr_badges == 8
                else f"Head to the next Gym. Train your team on the way."
            )
            pairs.append(RomPair(prompt=prompt, response=response,
                event_type="badge_earned",
                metadata={"total_badges": curr_badges, "step": step},
                timestamp=time.time()))

        return pairs

    def _drive_input(self, pyboy: Any) -> None:
        if self.current_button is None or self.button_ticks_left <= 0:
            self.current_button = choose_button(self.rng)
            self.button_ticks_left = self.hold_ticks
            _, press_name, _ = self.current_button
            pyboy.send_input(getattr(self.WindowEvent, press_name))
        else:
            self.button_ticks_left -= 1
            if self.button_ticks_left <= 0 and self.current_button is not None:
                _, _, release_name = self.current_button
                pyboy.send_input(getattr(self.WindowEvent, release_name))

    def _capture_frame(self, pyboy: Any) -> Optional[Any]:
        try:
            arr = pyboy.screen.ndarray  # HxWx3 uint8
            if arr is None:
                return None
            img = self.Image.fromarray(np.asarray(arr, dtype=np.uint8))
            if self.gif_scale != 1.0:
                w, h = img.size
                img = img.resize(
                    (max(1, int(w * self.gif_scale)), max(1, int(h * self.gif_scale)))
                )
            return img.convert("P", palette=self.Image.Palette.ADAPTIVE)
        except Exception:
            return None

    def _extract_dialogue_ocr(self, pyboy: Any) -> str:
        if self.pytesseract is None:
            return ""
        try:
            arr = np.asarray(pyboy.screen.ndarray, dtype=np.uint8)
            h, w, _ = arr.shape
            # Typical dialogue box lives in lower third.
            crop = arr[int(h * 0.62): h, 0:w]
            img = self.Image.fromarray(crop)
            text = self.pytesseract.image_to_string(img, config="--psm 6")
            return normalize_dialogue_text(text)
        except Exception:
            return ""

    def _maybe_record_dialogue(self, pyboy: Any, step: int) -> None:
        text = self._extract_dialogue_ocr(pyboy)
        if not dialogue_like(text):
            return
        if text == self.last_dialogue:
            return
        self.last_dialogue = text

        button_name = self.current_button[0] if self.current_button else "A"
        prompt = (
            f"[ROM_DIALOGUE] {self.rom_title} frame {step}: "
            f"Observed dialogue: \"{text}\". What should the autopilot do next?"
        )
        response = (
            f"Press {button_name} to progress dialogue safely, then continue exploration "
            f"to gather the next conversation state."
        )
        pair = RomPair(
            prompt=prompt,
            response=response,
            event_type="rom_dialogue",
            metadata={
                "source": "pokemon_rom_bridge",
                "rom_title": self.rom_title,
                "rom_system": self.rom_system,
                "step": step,
                "button": button_name,
                "dialogue": text,
            },
            timestamp=time.time(),
        )
        self.pairs.append(pair)

    def _emit_sparse_action_pairs(self) -> None:
        # Fallback when OCR is unavailable or no text was detected.
        step_stride = max(1, self.steps // min(self.max_pairs, 20))
        for idx, step in enumerate(range(0, self.steps, step_stride)):
            if idx >= self.max_pairs:
                break
            button_name, _, _ = choose_button(self.rng)
            prompt = (
                f"[ROM_STATE] {self.rom_title} frame {step}: "
                "No OCR dialogue extracted. Choose the next exploration action."
            )
            response = (
                f"Use {button_name} to advance traversal and collect future state/dialogue."
            )
            self.pairs.append(
                RomPair(
                    prompt=prompt,
                    response=response,
                    event_type="rom_action",
                    metadata={
                        "source": "pokemon_rom_bridge",
                        "rom_title": self.rom_title,
                        "rom_system": self.rom_system,
                        "step": step,
                        "button": button_name,
                        "ocr": "unavailable_or_no_text",
                    },
                    timestamp=time.time(),
                )
            )

    def _save_gif(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self.frames:
            return path
        duration_ms = int(1000 / self.gif_fps)
        self.frames[0].save(
            path,
            save_all=True,
            append_images=self.frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a legal local GB/GBC ROM and export prompt/response JSONL."
    )
    parser.add_argument("--rom", type=str, required=True, help="Path to local ROM (.gb/.gbc)")
    parser.add_argument("--steps", type=int, default=4000, help="Emulation steps/ticks")
    parser.add_argument("--sample-every", type=int, default=8, help="Capture 1 frame every N ticks")
    parser.add_argument("--hold-ticks", type=int, default=3, help="Button hold duration in ticks")
    parser.add_argument("--ocr-every", type=int, default=20, help="Run OCR every N ticks")
    parser.add_argument("--max-pairs", type=int, default=500, help="Cap exported training pairs")
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR), help="JSONL output directory")
    parser.add_argument("--gif", type=str, default="", help="Optional GIF output path")
    parser.add_argument("--gif-fps", type=int, default=10, help="GIF fps")
    parser.add_argument("--gif-scale", type=float, default=0.5, help="GIF scale factor")
    parser.add_argument("--gif-max-frames", type=int, default=220, help="Max frames stored for GIF")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic input seed")
    parser.add_argument(
        "--smart-agent",
        action="store_true",
        help="Enable memory-aware Pokemon Crystal smart policy/data generation.",
    )
    parser.add_argument(
        "--game",
        type=str,
        default="auto",
        choices=["auto", "pokemon_crystal", "pokemon_gen1", "generic"],
        help="Game profile for smart mode.",
    )
    parser.add_argument(
        "--hf-repo",
        type=str,
        default="",
        help="HuggingFace dataset repo ID for auto-push (e.g., 'SCBE-AETHER/pokemon-crystal-sft-v1').",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        default="",
        help="HuggingFace API token (or set HF_TOKEN env var).",
    )
    parser.add_argument(
        "--story-pack",
        action="append",
        default=[],
        help=(
            "Optional JSONL lore/minigame pack to merge into emulator output "
            "(repeatable). Rows should contain prompt/response."
        ),
    )
    parser.add_argument(
        "--story-pack-mode",
        type=str,
        default="off",
        choices=["off", "prepend", "interleave", "both"],
        help="How to inject story-pack rows into output.",
    )
    parser.add_argument(
        "--story-pack-every",
        type=int,
        default=600,
        help="Interleave cadence in emulator steps when story-pack mode is interleave/both.",
    )
    parser.add_argument(
        "--story-pack-limit",
        type=int,
        default=0,
        help="Max rows loaded per story-pack file (0 = all rows).",
    )
    parser.add_argument(
        "--i-own-this-rom",
        action="store_true",
        help="Required acknowledgement that you legally own and dumped this ROM.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.i_own_this_rom:
        print(
            "Refusing to run without legal acknowledgement.\n"
            "Pass --i-own-this-rom if this ROM was legally obtained by you."
        )
        return 2

    rom_path = Path(args.rom).expanduser().resolve()
    if not rom_path.is_file():
        print(f"ROM not found: {rom_path}")
        return 2

    bridge = RomEmulatorBridge(
        rom_path=rom_path,
        out_dir=Path(args.out_dir).expanduser().resolve(),
        steps=args.steps,
        sample_every=args.sample_every,
        hold_ticks=args.hold_ticks,
        ocr_every=args.ocr_every,
        max_pairs=args.max_pairs,
        gif_path=Path(args.gif).expanduser().resolve() if args.gif else None,
        gif_fps=args.gif_fps,
        gif_scale=args.gif_scale,
        gif_max_frames=args.gif_max_frames,
        seed=args.seed,
        smart_agent=args.smart_agent,
        game=args.game,
        hf_repo=args.hf_repo,
        hf_token=args.hf_token,
        story_pack_paths=[Path(p) for p in (args.story_pack or [])],
        story_pack_mode=args.story_pack_mode,
        story_pack_every=args.story_pack_every,
        story_pack_limit=args.story_pack_limit,
    )

    try:
        summary = bridge.run()
    except Exception as exc:
        print(f"Run failed: {exc}")
        return 1

    print("\nROM bridge completed.")
    print(f"  ROM:          {summary.rom_title} ({summary.rom_system})")
    print(f"  Steps:        {summary.steps}")
    print(f"  Training rows:{summary.pairs}")
    print(f"  JSONL:        {summary.jsonl_path}")
    if summary.gif_path:
        print(f"  GIF:          {summary.gif_path}")
    print(f"  OCR enabled:  {summary.ocr_enabled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
