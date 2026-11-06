"""
@file export.py
@module spiral-word-app/export
@layer Layer 14
@component Word .docx export (dependency-free)

Export a SpiralWord document to a real Word .docx. A .docx is just a zip of OOXML, so this needs no
python-docx — it returns the file as bytes for the API to stream. Wired into app.py as GET /doc/{id}/export.docx
(governed + audited like every other operation).
"""

import io
import re
import zipfile

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _para(text: str, bold: bool = False, size: int = None, style: str = None) -> str:
    rpr = ""
    if bold or size:
        rpr = "<w:rPr>%s%s</w:rPr>" % ("<w:b/>" if bold else "", ('<w:sz w:val="%d"/>' % size) if size else "")
    # XML 1.0 excludes control characters which can appear in pasted text.
    text = "".join(
        c
        for c in text
        if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
    )
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return '<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (ppr, rpr, _esc(text))


def parse_doc(text: str):
    """SpiralWord text -> (title, sections). First non-empty line = title; '# heading' lines start sections."""
    lines = text.splitlines()
    title = "Untitled"
    for i, ln in enumerate(lines):
        if ln.strip():
            title = ln.lstrip("# ").strip()
            lines = lines[i + 1 :]
            break
    sections, heading, paras = [], "", []
    for ln in lines:
        s = ln.strip()
        if s.startswith("#"):
            if heading or paras:
                sections.append((heading, paras))
                paras = []
            heading = s.lstrip("# ").strip()
        elif s:
            paras.append(s)
    if heading or paras:
        sections.append((heading, paras))
    return title, sections


def _document_xml(title: str, sections) -> str:
    body = [_para(title, bold=True, size=40)]
    for heading, paras in sections:
        if heading:
            body.append(_para(heading, bold=True, size=30))
        for p in paras:
            body.append(_para(p))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(body)
        + "<w:sectPr/></w:body></w:document>"
    )


def docx_bytes(text: str) -> bytes:
    """Render a SpiralWord document to a .docx file, returned as bytes."""
    title, sections = parse_doc(text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", _document_xml(title, sections))
    return buf.getvalue()


def docx_sections(title: str, sections) -> bytes:
    """Export explicit sections without interpreting their prose as Markdown."""
    body = [_para(title, bold=True, size=40, style="Title")]
    for heading, text in sections:
        body.append(_para(heading, bold=True, size=30, style="Heading1"))
        body.extend(_para(line) for line in text.split("\n"))
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        + "".join(body)
        + "<w:sectPr/></w:body></w:document>"
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style></w:styles>'
    )
    content_types = _CONTENT_TYPES.replace(
        "</Types>",
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml", xml)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", relationships)
    return buf.getvalue()


def read_docx_text(data: bytes) -> str:
    """Read the visible text back out of docx bytes — used to verify the export."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    return (
        "\n".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, re.S))
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


if __name__ == "__main__":
    data = docx_bytes("Report\n# Section\nhello & <world>\nsecond line\n")
    assert zipfile.is_zipfile(io.BytesIO(data)), "not a valid docx zip"
    txt = read_docx_text(data)
    assert "Report" in txt and "Section" in txt and "hello & <world>" in txt, txt
    print("export.py self-test ok: %d bytes, text round-trips (incl. XML-escaped chars)" % len(data))
