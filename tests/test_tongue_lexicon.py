"""tongue_lexicon: the semantic classifier on top of the grid -- a pluggable conlang word->tongue lexicon.

Proves the seed (real sixtongues conlang fragments) classifies tongue-specific words, multi-state Venn
membership (a word shared by two tongues), and that a fuller word list drops in via add_wordlist/merge.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import tongue_lexicon as tl  # noqa: E402


def test_seed_classifies_conlang_words_to_the_right_tongue():
    lex = tl.load_seed()
    assert lex.size() == 96  # 6 tongues x 16 real conlang prefixes
    assert lex.best("veil the shade in dusk") == "UM"  # redaction/veil tongue
    assert lex.best("kor vel zar") == "KO"
    assert lex.best("bip bop fizz the gear") == "CA"


def test_multi_state_venn_a_word_shared_by_two_tongues():
    lex = tl.load_seed()
    hits = lex.classify("anvil forge seal the oath")
    assert "DR" in hits  # anvil/forge/seal/oath are Draumric (auth/integrity)
    assert "oath" in hits.get("RU", []) and "oath" in hits["DR"]  # 'oath' lives in BOTH -> Venn overlap


def test_fuller_wordlist_drops_in():
    lex = tl.load_seed()
    assert lex.classify("conceal the whisper") == {}  # not in the seed
    lex.add_wordlist("UM", ["whisper", "conceal", "shroud"])  # ingest a fuller list
    assert lex.best("conceal the whisper") == "UM"


def test_merge_two_lexicons():
    a = tl.Lexicon()
    a.add_wordlist("KO", ["qbegin"])
    b = tl.Lexicon()
    b.add_wordlist("DR", ["zsign"])
    a.merge(b)
    assert a.best("the qbegin step") == "KO"  # a's own word
    assert a.best("the zsign here") == "DR"  # b's word, after merge


def test_no_match_is_empty_not_a_guess():
    lex = tl.load_seed()
    assert lex.classify("a plain english sentence with no tongue words") == {}
    assert lex.best("nothing here") is None


def test_real_kor_aelin_conlang_loads_and_classifies():
    # the payoff: Issac's real Kor'aelin word list drops in and the classifier reads it WITH meaning
    full = tl.load_full()
    seed = tl.load_seed()
    assert full.size() > seed.size()  # conlang words merged on top of the seed
    assert full.best("the zar'thul opens and maeji'kor flows") == "KO"
    assert full.best("sil binds, thul transforms, ael endures") == "KO"  # the 7 sacred particles
    assert full.meaning("maeji'kor") == {"KO": "heart of magic"}
    assert full.meaning("vel")["KO"].startswith("invitation")


def test_load_conlang_file_directly():
    import json
    from pathlib import Path

    path = Path(tl.__file__).resolve().parents[2] / "lexicons" / "kor_aelin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tongue"] == "KO" and "words" in data  # valid conlang-file shape
    lex = tl.Lexicon().load_conlang(str(path))
    assert lex.best("zar'sil'ael") == "KO" and "eternal" in lex.meaning("zar'sil'ael")["KO"]


def test_all_five_word_tongues_classify_from_real_vocab():
    # the full Six Sacred Tongues wordlist: AV/RU/CA/UM/KO now have real words (DR has none yet)
    full = tl.load_full()
    assert full.size() > 200  # seed 96 + the five tongues' vocab
    assert full.best("nos busca sabia in spiral-unity") == "AV"
    assert full.best("gol the vel'ar med'ar oath") == "RU"
    assert full.best("sapi'gear spira'zuni nog rad") == "CA"
    assert full.best("sek drath grul azh the bond") == "UM"
    assert full.best("maeji and kor'val and zar'thul") == "KO"
    assert full.meaning("busca") == {"AV": "seek / search"}
    assert "sever" in full.meaning("sek")["UM"]
