"""Compound receipt for one agent-math atom.

A cell stores three faces: the math ledger, the word, and the code token.
Match, math, and science stay three scores. An overlap is several candidates
on one board cell until measurement. A hyperatom is that cell plus at most
three child hyperatoms. A compound is a chain of hyperatoms. The chain is
admitted only when every cell has been measured and every science score
reaches the threshold.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from python.scbe.chemistry_science_score import THRESHOLD, score_formulas

SCHEMA = "aethermoore_chemistry_compound_receipt_v1"
BOARD_SIZE = 256
BRANCH_LIMIT = 3
TRIT_REFUSED = -1
TRIT_OPEN = 0
TRIT_ADMITTED = 1

BOUNDARY = (
    "The receipt stores math, word, and code as three faces. "
    "Match, math, and science stay separate scores and are not added together. "
    "The trit is the measurement of the cell: open, admitted, or refused. "
    "A chain is admitted only when every cell reaches the science threshold. "
    "The word and the code are carriers. They are not parsed as elements."
)


def _board(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("board index must be an integer from 0 through 255")
    if value < 0 or value >= BOARD_SIZE:
        raise ValueError("board index must be an integer from 0 through 255")
    return value


def _text(value: Any, face: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{face} face must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{face} face must be a string")
    return text


def _candidate(spec: dict[str, Any]) -> dict[str, str]:
    return {
        "formula": _text(spec.get("formula"), "formula"),
        "word": _text(spec.get("word"), "word"),
        "code": _text(spec.get("code"), "code"),
    }


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the caller spec with faces checked and children capped at three."""
    if not isinstance(spec, dict):
        raise ValueError("a compound node must be an object")
    children = spec.get("children") or []
    if not isinstance(children, list):
        raise ValueError("children must be a list")
    if len(children) > BRANCH_LIMIT:
        raise ValueError("a hyperatom has at most 3 children")
    normalized_children = [normalize_spec(child) for child in children]
    if "overlap" in spec and "formula" in spec:
        raise ValueError("a node is one formula or an overlap, not both")
    if "overlap" in spec:
        rows = spec.get("overlap")
        if not isinstance(rows, list) or not rows:
            raise ValueError("an overlap needs at least one candidate")
        return {
            "reference": _text(spec.get("reference"), "reference"),
            "board_index": _board(spec.get("board_index")),
            "measured": bool(spec.get("measured", False)),
            "overlap": [_candidate(row) for row in rows],
            "children": normalized_children,
        }
    return {
        "formula": _text(spec.get("formula"), "formula"),
        "reference": _text(spec.get("reference"), "reference"),
        "word": _text(spec.get("word"), "word"),
        "code": _text(spec.get("code"), "code"),
        "board_index": _board(spec.get("board_index")),
        "measured": bool(spec.get("measured", True)),
        "children": normalized_children,
    }


def _receipt_id(identity: dict[str, Any]) -> str:
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return "compound_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _face_scores(formula: str, reference: str) -> dict[str, Any]:
    science = score_formulas(formula, reference)
    candidate = science["candidate"]
    matched = bool(science["venn"]["reference_match"])
    return {
        "match_score": 1.0 if matched else 0.0,
        "math_score": 1.0 if candidate.get("exists") else 0.0,
        "science_score": int(science["science_score"]),
        "science_threshold": int(science["threshold"]),
        "science_admitted": bool(science["admitted"]),
        "science_failed": list(science["failed"]),
        "venn": science["venn"]["region"],
        "composition": candidate.get("composition") or {},
        "charge": candidate.get("charge"),
        "exists": bool(candidate.get("exists")),
    }


def _score_row(formula: str, reference: str, word: str, code: str, board_index: int) -> dict[str, Any]:
    scores = _face_scores(formula, reference)
    return {
        "faces": {
            "math": {
                "formula": formula,
                "reference": reference,
                "composition": scores["composition"],
                "charge": scores["charge"],
                "exists": scores["exists"],
            },
            "word": word,
            "code": {"token": code, "board_index": board_index},
        },
        "match_score": scores["match_score"],
        "math_score": scores["math_score"],
        "science_score": scores["science_score"],
        "science_threshold": scores["science_threshold"],
        "science_admitted": scores["science_admitted"],
        "science_failed": scores["science_failed"],
        "venn": scores["venn"],
    }


def _min_score(parts: list[dict[str, Any]], key: str) -> float | int | None:
    values = [part[key] for part in parts]
    if any(value is None for value in values):
        return None
    return min(values)


