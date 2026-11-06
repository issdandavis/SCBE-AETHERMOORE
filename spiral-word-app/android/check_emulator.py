"""Real emulator QA via ADB and the development WebView's Chrome protocol.

Uses a running emulator-5580, the installed development APK, and localhost:8799.
Coordinates are derived from the current UI tree. Only synthetic writing is used.
"""

import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import websocket

SERIAL = "emulator-5580"
PACKAGE = "io.aethermoor.spiralword"
OUT = Path(__file__).parent / "build" / "qa"


def adb(*args):
    return subprocess.check_output(["adb", "-s", SERIAL, *args], text=True, encoding="utf-8").strip()


class Page:
    def __init__(self):
        for _ in range(20):
            try:
                pid = adb("shell", "pidof", PACKAGE)
                break
            except subprocess.CalledProcessError:
                time.sleep(0.25)
        else:
            raise RuntimeError("App process did not start")
        adb("forward", "tcp:9227", "localabstract:webview_devtools_remote_" + pid)
        for _ in range(30):
            try:
                pages = json.loads(urllib.request.urlopen("http://127.0.0.1:9227/json", timeout=2).read())
                self.socket = websocket.create_connection(
                    pages[0]["webSocketDebuggerUrl"], timeout=8, suppress_origin=True
                )
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("WebView debugger did not become available")
        self.number = 0

    def evaluate(self, expression):
        self.number += 1
        self.socket.send(
            json.dumps(
                {
                    "id": self.number,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expression, "returnByValue": True},
                }
            )
        )
        while True:
            response = json.loads(self.socket.recv())
            if response.get("id") == self.number:
                if "error" in response or "exceptionDetails" in response.get("result", {}):
                    raise RuntimeError(str(response)[:600])
                return response["result"]["result"].get("value")

    def until(self, expression):
        for _ in range(40):
            if self.evaluate(expression):
                return
            time.sleep(0.25)
        raise AssertionError(expression)

    def click(self, selector):
        self.evaluate(f"document.querySelector({json.dumps(selector)}).click()")


def screenshot(name):
    with (OUT / name).open("wb") as f:
        subprocess.run(["adb", "-s", SERIAL, "exec-out", "screencap", "-p"], stdout=f, check=True)


def tap_text(text, attribute="text"):
    adb("shell", "uiautomator", "dump", "/sdcard/spiral-qa.xml")
    raw = adb("shell", "cat", "/sdcard/spiral-qa.xml")
    (OUT / "android-save-picker.xml").write_text(raw, encoding="utf-8")
    for node in ET.fromstring(raw).iter("node"):
        if node.get(attribute, "").casefold() == text.casefold() and node.get("enabled") == "true":
            x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
            adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
            return
    raise AssertionError("No enabled button in UI tree: " + text)


def main():
    OUT.mkdir(exist_ok=True)
    adb("reverse", "tcp:8799", "tcp:8799")
    adb("shell", "settings", "put", "system", "accelerometer_rotation", "0")
    adb("shell", "settings", "put", "system", "user_rotation", "0")
    page = Page()
    page.until("Boolean(window.SpiralWord)")
    page.click("#edit-tab")
    page.evaluate(
        "document.querySelector('#title').value='';document.querySelector('#title').scrollIntoView();document.querySelector('#title').focus()"
    )
    tap_text("title", "resource-id")
    adb("shell", "input", "text", "Android%sWriting%sTest")
    page.evaluate(
        "document.querySelector('#body').value='';document.querySelector('#body').scrollIntoView();document.querySelector('#body').focus()"
    )
    tap_text("body", "resource-id")
    adb("shell", "input", "text", "This%sis%sa%sphone%stest%sparagraph.%sIt%schecks%srotation%sand%sfile%ssaving.")
    body = page.evaluate("document.querySelector('#body').value")
    assert "phone test paragraph" in body
    page.click("#preview-tab")
    page.evaluate("window.scrollTo(0,0)")
    screenshot("android-portrait-filled.png")
    adb("shell", "settings", "put", "system", "user_rotation", "1")
    page.until("innerWidth > innerHeight")
    time.sleep(1)  # Let Android finish its compositor rotation animation.
    assert page.evaluate("document.querySelector('#body').value") == body
    screenshot("android-landscape.png")
    page.evaluate("document.querySelector('#api-url').value='http://127.0.0.1:8799/mla/api'")
    page.click("#native-connect")
    page.until("document.querySelector('#status').textContent.includes('Connected to the matching')")
    page.click("#native-validate")
    page.until("document.querySelector('#status').textContent.includes('Server checked 7 items; 0')")
    page.click("#export")
    time.sleep(1)
    tap_text("SAVE")
    page.until("document.querySelector('#status').textContent.includes('File saved.')")
    target = OUT / "ANDROID-EXPORTED-TEST.docx"
    adb("pull", "/sdcard/Download/Davis, Issac My MLA Template.docx", str(target))
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert b"phone test paragraph" in z.read("word/document.xml")
        assert b"PAGE" in z.read("word/header1.xml")
    page.socket.close()
    adb("shell", "am", "force-stop", PACKAGE)
    adb("shell", "am", "start", "-n", PACKAGE + "/.MainActivity")
    time.sleep(1)
    page = Page()
    page.until("Boolean(window.SpiralWord)")
    assert page.evaluate("document.querySelector('#body').value") == body
    result = {
        "passed": True,
        "device": SERIAL,
        "android": adb("shell", "getprop", "ro.build.version.release"),
        "flows": [
            "APK install/launch",
            "real ADB text input",
            "portrait",
            "landscape rotation",
            "draft retention on rotation",
            "native API profile and validation",
            "native document picker",
            "DOCX saved and pulled back",
            "draft retained after force-stop/relaunch",
        ],
        "userAgent": page.evaluate("navigator.userAgent"),
    }
    (OUT / "ANDROID_QA.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    page.socket.close()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
