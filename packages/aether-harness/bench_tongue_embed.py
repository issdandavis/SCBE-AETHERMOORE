"""Null-test the tongue embedding — is the six-tongue basis load-bearing?

The honest question is NOT "does tongue recall work?" but "does the SPECIFIC
tongue structure beat a shuffled-tongue null?" We compare three embeddings on a
labeled recall set whose queries deliberately share little SURFACE wording with
their target note but DO share governance MEANING (so a byte-fingerprint alone
struggles, and only a real semantic axis can close the gap):

    (a) generic char-hash      — the old baseline (byte surface similarity)
    (b) tongue embedding       — φ-weighted six-tongue axes + fingerprint
    (c) shuffled-lexicon null  — (b) with every seed word randomly reassigned to
                                 a different tongue (same words, broken grouping)

Verdict:
    b > a  → the tongue axes add recall on top of surface similarity.
    b > c  → the SPECIFIC tongue groupings (not just "having 6 buckets") are
             what carry the signal. This is the load-bearing test.
    b ≈ c  → decorative for RECALL; keep the channel only for the interpretable
             governance tag (dominant_tongue), and say so plainly.

Run:  python packages/aether-harness/bench_tongue_embed.py
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

import numpy as np

_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

import tongue_embed as te  # noqa: E402

# A labeled recall set. Each note carries governance-valenced content; each query
# targets one note by MEANING while avoiding most of its surface words.
NOTES: dict[str, str] = {
    "blocked_delete": "the gate refused a recursive wipe that would erase the whole tree",
    "water_peril": "a flooded channel cuts the map in two and will drown anything crossing",
    "agent_vow": "the worker swore never to touch the sealed vault and to keep that promise",
    "factor_job": "the task was to find the prime divisors of the large locking integer",
    "who_sent": "the header recorded which operator dispatched the inbound request",
    "goal_corner": "the objective sits in the far upper-right of the field, reached by heading there",
    "fortress_wall": "the rampart is a solid stone structure framing the northern edge",
    "trust_handoff": "control was pledged to the next holder under a binding agreement",
}

QUERIES: list[tuple[str, str]] = [
    ("which hazardous operation was stopped", "blocked_delete"),
    ("where on the map is it dangerous to step", "water_peril"),
    ("what did the worker pledge not to do", "agent_vow"),
    ("compute the divisors of the number", "factor_job"),
    ("who issued the incoming message", "who_sent"),
    ("how do I get to the destination", "goal_corner"),
    ("describe the defensive stonework", "fortress_wall"),
    ("what was promised to the successor", "trust_handoff"),
    ("a destructive command that was denied", "blocked_delete"),
    ("the deadly part of the terrain", "water_peril"),
]


def char_hash_embed(text: str, dim: int = 64) -> np.ndarray:
    """The previous generic embedding — byte-trigram surface hash."""
    vec = np.zeros(dim, dtype=np.float64)
    for tok in (t for t in text.lower().split() if t):
        vec[_h(tok) % dim] += 2.0
        for i in range(len(tok) - 2):
            vec[_h(tok[i : i + 3]) % dim] += 1.0
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def _h(s: str) -> int:
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:8], "big")


def shuffled_lexicon(seed: int = 7) -> dict[str, list[str]]:
    """Same seed words, randomly reassigned across tongues (broken grouping)."""
    rng = random.Random(seed)
    all_words = [w for words in te.TONGUE_LEXICON.values() for w in words]
    rng.shuffle(all_words)
    sizes = [len(te.TONGUE_LEXICON[t]) for t in te.TONGUES]
    out, k = {}, 0
    for t, sz in zip(te.TONGUES, sizes):
        out[t] = all_words[k : k + sz]
        k += sz
    return out


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def evaluate(embed_fn) -> tuple[float, float]:
    """Return (recall@1, MRR) over the query set for an embedding function."""
    note_vecs = {k: embed_fn(v) for k, v in NOTES.items()}
    keys = list(NOTES)
    hits, rr = 0, 0.0
    for query, target in QUERIES:
        q = embed_fn(query)
        ranked = sorted(keys, key=lambda k: _cos(q, note_vecs[k]), reverse=True)
        rank = ranked.index(target) + 1
        hits += 1 if rank == 1 else 0
        rr += 1.0 / rank
    n = len(QUERIES)
    return hits / n, rr / n


def run() -> dict[str, tuple[float, float]]:
    shuf = shuffled_lexicon()
    results = {
        "a_char_hash": evaluate(char_hash_embed),
        "b_tongue": evaluate(te.tongue_embed),
        "c_shuffled_null": evaluate(lambda t: te.tongue_embed(t, lexicon=shuf)),
        "gov_only": evaluate(te.governance_channel),  # the 6-dim axis channel alone
    }
    return results


def main() -> int:
    r = run()
    print("\n  TONGUE EMBEDDING — null-test (recall@1 / MRR over governance queries)\n")
    print(f"  {'embedding':22} {'recall@1':>9} {'MRR':>7}")
    print("  " + "─" * 42)
    for name, (rec, mrr) in r.items():
        print(f"  {name:22} {rec:>9.2f} {mrr:>7.2f}")
    print("  " + "─" * 42)

    a = r["a_char_hash"][1]
    b = r["b_tongue"][1]
    c = r["c_shuffled_null"][1]
    g = r["gov_only"][1]
    print(f"\n  b vs a (tongue adds over surface hash): {b - a:+.2f} MRR")
    print(f"  b vs c (specific groupings vs shuffled): {c and b - c:+.2f} MRR")
    print(f"  governance channel alone:               {g:.2f} MRR")
    if b > a + 0.02 and b > c + 0.02:
        verdict = "LOAD-BEARING — tongue axes add recall AND the specific groupings matter."
    elif b > c + 0.02:
        verdict = "PARTIALLY load-bearing — groupings beat shuffled, but no lift over the hash."
    else:
        verdict = "DECORATIVE for recall — keep the tongue channel only for the governance TAG."
    print(f"\n  VERDICT: {verdict}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
