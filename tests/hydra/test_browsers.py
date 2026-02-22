"""
Tests for HYDRA Browser Backends -- AI-Independent.
=====================================================

Covers:
- BrowserBackend ABC (cannot instantiate directly)
- PlaywrightBackend: constructor defaults, ImportError on missing lib
- SeleniumBackend: constructor defaults, ImportError on missing lib
- CDPBackend: constructor defaults, ImportError on missing lib
- Interface compliance (all concrete classes declare required methods)
"""

import asyncio
import inspect
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.browsers import (
    BrowserBackend,
    PlaywrightBackend,
    SeleniumBackend,
    CDPBackend,
)


# =========================================================================
# Abstract base class
# =========================================================================


class TestBrowserBackendABC:
    """BrowserBackend is abstract and cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BrowserBackend()

    def test_required_abstract_methods(self):
        expected = {
            "initialize", "navigate", "click", "type_text",
            "screenshot", "scroll", "get_page_content", "close",
        }
        abstract = set()
        for name in expected:
            method = getattr(BrowserBackend, name, None)
            if method and getattr(method, "__isabstractmethod__", False):
                abstract.add(name)
        assert abstract == expected


# =========================================================================
# PlaywrightBackend
# =========================================================================


class TestPlaywrightBackend:
    """PlaywrightBackend construction and interface compliance."""

    def test_constructor_defaults(self):
        backend = PlaywrightBackend()
        assert backend._headless is True
        assert backend._browser_type == "chromium"
        assert backend._browser is None
        assert backend._page is None

    def test_constructor_custom_args(self):
        backend = PlaywrightBackend(headless=False, browser_type="firefox")
        assert backend._headless is False
        assert backend._browser_type == "firefox"

    def test_is_browser_backend_subclass(self):
        assert issubclass(PlaywrightBackend, BrowserBackend)

    def test_implements_all_abstract_methods(self):
        """All abstract methods from BrowserBackend are implemented."""
        required = {
            "initialize", "navigate", "click", "type_text",
            "screenshot", "scroll", "get_page_content", "close",
        }
        for method_name in required:
            method = getattr(PlaywrightBackend, method_name, None)
            assert method is not None, f"Missing method: {method_name}"
            assert not getattr(method, "__isabstractmethod__", False), (
                f"{method_name} is still abstract"
            )

    def test_all_methods_are_async(self):
        """All interface methods should be coroutines."""
        for name in ["initialize", "navigate", "click", "type_text",
                      "screenshot", "scroll", "get_page_content", "close"]:
            method = getattr(PlaywrightBackend, name)
            assert asyncio.iscoroutinefunction(method), f"{name} should be async"


# =========================================================================
# SeleniumBackend
# =========================================================================


class TestSeleniumBackend:
    """SeleniumBackend construction and interface compliance."""

    def test_constructor_defaults(self):
        backend = SeleniumBackend()
        assert backend._headless is True
        assert backend._driver is None

    def test_constructor_not_headless(self):
        backend = SeleniumBackend(headless=False)
        assert backend._headless is False

    def test_is_browser_backend_subclass(self):
        assert issubclass(SeleniumBackend, BrowserBackend)

    def test_implements_all_abstract_methods(self):
        required = {
            "initialize", "navigate", "click", "type_text",
            "screenshot", "scroll", "get_page_content", "close",
        }
        for method_name in required:
            method = getattr(SeleniumBackend, method_name, None)
            assert method is not None, f"Missing method: {method_name}"
            assert not getattr(method, "__isabstractmethod__", False)

    def test_all_methods_are_async(self):
        for name in ["initialize", "navigate", "click", "type_text",
                      "screenshot", "scroll", "get_page_content", "close"]:
            method = getattr(SeleniumBackend, name)
            assert asyncio.iscoroutinefunction(method), f"{name} should be async"


# =========================================================================
# CDPBackend
# =========================================================================


class TestCDPBackend:
    """CDPBackend construction and interface compliance."""

    def test_constructor_defaults(self):
        backend = CDPBackend()
        assert backend._cdp_url == "http://localhost:9222"
        assert backend._ws is None
        assert backend._msg_id == 0

    def test_constructor_custom_url(self):
        backend = CDPBackend(cdp_url="http://remote:9333")
        assert backend._cdp_url == "http://remote:9333"

    def test_is_browser_backend_subclass(self):
        assert issubclass(CDPBackend, BrowserBackend)

    def test_implements_all_abstract_methods(self):
        required = {
            "initialize", "navigate", "click", "type_text",
            "screenshot", "scroll", "get_page_content", "close",
        }
        for method_name in required:
            method = getattr(CDPBackend, method_name, None)
            assert method is not None, f"Missing method: {method_name}"
            assert not getattr(method, "__isabstractmethod__", False)

    def test_all_methods_are_async(self):
        for name in ["initialize", "navigate", "click", "type_text",
                      "screenshot", "scroll", "get_page_content", "close"]:
            method = getattr(CDPBackend, name)
            assert asyncio.iscoroutinefunction(method), f"{name} should be async"


# =========================================================================
# Cross-backend consistency
# =========================================================================


class TestBackendConsistency:
    """All backends share the same public interface."""

    BACKENDS = [PlaywrightBackend, SeleniumBackend, CDPBackend]
    INTERFACE = [
        "initialize", "navigate", "click", "type_text",
        "screenshot", "scroll", "get_page_content", "close",
    ]

    def test_all_backends_have_same_methods(self):
        for cls in self.BACKENDS:
            for method_name in self.INTERFACE:
                assert hasattr(cls, method_name), (
                    f"{cls.__name__} missing {method_name}"
                )

    def test_navigate_takes_url_param(self):
        """navigate(self, url) signature across all backends."""
        for cls in self.BACKENDS:
            sig = inspect.signature(cls.navigate)
            params = list(sig.parameters.keys())
            assert "url" in params, f"{cls.__name__}.navigate missing 'url' param"

    def test_click_takes_selector_param(self):
        for cls in self.BACKENDS:
            sig = inspect.signature(cls.click)
            params = list(sig.parameters.keys())
            assert "selector" in params, f"{cls.__name__}.click missing 'selector'"

    def test_type_text_takes_selector_and_text(self):
        for cls in self.BACKENDS:
            sig = inspect.signature(cls.type_text)
            params = list(sig.parameters.keys())
            assert "selector" in params
            assert "text" in params
