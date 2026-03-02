# tests/test_jitter_engine.py
import pytest

def test_jitter_timing_in_range():
    from src.browser.jitter_engine import JitterEngine
    engine = JitterEngine(timing_range_ms=(200, 2000), seed=42)
    delays = [engine.next_delay_ms() for _ in range(100)]
    assert all(200 <= d <= 2000 for d in delays)
    assert len(set(delays)) > 10  # not all the same

def test_jitter_user_agent_rotation():
    from src.browser.jitter_engine import JitterEngine
    engine = JitterEngine(seed=42)
    agents = [engine.next_user_agent() for _ in range(20)]
    assert len(set(agents)) > 1  # rotates

def test_jitter_viewport_variation():
    from src.browser.jitter_engine import JitterEngine
    engine = JitterEngine(seed=42)
    viewports = [engine.next_viewport() for _ in range(10)]
    assert all(isinstance(v, tuple) and len(v) == 2 for v in viewports)
    assert len(set(viewports)) > 1

def test_jitter_config_serializable():
    from src.browser.jitter_engine import JitterEngine
    engine = JitterEngine(timing_range_ms=(100, 500))
    config = engine.to_dict()
    assert config["timing_range_ms"] == [100, 500]
    assert "user_agents" in config
