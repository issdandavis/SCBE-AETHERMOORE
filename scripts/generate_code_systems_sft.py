#!/usr/bin/env python3
"""Generate the 6 missing code-systems SFT datasets from the SCBE codebase.

Produces:
  1. code_brushes_sft.jsonl          - Reusable code patterns from TS/Python
  2. code_substrate_l0_sft.jsonl     - L0 binary-first substrate patterns
  3. infrastructure_sft.jsonl        - Docker, CI/CD, deploy, config patterns
  4. typescript_docs_sft.jsonl       - TypeScript module explanations + usage
  5. python_docstrings_sft.jsonl     - Python function docstring Q&A pairs
  6. universal_code_primitives_sft.jsonl - Cross-language primitive patterns
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "training-data" / "sft"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM_MSG = (
    "You are Polly, the SCBE-AETHERMOORE coding assistant. "
    "You explain code patterns, architecture, and implementation details "
    "from the 14-layer security pipeline."
)


def sft_record(user: str, assistant: str, tags: list[str] | None = None) -> dict:
    rec: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }
    if tags:
        rec["tags"] = tags
    return rec


def write_jsonl(path: Path, records: list[dict]) -> int:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


# ─────────────────────────────────────────────
# 1. Code Brushes — reusable patterns from TS
# ─────────────────────────────────────────────

def generate_code_brushes() -> list[dict]:
    records = []
    ts_files = sorted((ROOT / "src").rglob("*.ts"))

    # Extract exported functions/classes
    export_re = re.compile(
        r"^export\s+(function|class|const|interface|type|enum)\s+(\w+)",
        re.MULTILINE,
    )
    jsdoc_re = re.compile(r"/\*\*\s*(.*?)\*/", re.DOTALL)

    for f in ts_files:
        if "node_modules" in str(f) or "dist" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = f.relative_to(ROOT)
        exports = export_re.findall(text)
        jsdocs = jsdoc_re.findall(text)

        for kind, name in exports:
            # Find the surrounding context (up to 40 lines after the export)
            pattern = re.compile(
                rf"^(export\s+{kind}\s+{re.escape(name)}.*?)(?=\nexport\s|\nclass\s|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            match = pattern.search(text)
            if not match:
                continue
            snippet = match.group(1)[:1500]  # cap length
            if len(snippet) < 80:
                continue

            # Find closest JSDoc above
            doc_hint = ""
            pos = match.start()
            for doc in jsdocs:
                clean = " ".join(doc.split())
                if clean and text.find("/**") < pos:
                    doc_hint = clean[:300]

            user_q = f"Explain the `{name}` {kind} from `{rel}` and show how to use it."
            answer = f"`{name}` is a {kind} defined in `{rel}`.\n\n"
            if doc_hint:
                answer += f"Documentation: {doc_hint}\n\n"
            answer += f"```typescript\n{snippet}\n```\n\n"
            answer += f"This is part of the SCBE 14-layer pipeline."

            records.append(sft_record(user_q, answer, ["code-brush", kind]))

        if len(records) >= 200:
            break

    return records


# ─────────────────────────────────────────────
# 2. Code Substrate L0 — binary-first patterns
# ─────────────────────────────────────────────

def generate_code_substrate_l0() -> list[dict]:
    records = []

    # Mine L0/L1 substrate files
    substrate_dirs = [
        ROOT / "src" / "harmonic",
        ROOT / "src" / "symphonic_cipher" / "scbe_aethermoore",
        ROOT / "src" / "tokenizer",
        ROOT / "src" / "crypto",
    ]

    binary_keywords = [
        "binary", "bit", "encode", "decode", "hash", "digest",
        "token", "embed", "quantize", "normalize", "clamp",
    ]

    for d in substrate_dirs:
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.py")):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rel = f.relative_to(ROOT)

            # Parse functions
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                name = node.name
                if name.startswith("_") and not name.startswith("__"):
                    continue

                docstring = ast.get_docstring(node) or ""
                # Check if function is substrate-relevant
                source_lines = text.split("\n")
                start = node.lineno - 1
                end = min(node.end_lineno or start + 30, len(source_lines))
                body = "\n".join(source_lines[start:end])

                if not any(kw in body.lower() or kw in name.lower() for kw in binary_keywords):
                    continue
                if len(body) < 60:
                    continue

                snippet = body[:1200]
                user_q = f"What does `{name}` in `{rel}` do at the L0 substrate level?"
                answer = f"`{name}` is a substrate-level function in `{rel}`.\n\n"
                if docstring:
                    answer += f"{docstring[:400]}\n\n"
                answer += f"```python\n{snippet}\n```"

                records.append(sft_record(user_q, answer, ["l0-substrate", "binary-first"]))

        if len(records) >= 150:
            break

    # Also mine TS substrate
    for f in sorted((ROOT / "src" / "harmonic").rglob("*.ts")):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = f.relative_to(ROOT)

        fn_re = re.compile(r"(?:export\s+)?function\s+(\w+)\s*\(([^)]*)\)[^{]*\{", re.MULTILINE)
        for m in fn_re.finditer(text):
            name = m.group(1)
            if not any(kw in name.lower() or kw in text[m.start():m.start()+500].lower() for kw in binary_keywords):
                continue
            snippet = text[m.start():m.start()+1000]
            user_q = f"How does `{name}` in `{rel}` handle binary/encoding at the substrate level?"
            answer = f"`{name}` from `{rel}` operates at the binary substrate layer:\n\n```typescript\n{snippet}\n```"
            records.append(sft_record(user_q, answer, ["l0-substrate", "typescript"]))

        if len(records) >= 200:
            break

    return records


# ─────────────────────────────────────────────
# 3. Infrastructure — Docker, CI, deploy, config
# ─────────────────────────────────────────────

def generate_infrastructure() -> list[dict]:
    records = []

    # Dockerfiles
    for df in sorted(ROOT.glob("Dockerfile*")):
        try:
            text = df.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        name = df.name
        user_q = f"Explain the `{name}` and what it builds."
        # Summarize stages
        stages = re.findall(r"^FROM\s+(.+?)(?:\s+AS\s+(\w+))?$", text, re.MULTILINE)
        stage_desc = ", ".join(f"{s[1] or 'base'} ({s[0]})" for s in stages) if stages else "single-stage"
        answer = f"`{name}` is a Docker build file with stages: {stage_desc}.\n\n```dockerfile\n{text[:1500]}\n```"
        records.append(sft_record(user_q, answer, ["infrastructure", "docker"]))

    # CI workflows
    wf_dir = ROOT / ".github" / "workflows"
    if wf_dir.exists():
        for wf in sorted(wf_dir.glob("*.yml"))[:30]:
            try:
                text = wf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            name = wf.stem
            # Extract 'name:' field
            name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
            wf_name = name_match.group(1).strip() if name_match else name
            triggers = re.findall(r"^\s+- (push|pull_request|schedule|workflow_dispatch)", text, re.MULTILINE)
            trigger_str = ", ".join(set(triggers)) if triggers else "manual"

            user_q = f"What does the `{wf_name}` CI workflow do and when does it trigger?"
            answer = (
                f"The `{wf_name}` workflow (`{wf.name}`) triggers on: {trigger_str}.\n\n"
                f"```yaml\n{text[:1200]}\n```"
            )
            records.append(sft_record(user_q, answer, ["infrastructure", "ci-cd"]))

    # K8s manifests
    k8s_dir = ROOT / "k8s"
    if k8s_dir.exists():
        for mf in sorted(k8s_dir.rglob("*.yaml"))[:10]:
            try:
                text = mf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = mf.relative_to(ROOT)
            kind_match = re.search(r"^kind:\s*(\w+)", text, re.MULTILINE)
            kind = kind_match.group(1) if kind_match else "resource"
            user_q = f"What does the Kubernetes {kind} in `{rel}` configure?"
            answer = f"`{rel}` defines a Kubernetes {kind}:\n\n```yaml\n{text[:1200]}\n```"
            records.append(sft_record(user_q, answer, ["infrastructure", "k8s"]))

    # Docker compose files
    for dc in sorted(ROOT.glob("docker-compose*.yml")):
        try:
            text = dc.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        services = re.findall(r"^\s{2}(\w[\w-]*):", text, re.MULTILINE)
        user_q = f"What services does `{dc.name}` orchestrate?"
        answer = f"`{dc.name}` defines services: {', '.join(services[:10])}.\n\n```yaml\n{text[:1200]}\n```"
        records.append(sft_record(user_q, answer, ["infrastructure", "docker-compose"]))

    # Config files
    for cfg_dir in [ROOT / "config"]:
        if not cfg_dir.exists():
            continue
        for cf in sorted(cfg_dir.rglob("*"))[:15]:
            if cf.is_dir() or cf.stat().st_size > 50000:
                continue
            try:
                text = cf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = cf.relative_to(ROOT)
            user_q = f"What is the purpose of the config file `{rel}`?"
            answer = f"`{rel}` configures part of the SCBE stack:\n\n```\n{text[:1000]}\n```"
            records.append(sft_record(user_q, answer, ["infrastructure", "config"]))

    return records


# ─────────────────────────────────────────────
# 4. TypeScript Docs — module-level explanations
# ─────────────────────────────────────────────

def generate_typescript_docs() -> list[dict]:
    records = []

    for f in sorted((ROOT / "src").rglob("*.ts")):
        if "node_modules" in str(f) or "dist" in str(f) or ".d.ts" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = f.relative_to(ROOT)
        if len(text) < 200:
            continue

        # Extract file header comment
        header = ""
        header_match = re.match(r"/\*\*\s*(.*?)\*/", text, re.DOTALL)
        if header_match:
            header = " ".join(header_match.group(1).split())[:500]

        # Extract layer/module/component tags
        layer_match = re.search(r"@layer\s+(.+)", text)
        module_match = re.search(r"@module\s+(.+)", text)
        layer = layer_match.group(1).strip() if layer_match else ""
        module = module_match.group(1).strip() if module_match else ""

        # Extract exports
        exports = re.findall(r"export\s+(?:function|class|const|interface)\s+(\w+)", text)
        export_list = ", ".join(exports[:10]) if exports else "internal"

        user_q = f"What does the TypeScript module `{rel}` do and what does it export?"
        answer = f"**Module**: `{rel}`\n"
        if layer:
            answer += f"**Layer**: {layer}\n"
        if module:
            answer += f"**Module path**: {module}\n"
        if header:
            answer += f"\n{header}\n"
        answer += f"\n**Exports**: {export_list}\n"
        answer += f"\n```typescript\n{text[:1500]}\n```"

        records.append(sft_record(user_q, answer, ["typescript-docs", layer or "general"]))

        if len(records) >= 200:
            break

    return records


# ─────────────────────────────────────────────
# 5. Python Docstrings — function-level Q&A
# ─────────────────────────────────────────────

def generate_python_docstrings() -> list[dict]:
    records = []

    py_dirs = [ROOT / "src", ROOT / "scripts", ROOT / "agents", ROOT / "mcp"]

    for d in py_dirs:
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.py")):
            if "__pycache__" in str(f):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except Exception:
                continue

            rel = f.relative_to(ROOT)
            source_lines = text.split("\n")

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue

                name = node.name
                docstring = ast.get_docstring(node)
                if not docstring or len(docstring) < 30:
                    continue

                start = node.lineno - 1
                end = min(node.end_lineno or start + 20, len(source_lines))
                # Just the signature + docstring, not full body
                sig_end = min(start + 25, end)
                snippet = "\n".join(source_lines[start:sig_end])

                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                user_q = f"What does the Python {kind} `{name}` in `{rel}` do?"
                answer = f"`{name}` ({kind} in `{rel}`):\n\n{docstring[:600]}\n\n```python\n{snippet}\n```"

                records.append(sft_record(user_q, answer, ["python-docstring", kind]))

            if len(records) >= 200:
                break
        if len(records) >= 200:
            break

    return records


# ─────────────────────────────────────────────
# 6. Universal Code Primitives — cross-language
# ─────────────────────────────────────────────

def generate_universal_primitives() -> list[dict]:
    records = []

    # Find functions/concepts that exist in BOTH TS and Python
    ts_names: dict[str, tuple[str, str]] = {}
    py_names: dict[str, tuple[str, str]] = {}

    # Collect TS function names
    for f in (ROOT / "src").rglob("*.ts"):
        if "node_modules" in str(f) or "dist" in str(f) or ".d.ts" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(f.relative_to(ROOT))
        for m in re.finditer(r"(?:export\s+)?function\s+(\w+)", text):
            name = m.group(1)
            snippet = text[m.start():m.start()+800]
            ts_names[name.lower()] = (rel, snippet)

    # Collect Python function names
    for f in (ROOT / "src").rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(f.relative_to(ROOT))
        for m in re.finditer(r"^def\s+(\w+)", text, re.MULTILINE):
            name = m.group(1)
            snippet = text[m.start():m.start()+800]
            # Normalize: snake_case -> lowercase for matching
            normalized = name.lower().replace("_", "")
            py_names[normalized] = (rel, snippet)

    # Find matches (same name in both languages)
    ts_normalized = {}
    for name, val in ts_names.items():
        ts_normalized[name.lower().replace("_", "")] = (name, val)

    matched = 0
    for py_key, (py_path, py_snip) in py_names.items():
        if py_key in ts_normalized:
            ts_orig, (ts_path, ts_snip) = ts_normalized[py_key]
            user_q = (
                f"Show the cross-language implementation of `{py_key}` "
                f"in both TypeScript and Python."
            )
            answer = (
                f"This primitive exists in both languages:\n\n"
                f"**TypeScript** (`{ts_path}`):\n```typescript\n{ts_snip[:600]}\n```\n\n"
                f"**Python** (`{py_path}`):\n```python\n{py_snip[:600]}\n```\n\n"
                f"Both implementations must produce identical outputs for cross-language parity."
            )
            records.append(sft_record(user_q, answer, ["universal-primitive", "cross-language"]))
            matched += 1
            if matched >= 100:
                break

    # Also add standalone primitives from core modules
    core_primitives = [
        ("hyperbolic distance", "arcosh(1 + 2*||u-v||^2 / ((1-||u||^2)*(1-||v||^2)))"),
        ("harmonic wall", "H(d,pd) = 1/(1 + phi*d_H + 2*pd)"),
        ("poincare embedding", "exp_0(v) = tanh(||v||/2) * v/||v||"),
        ("mobius addition", "a (+) b = ((1+2<a,b>+||b||^2)*a + (1-||a||^2)*b) / (1+2<a,b>+||a||^2*||b||^2)"),
        ("breathing transform", "B(t) = A * sin(omega*t + phase) * decay(t)"),
        ("lift coefficient", "C_L = 2*pi*sin(alpha) pre-stall"),
    ]

    for name, formula in core_primitives:
        user_q = f"What is the `{name}` primitive and its canonical formula?"
        answer = (
            f"The `{name}` is a universal SCBE primitive.\n\n"
            f"**Formula**: `{formula}`\n\n"
            f"This primitive is implemented in both TypeScript (canonical) and Python (reference). "
            f"Cross-language parity tests verify identical outputs."
        )
        records.append(sft_record(user_q, answer, ["universal-primitive", "formula"]))

    return records


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    generators = [
        ("code_brushes_sft.jsonl", generate_code_brushes),
        ("code_substrate_l0_sft.jsonl", generate_code_substrate_l0),
        ("infrastructure_sft.jsonl", generate_infrastructure),
        ("typescript_docs_sft.jsonl", generate_typescript_docs),
        ("python_docstrings_sft.jsonl", generate_python_docstrings),
        ("universal_code_primitives_sft.jsonl", generate_universal_primitives),
    ]

    total = 0
    for filename, gen_fn in generators:
        print(f"Generating {filename}...", end=" ", flush=True)
        records = gen_fn()
        count = write_jsonl(OUT / filename, records)
        print(f"{count} records")
        total += count

    print(f"\nTotal: {total} records across 6 files")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
