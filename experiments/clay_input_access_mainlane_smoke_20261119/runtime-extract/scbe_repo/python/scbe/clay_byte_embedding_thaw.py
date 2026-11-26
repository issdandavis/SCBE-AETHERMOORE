"""Action-gated partial thaw for Clay's canonical 256 byte-token rows.

The counting parent remains byte-for-byte immutable.  Action inference reads a
trainable shadow copy of only the 256 private-use byte embedding rows before
the frozen GRU.  Counting inference always reads the original embedding table.
This gives the new skill input access without letting action training overwrite
the retained counting path.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import random
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from python.scbe.clay_frozen_multiview_adapter import FrozenActionModel
from python.scbe.clay_frozen_multiview_data import (
    ActionTextRow,
    BYTE_TOKEN_BASE,
)

SCHEMA = "clay.action-gated-byte-embedding-thaw.v1"
BYTE_COUNT = 256
THAW_ARMS = (
    "byte_thaw_multiview",
    "byte_thaw_static",
    "byte_thaw_sample_shuffled",
)


class ActionGatedByteEmbeddingThaw(FrozenActionModel):
    """Frozen counting model with action-only trainable byte embedding rows."""

    def __init__(self, vocab: Sequence[str]) -> None:
        super().__init__(len(vocab))
        stoi = {token: index for index, token in enumerate(vocab)}
        byte_token_ids = []
        for value in range(BYTE_COUNT):
            token = chr(BYTE_TOKEN_BASE + value)
            if token not in stoi:
                raise ValueError(f"vocabulary is missing byte token {value}")
            byte_token_ids.append(stoi[token])
        ids = torch.tensor(byte_token_ids, dtype=torch.long)
        lookup = torch.full((len(vocab),), -1, dtype=torch.long)
        lookup[ids] = torch.arange(BYTE_COUNT, dtype=torch.long)
        self.register_buffer("byte_token_ids", ids, persistent=False)
        self.register_buffer("byte_lookup", lookup, persistent=False)
        self.thawed_byte_rows = nn.Parameter(torch.empty(BYTE_COUNT, 64))
        self._parent_loaded = False

    def load_parent_state(self, state: Mapping[str, Tensor]) -> None:
        """Load a base parent and initialize the shadow rows exactly once."""

        result = self.load_state_dict(state, strict=False)
        if result.unexpected_keys or result.missing_keys != ["thawed_byte_rows"]:
            raise RuntimeError(
                "parent state does not match the byte-thaw architecture: "
                f"missing={result.missing_keys}, unexpected={result.unexpected_keys}"
            )
        with torch.no_grad():
            self.thawed_byte_rows.copy_(self.e.weight[self.byte_token_ids])
        self._parent_loaded = True

    def _embed(self, inputs: Tensor, head: str) -> Tensor:
        embedded = self.e(inputs)
        if head != "action":
            return embedded
        if not self._parent_loaded:
            raise RuntimeError("load_parent_state must run before action inference")
        byte_indices = self.byte_lookup[inputs]
        active = byte_indices >= 0
        replacement = self.thawed_byte_rows[byte_indices.clamp(min=0)]
        return torch.where(active.unsqueeze(-1), replacement, embedded)

    def forward(
        self, inputs: Tensor, head: str, state: Any = None
    ) -> tuple[Tensor, Any]:
        core_state = state[0] if isinstance(state, tuple) else state
        hidden, core_state = self.g(self._embed(inputs, head), core_state)
        if head == "count":
            return self.count_head(hidden), core_state
        carrier = (
            torch.ones_like(hidden) if self.active_path == "adapter_null" else hidden
        )
        return self.adapter_head(self.adapter(carrier)), (core_state, None)

    def parameters_for(self, stage: str) -> list[nn.Parameter]:
        if stage in THAW_ARMS:
            modules: tuple[nn.Module, ...] = (self.adapter, self.adapter_head)
            return [
                *(parameter for module in modules for parameter in module.parameters()),
                self.thawed_byte_rows,
            ]
        return super().parameters_for(stage)

    def thaw_receipt(self) -> dict[str, Any]:
        original = self.e.weight[self.byte_token_ids]
        changed = torch.ne(original, self.thawed_byte_rows).any(dim=1)
        return {
            "schema": SCHEMA,
            "action_gated": True,
            "byte_rows": BYTE_COUNT,
            "embedding_width": int(self.thawed_byte_rows.shape[1]),
            "trainable_byte_scalars": int(self.thawed_byte_rows.numel()),
            "changed_byte_rows": int(changed.sum().item()),
            "count_path_uses_parent_embedding": True,
        }


def sample_local_byte_shuffle(row: ActionTextRow, *, seed: int) -> ActionTextRow:
    """Destroy stable byte identity with a deterministic per-sample bijection."""

    digest = hashlib.sha256(f"{seed}:{row.sample.sample_id}".encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    permutation = list(range(BYTE_COUNT))
    rng.shuffle(permutation)
    body = row.prompt[3:-3]
    remapped = "".join(
        chr(BYTE_TOKEN_BASE + permutation[ord(token) - BYTE_TOKEN_BASE])
        for token in body
    )
    return replace(row, prompt=f"K :{remapped} =>")


def sample_local_byte_shuffle_rows(
    rows: Sequence[ActionTextRow], *, seed: int
) -> tuple[ActionTextRow, ...]:
    return tuple(sample_local_byte_shuffle(row, seed=seed) for row in rows)


__all__ = [
    "ActionGatedByteEmbeddingThaw",
    "BYTE_COUNT",
    "SCHEMA",
    "THAW_ARMS",
    "sample_local_byte_shuffle",
    "sample_local_byte_shuffle_rows",
]
