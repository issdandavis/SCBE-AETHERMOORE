"""Speech senses, compatible sharing and perspective boundaries, not learned accuracy."""

from fractions import Fraction
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from python.scbe.function_lexicon import (  # noqa: E402
    FunctionLexicon,
    ROLES,
    normalize_ratios,
    perspective_views,
    resolve_reference,
)
from python.scbe.tongue_lexicon import Lexicon, load_full  # noqa: E402


def test_six_existing_wordlists_load_shared_registry_without_polluting_native_words():
    lex = load_full()
    assert set(lex.functions.bindings) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert lex.meaning("maeji'kor") == {"KO": "heart of magic"}
    assert lex.meaning("the") == {}
    for tongue in lex.functions.bindings:
        words = lex.functions.wordlist(tongue)
        assert len(words) == len(lex.functions.entries) >= 100
        assert len({w["codec_payload"] for w in words}) == len(words)
    assert lex.functions.wordlist("AV")[0]["representation"] == "derived_codec_sequence_not_native_translation"
    assert lex.functions.bindings["AV"]["native_bindings"]["nos"] == ["pron.we.unspecified"]


def test_all_five_course_families_and_four_content_families():
    f = FunctionLexicon()
    assert {"article", "preposition", "conjunction", "pronoun", "helping_verb"} <= {
        e["family"] for e in f.entries.values()
    }
    assert {"noun", "verb", "adjective", "adverb"} <= {
        e["family"] for e in f.entries.values() if e["kind"] == "content"
    }
    assert f.lookup("one")[0]["kind"] == "content"
    assert f.lookup("one")[0]["upos"] == "NUM"


def test_homographs_keep_senses_and_unknown_stays_unknown():
    f = FunctionLexicon()
    assert {e["family"] for e in f.lookup("that")} == {"determiner", "pronoun", "conjunction"}
    assert {e["kind"] for e in f.lookup("have")} == {"content", "function"}
    assert len(f.lookup("have", family="helping_verb")) == 1
    assert f.lookup("qzxunknown") == []


def test_exact_ratios_preserve_subdecimal_mass():
    mix = normalize_ratios({"speaker": "0.0001", "listener": "0.1"}, ROLES)
    assert mix["speaker"] == "1/1001" and mix["listener"] == "1000/1001"
    assert sum(Fraction(v) for v in mix.values()) == 1
    assert mix["omniscient_narrator"] == "0"


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"speaker": 0},
        {"speaker": -1},
        {"speaker": True},
        {"speaker": "NaN"},
        {"speaker": float("inf")},
        {"bogus": 1},
    ],
)
def test_invalid_ratios_fail(weights):
    with pytest.raises(ValueError):
        normalize_ratios(weights, ROLES)


def test_compatible_scope_sharing_preserves_occurrences():
    f = FunctionLexicon()
    out = f.compose(
        [
            {"id": "pron.we.unspecified", "scope": "s", "referent": "team", "weight": 1},
            {"id": "pron.we.inclusive", "scope": "s", "referent": "team", "weight": 3},
        ],
        perspective={"speaker": 3, "listener": 1},
        stance={"positive": 1, "negative": 1},
        topic="plan",
    )
    cell = out["cells"]["s"]
    assert cell["features"]["Clusivity"] == "In"
    assert [m["ratio"] for m in cell["occurrences"]] == ["1/4", "3/4"]
    assert out["stance"]["ratios"] == {"negative": "1/2", "neutral": "0", "positive": "1/2"}
    assert out["perspective"]["speaker"] == "3/4"


def test_stance_cannot_flip_negation_and_incompatible_scopes_cannot_be_averaged():
    f = FunctionLexicon()
    out = f.compose([{"id": "part.negation", "scope": "clause"}], stance={"positive": 999}, topic="weather")
    assert out["cells"]["clause"]["features"]["Polarity"] == "Neg"
    with pytest.raises(ValueError, match="Conflicting"):
        f.compose(
            [{"id": "pron.speaker.subject", "scope": "same"}, {"id": "pron.addressee", "scope": "same", "weight": 1000}]
        )
    with pytest.raises(ValueError, match="referents"):
        f.compose(
            [
                {"id": "pron.third.they", "scope": "same", "referent": "A"},
                {"id": "pron.third.they", "scope": "same", "referent": "B"},
            ]
        )
    separate = f.compose(
        [{"id": "pron.speaker.subject", "scope": "subject"}, {"id": "pron.addressee", "scope": "object"}]
    )
    assert len(separate["cells"]) == 2


