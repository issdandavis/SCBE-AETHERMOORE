"""EPUB and DOCX builders (pandoc-driven)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .profile import Profile


class PandocNotAvailable(RuntimeError):
    pass


def _ensure_pandoc() -> None:
    if shutil.which("pandoc") is None:
        raise PandocNotAvailable("pandoc not found on PATH. Install from https://pandoc.org/installing.html")


_EPUB_CSS = """\
@namespace epub "http://www.idpf.org/2007/ops";
body { font-family: serif; line-height: 1.5; margin: 0.5em; }
h1 {
  page-break-before: always;
  break-before: page;
  -epub-page-break-before: always;
  text-align: center;
  margin-top: 3em;
  margin-bottom: 1.5em;
  font-size: 1.4em;
}
h2 { margin-top: 1.5em; margin-bottom: 0.6em; font-size: 1.2em; }
h3 { margin-top: 1.2em; margin-bottom: 0.5em; font-size: 1.05em; }
p { margin: 0 0 0.6em 0; text-indent: 1.5em; }
p.first, h1 + p, h2 + p, h3 + p, blockquote + p { text-indent: 0; }
blockquote { margin: 0.8em 1.5em; font-style: italic; }
hr { border: 0; text-align: center; margin: 1.2em 0; }
hr:after { content: "* * *"; letter-spacing: 0.4em; }
"""


def _write_epub_css(out_dir: Path) -> Path:
    css_path = (out_dir / "bookforge-epub.css").resolve()
    css_path.write_text(_EPUB_CSS, encoding="utf-8")
    return css_path


def build_epub(profile: Profile, *, out_path: Optional[Path] = None) -> Path:
    _ensure_pandoc()
    p = profile
    p.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (p.output_dir / f"{p.source_md.stem}.epub")
    out_path = Path(out_path).resolve()
    css_path = _write_epub_css(p.output_dir)

    args = [
        "pandoc", str(p.source_md),
        "-o", str(out_path),
        "--toc", "--toc-depth=2",
        "--epub-chapter-level=1",
        "--css", str(css_path),
        "--metadata", f"title={p.title}",
    ]
    if p.subtitle:
        args += ["--metadata", f"subtitle={p.subtitle}"]
    if p.author:
        args += ["--metadata", f"author={p.author}"]
    if p.publisher:
        args += ["--metadata", f"publisher={p.publisher}"]
    if p.isbn:
        args += ["--metadata", f"identifier={p.isbn}"]
    args += ["--metadata", "lang=en"]

    subprocess.run(args, check=True)
    return out_path


def build_docx(profile: Profile, *, out_path: Optional[Path] = None) -> Path:
    _ensure_pandoc()
    p = profile
    p.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (p.output_dir / f"{p.source_md.stem}.docx")
    out_path = Path(out_path).resolve()

    args = [
        "pandoc", str(p.source_md),
        "-o", str(out_path),
        "--toc", "--toc-depth=2",
        "-s",
        "--metadata", f"title={p.title}",
    ]
    if p.author:
        args += ["--metadata", f"author={p.author}"]
    subprocess.run(args, check=True)
    return out_path
