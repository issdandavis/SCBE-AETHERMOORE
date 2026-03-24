"""Tests for agent squad orchestration."""

import pytest
from src.aetherbrowser.agents import AgentSquad, AgentState, TongueRole
from src.aetherbrowser.ws_feed import WsFeed


class TestSquadCreation:
    def test_squad_has_six_agents(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        assert len(squad.agents) == 6

    def test_all_tongues_present(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        roles = {a.role for a in squad.agents.values()}
        assert roles == {TongueRole.KO, TongueRole.AV, TongueRole.RU, TongueRole.CA, TongueRole.UM, TongueRole.DR}

    def test_all_start_idle(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        for agent in squad.agents.values():
            assert agent.state == AgentState.IDLE


class TestTaskDecomposition:
    def test_research_assigns_av_and_ca(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        assignments = squad.decompose("Research hyperbolic competitors")
        roles_assigned = {a["role"] for a in assignments}
        assert TongueRole.KO in roles_assigned
        assert TongueRole.AV in roles_assigned
        assert TongueRole.CA in roles_assigned

    def test_page_analysis_assigns_ca_and_dr(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        assignments = squad.decompose("Analyze this page", task_type="page")
        roles_assigned = {a["role"] for a in assignments}
        assert TongueRole.KO in roles_assigned
        assert TongueRole.CA in roles_assigned
        assert TongueRole.DR in roles_assigned

    def test_ko_always_leads(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        for task in ["Research X", "Summarize Y", "Analyze Z"]:
            assignments = squad.decompose(task)
            assert any(a["role"] == TongueRole.KO for a in assignments)


class TestAgentState:
    def test_set_agent_state(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        squad.set_state(TongueRole.AV, AgentState.WORKING)
        assert squad.agents[TongueRole.AV].state == AgentState.WORKING

    def test_get_status_snapshot(self):
        feed = WsFeed()
        squad = AgentSquad(feed)
        squad.set_state(TongueRole.CA, AgentState.WORKING)
        snap = squad.status_snapshot()
        assert snap[TongueRole.CA]["state"] == "working"
        assert snap[TongueRole.KO]["state"] == "idle"
