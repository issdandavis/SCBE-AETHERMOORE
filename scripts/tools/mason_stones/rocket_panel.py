"""Stone pack: rocket_core — a real, headless rocket control panel.

Pure data: the mason loader builds Piece/Slot/Schematic objects from PACK.
Templates are stones (code with __H_<hole>__ chisel-points); each slot's
"request" is real code executed in place next to the stones already set.
"""

PACK = {
    "name": "rocket_panel",
    "pieces": {
        "telemetry": {
            "shape": "sensors+clamp",
            "holes": ["FUEL_MAX", "ALT_MAX"],
            "template": """
class Telemetry:
    LIMITS = {'fuel': (0, __H_FUEL_MAX__), 'altitude': (0, __H_ALT_MAX__), 'velocity': (-50, 400)}

    def __init__(self):
        self.readings = {key: 0 for key in self.LIMITS}

    def record(self, key, value):
        lo, hi = self.LIMITS[key]
        self.readings[key] = min(max(value, lo), hi)
        return self.readings[key]

    def read(self, key):
        return self.readings[key]
""",
        },
        "stages": {
            "shape": "sequencer",
            "template": """
class StageStack:
    def __init__(self, stages):
        self.stages = [{'name': n, 'fuel': f, 'burn': b} for (n, f, b) in stages]
        self.separated = []

    @property
    def active(self):
        return self.stages[0] if self.stages else None

    def burn_tick(self):
        stage = self.active
        if stage is None:
            return 0
        burned = min(stage['fuel'], stage['burn'])
        stage['fuel'] -= burned
        if stage['fuel'] <= 0:
            self.separated.append(self.stages.pop(0)['name'])
        return burned
""",
        },
        "countdown": {
            "shape": "ticker",
            "template": """
class Countdown:
    def __init__(self, t_minus):
        self.t = t_minus
        self.holding = False
        self.ignition = False

    def hold(self):
        self.holding = True

    def resume(self):
        self.holding = False

    def tick(self):
        if not (self.ignition or self.holding):
            self.t = max(0, self.t - 1)
            self.ignition = self.t == 0
        return self.t
""",
        },
        "panel": {
            "shape": "facade",
            "holes": ["LIFT", "TARGET"],
            "template": """
class ControlPanel:
    LIFT = __H_LIFT__
    TARGET = __H_TARGET__

    def __init__(self, stages, t_minus=3):
        self.telemetry = Telemetry()
        self.stack = StageStack(stages)
        self.countdown = Countdown(t_minus)
        self.armed = self.aborted = self.flying = self.mission_complete = False
        self.telemetry.record('fuel', sum(st['fuel'] for st in self.stack.stages))

    def arm(self):
        if not self.aborted:
            self.armed = True
        return self.armed

    def tick(self):
        if self.aborted or not self.armed:
            return self.status()
        if not self.flying:
            self.countdown.tick()
            self.flying = self.countdown.ignition
            return self.status()
        t = self.telemetry
        burned = self.stack.burn_tick()
        t.record('fuel', t.read('fuel') - burned)
        t.record('velocity', burned * self.LIFT)
        t.record('altitude', t.read('altitude') + t.read('velocity'))
        self.mission_complete = t.read('altitude') >= self.TARGET
        return self.status()

    def abort(self):
        self.aborted = True
        self.armed = self.flying = False
        self.countdown.hold()
        for st in self.stack.stages:
            st['burn'] = 0
        self.telemetry.record('velocity', 0)
        return self.status()

    def status(self):
        s = {'armed': self.armed, 'aborted': self.aborted, 'flying': self.flying}
        s.update(self.telemetry.readings)
        s['t_minus'] = self.countdown.t
        s['stage'] = self.stack.active['name'] if self.stack.active else None
        s['separated'] = list(self.stack.separated)
        return s
""",
        },
    },
    # An "empty sphere" panel: arms, counts down, and even flies — but abort()
    # never safes anything. The panel slot's request must reject it.
    "stubs": {
        "panel": {
            "shape": "facade",
            "holes": ["LIFT", "TARGET"],
            "template": """
class ControlPanel:
    LIFT = __H_LIFT__
    TARGET = __H_TARGET__

    def __init__(self, stages, t_minus=3):
        self.telemetry = Telemetry()
        self.stack = StageStack(stages)
        self.countdown = Countdown(t_minus)
        self.armed = self.aborted = self.flying = self.mission_complete = False
        self.telemetry.record('fuel', sum(st['fuel'] for st in self.stack.stages))

    def arm(self):
        self.armed = True
        return self.armed

    def tick(self):
        if not self.armed:
            return self.status()
        if not self.flying:
            self.countdown.tick()
            self.flying = self.countdown.ignition
            return self.status()
        t = self.telemetry
        burned = self.stack.burn_tick()
        t.record('fuel', t.read('fuel') - burned)
        t.record('velocity', burned * self.LIFT)
        t.record('altitude', t.read('altitude') + t.read('velocity'))
        return self.status()

    def abort(self):
        return self.status()  # TODO: never cuts burn, never marks aborted, never refuses launch

    def status(self):
        s = {'armed': self.armed, 'aborted': self.aborted, 'flying': self.flying}
        s.update(self.telemetry.readings)
        s['t_minus'] = self.countdown.t
        s['stage'] = self.stack.active['name'] if self.stack.active else None
        s['separated'] = list(self.stack.separated)
        return s
""",
        },
    },
    "schematics": {
        "rocket_core": {
            "out": "rocket_core.py",
            "slots": [
                {
                    "name": "telemetry",
                    "piece": "telemetry",
                    "fills": {"FUEL_MAX": 100, "ALT_MAX": 10000},
                    "request": (
                        "t = Telemetry()\n"
                        "assert t.record('fuel', 120) == 100, 'must clamp to FUEL_MAX'\n"
                        "assert t.record('fuel', -5) == 0 and t.record('altitude', 50) == 50\n"
                        "assert t.record('velocity', 999) == 400\n"
                        "try:\n"
                        "    t.record('thrust', 1)\n"
                        "    raise AssertionError('unknown channel must raise')\n"
                        "except KeyError:\n"
                        "    pass"
                    ),
                },
                {
                    "name": "stages",
                    "piece": "stages",
                    "request": (
                        "s = StageStack([('booster', 6, 3), ('upper', 4, 2)])\n"
                        "assert s.active['name'] == 'booster'\n"
                        "assert s.burn_tick() == 3 and s.burn_tick() == 3\n"
                        "assert s.separated == ['booster'] and s.active['name'] == 'upper'\n"
                        "assert s.burn_tick() == 2 and s.burn_tick() == 2\n"
                        "assert s.active is None and s.burn_tick() == 0\n"
                        "assert s.separated == ['booster', 'upper']"
                    ),
                },
                {
                    "name": "countdown",
                    "piece": "countdown",
                    "request": (
                        "c = Countdown(3)\n"
                        "assert c.tick() == 2\n"
                        "c.hold()\n"
                        "assert c.tick() == 2 and not c.ignition, 'hold must freeze the clock'\n"
                        "c.resume()\n"
                        "assert c.tick() == 1 and c.tick() == 0\n"
                        "assert c.ignition is True\n"
                        "assert c.tick() == 0, 'must stay at T-0'"
                    ),
                },
                {
                    "name": "panel",
                    "piece": "panel",
                    "fills": {"LIFT": 10, "TARGET": 100},
                    "request": (
                        "p = ControlPanel([('booster', 6, 3), ('upper', 4, 2)], t_minus=2)\n"
                        "assert p.arm() is True\n"
                        "p.tick(); p.tick()\n"
                        "assert p.flying is True\n"
                        "s = p.tick()\n"
                        "assert s['altitude'] == 30 and s['fuel'] == 7, s\n"
                        "s = p.abort()\n"
                        "assert s['aborted'] is True and s['armed'] is False and s['flying'] is False, s\n"
                        "assert s['velocity'] == 0, 'abort must zero velocity'\n"
                        "assert p.tick()['altitude'] == 30, 'abort must stop altitude gain'\n"
                        "assert p.arm() is False, 'abort must refuse re-arm'\n"
                        "# anti-cheat probe: random stage config, altitude must equal the burn math\n"
                        "import random\n"
                        "b = random.randint(1, 3)\n"
                        "n = random.randint(2, 4)\n"
                        "rp = ControlPanel([('r', b * n, b)], t_minus=1)\n"
                        "assert rp.arm() is True\n"
                        "rp.tick()\n"
                        "assert rp.flying is True\n"
                        "alt = 0\n"
                        "for _ in range(n):\n"
                        "    alt += b * ControlPanel.LIFT\n"
                        "    s = rp.tick()\n"
                        "    assert s['altitude'] == alt, (s['altitude'], alt)\n"
                        "assert s['fuel'] == 0 and s['separated'] == ['r'] and rp.stack.active is None, s"
                    ),
                },
            ],
            "integration": (
                "panel = ControlPanel([('booster', 6, 3), ('upper', 4, 2)], t_minus=3)\n"
                "panel.tick()\n"
                "assert panel.status()['t_minus'] == 3, 'no countdown before arm'\n"
                "assert panel.arm() is True\n"
                "panel.tick(); panel.tick(); panel.tick()\n"
                "assert panel.flying is True and panel.status()['t_minus'] == 0\n"
                "assert panel.tick()['altitude'] == 30\n"
                "s = panel.tick()\n"
                "assert s['altitude'] == 60 and s['separated'] == ['booster'] and s['stage'] == 'upper', s\n"
                "assert panel.tick()['altitude'] == 80\n"
                "s = panel.tick()\n"
                "assert s['altitude'] == 100 and s['fuel'] == 0 and s['stage'] is None, s\n"
                "assert s['separated'] == ['booster', 'upper'] and panel.mission_complete is True\n"
                "ab = ControlPanel([('solo', 4, 2)], t_minus=1)\n"
                "ab.arm()\n"
                "ab.tick()\n"
                "assert ab.tick()['altitude'] == 20\n"
                "ab.abort()\n"
                "ab.tick(); ab.tick()\n"
                "s = ab.status()\n"
                "assert s['altitude'] == 20 and s['velocity'] == 0 and s['aborted'] is True, s\n"
                "assert ab.arm() is False and ab.mission_complete is False"
            ),
        },
    },
}
