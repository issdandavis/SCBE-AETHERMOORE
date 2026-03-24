#!/usr/bin/env python3
"""Qualitative Sacred Egg benchmark against adjacent security patterns.

This is an engineering comparison tool, not a mathematical proof engine.
It makes the Sacred Egg concept explicit enough to reason about by scoring
systems across the capabilities the Notion docs emphasize.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

AXES: Tuple[Tuple[str, str], ...] = (
    ("genesis", "control creation/spawn authority"),
    ("pre_crypto", "gate before meaningful cryptographic reveal"),
    ("geometry", "bind to geometry or region"),
    ("path", "bind to path / ring descent / trajectory"),
    ("quorum", "require multi-party or threshold agreement"),
    ("noise", "fail-to-noise or oracle-resistant deny"),
    ("policy_release", "bind release to policy at decrypt/use time"),
    ("habitat", "constrain runtime habitat / execution area"),
    ("transit", "carry governance constraints during transmission"),
    ("semantic", "preserve semantic traceability / role tags"),
)

TOKENIZER_ROLES: Dict[str, str] = {
    "KO": "intent / nonce",
    "AV": "metadata / AAD",
    "RU": "binding / salt",
    "CA": "compute / ciphertext",
    "UM": "security / redaction",
    "DR": "structure / tag",
}


@dataclass(frozen=True)
class Profile:
    name: str
    family: str
    scores: Dict[str, int]
    note: str

    def total(self) -> int:
        return sum(self.scores[axis] for axis, _ in AXES)

    def weighted(self, weights: Dict[str, int]) -> int:
        return sum(self.scores[axis] * weights.get(axis, 0) for axis, _ in AXES)


def profiles() -> List[Profile]:
    return [
        Profile(
            name="Sacred Egg",
            family="composed governance object",
            scores={
                "genesis": 5,
                "pre_crypto": 5,
                "geometry": 5,
                "path": 5,
                "quorum": 5,
                "noise": 5,
                "policy_release": 4,
                "habitat": 2,
                "transit": 5,
                "semantic": 5,
            },
            note="Best fit for governed genesis, multi-condition hatch, and packet-level release.",
        ),
        Profile(
            name="gVisor sandbox",
            family="runtime isolation",
            scores={
                "genesis": 0,
                "pre_crypto": 1,
                "geometry": 0,
                "path": 0,
                "quorum": 0,
                "noise": 0,
                "policy_release": 0,
                "habitat": 5,
                "transit": 1,
                "semantic": 1,
            },
            note="Best fit for workload containment, not governed spawning or semantic release.",
        ),
        Profile(
            name="Biscuit",
            family="authorization token",
            scores={
                "genesis": 1,
                "pre_crypto": 2,
                "geometry": 0,
                "path": 0,
                "quorum": 1,
                "noise": 0,
                "policy_release": 3,
                "habitat": 0,
                "transit": 2,
                "semantic": 4,
            },
            note="Strong for decentralized authorization and attenuation, weak on habitat and fail-to-noise.",
        ),
        Profile(
            name="Macaroons",
            family="attenuated bearer credential",
            scores={
                "genesis": 1,
                "pre_crypto": 1,
                "geometry": 0,
                "path": 0,
                "quorum": 1,
                "noise": 0,
                "policy_release": 2,
                "habitat": 0,
                "transit": 2,
                "semantic": 3,
            },
            note="Good for caveat-based delegation, not for multi-axis hatch protocols.",
        ),
        Profile(
            name="CP-ABE",
            family="policy-bound decryption",
            scores={
                "genesis": 1,
                "pre_crypto": 3,
                "geometry": 0,
                "path": 0,
                "quorum": 0,
                "noise": 0,
                "policy_release": 5,
                "habitat": 0,
                "transit": 2,
                "semantic": 2,
            },
            note="Excellent when the main problem is policy-bound decrypt, not runtime flow governance.",
        ),
        Profile(
            name="Threshold cryptography",
            family="split authority",
            scores={
                "genesis": 2,
                "pre_crypto": 1,
                "geometry": 0,
                "path": 0,
                "quorum": 5,
                "noise": 0,
                "policy_release": 1,
                "habitat": 0,
                "transit": 2,
                "semantic": 1,
            },
            note="Excellent at split trust and quorum, weak on semantic and geometric binding.",
        ),
        Profile(
            name="Intel SGX",
            family="trusted execution environment",
            scores={
                "genesis": 0,
                "pre_crypto": 2,
                "geometry": 0,
                "path": 0,
                "quorum": 0,
                "noise": 0,
                "policy_release": 1,
                "habitat": 4,
                "transit": 1,
                "semantic": 1,
            },
            note="Strong for protecting secrets in use, not for multi-condition packet hatching.",
        ),
    ]


GOALS: Dict[str, Dict[str, int]] = {
    "spawn_governance": {
        "genesis": 3,
        "pre_crypto": 2,
        "geometry": 2,
        "path": 2,
        "quorum": 2,
        "noise": 1,
    },
    "payload_release": {
        "pre_crypto": 2,
        "policy_release": 3,
        "noise": 2,
        "transit": 2,
        "geometry": 1,
        "semantic": 1,
    },
    "runtime_isolation": {
        "habitat": 4,
        "pre_crypto": 1,
        "transit": 1,
    },
    "delegated_authorization": {
        "policy_release": 2,
        "semantic": 2,
        "transit": 1,
        "quorum": 1,
        "genesis": 1,
    },
}


def markdown_table(rows: Iterable[Iterable[str]]) -> str:
    row_list = [list(row) for row in rows]
    header = "| " + " | ".join(row_list[0]) + " |"
    divider = "| " + " | ".join(["---"] * len(row_list[0])) + " |"
    body = ["| " + " | ".join(row) + " |" for row in row_list[1:]]
    return "\n".join([header, divider, *body])


def benchmark_table(items: List[Profile]) -> str:
    headers = ["System", *[label for _, label in AXES], "total"]
    rows = [headers]
    for profile in items:
        rows.append(
            [
                profile.name,
                *[str(profile.scores[axis]) for axis, _ in AXES],
                str(profile.total()),
            ]
        )
    return markdown_table(rows)


def goal_rankings(items: List[Profile]) -> str:
    lines: List[str] = []
    for goal, weights in GOALS.items():
        ranked = sorted(items, key=lambda item: item.weighted(weights), reverse=True)
        top = ranked[:3]
        lines.append(f"## Goal: {goal.replace('_', ' ')}")
        for index, item in enumerate(top, start=1):
            lines.append(f"{index}. {item.name} — {item.weighted(weights)}")
        lines.append("")
    return "\n".join(lines).strip()


def tokenizer_section() -> str:
    rows = [["Tokenizer", "Role"]]
    for key, value in TOKENIZER_ROLES.items():
        rows.append([key, value])
    return markdown_table(rows)


def report() -> str:
    items = profiles()
    sections = [
        "# Sacred Egg Benchmark",
        "",
        "This is a qualitative engineering benchmark, not a performance test or proof.",
        "",
        "## Tokenizer roles",
        tokenizer_section(),
        "",
        "## Capability matrix",
        benchmark_table(items),
        "",
        "## Goal rankings",
        goal_rankings(items),
        "",
        "## Notes",
        "- Sacred Egg currently benchmarks as a composed governance object.",
        "- gVisor is still the clearest runtime isolation baseline.",
        "- Biscuit and Macaroons remain the cleaner delegation baselines.",
        "- CP-ABE remains the cleaner policy-bound decryption baseline.",
        "- Threshold cryptography remains the cleaner quorum baseline.",
        "- Intel SGX remains the clearer secret-in-use baseline.",
        "",
        "## Practical interpretation",
        "If the SCBE idea is real, it is not replacing one of these systems. It is trying to compose several of their strengths into one hatch object.",
    ]
    return "\n".join(sections)


if __name__ == "__main__":
    print(report())
