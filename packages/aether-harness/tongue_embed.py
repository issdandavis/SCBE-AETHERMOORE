"""Tongue embedding — memory vectors on the Six Sacred Tongues basis.

A text embedding built from YOUR conlang systems, not a generic hash:

  GOVERNANCE CHANNEL (6 dims, the load-bearing part)
      Project text onto the six tongues as governance axes, using a small
      lexicon seeded from each tongue's own domain + its English-flavored
      morphemes (joy/good→KO intent, oath/iron→RU binding, forge/stone/frame→
      DR structure, null/hollow/ache→UM veil/risk, gear/fizz/bit→CA craft,
      name/note→AV context). Weighted by the φ^k tongue weights from
      langues_metric (KO=1 … DR=φ⁵). This channel is interpretable: every note
      gets a dominant tongue, which is exactly what the governance gate speaks.

  FINGERPRINT CHANNEL (lexical discrimination)
      A deterministic hashed byte-trigram histogram, so two distinct notes
      don't collide. HONEST: this is byte-level surface similarity — the same
      thing the old generic hash did. It carries most of the raw recall
      accuracy; the tongue channel is what (may) add governance-meaningful
      structure on top. bench_tongue_embed.py null-tests which is true.

No new dependencies (stdlib hashlib + numpy, already present). Deterministic
across processes, fixed dim, never returns a zero vector.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Real φ^k tongue weights from the langues metric (KO=φ⁰ … DR=φ⁵).
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (  # noqa: E402
    TONGUE_WEIGHTS,
    TONGUES,
)

# The six tongues as governance axes. Each axis lexicon is seeded from the
# tongue's own domain (src/crypto/sacred_tongues.py) plus governance-valenced
# terms in its register. Words are matched as stems (prefix match), so
# "binding", "binds", "bound" all hit RU's "bind".
TONGUE_LEXICON: dict[str, list[str]] = {
    "KO": [  # flow / intent / motion — Kor'aelin (nonce/flow/intent)
        "intent",
        "intend",
        "flow",
        "go",
        "goal",
        "move",
        "reach",
        "seek",
        "want",
        "toward",
        "joy",
        "good",
        "open",
        "path",
        "route",
        "head",
        "travel",
        "walk",
        "step",
        "aim",
        "pursue",
        "drive",
    ],
    "AV": [  # context / voice / metadata — Avali (aad/header/metadata)
        "say",
        "said",
        "tell",
        "ask",
        "name",
        "note",
        "report",
        "message",
        "context",
        "who",
        "header",
        "meta",
        "label",
        "record",
        "describe",
        "state",
        "log",
        "tag",
        "title",
        "speak",
        "voice",
        "announce",
    ],
    "RU": [  # binding / oath / trust — Runethic (salt/binding)
        "oath",
        "vow",
        "bind",
        "promise",
        "trust",
        "lock",
        "key",
        "hold",
        "anchor",
        "seal",
        "commit",
        "covenant",
        "pledge",
        "bond",
        "iron",
        "rune",
        "guarantee",
        "secure",
        "honor",
        "loyal",
        "keep",
    ],
    "CA": [  # compute / craft / number — Cassisivadan (ciphertext/bitcraft)
        "compute",
        "count",
        "number",
        "bit",
        "math",
        "gear",
        "code",
        "calc",
        "data",
        "mix",
        "build",
        "factor",
        "prime",
        "sum",
        "loop",
        "machine",
        "engine",
        "calculate",
        "encode",
        "cipher",
        "byte",
        "digit",
    ],
    "UM": [  # risk / veil / concealment — Umbroth (redaction/veil)
        "risk",
        "hazard",
        "danger",
        "hide",
        "veil",
        "null",
        "hollow",
        "ache",
        "dark",
        "threat",
        "warn",
        "harm",
        "shadow",
        "block",
        "deny",
        "delete",
        "attack",
        "malicious",
        "conceal",
        "secret",
        "redact",
        "drown",
        "water",
    ],
    "DR": [  # structure / integrity / place — Draumric (tag/structure)
        "structure",
        "frame",
        "stone",
        "forge",
        "wall",
        "pillar",
        "foundation",
        "integrity",
        "map",
        "corner",
        "north",
        "south",
        "east",
        "west",
        "place",
        "grid",
        "column",
        "row",
        "edge",
        "build",
        "solid",
        "anvil",
        "temper",
    ],
}

_DIM = 96  # 6 governance dims (interpretable) padded into a blended vector
_GOV_GAIN = 1.0  # weight of the governance channel vs the fingerprint channel
_FP_DIM = 90  # fingerprint dimensions (96 - 6)


def _stable_hash(s: str) -> int:
    return int.from_bytes(hashlib.md5(s.encode("utf-8")).digest()[:8], "big")


def tongue_scores(text: str, lexicon: dict[str, list[str]] | None = None) -> np.ndarray:
    """Raw (unweighted) affinity of text to each of the six tongues.

    Stem match: a lexicon entry hits if any whitespace token of the text starts
    with it (so 'binding' matches 'bind'). Returns a length-6 vector aligned to
    TONGUES order [KO, AV, RU, CA, UM, DR].
    """
    lex = lexicon or TONGUE_LEXICON
    tokens = [t.strip(".,!?;:'\"()[]").lower() for t in text.split()]
    tokens = [t for t in tokens if t]
    scores = np.zeros(6, dtype=np.float64)
    for i, tongue in enumerate(TONGUES):
        seeds = lex[tongue]
        for tok in tokens:
            if any(tok.startswith(seed) or seed.startswith(tok) and len(tok) >= 4 for seed in seeds):
                scores[i] += 1.0
    return scores


def governance_channel(text: str, lexicon: dict[str, list[str]] | None = None) -> np.ndarray:
    """6-dim φ^k-weighted tongue projection (the interpretable channel)."""
    scores = tongue_scores(text, lexicon)
    weighted = scores * np.asarray(TONGUE_WEIGHTS, dtype=np.float64)
    n = np.linalg.norm(weighted)
    return weighted / n if n > 0 else weighted


def fingerprint_channel(text: str, dim: int = _FP_DIM) -> np.ndarray:
    """Deterministic hashed byte-trigram histogram (lexical discrimination).

    HONEST: this is surface/byte similarity, equivalent to the old generic
    hash. It keeps distinct notes apart; it carries no governance meaning.
    """
    vec = np.zeros(dim, dtype=np.float64)
    tokens = [t for t in text.lower().split() if t]
    for tok in tokens:
        vec[_stable_hash(tok) % dim] += 2.0
        for i in range(len(tok) - 2):
            vec[_stable_hash(tok[i : i + 3]) % dim] += 1.0
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


def tongue_embed(
    text: str,
    dim: int = _DIM,
    gov_gain: float = _GOV_GAIN,
    lexicon: dict[str, list[str]] | None = None,
) -> np.ndarray:
    """Blend the governance channel (φ-weighted tongues) with the fingerprint.

    The two channels are each unit-normalized, then concatenated with the
    governance channel scaled by ``gov_gain``, and the whole vector is
    re-normalized. Never returns a zero vector.
    """
    gov = governance_channel(text, lexicon) * gov_gain  # 6 dims
    fp = fingerprint_channel(text, dim - 6)  # remaining dims
    blended = np.concatenate([gov, fp])
    n = np.linalg.norm(blended)
    if n == 0:  # no lexicon hit and empty fingerprint — anchor on the text hash
        blended[6 + (_stable_hash(text) % (dim - 6))] = 1.0
        return blended
    return blended / n


def dominant_tongue(text: str, lexicon: dict[str, list[str]] | None = None) -> str | None:
    """The tongue a note speaks loudest in, for governance-tagged memory.

    Uses RAW (unweighted) scores so the tag reflects content, not φ inflation.
    Returns None if the text hits no tongue lexicon.
    """
    scores = tongue_scores(text, lexicon)
    if not scores.any():
        return None
    return TONGUES[int(np.argmax(scores))]