def _trit_from(parts: list[dict[str, Any]]) -> int:
    trits = [int(part["trit"]) for part in parts]
    if any(trit == TRIT_OPEN for trit in trits):
        return TRIT_OPEN
    if any(trit == TRIT_REFUSED for trit in trits):
        return TRIT_REFUSED
    return TRIT_ADMITTED


def _joint(parts: list[dict[str, Any]]) -> dict[str, Any]:
    trit = _trit_from(parts)
    return {
        "match_score": _min_score(parts, "match_score"),
        "math_score": _min_score(parts, "math_score"),
        "science_score": _min_score(parts, "science_score"),
        "science_threshold": THRESHOLD,
        "trit": trit,
        "admitted": trit == TRIT_ADMITTED,
    }


def _cell_trit(scores: dict[str, Any], measured: bool) -> int:
    if not measured:
        return TRIT_OPEN
    if scores["science_admitted"]:
        return TRIT_ADMITTED
    return TRIT_REFUSED


def _same_ledger(rows: list[dict[str, Any]]) -> bool:
    compositions = [json.dumps(row["faces"]["math"]["composition"], sort_keys=True) for row in rows]
    charges = [row["faces"]["math"]["charge"] for row in rows]
    return len(set(compositions)) == 1 and len(set(charges)) == 1


def _build_cell(spec: dict[str, Any]) -> dict[str, Any]:
    scores = _score_row(
        spec["formula"],
        spec["reference"],
        spec["word"],
        spec["code"],
        spec["board_index"],
    )
    trit = _cell_trit(scores, spec["measured"])
    decided = spec["measured"]
    return {
        "kind": "cell",
        "board_index": spec["board_index"],
        "measured": spec["measured"],
        "faces": scores["faces"],
        "match_score": scores["match_score"] if decided else None,
        "math_score": scores["math_score"] if decided else None,
        "science_score": scores["science_score"] if decided else None,
        "science_threshold": THRESHOLD,
        "science_admitted": scores["science_admitted"] if decided else False,
        "science_failed": scores["science_failed"],
        "venn": scores["venn"],
        "trit": trit,
        "admitted": trit == TRIT_ADMITTED,
        "preview": {
            "match_score": scores["match_score"],
            "math_score": scores["math_score"],
            "science_score": scores["science_score"],
        },
    }


def _build_overlap(spec: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        _score_row(row["formula"], spec["reference"], row["word"], row["code"], spec["board_index"])
        for row in spec["overlap"]
    ]
    measured = spec["measured"]
    admitted_rows = [row for row in candidates if row["science_admitted"]]
    if not measured:
        joint = {
            "selected": [],
            "match_score": None,
            "math_score": None,
            "science_score": None,
            "trit": TRIT_OPEN,
            "admitted": False,
            "ledger_conflict": False,
        }
    elif admitted_rows and not _same_ledger(admitted_rows):
        joint = {
            "selected": [],
            "match_score": None,
            "math_score": None,
            "science_score": None,
            "trit": TRIT_OPEN,
            "admitted": False,
            "ledger_conflict": True,
        }
    else:
        pool = admitted_rows or candidates
        joint = {
            "selected": [
                {
                    "formula": row["faces"]["math"]["formula"],
                    "word": row["faces"]["word"],
                    "code": row["faces"]["code"]["token"],
                }
                for row in admitted_rows
            ],
            "match_score": min(row["match_score"] for row in pool),
            "math_score": min(row["math_score"] for row in pool),
            "science_score": min(row["science_score"] for row in pool),
            "trit": TRIT_ADMITTED if admitted_rows else TRIT_REFUSED,
            "admitted": bool(admitted_rows),
            "ledger_conflict": False,
        }
    return {
        "kind": "overlap",
        "board_index": spec["board_index"],
        "reference": spec["reference"],
        "measured": measured,
        "candidates": candidates,
        "selected": joint["selected"],
        "ledger_conflict": joint["ledger_conflict"],
        "match_score": joint["match_score"],
        "math_score": joint["math_score"],
        "science_score": joint["science_score"],
        "science_threshold": THRESHOLD,
        "trit": joint["trit"],
        "admitted": joint["admitted"],
    }


def _build_node(spec: dict[str, Any]) -> dict[str, Any]:
    root = _build_overlap(spec) if "overlap" in spec else _build_cell(spec)
    children = [_build_node(child) for child in spec["children"]]
    parts = [root, *children]
    joint = _joint(parts)
    return {
        "kind": "hyperatom",
        "node": root,
        "children": children,
        "match_score": joint["match_score"],
        "math_score": joint["math_score"],
        "science_score": joint["science_score"],
        "science_threshold": THRESHOLD,
        "trit": joint["trit"],
        "admitted": joint["admitted"],
    }


