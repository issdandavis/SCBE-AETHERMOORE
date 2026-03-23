from __future__ import annotations

from scripts.system import colab_notebook_smoke as smoke


class _FakeButton:
    def __init__(self, *, text: str = "", aria_label: str | None = None) -> None:
        self._text = text
        self._aria_label = aria_label
        self.clicked = False

    def inner_text(self, timeout: int = 0) -> str:
        return self._text

    def get_attribute(self, name: str, timeout: int = 0) -> str | None:
        if name == "aria-label":
            return self._aria_label
        return None

    def click(self, timeout: int = 0) -> None:
        self.clicked = True


class _FakeLocator:
    def __init__(self, buttons: list[_FakeButton]) -> None:
        self._buttons = buttons

    def count(self) -> int:
        return len(self._buttons)

    def nth(self, index: int) -> _FakeButton:
        return self._buttons[index]


class _FakeConnectPage:
    def __init__(self, buttons: list[_FakeButton]) -> None:
        self._locator = _FakeLocator(buttons)

    def get_by_role(self, role: str, name=None) -> _FakeLocator:
        assert role == "button"
        return self._locator


def test_maybe_click_connect_uses_aria_label_when_button_text_is_empty() -> None:
    target = _FakeButton(text="", aria_label="Connect")
    page = _FakeConnectPage([target])

    result = smoke._maybe_click_connect(page)

    assert result["attempted"] is True
    assert result["clicked"] is True
    assert result["label"] == "Connect"
    assert target.clicked is True


class _FakeScratchPage:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = list(responses)
        self.waits: list[int] = []

    def evaluate(self, script: str, arg=None):
        assert self._responses, f"no fake response left for script: {script[:40]}"
        return self._responses.pop(0)

    def wait_for_timeout(self, delay: int) -> None:
        self.waits.append(delay)


def test_run_scratch_cell_reports_success_when_marker_appears() -> None:
    page = _FakeScratchPage(
        [
            {"ok": True},
            {"ok": True, "method": "colab_api", "index": 20},
            {"ok": True, "method": "runButton.click"},
            {"ok": True, "output_count": 1, "joined_text": "SCBE_COLAB_SMOKE_OK", "busy": False, "execution_count": 1},
        ]
    )

    result = smoke._run_scratch_cell(page, smoke_code="print('SCBE_COLAB_SMOKE_OK')", wait_ms=5000)

    assert result["attempted"] is True
    assert result["success"] is True
    assert result["run_result"]["method"] == "runButton.click"
    assert page.waits == [1200, 400, 1000]


def test_runtime_attached_uses_kernel_state_and_connection_timestamp() -> None:
    assert smoke._runtime_attached({"usage_visible": True, "kernel_state": "connect"}) is True
    assert smoke._runtime_attached({"usage_visible": False, "kernel_state": "connected"}) is True
    assert smoke._runtime_attached({"usage_visible": False, "kernel_state": "connect", "kernel_last_connected_time_ms": 1}) is True
    assert smoke._runtime_attached({"usage_visible": False, "kernel_state": "connect", "kernel_last_connected_time_ms": -1}) is False
