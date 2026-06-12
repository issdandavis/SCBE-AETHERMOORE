"""Stone pack: snake_core — a real, headless Snake engine.

Pure data: the mason loader builds Piece/Slot/Schematic objects from PACK.
Templates are stones (code with __H_<hole>__ chisel-points); each slot's
"request" is real code executed in place next to the stones already set.
"""

PACK = {
    "name": "snake",
    "pieces": {
        "world": {
            "shape": "config",
            "holes": ["W", "H", "FOOD"],
            "template": "W = __H_W__\nH = __H_H__\nFOOD_SEQ = __H_FOOD__",
        },
        "board": {
            "shape": "board",
            "template": """
class Board:
    def __init__(self, w, h):
        self.w = w
        self.h = h

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h
""",
        },
        "snake": {
            "shape": "mover",
            "template": """
class Snake:
    def __init__(self, start):
        self.body = [start]

    @property
    def head(self):
        return self.body[0]

    def advance(self, dx, dy, grow=False):
        nx, ny = self.head[0] + dx, self.head[1] + dy
        self.body.insert(0, (nx, ny))
        if not grow:
            self.body.pop()
        return self.head

    def bites_itself(self):
        return self.head in self.body[1:]
""",
        },
        "engine": {
            "shape": "rules+scorer",
            "template": """
class SnakeGame:
    DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

    def __init__(self, w=None, h=None, food_seq=None):
        w = W if w is None else w
        h = H if h is None else h
        self.board = Board(w, h)
        self.snake = Snake((w // 2, h // 2))
        self.food_seq = list(FOOD_SEQ if food_seq is None else food_seq)
        self.score = 0
        self.alive = True
        self.food = self._next_food()

    def _next_food(self):
        while self.food_seq:
            spot = tuple(self.food_seq.pop(0))
            if spot not in self.snake.body:
                return spot
        return None

    def step(self, direction):
        if not self.alive:
            return self.score
        dx, dy = self.DIRS[direction]
        nx, ny = self.snake.head[0] + dx, self.snake.head[1] + dy
        eats = (nx, ny) == self.food
        self.snake.advance(dx, dy, grow=eats)
        if not self.board.in_bounds(nx, ny) or self.snake.bites_itself():
            self.alive = False
            return self.score
        if eats:
            self.score += 1
            self.food = self._next_food()
        return self.score
""",
        },
    },
    # An "empty sphere" engine: looks like a SnakeGame, but step() never moves
    # the snake and never scores. The engine slot's request must reject it.
    "stubs": {
        "engine": {
            "shape": "rules+scorer",
            "template": """
class SnakeGame:
    DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

    def __init__(self, w=None, h=None, food_seq=None):
        w = W if w is None else w
        h = H if h is None else h
        self.board = Board(w, h)
        self.snake = Snake((w // 2, h // 2))
        self.score = 0
        self.alive = True
        self.food = None

    def step(self, direction):
        return self.score  # TODO: never moves, never eats, never dies
""",
        },
    },
    "schematics": {
        "snake_core": {
            "out": "snake_core.py",
            "slots": [
                {
                    "name": "world",
                    "piece": "world",
                    "fills": {"W": 7, "H": 7, "FOOD": "[(4, 3), (4, 5), (2, 5)]"},
                    "request": (
                        "assert W == 7 and H == 7\n" "assert len(FOOD_SEQ) == 3\n" "assert tuple(FOOD_SEQ[0]) == (4, 3)"
                    ),
                },
                {
                    "name": "board",
                    "piece": "board",
                    "request": (
                        "b = Board(W, H)\n"
                        "assert b.in_bounds(0, 0)\n"
                        "assert b.in_bounds(6, 6)\n"
                        "assert not b.in_bounds(7, 0)\n"
                        "assert not b.in_bounds(0, -1)"
                    ),
                },
                {
                    "name": "snake",
                    "piece": "snake",
                    "request": (
                        "s = Snake((3, 3))\n"
                        "s.advance(1, 0)\n"
                        "assert s.head == (4, 3) and len(s.body) == 1\n"
                        "s.advance(0, 1, grow=True)\n"
                        "assert s.head == (4, 4) and len(s.body) == 2\n"
                        "t = Snake((1, 1))\n"
                        "t.body = [(1, 1), (2, 1), (2, 2), (1, 2), (0, 2)]\n"
                        "t.advance(0, 1)\n"
                        "assert t.bites_itself()"
                    ),
                },
                {
                    "name": "engine",
                    "piece": "engine",
                    "request": (
                        "g = SnakeGame()\n"
                        "assert g.food == (4, 3)\n"
                        "g.step('right')\n"
                        "assert g.score == 1, g.score\n"
                        "assert g.snake.head == (4, 3), g.snake.head\n"
                        "assert len(g.snake.body) == 2\n"
                        "assert g.alive\n"
                        "# anti-cheat probe: random food position + injected food_seq must be honored\n"
                        "import random\n"
                        "dx = random.choice([-1, 1])\n"
                        "g3 = SnakeGame(food_seq=[(3 + dx, 3)])\n"
                        "g3.step('right' if dx == 1 else 'left')\n"
                        "assert g3.score == 1 and g3.snake.head == (3 + dx, 3), (g3.score, g3.snake.head)"
                    ),
                },
            ],
            "integration": (
                "g = SnakeGame()\n"
                "for mv in ['right', 'down', 'down', 'left', 'left']:\n"
                "    g.step(mv)\n"
                "assert g.score == 3, g.score\n"
                "assert len(g.snake.body) == 4, len(g.snake.body)\n"
                "assert g.alive\n"
                "assert g.food is None\n"
                "for mv in ['left', 'left', 'left']:\n"
                "    g.step(mv)\n"
                "assert g.alive is False, 'wall must kill'\n"
                "assert g.score == 3\n"
                "g2 = SnakeGame()\n"
                "g2.step('up')\n"
                "assert g2.alive and g2.score == 0"
            ),
        },
    },
}
