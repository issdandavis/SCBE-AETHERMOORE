# tests/test_octopus_kernel.py
import pytest
import asyncio

def test_kernel_init():
    from src.browser.octopus_kernel import OctopusKernel
    kernel = OctopusKernel()
    assert kernel.eye is not None
    assert kernel.judge is not None
    assert kernel.forge is not None

def test_kernel_mode_selection():
    from src.browser.octopus_kernel import OctopusKernel
    kernel = OctopusKernel()
    mode = kernel.select_mode(domain="wikipedia.org", action="read")
    assert mode == "sightless"
    mode2 = kernel.select_mode(domain="chase.com", action="submit")
    assert mode2 == "governed_critical"

@pytest.mark.asyncio
async def test_eye_observe_returns_pagevision():
    from src.browser.octopus_kernel import TheEye
    eye = TheEye()
    # Mock observation (no real browser)
    vision = await eye.observe_mock(
        url="https://example.com",
        a11y_tree={"role": "document", "children": [{"role": "button", "name": "Click me"}]},
        page_text="Welcome to Example.com"
    )
    assert vision.page_type is not None
    assert vision.confidence > 0
    assert len(vision.interactive_elements) >= 1

@pytest.mark.asyncio
async def test_judge_triangulate_agreement():
    from src.browser.octopus_kernel import TheJudge
    judge = TheJudge()
    result = await judge.triangulate(
        a11y_elements=["button:Submit", "input:email"],
        dom_elements=["button:Submit", "input:email"],
        visual_elements=["button:Submit", "input:email"],
    )
    assert result.consensus is True
    assert result.confidence > 0.9

@pytest.mark.asyncio
async def test_judge_triangulate_disagreement():
    from src.browser.octopus_kernel import TheJudge
    judge = TheJudge()
    result = await judge.triangulate(
        a11y_elements=["button:Submit"],
        dom_elements=["button:Submit", "input:email"],
        visual_elements=["div:Ad", "button:Close"],
    )
    assert result.consensus is False
    assert result.confidence < 0.5

def test_forge_create_tool():
    from src.browser.octopus_kernel import TheForge
    from src.browser.site_log import SiteLogStore
    store = SiteLogStore(base_dir="/tmp/test_forge_logs")
    forge = TheForge(site_log_store=store)
    tool = forge.create_tool(
        domain="shopify.com",
        trigger="login page detected",
        steps=[
            {"action": "click", "selector": "#login-button"},
            {"action": "type", "selector": "#email", "value": "{email}"},
            {"action": "click", "selector": "#submit"},
        ],
    )
    assert tool.domain == "shopify.com"
    assert tool.trigger == "login page detected"
    assert len(tool.action_sequence) == 3
    assert tool.ttl_hours == 72

@pytest.mark.asyncio
async def test_kernel_execute_sightless():
    from src.browser.octopus_kernel import OctopusKernel
    kernel = OctopusKernel()
    result = await kernel.execute_mock(
        task="scrape the title from example.com",
        domain="example.com",
        action="read",
    )
    assert result.mode == "sightless"
    assert result.success is True
