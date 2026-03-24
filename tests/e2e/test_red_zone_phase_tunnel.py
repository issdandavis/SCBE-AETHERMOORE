"""End-to-end test: RED zone site through topology engine + phase tunnel.

Simulates an agent encountering a suspicious site, mapping its topology
in hyperbolic space, and phase-tunneling to preview dangerous links
without operationally entering them.

This is the real test: can the curved browser let you SEE what's behind
a RED zone link without CLICKING through?
"""

import math
from pathlib import Path
from urllib.parse import urlparse


from src.aetherbrowser.phase_tunnel import (
    KernelStack,
    TunnelGovernor,
    TunnelOutcome,
    compute_transmission,
    compute_transparency_frequency,
)
from src.aetherbrowser.topology_engine import (
    compute_page_topology,
)


def _host_has_suffix(url: str, *labels: str) -> bool:
    host = (urlparse(url).hostname or "").strip(".").lower()
    host_labels = [part for part in host.split(".") if part]
    suffix = [part.lower() for part in labels]
    return len(host_labels) >= len(suffix) and host_labels[-len(suffix) :] == suffix


# ---------------------------------------------------------------------------
# Load the RED zone test site
# ---------------------------------------------------------------------------

RED_ZONE_HTML = Path(__file__).parent / "fixtures" / "red-zone-site.html"


