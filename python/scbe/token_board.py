"""token_board: a conlang token bound to a VERIFIED legal move -- the tokenizer as a measurable
control board, not an aesthetic layer.

Each token names one move on the board, and every move is a DETERMINISTIC predicate (numtheory), so a
pick is checkable instantly. The task is to classify n into {unit, prime, prime-power, composite} --
the same categories sieve_calc uses. We then measure a small model under escalating governance:

    raw          -- free-text label, no board (the floor)
    board        -- must pick ONE legal token (the move surface is constrained)
    pruned       -- on a PROVABLY-wrong pick (its predicate is false for n) prune that token, re-pick
    restructured -- decompose the 4-way choice into ordered yes/no predicates (externalized structure)
    tool         -- route to the deterministic classifier (always correct)

THE MEASUREMENT GUARD (the lesson that a bad matcher can fake the exact lift we are looking for):
grading is the VERIFIED predicate itself -- `_truth(n)`, the math -- and a pick is matched by EXACT
token membership, never substring/fuzzy. Pruning removes only moves the predicate PROVES illegal; it
never reveals the answer, so the model still has to choose the right token among what remains.

    python -m python.scbe.token_board            # reference (truth) board -- validates the harness
    python -m python.scbe.token_board --model qwen2.5-coder:1.5b   # a real small model
"""

from __future__ import annotations

import argparse
import os
from typing import Callable, Dict, List, Optional, Sequence

from src import numtheory as nt

Ask = Callable[[str], str]

# A conlang token -> (label, gloss). Each label is backed by a verified predicate via _truth().
TOKENS: Dict[str, tuple] = {
    "UNE": ("unit", "n is 1 (a unit: neither prime nor composite)"),
    "ZOR": ("prime", "n is prime"),
    "KAEL": ("prime-power", "n is a power of a single prime, p^k with k>=2 (e.g. 8=2^3, 49=7^2)"),
    "VEX": ("composite", "n has two or more distinct prime factors (e.g. 12, 91)"),
}
LABELS = [v[0] for v in TOKENS.values()]


def _truth(n: int) -> str:
    """Ground truth = the math, computed deterministically (the verifier AND the tool)."""
    if n <= 1:
        return "unit"
    if nt.is_prime(n):
        return "prime"
    return "prime-power" if len(nt.factorization(n)) == 1 else "composite"


def _board_text(legal: Sequence[str]) -> str:
    return "\n".join("  %s = %s" % (t, TOKENS[t][1]) for t in legal)


def _parse_token(reply: str, legal: Sequence[str]) -> Optional[str]:
    """EXACT token membership -- the measurement guard. Pick the legal token that appears as a word;
    if zero or more than one legal token appears, there is no unambiguous move."""
    up = (reply or "").upper()
    hits = [t for t in legal if t in up]
    return hits[0] if len(hits) == 1 else None


def _parse_label(reply: str) -> Optional[str]:
    low = (reply or "").lower()
    hits = [lbl for lbl in LABELS if lbl in low]
    # 'prime' is a substring of 'prime-power' -> prefer the longer match, require uniqueness otherwise
    if "prime-power" in low:
        hits = [h for h in hits if h != "prime"] or hits
    return hits[0] if len(set(hits)) == 1 else None


def _yes(reply: str) -> bool:
    return (reply or "").strip().lower().startswith("y")


# ---- the five conditions; each returns a predicted label (or None = no valid move) ----


def raw_label(n: int, ask: Ask) -> Optional[str]:
    q = "Classify the number %d as exactly one of: unit, prime, prime-power, composite. Answer one word." % n
    return _parse_label(ask(q))


def board_pick(n: int, ask: Ask) -> Optional[str]:
    legal = list(TOKENS)
    q = "Classify %d. Pick exactly ONE token from this board:\n%s\nReply with only the token." % (n, _board_text(legal))
    tok = _parse_token(ask(q), legal)
    return TOKENS[tok][0] if tok else None


def pruned_pick(n: int, ask: Ask) -> Optional[str]:
    """On a provably-wrong pick (its predicate is false for n) prune that token and re-pick. Only
    illegal moves are removed; the right token is never revealed, so the model still has to find it."""
    legal = list(TOKENS)
    for _ in range(len(TOKENS)):
        if not legal:
            return None
        q = "Classify %d. Pick exactly ONE token:\n%s\nReply with only the token." % (n, _board_text(legal))
        tok = _parse_token(ask(q), legal)
        if tok is None:
            return None
        label = TOKENS[tok][0]
        if label == _truth(n):  # the predicate proves this move legal
            return label
        legal.remove(tok)  # provably illegal -> prune and re-pick
    return None


