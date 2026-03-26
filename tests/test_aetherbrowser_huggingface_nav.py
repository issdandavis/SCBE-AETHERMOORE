from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.system.aetherbrowser_huggingface_nav as hf_nav


def test_api_fallback_normalizes_and_limits(monkeypatch) -> None:
    def fake_fetch_json(url: str):
        assert "https://huggingface.co/api/models" in url
        return [
            {
                "id": "openai/clip-vit-base-patch32",
                "description": "Contrastive vision-language model",
                "likes": 42,
                "downloads": 9001,
            },
            {
                "id": "google/vit-base-patch16-224",
                "pipeline_tag": "image-classification",
            },
        ]

    monkeypatch.setattr(hf_nav, "_fetch_json", fake_fetch_json)

    results = hf_nav.nav_huggingface_api_fallback(
        "vision transformer",
        max_results=1,
        search_type="models",
    )

    assert results == [
        {
            "title": "openai/clip-vit-base-patch32",
            "description": "Contrastive vision-language model",
            "link": "https://huggingface.co/openai/clip-vit-base-patch32",
            "type": "models",
            "source": "api",
            "likes": 42,
            "downloads": 9001,
        }
    ]


def test_playwright_path_exports_to_vault(monkeypatch, tmp_path: Path) -> None:
    class FakePage:
        def __init__(self) -> None:
            self.visited = []

        def goto(self, url: str, timeout: int = 0) -> None:
            self.visited.append((url, timeout))

        def wait_for_load_state(self, state: str, timeout: int = 0) -> None:
            return None

    class FakeBrowser:
        def __init__(self, page: FakePage) -> None:
            self._page = page
            self.closed = False

        def new_page(self) -> FakePage:
            return self._page

        def close(self) -> None:
            self.closed = True

    class FakeChromium:
        def __init__(self, page: FakePage) -> None:
            self._page = page

        def launch(self, headless: bool = True) -> FakeBrowser:
            assert headless is True
            return FakeBrowser(self._page)

    class FakePlaywright:
        def __init__(self, page: FakePage) -> None:
            self.chromium = FakeChromium(page)

    class FakeContext:
        def __init__(self, page: FakePage) -> None:
            self._page = page

        def __enter__(self) -> FakePlaywright:
            return FakePlaywright(self._page)

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    fake_page = FakePage()
    monkeypatch.setattr(hf_nav, "_load_sync_playwright", lambda: (lambda: FakeContext(fake_page)))
    monkeypatch.setattr(
        hf_nav,
        "_extract_browser_results",
        lambda page, surface_type, max_results: [
            {
                "title": "openai/whisper-large-v3",
                "description": "Speech recognition model card",
                "link": "https://huggingface.co/openai/whisper-large-v3",
                "type": surface_type,
                "source": "playwright",
            }
        ],
    )

    results = hf_nav.nav_huggingface_playwright(
        "speech recognition",
        max_results=3,
        search_type="models",
        save_to_vault=str(tmp_path),
    )

    assert len(results) == 1
    assert results[0]["source"] == "playwright"
    assert fake_page.visited == [("https://huggingface.co/models?search=speech+recognition", 20000)]

    note_path = tmp_path / "huggingface_speech_recognition_models.md"
    assert note_path.exists()
    note_text = note_path.read_text(encoding="utf-8")
    assert "openai/whisper-large-v3" in note_text
    assert "Speech recognition model card" in note_text


def test_playwright_missing_falls_back_to_api(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_fallback(query: str, max_results: int, search_type: str, save_to_vault: str | None):
        captured["args"] = (query, max_results, search_type, save_to_vault)
        return [{"title": "fallback-result", "link": "https://huggingface.co/spaces/org/demo"}]

    monkeypatch.setattr(hf_nav, "_load_sync_playwright", lambda: None)
    monkeypatch.setattr(hf_nav, "nav_huggingface_api_fallback", fake_fallback)

    results = hf_nav.nav_huggingface_playwright(
        "demo space",
        max_results=2,
        search_type="spaces",
        save_to_vault=str(tmp_path),
    )

    assert results == [{"title": "fallback-result", "link": "https://huggingface.co/spaces/org/demo"}]
    assert captured["args"] == ("demo space", 2, "spaces", str(tmp_path))


def test_main_json_output_uses_no_browser(monkeypatch, capsys) -> None:
    expected = [
        {
            "title": "HuggingFaceH4/zephyr-7b-beta",
            "description": "Instruction-tuned chat model",
            "link": "https://huggingface.co/HuggingFaceH4/zephyr-7b-beta",
            "type": "models",
            "source": "api",
        }
    ]
    monkeypatch.setattr(hf_nav, "nav_huggingface_api_fallback", lambda *args, **kwargs: expected)

    exit_code = hf_nav.main(["zephyr", "--json", "--no-browser"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
