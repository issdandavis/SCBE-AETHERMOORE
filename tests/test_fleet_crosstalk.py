"""Tests for the governed AI-to-AI fleet cross-talk engine (src/fleet_crosstalk.py)."""

import pytest

from src import fleet_crosstalk as fc


def _stub_score(allow_all=True, deny_substr=None):
    """A deterministic score_fn: DENY messages containing deny_substr, else ALLOW."""

    def score(text):
        if deny_substr and deny_substr in text:
            return {"decision": "DENY", "H_eff": 0.1}
        return {"decision": "ALLOW", "H_eff": 1.0}

    return score


def _echo_responder(agent, topic, turns):
    """Deterministic responder: states who is speaking and how many turns precede it."""
    return f"{agent.name} turn after {len(turns)} prior on {topic}"


def test_turn_count_and_structure():
    agents = [fc.Agent("A"), fc.Agent("B")]
    result = fc.run_crosstalk("widgets", agents, rounds=3, responder=_echo_responder, score_fn=_stub_score())
    assert result["governance"]["total"] == 6  # 2 agents x 3 rounds
    assert result["agents"] == ["A", "B"]
    assert [t["agent"] for t in result["turns"]] == ["A", "B", "A", "B", "A", "B"]
    assert [t["round"] for t in result["turns"]] == [1, 1, 2, 2, 3, 3]
    assert all(t["accepted"] for t in result["turns"])


def test_sieve_withholds_flagged_turns():
    agents = [fc.Agent("Clean"), fc.Agent("Bad")]

    def responder(agent, topic, turns):
        return "BLOCKME payload" if agent.name == "Bad" else "all good here"

    result = fc.run_crosstalk("x", agents, rounds=2, responder=responder, score_fn=_stub_score(deny_substr="BLOCKME"))
    g = result["governance"]
    assert g["total"] == 4
    assert g["accepted"] == 2 and g["withheld"] == 2
    assert g["by_decision"] == {"ALLOW": 2, "DENY": 2}
    bad_turns = [t for t in result["turns"] if t["agent"] == "Bad"]
    assert all(not t["accepted"] and t["decision"] == "DENY" for t in bad_turns)


def test_no_gate_accepts_everything_but_still_scores():
    agents = [fc.Agent("Bad")]

    def responder(agent, topic, turns):
        return "BLOCKME"

    result = fc.run_crosstalk(
        "x", agents, rounds=2, responder=responder, score_fn=_stub_score(deny_substr="BLOCKME"), gate=False
    )
    assert result["governance"]["accepted"] == 2
    assert result["governance"]["by_decision"] == {"DENY": 2}  # scored, just not withheld


def test_withheld_turns_excluded_from_history():
    """A withheld turn must not appear in the context the next speaker receives."""
    seen_histories = []

    def responder(agent, topic, turns):
        seen_histories.append(fc._accepted_history(turns))
        return "BLOCKME" if agent.name == "Bad" else "fine"

    agents = [fc.Agent("Bad"), fc.Agent("Good")]
    fc.run_crosstalk("x", agents, rounds=1, responder=responder, score_fn=_stub_score(deny_substr="BLOCKME"))
    # Good speaks after Bad; Bad's turn was withheld, so Good sees an empty history.
    assert seen_histories[1] == []


def test_invalid_args_raise():
    with pytest.raises(ValueError):
        fc.run_crosstalk("x", [], rounds=1, responder=_echo_responder, score_fn=_stub_score())
    with pytest.raises(ValueError):
        fc.run_crosstalk("x", [fc.Agent("A")], rounds=0, responder=_echo_responder, score_fn=_stub_score())


def test_make_ai_responder_handles_str_and_tuple():
    calls = []

    def ask_tuple(prompt, backend, model):
        calls.append((backend, model))
        return ("tuple-answer", backend or "auto")

    def ask_str(prompt, backend, model):
        return "str-answer"

    r1 = fc.make_ai_responder(ask_tuple)
    r2 = fc.make_ai_responder(ask_str)
    a = fc.Agent("A", backend="openai", model="gpt-4o-mini")
    assert r1(a, "topic", []) == "tuple-answer"
    assert r2(a, "topic", []) == "str-answer"
    assert calls == [("openai", "gpt-4o-mini")]


def test_eliza_responder_is_deterministic_and_nonempty():
    a = fc.Agent("Proposer", persona="proposes ideas")
    out1 = fc.eliza_responder(a, "scaling the fleet", [])
    out2 = fc.eliza_responder(a, "scaling the fleet", [])
    assert out1 == out2
    assert out1.startswith("(Proposer)")
    assert len(out1) > len("(Proposer) ")


def test_eliza_crosstalk_end_to_end_offline():
    """Full offline run with the real ELIZA responder and a permissive scorer."""
    agents = [fc.Agent("Proposer", "proposes ideas"), fc.Agent("Skeptic", "finds risks")]
    result = fc.run_crosstalk(
        "how to route a free-LLM fleet", agents, rounds=2, responder=fc.eliza_responder, score_fn=_stub_score()
    )
    assert result["governance"]["total"] == 4
    assert all(t["message"] for t in result["turns"])  # no empty turns
