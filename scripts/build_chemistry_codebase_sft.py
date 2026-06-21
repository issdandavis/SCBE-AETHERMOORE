"""build_chemistry_codebase_sft: self-contained chemistry-primary SFT from the chem CODE + docs + notes.

The older scripts/build_chemistry_primary_sft.py filters drill_langues_full_*.sft.jsonl -- which is NOT in
the repo (the drill source was never committed), so chemistry never actually entered training. This
generator is self-contained: it mines the chemistry material that DOES ship in the repo into chat-`messages`
SFT records, with no external data dependency, so the systems-coder notebook can include chem on the next run.

Sources (all in-repo):
  * the chemistry MODULES   -- reaction_language, reaction_state, reaction_balance, reaction_harness,
                               chemical_fusion, chemistry_dimensions, atomic_tokenization (module +
                               function/class docstrings -> Q/A)
  * the chemistry SPECS/RESEARCH docs + THEORY notes (markdown sections -> Q/A)

Output: training-data/sft/chemistry_codebase_sft.jsonl  ({"messages": [...]} records).

    python scripts/build_chemistry_codebase_sft.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "training-data" / "sft" / "chemistry_codebase_sft.jsonl"

SYSTEM = (
    "You are an SCBE-AETHERMOORE chemistry-coding assistant. You understand the atomic/semantic tokenizer, "
    "the reaction language, the cross-language reaction state model, reaction balancing, and chemical fusion "
    "as a coding system. Write correct, SCBE-style code and clear explanations."
)

CHEM_PY = [
    "python/scbe/reaction_language.py",
    "python/scbe/reaction_state.py",
    "python/scbe/reaction_balance.py",
    "python/scbe/reaction_harness.py",
    "python/scbe/chemical_fusion.py",
    "python/scbe/chemistry_dimensions.py",
    "python/scbe/atomic_tokenization.py",
]
CHEM_DOCS = [
    "docs/SEMANTIC_ATOM_TOKENIZER.md",
    "docs/specs/CHEM_SEMANTIC_DECOMPOSITION_BRIDGE.md",
    "docs/specs/CROSS_LANGUAGE_REACTION_STATE_MODEL.md",
    "docs/research/chemistry_cli_space_systems_2026-05-31.md",
    "docs/research/layered_lattice_molecular_ai_targets_2026-05-31.md",
    "notes/theory/atomic-tokenizer-chemistry-unified.md",
    "notes/theory/pooled-reaction-energy-storage.md",
    "notes/round-table/2026-03-20-molecular-orbitals-of-context.md",
]


def _rec(user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {"source": "chemistry_codebase_sft", "lane": "chemistry_primary"},
    }


def py_pairs(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return []
    out: list[dict] = []
    mod_doc = ast.get_docstring(tree)
    if mod_doc and len(mod_doc) > 40:
        out.append(_rec("Explain the `%s` module in SCBE's chemistry coding system." % path.stem, mod_doc.strip()))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            if not doc or len(doc) < 40:
                continue
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            try:
                sig = ast.unparse(node.args) if not isinstance(node, ast.ClassDef) else ""
            except Exception:
                sig = ""
            q = "In SCBE's chemistry system (`%s`), what does the %s `%s(%s)` do?" % (path.stem, kind, node.name, sig)
            out.append(_rec(q, doc.strip()))
    return out


def md_pairs(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[dict] = []
    # split on markdown headings; each (heading, body) with a substantial body becomes one Q/A
    parts = re.split(r"(?m)^#{1,4}\s+(.+)$", text)
    # parts = [pre, h1, body1, h2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()[:140]
        body = parts[i + 1].strip()
        if len(body) < 80:
            continue
        out.append(_rec("Explain '%s' in SCBE's chemistry system." % title, body[:1800]))
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for rel in CHEM_PY:
        p = REPO / rel
        if p.exists():
            n = len(records)
            records.extend(py_pairs(p))
            print("  PY   %-44s %d pairs" % (rel, len(records) - n))
        else:
            print("  miss %-44s (not found)" % rel)
    for rel in CHEM_DOCS:
        p = REPO / rel
        if p.exists():
            n = len(records)
            records.extend(md_pairs(p))
            print("  DOC  %-44s %d pairs" % (rel, len(records) - n))
        else:
            print("  miss %-44s (not found)" % rel)
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("\n[chemistry_codebase_sft] wrote %d records -> %s" % (len(records), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
