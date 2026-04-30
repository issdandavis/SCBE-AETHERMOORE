#!/usr/bin/env python3
"""Parse Aether++ English-like statements into a typed AST."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR"}


@dataclass(frozen=True)
class Node:
    kind: str
    data: dict[str, Any]
    text: str


def split_statements(program: str) -> list[str]:
    # Statement terminator is ".", but keep decimal literals like 0.5 intact.
    chunks: list[str] = []
    buf: list[str] = []
    text = program.strip()
    for i, ch in enumerate(text):
        if ch == ".":
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if prev.isdigit() and nxt.isdigit():
                buf.append(ch)
                continue
            current = "".join(buf).strip()
            if current:
                chunks.append(current)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        chunks.append(tail)
    return chunks


def _m(pat: str, text: str) -> re.Match[str] | None:
    return re.fullmatch(pat, text, flags=re.IGNORECASE)


def parse_statement(text: str) -> Node:
    line = text.strip()

    m = _m(r"create\s+spacaita\s+system\s+with\s+(\d+)\s+manifolds?", line)
    if m:
        return Node("create_system", {"manifolds": int(m.group(1))}, line)

    m = _m(r"set\s+goal\s+to\s+(.+)", line)
    if m:
        goal = m.group(1).strip().strip("\"'")
        return Node("set_goal", {"goal": goal}, line)

    m = _m(
        r"apply\s+discrete\s+fold\s+(-?\d+(?:\.\d+)?)\s+to\s+manifold\s+(\d+)"
        r"(?:\s+with\s+goal\s+signal\s+(-?\d+(?:\.\d+)?))?"
        r"(?:\s+in\s+tongue\s+([A-Za-z]{2}))?",
        line,
    )
    if m:
        tongue = (m.group(4) or "KO").upper()
        if tongue not in TONGUES:
            raise ValueError(f"Unknown tongue in fold statement: {tongue}")
        return Node(
            "apply_fold",
            {
                "discrete_op": float(m.group(1)),
                "manifold": int(m.group(2)),
                "goal_signal": float(m.group(3)) if m.group(3) else 1.0,
                "tongue": tongue,
            },
            line,
        )

    m = _m(
        r"cross\s+propagate\s+from\s+manifold\s+(\d+)\s+to\s+manifold\s+(\d+)"
        r"(?:\s+with\s+ratio\s+(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?))?",
        line,
    )
    if m:
        ratio = [0.45, 0.30, 0.25]
        if m.group(3):
            ratio = [float(m.group(3)), float(m.group(4)), float(m.group(5))]
        return Node(
            "cross_propagate",
            {"src": int(m.group(1)), "dst": int(m.group(2)), "ratio": ratio},
            line,
        )

    m = _m(r"encode\s+\"([^\"]+)\"(?:\s+in\s+tongue\s+([A-Za-z]{2}))?", line)
    if m:
        tongue = (m.group(2) or "KO").upper()
        if tongue not in TONGUES:
            raise ValueError(f"Unknown tongue in encode statement: {tongue}")
        return Node("encode", {"content": m.group(1), "tongue": tongue}, line)

    if _m(r"(show|get)\s+status", line):
        return Node("show_status", {}, line)

    if _m(r"run\s+route", line):
        return Node("run_route", {}, line)

    raise ValueError(f"Unrecognized Aether++ statement: {line}")


def parse_program(program: str) -> list[Node]:
    statements = split_statements(program)
    if not statements:
        raise ValueError("Aether++ program is empty")
    return [parse_statement(line) for line in statements]


def ast_to_dict(nodes: list[Node]) -> list[dict[str, Any]]:
    return [asdict(node) for node in nodes]
