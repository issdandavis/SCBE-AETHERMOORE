"""The Judge (DR) holds a binding veto in swarm roundtable consensus.

Regression for a real governance hole: the count-only aggregator returned
ALLOW on a 4/6 majority even when the Judge cast its risk>0.9 DENY veto, so
the "veto power" promised by JudgeAgent.vote()'s docstring was never honored.
"""

from __future__ import annotations

import asyncio

from agents.swarm_browser import JudgeAgent, SacredTongue, SwarmMessage


def _vote(agent: str, decision: str) -> dict:
    return {"agent": agent, "decision": decision, "confidence": 0.9, "reasoning": ""}


def _judge() -> JudgeAgent:
    # _aggregate_votes never touches self.swarm, so a bare instance is enough.
    return JudgeAgent(swarm=None)


def test_judge_deny_veto_overrides_a_4_of_6_allow_majority():
    judge = _judge()
    votes = [_vote(t, "ALLOW") for t in ("KO", "AV", "RU", "CA", "UM")]
    votes.append(_vote(SacredTongue.DR.value, "DENY"))  # the risk>0.9 veto
    assert judge._aggregate_votes(votes) == "DENY"


def test_judge_escalate_cannot_be_overridden_into_allow():
    judge = _judge()
    votes = [_vote(t, "ALLOW") for t in ("KO", "AV", "RU", "CA")]  # 4/6 ALLOW
    votes.append(_vote("UM", "ALLOW"))
    votes.append(_vote(SacredTongue.DR.value, "ESCALATE"))
    assert judge._aggregate_votes(votes) == "ESCALATE"


def test_unanimous_allow_still_allows_when_judge_agrees():
    judge = _judge()
    votes = [_vote(t, "ALLOW") for t in ("KO", "AV", "RU", "CA", "UM", SacredTongue.DR.value)]
    assert judge._aggregate_votes(votes) == "ALLOW"


def test_two_non_judge_denies_still_deny_via_tally():
    judge = _judge()
    votes = [_vote("KO", "DENY"), _vote("AV", "DENY")]
    votes += [_vote(t, "ALLOW") for t in ("RU", "CA")]
    votes.append(_vote(SacredTongue.DR.value, "ALLOW"))
    assert judge._aggregate_votes(votes) == "DENY"


def test_judge_cannot_loosen_a_tally_denial():
    """A Judge ALLOW must not rescue an action two other agents denied."""
    judge = _judge()
    votes = [_vote("KO", "DENY"), _vote("AV", "DENY"), _vote("RU", "ALLOW")]
    votes.append(_vote(SacredTongue.DR.value, "ALLOW"))
    assert judge._aggregate_votes(votes) == "DENY"


def test_judge_override_flag_is_honest():
    judge = _judge()

    # veto changed the outcome -> override True
    veto_votes = [_vote(t, "ALLOW") for t in ("KO", "AV", "RU", "CA", "UM")]
    veto_votes.append(_vote(SacredTongue.DR.value, "DENY"))
    msg = SwarmMessage(
        id="t", from_agent=SacredTongue.DR, to_agent=None, action="request_approval", payload={"votes": veto_votes}
    )
    out = asyncio.run(judge.process(msg))
    assert out.payload["decision"] == "DENY"
    assert out.payload["judge_override"] is True

    # plain unanimous ALLOW -> Judge agreed, no override
    allow_votes = [_vote(t, "ALLOW") for t in ("KO", "AV", "RU", "CA", "UM", SacredTongue.DR.value)]
    msg2 = SwarmMessage(
        id="t2", from_agent=SacredTongue.DR, to_agent=None, action="request_approval", payload={"votes": allow_votes}
    )
    out2 = asyncio.run(judge.process(msg2))
    assert out2.payload["decision"] == "ALLOW"
    assert out2.payload["judge_override"] is False
