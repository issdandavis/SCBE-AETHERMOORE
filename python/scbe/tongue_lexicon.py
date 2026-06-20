"""tongue_lexicon: a SEMANTIC classifier on top of the token grid.

The grid (tongue_diff.grid_encode / packages/sixtongues) is the ENCODING face -- bytes <-> syllables.
This is the MEANING face: a pluggable LEXICON (tongue-specific words -> tongue + meaning) that classifies
an input by which tongue's vocabulary its words belong to. The tongues started as CONLANGS, so the real
classifier is a dictionary lookup against each tongue's word list.

SEEDED from the real conlang word-fragments already in the repo (the 16 sixtongues prefixes per tongue:
KO sil/kor/vel..., UM veil/zhur/nar..., etc.) -- so it works NOW on conlang text. The fuller conlang
word->meaning dictionaries live in Issac's other systems; bring any per-tongue word list and drop it in
with `add_wordlist` / `merge` -- same shape, no code change. Honest scope: the SEED is form-fragments,
not full word->meaning; a richer dictionary makes the classification richer.

    from python.scbe.tongue_lexicon import load_seed
    lex = load_seed()
    lex.classify("veil the shade in dusk")   # -> {'UM': ['veil', 'shade', 'dusk']}
    lex.add_wordlist("CA", ["fizz", "buzz", "loop"])   # ingest more conlang/role words
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .tongue_diff import _GRID_CODE, _grid

_WORD = re.compile(r"[a-z']+")


class Lexicon:
    """tongue -> {word: meaning}. classify() = which tongue's words an input contains."""

    def __init__(self) -> None:
        self.words: Dict[str, Dict[str, str]] = {code: {} for code in _GRID_CODE}

    def add(self, tongue: str, word: str, meaning: str = "") -> None:
        self.words[tongue][word.lower().strip()] = meaning

    def add_wordlist(self, tongue: str, words: Sequence[str]) -> None:
        """Drop in a per-tongue word list (the shape Issac's conlang dictionaries provide)."""
        for w in words:
            if w:
                self.add(tongue, w)

    def merge(self, other: "Lexicon") -> "Lexicon":
        for tongue, wm in other.words.items():
            self.words.setdefault(tongue, {}).update(wm)
        return self

    def size(self) -> int:
        return sum(len(wm) for wm in self.words.values())

    def classify(self, text: str) -> Dict[str, List[str]]:
        """{tongue: [matched words]} -- the multi-state Venn membership, now by real vocabulary."""
        toks = set(_WORD.findall((text or "").lower()))
        hits: Dict[str, List[str]] = {}
        for tongue, wm in self.words.items():
            found = sorted(t for t in toks if t in wm)
            if found:
                hits[tongue] = found
        return hits

    def best(self, text: str) -> Optional[str]:
        """The dominant tongue (most matched words), or None."""
        hits = self.classify(text)
        return max(hits, key=lambda t: len(hits[t])) if hits else None

    def meaning(self, word: str) -> Dict[str, str]:
        """{tongue: meaning} for a word across all tongues it appears in (multi-state Venn)."""
        w = word.lower().strip()
        return {t: wm[w] for t, wm in self.words.items() if w in wm}

    def load_conlang(self, path: str) -> "Lexicon":
        """Ingest a real conlang file: {tongue, words{...}, particles{...}, roots{...}} -> word:meaning.
        This is the slot Issac's word lists drop into -- e.g. lexicons/kor_aelin.json (the KO tongue)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        tongue = data["tongue"]
        for section in ("particles", "roots", "words"):
            for word, gloss in (data.get(section) or {}).items():
                self.add(tongue, word, gloss)
        return self


def load_seed() -> Lexicon:
    """Seed from the REAL sixtongues conlang prefixes (16 tongue-specific fragments per tongue). Real
    vocabulary, in-repo; merge fuller word->meaning dictionaries on top when they arrive."""
    m = _grid()
    inv = {v: k for k, v in _GRID_CODE.items()}  # 'ko' -> 'KO'
    lex = Lexicon()
    for code, spec in m.TONGUES.items():
        lex.add_wordlist(inv[code], list(spec.prefixes))
    return lex


def load_full(lexicon_dir: Optional[str] = None) -> Lexicon:
    """The seed (form-fragments) PLUS every real conlang file in lexicons/ -- so when Issac drops a
    word list (kor_aelin.json today; the other five tongues next), it merges automatically. A conlang
    file is any JSON with a 'tongue' key + a 'words'/'particles'/'roots' section."""
    lex = load_seed()
    root = Path(lexicon_dir) if lexicon_dir else Path(__file__).resolve().parents[2] / "lexicons"
    for f in sorted(root.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "tongue" in data and any(k in data for k in ("words", "particles", "roots")):
            lex.load_conlang(str(f))
    return lex


if __name__ == "__main__":
    lex = load_seed()
    print("SEMANTIC TONGUE CLASSIFIER  (seed lexicon: %d words from the real conlang fragments)\n" % lex.size())
    for s in ["veil the shade in dusk", "kor vel zar", "anvil forge seal the oath", "bip bop fizz the gear"]:
        print("  %-32s -> %s   best=%s" % ("'" + s + "'", lex.classify(s), lex.best(s)))
    print("\n  ingest a fuller word list:")
    lex.add_wordlist("UM", ["whisper", "conceal", "shroud"])
    print("  'conceal the whisper' ->", lex.classify("conceal the whisper"))
