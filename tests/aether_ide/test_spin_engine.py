"""Tests for aether_ide.spin_engine."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.spin_engine import SpinEngine


def test_spin_returns_dict():
    se = SpinEngine()
    result = se.spin("test topic")
    assert isinstance(result, dict)
    assert "topic" in result
    assert "trajectory" in result


def test_spin_count():
    se = SpinEngine()
    assert se.spin_count == 0
    se.spin("topic 1")
    assert se.spin_count == 1
    se.spin("topic 2")
    assert se.spin_count == 2


def test_spin_trajectory_length():
    se = SpinEngine()
    result = se.spin("test", spins=5)
    assert len(result["trajectory"]) >= 1
