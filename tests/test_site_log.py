# tests/test_site_log.py
import json
import pytest
from pathlib import Path

def test_site_log_create_new_domain():
    """Creating a log for unknown domain initializes defaults."""
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_site_logs")
    log = store.get_or_create("github.com")
    assert log.domain == "github.com"
    assert log.visit_count == 0
    assert log.success_rate == 0.0
    assert log.status == "unknown"

def test_site_log_record_visit():
    """Recording a successful visit updates counters."""
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_site_logs")
    log = store.get_or_create("github.com")
    log.record_visit(path=["/", "/login", "/dashboard"], success=True, time_ms=1200)
    assert log.visit_count == 1
    assert log.success_rate == 1.0
    assert ["/", "/login", "/dashboard"] in log.reliable_paths

def test_site_log_record_failure():
    """Recording a failed visit tracks failure point."""
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_site_logs")
    log = store.get_or_create("shopify.com")
    log.record_visit(path=["/", "/admin", "/products"], success=False, time_ms=5000, failure_point="/admin")
    assert log.visit_count == 1
    assert log.success_rate == 0.0
    assert "/admin" in log.failure_patterns

def test_site_log_persist_and_reload():
    """Logs persist to JSON and reload correctly."""
    from src.browser.site_log import SiteLogStore
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        store1 = SiteLogStore(base_dir=tmpdir)
        log1 = store1.get_or_create("example.com")
        log1.record_visit(path=["/"], success=True, time_ms=500)
        store1.save(log1)

        store2 = SiteLogStore(base_dir=tmpdir)
        log2 = store2.get_or_create("example.com")
        assert log2.visit_count == 1
        assert log2.success_rate == 1.0

def test_site_log_navigation_map():
    """Can store and retrieve named navigation targets."""
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_site_logs")
    log = store.get_or_create("notion.so")
    log.set_nav_target("login_button", "button[data-testid='login']")
    log.set_nav_target("search_box", "input[type='search']")
    assert log.navigation_map["login_button"] == "button[data-testid='login']"
    assert len(log.navigation_map) == 2

def test_site_log_status_lifecycle():
    """Status progresses: unknown -> exploring -> mapped -> reliable."""
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_site_logs")
    log = store.get_or_create("test.com")
    assert log.status == "unknown"
    log.record_visit(path=["/"], success=True, time_ms=100)
    assert log.status == "exploring"
    for i in range(9):
        log.record_visit(path=["/", f"/page{i}"], success=True, time_ms=100)
    assert log.status == "mapped"  # 10+ visits
    # 20+ visits with >90% success -> reliable
    for i in range(10):
        log.record_visit(path=["/", f"/deep{i}"], success=True, time_ms=100)
    assert log.status == "reliable"
