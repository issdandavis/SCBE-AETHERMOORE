"""Sequence-aware overlay graph builders for memory and retrieval.

These helpers turn token streams into lightweight graph signatures instead of
collapsing everything into a single vector too early. Each overlay is a
typed multigraph represented as node/edge counters so it remains both
human-readable and cheap to compare at runtime.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Sequence

from python.scbe.atomic_tokenization import (
    AtomicTokenState,
    TONGUES,
    map_token_to_atomic_state,
)
from python.scbe.tongue_code_lanes import CODE_LANE_REGISTRY, KNOWN_CODE_LANES


INTENTION_CLASS_MAP: Dict[str, str] = {
    "INERT_WITNESS": "observe",
    "ENTITY": "identify",
    "ACTION": "act",
    "NEGATION": "constrain",
    "MODIFIER": "refine",
    "RELATION": "connect",
    "TEMPORAL": "sequence",
}

INTENTION_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "observe": ("find", "inspect", "read", "recall", "see", "show", "where", "which", "what"),
    "act": ("add", "apply", "build", "create", "execute", "make", "push", "run", "write"),
    "govern": ("audit", "govern", "policy", "prove", "risk", "safe", "trust", "verify"),
    "connect": ("between", "bridge", "connect", "cross", "link", "map", "relay", "with"),
    "sequence": ("after", "before", "history", "later", "reduce", "resume", "state", "then"),
    "transform": ("decode", "encode", "fuse", "project", "rerank", "tokenize", "translate"),
}

POLICY_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "allow": ("allow", "permit", "pass"),
    "deny": ("block", "deny", "forbid", "hold", "prevent", "reject"),
    "require": ("enforce", "must", "require", "should"),
    "verify": ("attest", "prove", "validate", "verify"),
    "trust": ("authority", "confidence", "integrity", "trust"),
    "risk": ("danger", "hazard", "review", "risk", "warn"),
    "scope": ("boundary", "context", "scope", "zone"),
}

CODE_ALIASES: Dict[str, str] = {
    "asm": "assembly",
    "c": "c",
    "forth": "forth",
    "javascript": "typescript",
    "js": "typescript",
    "lisp": "lisp",
    "make": "make",
    "py": "python",
    "python": "python",
    "rust": "rust",
    "sql": "sql",
    "ts": "typescript",
    "typescript": "typescript",
}

REVERSE_CODE_MAP: Dict[str, str] = {}
for profile in CODE_LANE_REGISTRY.values():
    for tongue, lane in profile.items():
        REVERSE_CODE_MAP.setdefault(lane, tongue)


@dataclass(frozen=True, slots=True)
class OverlayGraph:
    intention_nodes: Dict[str, int]
    intention_edges: Dict[str, int]
    policy_nodes: Dict[str, int]
    policy_edges: Dict[str, int]
    code_tongue_nodes: Dict[str, int]
    code_tongue_edges: Dict[str, int]


def _tokenize(text: str) -> List[str]:
    token = []
    tokens: List[str] = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            token.append(ch.lower())
            continue
        if token:
            tokens.append("".join(token))
            token.clear()
    if token:
        tokens.append("".join(token))
    return tokens


def _edge_counter(sequence: Sequence[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for left, right in zip(sequence, sequence[1:]):
        counter[f"{left}->{right}"] += 1
    return counter


def _keyword_match(token: str, mapping: Dict[str, tuple[str, ...]]) -> str | None:
    for label, keywords in mapping.items():
        if token in keywords:
            return label
    return None


def _primary_intention(token: str, state: AtomicTokenState) -> str:
    keyword_label = _keyword_match(token, INTENTION_KEYWORDS)
    if keyword_label:
        return keyword_label
    return INTENTION_CLASS_MAP[state.semantic_class]


def _policy_labels(token: str, state: AtomicTokenState) -> List[str]:
    labels: List[str] = []
    keyword_label = _keyword_match(token, POLICY_KEYWORDS)
    if keyword_label:
        labels.append(keyword_label)

    if state.semantic_class == "NEGATION" and "deny" not in labels:
        labels.append("deny")
    if state.semantic_class in {"RELATION", "TEMPORAL"} and "scope" not in labels:
        labels.append("scope")
    if state.semantic_class == "ACTION" and token in {"prove", "validate", "verify"} and "verify" not in labels:
        labels.append("verify")
    return labels


def _active_tongue_counts(states: Sequence[AtomicTokenState]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for state in states:
        for tongue, value in state.tau.as_dict().items():
            if value == 1:
                counts[tongue] += 1
    return counts


def _identity_edges(node_counts: Counter[str]) -> Counter[str]:
    edges: Counter[str] = Counter()
    for node, count in node_counts.items():
        edges[f"{node}->{node}"] += count
    return edges


def build_overlay_graph(
    text: str,
    *,
    language: str | None = None,
    context_class: str | None = "memory",
) -> OverlayGraph:
    tokens = _tokenize(text)
    states = [
        map_token_to_atomic_state(token, language=language, context_class=context_class)
        for token in tokens
    ]

    intention_sequence = [_primary_intention(token, state) for token, state in zip(tokens, states)]
    intention_nodes = Counter(intention_sequence)
    intention_edges = _identity_edges(intention_nodes)
    intention_edges.update(_edge_counter(intention_sequence))

    policy_sequence: List[str] = []
    for token, state in zip(tokens, states):
        policy_sequence.extend(_policy_labels(token, state))
    policy_nodes = Counter(policy_sequence)
    policy_edges = _identity_edges(policy_nodes)
    policy_edges.update(_edge_counter(policy_sequence))

    code_tongue_nodes: Counter[str] = Counter()
    code_tongue_edges: Counter[str] = Counter()

    active_tongues = _active_tongue_counts(states)
    for tongue, count in active_tongues.items():
        node = f"tongue:{tongue}"
        code_tongue_nodes[node] += count

    explicit_lanes: Counter[str] = Counter()
    explicit_tongues: Counter[str] = Counter()
    for token in tokens:
        lane = CODE_ALIASES.get(token)
        if lane and lane in KNOWN_CODE_LANES:
            explicit_lanes[lane] += 1
        upper = token.upper()
        if upper in TONGUES:
            explicit_tongues[upper] += 1

    for lane, count in explicit_lanes.items():
        code_tongue_nodes[f"lane:{lane}"] += count
    for tongue, count in explicit_tongues.items():
        code_tongue_nodes[f"tongue:{tongue}"] += count

    for tongue, count in active_tongues.items():
        for profile_name, profile in CODE_LANE_REGISTRY.items():
            lane = profile.get(tongue)
            if not lane:
                continue
            profile_node = f"profile:{profile_name}"
            tongue_node = f"tongue:{tongue}"
            lane_node = f"lane:{lane}"
            code_tongue_nodes[profile_node] += 1
            code_tongue_nodes[lane_node] += 1
            code_tongue_edges[f"{profile_node}->{tongue_node}"] += count
            code_tongue_edges[f"{tongue_node}->{lane_node}"] += count
            code_tongue_edges[f"{lane_node}->{tongue_node}"] += count

    for lane, count in explicit_lanes.items():
        lane_node = f"lane:{lane}"
        mapped_tongue = REVERSE_CODE_MAP.get(lane)
        if mapped_tongue:
            tongue_node = f"tongue:{mapped_tongue}"
            code_tongue_edges[f"{lane_node}->{tongue_node}"] += count
            code_tongue_edges[f"{tongue_node}->{lane_node}"] += count

    code_tongue_edges.update(_identity_edges(code_tongue_nodes))

    return OverlayGraph(
        intention_nodes=dict(intention_nodes),
        intention_edges=dict(intention_edges),
        policy_nodes=dict(policy_nodes),
        policy_edges=dict(policy_edges),
        code_tongue_nodes=dict(code_tongue_nodes),
        code_tongue_edges=dict(code_tongue_edges),
    )


__all__ = ["OverlayGraph", "build_overlay_graph"]
