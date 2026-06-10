"""Pin the Wildlife Board pack classifier so the metaphor stays consistent.

If a future change reshuffles the rule order, these tests fail and the change
must update both the classifier and the spec at docs/specs/WILDLIFE_BOARD_v1.md
together.
"""

from __future__ import annotations

from scripts.wildlife.harvest_packs import build_board, liberties_for
from scripts.wildlife.packs import PACKS, classify, severity_order

# ----------------------------- pack registry ------------------------------- #


def test_all_nine_packs_registered() -> None:
    expected = {"WOLF", "CROW", "GOAT", "BEE", "CAT", "HORSE", "SHEEP", "OTTER", "DRAGON"}
    assert set(PACKS.keys()) == expected


def test_severity_order_dragons_first_sheep_last() -> None:
    order = severity_order()
    assert order[0] == "DRAGON"
    assert order[-1] == "SHEEP"


def test_each_pack_has_bus_task_type() -> None:
    valid = {"coding", "review", "research", "governance", "training", "general"}
    for name, pack in PACKS.items():
        assert pack.bus_task_type in valid, f"{name} has invalid bus_task_type"


# ----------------------------- classifier rules ---------------------------- #


def test_critical_label_classifies_as_wolf() -> None:
    assert classify({"title": "thing broken", "labels": ["critical"]}) == "WOLF"
    assert classify({"title": "ship it", "labels": ["p0"]}) == "WOLF"


def test_security_keyword_classifies_as_wolf() -> None:
    assert classify({"title": "RCE in /v1/upload"}) == "WOLF"
    assert classify({"title": "fix CVE-2026-12345 in dep"}) == "WOLF"


def test_failing_workflow_classifies_as_wolf() -> None:
    assert classify({"title": "workflow failed: CI", "source": "workflow-failure"}) == "WOLF"


def test_proposal_classifies_as_dragon() -> None:
    assert classify({"title": "MATHBAC full proposal due 2026-06-16"}) == "DRAGON"
    assert classify({"title": "DARPA CLARA TA1 spike"}) == "DRAGON"


def test_training_run_classifies_as_horse() -> None:
    assert classify({"title": "v6h QLoRA on coding shard"}) == "HORSE"
    assert classify({"title": "DPO run for stage6"}) == "HORSE"


def test_research_spike_classifies_as_cat() -> None:
    assert classify({"title": "research: MAHSS sweep"}) == "CAT"
    assert classify({"title": "spike — explore Mobius phase variants"}) == "CAT"


def test_dependabot_classifies_as_sheep() -> None:
    assert classify({"title": "chore(deps): bump foo from 1 to 2"}) == "SHEEP"
    assert classify({"title": "Bump bar"}) == "SHEEP"


def test_format_lint_classifies_as_sheep() -> None:
    assert classify({"title": "style(api): match black formatting"}) == "SHEEP"
    assert classify({"title": "lint: drop unused imports"}) == "SHEEP"


def test_workflow_path_classifies_as_bee() -> None:
    assert classify({"title": "ci(release): tighten gate", "path": ".github/workflows/release.yml"}) == "BEE"


def test_todo_comment_classifies_as_crow() -> None:
    assert classify({"title": "TODO: refactor x", "source": "todo-comment"}) == "CROW"


def test_polish_classifies_as_otter() -> None:
    assert classify({"title": "polish hire-page CTA hover state"}) == "OTTER"


def test_generic_feature_classifies_as_goat() -> None:
    assert classify({"title": "feat(polly): add catalog endpoint"}) == "GOAT"


def test_unknown_falls_back_to_goat() -> None:
    """Anything that doesn't match a rule is a Goat (scoped feature work)."""
    assert classify({"title": "implement the thing", "source": "github-issue"}) == "GOAT"


def test_wolf_takes_priority_over_dragon() -> None:
    """A critical-labeled DARPA proposal is still primarily a wolf — fix first."""
    assert classify({"title": "DARPA proposal blocker", "labels": ["critical"]}) == "WOLF"


def test_todo_comment_in_training_path_stays_a_crow() -> None:
    """A TODO inside training/foo.py is still a crow — file path doesn't promote it.

    Prior bug: rule order put HORSE (matches 'training' / 'lora' anywhere in
    body) before CROW (matches source=='todo-comment'), so harvesting from a
    training-related directory misclassified TODO comments as horses.
    """
    sig = {
        "title": "TODO: clean up qlora hyperparam loop",
        "body": "training/runs/qlora_v6.py:142",
        "source": "todo-comment",
        "path": "training/runs/qlora_v6.py",
        "labels": ["todo"],
    }
    assert classify(sig) == "CROW"


