#!/usr/bin/env python3
"""Deterministic LaTeX paper synthesis from an aggregated documentation bundle.

This intentionally avoids external LLM calls so CI can run offline.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TITLE_DEFAULT = "Hyperbolic Lattice Cross-Stitch: Geometric AI Governance with Post-Quantum Security"


def _extract_sentences(text: str, limit: int = 4) -> list[str]:
    candidates = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    clean = []
    for c in candidates:
        s = c.strip()
        if len(s) < 35:
            continue
        clean.append(s)
        if len(clean) >= limit:
            break
    return clean


def synthesize_latex(bundle: dict, title: str, author: str) -> str:
    docs = bundle.get("documents", [])
    overview = " ".join((d.get("content", "")[:1200] for d in docs[:6]))
    abstract_lines = _extract_sentences(overview, limit=3)
    abstract = " ".join(abstract_lines) or "This paper presents a governed AI runtime that combines hyperbolic geometry, multi-agent coordination, and post-quantum security controls."

    refs = "\n".join(f"\\item \\texttt{{{d.get('path', 'unknown')}}}" for d in docs[:20])

    return f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{hyperref}}
\\title{{{title}}}
\\author{{{author}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
{abstract}
\\end{{abstract}}

\\section{{Introduction}}
SCBE-AETHERMOORE combines governed execution, multi-agent orchestration, and cryptographic policy enforcement to support long-horizon autonomy.

\\section{{Related Work}}
We build on hyperbolic representation learning, post-quantum cryptography standardization, and secure multi-agent control pipelines.

\\section{{System Architecture}}
The system layers policy evaluation, trust zoning, and action verification around browser and workflow agents. A practical control loop maps actions to decisions in \\{{ALLOW, QUARANTINE, DENY\\}}.

\\section{{Mathematical and Security Framework}}
A bounded hyperbolic manifold is used as a geometry-aware risk space. A safety score can be represented as:
\\[
H(d,p_d)=\\frac{{1}}{{1+d+2p_d}}
\\]
where $d$ is geometric distance and $p_d$ is projected drift.

\\section{{Implementation}}
Implementation artifacts include TypeScript and Python modules for orchestration, verification, and audit trace generation.

\\section{{Evaluation Plan}}
We evaluate reliability for long-horizon mission execution using chunked action scheduling, lock-aware coordination, and governance checkpoints.

\\section{{Applications}}
Potential applications include governed enterprise agents, multi-browser operational automation, and resilient remote swarm workloads.

\\section{{Source Artifacts}}
The following source files were synthesized into this draft:
\\begin{{itemize}}
{refs}
\\end{{itemize}}

\\section{{Conclusion}}
This draft provides an auditable bridge from architecture specification to repeatable publication packaging.

\\end{{document}}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize arXiv-ready LaTeX from aggregated docs")
    parser.add_argument("--bundle", default="artifacts/arxiv/aggregated_bundle.json")
    parser.add_argument("--title", default=TITLE_DEFAULT)
    parser.add_argument("--author", default="Issac Davis")
    parser.add_argument("--output", default="artifacts/arxiv/paper.tex")
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    latex = synthesize_latex(bundle=bundle, title=args.title, author=args.author)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(latex, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
