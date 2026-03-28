"""Tests for the Poincare disk topology engine."""

import math

import pytest

from src.aetherbrowser.topology_engine import (
    classify_zone,
    compute_langues_cost_gradient,
    compute_page_topology,
    project_to_disk,
    semantic_distance,
)


class TestSemanticDistance:
    def test_identical_text_is_zero(self):
        d = semantic_distance("hello world", "hello world")
        assert d == 0.0

    def test_no_overlap_is_one(self):
        d = semantic_distance("alpha beta gamma", "delta epsilon zeta")
        assert d == 1.0

    def test_partial_overlap_is_between_zero_and_one(self):
        d = semantic_distance("python machine learning", "python data science")
        assert 0 < d < 1

    def test_empty_text_is_one(self):
        assert semantic_distance("", "hello") == 1.0
        assert semantic_distance("hello", "") == 1.0

    def test_url_contributes_to_similarity(self):
        d_without = semantic_distance("github repository", "click here")
        d_with = semantic_distance(
            "github repository", "click here", "https://github.com/repo"
        )
        assert d_with < d_without


class TestClassifyZone:
    def test_github_is_green(self):
        assert classify_zone("https://github.com/issdandavis") == "GREEN"

    def test_reddit_is_yellow(self):
        assert classify_zone("https://reddit.com/r/python") == "YELLOW"

    def test_unknown_is_red(self):
        assert classify_zone("https://evil-site.example.com") == "RED"

    def test_subdomain_of_green(self):
        assert classify_zone("https://api.github.com/repos") == "GREEN"

    def test_www_prefix_stripped(self):
        assert classify_zone("https://www.github.com/foo") == "GREEN"


class TestProjectToDisk:
    def test_zero_distance_at_origin(self):
        x, y = project_to_disk(0, 0)
        assert x == pytest.approx(0, abs=1e-10)
        assert y == pytest.approx(0, abs=1e-10)

    def test_coordinates_inside_unit_disk(self):
        for d in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            for angle in [0, math.pi / 4, math.pi / 2, math.pi]:
                x, y = project_to_disk(d, angle)
                r = math.sqrt(x * x + y * y)
                assert r < 1.0, f"r={r} >= 1 for d={d}, angle={angle}"

    def test_larger_distance_gives_larger_radius(self):
        _, _ = project_to_disk(0.1, 0)
        r1 = math.sqrt(
            project_to_disk(0.1, 0)[0] ** 2 + project_to_disk(0.1, 0)[1] ** 2
        )
        r2 = math.sqrt(
            project_to_disk(1.0, 0)[0] ** 2 + project_to_disk(1.0, 0)[1] ** 2
        )
        assert r2 > r1


class TestLanguesCostGradient:
    def test_gradient_has_correct_length(self):
        stops = compute_langues_cost_gradient(n_samples=10)
        assert len(stops) == 10

    def test_cost_increases_toward_boundary(self):
        stops = compute_langues_cost_gradient()
        costs = [s["cost"] for s in stops]
        # Cost should generally increase (monotone for most of the range)
        assert costs[-1] > costs[0]

    def test_radius_ranges_from_zero_to_one(self):
        stops = compute_langues_cost_gradient()
        assert stops[0]["radius"] == 0.0
        assert stops[-1]["radius"] == 1.0


class TestComputePageTopology:
    def test_empty_links_returns_center_only(self):
        result = compute_page_topology(
            url="https://example.com",
            title="Test Page",
            text="Some content",
            links=[],
        )
        assert result["center"]["url"] == "https://example.com"
        assert result["node_count"] == 0
        assert len(result["nodes"]) == 0

    def test_nodes_inside_unit_disk(self):
        links = [
            {"text": "GitHub", "href": "https://github.com"},
            {"text": "Reddit", "href": "https://reddit.com"},
            {"text": "Unknown", "href": "https://example.org"},
        ]
        result = compute_page_topology(
            url="https://test.com",
            title="Test",
            text="programming github code",
            links=links,
        )
        for node in result["nodes"]:
            r = math.sqrt(node["x"] ** 2 + node["y"] ** 2)
            assert r < 1.0, f"Node {node['label']} at r={r} outside disk"

    def test_zone_rings_present(self):
        result = compute_page_topology(
            url="https://test.com",
            title="Test",
            text="content",
            links=[{"text": "link", "href": "https://example.com"}],
        )
        assert len(result["zone_rings"]) == 3
        zones = [r["zone"] for r in result["zone_rings"]]
        assert "GREEN" in zones
        assert "YELLOW" in zones
        assert "RED" in zones

    def test_langues_cost_present(self):
        result = compute_page_topology(
            url="https://test.com",
            title="Test",
            text="content",
            links=[],
        )
        assert len(result["langues_cost"]) > 0

    def test_max_nodes_capped(self):
        links = [
            {"text": f"Link {i}", "href": f"https://example{i}.com"} for i in range(100)
        ]
        result = compute_page_topology(
            url="https://test.com",
            title="Test",
            text="content",
            links=links,
            max_nodes=40,
        )
        assert result["node_count"] <= 40

    def test_center_node_at_origin(self):
        result = compute_page_topology(
            url="https://test.com",
            title="Test",
            text="content",
            links=[{"text": "a", "href": "https://a.com"}],
        )
        assert result["center"]["x"] == 0.0
        assert result["center"]["y"] == 0.0
        assert result["center"]["zone"] == "GREEN"
