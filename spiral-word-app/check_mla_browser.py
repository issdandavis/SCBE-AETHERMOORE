"""Isolated browser QA. Native emulator testing is recorded separately."""

import json
from pathlib import Path
from zipfile import ZipFile
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).parent / "android" / "build" / "qa"
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel="msedge")
    context = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8799/mla/")
    expect(page.locator("#firstName")).to_have_value("Issac")
    page.locator("#title").fill("A Page for My Thoughts")
    body = "This is a software test paragraph, not an assignment submission. Rain & wind move past the window.\nA second paragraph checks automatic indentation."
    page.locator("#body").fill(body)
    page.locator("#works").fill("Example author. Example work.")
    page.locator("#template-name").fill("English 101 test")
    page.locator("#save-template").click()
    assert "Template saved" in page.locator("#status").inner_text()
    page.locator("#preview-tab").click()
    page.screenshot(path=str(OUT / "browser-portrait.png"), full_page=True)
    with page.expect_download() as waiting:
        page.locator("#export").click()
    download = waiting.value
    assert download.suggested_filename == "Davis, Issac My MLA Template.docx"
    sample = OUT / "TEST-ONLY-MLA.docx"
    download.save_as(sample)
    with ZipFile(sample) as z:
        assert z.testzip() is None
        assert b"PAGE" in z.read("word/header1.xml")
        assert b"&amp;" in z.read("word/document.xml")
    page.set_viewport_size({"width": 844, "height": 390})
    assert page.locator("#body").input_value() == body
    page.screenshot(path=str(OUT / "browser-landscape.png"), full_page=True)
    page.reload()
    expect(page.locator("#body")).to_have_value(body)
    assert page.locator("#body").input_value() == body
    page.on("dialog", lambda dialog: dialog.accept("1") if dialog.type == "prompt" else dialog.accept())
    page.locator("#load-template").click()
    assert page.locator("#body").input_value() == ""
    assert page.locator("#course").input_value() == "English 101"
    page.locator("#restore-draft").click()
    assert page.locator("#body").input_value() == body
    plugin = {
        "schema": "spiralword.rules.v1",
        "name": "Test length",
        "rules": [{"field": "body", "op": "minWords", "value": 100, "label": "100 words"}],
    }
    page.locator("details summary").click()
    page.locator("#import-plugin").set_input_files(
        {"name": "test-rules.json", "mimeType": "application/json", "buffer": json.dumps(plugin).encode()}
    )
    expect(page.locator("#plugin-label")).to_contain_text("Test length")
    assert page.locator("#checks .todo").count() == 1
    page.locator("#remove-plugin").click()
    page.locator("#api-check").click()
    expect(page.locator("#status")).to_contain_text("API is available")
    assert not errors, errors
    (OUT / "BROWSER_QA.json").write_text(
        json.dumps(
            {
                "passed": True,
                "viewport_sizes": [[390, 844], [844, 390]],
                "flows": [
                    "typing",
                    "live preview",
                    "DOCX download",
                    "responsive layout",
                    "reload persistence",
                    "template save/open",
                    "draft recovery",
                    "plugin checks",
                    "local API",
                ],
                "page_errors": errors,
                "native_emulator": False,
            },
            indent=2,
        )
    )
    browser.close()
print(OUT / "BROWSER_QA.json")