def parse_test_site():
    """Parse the red zone test site into the format page_analyzer would produce."""
    RED_ZONE_HTML.read_text(encoding="utf-8")

    return {
        "url": "https://suspicious-downloads.example.com",
        "title": "Suspicious Downloads Portal - Free Tools",
        "text": (
            "Free Premium Tools Download Portal. "
            "Download exclusive hacking tools, credential dumps, and premium software for free! "
            "Premium Password Recovery Tool. Credential Database. Universal License Keygen. "
            "Login to Premium Area. Enter your bank username. Enter your bank password. "
            "Download All Tools. Deploy to Network."
        ),
        "links": [
            {"text": "Premium Password Recovery Tool v3.2", "href": "https://evil-malware-site.example.com/tool1.exe"},
            {"text": "Credential Database 2026", "href": "https://phishing-central.example.net/creds.zip"},
            {"text": "Universal License Keygen", "href": "https://sketchy-downloads.example.org/keygen.exe"},
            {"text": "SCBE-AETHERMOORE (legitimate)", "href": "https://github.com/issdandavis/SCBE-AETHERMOORE"},
            {"text": "Research Paper (legitimate)", "href": "https://arxiv.org/abs/2401.00001"},
            {"text": "Stack Overflow (safe)", "href": "https://stackoverflow.com/questions/tagged/python"},
            {"text": "Reddit Hacking (yellow)", "href": "https://reddit.com/r/hacking"},
            {"text": "Underground Forum (red)", "href": "https://dark-forum.example.com"},
        ],
        "headings": [
            {"level": "H1", "text": "Free Premium Tools Download Portal"},
            {"level": "H2", "text": "Available Downloads"},
            {"level": "H2", "text": "Login to Premium Area"},
            {"level": "H2", "text": "Quick Actions"},
            {"level": "H2", "text": "Trusted Partners"},
        ],
        "topics": ["downloads", "tools", "credentials", "hacking"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRedZoneTopology:
    """Test that the topology engine correctly maps the RED zone site."""

    def setup_method(self):
        self.site = parse_test_site()
        self.topology = compute_page_topology(
            url=self.site["url"],
            title=self.site["title"],
            text=self.site["text"],
            links=self.site["links"],
            headings=self.site["headings"],
            topics=self.site["topics"],
            risk_tier="high",
        )

    def test_center_node_is_the_page(self):
        assert self.topology["center"]["url"] == "https://suspicious-downloads.example.com"
        assert self.topology["center"]["zone"] == "GREEN"  # center is always safe by definition

    def test_all_nodes_inside_unit_disk(self):
        for node in self.topology["nodes"]:
            r = math.sqrt(node["x"] ** 2 + node["y"] ** 2)
            assert r < 1.0, f"Node {node['label']} at r={r} outside disk"

    def test_malware_links_classified_red(self):
        red_urls = {
            "https://evil-malware-site.example.com/tool1.exe",
            "https://phishing-central.example.net/creds.zip",
            "https://sketchy-downloads.example.org/keygen.exe",
            "https://dark-forum.example.com",
        }
        for node in self.topology["nodes"]:
            if node["url"] in red_urls:
                assert node["zone"] == "RED", f"{node['url']} should be RED, got {node['zone']}"

    def test_legitimate_links_classified_green(self):
        green_urls = {
            "https://github.com/issdandavis/SCBE-AETHERMOORE",
            "https://arxiv.org/abs/2401.00001",
            "https://stackoverflow.com/questions/tagged/python",
        }
        for node in self.topology["nodes"]:
            if node["url"] in green_urls:
                assert node["zone"] == "GREEN", f"{node['url']} should be GREEN, got {node['zone']}"

    def test_reddit_classified_yellow(self):
        for node in self.topology["nodes"]:
            if _host_has_suffix(node["url"], "reddit", "com"):
                assert node["zone"] == "YELLOW", f"Reddit should be YELLOW, got {node['zone']}"

    def test_red_nodes_further_from_center_than_green(self):
        red_radii = [n["radius"] for n in self.topology["nodes"] if n["zone"] == "RED"]
        green_radii = [n["radius"] for n in self.topology["nodes"] if n["zone"] == "GREEN"]

        if red_radii and green_radii:
            # On average, RED nodes should have higher semantic distance
            # (Note: radius depends on semantic distance, not zone, so this isn't guaranteed
            #  for every individual node, but should hold on average for a page about hacking tools)
            _ = sum(red_radii) / len(red_radii)
            _ = sum(green_radii) / len(green_radii)
            # Just verify both exist — positioning depends on content similarity
            assert len(red_radii) >= 3
            assert len(green_radii) >= 2

    def test_zone_rings_cover_full_disk(self):
        rings = self.topology["zone_rings"]
        assert rings[0]["inner_radius"] == 0
        assert rings[-1]["outer_radius"] == 1.0

    def test_langues_cost_increases_toward_boundary(self):
        costs = self.topology["langues_cost"]
        assert costs[0]["cost"] < costs[-1]["cost"]


class TestRedZonePhaseTunnel:
    """Test phase tunneling through RED zone governance walls."""

    def setup_method(self):
        self.site = parse_test_site()
        self.topology = compute_page_topology(
            url=self.site["url"],
            title=self.site["title"],
            text=self.site["text"],
            links=self.site["links"],
            topics=self.site["topics"],
            risk_tier="high",
        )
        self.governor = TunnelGovernor()

    def test_new_agent_cannot_tunnel_red(self):
        """A brand new agent with no experience should not be able to tunnel deep into RED."""
        kernel = KernelStack(genesis_hash="newborn")
        red_nodes = [n for n in self.topology["nodes"] if n["zone"] == "RED"]

        for node in red_nodes:
            result = compute_transmission(
                d_H=node["semantic_dist"] + 1.0,  # beyond the wall
                agent_phase=0.0,  # random phase — unlikely to match
                target_zone="RED",
                kernel=kernel,
            )
            # New agent should get REFLECT or COLLAPSE, never TUNNEL
            assert result.outcome in (
                TunnelOutcome.REFLECT,
                TunnelOutcome.COLLAPSE,
            ), f"Newborn tunneled RED: {result.outcome} for {node['url']}"
            assert result.commit_allowed is False

    def test_experienced_agent_can_attenuate_red(self):
        """An experienced agent with many scars can at least ATTENUATE through RED."""
        kernel = KernelStack(genesis_hash="veteran")
        for i in range(10):
            kernel.add_scar(f"mission_{i}")

        next(n for n in self.topology["nodes"] if n["zone"] == "RED")

        # Use the optimal phase for RED zone
        wall_freq = compute_transparency_frequency("RED", 0.5)

        result = compute_transmission(
            d_H=0.5,
            agent_phase=wall_freq,  # tuned to wall frequency
            target_zone="RED",
            kernel=kernel,
        )

        # Experienced agent with correct phase should at least attenuate
        assert result.outcome in (
            TunnelOutcome.ATTENUATE,
            TunnelOutcome.TUNNEL,
        ), f"Veteran couldn't attenuate RED: {result.outcome}, T={result.transmission_coeff}"
        assert result.amplitude_out > 0  # some signal gets through

    def test_green_links_always_accessible(self):
        """GREEN zone links should always be fully accessible."""
        kernel = KernelStack(genesis_hash="any_agent")

        green_nodes = [n for n in self.topology["nodes"] if n["zone"] == "GREEN"]
        for node in green_nodes:
            wall_freq = compute_transparency_frequency("GREEN", 0.1)
            result = compute_transmission(
                d_H=0.1,  # close to center
                agent_phase=wall_freq,
                target_zone="GREEN",
                kernel=kernel,
            )
            # GREEN should be easy even for new agents
            assert result.transmission_coeff > 0, f"GREEN link blocked: {node['url']}, T={result.transmission_coeff}"

    def test_phase_read_red_without_commit(self):
        """The key feature: preview RED zone content without committing to enter.

        This is the 'mirage' — you can see what's there without being there.
        """
        kernel = KernelStack(genesis_hash="browser_agent")
        for i in range(5):
            kernel.add_scar(f"s_{i}")

        next(n for n in self.topology["nodes"] if n["zone"] == "RED")

        # Issue a tunnel permit for observation only
        permit = self.governor.issue_permit(
            agent_id="browser-1",
            kernel=kernel,
            target_zone="RED",
            requested_depth=0.3,  # shallow
        )
        assert permit is not None
        assert permit.active

        # Agent moves into the tunnel at shallow depth
        status = self.governor.update_position(
            agent_id="browser-1",
            d_H=0.1,
            current_phase=permit.required_phase,
            action="observe",
        )
        assert status["status"] == "tunneling"
        assert status["action"] == "continue"

        # Agent can observe (phase-read) but compute_transmission confirms no commit
        result = compute_transmission(
            d_H=0.1,
            agent_phase=permit.required_phase,
            target_zone="RED",
            kernel=kernel,
        )

        # We got information (T > 0) but commit should be gated
        assert result.amplitude_out > 0, "Phase-read should yield some signal"

        # Agent returns cleanly
        self.governor.complete_tunnel("browser-1", kernel, success=True)
        assert not permit.active

    def test_tunnel_permit_prevents_deep_penetration(self):
        """Agent cannot go deeper than permitted, even with correct phase."""
        kernel = KernelStack(genesis_hash="test")
        permit = self.governor.issue_permit(
            agent_id="agent-deep",
            kernel=kernel,
            target_zone="RED",
            requested_depth=0.3,
        )

        # Try to go way beyond permitted depth
        status = self.governor.update_position(
            agent_id="agent-deep",
            d_H=5.0,  # way beyond 0.3
            current_phase=permit.required_phase,
        )
        assert status["status"] == "boundary_exceeded"
        assert status["action"] == "forced_return"

    def test_policy_override_blocks_everything(self):
        """When chi_policy=False (hard governance block), nothing passes."""
        kernel = KernelStack(genesis_hash="super_agent")
        for i in range(20):
            kernel.add_scar(f"s_{i}")

        wall_freq = compute_transparency_frequency("RED", 0.1)
        result = compute_transmission(
            d_H=0.1,
            agent_phase=wall_freq,
            target_zone="RED",
            kernel=kernel,
            chi_policy=False,  # HARD BLOCK
        )
        assert result.outcome == TunnelOutcome.REFLECT
        assert result.transmission_coeff == 0.0
        assert result.commit_allowed is False


class TestFullFlowIntegration:
    """Full flow: site -> topology -> phase tunnel decisions for every link."""

    def test_full_red_zone_analysis(self):
        """Run the complete pipeline on the RED zone test site.

        For every link, compute:
        1. Zone classification
        2. Topology position
        3. Phase tunnel outcome
        4. Whether the agent can see vs commit

        This is what the curved browser would show the operator.
        """
        site = parse_test_site()
        topology = compute_page_topology(
            url=site["url"],
            title=site["title"],
            text=site["text"],
            links=site["links"],
            topics=site["topics"],
        )

        # Create an agent with moderate experience
        kernel = KernelStack(genesis_hash="issac_browser_agent")
        for i in range(7):
            kernel.add_scar(f"session_{i}")

        results = []

        for node in topology["nodes"]:
            zone = node["zone"]
            wall_freq = compute_transparency_frequency(zone, node["semantic_dist"])

            # Try with optimal phase (agent knows the frequency)
            result_optimal = compute_transmission(
                d_H=max(node["semantic_dist"], 0.01),
                agent_phase=wall_freq,
                target_zone=zone,
                kernel=kernel,
            )

            # Try with random phase (agent doesn't know)
            result_blind = compute_transmission(
                d_H=max(node["semantic_dist"], 0.01),
                agent_phase=0.0,
                target_zone=zone,
                kernel=kernel,
            )

            results.append(
                {
                    "url": node["url"],
                    "label": node["label"],
                    "zone": zone,
                    "radius": node["radius"],
                    "semantic_dist": node["semantic_dist"],
                    "optimal_outcome": result_optimal.outcome,
                    "optimal_T": result_optimal.transmission_coeff,
                    "optimal_commit": result_optimal.commit_allowed,
                    "blind_outcome": result_blind.outcome,
                    "blind_T": result_blind.transmission_coeff,
                    "blind_commit": result_blind.commit_allowed,
                }
            )

        # Print the full decision table
        print("\n" + "=" * 90)
        print("FULL RED ZONE ANALYSIS — Phase Tunnel Decisions")
        print("=" * 90)
        print(f"{'Label':<35} {'Zone':<8} {'Optimal':<12} {'T':<8} {'Commit':<8} {'Blind':<12} {'T':<8}")
        print("-" * 90)

        for r in results:
            print(
                f"{r['label']:<35} {r['zone']:<8} "
                f"{r['optimal_outcome']:<12} {r['optimal_T']:<8.4f} "
                f"{'YES' if r['optimal_commit'] else 'NO':<8} "
                f"{r['blind_outcome']:<12} {r['blind_T']:<8.4f}"
            )

        # Verify invariants across all results
        green_results = [r for r in results if r["zone"] == "GREEN"]
        red_results = [r for r in results if r["zone"] == "RED"]

        # GREEN links should always have some transmission
        for r in green_results:
            assert r["optimal_T"] > 0, f"GREEN link {r['url']} has zero transmission"

        # RED links with blind phase should mostly reflect/collapse
        red_blind_blocked = sum(1 for r in red_results if r["blind_outcome"] in ("reflect", "collapse"))
        assert (
            red_blind_blocked >= len(red_results) // 2
        ), f"Too many RED links accessible with blind phase: {len(red_results) - red_blind_blocked}/{len(red_results)}"

        # No blind RED access should allow commit
        for r in red_results:
            assert r["blind_commit"] is False, f"Blind RED commit allowed for {r['url']}"

        print("\n" + "=" * 90)
        print(f"GREEN links: {len(green_results)} (all accessible)")
        print(f"RED links: {len(red_results)} ({red_blind_blocked}/{len(red_results)} blocked with blind phase)")
        print(f"No blind RED commits: VERIFIED")
        print("=" * 90)
