from __future__ import annotations

from typing import Any

from scripts.system.shopify_toggle_password_gate import detect_storefront_gate


class _Locator:
    def __init__(self, *, matches: bool, checked: bool = False) -> None:
        self._matches = matches
        self._checked = checked
        self.first = self

    def count(self) -> int:
        return int(self._matches)

    def is_checked(self) -> bool:
        return self._checked


class _Page:
    def __init__(self, matching_selector: str | None, checked: bool = False) -> None:
        self.matching_selector = matching_selector
        self.checked = checked

    def locator(self, selector: str) -> Any:
        return _Locator(matches=selector == self.matching_selector, checked=self.checked)


def test_detect_storefront_gate_returns_locator_and_boolean_only() -> None:
    selector = "label:has-text('Password protection') input[type='checkbox']"
    page = _Page(selector, checked=True)

    checkbox, enabled = detect_storefront_gate(page)

    assert checkbox is not None
    assert enabled is True


def test_detect_storefront_gate_reports_no_match() -> None:
    checkbox, enabled = detect_storefront_gate(_Page(None))

    assert checkbox is None
    assert enabled is False
