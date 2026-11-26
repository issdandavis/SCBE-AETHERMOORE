"""Tokens as numbers — bijective numeration over any ordered token set.

Set a series of tokens as your "number set" and it *is* a positional number system:
with k symbols, **bijective base-k** gives every non-negative integer exactly one
finite token sequence and back — no leading-symbol ambiguity (the flaw that makes
ordinary base-k non-bijective). So you decode -> operate -> encode, and the tokens
carry the arithmetic.

Any ordered, unique alphabet works — including a Sacred Tongues token grid (its 256
tokens become a bijective base-256 number system); this module stays standalone and
takes the alphabet as data.
"""

from __future__ import annotations

from typing import List, Sequence


def bijective_encode(n: int, alphabet: Sequence[str]) -> List[str]:
    """Encode a non-negative integer as a token sequence in bijective base-len(alphabet)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    k = len(alphabet)
    if k < 1:
        raise ValueError("alphabet must be non-empty")
    if k == 1:
        return [alphabet[0]] * n  # unary
    out: List[str] = []
    while n > 0:
        n, r = divmod(n, k)
        if r == 0:
            r = k
            n -= 1
        out.append(alphabet[r - 1])  # bijective digits are 1..k
    return list(reversed(out))


def bijective_decode(tokens: Sequence[str], alphabet: Sequence[str]) -> int:
    """Decode a token sequence in bijective base-len(alphabet) back to an integer."""
    k = len(alphabet)
    index = {t: i for i, t in enumerate(alphabet)}
    n = 0
    for t in tokens:
        if t not in index:
            raise ValueError(f"token {t!r} is not in the alphabet")
        n = n * k + (index[t] + 1)
    return n


class TokenNumbers:
    """Treat an ordered token alphabet as a number system; operate directly on token series."""

    def __init__(self, alphabet: Sequence[str]) -> None:
        if len(set(alphabet)) != len(alphabet):
            raise ValueError("alphabet symbols must be unique")
        if not alphabet:
            raise ValueError("alphabet must be non-empty")
        self.alphabet = list(alphabet)

    @property
    def base(self) -> int:
        return len(self.alphabet)

    def encode(self, n: int) -> List[str]:
        return bijective_encode(n, self.alphabet)

    def decode(self, tokens: Sequence[str]) -> int:
        return bijective_decode(tokens, self.alphabet)

    def add(self, a: Sequence[str], b: Sequence[str]) -> List[str]:
        return self.encode(self.decode(a) + self.decode(b))

    def mul(self, a: Sequence[str], b: Sequence[str]) -> List[str]:
        return self.encode(self.decode(a) * self.decode(b))
