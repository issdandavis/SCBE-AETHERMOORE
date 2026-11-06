from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient
from scene_board import BoardStore, Conflict, render
import scene_board_api as api
from app import app
from export import docx_sections


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = BoardStore(Path(self.temp.name) / "boards.sqlite3")
        self.board = self.store.create("A story")
        self.bid, self.sid = self.board["id"], self.board["sections"][0]["id"]

    def edit(self, lane, text, revision=0, **kwargs):
        return self.store.update(self.bid, self.sid, lane, revision, text, lane.title(), "prose", **kwargs)

    def test_lanes_persist_and_render_without_changing_sources(self):
        self.edit("left", "First line\nSecond line")
        self.edit("right", "<script>alert(1)</script>")
        self.edit("center", "Begin.\n{{left:2}}\n{{right}}")
        reopened = BoardStore(self.store.file).get(self.bid)["sections"][0]
        compiled = render(reopened)
        self.assertEqual(compiled["text"], "Begin.\nSecond line\n<script>alert(1)</script>")
        self.assertEqual(reopened["lanes"]["left"]["text"], "First line\nSecond line")
        self.assertEqual(compiled["sources"]["left"]["revision"], 1)
        self.assertEqual(len(self.store.history(self.bid, self.sid, "left")), 2)

    def test_distinct_lanes_can_commit_concurrently(self):
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda lane: self.edit(lane, lane), ["left", "right"]))
        final = self.store.get(self.bid)["sections"][0]["lanes"]
        self.assertEqual(final["left"]["text"], "left")
        self.assertEqual(final["right"]["text"], "right")
        self.assertEqual(len(results), 2)

    def test_same_lane_conflict_and_stale_ai_context(self):
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.edit, "left", str(n)) for n in range(2)]
        self.assertEqual(sum(isinstance(f.exception(), Conflict) for f in futures), 1)
        with self.assertRaises(Conflict):
            self.edit("center", "stale generated scene", expected_context={"left": 0, "center": 0, "right": 0})
        self.assertEqual(self.store.get(self.bid)["sections"][0]["lanes"]["center"]["text"], "")

    def test_source_references_are_one_pass_and_validated(self):
        self.edit("left", "{{right:1}}")
        self.edit("center", "{{left:1}}")
        self.assertEqual(render(self.store.get(self.bid)["sections"][0])["text"], "{{right:1}}")
        self.edit("center", "{{left:99}}", 1)
        with self.assertRaises(ValueError):
            render(self.store.get(self.bid)["sections"][0])
        with self.assertRaises(ValueError):
            self.edit("right", "x" * 65537)
        self.edit("right", "x" * 65536)
        self.edit("center", "{{right}}" * 5, 2)
        with self.assertRaisesRegex(ValueError, "Combined section is too long"):
            render(self.store.get(self.bid)["sections"][0])

    def test_api_conflicts_draft_is_separate_and_docx_is_real(self):
        with patch.object(api, "_store", self.store), TestClient(app, base_url="http://127.0.0.1:8768") as client:
            root = f"/boards/{self.bid}/sections/{self.sid}"
            payload = {"expected_revision": 0, "text": "A saved scene.", "speaker": "Narrator", "format": "prose"}
            self.assertEqual(client.patch(root + "/center", json=payload).status_code, 200)
            self.assertEqual(client.patch(root + "/center", json=payload).status_code, 409)
            revision = {"left": 0, "right": 0, "center": 1}
            with patch.object(api.ai_ports, "call", return_value="Proposed scene.") as call:
                response = client.post(root + "/draft", json={"provider": "echo", "expected_context": revision})
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()["applied"])
                self.assertTrue(response.json()["diagnostic"])
                call.assert_called_once()
            self.assertEqual(self.store.get(self.bid)["sections"][0]["lanes"]["center"]["text"], "A saved scene.")
            exported = client.get(f"/boards/{self.bid}/export.docx")
            self.assertEqual(exported.status_code, 200)
            with ZipFile(BytesIO(exported.content)) as doc:
                self.assertIn(b"A saved scene.", doc.read("word/document.xml"))
            with patch.object(api.ai_ports, "call", return_value="[ERROR] secret upstream detail"):
                failed = client.post(root + "/draft", json={"provider": "echo", "expected_context": revision})
                self.assertEqual(failed.status_code, 502)
                self.assertNotIn("secret", failed.text)

    def test_api_origin_limits_unknown_boards_and_governance(self):
        with patch.object(api, "_store", self.store), TestClient(app, base_url="http://127.0.0.1:8768") as client:
            self.assertEqual(
                client.post(
                    "/boards", json={"title": "bad"}, headers={"Origin": "https://unrelated.example"}
                ).status_code,
                403,
            )
            self.assertEqual(client.get("/boards/missing").status_code, 404)
            self.assertEqual(client.post("/boards", json={"title": "ok", "extra": "no"}).status_code, 422)
            with patch.object(api, "check_governance", return_value=(False, "blocked")):
                self.assertEqual(client.post("/boards", json={"title": "no"}).status_code, 403)
            self.assertEqual(client.get("/board").status_code, 200)
            self.assertEqual(client.get("/board/assets/not-a-file").status_code, 422)

    def test_outline_changes_preserve_content_and_reject_stale_or_missing_sections(self):
        self.edit("center", "My chapter stays attached to its ID")
        board = self.store.add_section(self.bid, "Second scene")
        ordered = [{"id": s["id"], "title": s["title"]} for s in reversed(board["sections"])]
        ordered[1]["title"] = "New title for the first scene"
        changed = self.store.outline(self.bid, board["revision"], "New manuscript title", ordered)
        self.assertEqual(changed["sections"][1]["lanes"]["center"]["text"], "My chapter stays attached to its ID")
        self.assertEqual(changed["sections"][1]["id"], self.sid)
        with self.assertRaises(Conflict):
            self.store.outline(self.bid, board["revision"], "stale", ordered)
        with self.assertRaises(ValueError):
            self.store.outline(self.bid, changed["revision"], "missing", ordered[:1])
        self.assertEqual(self.store.get(self.bid), changed)
        with patch.object(api, "_store", self.store), TestClient(app, base_url="http://localhost") as client:
            response = client.patch(
                f"/boards/{self.bid}/outline",
                json={"expected_revision": changed["revision"], "title": "Final", "sections": ordered},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["title"], "Final")

    def test_structured_word_export_keeps_literal_text_and_heading_styles(self):
        text = "# not a heading\n  indentation\n\n中文 — &lt; <literal>\ncontrol:\x01"
        with ZipFile(BytesIO(docx_sections("Book", [("Chapter", text)]))) as doc:
            xml = ET.fromstring(doc.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            values = [node.text or "" for node in xml.findall(".//w:t", ns)]
            self.assertEqual(
                values, ["Book", "Chapter", "# not a heading", "  indentation", "", "中文 — &lt; <literal>", "control:"]
            )
            self.assertEqual(len(xml.findall(".//w:pStyle[@w:val='Heading1']", ns)), 1)
            self.assertIn("word/styles.xml", doc.namelist())

    def test_writing_use_cases_keep_sources_separate_and_update_references(self):
        cases = [
            (
                "fiction",
                "dialogue",
                "The bridge is closed.",
                "dialogue",
                "We will wait.",
                "Rain fell.\n{{left}}\n{{right}}",
                "Rain fell.\nMira: The bridge is closed.\nRen: We will wait.",
            ),
            (
                "technical guide",
                "markdown",
                "def area(r):\n    return 3.14 * r * r",
                "notes",
                "Reject negative radii.",
                "Implementation\n{{left}}\nConstraints\n{{right}}",
                "Implementation\ndef area(r):\n    return 3.14 * r * r\nConstraints\n- Reject negative radii.",
            ),
            (
                "lesson",
                "notes",
                "A = πr²",
                "notes",
                "What changes when the radius doubles?",
                "Circle area\n{{left}}\nPractice\n{{right}}",
                "Circle area\n- A = πr²\nPractice\n- What changes when the radius doubles?",
            ),
        ]
        for title, lf, left, rf, right, center, expected in cases:
            with self.subTest(title):
                board = self.store.create(title)
                bid, sid = board["id"], board["sections"][0]["id"]
                self.store.update(bid, sid, "left", 0, left, "Mira", lf)
                self.store.update(bid, sid, "right", 0, right, "Ren", rf)
                result = self.store.update(bid, sid, "center", 0, center, "Narrator", "prose")
                self.assertEqual(render(result["sections"][0])["text"], expected)
                revised = self.store.update(bid, sid, "left", 1, left + " Revised.", "Mira", lf)
                self.assertIn("Revised.", render(revised["sections"][0])["text"])
                self.assertEqual(revised["sections"][0]["lanes"]["center"]["text"], center)
                self.assertEqual(revised["sections"][0]["lanes"]["right"]["text"], right)


if __name__ == "__main__":
    unittest.main()
