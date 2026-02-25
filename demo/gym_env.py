#!/usr/bin/env python3
"""
Gymnasium RL wrapper for the Aethermoor RPG.
=============================================

Exposes the Aethermoor game as a Gymnasium environment suitable for
reinforcement learning training.  The observation space is the native
GBA resolution (240x160x3 RGB) down-scaled from the game's 640x480
render surface.

Install: ``pip install gymnasium pygame-ce numpy``
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Guarded gymnasium import
# ---------------------------------------------------------------------------
try:
    import gymnasium
    from gymnasium import spaces

    HAS_GYMNASIUM = True
except ImportError:
    HAS_GYMNASIUM = False

    # Stubs so the module is always importable.
    class _StubEnv:  # type: ignore[no-redef]
        pass

    class spaces:  # type: ignore[no-redef]
        Box = None
        Discrete = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NATIVE_W, NATIVE_H = 240, 160  # GBA native resolution
GAME_W, GAME_H = 640, 480      # AethermoorGame render surface size

ACTION_MAP: Dict[int, int] = {
    0: pygame.K_UP,
    1: pygame.K_DOWN,
    2: pygame.K_LEFT,
    3: pygame.K_RIGHT,
    4: pygame.K_RETURN,   # Confirm
    5: pygame.K_ESCAPE,   # Cancel
    6: pygame.K_1,        # Spell slot 1
    7: pygame.K_2,        # Spell slot 2
    8: pygame.K_3,        # Spell slot 3
    9: pygame.K_4,        # Spell slot 4
}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
_BaseClass = gymnasium.Env if HAS_GYMNASIUM else _StubEnv  # type: ignore[misc]


class AethermoorEnv(_BaseClass):  # type: ignore[misc]
    """Gymnasium environment wrapping the Aethermoor RPG demo.

    Observations are RGB frames at GBA native resolution (240x160).
    The agent selects from 10 discrete actions (d-pad, confirm/cancel,
    four spell slots).
    """

    metadata: Dict[str, Any] = {
        "render_modes": ["rgb_array", "human"],
        "render_fps": 30,
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        render_mode: str = "rgb_array",
        headless: bool = True,
        max_steps: int = 10_000,
    ) -> None:
        if not HAS_GYMNASIUM:
            raise ImportError(
                "gymnasium required -- install with: pip install gymnasium"
            )

        super().__init__()

        self.render_mode: str = render_mode
        self.headless: bool = headless
        self.max_steps: int = max_steps
        self.current_step: int = 0
        self.total_reward: float = 0.0
        self.training_pairs_generated: int = 0

        # Lazy-initialised game instance.
        self.game: Optional[Any] = None

        # Spaces
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=(NATIVE_H, NATIVE_W, 3),
            dtype=np.uint8,
        )
        self.action_space = spaces.Discrete(10)

        # State tracking between steps (used for reward deltas).
        self._prev_battle_active: bool = False
        self._prev_battle_victory: bool = False
        self._prev_battle_defeat: bool = False
        self._prev_training_pairs: int = 0
        self._prev_scene_id: str = "title"

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset the environment and return the initial observation."""
        super().reset(seed=seed)

        # Force headless SDL driver when requested.
        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        # (Re-)create the game.  We lazy-import AethermoorGame here to
        # avoid circular imports at module level.
        from aethermoor_game import AethermoorGame

        # Tear down any previous pygame state so we get a clean init.
        if self.game is not None:
            try:
                pygame.quit()
            except Exception:
                pass

        self.game = AethermoorGame()

        # Skip the title screen -- jump straight into the first scene.
        self.game.game_phase = "scene"
        self.game._load_scene("earth_morning")

        # Counters
        self.current_step = 0
        self.total_reward = 0.0
        self.training_pairs_generated = 0

        # Snapshot previous-state trackers.
        self._prev_battle_active = False
        self._prev_battle_victory = False
        self._prev_battle_defeat = False
        self._prev_training_pairs = self.game.sft_count + self.game.dpo_count
        self._prev_scene_id = self.game.scene.current_scene_id

        obs = self._get_observation()
        info = self._build_info()
        return obs, info

    def step(
        self,
        action: int,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Execute one action and advance the game by a single tick."""
        assert self.game is not None, "call reset() before step()"

        self.current_step += 1

        # ----- Inject the action as a pygame key event ----- #
        pg_key = ACTION_MAP.get(int(action))
        if pg_key is not None:
            down_event = pygame.event.Event(pygame.KEYDOWN, key=pg_key)
            up_event = pygame.event.Event(pygame.KEYUP, key=pg_key)
            pygame.event.post(down_event)
            pygame.event.post(up_event)

        # ----- Tick the game ----- #
        self.game._handle_events()
        self.game._update(1.0 / 30.0)

        # Render to game_surface so we can capture a frame.
        self.game._draw()

        # ----- Reward calculation ----- #
        reward = self._compute_reward()
        self.total_reward += reward

        # ----- Termination / truncation ----- #
        terminated = self._is_terminated()
        truncated = self.current_step >= self.max_steps

        obs = self._get_observation()
        info = self._build_info()

        # Snapshot state for the next delta computation.
        self._snapshot_state()

        return obs, reward, terminated, truncated, info

    def render(self) -> Optional[np.ndarray]:
        """Render according to the chosen render_mode."""
        if self.render_mode == "human":
            pygame.display.flip()
            return None
        elif self.render_mode == "rgb_array":
            return self._get_observation()
        return None

    def close(self) -> None:
        """Clean up pygame resources."""
        try:
            pygame.quit()
        except Exception:
            pass
        self.game = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_observation(self) -> np.ndarray:
        """Capture the game_surface and scale to native GBA resolution.

        Returns an (160, 240, 3) uint8 numpy array.
        """
        if self.game is None:
            return np.zeros((NATIVE_H, NATIVE_W, 3), dtype=np.uint8)

        # Scale the 640x480 game_surface down to 240x160.
        scaled = pygame.transform.smoothscale(
            self.game.game_surface, (NATIVE_W, NATIVE_H)
        )

        # pygame surfarray gives (W, H, C); we need (H, W, C).
        arr: np.ndarray = pygame.surfarray.array3d(scaled)  # (240, 160, 3)
        arr = arr.transpose((1, 0, 2))  # (160, 240, 3)
        return arr.astype(np.uint8)

    def _compute_reward(self) -> float:
        """Compute the reward delta for the current step."""
        assert self.game is not None
        reward = 0.0
        battle = self.game.battle

        # +5.0 for battle victory (edge-triggered).
        if battle.victory and not self._prev_battle_victory:
            reward += 5.0

        # +10.0 for tower floor advance.
        # The current game doesn't have an explicit tower_floor attribute
        # yet, but we detect scene transitions as a proxy for progression.
        current_scene = self.game.scene.current_scene_id
        if current_scene != self._prev_scene_id and current_scene != "title":
            reward += 10.0

        # +0.1 for each new training pair generated.
        current_pairs = self.game.sft_count + self.game.dpo_count
        new_pairs = current_pairs - self._prev_training_pairs
        if new_pairs > 0:
            reward += 0.1 * new_pairs
            self.training_pairs_generated += new_pairs

        # +0.5 for HP preservation (party average HP ratio * 0.5).
        if self.game.party:
            alive = [c for c in self.game.party if c.stats.max_hp > 0]
            if alive:
                avg_hp_ratio = sum(
                    c.stats.hp / c.stats.max_hp for c in alive
                ) / len(alive)
                reward += avg_hp_ratio * 0.5

        # +0.2 for tongue diversity bonus (unique tongues with prof > 0).
        if self.game.party:
            hero = self.game.party[0]
            unique_tongues = sum(
                1 for v in hero.stats.tongue_prof.values() if v > 0.0
            )
            reward += unique_tongues * 0.2

        # -1.0 for party defeat (edge-triggered).
        if battle.defeat and not self._prev_battle_defeat:
            reward -= 1.0

        return reward

    def _is_terminated(self) -> bool:
        """Check whether the episode should terminate."""
        assert self.game is not None

        # Party wipe.
        if self.game.battle.defeat:
            return True

        # All party members dead outside of battle.
        if self.game.party and all(
            c.stats.hp <= 0 for c in self.game.party
        ):
            return True

        # Reached floor 100 -- currently represented by exhausting all
        # scenes (the game has no explicit floor counter yet).
        if (
            self.game.scene.scene_finished
            and self.game.scene.next_scene() is None
            and not self.game.battle.active
        ):
            return True

        return False

    def _snapshot_state(self) -> None:
        """Cache state for delta-based reward calculation next step."""
        assert self.game is not None
        self._prev_battle_active = self.game.battle.active
        self._prev_battle_victory = self.game.battle.victory
        self._prev_battle_defeat = self.game.battle.defeat
        self._prev_training_pairs = self.game.sft_count + self.game.dpo_count
        self._prev_scene_id = self.game.scene.current_scene_id

    def _build_info(self) -> Dict[str, Any]:
        """Build the info dict returned alongside observations."""
        if self.game is None:
            return {}

        battle = self.game.battle
        hero = self.game.party[0] if self.game.party else None
        return {
            "scene_id": self.game.scene.current_scene_id,
            "game_phase": self.game.game_phase,
            "battle_active": battle.active,
            "battle_victory": battle.victory,
            "battle_defeat": battle.defeat,
            "total_reward": self.total_reward,
            "training_pairs": self.game.sft_count + self.game.dpo_count,
            "sft_count": self.game.sft_count,
            "dpo_count": self.game.dpo_count,
            "party_size": len(self.game.party),
            "hero_hp": hero.stats.hp if hero else 0,
            "hero_max_hp": hero.stats.max_hp if hero else 0,
            "tongue_prof": dict(hero.stats.tongue_prof) if hero else {},
            "current_step": self.current_step,
        }


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    env = AethermoorEnv()
    obs, info = env.reset()
    print(f"Observation shape: {obs.shape}")
    print(f"Action space: {env.action_space}")
    for i in range(10):
        obs, reward, term, trunc, info = env.step(env.action_space.sample())
        print(f"Step {i}: reward={reward:.2f}, terminated={term}")
        if term or trunc:
            break
    env.close()
