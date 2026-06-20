"""Playability checker: static target checks and dry-run auto-fill."""

import pytest

from python.helm import Step, dry_run, flag, static_check, upstream


def test_static_check_rejects_missing_upstream():
    steps = [Step("ship", "deploy", lambda objective, context: "x", criteria=(upstream("build", "verified"),))]
    report = static_check(steps)
    assert report.ok is False
    assert "missing upstream step build" in report.errors[0]


def test_static_check_rejects_duplicate_names():
    steps = [
        Step("same", "build", lambda objective, context: {"ok": True}),
        Step("same", "verify", lambda objective, context: {"ok": True}),
    ]
    report = static_check(steps)
    assert report.ok is False
    assert "duplicate step name: same" in report.errors


def test_dry_run_auto_fills_flags_and_upstream_keys_without_real_actions():
    effects = {}
    steps = [
        Step(
            "build",
            "build",
            lambda objective, context: effects.setdefault("real_build", True),
            criteria=(flag("ready"),),
        ),
        Step(
            "ship",
            "deploy",
            lambda objective, context: effects.setdefault("real_ship", True),
            criteria=(upstream("build", "verified", True),),
        ),
    ]
    run = dry_run("ship it", steps)
    assert run.fully_autonomous
    assert run.results["build"]["verified"] is True
    assert effects == {}


def test_dry_run_refuses_unplayable_graph():
    steps = [Step("ship", "deploy", lambda objective, context: "x", criteria=(upstream("missing", "ok"),))]
    with pytest.raises(ValueError, match="missing upstream step"):
        dry_run("x", steps)
