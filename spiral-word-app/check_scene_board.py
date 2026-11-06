"""Rendered local workflow, using an isolated store and no live AI provider calls."""

import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import time
import urllib.request
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "artifacts" / "scene_board_20260923"
OUT.mkdir(parents=True, exist_ok=True)
DATA = OUT / ("test-store-" + str(time.time_ns()))
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
BASE = f"http://127.0.0.1:{port}"
errors = []
with (OUT / "server.log").open("w", encoding="utf-8") as log:
    server = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "uvicorn",
            "app:app",
            "--app-dir",
            str(HERE),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        stdout=log,
        stderr=log,
        env=dict(os.environ, SPIRAL_WORD_HOME=str(DATA)),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("Isolated test server exited")
            try:
                urllib.request.urlopen(BASE + "/boards", timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Local test server did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                args=["--disable-gpu"],
            )
            context = browser.new_context(viewport={"width": 1536, "height": 1000}, accept_downloads=True)
            context.route(
                "**/*", lambda route: route.continue_() if route.request.url.startswith(BASE + "/") else route.abort()
            )
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(BASE + "/board")
            expect(page.locator("#left-text")).to_have_value("You came back.\nI kept the light burning.")
            expect(page.locator("#save")).to_be_enabled()
            expect(page.locator("#provider option")).to_have_count(5)
            page.screenshot(path=str(OUT / "desktop.png"), full_page=True)
            page.locator("#left-text").fill("I brought a map.\n<script>window.bad = true</script>")
            page.locator("#center-text").fill("A scene in the rain.\n{{left:1}}\n{{left:2}}\n{{right:2}}")
            page.click("#save")
            expect(page.locator("#status")).to_have_text("All changes saved on this computer.")
            page.click("#preview-button")
            expect(page.locator("#preview")).to_contain_text("Mira: I brought a map.")
            expect(page.locator("#preview")).to_contain_text("<script>window.bad = true</script>")
            assert page.evaluate("window.bad === undefined")
            page.reload()
            expect(page.locator("#left-text")).to_have_value("I brought a map.\n<script>window.bad = true</script>")
            expect(page.locator("#save")).to_be_enabled()
            page.once("dialog", lambda dialog: dialog.accept("Crossing the river"))
            page.click("#new-section")
            expect(page.locator("#sections button")).to_have_count(2)
            expect(page.locator("#center-text")).to_have_value("")
            page.locator("#center-text").fill("They waited beside the river.")
            page.click("#save")
            expect(page.locator("#status")).to_have_text("All changes saved on this computer.")
            # A browser stub verifies proposal acceptance and stale-source rejection.
            # It never reaches the configured live provider.
            calls = []

            def draft_stub(route):
                body = route.request.post_data_json
                calls.append(body)
                route.fulfill(
                    json={
                        "text": "They crossed when the water fell.",
                        "provider": "ui-test-stub",
                        "diagnostic": False,
                        "expected_context": body["expected_context"],
                        "source_sha256": "test-fixture",
                        "applied": False,
                    }
                )

            page.route("**/draft", draft_stub)
            page.select_option("#provider", "openai")
            page.click("#draft")
            expect(page.locator("#proposal-box")).to_be_visible()
            bid = page.locator("#documents").input_value()
            document = context.request.get(BASE + "/boards/" + bid).json()
            sec = document["sections"][-1]
            right = sec["lanes"]["right"]
            changed = context.request.patch(
                BASE + f"/boards/{bid}/sections/{sec['id']}/right",
                data={
                    "expected_revision": right["revision"],
                    "speaker": right["speaker"],
                    "format": right["format"],
                    "text": "A new fact.",
                },
            )
            assert changed.status == 200
            page.click("#apply")
            expect(page.locator("#status")).to_contain_text("Source lanes changed")
            expect(page.locator("#center-text")).to_have_value("They waited beside the river.")
            page.reload()
            expect(page.locator("#sections button")).to_have_count(2)
            expect(page.locator("#save")).to_be_enabled()
            page.get_by_role("button", name="Crossing the river", exact=True).click()
            expect(page.locator("#right-text")).to_have_value("A new fact.")
            page.select_option("#provider", "openai")
            page.click("#draft")
            expect(page.locator("#proposal-box")).to_be_visible()
            page.click("#apply")
            expect(page.locator("#center-text")).to_have_value("They crossed when the water fell.")
            expect(page.locator("#right-text")).to_have_value("A new fact.")
            with page.expect_download() as info:
                page.click("#export")
            info.value.save_as(OUT / "scene-board.docx")
            with ZipFile(OUT / "scene-board.docx") as document:
                xml = document.read("word/document.xml")
                assert b"Crossing the river" in xml and b"They crossed when the water fell." in xml
            # Saving one dirty lane must not refresh the expected revision of a
            # second dirty lane whose unseen text changed in another client.
            page.locator("#left-text").fill("My new left line.")
            page.locator("#right-text").fill("My unsaved right line.")
            document = context.request.get(BASE + "/boards/" + bid).json()
            sec = document["sections"][-1]
            right = sec["lanes"]["right"]
            changed = context.request.patch(
                BASE + f"/boards/{bid}/sections/{sec['id']}/right",
                data={
                    "expected_revision": right["revision"],
                    "speaker": right["speaker"],
                    "format": right["format"],
                    "text": "Another writer updated this line.",
                },
            )
            assert changed.status == 200
            page.click("#save")
            expect(page.locator("#status")).to_contain_text("This lane changed")
            expect(page.locator("#right-text")).to_have_value("My unsaved right line.")
            final = context.request.get(BASE + "/boards/" + bid).json()["sections"][-1]["lanes"]
            assert final["left"]["text"] == "My new left line."
            assert final["right"]["text"] == "Another writer updated this line."
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
            assert not errors, errors
            assert len(calls) == 2
            receipt = dict(
                passed=True,
                desktop=True,
                mobile=True,
                separate_panels=True,
                sections=True,
                saves_survive_reload=True,
                literal_markup_safe=True,
                stale_ai_rejected=True,
                approved_proposal_applied=True,
                source_lanes_preserved=True,
                two_dirty_lanes_preserve_remote_changes=True,
                real_docx_export=True,
                ai_provider_calls="Two browser stubs; zero paid/model calls",
                page_errors=errors,
                storage=str(DATA),
            )
            (OUT / "UI_RECEIPT.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            print(json.dumps(receipt))
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=15)
