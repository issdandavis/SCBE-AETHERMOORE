"""Canonical ARC process tokens rendered through SCBE's existing faces.

The ARC package owns hypothesis synthesis.  This module only turns its result
into a reversible, phase-typed process receipt.  Existing CA opcodes are used
when their semantics match; missing ARC primitives remain named extensions and
never receive invented numeric opcode IDs.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from python.scbe.atomic_tokenization import map_token_to_atomic_state
from python.scbe.ca_opcode_table import OP_TABLE
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES

LANES = ("OBS", "FEAT", "REL", "HYP", "ACT", "ASSERT", "MEM")
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
FACE_ORDER = (*TONGUE_ORDER, "ARC_ATOMIC")

# These names are exact CA operations, not aliases for spatial ARC operations.
_SAFE_OPCODE_NAMES = frozenset(
    {"and", "or", "not", "xor", "eq", "neq", "min", "max", "within"}
)


def _load_arc_generic(arc_root: Path):
    expected = (arc_root / "arc_prize_2026" / "generic.py").resolve()
    if not expected.is_file():
        raise ValueError(f"ARC generic module not found: {expected}")
    root_text = str(arc_root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    importlib.invalidate_caches()
    module = importlib.import_module("arc_prize_2026.generic")
    loaded = Path(str(module.__file__)).resolve()
    if loaded != expected:
        raise ValueError(f"ARC module collision: expected {expected}, loaded {loaded}")
    if not callable(getattr(module, "synthesize_rules", None)):
        raise ValueError("ARC generic module does not expose synthesize_rules(task)")
    return module


def _shape(grid: Sequence[Sequence[int]]) -> list[int]:
    return [len(grid), len(grid[0]) if grid else 0]


def _normal_grid(grid: Any) -> tuple[tuple[int, ...], ...] | None:
    if grid is None:
        return None
    return tuple(tuple(int(value) for value in row) for row in grid)


def _fits_training(rule: Callable[[Any], Any], task: Mapping[str, Any]) -> bool:
    for pair in task.get("train", []):
        try:
            actual = rule(_normal_grid(pair["input"]))
        except (IndexError, KeyError, TypeError, ValueError):
            return False
        if _normal_grid(actual) != _normal_grid(pair["output"]):
            return False
    return bool(task.get("train"))


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
    return cleaned or "UNKNOWN"


def _atomic_face(canonical_id: str, lane: str) -> dict[str, Any]:
    state = map_token_to_atomic_state(
        canonical_id,
        language="arc",
        context_class=lane.lower(),
    )
    return {
        "face": "canonical_arc_atomic",
        "canonical_id": canonical_id,
        "utf8_hex": canonical_id.encode("utf-8").hex(),
        "semantic_class": state.semantic_class,
        "element": {
            "symbol": state.element.symbol,
            "atomic_number": state.element.Z,
            "group": state.element.group,
            "period": state.element.period,
        },
        "tau": state.tau.as_dict(),
        "roundtrip": bytes.fromhex(canonical_id.encode("utf-8").hex()).decode("utf-8")
        == canonical_id,
    }


def _render_record(
    lane: str,
    canonical_id: str,
    payload: Mapping[str, Any],
    *,
    execution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = canonical_id.encode("utf-8")
    faces: dict[str, Any] = {}
    reversible = True
    for code in TONGUE_ORDER:
        lower = code.lower()
        encoded = SACRED_TONGUE_TOKENIZER.encode_bytes(lower, raw)
        decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(lower, encoded)
        roundtrip = decoded == raw
        reversible = reversible and roundtrip
        faces[code] = {
            "tongue": TONGUES[lower].name,
            "tokens": encoded,
            "roundtrip": roundtrip,
        }
    atomic = _atomic_face(canonical_id, lane)
    faces["ARC_ATOMIC"] = atomic
    reversible = reversible and bool(atomic["roundtrip"])
    record: dict[str, Any] = {
        "lane": lane,
        "canonical_id": canonical_id,
        "payload": dict(payload),
        "faces": faces,
        "reversible": reversible,
    }
    if lane == "ACT":
        record["execution"] = dict(execution or {"executable": False})
    elif execution is not None:
        raise ValueError("execution metadata is only valid on ACT records")
    return record


def _action_specs(rule_name: str) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    opcode_by_name = {entry.name: entry for entry in OP_TABLE.values()}
    words = re.findall(r"[a-z][a-z0-9_]*", rule_name.lower())
    specs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    for name in words:
        if name not in _SAFE_OPCODE_NAMES or name not in opcode_by_name or name in seen:
            continue
        seen.add(name)
        entry = opcode_by_name[name]
        specs.append(
            (
                f"ARC.ACT.OPCODE.{name.upper()}",
                {"rule": rule_name, "primitive": name},
                {
                    "executable": True,
                    "registry": "python.scbe.ca_opcode_table.OP_TABLE",
                    "op_id": entry.op_id,
                    "opcode_hex": f"0x{entry.op_id:02X}",
                    "name": entry.name,
                    "trit": entry.trit.tolist(),
                },
            )
        )

    family = rule_name.split(":", 1)[0]
    if family not in _SAFE_OPCODE_NAMES:
        specs.insert(
            0,
            (
                f"ARCX.ACT.{_slug(family)}",
                {"rule": rule_name, "primitive": family, "extension": True},
                {
                    "executable": False,
                    "registry": None,
                    "op_id": None,
                    "reason": "ARC primitive has no semantically exact CA opcode",
                },
            ),
        )
    return specs


def build_arc_token_process(
    *,
    task_id: str,
    task: Mapping[str, Any],
    arc_root: Path,
    max_hypotheses: int = 4,
) -> dict[str, Any]:
    """Call ARC synthesis and emit a reversible seven-face process receipt."""

    if max_hypotheses < 1:
        raise ValueError("max_hypotheses must be at least 1")
    if not isinstance(task.get("train"), list) or not isinstance(task.get("test"), list):
        raise ValueError("ARC task must contain train and test lists")

    generic = _load_arc_generic(arc_root.resolve())
    synthesized = list(generic.synthesize_rules(dict(task)))
    exact_rules = [item for item in synthesized if _fits_training(item[2], task)]
    hypotheses = exact_rules[:max_hypotheses]

    train_shapes = [
        {"input": _shape(pair["input"]), "output": _shape(pair["output"])}
        for pair in task["train"]
    ]
    same_shape = sum(item["input"] == item["output"] for item in train_shapes)
    colors = sorted(
        {
            int(value)
            for pair in task["train"]
            for side in ("input", "output")
            for row in pair[side]
            for value in row
        }
    )

    specs: list[tuple[str, str, dict[str, Any], dict[str, Any] | None]] = [
        ("OBS", "ARC.OBS.TASK", {"task_id": task_id}, None),
        (
            "FEAT",
            "ARC.FEAT.GRID_SHAPES",
            {"train_shapes": train_shapes, "test_shapes": [_shape(x["input"]) for x in task["test"]]},
            None,
        ),
        ("FEAT", "ARC.FEAT.COLOR_SET", {"colors": colors, "cardinality": len(colors)}, None),
        (
            "REL",
            "ARC.REL.TRAIN_INPUT_OUTPUT",
            {
                "pair_count": len(task["train"]),
                "same_shape_pairs": same_shape,
                "changed_shape_pairs": len(train_shapes) - same_shape,
            },
            None,
        ),
    ]
    for index, (name, complexity, _rule) in enumerate(hypotheses):
        specs.append(
            (
                "HYP",
                f"ARC.HYP.CANDIDATE.{index:02d}",
                {"rule": name, "complexity": complexity, "train_exact": True},
                None,
            )
        )

    chosen_rule = hypotheses[0][0] if hypotheses else None
    if chosen_rule:
        for canonical_id, payload, execution in _action_specs(chosen_rule):
            specs.append(("ACT", canonical_id, payload, execution))

    promoted = bool(hypotheses)
    assertion_id = "ARC.ASSERT.TRAIN_EXACT" if promoted else "ARC.ASSERT.UNPROVEN"
    specs.extend(
        [
            (
                "ASSERT",
                assertion_id,
                {
                    "passed": promoted,
                    "exact_candidate_count": len(exact_rules),
                    "gate": "PASS" if promoted else "HOLD",
                },
                None,
            ),
            (
                "MEM",
                "ARC.MEM.PROCESS_RECEIPT",
                {
                    "task_id": task_id,
                    "chosen_rule": chosen_rule,
                    "promotion": "PASS" if promoted else "HOLD",
                },
                None,
            ),
        ]
    )

    records = [
        _render_record(lane, canonical_id, payload, execution=execution)
        for lane, canonical_id, payload, execution in specs
    ]
    return {
        "schema_version": "geoseal_arc_token_process_v1",
        "ok": True,
        "task_id": task_id,
        "arc_module": {
            "path": str(Path(generic.__file__).resolve()),
            "call": "arc_prize_2026.generic.synthesize_rules",
        },
        "lane_order": list(LANES),
        "face_order": list(FACE_ORDER),
        "records": records,
        "promotion": {
            "gate": "PASS" if promoted else "HOLD",
            "assertion": assertion_id,
            "chosen_rule": chosen_rule,
        },
        "reversible": all(record["reversible"] for record in records),
    }
