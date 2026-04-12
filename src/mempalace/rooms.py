from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.ca_lexicon import LEXICON, TONGUE_NAMES, LexiconEntry


@dataclass
class Room:
    op_id: int
    name: str
    wing: str
    entry: LexiconEntry
    corridors: Dict[str, List[int]] = field(default_factory=dict)

    def neighbors(self) -> Set[int]:
        out: Set[int] = set()
        for targets in self.corridors.values():
            out.update(targets)
        out.discard(self.op_id)
        return out


_WING_GATES = ((0x0F, 0x10), (0x1F, 0x20), (0x2F, 0x30))


def build_palace() -> Dict[int, Room]:
    palace: Dict[int, Room] = {}
    for op_id, entry in LEXICON.items():
        palace[op_id] = Room(
            op_id=op_id,
            name=entry.name,
            wing=entry.band,
            entry=entry,
            corridors={},
        )

    for op_id, room in palace.items():
        band_corridor: List[int] = []
        if op_id + 1 in palace and palace[op_id + 1].wing == room.wing:
            band_corridor.append(op_id + 1)
        if op_id - 1 in palace and palace[op_id - 1].wing == room.wing:
            band_corridor.append(op_id - 1)
        room.corridors["band"] = band_corridor

    for a, b in _WING_GATES:
        palace[a].corridors.setdefault("gate", []).append(b)
        palace[b].corridors.setdefault("gate", []).append(a)

    for t_idx, t_name in enumerate(TONGUE_NAMES):
        if t_name == "CA":
            continue
        active = [op_id for op_id, room in palace.items() if room.entry.trit[t_idx] == 1]
        for op_id in active:
            palace[op_id].corridors.setdefault(t_name, [])
            for other in active:
                if other != op_id:
                    palace[op_id].corridors[t_name].append(other)

    return palace
