"""Small deterministic worker used by the shell's real manuscript rehearsal."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["audit", "snapshot", "export"])
    parser.add_argument("--base", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    parsed = urllib.parse.urlsplit(args.base)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or parsed.username
        or parsed.password
    ):
        parser.error("This rehearsal only uses the local writing server")
    url = args.base.rstrip("/") + "/boards/" + urllib.parse.quote(args.board, safe="")
    with urllib.request.urlopen(url, timeout=15) as reply:
        source = reply.read(32 * 1024 * 1024 + 1)
    if len(source) > 32 * 1024 * 1024:
        raise ValueError("Source exceeds rehearsal limit")
    board = json.loads(source)
    report = {
        "operation": args.operation,
        "sections": len(board["sections"]),
        "source_sha256": hashlib.sha256(source).hexdigest(),
    }
    if args.operation == "audit":
        with urllib.request.urlopen(url + "/preview", timeout=15) as reply:
            preview = json.load(reply)
        report["rendered_words"] = sum(len(s["text"].split()) for s in preview["sections"])
        report["unresolved_references"] = sum(
            s["text"].count("{{left") + s["text"].count("{{right") for s in preview["sections"]
        )
        report["unique_section_ids"] = len({s["id"] for s in board["sections"]}) == len(board["sections"])
    else:
        if not args.output:
            parser.error("--output is required for a file operation")
        data = source
        if args.operation == "export":
            with urllib.request.urlopen(url + "/export.docx", timeout=15) as reply:
                data = reply.read(32 * 1024 * 1024 + 1)
            with ZipFile(BytesIO(data)) as doc:
                xml = ET.fromstring(doc.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                report["heading_count"] = len(xml.findall(".//w:pStyle[@w:val='Heading1']", ns))
        target = Path(args.output)
        with target.open("xb") as file:  # never overwrite a manuscript or a prior receipt
            file.write(data)
        report.update(path=str(target), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
