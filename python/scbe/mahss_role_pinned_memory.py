"""Role-pinned HRR memory for MAHSS Phase 1 (v8-pre).

This implements Option B from the MAHSS spec: roles are pre-assigned
deterministic random vectors keyed by semantic name (TONGUE, LANG, SLOT,
METRIC, KEYWORD, IDENT). A memory bundle stores ``Σᵢ (role_i ⊛ filler_i)``
and is queried by ``M ⊛† role`` to retrieve the bound filler.

The hypothesis this module tests: given correct role pinning at adequate
dim, HRR unbinding retrieves the right marker for each role with top-1
accuracy well above chance. If true, MAHSS-as-retrieval is a viable
substrate for the v6g raw-floor problem; if false, learned routing
(Option A) is the only path forward."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from python.scbe.mahss import (
    EPS,
    circular_convolution,
    circular_correlation,
    l2_normalize,
    role_vector,
)


@dataclass(frozen=True)
class RetrievalScore:
    role: str
    expected: str
    retrieved: str
    score: float
    margin: float
    ranks: tuple[tuple[str, float], ...]
    correct: bool


class RolePinnedMemory:
    """HRR memory with operator-pinned role and filler vectors.

    Each role and each filler gets a deterministic random vector built via
    SHA-256 namespacing (``role::TONGUE`` vs ``filler::TONGUE::umbroth``)
    so that two memories with the same vocabulary have identical bindings.

    Adding a filler registers it in the role's dictionary; binding a
    (role, filler) pair both registers AND adds it to the memory bundle.
    Distractors can be registered without being bound, so retrieval has
    to choose the bound one out of a realistic candidate set."""

    def __init__(self, dim: int = 4096) -> None:
        if dim < 16:
            raise ValueError(f"dim must be >= 16, got {dim}")
        self.dim = dim
        self.memory = np.zeros(dim, dtype=float)
        self._role_vecs: dict[str, np.ndarray] = {}
        self._filler_vecs: dict[str, dict[str, np.ndarray]] = {}
        self._bindings: list[tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Role / filler registration
    # ------------------------------------------------------------------

    def role_vector_for(self, role: str) -> np.ndarray:
        if role not in self._role_vecs:
            self._role_vecs[role] = role_vector(f"role::{role}", self.dim)
        return self._role_vecs[role]

    def register_filler(self, role: str, filler: str) -> np.ndarray:
        """Add a filler to the role's candidate dictionary without binding it."""

        bucket = self._filler_vecs.setdefault(role, {})
        if filler not in bucket:
            bucket[filler] = role_vector(f"filler::{role}::{filler}", self.dim)
        return bucket[filler]

    def register_distractors(self, role: str, distractors: Iterable[str]) -> None:
        for d in distractors:
            self.register_filler(role, d)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def bind(self, role: str, filler: str) -> None:
        """Add (role ⊛ filler) to the memory bundle."""

        role_vec = self.role_vector_for(role)
        filler_vec = self.register_filler(role, filler)
        self.memory = self.memory + circular_convolution(role_vec, filler_vec)
        self._bindings.append((role, filler))

    def bind_many(self, pairs: Iterable[tuple[str, str]]) -> None:
        for role, filler in pairs:
            self.bind(role, filler)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(self, role: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        """Unbind by role, rank against the role's filler dictionary.

        Returns up to ``top_k`` (filler, score) pairs sorted by descending
        cosine similarity. Score is the raw cosine, not a probability.
        Empty list if the role has no fillers registered."""

        if role not in self._filler_vecs or not self._filler_vecs[role]:
            return []
        role_vec = self.role_vector_for(role)
        unbound = circular_correlation(role_vec, self.memory)
        unbound_n = l2_normalize(unbound)
        scored: list[tuple[str, float]] = []
        for filler, vec in self._filler_vecs[role].items():
            scored.append((filler, float(np.dot(unbound_n, l2_normalize(vec)))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def score(self, role: str, expected: str, *, top_k: int = 5) -> RetrievalScore:
        """Retrieve and score a single (role, expected_filler) probe."""

        ranks = self.query(role, top_k=top_k)
        if not ranks:
            return RetrievalScore(
                role=role,
                expected=expected,
                retrieved="",
                score=0.0,
                margin=0.0,
                ranks=(),
                correct=False,
            )
        retrieved, score = ranks[0]
        runner_up = ranks[1][1] if len(ranks) > 1 else 0.0
        return RetrievalScore(
            role=role,
            expected=expected,
            retrieved=retrieved,
            score=score,
            margin=score - runner_up,
            ranks=tuple(ranks),
            correct=(retrieved == expected),
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def crosstalk_floor(self) -> float:
        """Expected per-binding crosstalk magnitude at current load.

        For random orthogonal-ish vectors with N bindings in dim d, off-target
        unbinding has expected magnitude ~ sqrt(N) / sqrt(d). Signal is ~1.
        So SNR ~ sqrt(d / N). At d=4096, N=10 → SNR ~ 20."""

        if not self._bindings:
            return 0.0
        return math.sqrt(len(self._bindings) / self.dim)

    @property
    def num_bindings(self) -> int:
        return len(self._bindings)

    @property
    def num_roles(self) -> int:
        return len(self._role_vecs)

    @property
    def num_fillers(self) -> int:
        return sum(len(b) for b in self._filler_vecs.values())

    def filler_dict_size(self, role: str) -> int:
        return len(self._filler_vecs.get(role, {}))


# ----------------------------------------------------------------------
# v6g failure corpus — derived from the 2026-05-07 gate report
# ----------------------------------------------------------------------

# Each entry: (prompt_id, [(role, expected_filler), ...])
# Roles parsed from the missing_required field of each raw-failing prompt.
V6G_RAW_FAILURE_CORPUS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "code_eval_count_vowels_translate",
        (("IDENT", "count_vowels"), ("TONGUE", "umbroth"), ("LANG", "haskell")),
    ),
    (
        "code_eval_zero_guard_safe_subtract",
        (("EXPR", "a - b"),),
    ),
    (
        "code_eval_clamp_value_rust",
        (("KEYWORD", "return"),),
    ),
    (
        "code_eval_avali_javascript_lens",
        (("LITERAL", "''"),),
    ),
    (
        "code_eval_identify_algorithm_haskell",
        (
            ("SLOT", "algorithm:"),
            ("TONGUE", "umbroth"),
            ("METRIC", "phi=6.85"),
            ("SLOT", "sig"),
            ("SLOT", "body"),
        ),
    ),
    (
        "code_eval_multi_lens_consistency",
        (
            ("TONGUE", "kor'aelin"),
            ("TONGUE", "avali"),
            ("TONGUE", "runethic"),
            ("IDENT", "def triple"),
            ("IDENT", "function triple"),
            ("EXPR", "* 3"),
        ),
    ),
    (
        "code_eval_approval_card_verdict",
        (("KEYWORD", "horizon"), ("TONGUE", "draumric"), ("TONGUE", "kor'aelin")),
    ),
    (
        "code_eval_geoseal_pair_route",
        (("TONGUE", "kor'aelin"), ("KEYWORD", "total")),
    ),
    (
        "code_eval_lane_boundary_no_chem",
        (("IDENT", "queue_drain_guard"), ("KEYWORD", "code identifier"), ("KEYWORD", "unit test")),
    ),
    (
        "code_eval_runethic_option_chain",
        (("LITERAL", "Some"), ("LITERAL", "None")),
    ),
)


# Distractor vocabularies per role — pulled from the broader v6g context.
# These are realistic alternatives the model could hallucinate. The retrieval
# task: pick the BOUND filler over the larger candidate set including these.
V6G_DISTRACTORS: dict[str, tuple[str, ...]] = {
    "TONGUE": ("kor'aelin", "avali", "runethic", "cassisivadan", "umbroth", "draumric"),
    "LANG": ("python", "haskell", "javascript", "rust", "mathematica", "markdown"),
    "SLOT": ("algorithm:", "sig", "body", "init", "loop_open", "loop_body", "ret", "slots:"),
    "METRIC": ("phi=1.00", "phi=1.62", "phi=2.62", "phi=4.24", "phi=6.85", "phi=11.09"),
    "KEYWORD": (
        "return", "horizon", "total", "code identifier", "unit test",
        "verdict", "evidence", "next", "tongue", "phi_weight",
    ),
    "IDENT": (
        "count_vowels", "queue_drain_guard", "def triple", "function triple",
        "fn triple", "running_average", "merge_counts", "inventory_unique",
        "safe_subtract", "clamp_value", "first_positive",
    ),
    "EXPR": ("a - b", "* 3", "+ 1", "- 1", "/ 2", "% 10", "** 2", "<< 1"),
    "LITERAL": ("''", "Some", "None", "True", "False", "0.0", "[]", "{}", "null"),
}


def build_per_prompt_memory(
    prompt_pairs: Iterable[tuple[str, str]],
    *,
    dim: int = 4096,
    distractors: dict[str, tuple[str, ...]] | None = None,
) -> RolePinnedMemory:
    """Build memory for a single prompt's required (role, filler) pairs.

    All distractors per role are registered (so retrieval picks from a
    realistic candidate set), but only the prompt's pairs are bound."""

    mem = RolePinnedMemory(dim=dim)
    if distractors:
        for role, options in distractors.items():
            mem.register_distractors(role, options)
    for role, filler in prompt_pairs:
        mem.bind(role, filler)
    return mem


__all__ = [
    "RetrievalScore",
    "RolePinnedMemory",
    "V6G_DISTRACTORS",
    "V6G_RAW_FAILURE_CORPUS",
    "build_per_prompt_memory",
]
