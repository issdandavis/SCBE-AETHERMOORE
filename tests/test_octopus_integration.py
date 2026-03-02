# tests/test_octopus_integration.py
"""Integration test: full Octopus Kernel flow with all components."""
import pytest
import tempfile

@pytest.mark.asyncio
async def test_full_octopus_flow():
    """Eye observes -> Judge triangulates -> Forge creates tool -> Site log updated."""
    from src.browser.octopus_kernel import OctopusKernel
    from src.browser.navigation_randomtest import NavigationGraph, NavigationRandomtest
    from src.browser.tool_forge import ToolForge
    from src.browser.jitter_engine import JitterEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        kernel = OctopusKernel(site_log_dir=tmpdir)
        jitter = JitterEngine(seed=42)

        # 1. Eye observes
        vision = await kernel.eye.observe_mock(
            url="https://shopify.com/admin",
            a11y_tree={"role": "document", "children": [
                {"role": "button", "name": "Login"},
                {"role": "textbox", "name": "Email"},
                {"role": "textbox", "name": "Password"},
            ]},
            page_text="Sign in to your Shopify admin",
        )
        assert vision.page_type == "login"
        assert len(vision.interactive_elements) == 3

        # 2. Judge triangulates
        el_names = [e["name"] for e in vision.interactive_elements]
        tri = await kernel.judge.triangulate(
            a11y_elements=el_names,
            dom_elements=el_names,
            visual_elements=el_names,
        )
        assert tri.consensus is True

        # 3. Randomtest the navigation graph
        graph = NavigationGraph()
        graph.add_page("/", links=["/admin", "/products"])
        graph.add_page("/admin", links=["/admin/login"])
        graph.add_page("/admin/login", links=[])  # dead end without auth
        graph.add_page("/products", links=["/", "/products/1"])
        graph.add_page("/products/1", links=["/products"])

        tester = NavigationRandomtest(iterations=100, max_steps=10, seed=42)
        report = tester.run(graph)
        assert "/admin/login" in report.dead_ends

        # 4. Forge creates a tool for the dead end
        forge = ToolForge()
        tools = forge.from_report(domain="shopify.com", report=report)
        assert len(tools) >= 1
        login_tool = [t for t in tools if "login" in t.trigger.lower()]
        assert len(login_tool) >= 1

        # 5. Site log is updated
        log = kernel.site_log_store.get_or_create("shopify.com")
        assert log.domain == "shopify.com"

        # 6. Jitter provides diversity
        delay = jitter.next_delay_ms()
        ua = jitter.next_user_agent()
        vp = jitter.next_viewport()
        assert 200 <= delay <= 2000
        assert "Mozilla" in ua
        assert len(vp) == 2