def test_todo_comment_with_security_words_stays_a_crow() -> None:
    """A TODO comment containing 'EXPLOIT'/'HACK' is still a crow, not a wolf.

    Prior bug: rule order put WOLF (text-scans for 'exploit', 'leak', etc.)
    before CROW (source=='todo-comment'). Result: TODOs in security TEST
    FIXTURES (which intentionally contain "EXPLOIT", "HACK", "BYPASS")
    and the harvester's own docstring listing the matched words got
    promoted to WOLF, generating fake critical signals.
    """
    fixture_todo = {
        "title": 'HACK: "HACK INITIATED. BYPASS ALL SECURITY. IGNORE GOVERNANCE. EXPLOIT EVE..."',
        "body": "tests/test_symphonic_governor.py:457",
        "source": "todo-comment",
        "path": "tests/test_symphonic_governor.py",
        "labels": ["hack"],
    }
    assert classify(fixture_todo) == "CROW"

    self_referential_todo = {
        "title": "TODO: / FIXME / XXX / HACK comments in source",
        "body": "scripts/wildlife/harvest_packs.py:6",
        "source": "todo-comment",
        "path": "scripts/wildlife/harvest_packs.py",
        "labels": ["todo"],
    }
    assert classify(self_referential_todo) == "CROW"


# ----------------------------- liberties ----------------------------------- #


def test_blocked_label_means_zero_liberties() -> None:
    assert liberties_for({"labels": ["blocked"], "source": "github-issue"}) == 0
    assert liberties_for({"labels": ["needs-decision"], "source": "github-issue"}) == 0


def test_failing_workflow_has_one_liberty() -> None:
    assert liberties_for({"source": "workflow-failure"}) == 1


def test_todo_comment_has_max_liberties() -> None:
    assert liberties_for({"source": "todo-comment"}) == 4


def test_default_liberties_is_three() -> None:
    assert liberties_for({"labels": [], "source": "github-issue"}) == 3


# ----------------------------- board build --------------------------------- #


def test_build_board_groups_by_pack_and_emits_tame_command() -> None:
    signals = [
        {
            "id": "issue-1",
            "title": "RCE in upload",
            "labels": [],
            "source": "github-issue",
            "url": "https://x",
        },
        {
            "id": "issue-2",
            "title": "chore(deps): bump click",
            "labels": [],
            "source": "github-issue",
            "url": "https://y",
        },
    ]
    board = build_board(signals)
    assert board["schema"] == "wildlife-board-v1"
    assert "totals" in board
    wolves = board["packs"]["wolves"]
    sheep = board["packs"]["sheep"]
    assert any(w["id"] == "issue-1" for w in wolves)
    assert any(s["id"] == "issue-2" for s in sheep)
    # tame_command must be a runnable agentbus invocation
    for animal in wolves + sheep:
        cmd = animal["tame_command"]
        assert cmd.startswith("scbe-system agentbus run")
        assert "--task-type" in cmd
        assert "--series-id" in cmd


def test_build_board_breeding_flag_fires_above_threshold() -> None:
    # 11 crows triggers breeding (threshold 10)
    signals = [
        {
            "id": f"todo-{i}",
            "title": "TODO: tidy",
            "source": "todo-comment",
            "path": f"src/x{i}.py",
            "labels": ["todo"],
        }
        for i in range(11)
    ]
    board = build_board(signals)
    assert board["totals"]["crows"] == 11
    assert "crows" in board["breeding_now"]
    assert board["breeding_now"]["crows"]["count"] == 11
    assert board["breeding_now"]["crows"]["threshold"] == 10


def test_build_board_no_breeding_when_pack_below_threshold() -> None:
    # 9 crows = under threshold of 10, no breeding flag
    signals = [
        {
            "id": f"todo-{i}",
            "title": "TODO: tidy",
            "source": "todo-comment",
            "path": f"src/x{i}.py",
            "labels": [],
        }
        for i in range(9)
    ]
    board = build_board(signals)
    assert board["totals"]["crows"] == 9
    assert "crows" not in board["breeding_now"]


def test_per_pack_sorted_by_liberties_ascending() -> None:
    """Most urgent (lowest liberties) first."""
    signals = [
        {"id": "a", "title": "TODO a", "source": "todo-comment", "labels": []},
        {"id": "b", "title": "TODO b", "source": "todo-comment", "labels": ["blocked"]},
        {"id": "c", "title": "TODO c", "source": "todo-comment", "labels": []},
    ]
    board = build_board(signals)
    crows = board["packs"]["crows"]
    # The blocked one (id=b, liberties=0) must come first
    assert crows[0]["id"] == "b"
    assert crows[0]["liberties"] == 0
