"""Helm demo stays runnable and honest."""

from python.helm.demo import render_demo, run_demo


def test_demo_reports_playable_workflow_and_broken_graph():
    result = run_demo()
    text = render_demo(result)

    assert result["playability_ok"] is True
    assert result["dry_run"]["approved"] == 3
    assert result["dag_run"]["approved"] == 3
    assert result["storylet_run"]["order"] == ["discover", "draft", "polish"]
    assert result["broken_graph"]["ok"] is False
    assert "missing upstream step missing" in result["broken_graph"]["errors"][0]
    assert "Helm demo: AI workflow playability checker" in text
