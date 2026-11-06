"""Repeatable long-manuscript task rehearsal; isolated store, no model calls."""

import argparse
from contextlib import contextmanager
import hashlib
from io import BytesIO
import json
import os
import re
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "artifacts" / "writing_usability_20260923"


@contextmanager
def local_server(folder):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    with (folder / "server.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
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
            env=dict(os.environ, SPIRAL_WORD_HOME=str(folder / "store")),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Test server exited; inspect server.log")
                try:
                    urllib.request.urlopen(base + "/boards", timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Test server unavailable")
            yield base
        finally:
            proc.terminate()
            proc.wait(timeout=15)


def fixture(api, base):
    board = api.post(base + "/boards", data={"title": "The River Ledger — manuscript rehearsal"}).json()
    edits = []
    for index in range(24):
        if index:
            board = api.post(
                base + f"/boards/{board['id']}/sections", data={"title": f"Chapter {index+1:02d} — The crossing"}
            ).json()
        section = board["sections"][-1]
        # Varied sentinels establish order and completeness. Repeated prose is a
        # synthetic load fixture, not evidence about a model's writing quality.
        prose = [f"BEGIN-CHAPTER-{index+1:02d}", "# A painted sign, literally", "  A line indented by two spaces."]
        for paragraph in range(70):
            prose.append(
                f"At marker {index+1}-{paragraph+1}, Mira checked the river chart against Ren's account. "
                "The bridge remained closed until dawn. They noted each changed current, kept the lantern dry, "
                "and agreed to ask the ferryman before moving their camp."
            )
        prose.extend(["{{left:1}}", "{{right:1}}", f"END-CHAPTER-{index+1:02d}"])
        for lane, content in {
            "left": "The bridge is closed.\nThe lantern belongs to Mira.",
            "right": "We can wait until dawn.\nI have the river chart.",
            "center": "\n\n".join(prose),
        }.items():
            t = time.perf_counter()
            response = api.patch(
                base + f"/boards/{board['id']}/sections/{section['id']}/{lane}",
                data={
                    "expected_revision": 0,
                    "speaker": "Mira" if lane == "left" else "Ren" if lane == "right" else "Narrator",
                    "format": "prose" if lane == "center" else "dialogue",
                    "text": content,
                },
            )
            assert response.status == 200, response.text()
            edits.append((time.perf_counter() - t) * 1000)
            board = response.json()
    return board, edits


def run(label, tasks=False, shell=False):
    folder = OUT / f"{label}-{time.time_ns()}"
    folder.mkdir(parents=True)
    report = {"label": label, "kind": "automated task rehearsal, not a human study", "model_calls": 0}
    with local_server(folder) as base, sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=["--disable-gpu"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        context.route(
            "**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort()
        )
        board, edits = fixture(context.request, base)
        preview = context.request.get(base + f"/boards/{board['id']}/preview").json()
        expected = [s["text"] for s in preview["sections"]]
        report["sections"] = len(expected)
        report["rendered_words"] = sum(len(t.split()) for t in expected)
        report["save_ms"] = {"median": statistics.median(edits), "max": max(edits), "samples": len(edits)}
        if shell:
            result = subprocess.run(
                [
                    "pwsh",
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    r"C:\dev\loom\clay_shell\check_writing.ps1",
                    "-BaseUrl",
                    base,
                    "-BoardId",
                    board["id"],
                    "-OutputDirectory",
                    str(folder / "shell"),
                    "-Worker",
                    str(HERE / "check_writing_tools.py"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            (folder / "shell-run.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
            assert result.returncode == 0, str(folder / "shell-run.log")
            report["shell"] = json.loads((folder / "shell" / "SHELL_REPORT.json").read_text(encoding="utf-8-sig"))
        (folder / "source-board.json").write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
        t = time.perf_counter()
        exported = context.request.get(base + f"/boards/{board['id']}/export.docx")
        report["export_ms"] = (time.perf_counter() - t) * 1000
        assert exported.status == 200
        (folder / "manuscript.docx").write_bytes(exported.body())
        with ZipFile(BytesIO(exported.body())) as doc:
            xml = ET.fromstring(doc.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            text = "\n".join(node.text or "" for node in xml.findall(".//w:t", ns))
            report["all_chapter_sentinels_exported"] = all(text.count(f"END-CHAPTER-{i+1:02d}") == 1 for i in range(24))
            report["literal_hash_line_preserved"] = "# A painted sign, literally" in text
            report["indentation_preserved"] = "  A line indented by two spaces." in text
            report["word_outline_headings"] = len(xml.findall(".//w:pStyle[@w:val='Heading1']", ns))
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        t = time.perf_counter()
        page.goto(base + "/board")
        expect(page.locator("#save")).to_be_enabled()
        expect(page.locator("#center-text")).to_have_value(re.compile("BEGIN-CHAPTER-01"))
        report["open_ms"] = (time.perf_counter() - t) * 1000
        report["desktop_no_horizontal_overflow"] = page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("#sections button").last.click()
        expect(page.locator("#center-text")).to_have_value(re.compile("END-CHAPTER-24"))
        page.reload()
        expect(page.locator("#save")).to_be_enabled()
        report["last_section_restored"] = "END-CHAPTER-24" in page.locator("#center-text").input_value()
        page.locator("#center-text").fill("UNSAVED-RECOVERY-EXERCISE")
        page.close()  # abrupt close skips beforeunload, like losing the tab/process
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base + "/board")
        expect(page.locator("#save")).to_be_enabled()
        report["unsaved_draft_recovered"] = page.locator("#center-text").input_value() == "UNSAVED-RECOVERY-EXERCISE"
        report["has_section_search"] = page.locator("#section-search").count() > 0
        report["has_revision_browser"] = page.locator("#history-button").count() > 0
        report["has_outline_controls"] = page.locator("#rename-section").count() > 0
        if tasks:
            # Recover the saved chapter through the actual revision controls.
            page.click("#history-button")
            page.select_option("#history-lane", "center")
            expect(page.locator("#history-text")).to_have_value(re.compile("END-CHAPTER-24"))
            expect(page.locator("#use-revision")).to_be_enabled()
            page.once("dialog", lambda d: d.accept())
            page.click("#use-revision")
            expect(page.locator("#center-text")).to_have_value(re.compile("END-CHAPTER-24"))
            page.click("#save")
            expect(page.locator("#status")).to_have_text("All changes saved on this computer.")
            page.once("dialog", lambda d: d.accept("Lantern return"))
            page.click("#rename-section")
            expect(page.locator("#sections button.active")).to_have_text("Lantern return")
            page.click("#earlier-section")
            expect(page.locator("#save")).to_be_enabled()
            saved = context.request.get(base + f"/boards/{board['id']}").json()
            assert saved["sections"][-2]["title"] == "Lantern return"
            assert saved["sections"][-2]["lanes"] == board["sections"][-1]["lanes"] | {
                "center": dict(board["sections"][-1]["lanes"]["center"], revision=2)
            }
            page.locator("#section-search").fill("BEGIN-CHAPTER-19")
            expect(page.locator("#sections button:visible")).to_have_count(1)
            page.locator("#sections button:visible").click()
            expect(page.locator("#center-text")).to_have_value(re.compile("END-CHAPTER-19"))
            page.locator("#section-search").fill("")
            original = page.locator("#center-text").input_value()
            page.locator("#center-text").fill(original + "\nA revision for the exercise.")
            page.click("#save")
            expect(page.locator("#status")).to_have_text("All changes saved on this computer.")
            page.click("#history-button")
            expect(page.locator("#history-text")).to_have_value(re.compile("A revision for the exercise."))
            page.select_option("#history-revision", "1")
            page.click("#use-revision")
            expect(page.locator("#center-text")).to_have_value(original)
            page.click("#save")
            expect(page.locator("#status")).to_have_text("All changes saved on this computer.")
            saved = context.request.get(base + f"/boards/{board['id']}").json()
            section19 = next(s for s in saved["sections"] if s["id"] == board["sections"][18]["id"])
            assert section19["lanes"]["center"]["revision"] == 3
            assert section19["lanes"]["center"]["text"] == original
            report["task_checks"] = dict(
                recover_saved_version=True,
                rename_section=True,
                reorder_preserves_lanes=True,
                find_chapter_by_content=True,
                restore_old_revision_as_new=True,
            )
            page.screenshot(path=str(folder / "desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        report["mobile_no_horizontal_overflow"] = page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(folder / "mobile.png"), full_page=True)
        report["page_errors"] = errors
        report["board_sha256"] = hashlib.sha256((folder / "source-board.json").read_bytes()).hexdigest()
        browser.close()
    (folder / "REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(folder / "REPORT.json"), **report}))
    return folder


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--tasks", action="store_true")
    parser.add_argument("--shell", action="store_true")
    args = parser.parse_args()
    run(args.label, args.tasks, args.shell)
