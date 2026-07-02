"""XeLaTeX interior PDF builder.

Pipeline: manuscript.md -> pandoc -> body.tex -> wrapped document.tex
-> xelatex (twice, for TOC stabilization) -> PDF.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from importlib import resources
from pathlib import Path
from typing import Optional

from .manuscript import clean_source_text
from .profile import Profile


class XeLaTeXNotAvailable(RuntimeError):
    pass


def is_available() -> bool:
    return shutil.which("xelatex") is not None and shutil.which("pandoc") is not None


def _latex_escape(text: str) -> str:
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    out = text
    for a, b in replacements:
        out = out.replace(a, b)
    return out


def _scene_break_filter_path() -> Path:
    """Locate the bundled Lua filter on disk."""
    try:
        anchor = resources.files("scbe_bookforge").joinpath("templates/scene_break.lua")
        with resources.as_file(anchor) as p:
            return Path(p).resolve()
    except (ModuleNotFoundError, FileNotFoundError):
        here = Path(__file__).resolve().parent / "templates" / "scene_break.lua"
        if here.exists():
            return here
        raise FileNotFoundError("scene_break.lua filter not packaged with scbe_bookforge")


def _run_pandoc_to_body_tex(source_md: Path, body_tex: Path) -> None:
    """Convert the manuscript body to LaTeX. Shift level-2 headings to chapters."""
    cleaned_text, _ = clean_source_text(source_md.read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(cleaned_text)
        tmp_path = Path(tmp.name)

    try:
        subprocess.run(
            [
                "pandoc",
                "-f", "markdown+smart",
                "-t", "latex",
                "--shift-heading-level-by=-1",
                "--lua-filter", str(_scene_break_filter_path()),
                "--wrap=preserve",
                "-o", str(body_tex),
                str(tmp_path),
            ],
            check=True,
        )
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _compose_document(profile: Profile, body_tex_relpath: str) -> str:
    """Build the wrapping LaTeX source around the pandoc-produced body."""
    p = profile
    inside = p.effective_inside_in
    chapter_size_inner = p.chapter_title_size_pt * 1.2

    parts: list[str] = []
    parts.append(rf"\documentclass[{int(round(p.body_size_pt))}pt,openright]{{book}}")
    parts.append(
        rf"\usepackage[paperwidth={p.trim_w_in}in,paperheight={p.trim_h_in}in,"
        rf"inner={inside}in,outer={p.outside_in}in,top={p.top_in}in,bottom={p.bottom_in}in,"
        rf"includehead,headsep=0.18in]{{geometry}}"
    )
    parts.append(r"\usepackage{fontspec}")
    parts.append(r"\usepackage[hidelinks]{hyperref}")
    parts.append(rf"\setmainfont{{{p.body_font}}}")
    parts.append(r"\usepackage{microtype}")
    parts.append(r"\usepackage{setspace}")
    line_stretch = round(p.leading_pt / p.body_size_pt, 4)
    parts.append(rf"\setstretch{{{line_stretch}}}")
    parts.append(r"\usepackage[english]{babel}")
    parts.append(r"\usepackage{titlesec}")
    parts.append(
        rf"\titleformat{{\chapter}}[block]"
        rf"{{\centering\bfseries\fontsize{{{p.chapter_title_size_pt}}}{{{chapter_size_inner:.2f}}}\selectfont}}"
        r"{}{0em}{}"
    )
    parts.append(r"\titlespacing*{\chapter}{0pt}{60pt}{30pt}")
    parts.append(r"\usepackage{fancyhdr}")
    parts.append(r"\pagestyle{fancy}")
    parts.append(r"\fancyhf{}")
    parts.append(r"\fancyhead[LE,RO]{\thepage}")
    parts.append(r"\fancyhead[CE]{\nouppercase{\leftmark}}")
    parts.append(r"\fancyhead[CO]{\nouppercase{\rightmark}}")
    parts.append(r"\renewcommand{\headrulewidth}{0pt}")
    parts.append(r"\fancypagestyle{plain}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}\renewcommand{\footrulewidth}{0pt}}")
    parts.append(r"\usepackage{emptypage}")
    parts.append(rf"\setlength{{\parindent}}{{{p.first_line_indent_in}in}}")
    parts.append(r"\setlength{\parskip}{0pt}")
    parts.append(r"\frenchspacing")

    # Prevent ToC from numbering chapters in a way that prints "Chapter X" twice
    parts.append(r"\renewcommand{\chaptername}{}")
    parts.append(r"\renewcommand{\thechapter}{}")

    parts.append(r"\sloppy")
    parts.append(r"\begin{document}")
    parts.append(r"\frontmatter")

    # Half title
    parts.append(r"\thispagestyle{empty}")
    parts.append(r"\vspace*{2in}")
    parts.append(r"\begin{center}")
    parts.append(rf"{{\fontsize{{18}}{{22}}\selectfont {_latex_escape(p.title.upper())}}}")
    parts.append(r"\end{center}")
    parts.append(r"\clearpage")

    # Title page
    parts.append(r"\thispagestyle{empty}")
    parts.append(r"\vspace*{1.4in}")
    parts.append(r"\begin{center}")
    parts.append(rf"{{\fontsize{{25}}{{30}}\bfseries\selectfont {_latex_escape(p.title)}}}\\[18pt]")
    if p.subtitle:
        parts.append(rf"{{\fontsize{{11}}{{14}}\itshape\selectfont {_latex_escape(p.subtitle)}}}\\[1.2in]")
    if p.author:
        parts.append(rf"{{\fontsize{{14}}{{16}}\selectfont by {_latex_escape(p.author)}}}")
    parts.append(r"\end{center}")
    parts.append(r"\clearpage")

    # Copyright page
    parts.append(r"\thispagestyle{empty}")
    parts.append(r"\vspace*{5.5in}")
    parts.append(r"{\fontsize{8.5}{11}\selectfont\noindent")
    parts.append(rf"Copyright \copyright\ {p.copyright_year} {_latex_escape(p.author)}. All rights reserved.\\[6pt]")
    if p.edition_statement:
        parts.append(rf"{_latex_escape(p.edition_statement)}\\")
    if p.isbn:
        parts.append(rf"{_latex_escape(p.isbn)}\\[6pt]")
    if p.creative_nonfiction_notice:
        parts.append(rf"{_latex_escape(p.creative_nonfiction_notice)}\\[6pt]")
    parts.append(
        r"No part of this book may be reproduced, distributed, or transmitted in any form "
        r"or by any means without prior written permission, except for brief quotations in "
        r"reviews, criticism, scholarship, or other uses permitted by law.\\[6pt]"
    )
    if p.publisher:
        parts.append(rf"Published by {_latex_escape(p.publisher)}")
    parts.append(r"}\clearpage")

    # Dedication
    if p.dedication:
        parts.append(r"\thispagestyle{empty}")
        parts.append(r"\vspace*{3in}")
        parts.append(r"\begin{center}\itshape")
        parts.append(_latex_escape(p.dedication))
        parts.append(r"\end{center}\clearpage")

    # Epigraph
    if p.epigraph_enabled and p.epigraph_text:
        parts.append(r"\thispagestyle{empty}")
        parts.append(r"\vspace*{3in}")
        parts.append(r"\begin{center}")
        parts.append(rf"\itshape {_latex_escape(p.epigraph_text)}")
        if p.epigraph_attribution:
            parts.append(rf"\\[12pt]\upshape\fontsize{{8.5}}{{11}}\selectfont --- {_latex_escape(p.epigraph_attribution)}")
        parts.append(r"\end{center}\clearpage")

    # Contents
    parts.append(r"\renewcommand{\contentsname}{\normalfont\Large Contents}")
    parts.append(r"\tableofcontents")
    parts.append(r"\clearpage")

    parts.append(r"\mainmatter")
    parts.append(rf"\input{{{body_tex_relpath}}}")
    parts.append(r"\end{document}")

    return "\n".join(parts) + "\n"


def build(
    profile: Profile,
    *,
    out_pdf: Optional[Path] = None,
    workdir: Optional[Path] = None,
) -> Path:
    """Build the interior PDF. Returns the absolute output path."""
    if not is_available():
        raise XeLaTeXNotAvailable(
            "XeLaTeX or pandoc not found. Install MiKTeX (https://miktex.org/) "
            "and pandoc (https://pandoc.org/installing.html), or set "
            "interior_engine='reportlab' in the profile."
        )

    profile.output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_pdf or (profile.output_dir / f"{profile.source_md.stem}-interior.pdf")
    out_pdf = Path(out_pdf).resolve()

    workdir = workdir or (profile.output_dir / "_bookforge_tex")
    workdir.mkdir(parents=True, exist_ok=True)

    body_tex = workdir / "body.tex"
    _run_pandoc_to_body_tex(profile.source_md, body_tex)

    document_tex = workdir / "document.tex"
    document_tex.write_text(_compose_document(profile, "body.tex"), encoding="utf-8")

    # Run xelatex twice for TOC + cross-refs to stabilize
    for _ in range(2):
        subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory", str(workdir),
                str(document_tex),
            ],
            check=True,
            cwd=str(workdir),
        )

    produced_pdf = workdir / "document.pdf"
    if not produced_pdf.exists():
        raise RuntimeError(f"xelatex completed but {produced_pdf} not found")

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.write_bytes(produced_pdf.read_bytes())
    return out_pdf
