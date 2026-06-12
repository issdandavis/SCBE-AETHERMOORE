"""Stone pack: breakout_core — a real, headless Breakout/Arkanoid engine.

Pure data: the mason loader builds Piece/Slot/Schematic objects from PACK.
Deterministic integer physics: ball velocity components are +/-1, bounces
invert a component, every trajectory is hand-traceable on the 9x7 board.
"""

PACK = {
    "name": "breakout",
    "pieces": {
        "world": {
            "shape": "config",
            "holes": ["W", "H", "ROWS", "POINTS"],
            "template": (
                "WIDTH = __H_W__\n"
                "HEIGHT = __H_H__\n"
                "BRICK_ROWS = __H_ROWS__\n"
                "POINTS_PER_BRICK = __H_POINTS__\n"
                "PADDLE_WIDTH = 3"
            ),
        },
        "paddle": {
            "shape": "mover",
            "template": """
class Paddle:
    def __init__(self, x, y, width, board_w):
        self.x = x
        self.y = y
        self.width = width
        self.board_w = board_w

    def move(self, dx):
        self.x = max(0, min(self.board_w - self.width, self.x + dx))
        return self.x

    def covers(self, x):
        return self.x <= x < self.x + self.width
""",
        },
        "ball": {
            "shape": "projectile",
            "template": """
class Ball:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

    def next_pos(self, board_w):
        nx = self.x + self.vx
        ny = self.y + self.vy
        if nx < 0 or nx >= board_w:
            self.vx = -self.vx
            nx = self.x + self.vx
        if ny < 0:
            self.vy = -self.vy
            ny = self.y + self.vy
        return nx, ny
""",
        },
        "bricks": {
            "shape": "board",
            "template": """
class Bricks:
    def __init__(self, rows, width):
        self.cells = {(x, y) for y in rows for x in range(width)}

    def hit(self, x, y):
        if (x, y) in self.cells:
            self.cells.discard((x, y))
            return True
        return False

    def cleared(self):
        return not self.cells
""",
        },
        "engine": {
            "shape": "rules+scorer",
            "template": """
class Breakout:
    def __init__(self, brick_cells=None):
        self.width = WIDTH
        self.height = HEIGHT
        self.paddle = Paddle(3, HEIGHT - 1, PADDLE_WIDTH, WIDTH)
        self.ball = Ball(4, 4, 1, -1)
        self.bricks = Bricks(BRICK_ROWS, WIDTH)
        if brick_cells is not None:
            self.bricks.cells = set(brick_cells)
        self.score = 0
        self.lost = False
        self.won = False

    def step(self):
        if self.lost or self.won:
            return self.score
        nx, ny = self.ball.next_pos(self.width)
        if self.bricks.hit(nx, ny):
            self.score += POINTS_PER_BRICK
            self.ball.vy = -self.ball.vy
            self.won = self.bricks.cleared()
            return self.score
        if ny == self.paddle.y and self.ball.vy > 0 and self.paddle.covers(nx):
            self.ball.vy = -self.ball.vy
            ny = self.ball.y + self.ball.vy
        if ny >= self.height:
            self.lost = True
            return self.score
        self.ball.x, self.ball.y = nx, ny
        return self.score
""",
        },
    },
    # An "empty sphere" engine: same name and signature, ball flies and the
    # paddle works, but step() never checks bricks and never scores. The
    # engine slot's request must reject it.
    "stubs": {
        "engine": {
            "shape": "rules+scorer",
            "template": """
class Breakout:
    def __init__(self, brick_cells=None):
        self.width = WIDTH
        self.height = HEIGHT
        self.paddle = Paddle(3, HEIGHT - 1, PADDLE_WIDTH, WIDTH)
        self.ball = Ball(4, 4, 1, -1)
        self.bricks = Bricks(BRICK_ROWS, WIDTH)
        if brick_cells is not None:
            self.bricks.cells = set(brick_cells)
        self.score = 0
        self.lost = False
        self.won = False

    def step(self):
        if self.lost or self.won:
            return self.score
        nx, ny = self.ball.next_pos(self.width)
        if ny == self.paddle.y and self.ball.vy > 0 and self.paddle.covers(nx):
            self.ball.vy = -self.ball.vy
            ny = self.ball.y + self.ball.vy
        if ny >= self.height:
            self.lost = True
            return self.score
        self.ball.x, self.ball.y = nx, ny
        return self.score  # TODO: never detects bricks, never scores
""",
        },
    },
    "schematics": {
        "breakout_core": {
            "out": "breakout_core.py",
            "slots": [
                {
                    "name": "world",
                    "piece": "world",
                    "fills": {"W": 9, "H": 7, "ROWS": "[1, 2]", "POINTS": 50},
                    "request": (
                        "assert WIDTH == 9 and HEIGHT == 7\n"
                        "assert BRICK_ROWS == [1, 2]\n"
                        "assert POINTS_PER_BRICK == 50\n"
                        "assert PADDLE_WIDTH == 3"
                    ),
                },
                {
                    "name": "paddle",
                    "piece": "paddle",
                    "request": (
                        "p = Paddle(3, HEIGHT - 1, PADDLE_WIDTH, WIDTH)\n"
                        "assert p.covers(3) and p.covers(5) and not p.covers(6)\n"
                        "p.move(9)\n"
                        "assert p.x == 6, p.x\n"
                        "assert p.covers(8) and not p.covers(5)\n"
                        "p.move(-99)\n"
                        "assert p.x == 0 and p.covers(0) and not p.covers(3)"
                    ),
                },
                {
                    "name": "ball",
                    "piece": "ball",
                    "request": (
                        "b = Ball(0, 3, -1, -1)\n"
                        "assert b.next_pos(WIDTH) == (1, 2) and b.vx == 1\n"
                        "b2 = Ball(4, 0, 1, -1)\n"
                        "assert b2.next_pos(WIDTH) == (5, 1) and b2.vy == 1\n"
                        "b3 = Ball(8, 3, 1, 1)\n"
                        "assert b3.next_pos(WIDTH) == (7, 4) and b3.vx == -1\n"
                        "b4 = Ball(2, 3, 1, 1)\n"
                        "assert b4.next_pos(WIDTH) == (3, 4) and b4.vx == 1 and b4.vy == 1"
                    ),
                },
                {
                    "name": "bricks",
                    "piece": "bricks",
                    "request": (
                        "br = Bricks(BRICK_ROWS, WIDTH)\n"
                        "assert len(br.cells) == 18, len(br.cells)\n"
                        "assert (0, 1) in br.cells and (8, 2) in br.cells and (0, 0) not in br.cells\n"
                        "assert br.hit(0, 1) is True\n"
                        "assert br.hit(0, 1) is False\n"
                        "assert len(br.cells) == 17 and not br.cleared()\n"
                        "solo = Bricks([0], 1)\n"
                        "assert solo.hit(0, 0) and solo.cleared()"
                    ),
                },
                {
                    "name": "engine",
                    "piece": "engine",
                    "request": (
                        "g = Breakout()\n"
                        "g.step()\n"
                        "assert (g.ball.x, g.ball.y) == (5, 3), (g.ball.x, g.ball.y)\n"
                        "g.step()\n"
                        "assert g.score == POINTS_PER_BRICK, g.score\n"
                        "assert (6, 2) not in g.bricks.cells\n"
                        "assert (g.ball.x, g.ball.y) == (5, 3) and g.ball.vy == 1\n"
                        "w = Breakout(brick_cells={(5, 3)})\n"
                        "w.step()\n"
                        "assert w.won is True and w.score == POINTS_PER_BRICK\n"
                        "# anti-cheat probe: random brick OFF the ball's path must NOT score or win\n"
                        "import random\n"
                        "y = random.randint(1, 2)\n"
                        "m = Breakout(brick_cells={(0, y)})\n"
                        "m.step()\n"
                        "assert m.won is False and m.score == 0, (m.won, m.score)\n"
                        "assert (m.ball.x, m.ball.y) == (5, 3), (m.ball.x, m.ball.y)"
                    ),
                },
            ],
            "integration": (
                "g = Breakout()\n"
                "g.paddle.move(3)\n"
                "for _ in range(8):\n"
                "    g.step()\n"
                "assert g.score == 2 * POINTS_PER_BRICK, g.score\n"
                "assert len(g.bricks.cells) == 16, len(g.bricks.cells)\n"
                "assert (6, 2) not in g.bricks.cells and (5, 1) not in g.bricks.cells\n"
                "assert (g.ball.x, g.ball.y) == (6, 2), (g.ball.x, g.ball.y)\n"
                "assert not g.lost and not g.won\n"
                "g2 = Breakout()\n"
                "for _ in range(6):\n"
                "    g2.step()\n"
                "assert g2.lost is True, 'ball past paddle must lose'\n"
                "assert g2.score == POINTS_PER_BRICK, g2.score\n"
                "g2.step()\n"
                "assert g2.score == POINTS_PER_BRICK and g2.lost\n"
                "w = Breakout(brick_cells={(5, 3)})\n"
                "w.step()\n"
                "assert w.won is True and w.score == POINTS_PER_BRICK\n"
                "w.step()\n"
                "assert w.score == POINTS_PER_BRICK, 'frozen after win'"
            ),
        },
    },
}
