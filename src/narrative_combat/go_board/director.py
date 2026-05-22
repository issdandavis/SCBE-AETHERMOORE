"""Phase machine: drives narratively-meaningful moves across the legality kernel.

Honest framing — the arc does not emerge from free play. The director runs a fixed six-phase
sequence (opening -> first_tactic -> hidden_problem -> cost_unavoidable -> strategy_change ->
understanding_wins); the board supplies the spatial mechanics (liberties, capture, ko, qi,
treaty, study) that make each phase non-trivial. Every turn carries the board_event, the
deterministic `mechanical` truth, the rendered `prose`, and a `verifier` note asserting the
prose must honor that truth. The seed decides the climax: a capture or a brokered treaty.
"""

from __future__ import annotations

from random import Random
from typing import Any

from .governor import SearchGovernor, StudyRecord
from .kernel import Board
from .models import GoEncounter
from .translator import GoTemplateTranslator

SCHEMA = "scbe.narrative_combat.go_fight.v1"
DEFENDER_ANCHOR = (2, 2)  # the pressured group the fight forms around


class GoDirector:
    def __init__(self, encounter: GoEncounter, translator: Any | None = None, governor: SearchGovernor | None = None):
        self.encounter = encounter
        self.board = Board(size=encounter.board_size)
        self.rng = Random(encounter.seed)
        self.translator = translator if translator is not None else GoTemplateTranslator()
        self.governor = governor if governor is not None else SearchGovernor()
        self.qi: dict[int, int] = {p.color: 0 for p in encounter.parties}
        self.captures: dict[int, int] = {p.color: 0 for p in encounter.parties}
        self.claimed_qi: set = set()
        self.treaty_zone: list | None = None
        self._turns: list[dict] = []
        self._turn_index = 0

    def run(self) -> dict[str, Any]:
        attacker = self.encounter.parties[0].color
        defender = self.encounter.parties[1].color
        target = DEFENDER_ANCHOR

        self._place(attacker, (6, 6), "opening", "presence")
        self._place(defender, target, "opening", "presence")
        self._pressure(attacker, (2, 3), target, "first_tactic", "contact")
        self._pressure(attacker, (1, 2), target, "hidden_problem", "liberty_pressure")
        self._claim_qi(attacker, (4, 3), "hidden_problem")
        self._study(attacker, "hidden_problem")
        self._pressure(attacker, (3, 2), target, "cost_unavoidable", "atari")

        kill = (2, 1)
        observation = self.board.probe(attacker, kill)  # the probe move: sense without committing
        self._emit(
            "strategy_change",
            attacker,
            "probe",
            {"point": kill, "would_capture": [list(p) for p in observation.would_capture], "committed": False},
            f"probe only; would capture {[list(p) for p in observation.would_capture]}; board left unchanged",
        )

        if self.rng.random() < 0.5:
            ending = self._capture(attacker, kill, "understanding_wins")
        else:
            ending = self._treaty(defender, target, "understanding_wins")
        return self._packet(ending)

    # --- turn emitters ---

    def _emit(self, phase: str, color: int, board_event: str, mechanical: dict, verifier_claim: str) -> dict:
        event = {"phase": phase, "party": color, "board_event": board_event, "mechanical": mechanical}
        prose = self.translator.render(event, self.encounter)
        self._turn_index += 1
        turn = {
            "turn_id": f"turn_{self._turn_index:03d}",
            "phase": phase,
            "party": self.encounter.parties[color].name,
            "color": color,
            "board_event": board_event,
            "mechanical": mechanical,
            "prose": prose,
            "verifier": {"claim": verifier_claim, "source": "kernel", "rendered": bool(prose)},
        }
        self._turns.append(turn)
        return turn

    def _place(self, color: int, pt: tuple, phase: str, board_event: str) -> dict:
        result = self.board.place(color, pt)
        name = self.encounter.parties[color].name
        return self._emit(
            phase,
            color,
            board_event,
            {"point": pt, "liberties": result.liberties},
            f"{name} placed at {pt}; its group has {result.liberties} liberties",
        )

    def _pressure(self, color: int, pt: tuple, target: tuple, phase: str, board_event: str) -> dict:
        self.board.place(color, pt)
        _, libs = self.board.group_and_liberties(target)
        name = self.encounter.parties[color].name
        return self._emit(
            phase,
            color,
            board_event,
            {"point": pt, "target": target, "target_liberties": len(libs)},
            f"after {name} plays {pt}, the group at {target} has {len(libs)} liberties left",
        )

    def _claim_qi(self, color: int, pt: tuple, phase: str) -> dict:
        self.board.place(color, pt)
        name = self.encounter.parties[color].name
        for node in self.encounter.qi_nodes:
            if node.point in self.claimed_qi:
                continue
            if node.point == pt or node.point in self.board.neighbors(pt):
                self.claimed_qi.add(node.point)
                self.qi[color] += node.value
                return self._emit(
                    phase,
                    color,
                    "qi_claimed",
                    {"point": pt, "qi_node": node.point, "qi_gained": node.value, "qi_total": self.qi[color]},
                    f"{name} claimed qi node {node.point} (+{node.value}); reserve now {self.qi[color]}",
                )
        return self._emit(
            phase,
            color,
            "presence",
            {"point": pt, "liberties": self.board.liberties(pt)},
            f"{name} placed at {pt}; no qi node adjacent",
        )

    def _study(self, color: int, phase: str) -> dict:
        name = self.encounter.parties[color].name
        query = f"{self.encounter.style} techniques to break a {self.encounter.terrain_name} guard"
        results = self.governor.study(query, seed=self.encounter.seed, turn_index=self._turn_index + 1)
        decision = self.governor.audit[-1].decision if self.governor.audit else "unknown"
        return self._emit(
            phase,
            color,
            "study_revealed",
            {"query": query, "study": list(results), "backend": self.governor.backend.name, "committed": False},
            f"{name} ran a governed study: decision={decision}, backend={self.governor.backend.name}, "
            f"{len(results)} result(s)",
        )

    def _capture(self, color: int, pt: tuple, phase: str) -> str:
        result = self.board.place(color, pt)
        self.captures[color] += len(result.captured)
        name = self.encounter.parties[color].name
        captured = [list(p) for p in result.captured]
        self._emit(
            phase,
            color,
            "capture",
            {"point": pt, "captured": captured},
            f"{name} captured {captured} by playing {pt}",
        )
        return "capture"

    def _treaty(self, color: int, target: tuple, phase: str) -> str:
        group, _ = self.board.group_and_liberties(target)
        self.board.set_protected(group)
        self.treaty_zone = sorted(list(p) for p in group)
        name = self.encounter.parties[color].name
        self._emit(
            phase,
            color,
            "treaty_locked",
            {"zone": f"the ground around {target}", "protected": sorted(list(p) for p in group)},
            f"{name} locked a treaty over {sorted(group)}; those stones are now uncapturable",
        )
        return "treaty"

    # --- packet ---

    @staticmethod
    def _record(record: StudyRecord) -> dict:
        return {
            "query": record.query,
            "decision": record.decision,
            "backend": record.backend,
            "latency_ms": round(record.latency_ms, 3),
            "results": list(record.results),
        }

    def _packet(self, ending: str) -> dict[str, Any]:
        score = self.board.score()
        colors = [p.color for p in self.encounter.parties]
        return {
            "schema": SCHEMA,
            "encounter_id": self.encounter.encounter_id,
            "seed": self.encounter.seed,
            "style": self.encounter.style,
            "board_size": self.encounter.board_size,
            "terrain": {"name": self.encounter.terrain_name, "tags": self.encounter.terrain_tags},
            "parties": [
                {"name": p.name, "color": p.color, "temperament": p.temperament, "goal": p.goal}
                for p in self.encounter.parties
            ],
            "qi_nodes": [
                {"point": list(n.point), "value": n.value, "claimed": n.point in self.claimed_qi}
                for n in self.encounter.qi_nodes
            ],
            "turns": self._turns,
            "final_board": self.board.ascii(),
            "graph": self.board.graph_view(),
            "study_audit": [self._record(r) for r in self.governor.audit],
            "aftermath": {
                "ending": ending,
                "captures": {self.encounter.parties[c].name: self.captures[c] for c in colors},
                "qi": {self.encounter.parties[c].name: self.qi[c] for c in colors},
                "score": {self.encounter.parties[c].name: score.get(c, 0) for c in colors},
                "treaty_zone": self.treaty_zone,
            },
        }
