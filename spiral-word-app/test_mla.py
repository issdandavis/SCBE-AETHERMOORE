"""Check real exported package semantics, not just compiler success."""

import base64
from io import BytesIO
import json
from pathlib import Path
import subprocess
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from fastapi.testclient import TestClient
from app import app
from mla_api import compile_document

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
DOCUMENT = dict(
    firstName="Issac",
    lastName="Davis",
    instructor="John Anderson",
    course="English 101",
    date="2026-09-24",
    title="An Evening Walk",
    body="Practice example: rain & wind <outside>.\nSecond paragraph: café.",
    works="Example author. Example work.",
)


class MLATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compile_document(DOCUMENT, True)
        cls.data = base64.b64decode(cls.result["base64"])

    def xml(self, name):
        with ZipFile(BytesIO(self.data)) as z:
            self.assertIsNone(z.testzip())
            return ET.fromstring(z.read("word/" + name + ".xml"))

    def test_heading_content_and_escaping(self):
        texts = [n.text for n in self.xml("document").findall(".//w:t", NS)]
        self.assertEqual(
            texts[:5], ["Issac Davis", "John Anderson", "English 101", "24 September 2026", "An Evening Walk"]
        )
        self.assertIn("Practice example: rain & wind <outside>.", texts)
        self.assertIn("Second paragraph: café.", texts)
        self.assertEqual(self.result["filename"], "Davis, Issac My MLA Template.docx")

    def test_margins_spacing_font_indent_and_plain_title(self):
        doc = self.xml("document")
        margin = doc.find(".//w:pgMar", NS)
        for side in ("top", "bottom", "left", "right"):
            self.assertEqual(margin.get(W + side), "1440")
        self.assertEqual(margin.get(W + "header"), "720")
        paragraphs = doc.findall(".//w:body/w:p", NS)
        for p in paragraphs:
            spacing = p.find("w:pPr/w:spacing", NS)
            self.assertEqual([spacing.get(W + k) for k in ("line", "before", "after")], ["480", "0", "0"])
        self.assertEqual(paragraphs[4].find("w:pPr/w:jc", NS).get(W + "val"), "center")
        for prop in ("b", "i", "u"):
            self.assertIsNone(paragraphs[4].find(".//w:" + prop, NS))
        self.assertEqual(paragraphs[5].find("w:pPr/w:ind", NS).get(W + "firstLine"), "720")
        for name in ("document", "header1"):
            for font in self.xml(name).findall(".//w:rFonts", NS):
                self.assertEqual(font.get(W + "ascii"), "Times New Roman")
            for size in self.xml(name).findall(".//w:sz", NS):
                self.assertEqual(size.get(W + "val"), "24")

    def test_real_running_field_and_works_page_break(self):
        hdr = self.xml("header1")
        self.assertEqual(hdr.find(".//w:fldSimple", NS).get(W + "instr").strip(), "PAGE")
        self.assertEqual(hdr.find(".//w:t", NS).text, "Davis ")
        doc = self.xml("document")
        self.assertEqual(len(doc.findall(".//w:pageBreakBefore", NS)), 1)
        self.assertEqual(doc.findall(".//w:body/w:p", NS)[-1].find("w:pPr/w:ind", NS).get(W + "hanging"), "720")
        self.assertIsNone(doc.find(".//w:titlePg", NS))

    def test_required_fields_dates_and_valid_leap_day(self):
        for change in ({"date": "2026-02-30"}, {"title": "Untitled"}, {"body": ""}, {"course": ""}):
            result = compile_document({**DOCUMENT, **change})
            self.assertTrue(any(not c["ok"] for c in result["checks"]))
        self.assertTrue(all(c["ok"] for c in compile_document({**DOCUMENT, "date": "2028-02-29"})["checks"]))

    def test_api_same_bytes_and_local_origin_restriction(self):
        with TestClient(app, base_url="http://127.0.0.1") as client:
            self.assertEqual(client.get("/mla/").status_code, 200)
            response = client.post("/mla/api/export.docx", json=DOCUMENT)
            self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else "")
            self.assertEqual(response.content, self.data)
            self.assertEqual(
                client.post(
                    "/mla/api/validate", json=DOCUMENT, headers={"origin": "https://foreign.example"}
                ).status_code,
                403,
            )
            self.assertEqual(client.post("/mla/api/validate", json={**DOCUMENT, "unexpected": 1}).status_code, 422)
            self.assertEqual(client.post("/mla/api/export.docx", json={**DOCUMENT, "body": ""}).status_code, 422)

    def test_plugins_are_data_only_and_reject_unknown_operators(self):
        core = Path(__file__).parent / "mla_web" / "core.js"
        script = """const m=require(process.argv[1]);const d=m.clean({body:'one two three'});
        const p={schema:'spiralword.rules.v1',name:'Practice',rules:[{field:'body',op:'minWords',value:4,label:'Four words'}]};
        if(m.pluginRules(p,d)[0].ok)process.exit(1);
        p.rules[0].op='eval';try{m.pluginRules(p,d);process.exit(2);}catch{}
        process.stdout.write('ok');"""
        result = subprocess.run(["node", "-e", script, str(core.resolve())], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "ok")


if __name__ == "__main__":
    unittest.main()
