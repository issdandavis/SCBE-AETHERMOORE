"""Local Terminus guild runner for agent training pairs.

This is a deterministic command-line harness inspired by the forked Terminus
game, the repo's ChoiceScript branching engine, and the Godot terminal/client
pattern. It gives agents a small game they can play without a browser, then
writes command/result pairs at save checkpoints for SFT and benchmark replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "terminus_training"


@dataclass(frozen=True)
class Enemy:
    name: str
    problem: str
    answer: str
    domain: str


@dataclass
class Room:
    name: str
    description: str
    exits: list[str] = field(default_factory=list)
    items: dict[str, str] = field(default_factory=dict)
    enemies: dict[str, Enemy] = field(default_factory=dict)
    checkpoint: bool = False


@dataclass
class StepRecord:
    step: int
    room: str
    command: str
    response: str
    score_delta: int
    checkpoint: bool
    metadata: dict[str, Any]


def build_world() -> dict[str, Room]:
    world: dict[str, Room] = {
        "Home": Room(
            "Home",
            "Home base. Use ls, cd GuildDistrict, or cd WesternForest.",
            exits=["GuildDistrict", "WesternForest", "MIT"],
            items={
                "WelcomeLetter": "Use ls to survey, cd Place to move, less Item to inspect, and solve Enemy answer in MathArena.",
            },
            checkpoint=True,
        ),
        "GuildDistrict": Room(
            "GuildDistrict",
            "A hub of code-language guilds and advanced representation guilds.",
            exits=[
                "PythonGuild",
                "JavaScriptGuild",
                "RustGuild",
                "HaskellGuild",
                "BinaryGuild",
                "HexadecimalGuild",
                "AdvancedMathematicsGuild",
                "Home",
            ],
            items={
                "GuildDirectory": (
                    "PythonGuild, JavaScriptGuild, RustGuild, HaskellGuild, BinaryGuild, "
                    "HexadecimalGuild, and AdvancedMathematicsGuild are open."
                ),
                "GuildClerk": "Read a Board, enter MathArena, inspect enemies, then solve them.",
            },
            checkpoint=True,
        ),
        "PythonGuild": Room(
            "PythonGuild",
            "Readable automation guild.",
            exits=["GuildDistrict"],
            items={"Board": "Intent -> function -> test. Keep the data shape visible."},
            checkpoint=True,
        ),
        "JavaScriptGuild": Room(
            "JavaScriptGuild",
            "Browser and event-loop guild.",
            exits=["GuildDistrict"],
            items={"Board": "Event -> handler -> state update -> UI result."},
            checkpoint=True,
        ),
        "RustGuild": Room(
            "RustGuild",
            "Ownership and boundary guild.",
            exits=["GuildDistrict"],
            items={"Board": "Name ownership, borrowing, mutation, and failure states before coding."},
            checkpoint=True,
        ),
        "HaskellGuild": Room(
            "HaskellGuild",
            "Typed transformation guild.",
            exits=["GuildDistrict"],
            items={"Board": "Break the task into pure functions and compose them."},
            checkpoint=True,
        ),
        "BinaryGuild": Room(
            "BinaryGuild",
            "Bit-level representation guild.",
            exits=["GuildDistrict"],
            items={"Board": "Check width, carries, masks, and bitwise operators."},
            checkpoint=True,
        ),
        "HexadecimalGuild": Room(
            "HexadecimalGuild",
            "Compact byte-notation guild.",
            exits=["GuildDistrict"],
            items={"Board": "Translate hex to binary when the byte shape is unclear."},
            checkpoint=True,
        ),
        "AdvancedMathematicsGuild": Room(
            "AdvancedMathematicsGuild",
            "Math guild. Problems are modeled as enemies with givens, targets, and win conditions.",
            exits=["GuildDistrict", "MathArena"],
            items={
                "EnemyMethod": "less EnemyName to inspect, then solve EnemyName answer.",
                "Board": "Identify givens, target, allowed move, and proof of defeat.",
            },
            checkpoint=True,
        ),
        "MathArena": Room(
            "MathArena",
            "A benchmark room for math enemies.",
            exits=["AdvancedMathematicsGuild"],
            items={"ArenaRules": "Each solve command produces an action/result training pair."},
            enemies={
                "LinearEquationEnemy": Enemy("LinearEquationEnemy", "Solve 2x + 6 = 14.", "4", "algebra"),
                "BinaryMaskEnemy": Enemy("BinaryMaskEnemy", "Compute 1010 AND 1100.", "1000", "binary"),
                "HexCarryEnemy": Enemy("HexCarryEnemy", "Compute 0x0F + 0x01.", "0x10", "hexadecimal"),
                "ProofGateEnemy": Enemy("ProofGateEnemy", "If A implies B, and A is true, what follows?", "B", "logic"),
            },
            checkpoint=True,
        ),
        "WesternForest": Room(
            "WesternForest",
            "Original Terminus path toward the academy.",
            exits=["Home", "SpellCastingAcademy"],
            items={"Sign": "Spell Casting Academy ahead."},
        ),
        "SpellCastingAcademy": Room(
            "SpellCastingAcademy",
            "Original lesson path.",
            exits=["WesternForest", "Lessons"],
            items={"HurryingStudent": "Try Lessons for movement mechanics."},
        ),
        "Lessons": Room(
            "Lessons",
            "Movement lesson path.",
            exits=["SpellCastingAcademy"],
            items={"Professor": "mv Item Location moves an item when allowed."},
            checkpoint=True,
        ),
        "MIT": Room("MIT", "Original advanced campus route.", exits=["Home"], items={"AdmissionLetter": "Welcome to MIT."}),
    }
    return world


def _match(name: str, choices: Iterable[str]) -> str | None:
    target = "".join(str(name).lower().split())
    for choice in choices:
        compact = "".join(choice.lower().split())
        if compact == target:
            return choice
    for choice in choices:
        compact = "".join(choice.lower().split())
        if compact.startswith(target) or target.startswith(compact):
            return choice
    return None


class TerminusTrainingSession:
    def __init__(self, world: dict[str, Room] | None = None, agent_id: str = "agent"):
        self.world = world or build_world()
        self.agent_id = agent_id
        self.room = "Home"
        self.score = 0
        self.step = 0
        self.solved: set[str] = set()
        self.records: list[StepRecord] = []

    def run(self, command: str) -> str:
        self.step += 1
        command = " ".join(command.strip().split())
        response, delta, metadata = self._dispatch(command)
        self.score += delta
        room = self.world[self.room]
        checkpoint = room.checkpoint or bool(metadata.get("solved_enemy"))
        self.records.append(
            StepRecord(
                step=self.step,
                room=self.room,
                command=command,
                response=response,
                score_delta=delta,
                checkpoint=checkpoint,
                metadata=metadata,
            )
        )
        return response

    def _dispatch(self, command: str) -> tuple[str, int, dict[str, Any]]:
        if not command:
            return "No command entered.", 0, {"event_type": "empty"}
        parts = command.split()
        verb = parts[0].lower()
        args = parts[1:]
        room = self.world[self.room]

        if verb in {"look", "ls"}:
            exits = "\n".join(room.exits) or "None"
            items = "\n".join(room.items.keys()) or "None"
            enemies = "\n".join(room.enemies.keys()) or "None"
            return f"Locations:\n{exits}\nItems:\n{items}\nEnemies:\n{enemies}", 1, {"event_type": "survey"}

        if verb in {"read", "inspect", "less"}:
            if not args:
                return "Use less ItemName.", 0, {"event_type": "bad_read"}
            name = _match("".join(args), list(room.items) + list(room.enemies))
            if not name:
                return f"There is no {' '.join(args)} here.", 0, {"event_type": "missed_read"}
            if name in room.items:
                return room.items[name], 2, {"event_type": "read_item", "item": name}
            enemy = room.enemies[name]
            return (
                f"Enemy: {enemy.name}\nProblem: {enemy.problem}\nDomain: {enemy.domain}\nCommand: solve {enemy.name} answer",
                2,
                {"event_type": "inspect_enemy", "enemy": enemy.name, "domain": enemy.domain},
            )

        if verb in {"go", "enter", "cd"}:
            if not args:
                self.room = "Home"
                return "Returned Home.", 1, {"event_type": "move", "target": "Home"}
            target_arg = "".join(args)
            if target_arg == "..":
                target_arg = "GuildDistrict" if self.room.endswith("Guild") else "Home"
            target = _match(target_arg, room.exits)
            if not target:
                item = _match(target_arg, room.items)
                if item:
                    return f"{item} is an item. Use less {item}.", 0, {"event_type": "wrong_target_type", "item": item}
                return f"No route to {' '.join(args)} from {self.room}.", 0, {"event_type": "bad_route"}
            self.room = target
            return f"Moved to {target}. {self.world[target].description}", 3, {"event_type": "move", "target": target}

        if verb in {"solve", "attack"}:
            if len(args) < 2:
                return "Use solve EnemyName answer.", 0, {"event_type": "bad_solve"}
            enemy_name = _match(args[0], room.enemies)
            if not enemy_name:
                return "No active enemy by that name in this room.", 0, {"event_type": "missing_enemy"}
            answer = "".join(args[1:])
            enemy = room.enemies[enemy_name]
            ok = answer.lower() == enemy.answer.lower()
            if ok:
                self.solved.add(enemy.name)
                return (
                    f"{enemy.name} defeated. Answer {enemy.answer} matched the win condition.",
                    10,
                    {"event_type": "solve_enemy", "enemy": enemy.name, "domain": enemy.domain, "solved_enemy": True},
                )
            return (
                f"{enemy.name} resisted. Inspect the givens with less {enemy.name}.",
                -1,
                {"event_type": "failed_enemy", "enemy": enemy.name, "domain": enemy.domain},
            )

        if verb in {"hint", "help"}:
            return self.hint(), 0, {"event_type": "hint"}

        return f"Unknown command: {parts[0]}", 0, {"event_type": "unknown_command"}

    def hint(self) -> str:
        if self.room == "Home":
            return "Run cd GuildDistrict."
        if self.room == "GuildDistrict":
            return "Run less GuildDirectory, then cd AdvancedMathematicsGuild."
        if self.room == "AdvancedMathematicsGuild":
            return "Run less EnemyMethod, then cd MathArena."
        if self.room == "MathArena":
            return "Run less LinearEquationEnemy, then solve LinearEquationEnemy 4."
        return "Use ls, less Item, cd Place, and solve Enemy answer."

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": "terminus_training_session_v1",
            "agent_id": self.agent_id,
            "final_room": self.room,
            "score": self.score,
            "steps": self.step,
            "solved": sorted(self.solved),
            "checkpoint_count": sum(1 for record in self.records if record.checkpoint),
        }


BENCHMARK_PATHS: dict[str, list[str]] = {
    "guild_math_intro": [
        "ls",
        "cd GuildDistrict",
        "less GuildDirectory",
        "cd AdvancedMathematicsGuild",
        "less EnemyMethod",
        "cd MathArena",
        "less LinearEquationEnemy",
        "solve LinearEquationEnemy 4",
    ],
    "representation_guilds": [
        "cd GuildDistrict",
        "cd BinaryGuild",
        "less Board",
        "cd ..",
        "cd HexadecimalGuild",
        "less Board",
        "cd ..",
        "cd AdvancedMathematicsGuild",
        "cd MathArena",
        "solve BinaryMaskEnemy 1000",
        "solve HexCarryEnemy 0x10",
    ],
}


def session_id(agent_id: str, scenario: str) -> str:
    digest = hashlib.sha256(f"{agent_id}:{scenario}:{time.time_ns()}".encode("utf-8")).hexdigest()[:12]
    return f"{scenario}-{digest}"


def write_session(session: TerminusTrainingSession, out_dir: Path, scenario: str) -> dict[str, Any]:
    sid = session_id(session.agent_id, scenario)
    session_dir = out_dir / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    events_path = session_dir / f"{sid}.jsonl"
    sft_path = session_dir / f"{sid}.sft.jsonl"
    manifest_path = session_dir / f"{sid}.manifest.json"

    with events_path.open("w", encoding="utf-8") as events, sft_path.open("w", encoding="utf-8") as sft:
        previous_response = "You are in Home. Use ls or cd GuildDistrict."
        for record in session.records:
            row = {
                "schema_version": "terminus_training_event_v1",
                "session_id": sid,
                "agent_id": session.agent_id,
                **record.__dict__,
            }
            events.write(json.dumps(row, ensure_ascii=False) + "\n")
            if record.checkpoint:
                sft.write(
                    json.dumps(
                        {
                            "id": f"{sid}:{record.step}",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "Play Terminus through command-line actions. Prefer valid routes, inspect before solving, and solve math enemies exactly.",
                                },
                                {"role": "user", "content": previous_response},
                                {"role": "assistant", "content": record.command},
                                {"role": "user", "content": record.response},
                            ],
                            "metadata": {
                                "track": "terminus_guild_agent_training",
                                "scenario": scenario,
                                "room": record.room,
                                "score_delta": record.score_delta,
                                **record.metadata,
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            previous_response = record.response

    manifest = {
        **session.summary(),
        "scenario": scenario,
        "session_id": sid,
        "events_path": str(events_path),
        "sft_path": str(sft_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {**manifest, "manifest_path": str(manifest_path)}


def run_scripted(commands: list[str], *, agent_id: str, scenario: str, out_dir: Path) -> dict[str, Any]:
    session = TerminusTrainingSession(agent_id=agent_id)
    for command in commands:
        session.run(command)
    return write_session(session, out_dir, scenario)


def run_benchmark(out_dir: Path, agent_id: str = "benchmark-agent") -> dict[str, Any]:
    runs = []
    for scenario, commands in BENCHMARK_PATHS.items():
        runs.append(run_scripted(commands, agent_id=agent_id, scenario=scenario, out_dir=out_dir))
    total_score = sum(run["score"] for run in runs)
    solved = sorted({enemy for run in runs for enemy in run["solved"]})
    report = {
        "schema_version": "terminus_training_benchmark_v1",
        "runs": runs,
        "total_score": total_score,
        "solved": solved,
        "pass": total_score >= 45 and {"LinearEquationEnemy", "BinaryMaskEnemy", "HexCarryEnemy"}.issubset(solved),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "latest_benchmark.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Terminus guild training sessions locally.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a named scripted scenario")
    p_run.add_argument("--scenario", choices=sorted(BENCHMARK_PATHS), default="guild_math_intro")
    p_run.add_argument("--agent-id", default="local-agent")
    p_run.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p_run.add_argument("--json", action="store_true")

    p_bench = sub.add_parser("benchmark", help="Run built-in benchmark paths")
    p_bench.add_argument("--agent-id", default="benchmark-agent")
    p_bench.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p_bench.add_argument("--json", action="store_true")

    p_play = sub.add_parser("play", help="Run commands passed on stdin or --command")
    p_play.add_argument("--command", action="append", default=[])
    p_play.add_argument("--agent-id", default="manual-agent")
    p_play.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p_play.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "run":
        payload = run_scripted(BENCHMARK_PATHS[args.scenario], agent_id=args.agent_id, scenario=args.scenario, out_dir=args.out_dir)
    elif args.cmd == "benchmark":
        payload = run_benchmark(args.out_dir, agent_id=args.agent_id)
    else:
        commands = args.command or [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        payload = run_scripted(commands, agent_id=args.agent_id, scenario="manual", out_dir=args.out_dir)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"score={payload.get('score', payload.get('total_score'))} pass={payload.get('pass', 'n/a')}")
        if "sft_path" in payload:
            print(payload["sft_path"])
        if "report_path" in payload:
            print(payload["report_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