def test_you_means_addressee_not_everyone_who_heard():
    f = FunctionLexicon()
    frame = {"speaker": "Ada", "addressees": ["Bo"], "hearers": ["Bo", "Cy"], "listeners": ["Cy"]}
    assert resolve_reference(f.entry("pron.speaker.subject"), frame) == ["Ada"]
    assert resolve_reference(f.entry("pron.addressee"), frame) == ["Bo"]
    assert resolve_reference(f.entry("pron.addressee"), {"hearers": ["Cy"]}) == []
    assert resolve_reference(f.entry("pron.third.they"), {}) == []


def test_inclusive_exclusive_we_and_nested_quotation_frames():
    f = FunctionLexicon()
    frame = {"speaker": "Ada", "addressees": ["Bo"], "group_members": ["Ada", "Bo"]}
    assert resolve_reference(f.entry("pron.we.inclusive"), frame) == ["Ada", "Bo"]
    with pytest.raises(ValueError):
        resolve_reference(f.entry("pron.we.exclusive"), frame)
    assert resolve_reference(f.entry("pron.speaker.subject"), {"speaker": "Bo", "addressees": ["Ada"]}) == ["Bo"]
    assert resolve_reference(f.entry("pron.we.unspecified"), {"speaker": "Ada"}) == []


def test_narrator_facts_never_leak_into_listener_projection():
    facts = [
        {"id": "secret", "text": "The key is blue.", "known_by": ["Ada"], "status": "fictional"},
        {"id": "report", "text": "Bo reports rain.", "known_by": ["Ada", "Bo"], "status": "reported"},
    ]
    result = perspective_views(
        facts, {"speaker": ["Ada"], "listener": ["Bo"]}, {"listener": 1, "omniscient_narrator": 9}
    )
    assert [f["id"] for f in result[0]["facts"]] == ["report"]
    assert len(result[1]["facts"]) == 2
    assert result[0]["ratio"] == "1/10"
    assert result[1]["ratio"] == "9/10"
    assert result[0]["facts"][0]["status"] == "reported"
    unknown = perspective_views(facts, {}, {"nonparticipant": 1})
    assert unknown[0]["facts"] == [] and unknown[0]["status"] == "UNBOUND"


def test_multiple_listeners_keep_individual_views_and_total_mass():
    facts = [{"id": "f", "text": "Only Bo was told.", "known_by": ["Bo"], "status": "fictional"}]
    views = perspective_views(facts, {"listener": ["Bo", "Cy"]}, {"listener": 1})
    assert [len(v["facts"]) for v in views] == [1, 0]
    assert sum(Fraction(v["ratio"]) for v in views) == 1


def test_dictionary_merge_preserves_functions_and_native_provenance():
    lex = Lexicon().merge(load_full())
    assert len(lex.function_meaning("the")) == 1
    assert len(lex.functions.bindings) == 6
    dr = json.loads((ROOT / "lexicons/draumric.json").read_text())
    assert "RULE-GENERATED" in dr["source"]


def test_registry_rejects_duplicate_ids_and_unknown_native_binding(tmp_path):
    f = FunctionLexicon()
    data = f.document
    data["entries"].append(data["entries"][0])
    path = tmp_path / "function_primitives.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Duplicate"):
        FunctionLexicon(path)
    source = json.loads((ROOT / "lexicons/avali.json").read_text())
    source["function_words"]["native_bindings"]["invented"] = ["pron.we.unspecified"]
    with pytest.raises(ValueError, match="existing word"):
        FunctionLexicon().bind_conlang(source)
