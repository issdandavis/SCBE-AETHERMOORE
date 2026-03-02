# tests/test_navigation_randomtest.py
import pytest

def test_navigation_graph_from_links():
    from src.browser.navigation_randomtest import NavigationGraph
    graph = NavigationGraph()
    graph.add_page("/", links=["/about", "/login", "/products"])
    graph.add_page("/about", links=["/", "/team"])
    graph.add_page("/login", links=["/", "/dashboard"])
    assert len(graph.pages) == 3
    assert graph.pages["/"].links == ["/about", "/login", "/products"]

def test_randomtest_runs_iterations():
    from src.browser.navigation_randomtest import NavigationGraph, NavigationRandomtest
    graph = NavigationGraph()
    graph.add_page("/", links=["/a", "/b"])
    graph.add_page("/a", links=["/", "/b"])
    graph.add_page("/b", links=["/", "/a"])
    tester = NavigationRandomtest(iterations=100, max_steps=10, seed=42)
    report = tester.run(graph)
    assert report.paths_tested == 100
    assert report.success_rate > 0.5
    assert len(report.hot_paths) > 0

def test_randomtest_detects_dead_end():
    from src.browser.navigation_randomtest import NavigationGraph, NavigationRandomtest
    graph = NavigationGraph()
    graph.add_page("/", links=["/dead"])
    graph.add_page("/dead", links=[])  # no way out
    tester = NavigationRandomtest(iterations=50, max_steps=5, seed=42)
    report = tester.run(graph)
    assert "/dead" in report.dead_ends

def test_randomtest_coverage_report():
    from src.browser.navigation_randomtest import NavigationGraph, NavigationRandomtest
    graph = NavigationGraph()
    graph.add_page("/", links=["/a", "/b", "/c"])
    graph.add_page("/a", links=["/"])
    graph.add_page("/b", links=["/"])
    graph.add_page("/c", links=["/"])
    tester = NavigationRandomtest(iterations=200, max_steps=5, seed=42)
    report = tester.run(graph)
    assert report.coverage_pct > 0.5
    assert isinstance(report.cold_paths, list)
    assert isinstance(report.failure_points, list)

def test_quicktest_exhaustive():
    from src.browser.navigation_randomtest import NavigationGraph, NavigationQuicktest
    graph = NavigationGraph()
    graph.add_page("/", links=["/a", "/b"])
    graph.add_page("/a", links=["/c"])
    graph.add_page("/b", links=["/c"])
    graph.add_page("/c", links=[])
    tester = NavigationQuicktest(max_depth=5)
    report = tester.run(graph)
    assert report.all_paths_found >= 2  # / -> /a -> /c  and  / -> /b -> /c