def _fmt_score(value: float | int | None) -> str:
    if value is None:
        return "open"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _fmt_trit(trit: int) -> str:
    if trit > 0:
        return "+1"
    return str(trit)


def _draw_faces(node: dict[str, Any], depth: int) -> list[str]:
    pad = "  " * depth
    if node["kind"] == "overlap":
        lines = [
            f"{pad}overlap board={node['board_index']} trit={_fmt_trit(node['trit'])} "
            f"measured={str(node['measured']).lower()}"
        ]
        for candidate in node["candidates"]:
            faces = candidate["faces"]
            lines.append(
                f"{pad}  {faces['word']} formula={faces['math']['formula']} "
                f"code={faces['code']['token']} "
                f"science={candidate['science_score']}/{candidate['science_threshold']}"
            )
        if node["selected"]:
            chosen = ", ".join(row["word"] for row in node["selected"])
            lines.append(f"{pad}  selected={chosen}")
        return lines
    faces = node["faces"]
    return [
        f"{pad}{faces['word']} board={node['board_index']} trit={_fmt_trit(node['trit'])} "
        f"match={_fmt_score(node['match_score'])} math={_fmt_score(node['math_score'])} "
        f"science={_fmt_score(node['science_score'])}/{node['science_threshold']}",
        f"{pad}  formula={faces['math']['formula']} code={faces['code']['token']}",
    ]


def _draw_hyperatom(node: dict[str, Any], depth: int) -> list[str]:
    pad = "  " * depth
    lines = [
        f"{pad}hyperatom trit={_fmt_trit(node['trit'])} "
        f"match={_fmt_score(node['match_score'])} math={_fmt_score(node['math_score'])} "
        f"science={_fmt_score(node['science_score'])}/{node['science_threshold']}"
    ]
    lines.extend(_draw_faces(node["node"], depth + 1))
    for child in node["children"]:
        lines.extend(_draw_hyperatom(child, depth + 1))
    return lines


def drawing(receipt: dict[str, Any]) -> str:
    """Text tree of the compound. The three scores stay on their own columns."""
    science = _fmt_score(receipt["science_score"])
    header = (
        f"{receipt['name']} trit={_fmt_trit(receipt['trit'])} "
        f"match={_fmt_score(receipt['match_score'])} math={_fmt_score(receipt['math_score'])} "
        f"science={science}/{receipt['science_threshold']}"
    )
    lines = [header]
    for node in receipt["hyperatoms"]:
        lines.extend(_draw_hyperatom(node, 1))
    return "\n".join(lines)


def compound(name: str, nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one compound receipt. Node order is the chain order."""
    label = _text(name, "name")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("a compound needs at least one hyperatom")
    identity_nodes = [normalize_spec(node) for node in nodes]
    built = [_build_node(node) for node in identity_nodes]
    joint = _joint(built)
    identity = {"name": label, "nodes": identity_nodes}
    receipt = {
        "schema_version": SCHEMA,
        "receipt_id": _receipt_id(identity),
        "kind": "compound",
        "name": label,
        "identity": identity,
        "hyperatoms": built,
        "match_score": joint["match_score"],
        "math_score": joint["math_score"],
        "science_score": joint["science_score"],
        "science_threshold": THRESHOLD,
        "trit": joint["trit"],
        "admitted": joint["admitted"],
        "boundary": BOUNDARY,
    }
    receipt["drawing"] = drawing(receipt)
    return receipt


def cell(
    *,
    formula: str,
    reference: str,
    word: str,
    code: str,
    board_index: int,
    measured: bool = True,
) -> dict[str, Any]:
    """Receipt for one measured cell, wrapped as a one-link compound."""
    return compound(
        word,
        [
            {
                "formula": formula,
                "reference": reference,
                "word": word,
                "code": code,
                "board_index": board_index,
                "measured": measured,
            }
        ],
    )


def measure(receipt: dict[str, Any]) -> dict[str, Any]:
    """Close every open cell and overlap. Scores are recomputed from the same faces."""
    identity = receipt.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("receipt has no identity to measure")

    def _close(spec: dict[str, Any]) -> dict[str, Any]:
        closed = dict(spec)
        closed["measured"] = True
        closed["children"] = [_close(child) for child in spec.get("children", [])]
        return closed

    return compound(identity["name"], [_close(node) for node in identity["nodes"]])
