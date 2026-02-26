from __future__ import annotations

import random
import tkinter as tk
from tkinter import font as tkfont

from .geoseal_hooks import geoseal_governance
from .lesson_engine import apply_lesson
from .models import AgentState, EggGenome
from .world import WorldCell, WorldSim


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


class Gen1GameView:
    """Retro (Gen-1 inspired) visual shell for the Polly Eggs prototype."""

    TILE = 16
    VIEW = 10
    HUD_W = 196
    DIALOG_H = 108
    OUTER_PAD = 10

    PALETTE = {
        "bg0": "#9bbc0f",
        "bg1": "#8bac0f",
        "bg2": "#306230",
        "bg3": "#0f380f",
        "alert": "#f8f8f8",
    }

    BIOME_COLORS = {
        "plains": "#9bbc0f",
        "forest": "#8bac0f",
        "shore": "#8bac0f",
        "ruins": "#306230",
        "cavern": "#0f380f",
    }

    LESSON_ROTATION = [
        "navigation-basics",
        "resource-discipline",
        "geoseal-boundary-test",
        "swarm-handoff",
    ]

    def __init__(self, seed: str = "aethermore-v1"):
        self.seed = seed
        self.world = WorldSim(seed=seed, size=24)
        self.rng = random.Random(f"{seed}-encounters")

        self.genome = EggGenome(egg_id="player-0001", world_seed=seed)
        self.state = AgentState(egg_id=self.genome.egg_id)
        self.lesson_index = 0

        self.player_x = self.world.size // 2
        self.player_y = self.world.size // 2
        self.last_outcome = "ALLOW"
        self.message = "AETHERMOORE FIELD TEST: Arrow keys move, Z gather, X train."

        self.map_px = self.TILE * self.VIEW
        self.window_w = self.map_px + self.HUD_W + (self.OUTER_PAD * 3)
        self.window_h = self.map_px + self.DIALOG_H + (self.OUTER_PAD * 3)

        self.root = tk.Tk()
        self.root.title("Polly Eggs - Retro Field Build")
        self.root.geometry(f"{self.window_w}x{self.window_h}")
        self.root.configure(bg=self.PALETTE["bg3"])
        self.root.resizable(False, False)

        self.font_ui = tkfont.Font(family="Courier New", size=9, weight="bold")
        self.font_dialog = tkfont.Font(family="Courier New", size=10, weight="bold")

        self.canvas = tk.Canvas(
            self.root,
            width=self.map_px,
            height=self.map_px,
            bg=self.PALETTE["bg0"],
            highlightthickness=3,
            highlightbackground=self.PALETTE["bg3"],
        )
        self.canvas.place(x=self.OUTER_PAD, y=self.OUTER_PAD)

        hud_x = self.OUTER_PAD * 2 + self.map_px
        self.hud = tk.Frame(
            self.root,
            bg=self.PALETTE["bg1"],
            width=self.HUD_W,
            height=self.map_px,
            highlightthickness=3,
            highlightbackground=self.PALETTE["bg3"],
        )
        self.hud.place(x=hud_x, y=self.OUTER_PAD)

        self.hud_labels: dict[str, tk.Label] = {}
        self._build_hud()

        self.dialog = tk.Label(
            self.root,
            text="",
            bg=self.PALETTE["bg0"],
            fg=self.PALETTE["bg3"],
            anchor="nw",
            justify="left",
            wraplength=self.window_w - (self.OUTER_PAD * 2) - 10,
            font=self.font_dialog,
            padx=8,
            pady=8,
            highlightthickness=3,
            highlightbackground=self.PALETTE["bg3"],
        )
        self.dialog.place(
            x=self.OUTER_PAD,
            y=self.OUTER_PAD * 2 + self.map_px,
            width=self.window_w - (self.OUTER_PAD * 2),
            height=self.DIALOG_H,
        )

        self.root.bind("<Up>", lambda _e: self._move(0, -1))
        self.root.bind("<Down>", lambda _e: self._move(0, 1))
        self.root.bind("<Left>", lambda _e: self._move(-1, 0))
        self.root.bind("<Right>", lambda _e: self._move(1, 0))
        self.root.bind("<z>", lambda _e: self._gather())
        self.root.bind("<x>", lambda _e: self._train())

        self._render_all()

    def run(self) -> None:
        self.root.mainloop()

    def _build_hud(self) -> None:
        title = tk.Label(
            self.hud,
            text="POLLY DEX",
            bg=self.PALETTE["bg2"],
            fg=self.PALETTE["bg0"],
            font=self.font_ui,
            padx=4,
            pady=4,
        )
        title.pack(fill="x", padx=5, pady=(5, 6))

        for key in [
            "tick",
            "pos",
            "biome",
            "risk",
            "resources",
            "outcome",
            "learning",
            "safety",
            "stability",
            "drift",
            "inventory",
        ]:
            lbl = tk.Label(
                self.hud,
                text="",
                bg=self.PALETTE["bg1"],
                fg=self.PALETTE["bg3"],
                anchor="w",
                justify="left",
                font=self.font_ui,
            )
            lbl.pack(fill="x", padx=6, pady=1)
            self.hud_labels[key] = lbl

    def _current_cell(self) -> WorldCell:
        return self.world.grid[self.player_y][self.player_x]

    def _set_message(self, text: str) -> None:
        self.message = text
        self.dialog.configure(text=text)

    def _move(self, dx: int, dy: int) -> None:
        nx = _clamp(self.player_x + dx, 0, self.world.size - 1)
        ny = _clamp(self.player_y + dy, 0, self.world.size - 1)

        if nx == self.player_x and ny == self.player_y:
            self._set_message("Edge of map. The route ends here.")
            self._render_all()
            return

        self.player_x = nx
        self.player_y = ny
        self.world.step()

        cell = self._current_cell()
        self.state.learning += 0.010
        self.state.drift += (0.020 * cell.risk) - 0.007
        self.state.safety += (0.010 * (1.0 - cell.risk)) - (0.004 * cell.risk)
        self.state.stability += 0.006 - (0.010 * abs(cell.risk - 0.5))
        self.state.clamp()

        if cell.risk > 0.72:
            self.state = apply_lesson(self.state, "geoseal-boundary-test")
        elif cell.biome == "ruins":
            self.state = apply_lesson(self.state, "navigation-basics")

        self.last_outcome = geoseal_governance(self.state, self.genome)
        risk_pct = int(cell.risk * 100)

        encounter_roll = self.rng.random()
        encounter_chance = 0.02 + (cell.risk * 0.18)
        if encounter_roll < encounter_chance:
            target = self.rng.choice(["Echo Wisp", "Null Beetle", "Shard Pup", "Proto Owl"])
            self._set_message(f"WILD {target.upper()} appeared in {cell.biome}. Risk {risk_pct}%.")
        else:
            self._set_message(f"Moved to {cell.biome}. Risk {risk_pct}%. GeoSeal: {self.last_outcome}.")

        self._render_all()

    def _gather(self) -> None:
        cell = self._current_cell()
        if cell.resources <= 0:
            self._set_message("No resources left in this tile.")
            self._render_all()
            return

        gained = min(2, cell.resources)
        cell.resources -= gained
        key = f"{cell.biome}_shard"
        self.state.inventory[key] = self.state.inventory.get(key, 0) + gained
        self.state = apply_lesson(self.state, "resource-discipline")
        self.last_outcome = geoseal_governance(self.state, self.genome)

        self._set_message(f"Gathered {gained} {cell.biome} shard(s). GeoSeal: {self.last_outcome}.")
        self._render_all()

    def _train(self) -> None:
        lesson = self.LESSON_ROTATION[self.lesson_index % len(self.LESSON_ROTATION)]
        self.lesson_index += 1
        self.state = apply_lesson(self.state, lesson)
        self.last_outcome = geoseal_governance(self.state, self.genome)
        self._set_message(f"Trained lesson: {lesson}. GeoSeal: {self.last_outcome}.")
        self._render_all()

    def _noise(self, x: int, y: int, salt: int) -> int:
        v = (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)
        return abs(v) % 100

    def _draw_tile(self, px: int, py: int, wx: int, wy: int, cell: WorldCell | None) -> None:
        if cell is None:
            self.canvas.create_rectangle(
                px,
                py,
                px + self.TILE,
                py + self.TILE,
                fill=self.PALETTE["bg3"],
                outline=self.PALETTE["bg2"],
                width=1,
            )
            return

        base = self.BIOME_COLORS.get(cell.biome, self.PALETTE["bg1"])
        self.canvas.create_rectangle(
            px,
            py,
            px + self.TILE,
            py + self.TILE,
            fill=base,
            outline=self.PALETTE["bg2"],
            width=1,
        )

        if cell.biome == "forest":
            for i in range(3):
                ox = self._noise(wx, wy, i) % 12
                oy = self._noise(wx, wy, i + 9) % 12
                self.canvas.create_rectangle(px + ox, py + oy, px + ox + 2, py + oy + 2, fill=self.PALETTE["bg3"], width=0)
        elif cell.biome == "shore":
            for i in (4, 9, 13):
                self.canvas.create_line(px + 1, py + i, px + self.TILE - 2, py + i, fill=self.PALETTE["bg2"], width=1)
        elif cell.biome == "ruins":
            self.canvas.create_rectangle(px + 2, py + 2, px + self.TILE - 3, py + 6, fill=self.PALETTE["bg3"], width=0)
            self.canvas.create_rectangle(px + 3, py + 9, px + self.TILE - 5, py + 13, fill=self.PALETTE["bg2"], width=0)
        elif cell.biome == "cavern":
            for i in range(2):
                ox = self._noise(wx, wy, i + 31) % 13
                oy = self._noise(wx, wy, i + 41) % 13
                self.canvas.create_rectangle(px + ox, py + oy, px + ox + 3, py + oy + 3, fill=self.PALETTE["bg2"], width=0)

        if cell.resources > 0:
            self.canvas.create_rectangle(
                px + self.TILE - 6,
                py + self.TILE - 6,
                px + self.TILE - 2,
                py + self.TILE - 2,
                fill=self.PALETTE["bg3"],
                width=0,
            )

    def _render_map(self) -> None:
        self.canvas.delete("all")

        half = self.VIEW // 2
        wx0 = self.player_x - half
        wy0 = self.player_y - half

        for vy in range(self.VIEW):
            for vx in range(self.VIEW):
                wx = wx0 + vx
                wy = wy0 + vy
                px = vx * self.TILE
                py = vy * self.TILE
                if 0 <= wx < self.world.size and 0 <= wy < self.world.size:
                    cell = self.world.grid[wy][wx]
                else:
                    cell = None
                self._draw_tile(px, py, wx, wy, cell)

        player_px = (self.player_x - wx0) * self.TILE
        player_py = (self.player_y - wy0) * self.TILE
        self.canvas.create_rectangle(
            player_px + 4,
            player_py + 3,
            player_px + 11,
            player_py + 7,
            fill=self.PALETTE["bg3"],
            width=0,
        )
        self.canvas.create_rectangle(
            player_px + 3,
            player_py + 8,
            player_px + 12,
            player_py + 14,
            fill=self.PALETTE["bg2"],
            width=0,
        )

        self.canvas.create_rectangle(
            1,
            1,
            self.map_px - 2,
            self.map_px - 2,
            outline=self.PALETTE["bg3"],
            width=2,
        )

    def _render_hud(self) -> None:
        cell = self._current_cell()
        inv_total = sum(self.state.inventory.values())

        self.hud_labels["tick"].configure(text=f"Tick: {self.world.tick}")
        self.hud_labels["pos"].configure(text=f"Pos: ({self.player_x:02d},{self.player_y:02d})")
        self.hud_labels["biome"].configure(text=f"Biome: {cell.biome}")
        self.hud_labels["risk"].configure(text=f"Risk: {cell.risk:.2f}")
        self.hud_labels["resources"].configure(text=f"Tile Res: {cell.resources}")
        self.hud_labels["outcome"].configure(text=f"GeoSeal: {self.last_outcome}")
        self.hud_labels["learning"].configure(text=f"Learning: {self.state.learning:.2f}")
        self.hud_labels["safety"].configure(text=f"Safety:   {self.state.safety:.2f}")
        self.hud_labels["stability"].configure(text=f"Stability:{self.state.stability:.2f}")
        self.hud_labels["drift"].configure(text=f"Drift:    {self.state.drift:.2f}")
        self.hud_labels["inventory"].configure(text=f"Inventory:{inv_total}")

        outcome_color = self.PALETTE["bg0"] if self.last_outcome == "ALLOW" else self.PALETTE["alert"]
        self.hud_labels["outcome"].configure(
            fg=outcome_color,
            bg=self.PALETTE["bg2"] if self.last_outcome != "ALLOW" else self.PALETTE["bg1"],
        )

    def _render_all(self) -> None:
        self._render_map()
        self._render_hud()
        self.dialog.configure(text=self.message)


def run_gen1_game(seed: str = "aethermore-v1") -> None:
    Gen1GameView(seed=seed).run()