def restructured_label(n: int, ask: Ask) -> Optional[str]:
    """Decompose the 4-way choice into ordered yes/no predicates -- the model still answers, but the
    decision STRUCTURE is externalized so it can't pick an off-category token."""
    if _yes(ask("Is the number %d equal to 1? Answer yes or no." % n)):
        return "unit"
    if _yes(ask("Is %d a prime number? Answer yes or no." % n)):
        return "prime"
    if _yes(ask("Is %d a power of a single prime (p^k with k>=2, like 8=2^3 or 49=7^2)? Answer yes or no." % n)):
        return "prime-power"
    return "composite"


def tool_label(n: int, ask: Optional[Ask] = None) -> str:
    """Route to the deterministic classifier -- the model is bypassed; the math answers."""
    return _truth(n)


CONDITIONS: Dict[str, Callable[[int, Ask], Optional[str]]] = {
    "raw": raw_label,
    "board": board_pick,
    "pruned": pruned_pick,
    "restructured": restructured_label,
    "tool": tool_label,
}


def run_board(numbers: Sequence[int], ask: Ask) -> Dict[str, Dict[str, object]]:
    """Score every condition over `numbers` by EXACT match against _truth (the math). Honest: a
    None pick (no legal move parsed) counts as wrong, never as a pass."""
    out: Dict[str, Dict[str, object]] = {}
    for name, fn in CONDITIONS.items():
        correct = sum(1 for n in numbers if fn(n, ask) == _truth(n))
        out[name] = {"correct": correct, "of": len(numbers), "acc": round(correct / len(numbers), 3)}
    return out


def make_ask(model: Optional[str] = None, base: Optional[str] = None, key: Optional[str] = None) -> Ask:
    """A real small model as the chooser (Ollama by default). A dead endpoint returns '' -> graded
    wrong, never a fabricated pass."""
    from python.helm import free_generator as fg

    base = base or os.environ.get("SCBE_LLM_BASE", fg.DEFAULT_BASE)
    key = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    model = model or os.environ.get("SCBE_LLM_MODEL", fg.DEFAULT_MODEL)

    def ask(prompt: str) -> str:
        try:
            return fg._chat([{"role": "user", "content": prompt}], base=base, key=key, model=model)
        except Exception:
            return ""

    return ask


def reference_ask(prompt: str) -> str:
    """An oracle chooser -- always answers correctly. Validates the harness: every condition should
    score 100% with it, so any sub-100% under a real model is the model, not a broken board."""
    import re

    m = re.search(r"\b(\d+)\b", prompt)
    n = int(m.group(1)) if m else 0
    low = prompt.lower()
    if "reply with only the token" in low:  # board / pruned: emit the correct token
        return {v[0]: k for k, v in TOKENS.items()}[_truth(n)]
    if "answer yes or no" in low:  # restructure: answer the specific sub-predicate
        if "equal to 1" in low:
            return "yes" if n <= 1 else "no"
        if "a prime number" in low:
            return "yes" if _truth(n) == "prime" else "no"
        return "yes" if _truth(n) == "prime-power" else "no"  # the prime-power question
    return _truth(n)  # raw: emit the correct label


# a default battery with the hard cases the recap flagged (unit=1, prime powers, multi-factor composites)
DEFAULT_NUMBERS: List[int] = [1, 2, 7, 13, 29, 4, 8, 27, 49, 121, 6, 12, 91, 100, 360]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-token-board", description="conlang tokens as a measurable control board")
    ap.add_argument("--model", default=None, help="Ollama model id (omit for the reference oracle)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    ask = make_ask(model=a.model) if a.model else reference_ask
    res = run_board(DEFAULT_NUMBERS, ask)
    who = a.model or "reference-oracle"
    print("TOKEN CONTROL BOARD  (%d numbers)  chooser=%s\n" % (len(DEFAULT_NUMBERS), who))
    for name in CONDITIONS:
        r = res[name]
        print("  %-13s %2d/%-2d  acc=%.3f" % (name, r["correct"], r["of"], r["acc"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
