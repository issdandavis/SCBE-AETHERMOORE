"""Tests for command planning and orchestration signals."""

from src.aetherbrowser.agents import AgentSquad
from src.aetherbrowser.command_planner import _infer_risk, build_command_plan
from src.aetherbrowser.router import ModelProvider, OctoArmorRouter
from src.aetherbrowser.ws_feed import WsFeed


class TestCommandPlanner:
    def test_build_command_plan_for_browser_task(self):
        squad = AgentSquad(WsFeed())
        router = OctoArmorRouter(enabled_providers={provider: True for provider in ModelProvider})

        plan = build_command_plan(
            text="Open the browser tab, fill the login form, and submit it",
            squad=squad,
            router=router,
        )

        assert plan.browser_action_required is True
        assert plan.escalation_ready is True
        assert plan.intent == "authenticate"
        assert plan.provider == "opus"
        assert plan.preferred_engine == "playwright"
        assert plan.risk_tier == "high"
        assert plan.approval_required is True
        assert plan.review_zone == "RED"
        assert plan.required_approvals
        assert any(action.requires_approval for action in plan.next_actions)
        assert plan.fallback_chain
        assert any(item["role"].value == "KO" for item in plan.assignments)

    def test_build_command_plan_without_cloud_escalation(self):
        squad = AgentSquad(WsFeed())
        router = OctoArmorRouter(
            enabled_providers={
                ModelProvider.LOCAL: True,
                ModelProvider.HAIKU: False,
                ModelProvider.SONNET: False,
                ModelProvider.OPUS: False,
                ModelProvider.FLASH: False,
                ModelProvider.GROK: False,
                ModelProvider.HUGGINGFACE: False,
            }
        )

        plan = build_command_plan(
            text="Summarize this page",
            squad=squad,
            router=router,
        )

        assert plan.escalation_ready is False
        assert plan.provider == "local"
        assert plan.intent == "analyze_page"
        assert plan.risk_tier == "low"
        assert plan.approval_required is False
        assert plan.next_actions

    def test_to_dict_normalizes_assignments_and_actions(self):
        squad = AgentSquad(WsFeed())
        router = OctoArmorRouter(enabled_providers={provider: True for provider in ModelProvider})

        plan = build_command_plan(
            text="Research GitHub competitors",
            squad=squad,
            router=router,
        )

        payload = plan.to_dict()
        assert payload["intent"] == "research"
        assert payload["risk_tier"] == "low"
        assert payload["targets"] == ["github.com"]
        assert payload["assignments"][0]["role"] == "KO"
        assert payload["next_actions"][0]["label"]

    def test_build_command_plan_honors_request_preferences(self):
        squad = AgentSquad(WsFeed())
        router = OctoArmorRouter(enabled_providers={provider: True for provider in ModelProvider})

        plan = build_command_plan(
            text="Summarize this page",
            squad=squad,
            router=router,
            routing_preferences={"KO": "sonnet"},
            auto_cascade=False,
        )

        assert plan.provider == "sonnet"
        assert plan.selection_reason == "preference_override"
        assert plan.auto_cascade is False
        assert plan.fallback_chain == ["sonnet"]

    def test_risk_gate_mcdc_condition_independence(self):
        """MC/DC-style independence pairs for the browser risk decision.

        The decision inputs are:
        A = auth keyword present
        S = side-effect keyword present
        H = high-risk keyword present
        B = browser action required
        R = read-only keyword present
        """
        cases = [
            # Baseline: no approvals, low risk.
            ("baseline", "inspect page", False, "low", []),
            # A independently changes approvals from none to medium.
            ("auth", "inspect token", False, "medium", ["Uses authentication or credentials"]),
            # S independently changes approvals from none to medium.
            ("side_effect", "inspect update", False, "medium", ["Performs a state-changing browser action"]),
            # H independently changes tier to high.
            ("high_risk", "inspect delete", False, "high", ["Touches a high-impact flow"]),
            # B independently adds approval when the action is not clearly read-only.
            ("browser_unknown", "open dashboard", True, "medium", ["Browser action is not clearly read-only"]),
            # R independently masks the browser-action approval and returns to low.
            ("browser_read_only", "open read dashboard", True, "low", []),
        ]

        for _name, text, browser_action_required, expected_tier, expected_reason_fragments in cases:
            lowered = text.lower()
            tokens = set(lowered.split())
            risk_tier, approvals = _infer_risk(
                lowered=lowered,
                tokens=tokens,
                browser_action_required=browser_action_required,
            )
            assert risk_tier == expected_tier
            for fragment in expected_reason_fragments:
                assert any(fragment in approval for approval in approvals)
