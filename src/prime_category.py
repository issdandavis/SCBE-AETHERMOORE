"""Prime-coded categories — sort/decode items by an assigned "prime target category".

Each category is assigned a distinct prime. An item's set of categories is encoded
as the *product* of those primes (a squarefree Gödel-style code). Then:

- an item **belongs to** a category  iff  its code is divisible by that category's
  prime — so filtering a fleet by a target category is a single modulo test (the
  sieve), and
- an item's full category set is **recovered** by factoring its code.

This is built directly on ``src.numtheory`` (``nth_prime`` for stable assignment,
``prime_factors`` to decode) — the prime sieve as the bedrock for categorization.

Assignment is deterministic: the i-th distinct category (in the order given) gets
the i-th prime, so the same category universe always yields the same codes.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from src import numtheory as nt


class PrimeCategories:
    """A fixed category universe with a stable category <-> prime assignment."""

    def __init__(self, categories: Iterable[str]) -> None:
        cats = list(dict.fromkeys(c.strip() for c in categories if c.strip()))  # dedupe, keep order
        if not cats:
            raise ValueError("need at least one category")
        self._cat_to_prime: Dict[str, int] = {c: nt.nth_prime(i + 1) for i, c in enumerate(cats)}
        self._prime_to_cat: Dict[int, str] = {p: c for c, p in self._cat_to_prime.items()}

    @property
    def mapping(self) -> Dict[str, int]:
        """The category -> prime assignment."""
        return dict(self._cat_to_prime)

    def prime_of(self, category: str) -> int:
        category = category.strip()
        if category not in self._cat_to_prime:
            raise KeyError(f"unknown category: {category!r}")
        return self._cat_to_prime[category]

    def code(self, categories: Iterable[str]) -> int:
        """Encode an item's category set as the product of the categories' primes."""
        code = 1
        for c in dict.fromkeys(c.strip() for c in categories if c.strip()):
            code *= self.prime_of(c)
        return code

    def decode(self, code: int) -> List[str]:
        """Recover the category set from a code by factoring it (sieve in reverse)."""
        if code < 1:
            raise ValueError("code must be >= 1")
        cats: List[str] = []
        for p in sorted(set(nt.prime_factors(code))):
            if p not in self._prime_to_cat:
                raise ValueError(f"code carries prime {p} with no assigned category")
            cats.append(self._prime_to_cat[p])
        return cats

    def in_category(self, code: int, target: str) -> bool:
        """True iff an item's code belongs to the target category (divisibility sieve)."""
        return code % self.prime_of(target) == 0

    def sort_by_category(self, items: Dict[str, Iterable[str]], target: str) -> List[str]:
        """Names of items tagged with ``target``, found by the divisibility sieve."""
        tp = self.prime_of(target)
        return [name for name, cats in items.items() if self.code(cats) % tp == 0]
