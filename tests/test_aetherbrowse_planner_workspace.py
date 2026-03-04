from aetherbrowse.runtime.planner import plan_rule_based


def test_workspace_shortcut_colab():
    plan = plan_rule_based("open google colab", page_context="", perception=None)
    assert plan.method == "rule_based"
    assert plan.steps[0].action == "navigate"
    assert "colab.research.google.com" in plan.steps[0].value


def test_workspace_profile_switch():
    plan = plan_rule_based("switch profile to creator-main", page_context="", perception=None)
    actions = [s.action for s in plan.steps]
    assert actions == ["switch_profile", "list_profiles"]
    assert plan.steps[0].profile_id == "creator-main"


def test_workspace_autofill_login_parse():
    plan = plan_rule_based("autofill login for github.com and submit", page_context="", perception=None)
    assert plan.steps[0].action == "autofill_login"
    assert plan.steps[0].value == "github.com"
    assert plan.steps[0].submit is True


def test_workspace_shortcut_replit_repo():
    plan = plan_rule_based("open replit build repo", page_context="", perception=None)
    assert plan.steps[0].action == "navigate"
    assert "ai-workflow-architect-replit" in plan.steps[0].value
